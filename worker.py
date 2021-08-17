import sys
import os
import time
import datetime
from multiprocessing import Value

from agent import AgentWrapper
from globs import *
from errors import *
import utils
from uds import (get_this_uds,
                 MESSAGES as MSGS)
from sequence import SequenceReader
import cursor


THIS_WORKER = None
WIN_DISPLAY_EN = None
WIN_REFRESH_INTERVAL = 5.0
MAX_SEQUENCE_WORKER = 5                     # maxi + mum worker processes


class SequenceWorker(object):
    """Sequence agent worker class to run sequences, one worker corresponds
    to a specific sequence, parsed from given sequence file."""

    def __init__(self, sequence_file, loops=1):
        self.seq_file = sequence_file   # sequence file
        if LOG_ENABLED:
            logfile = utils.new_log_path(sequence_file.split(os.sep)[-1])
            self.logfile = open(logfile, mode='w')  # logging file handler
        else:
            self.logfile = None
        self.errordump = None           # error obj dumped to errordump file when worker stops unexpectly
        self.errordumpfile = None       # errordump file handler to record errordump obj
        self.seq_loops = loops          # loop count that we run the sequence
        self.loop_failures = []         # failure info queue for current test loop
        self.uds = get_this_uds()       # unix domain socket for ipc to master
        self.agent = AgentWrapper(logfile=self.logfile)
        # read sequence file, to get the sequence of commands
        try:
            seqreader = SequenceReader(sequence_file)
            seqreader.parse_lines()
            self.sequence = seqreader.sequence
            self.subsequences = seqreader.subsequences
        except Exception as error:
            global WIN_DISPLAY_EN
            if WIN_DISPLAY_EN is not None:
                WIN_DISPLAY_EN.value = 0
            self.logging_error(error)
            raise error
        # running arguments that we really use
        self.running_sequence = self.sequence   # running sequence, by default the whole sequence
        self.running_loops = self.seq_loops     # running sequence loops
        self.cmplt_running_loops = 0            # how many loops that has completed
        self.running_command = 0                # running command running sequence

        self.spawned_workers = []               # workers spawned by current worker


    def logging_error(self, errorinfo):
        if not self.errordumpfile:
            error_header = '******ERROR DUMP MESSAGE******\n\n'
            error_title = 'TEST SEQUENCE: %s\n\n' %(self.seq_file)
            errordumpfile = utils.new_log_path(sequence=self.seq_file.split(os.sep)[-1], suffix='errordump')
            self.errordumpfile = open(errordumpfile, mode='w')
            self.errordumpfile.write(error_header + error_title)
            self.errordumpfile.flush()

        if self.errordumpfile and not self.errordumpfile.closed:
            if not isinstance(errorinfo, str): errorinfo = repr(errorinfo)
            self.errordumpfile.write(errorinfo)
            self.errordumpfile.flush()

    def stop(self):
        # send SEQUENCE COMPLETE message to master
        msg = {
            'MSG': MSGS.worker_run_cmplt.value,
            'NAME': self.seq_file.split('.')[0],
            }
        self.uds.send_server_msg(msg)
        # logging error dump object
        if self.errordump:
            errinfo = '\nDUMP ERROR INFO:\n' + repr(self.errordump) + '\n'
            ttyinfo = 'AGENT INFO:\n' + repr(self.agent) + '\n'
            self.logging_error(errinfo + '\n' + ttyinfo + '\n')
            self.errordump = None
        # close worker agent
        if self.agent:
            self.agent.close_on_exception()
            self.agent = None
        # flush worker logfile stream
        if self.logfile and not self.logfile.closed:
            self.logfile.flush()
            self.logfile.close()
            self.logfile = None
        # flush worker error dump file stream
        if self.errordumpfile and not self.errordumpfile.closed:
            self.errordumpfile.flush()
            self.errordumpfile.close()
            self.errordumpfile = None
        # update global
        global THIS_WORKER
        THIS_WORKER = None

    def format_errinfo(self, cmd, error=None):
        '''format error to error info strings, for concatenating and logging'''
        if type(error) in (ExpectFailure, TimeoutError, BuiltinCmdError):
            errdesc = '%s: ' %(type(error).__name__) + (error.args[0] if error.args else 'NARG')
        else:
            errdesc = repr(error)

        commandinfo = 'Command: %s' %(cmd if cmd else 'ENTER')
        sessioninfo = 'Session: %s' %(self.agent.this_session)
        sequenceinfo = 'Sequence: %s' %(self.seq_file)
        loopinfo = 'Loop: %d' %(self.cmplt_running_loops + 1)

        errinfo = utils.concat_text_lines(errdesc, commandinfo, sessioninfo, sequenceinfo, loopinfo)

        return errinfo

    def handle_error(self, cmd, error):
        '''handle all incoming errors with corresponding cmd'''
        errinfo = self.format_errinfo(cmd, error)
        raise_up = False

        # expect failure
        if isinstance(error, ExpectFailure):
            if STOP_ON_FAILURE:
                raise_up = True
        # timeout error
        elif isinstance(error, TimeoutError):
            raise_up = True
        # builtin error
        elif isinstance(error, BuiltinCmdError):
            raise_up = True
        # other errors
        else:
            self.logging_error('\nERROR INFO:\n')
            #self.logging_error(traceback.format_exc())
            #self.logging_error(sys.exc_info()[2])
            self.logging_error(errinfo + '\n')
            ttyinfo = 'AGENT INFO:\n' + repr(self.agent)
            self.logging_error(ttyinfo + '\n')

        if raise_up:
            # send loop failure message to the master to end master sensing
            msg = {
                'MSG': MSGS.loop_result_fail.value,
                'NAME': self.seq_file.split('.')[0],
                'LOOP': self.cmplt_running_loops + 1,
                'MSGQ': [errinfo, ],
                }
            self.uds.send_server_msg(msg)
            self.errordump = error
            self.stop()
            raise error
        else:
            # we don't stop the process, but append the error string to the loop failure queue, and send ths message queue
            # later to master, which will record these messages.
            self.loop_failures.append(errinfo)

    def exec_command(self, command):
        '''run single command and handle errors, no matter builtin command or normal shell command'''
        output = ''
        result = MSGS.command_result_pass  # by default pass

        try:
            output = self.agent.exec(command)
        except Exception as error:
            if type(error) in (ExpectFailure, TimeoutError):
                result = MSGS.command_result_fail   # timeout error and expect failure are test failure
            else:
                result = MSGS.test_need_recovery # unknown errors typically indicate environment failure

            if hasattr(error, 'output'):
                output = error.output   # error obj will hold the command's output when exception occurs
            self.handle_error(str(command), error)

        return result, output


    def run_sequence(self, sequence=None, loops=None):
        '''run sequence of commands, by default run the whole sequence parsed from the sequence file'''
        # update globals only when we start running sequence
        global THIS_WORKER
        THIS_WORKER = self

        if sequence: self.running_sequence = sequence
        if loops: self.running_loops = loops
        self.cmplt_running_loops = 0
        running_loop = lambda x: (x.cmplt_running_loops + 1)

        # loop retry parameters
        test_recovery_retry = TEST_RECOVERY_RETRY   # how many times we can retry running sequence if we see failures or errors
        last_recovery_loop = 0      # last loop we have retried to recovery

        # looping sequence
        while self.cmplt_running_loops < self.running_loops:
            # below are loop level parameters
            self.spawned_workers = []
            self.loop_failures = []
            loop_result = MSGS.loop_result_pass
            cmd_counter = 0
            # run commands
            while cmd_counter < len(self.running_sequence):
                self.running_command = self.running_sequence[cmd_counter]
                # run this command
                result, output = self.exec_command(self.running_command)
                # test need recovery
                if result == MSGS.test_need_recovery:
                    loop_result = result
                    # recovery failed after retry
                    if test_recovery_retry == 0:
                        e = RecoveryError('Recovery failed after %r retry at loop %r' %(TEST_RECOVERY_RETRY,
                                                                                        running_loop(self)))
                        self.logging_error('\n****************ERROR DUMP END****************\n')
                        edesc = '\n' + repr(e) + '\n'
                        self.logging_error(edesc + '\n')
                        self.stop()
                        return 0        # exit worker, quit

                    if running_loop(self) == last_recovery_loop:
                        test_recovery_retry -= 1
                    else:
                        last_recovery_loop = running_loop(self)
                        test_recovery_retry = TEST_RECOVERY_RETRY
                    # send master a recovery message
                    recovery_msg = {
                            'MSG': loop_result.value,
                            'NAME': self.seq_file.split('.')[0],
                            'LOOP': running_loop(self),
                            'MSGQ': self.loop_failures[-1],
                            }
                    self.uds.send_server_msg(recovery_msg)
                    # initialize loop level parameters
                    for worker in self.spawned_workers:
                        worker.kill()
                        time.sleep(0.1)
                    self.spawned_workers = []
                    self.loop_failures = []
                    loop_result = MSGS.loop_result_pass
                    self.agent.close_tty()  # close tty
                    cmd_counter = 0         # reset command counter
                else:
                    cmd_counter += 1
            # send master loop message
            loop_msg = {
                'MSG': loop_result.value,
                'NAME': self.seq_file.split('.')[0],
                'LOOP': running_loop(self),
                'MSGQ': self.loop_failures,
                }
            self.uds.send_server_msg(loop_msg)
            # ahead to next loop
            self.cmplt_running_loops += 1



class MasterWorker(object):
    """Master process, processing sequence workers message and display window output"""
    def __init__(self):
        self.failure_logfile = None
        self.seqworkers = []
        self.uds = get_this_uds()

    def logging_failure(self, data):
        if self.failure_logfile is None:
            log_header = '********FAILURE LOGGING********' + '\n\n'
            filename = utils.new_log_path(sequence=self.init_sequence_file.split(os.sep)[-1], suffix='failure')
            self.failure_logfile = open(filename, mode='w')
            self.failure_logfile.write(log_header)
            self.failure_logfile.flush()

        if self.failure_logfile and not self.failure_logfile.closed:
            self.failure_logfile.write(data)
            self.failure_logfile.flush()

    def update_worker_status(self, msg):
        if not isinstance(msg, dict) or 'NAME' not in msg or 'MSG' not in msg:
            return False

        arriver = msg['NAME']
        signal = msg['MSG']

        updated = False
        for worker in self.seqworkers:
            # sequence workers that has started
            if arriver == worker['NAME']:
                if signal == MSGS.worker_run_cmplt.value:
                    worker['STATUS'] = 'C'          # 'C' stands for Completed
                elif signal == MSGS.test_need_recovery.value:
                    errorlog = '\nERROR LOOP: %r \nERROR MESSAGE:\n' %(msg['LOOP'])
                    for elog in msg['MSGQ']:
                        errorlog = errorlog + elog + '\n'
                    self.logging_failure(errorlog)
                elif signal == MSGS.loop_result_fail.value:
                    worker['FAILURE-LOOPS'] += 1
                    failureinfo = { msg['LOOP']: msg['MSGQ'] }
                    worker['FAILURE-MESSAGES'].update(failureinfo)
                    failurelog = '\nFAILURE LOOP: %r \nFAILURE MESSAGES:\n' %(msg['loop'])
                    for flog in msg['MSGQ']:
                        failurelog = failurelog + flog + '\n'
                    self.logging_failure(failurelog)
                else:
                    worker['SUCCESS-LOOPS'] += 1    # loop pass

                updated = True
        # new sequence workers
        if not updated:
            if signal != MSGS.worker_run_start.value:
                raise RuntimeError('Invalid worker message received: %r' %(signal))

            if len(self.seqworkers) >= MAX_SEQUENCE_WORKER:
                raise RuntimeError('Too many sequences started, maximum: %r' %(MAX_SEQUENCE_WORKER))

            worker = {
                'NAME': arriver,
                'FAILURE-LOOPS': 0,
                'SUCCESS-LOOPS': 0,
                'TOTAL-LOOPS': msg['LOOPS'],
                'FAILURE-MESSAGES': {},
                'STATUS': 'R',  # 'R' stands for Running
                }
            self.seqworkers.append(worker)

        return True

    def some_worker_running(self):
        return any(w['STATUS'] == 'R' for w in self.seqworkers)



###############################################################################
# ********************** MULTIPROCESSING **************************************
###############################################################################
def run_sequence_worker(sequence_file, sequence_loops):
    job = SequenceWorker(sequence_file, sequence_loops)
    if job.logfile and not job.logfile.closed:
        line = '*************SEQUENCE LOGGING***************'
        job.logfile.write(line + '\n\n')
        line = 'SEQUENCE FILE: %s' %(sequence_file)
        job.logfile.write(line + '\n\n')
        job.logfile.flush()

    #print('\n------Sequence Worker Started------\n')
    #print('Worker sequence file: %s' %(sequence_file))
    #print('Worker sequence:')
    #for command in job.running_sequence:
    #    print('\t' + repr(command))
    #print('Worker logfile: %s' %(logfile.name if logfile else 'Log Disabled'))
    #print('Total loops: %d' %(job.iterations))
    job.run_sequence()

    #print('Worker exit normally, sequence file: %s' %(sequence_file) + \
    #      (', log dumped into: %s' %(logfile.name) if logfile else ''))
    if job.logfile and not job.logfile.closed:
        line = 'Test sequence completed successfully...'
        job.logfile.write('\n\n' + line + '\n')
        job.logfile.flush()
    # job completes
    job.stop()


# ********************** PROGRAM MAIN ENTRY **********************************
def start_master(main_sequence_file, main_sequence_loops=1):
    global WIN_DISPLAY_EN
    master = MasterWorker()
    # enable window display
    if WIN_DISPLAY_EN is None:
        WIN_DISPLAY_EN = Value('b', 1)
    else:
        WIN_DISPLAY_EN.value = 1

    # START THE MAIN WORKER
    mainworker = Process(target=run_sequence_worker, args=(main_sequence_file,
                                                           main_sequence_loops,))
    mainworker.start()
    message = {
        'MSG': MSGS.worker_run_start.value,
        'NAME': main_sequence_file.split('.')[0],
        'LOOPS': main_sequence_loops,
        }
    master.update_worker_status(message)

    this_uds = get_this_uds()
    t_start = time.time()   # process starting time
    # window display refresh
    while WIN_DISPLAY_EN.value > 0:
        # process incoming message
        master.update_worker_status(this_uds.recv_client_msg())

        window_header = '\n\nRUNNING WORKERS: %d \n' %(len(master.seqworkers))
        time_consume = str(datetime.timedelta(seconds=int(time.time() - t_start)))
        window_display = window_header + 'TIME CONSUME: %s\n\n' %(time_consume)
        cursor_lines = 5
        # quit everything if all test workers exit
        if not master.some_worker_running:
            # handle all buffered messages
            while master.update_worker_status(this_uds.recv_client_msg()): pass
            if this_uds.serversock:
                this_uds.serversock.close()
                this_uds.serversock = None
            WIN_DISPLAY_EN.value = 0

        # update window display
        for worker in master.seqworkers:
            success_loops = worker['SUCCESS-LOOPS']
            failure_loops = worker['FAILURE-LOOPS']
            window_display = window_display + \
                '* Worker [%s]: %d total loops, %d loops PASS, %d loops FAIL ...\n' %(worker['NAME'],
                                                                                    worker['TOTAL-LOOPS'],
                                                                                    success_loops,
                                                                                    failure_loops)
            cursor_lines += 1

        # refresh window display lines
        sys.stdout.write(window_display)
        sys.stdout.flush()
        time.sleep(WIN_REFRESH_INTERVAL)

        if WIN_DISPLAY_EN.value > 0:
            cursor.erase_lines_upward(cursor_lines)
    # display window summary when test completes
    window_summary_display = '\nRESULT SUMMARY:\n\n'
    for worker in master.seqworkers:
        success_loops = worker['SUCCESS-LOOPS']
        failure_loops = worker['FAILURE-LOOPS']
        window_summary_display = '\n' + window_summary_display + \
            '* Sequence [%s]>> Total loops: %d, %d loops PASSED, %d loops FAILED\n' %(worker['NAME'],
                                                                                     success_loops+failure_loops,
                                                                                     success_loops,
                                                                                     failure_loops)
        if worker['FAILURE-MESSAGES']:
            window_summary_display += 'FAILURE LOOPS: '
            window_summary_display += ', '.join([str(x) for x in worker['FAILURE-MESSAGES'].keys()])
        window_summary_display += '\n'

    sys.stdout.write(window_summary_display)
    sys.stdout.write('\nFailure log dumped to: %s\n\n' %(master.failure_logfile.name if master.failure_logfile else 'NA'))
    sys.stdout.flush()
    if master.failure_logfile and not master.failure_logfile.closed:
        master.failure_logfile.flush()
        master.failure_logfile.close()
    # Remove unix domain sock file
    if UNIX_DOMAIN_SOCKET:
        os.remove(UNIX_DOMAIN_SOCKET)



def get_this_worker():
    return THIS_WORKER
