#!/usr/bin/env python
"""create stage 4 runfolders, based on stage 3 runfolders"""
import os
import re
import sys
import logging
import QDYN
import numpy as np
from mgplottools.io import writetotxt
from run_stage1 import read_w2_wc
from clusterjob.utils import read_file, write_file
from notebook_utils import find_folders

HADAMARD = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)
PHASE = np.array([[1, 0], [0, np.exp(-0.25j*np.pi)]], dtype=np.complex128)

# single qubit target gates
GATE = {
    'H_left'  : QDYN.gate2q.Gate2Q(np.kron(HADAMARD, np.eye(2)), name='H_L'),
    'H_right' : QDYN.gate2q.Gate2Q(np.kron(np.eye(2), HADAMARD), name='H_R'),
    'Ph_left' : QDYN.gate2q.Gate2Q(np.kron(PHASE, np.eye(2)), name='S_L'),
    'Ph_right': QDYN.gate2q.Gate2Q(np.kron(np.eye(2), PHASE), name='S_R'),
    #'SWAP'    : QDYN.gate2q.SWAP,
}
GATE_RE = {
    'H_left'  : QDYN.linalg.vectorize(GATE['H_left']).real,
    'H_right' : QDYN.linalg.vectorize(GATE['H_right']).real,
    'Ph_left' : QDYN.linalg.vectorize(GATE['Ph_left']).real,
    'Ph_right': QDYN.linalg.vectorize(GATE['Ph_right']).real,
    #'SWAP'    : QDYN.linalg.vectorize(GATE['SWAP']).real
}
GATE_IM = {
    'H_left'  : QDYN.linalg.vectorize(GATE['H_left']).imag,
    'H_right' : QDYN.linalg.vectorize(GATE['H_right']).imag,
    'Ph_left' : QDYN.linalg.vectorize(GATE['Ph_left']).imag,
    'Ph_right': QDYN.linalg.vectorize(GATE['Ph_right']).imag,
    #'SWAP'    : QDYN.linalg.vectorize(GATE['SWAP']).imag
}


def get_stage3_runfolders(root, w2_wc, SQ, single_frequency=False):
    """Return a list of SQ or PE stage3 runfolders filtered down to only
    frequencies in w2_wc. If single_frequency is True, only include runfolder
    for which the guess pulses only had a single frequency originally.

    If SQ is True, return runfolder in which the target was the local gate.
    Otherwise, return runfolder in which the target was a PE
    """
    stage3_runfolders = []
    roots = []
    for (w2, wc) in w2_wc: # GHz
        w2_wc_folder = os.path.join(root,
                        'w2_%dMHz_wc_%dMHz' % (w2*1000, wc*1000))
        if os.path.isdir(w2_wc_folder):
            roots.append(w2_wc_folder)
    if SQ:
        subfolder_pattern = 'SQ*'
    else:
        subfolder_pattern = 'PE*'
    for root in roots:
        for folder in find_folders(root, 'stage3'):
            for subfolder in find_folders(folder, subfolder_pattern):
                if single_frequency:
                    if '1freq' in subfolder:
                        stage3_runfolders.append(subfolder)
                else:
                    stage3_runfolders.append(subfolder)
    return stage3_runfolders


def prepare_stage4(stage3_runfolder, SQ, stage_folder='stage4', dry_run=False):
    """Generate all stage4 runfolder based on the given stage3_runfolder.

    If SQ is True, stage3_runfolder must contain a config file that is
    appropriate for LI optimization for unity, and it must contain pulse.dat
    (result of stage3 optimization) which will be used as the guess pulse

    If SQ is False, stage3_runfolder must contain a config file that is
    appropritate for PE optimization. It must contain pulse.dat (result of
    stage3 optimization) and U_closest_PE.dat. The pulse will be be used as the
    guest pulse for a direct optimization (SM functional) towards the gate
    stored in U_closest_PE.dat.
    """
    logger = logging.getLogger(__name__)
    parts = stage3_runfolder.split(os.path.sep)
    assert parts[-2] == 'stage3', "stage3_runfolder must be contain 'stage3'" \
                                  "as penultimate folder"
    stage4_root = os.path.join(*(parts[:-2]+[stage_folder,]))
    logger.debug("Constructing runfolders based on stage 3 %s",
                 stage3_runfolder)
    pulse_dat = os.path.join(stage3_runfolder, "pulse.dat")
    pulse = QDYN.pulse.Pulse(pulse_dat)
    pulse.preamble = ['# guess pulse (copy of %s)' % pulse_dat,]
    config = read_file(os.path.join(stage3_runfolder, "config"))
    if SQ:
        targets = ['H_left', 'H_right', 'Ph_left', 'Ph_right']
    else:
        targets = ['PE']
    for target in targets:
        if target == 'PE':
            runfolder = os.path.join(stage4_root, "%s"%parts[-1])
        else:
            runfolder = os.path.join(stage4_root, "%s_%s"%(parts[-1], target))
        if os.path.isfile(os.path.join(runfolder, 'U.dat')):
            logger.debug("folder %s already contains a propagated OCT "
                         "result. Skipping", runfolder)
            continue
        if dry_run:
            logger.info("Generating %s", runfolder)
        else:
            QDYN.shutil.mkdir(runfolder)
            # guess pulse
            pulse.write(os.path.join(runfolder, 'pulse.guess'))
            # config: functional to SM, target to target_gate.dat
            write_file(os.path.join(runfolder, 'config'),
                       re.sub(r'iter_stop\s*=\s*\d+', r'iter_stop = 10000',
                       re.sub(r'max_hours\s*=\s*\d+', r'max_hours = 23',
                       re.sub(r'J_T_conv\s*=\s*[\de+-]+', r'J_T_conv = 1.0e-3',
                       re.sub(r'type\s*=\s*krotov2', r'type = krotovpk',
                       re.sub(r'gate\s*=\s*\w+', r'gate = target_gate.dat',
                       re.sub(r'J_T\s*=\s*\w+',  r'J_T = SM', config)))))))
            # target gate
            if SQ:
                writetotxt(os.path.join(runfolder, 'target_gate.dat'),
                        GATE_RE[target], GATE_IM[target])
            else:
                U_tgt = QDYN.gate2q.Gate2Q(file=os.path.join(
                            stage3_runfolder, "U_closest_PE.dat"))
                U_tgt_re = QDYN.linalg.vectorize(U_tgt).real
                U_tgt_im = QDYN.linalg.vectorize(U_tgt).imag
                writetotxt(os.path.join(runfolder, 'target_gate.dat'),
                        U_tgt_re, U_tgt_im)


def main(argv=None):
    """Main routine"""
    from optparse import OptionParser
    if argv is None:
        argv = sys.argv
    arg_parser = OptionParser(
    usage = "usage: %prog [options] RUNS",
    description = __doc__)
    arg_parser.add_option(
        '-n', action='store_true', dest='dry_run',
        default=False, help="Perform dry-run")
    arg_parser.add_option(
        '--debug', action='store_true', dest='debug',
        default=False, help="Enable debugging output")
    arg_parser.add_option(
        '--single-frequency', action='store_true', dest='single_frequency',
        default=False, help="Filter out all runs that use more than a single "
        "frequency")
    arg_parser.add_option(
        '--params-file', action='store', dest='params_file',
        help="File from which to read w2, wc tuples.")
    arg_parser.add_option(
        '--stage-folder', action='store', dest='stage_folder',
        default='stage4', help="Name of stage folder. Alternative stage "
        "folder names may be used to explore different OCT strategies")
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
    logger = logging.getLogger()
    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    w2_wc = None
    if options.params_file is None:
        arg_parser.error("--params-file must be given")
    else:
        w2_wc = read_w2_wc(options.params_file)
    for SQ in [True, False]:
        folders = get_stage3_runfolders(runs, w2_wc, SQ,
                                        options.single_frequency)
        for folder in folders:
            prepare_stage4(folder, SQ, stage_folder=options.stage_folder,
                           dry_run=options.dry_run)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
