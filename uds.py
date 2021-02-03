import sys
import os
import errno
import time
import datetime
import socket
import re
import json
from enum import Enum
import utils
from globs import *
from worker import MAX_SEQUENCE_WORKER

# retry timeout for socket
SOCK_RETRY_TIMEOUT = 90.0
UNIX_DOMAIN_SOCK = None
THIS_UDS = None

class MESSAGES(Enum):
    """Signal definitions for workers"""
    worker_run_start = 1    # start a new worker
    worker_run_cmplt = 2    # THIS worker completes
    loop_result_pass = 3    # current loop pass
    loop_result_fail = 4    # current loop fail
    command_result_pass = 5 # single command pass
    command_result_fail = 6 # single command fail
    # some unexpected errors occur, such as network error, pty error, scenerio-dependent
    test_need_recovery = 7


class UDS(object):
    """unix domain socket for ipc class"""
    def __init__(self):
        global UNIX_DOMAIN_SOCK
        if THIS_UDS is None:
            self.serversock = None

            UNIX_DOMAIN_SOCK = utils.new_uds_name(utils.get_this_seqfile())
            self.uds = UNIX_DOMAIN_SOCK

    def init_server_sock(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.setblocking(False)  # set nonblocking listening
        try:
            os.remove(self.uds)
        except OSError:
            pass
        sock.bind(self.uds)
        sock.listen(MAX_SEQUENCE_WORKER)
        self.serversock = sock


    def recv_client_msg(self):
        '''Receive a message from the uds sock, blocking'''
        if DEBUG_MODE_ON:
            return None

        if not self.serversock:
            self.init_server_sock()

        recved = b''
        msg = None

        try:
            conn, addr = self.serversock.accept()
            try:
                while True:
                    try:
                        s = conn.recv(4096)
                    except OSError:
                        s = b''

                    if not s and recved:
                        try:
                            msg = json.loads(utils.STR(recved))
                        except ValueError:
                            msg = utils.STR(recved)
                        break   # received a valid message from socket

                    recved = recved + s
            finally:
                conn.close()

        except OSError as err:
            if err.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                self.init_server_sock()

        return msg

    def send_server_msg(self, rawmsg):
        '''Send message to the uds sock'''
        if DEBUG_MODE_ON:
            return True

        if not isinstance(rawmsg, str):
            msg = json.dumps(rawmsg, ensure_ascii=True)

        tosend = utils.BYTES(msg)  # serialize message
        if not tosend:
            return False

        t_end = time.time() + SOCK_RETRY_TIMEOUT
        sent = False

        while time.time() <= t_end and not sent:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.setblocking(False)
                sock.connect(self.uds)
                sock.sendall(tosend)
                sent = True
            except OSError as err:
                # socket fails connecting or resource unavailable
                if err.errno not in (errno.EAGAIN, errno.EWOULDBLOCK,
                                     errno.ECONNREFUSED, errno.ECONNABORTED,
                                     errno.EBADF, errno.ENOTCONN, errno.EPIPE):
                    break

            finally:
                sock.close()

        if not sent:  # fails sending message
            if not hasattr(self, 'client_retry'):  # initialize server sock and retry
                self.client_retry = 1
                self.init_server_sock()
                self.send_server_msg(rawmsg)
            else:
                utils.disable_win_display()
                this_worker = utils.get_this_worker()
                error = RuntimeError("Send client message failed: %r" %(tosend))
                this_worker.logging_error(error)
                raise error



def get_this_uds():
    global THIS_UDS
    if THIS_UDS is None:
        THIS_UDS = UDS()
    return THIS_UDS
