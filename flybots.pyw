#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sys import version_info, stderr
if version_info.minor < 2:
    from flying_robots.compat import ArgumentParser
else:
    from argparse import ArgumentParser

from flying_robots.config import (
        get_config, apply_opts_to_conf, validate_conf,
        DEFAULT_UI
        )

parser = ArgumentParser()
parser.add_argument('-H', '--controls', dest='controls', action='store_true',
                    help='display game controls and exit')
parser.add_argument('-s', '--scores', dest='scores_only', action='store_true',
                    help='print high scores and exit')
parser.add_argument('-c', '--config', dest='conf_file',
                  help='provide a custom configuration file', metavar='FILE')
parser.add_argument('-l', '--level', dest='start_level',
                  help='start playing at the specified level', metavar='LEVEL')
parser.add_argument('-n', '--name', dest='name',
                  help='specify player name', metavar='NAME')
parser.add_argument('-x', dest='x', help='specify length on x-axis of grid',
                    metavar='N')
parser.add_argument('-y', dest='y', help='specify length on y-axis of grid',
                    metavar='N')
parser.add_argument('-z', dest='z', help='specify length on z-axis of grid',
                    metavar='N')
parser.add_argument('--curses', help='use the curses interface if on a system'
        ' that supports it', dest='ui', action='store_const', const='curses')
parser.add_argument('--tkinter', help='use the tkinter interface (default)',
        dest='ui', action='store_const', const='tkinter')

options = parser.parse_args()
if options.controls:
    from flying_robots.metadata import controls
    print(controls)
    exit(0)
if options.scores_only:
    from flying_robots.hs_handler import print_scores
    print_scores()

ui = options.ui or DEFAULT_UI
try:
    if ui == 'tkinter':
        from flying_robots.ui.tkinter_ui import start_interface
    else:
        from flying_robots.ui.curses_ui import start_interface
except ImportError:
    print('Could not import files necessary for the {} interface. '
            'Please ensure you have the necessary packages installed, '
            'or try specifying an alternative interface '
            '(use the --help flag for info on specifying an interface).'
            ''.format(ui),
            file=stderr)
    quit(1)

conf = get_config(options.conf_file)

# Each key in this dict is the name of the relevant attribute in the options
# object returned by parser.parse_args.
# Each value is a 3-tuple containing the name of the section in the config
# containing the option, the name of the option itself, and a boolean value
# indicating whether changing this option precludes the score from this game
# from being counted towards the high scores (True if it does).
optmap = {
    'name':         ('player', 'name', False),
    'start_level':  ('game', 'start_level', True),
    'x':            ('grid', 'x', True),
    'y':            ('grid', 'y', True),
    'z':            ('grid', 'z', True)
    }

apply_opts_to_conf(conf, options, optmap)
validate_conf(conf)
start_interface(conf)
