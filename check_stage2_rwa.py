#!/usr/bin/env python
"""Check that the RWA is valid, by propagating the pulses obtained from the
simplex optimization in the LAB frame
"""
import os
import time
import sys
import logging
import hashlib
logging.basicConfig(level=logging.ERROR)
from clusterjob import JobScript

from run_stage1 import split_seq, jobscript
from notebook_utils import get_stage2_table


def get_jobs(runs):
    """Generate a list of calls to ./prop_lab.py for "interesting" subfolders
    in the given 'runs' root"""
    jobs = []
    stage2_table = get_stage2_table(runs)
    (__, t_PE), (__, t_SQ) = stage2_table.groupby('target', sort=True)
    for runfolder in t_PE[(t_PE['max loss']<0.1) & (t_PE['C']>0.9)].index:
        if not os.path.isfile(os.path.join(runfolder, 'U_LAB.dat')):
            jobs.append('./prop_lab.py %s' % runfolder)
    for runfolder in t_SQ[(t_SQ['max loss']<0.1) & (t_SQ['C']<0.1)].index:
        if not os.path.isfile(os.path.join(runfolder, 'U_LAB.dat')):
            jobs.append('./prop_lab.py %s' % runfolder)
    return jobs


def main(argv=None):
    """Run RWA check"""
    from optparse import OptionParser
    if argv is None:
        argv = sys.argv
    arg_parser = OptionParser(
    usage = "usage: %prog [options] RUNS",
    description = __doc__)
    arg_parser.add_option(
        '--parallel', action='store', dest='parallel', type=int,
        default=1, help="Number of parallel processes per job [1]")
    arg_parser.add_option(
        '--jobs', action='store', dest='jobs', type=int,
        default=10, help="Number of jobs [10]")
    arg_parser.add_option(
        '--cluster-ini', action='store', dest='cluster_ini',
                    help="INI file from which to load clusterjob defaults")
    arg_parser.add_option(
        '-n', action='store_true', dest='dry_run',
        help="Perform a dry run")
    options, args = arg_parser.parse_args(argv)
    try:
        runs = os.path.join('.', os.path.normpath(args[1]))
    except IndexError:
        arg_parser.error("You must give RUNS")
    if not os.path.isdir(runs):
        arg_parser.error("RUNS must be a folder (%s)" % runs)
    if not runs.startswith(r'./'):
        arg_parser.error('RUNS must be relative to current folder, '
                         'e.g. ./runs')
    if options.cluster_ini is not None:
        JobScript.read_defaults(options.cluster_ini)
    submitted = []
    jobs = get_jobs(runs)
    job_ids = {}

    with open("check_stage2_rwa.log", "a") as log:
        log.write("%s\n" % time.asctime())
        for i_job, commands in enumerate(split_seq(jobs, options.jobs)):
            if len(commands) == 0:
                continue
            jobname = 'check_stage2_rwa_%02d' % (i_job+1)
            job = JobScript(body=jobscript(commands, options.parallel),
                            jobname=jobname, nodes=1, ppn=options.parallel,
                            stdout='%s-%%j.out'%jobname)
            cache_id = '%s_%s' % (
                        jobname, hashlib.sha256(str(argv)).hexdigest())
            if options.dry_run:
                print "======== JOB %03d ========" % (i_job + 1)
                print job
                print "========================="
            else:
                submitted.append(job.submit(cache_id=cache_id))
                job_ids[submitted[-1].job_id] = jobname
                log.write("Submitted %s to cluster as ID %s\n"%(
                        jobname, submitted[-1].job_id))
    for job in submitted:
        job.wait()
        if not job.successful():
            print "job '%s' did not finish successfully" % job_ids[job.job_id]

if __name__ == "__main__":
    sys.exit(main())
