#!/usr/bin/env python
import os
import sys
from StringIO import StringIO
import QDYN
import QDYNTransmonLib
import numpy as np
import matplotlib
from collections import OrderedDict
matplotlib.use('Agg')
import matplotlib.pylab as plt
from notebook_utils import get_Q_table, diss_error, PlotGrid
from notebook_utils import (get_stage1_table, get_stage2_table,
        get_stage3_table, get_zeta_table)
from mgplottools.mpl import new_figure, set_axis, get_color, ls
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import pandas as pd

STYLE = 'paper.mplstyle'

get_stage3_table = QDYN.memoize.memoize(get_stage3_table)
get_stage3_table.load('stage3_table.cache')
get_zeta_table = QDYN.memoize.memoize(get_zeta_table)
get_zeta_table.load('zeta_table.cache')

OUTFOLDER = './paper_images'
#OUTFOLDER = '/Users/goerz/Documents/Papers/TransmonLandscape'


def generate_field_free_plot(zeta_table, T, outfile):
    """Plot field-free entangling energy zeta, and projected concurrence after
    the given gate duration T in ns.
    """
    plots = PlotGrid(layout='paper')
    # parameters matching those in generate_map_plot
    plots.cell_width      =  5.986667
    plots.cell_height     =  4.6 # top + bottom + h from generate_map_plot
    #plots.left_margin     =  1.2 # set dynamically below
    plots.bottom_margin   =  0.8
    plots.h               =  3.6
    plots.w               =  3.6
    plots.cbar_width      =  0.25
    plots.cbar_gap        =  0.6
    plots.density         =  300
    plots.n_cols          =  3
    plots.contour_labels  = False
    plots.cbar_title      = True
    plots.ylabelpad       = -1.0
    plots.xlabelpad       =  0.5
    plots.clabelpad       =  4.0
    plots.scatter_size    =  0.0
    plots.x_major_ticks   = 0.5
    plots.x_minor         = 5
    plots.y_major_ticks   = 1.0
    plots.y_minor         = 5
    plots.draw_cell_box   = False

    plots.labels = [
    #          w_2   w_c     label pos
        ("A", (6.32, 5.75), (6.4, 5.2), 'grey'),
        ("B", (5.9,  6.2),  (5.95, 6.45), 'grey')
    ]

    zeta = zeta_table['zeta [MHz]']
    abs_zeta = np.clip(np.abs(zeta), a_min=1e-5, a_max=1e5)
    w2 = zeta_table['w2 [GHz]']
    wc = zeta_table['wc [GHz]']

    plots.add_cell(w2, wc, abs_zeta, title=r'$\zeta$~(MHz)', logscale=True,
                   vmin=1e-3, left_margin=1.1, y_labels=True)

    T_entangling = 500.0/abs_zeta
    plots.add_cell(w2, wc, T_entangling, logscale=True, vmax=1e3,
                    #vmin=0.0, vmax=100.0,
                   title=r'$T(\gamma=\pi)$ (ns)', left_margin=1.09,
                   y_labels=False)

    gamma_bare = 0.012
    rel_decay = zeta_table['gamma [MHz]'] / gamma_bare
    print("Min: %s" % np.min(rel_decay))
    print("Max: %s" % np.max(rel_decay))
    plots.add_cell(w2, wc, rel_decay, logscale=False, vmin=1, vmax=2.3,
                   title=r'$\gamma_{\text{dressed}} / \gamma_{\text{bare}}$',
                   left_margin=0.85, y_labels=False, cmap=plt.cm.cubehelix_r)

    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)

    fig = plots.plot(quiet=False, show=False, style=STYLE)

    fig.savefig(outfile)
    print("written %s" % outfile)
    plt.close(fig)


@FuncFormatter
def weyl_x_tick_fmt(x, pos):
    'The two args are the value and tick position'
    if x == 0:
        return '0'
    elif x == 1:
        return '1'
    else:
        return ''
        #return ("%.1f" % x)[1:]

@FuncFormatter
def weyl_y_tick_fmt(y, pos):
    'The two args are the value and tick position'
    if y == 0:
        return '0'
    elif y == 0.5:
        return '0.5'
    else:
        return ''


@FuncFormatter
def weyl_z_tick_fmt(z, pos):
    'The two args are the value and tick position'
    if z == 0.5:
        return '0.5'
    else:
        return ''


def generate_map_plot_SQ(stage_table_200, stage_table_050, stage_table_010,
        zeta_table, outfile):

    # axes:
    # * 200
    # * 50
    # * 10

    # vertical layout parameters
    top = 0.2     # top of figure to T=200 axes
    bottom = 0.8  # bottom of figure to T=010 axes
    gap = 0.4     # vertical gap between axes
    h = 3.6       # height of all axes
    cell_height = ((bottom + top + 2*gap) / 3.0) + h # 4.2
    bottom_margin = { # within each cell
         10: bottom,
         50: (bottom + h + gap) - cell_height,
        200: (bottom + 2*(h+gap)) - 2*cell_height,
    }

    # set up map plot
    map_plots = PlotGrid(layout='paper')
    map_plots.cell_width      =  5.75
    map_plots.cell_height     =  cell_height
    #map_plots.left_margin     =  1.2 # set dynamically below
    #map_plots.bottom_margin   =  1.0 # set dynamically below
    map_plots.h               =  h
    map_plots.w               =  3.6
    map_plots.cbar_width      =  0.25
    map_plots.cbar_gap        =  0.6
    map_plots.density         =  300
    map_plots.n_cols          =  3
    map_plots.contour_labels  = False
    map_plots.cbar_title      = True
    map_plots.ylabelpad       = -1.0
    map_plots.xlabelpad       =  0.5
    map_plots.clabelpad       =  4.0
    map_plots.scatter_size    =  0.0
    map_plots.x_major_ticks   = 0.5
    map_plots.x_minor         = 5
    map_plots.y_major_ticks   = 1.0
    map_plots.y_minor         = 5
    map_plots.draw_cell_box   = False

    weyl_label_offset = {
         10: bottom + h - 0.25,
         50: cell_height + bottom_margin[50] + h - 0.25,
        200: 2*cell_height + bottom_margin[200] + h -  0.25,
    }
    weyl_fig_height = 3 * cell_height


    map_plots.labels = [
        ("A", (6.32, 5.75), (6.4, 5.2), 'grey'),
        ("B", (5.9,  6.2),  (5.95, 6.45), 'grey')
    ]

    data = OrderedDict([
            (200, stage_table_200),
            (50,  stage_table_050),
            (10,  stage_table_010), ])

    for T in data.keys():

        stage_table = data[T]
        min_err = diss_error(gamma=1.2e-5, t=T)

        # filter stage table to single frequencies
        stage_table = stage_table[stage_table['category'].str.contains('1freq')]

        # get optimized concurrence table
        (__, t_PE), (__, t_SQ) = stage_table.groupby('target', sort=True)
        C_opt_table = t_SQ\
                .groupby(['w1 [GHz]', 'w2 [GHz]', 'wc [GHz]'], as_index=False)\
                .apply(lambda df: df.sort('J_PE').head(1))\
                .reset_index(level=0, drop=True)

        zeta = zeta_table['zeta [MHz]']
        gamma = -2.0 * np.pi * (zeta/1000.0) * T # entangling phase
        C_ff = np.abs(np.sin(0.5*gamma))

        # table of zetas at the same data points as C_opt_table
        ind = ['w1 [GHz]', 'w2 [GHz]', 'wc [GHz]']
        zeta_table2 = pd.merge(C_opt_table[ind+['C', 'max loss']],
                              zeta_table[ind+['zeta [MHz]']],
                              on=ind, how='left').dropna()
        zeta2 = zeta_table2['zeta [MHz]']
        gamma2 = -2.0 * np.pi * (zeta2/1000.0) * T # entangling phase
        C_ff2 = np.abs(np.sin(0.5*gamma2))

        # plot the maps
        map_x_labels = False
        if T == 10:
            map_x_labels = True

        map_plots.add_cell(zeta_table['w2 [GHz]'], zeta_table['wc [GHz]'],
                    1-C_ff, vmin=0.0, vmax=1.0,
                    contour_levels=0, logscale=False, title=r'$1-C_0$ (field-free)',
                    left_margin=1.1, bottom_margin=bottom_margin[T],
                    x_labels=map_x_labels, y_labels=True)
        map_plots.add_cell(C_opt_table['w2 [GHz]'], C_opt_table['wc [GHz]'],
                    1-C_opt_table['C'], vmin=0.0, vmax=1.0,
                    val_alpha=(1-C_opt_table['max loss']), bg='black',
                    contour_levels=0, logscale=False, title=r'$1-C_{\text{SQ}}$ (opt)',
                    left_margin=0.9, bottom_margin=bottom_margin[T],
                    x_labels=map_x_labels, y_labels=False)
        map_plots.add_cell(zeta_table2['w2 [GHz]'], zeta_table2['wc [GHz]'],
                    -zeta_table2['C']+C_ff2, vmin=0.0, vmax=1.0,
                    val_alpha=(1-zeta_table2['max loss']), bg='black',
                    contour_levels=0, logscale=False, title=r'$C_{0} - C_{\text{SQ}}$',
                    left_margin=0.7, bottom_margin=bottom_margin[T],
                    x_labels=map_x_labels, y_labels=False)

    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)

    fig_maps = map_plots.plot(quiet=False, show=False, style=STYLE)
    fig_width = map_plots.n_cols * map_plots.cell_width
    for T in [10, 50, 200]:
        fig_maps.text((1.1+0.5*map_plots.w)/fig_width,
                      weyl_label_offset[T]/weyl_fig_height,
                      r'$T = %d$~ns' % T, verticalalignment='top',
                      horizontalalignment='center', size=10)
    fig_maps.savefig(outfile)
    print("written %s" % outfile)
    plt.close(fig_maps)


def generate_map_plot_PE(stage_table_200, stage_table_050, stage_table_010,
        zeta_table, outfile):

    # axes:
    # * 200
    # * 50
    # * 10

    # vertical layout parameters
    top = 0.2     # top of figure to T=200 axes
    bottom = 0.8  # bottom of figure to T=010 axes
    gap = 0.4     # vertical gap between axes
    h = 3.6       # height of all axes
    cell_height = ((bottom + top + 2*gap) / 3.0) + h # 4.2
    bottom_margin = { # within each cell
         10: bottom,
         50: (bottom + h + gap) - cell_height,
        200: (bottom + 2*(h+gap)) - 2*cell_height,
    }

    # set up map plot
    map_plots = PlotGrid(layout='paper')
    map_plots.cell_width      =  5.85
    map_plots.cell_height     =  cell_height
    #map_plots.left_margin     =  1.2 # set dynamically below
    #map_plots.bottom_margin   =  1.0 # set dynamically below
    map_plots.h               =  h
    map_plots.w               =  3.6
    map_plots.cbar_width      =  0.25
    map_plots.cbar_gap        =  0.6
    map_plots.density         =  300
    map_plots.n_cols          =  2
    map_plots.contour_labels  = False
    map_plots.cbar_title      = True
    map_plots.ylabelpad       = -1.0
    map_plots.xlabelpad       =  0.5
    map_plots.clabelpad       =  4.0
    map_plots.scatter_size    =  0.0
    map_plots.x_major_ticks   = 0.5
    map_plots.x_minor         = 5
    map_plots.y_major_ticks   = 1.0
    map_plots.y_minor         = 5
    map_plots.draw_cell_box   = False

    map_plots.labels = [
        ("A", (6.32, 5.75), (6.4, 5.2), 'grey'),
        ("B", (5.9,  6.2),  (5.95, 6.45), 'grey')
    ]

    data = OrderedDict([
            (200, stage_table_200),
            (50,  stage_table_050),
            (10,  stage_table_010), ])

    for T in data.keys():

        stage_table = data[T]
        min_err = diss_error(gamma=1.2e-5, t=T)

        # filter stage table to single frequencies
        stage_table = stage_table[stage_table['category'].str.contains('1freq')]

        # get optimized concurrence table
        (__, t_PE), (__, t_SQ) = stage_table.groupby('target', sort=True)
        C_opt_table = t_PE\
                .groupby(['w1 [GHz]', 'w2 [GHz]', 'wc [GHz]'], as_index=False)\
                .apply(lambda df: df.sort('J_PE').head(1))\
                .reset_index(level=0, drop=True)

        # table of zetas at the same data points as C_opt_table
        ind = ['w1 [GHz]', 'w2 [GHz]', 'wc [GHz]']
        zeta_table2 = pd.merge(C_opt_table[ind+['C', 'max loss']],
                              zeta_table[ind+['zeta [MHz]']],
                              on=ind, how='left').dropna()
        zeta = zeta_table2['zeta [MHz]']
        gamma = -2.0 * np.pi * (zeta/1000.0) * T # entangling phase
        C_ff = np.abs(np.sin(0.5*gamma))

        # plot the maps
        map_x_labels = False
        if T == 10:
            map_x_labels = True

        map_plots.add_cell(C_opt_table['w2 [GHz]'], C_opt_table['wc [GHz]'],
                    C_opt_table['C'], vmin=0.0, vmax=1.0,
                    val_alpha=(1-C_opt_table['max loss']), bg='black',
                    contour_levels=0, logscale=False, title=r'$C_{\text{PE}}$ (opt)',
                    left_margin=1.1, bottom_margin=bottom_margin[T],
                    x_labels=map_x_labels, y_labels=True)
        map_plots.add_cell(zeta_table2['w2 [GHz]'], zeta_table2['wc [GHz]'],
                    zeta_table2['C']-C_ff, vmin=0.0, vmax=1.0,
                    val_alpha=(1-zeta_table2['max loss']), bg='black',
                    contour_levels=0, logscale=False, title=r'$C_{\text{PE}} - C_0$',
                    left_margin=0.8, bottom_margin=bottom_margin[T],
                    x_labels=map_x_labels, y_labels=False)

    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)

    out_path, out_filename = os.path.split(outfile)

    fig_maps = map_plots.plot(quiet=False, show=False, style=STYLE)
    fig_maps.savefig(outfile)
    print("written %s" % outfile)
    plt.close(fig_maps)



def generate_map_plot_weyl(stage_table_200, stage_table_050, stage_table_010,
        outfile):

    # axes:
    # * 200
    # * 50
    # * 10

    # vertical layout parameters (see PE plot)
    top = 0.2     # top of figure to T=200 axes
    bottom = 0.8  # bottom of figure to T=010 axes
    gap = 0.4     # vertical gap between axes
    h = 3.6       # height of all axes
    cell_height = ((bottom + top + 2*gap) / 3.0) + h # 4.2
    bottom_margin = { # within each cell
         10: bottom,
         50: (bottom + h + gap) - cell_height,
        200: (bottom + 2*(h+gap)) - 2*cell_height,
    }

    weyl_bottom_offset = {
         10: bottom,
         50: cell_height + bottom_margin[50],
        200: 2*cell_height + bottom_margin[200],
    }

    weyl_label_offset = {
         10: bottom + h - 0.25,
         50: cell_height + bottom_margin[50] + h - 0.25,
        200: 2*cell_height + bottom_margin[200] + h -  0.25,
    }

    # set up Weyl plot
    weyl_fig_width = 4.35
    weyl_fig_height = 3 * cell_height
    fig_weyl = new_figure(weyl_fig_width, weyl_fig_height, style=STYLE)
    weyl_left_margin = 0.3
    weyl_w = 3.8
    weyl_h = 3.2
    ax_weyl = {}

    data = OrderedDict([
            (200, stage_table_200),
            (50,  stage_table_050),
            (10,  stage_table_010), ])

    for T in data.keys():

        stage_table = data[T]
        min_err = diss_error(gamma=1.2e-5, t=T)

        # filter stage table to single frequencies
        stage_table = stage_table[stage_table['category'].str.contains('1freq')]

        (__, t_PE), (__, t_SQ) = stage_table.groupby('target', sort=True)

        # plot the weyl_chamber
        pos_weyl = [weyl_left_margin/weyl_fig_width,
                    (weyl_bottom_offset[T])/weyl_fig_height,
                    weyl_w/weyl_fig_width, weyl_h/weyl_fig_height]
        ax_weyl = fig_weyl.add_axes(pos_weyl, projection='3d')
        w = QDYN.weyl.WeylChamber()
        t_PE_weyl = t_PE[(t_PE['max loss']<0.1) & (t_PE['C']==1.0)]
        w.scatter(t_PE_weyl['c1'], t_PE_weyl['c2'], t_PE_weyl['c3'],
                  s=5, linewidth=0)
        w.render(ax_weyl)
        ax_weyl.xaxis._axinfo['ticklabel']['space_factor'] = 1.0
        ax_weyl.yaxis._axinfo['ticklabel']['space_factor'] = 1.0
        ax_weyl.zaxis._axinfo['ticklabel']['space_factor'] = 1.3
        ax_weyl.xaxis._axinfo['label']['space_factor'] = 1.5
        ax_weyl.yaxis._axinfo['label']['space_factor'] = 1.5
        ax_weyl.zaxis._axinfo['label']['space_factor'] = 1.5
        ax_weyl.xaxis.set_major_formatter(weyl_x_tick_fmt)
        ax_weyl.yaxis.set_major_formatter(weyl_y_tick_fmt)
        ax_weyl.zaxis.set_major_formatter(weyl_z_tick_fmt)
        fig_weyl.text(0.5, weyl_label_offset[T]/weyl_fig_height,
                      r'$T = %d$~ns' % T, verticalalignment='top',
                      horizontalalignment='center', size=10)

    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)

    fig_weyl.savefig(outfile)
    print("written %s" % outfile)
    plt.close(fig_weyl)


def generate_popdyn_plot(outfile):
    dyn = QDYNTransmonLib.popdyn.PopPlot(
          "./propagate/010_RWA_w2_6000MHz_wc_6300MHz_stage3/PE_1freq/",
          panel_width=3.5, left_margin=1.5, right_margin=3.0, top_margin=0.7)
    dyn.styles['tot']['ls'] = '--'
    dyn.plot(pops=('00', '01', '10', '11', 'tot'), in_panel_legend=False)
    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)
    plt.savefig(outfile)
    print("written %s" % outfile)


def generate_error_plot(outfile):

    fig_height      = 4.0
    fig_width       = 8.5               # Total canvas (cv) width
    left_margin     = 1.2               # Left cv -> plot area
    right_margin    = 0.2               # plot area -> right cv
    top_margin      = 0.25              # top cv -> plot area
    bottom_margin   = 0.6
    h = fig_height - (bottom_margin + top_margin)
    w = fig_width  - (left_margin + right_margin)
    data = r'''
    #                   minimum error  achieved PE error
    # gate duration [ns]
    5                        3.77e-04           1.54e-03
    10                       7.54e-04           8.84e-04
    20                       1.51e-03           1.56e-03
    50                       3.76e-03           3.87e-03
    100                      7.51e-03           7.59e-03
    200                      1.49e-02           1.50e-02
    '''
    T, eps_0, eps_PE = np.genfromtxt(StringIO(data), unpack=True)
    fig = new_figure(fig_width, fig_height, style=STYLE)
    pos = [left_margin/fig_width, bottom_margin/fig_height,
           w/fig_width, h/fig_height]
    ax = fig.add_axes(pos)
    ax.plot(T, eps_0, label=r'$\varepsilon_{\text{avg}}^0$', marker='o', ls='dotted')
    ax.plot(T, eps_PE, label=r'$\varepsilon_{\text{avg}}^{\text{PE}}$', marker='o', ls='dashed')
    ax.legend(loc='lower right')
    ax.annotate('QSL', xy=(10, 1e-3),  xycoords='data',
                xytext=(10, 1e-2), textcoords='data',
                arrowprops=dict(facecolor='black', width=1, headwidth=3, shrink=0.05),
                horizontalalignment='center', verticalalignment='top',
                )
    set_axis(ax, 'x', 4, 210, label='gate time (ns)', logscale=True, labelpad=-2)
    set_axis(ax, 'y', 1e-4, 1.0e-1, label='lowest gate error', logscale=True)
    ax.tick_params(axis='x', pad=3)

    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)
    fig.savefig(outfile, format=os.path.splitext(outfile)[1][1:])
    print("written %s" % outfile)


def generate_universal_pulse_plot(universal_rf, outfile):
    fig_width    = 18.0
    fig_height   = 11.0
    spec_offset  =  1.0
    phase_offset =  3.5 # PHASE
    phase_deriv_offset =  6.0 # PHASE
    pulse_offset = 8.5
    phase_h       =  1.5 # PHASE
    phase_deriv_h =  1.5 # PHASE
    label_offset = 10.75
    spec_h       =  1.5
    pulse_h      =  1.5
    left_margin  =  1.2
    right_margin =  0.25
    gap          =  0.5 # horizontal gap between panels

    fig = new_figure(fig_width, fig_height, style=STYLE)

    w = float(fig_width - (left_margin + right_margin + 4 * gap)) / 5

    labels = {
            'H_L': r'Hadamard (left)',
            'H_R': r'Hadamard (right)',
            'S_L': r'Phasegate (left)',
            'S_R': r'Phasegate (right)',
            'PE': r'BGATE',
    }

    for i_tgt, tgt in enumerate(['H_L', 'H_R', 'S_L', 'S_R', 'PE']):

        left_offset = left_margin + i_tgt * (w+gap)

        p = QDYN.pulse.Pulse(os.path.join(universal_rf[tgt], 'pulse.dat'),
                             freq_unit='MHz')
        freq, spectrum = p.spectrum(mode='abs', sort=True)
        spectrum *= 1.0 / len(spectrum)

        # column labels
        fig.text((left_offset + 0.5*w)/fig_width, label_offset/fig_height,
                  labels[tgt], verticalalignment='top',
                  horizontalalignment='center', size=10)

        # spectrum
        pos = [left_offset/fig_width, spec_offset/fig_height,
               w/fig_width, spec_h/fig_height]
        ax_spec = fig.add_axes(pos)
        ax_spec.plot(freq/100.0, 1.1*spectrum, label='spectrum')
        set_axis(ax_spec, 'x', -10, 10, range=(-6, 6), step=5, minor=5,
                 label='frequency (100 MHz)', labelpad=1)
        w1 = 5.9823 # GHz
        w2 = 5.8824 # GHz
        wd = 5.9325 # GHz
        ax_spec.axvline(x=10*(w2-wd), ls='--', color=get_color('green'))
        ax_spec.axvline(x=10*(w1-wd), ls='--', color=get_color('orange'))
        ax_spec.text(x=10*(w2-wd)-0.5, y=90, s=r'$\omega_2^d$',
                     ha='right', va='top', color=get_color('green'))
        ax_spec.text(x=10*(w1-wd)+0.5, y=90, s=r'$\omega_1^d$',
                     ha='left', va='top', color=get_color('orange'))
        if i_tgt == 0:
            set_axis(ax_spec, 'y', 0, 100, step=50, minor=5,
                    label=r'abs(spect) (arb. un.)')
        else:
            set_axis(ax_spec, 'y', 0, 100, step=50, minor=5, label='',
                     ticklabels=False)
        ##### PHASE ######
        pos = [left_offset/fig_width, phase_offset/fig_height,
               w/fig_width, phase_h/fig_height]
        ax_phase = fig.add_axes(pos)
        ax_phase.plot(p.tgrid, p.phase(unwrap=True) / np.pi)
        ax_phase.plot(p.tgrid, p.phase(unwrap=True, s=1000) / np.pi, dashes=ls['dotted'], color='grey')
        set_axis(ax_phase, 'x', 0, 50, step=10, minor=2, label='time (ns)',
                 labelpad=1)
        if i_tgt == 0:
            set_axis(ax_phase, 'y', -20, 20, range=(-14.9, 4.9), step=5, minor=5,
                    label=r'$\phi$ ($\pi$)')
        else:
            set_axis(ax_phase, 'y', -20, 20, range=(-14.9, 4.9), step=5, minor=5,
                     label='', ticklabels=False)

        pos = [left_offset/fig_width, phase_deriv_offset/fig_height,
               w/fig_width, phase_deriv_h/fig_height]
        ax_phase_deriv = fig.add_axes(pos)
        ax_phase_deriv.plot(p.tgrid, p.phase(unwrap=True, s=1000, derivative=True)/100)
        set_axis(ax_phase_deriv, 'x', 0, 50, step=10, minor=2, label='time (ns)',
                 labelpad=1)
        if i_tgt == 0:
            set_axis(ax_phase_deriv, 'y', -5, 5, range=(-4, 2), step=2, minor=5,
                    label=r'$d\phi/dt$ (100 MHz)')
        else:
            set_axis(ax_phase_deriv, 'y', -5, 5, range=(-4, 2), step=2, minor=5,
                     label='', ticklabels=False)
        ax_phase_deriv.axhline(y=10*(w2-wd), ls='--', color=get_color('green'))
        ax_phase_deriv.axhline(y=10*(w1-wd), ls='--', color=get_color('orange'))
        ##### PHASE ######

        # pulse
        pos = [left_offset/fig_width, pulse_offset/fig_height,
               w/fig_width, pulse_h/fig_height]
        ax_pulse = fig.add_axes(pos)
        p.render_pulse(ax_pulse)
        set_axis(ax_pulse, 'x', 0, 50, step=10, minor=2, label='time (ns)',
                 labelpad=1)
        if i_tgt == 0:
            set_axis(ax_pulse, 'y', 0, 300, step=100, minor=5,
                    label=r'abs(pulse) (MHz)')
        else:
            set_axis(ax_pulse, 'y', 0, 300, step=100, minor=5, label='',
                     ticklabels=False)

    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)
    fig.savefig(outfile, format=os.path.splitext(outfile)[1][1:])
    print("written %s" % outfile)


def generate_universal_popdyn_plot(universal_rf, outfile):
    fig_width           = 18.0
    legend_offset       = 10.5
    state_label_offset  = 10.0
    target_label_offset = 0.05
    left_margin         = 1.2
    right_margin        = 0.25
    bottom_margin       = 0.75
    top_margin          = 1.0
    h = 1.8

    w = float(fig_width - (left_margin + right_margin))/4
    fig_height = bottom_margin + top_margin + 5*h

    fig = new_figure(fig_width, fig_height, style=STYLE)

    for i_tgt, tgt in enumerate(['PE', 'S_R', 'S_L', 'H_R', 'H_L']):

        bottom_offset = bottom_margin + i_tgt*h

        dyn = QDYNTransmonLib.popdyn.PopPlot(universal_rf[tgt])

        for i_state, basis_state in enumerate(['00', '01', '10', '11']):

            left_offset = left_margin + i_state*w
            pos = [left_offset/fig_width, bottom_offset/fig_height,
                   w/fig_width, h/fig_height]
            ax_pop = fig.add_axes(pos)

            legend_lines = []
            p00, = ax_pop.plot(dyn.tgrid, dyn.pop[basis_state].pop00,
                              **dyn.styles['00'])
            p01, = ax_pop.plot(dyn.tgrid, dyn.pop[basis_state].pop01,
                              **dyn.styles['01'])
            p10, = ax_pop.plot(dyn.tgrid, dyn.pop[basis_state].pop10,
                              **dyn.styles['10'])
            p11, = ax_pop.plot(dyn.tgrid, dyn.pop[basis_state].pop11,
                              **dyn.styles['11'])
            pop_sum =   dyn.pop[basis_state].pop00 \
                      + dyn.pop[basis_state].pop10 \
                      + dyn.pop[basis_state].pop01 \
                      + dyn.pop[basis_state].pop11
            tot, = ax_pop.plot(dyn.tgrid, pop_sum, **dyn.styles['tot'])
            for line in (p00, p01, p10, p11, tot):
                legend_lines.append(line)

            if i_tgt == 0:
                if i_state < 3:
                    set_axis(ax_pop, 'x', 0, 50, step=10, minor=2, label='time (ns)',
                            labelpad=1, drop_ticklabels=[-1, ])
                else:
                    set_axis(ax_pop, 'x', 0, 50, step=10, minor=2, label='time (ns)',
                            labelpad=1)
            else:
                set_axis(ax_pop, 'x', 0, 50, step=10, minor=2,
                        label='', ticklabels=False)
            if i_state == 0:
                if i_tgt < 4:
                    set_axis(ax_pop, 'y', 0, 1, step=0.5, minor=5, label='population',
                            labelpad=1, drop_ticklabels=[-1, ])
                else:
                    set_axis(ax_pop, 'y', 0, 1, step=0.5, minor=5, label='population',
                            labelpad=1)
            else:
                set_axis(ax_pop, 'y', 0, 1, step=0.5, minor=5,
                        label='', ticklabels=False)

    fig.legend(legend_lines,
        ('00', '01', '10', '11', 'total logical subspace'),
        bbox_to_anchor=[(left_margin+2*w)/fig_width, legend_offset/fig_height],
        loc='center', ncol=5)

    state_labels = {
            '00': r'$\ket{\Psi(t=0)}=\ket{00}$',
            '01': r'$\ket{\Psi(t=0)}=\ket{01}$',
            '10': r'$\ket{\Psi(t=0)}=\ket{10}$',
            '11': r'$\ket{\Psi(t=0)}=\ket{11}$'
    }
    for i_state, basis_state in enumerate(['00', '01', '10', '11']):
        fig.text((left_margin + (i_state+0.5)*w)/fig_width,
                  state_label_offset/fig_height, state_labels[basis_state],
                  va='center', ha='center')

    target_labels = {
            'PE': r'BGATE',
            'S_R': r'Phasegate(2)',
            'S_L': r'Phasegate(1)',
            'H_R': r'Hadamard(2)',
            'H_L': r'Hadamard(1)'
    }
    for i_tgt, tgt in enumerate(['PE', 'S_R', 'S_L', 'H_R', 'H_L']):
        fig.text(target_label_offset/fig_width,
                 (bottom_margin + (i_tgt+0.5)*h)/fig_height,
                 target_labels[tgt],
                 rotation='vertical', va='center', ha='left')

    if OUTFOLDER is not None:
        outfile = os.path.join(OUTFOLDER, outfile)
    fig.savefig(outfile, format=os.path.splitext(outfile)[1][1:])
    print("written %s" % outfile)

def main(argv=None):

    if argv is None:
        argv = sys.argv
    if not os.path.isdir(OUTFOLDER):
        QDYN.shutil.mkdir(OUTFOLDER)

    stage_table_200 = get_stage3_table('./runs_200_RWA')
    stage_table_050 = get_stage3_table('./runs_020_RWA')
    stage_table_010 = get_stage3_table('./runs_010_RWA')
    zeta_table = get_zeta_table('./runs_050_RWA', T=50)


    universal_root = './runs_zeta_detailed/w2_5900MHz_wc_6200MHz'
    universal_rf = {
        'H_L': universal_root+'/50ns_w_center_H_left',
        'H_R': universal_root+'/50ns_w_center_H_right',
        'S_L': universal_root+'/50ns_w_center_Ph_left',
        'S_R': universal_root+'/50ns_w_center_Ph_right',
        'PE':  universal_root+'/PE_LI_BGATE_50ns_cont_SM'
    }

    # Fig 1
    generate_field_free_plot(zeta_table, T=50, outfile='fig1.pdf')

    # Fig 2
    generate_map_plot_SQ(stage_table_200, stage_table_050, stage_table_010,
                      zeta_table, outfile='fig2_top.pdf')
    generate_map_plot_PE(stage_table_200, stage_table_050, stage_table_010,
                      zeta_table, outfile='fig2_bottom_right.pdf')
    generate_map_plot_weyl(stage_table_200, stage_table_050, stage_table_010,
                      outfile='fig2_bottom_left.pdf')
    # Fig 3
    generate_error_plot(outfile='fig3.pdf')
    # Fig 4
    generate_universal_pulse_plot(universal_rf, outfile='fig4.pdf')
    # Fig 5
    generate_universal_popdyn_plot(universal_rf, outfile='fig5.pdf')


if __name__ == "__main__":
    sys.exit(main())
