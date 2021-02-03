#!/usr/bin/env python3
import os
import argparse
import globs

# add top directory to sys.path
import sys
sys.path.append(globs.TOPDIR)

NAME = 'AutoSequence'
VERSION = '0.1.0'
AUTHOR = "Ming Li(adagio.ming@gmail.com)."

# feed command line arguments
parser = argparse.ArgumentParser(prog=NAME,
                                 description='Sequence design based test automation tool.',
                                 add_help=False)
parser.add_argument('-v', '--version', action='version', version=' %(prog)s ' + VERSION,
                    help='Print %(prog)s version information and exit.')

parser.add_argument('-f', metavar='Sequence file', nargs='?', default='',
                    dest='main_sequence_file', help='Specify the main sequence file to start test.')

parser.add_argument('-l', metavar='Loop iterations', nargs='?',
                    default=1, type=int, dest='loops',
                    help='Specify loop iterations for the main sequence file specified by -l option.')

parser.add_argument('-S', '--stop-on-failure', dest='stop_on_failure',
                    action='store_true', help='Stop the test when failure occurs.')

parser.add_argument('-L', '--enable-logging', dest='logging_enabled',
                    action='store_true', help='Enable file logging.')

parser.add_argument('-D', '--debug-mode', dest='debug_mode_on',
                    action='store_true', help='Enable debug mode.')

parser.add_argument('-h', '--help', action='help',
                    help='Show this help information and exit.')


options = parser.parse_args()
globs.MAIN_SEQUENCE_FILE = options.main_sequence_file
globs.LOGGING_ENABLED = options.logging_enabled
globs.STOP_ON_FAILURE = options.stop_on_failure
globs.LOOP_ITERATIONS = options.loops
globs.DEBUG_MODE_ON = options.debug_mode_on

# check folders
if not os.path.isdir('./test_sequences'): os.mkdir('./test_sequences')
if not os.path.isdir('./log'): os.mkdir('./log')
if not os.path.isdir('./log/failure'): os.mkdir('./log/failure')
if not os.path.isdir('./log/errordump'): os.mkdir('./log/errordump')
if not os.path.isdir('./csvdump'): os.mkdir('./csvdump')


from worker import start_master
from worker import run_sequence_worker

if __name__ == '__main__':
    # Display tool information before launching
    print('\n%s, Version: %s' %(NAME, VERSION))
    print('UCS Server Testing Automation Tool.')
    print('Author: ' + AUTHOR)
    if globs.DEBUG_MODE_ON: # no window refreshing
        run_sequence_worker(globs.MAIN_SEQUENCE_FILE, globs.LOOP_ITERATIONS)
    else:
        start_master(globs.MAIN_SEQUENCE_FILE, globs.LOOP_ITERATIONS)
