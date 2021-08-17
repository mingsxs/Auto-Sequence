import os
import time
import re
from enum import Enum

import ptyprocess
import utils
from utils import BYTES, STR
from command import *
from globs import *
from errors import *


class AgentWrapper(object):
    """Basic agent class."""

    delay_retry_close = 0.05
    ttyfork_probe_command = ('telnet', 'ssh')
    CR = '\r'
    LF = '\n'

    def __init__(self, logfile=None):
        self.prompt = DEFAULT_LOCAL_PS1
        self.logfile = logfile
        self.post_read = ''
        self.tty = None

    def log(self, data=''):
        nsent = 0
        if self.logfile and not self.logfile.closed:
            while data:
                n = self.logfile.write(data)
                nsent += n
                data = data[n:]
            self.logfile.flush()

        return nsent

    def flush(self):
        if self.tty:
            out = self.post_read + STR(self.tty.read_all_nonblocking())
            self.post_read = ''
            out = utils.strip_ansi_escapes(out)
            self.log(out)

    def close_handler(self):
        if self.logfile and not self.logfile.closed:
            self.logfile.flush()
            self.logfile.close()

    def _expect(self, out, expect):
        """Expect each item in expect list, return False only if all items are found."""
        if not expect or not out: return False

        expects = expect if isinstance(expect, type(())) else (expect,)
        raise_up = False

        for exp in expects:
            pos = utils.magic_search(exp, out, find=True)
            if pos < 0:
                raise_up = True
                break
            out = out[pos+len(exp):]

        return raise_up

    def _escape(self, out, escape):
        """Escape each item in escape list, return False if any of items is found."""
        if not escape or not out: return False

        escapes = escape if isinstance(escape, type(())) else (escape,)
        raise_up = False

        for esc in escapes:
            if utils.magic_search(esc, out):
                raise_up = True
                break

        return raise_up

    def probe_read(self, command):
        

    def exec(self, command):
        if isinstance(command, BuiltinCmd):
            if hasattr(command, 'exec'):
                return command.exec()
            else:
                raise BuiltinCmdError('Builtin Command Error: %s, no EXCE method' %(command.args[0]))

        if isinstance(command, ShellCmd):
            tty = self.tty
            if tty and not tty.closed:
                if not tty.isalive():
                    raise 


    def close_tty(self):
        if self.tty and not self.tty.closed:
            self.flush()
            append = 'Close TTY ...'
            self.log('\n\n' + append + '\n\n')
            while not self.tty.closed:
                try:
                    self.tty.close()
                except:
                    time.sleep(self.delay_retry_close)

        self.prompt = DEFAULT_LOCAL_PS1
        self.tty = None

    def exit(self):
        self.flush()
        self.log('\n\n' + str(self) + '\n')
        self.close_tty()
        self.close_handler()

    def __str__(self):
        header = 'AGENT INFO:'
        ttydesc = str(self.tty)
        logname = self.logfile.name if self.logfile else 'NONE'
        prompt = self.prompt

        return utils.concat_text_lines(header, ttydesc, logname, prompt)

    def __repr__(self):
        return self.__str__()
