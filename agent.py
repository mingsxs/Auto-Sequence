import os
import time
import re
from enum import Enum

import ptyprocess
import utils
from command import *
from utils import BYTES, STR, magic_search
from globs import *
from errors import *


class AgentWrapper(object):
    """Basic agent class."""

    PTY_TRIGGER_CMDS = ('telnet', 'ssh')

    def __init__(self, logfile=None):
        self.prompt = LOCAL_SHELL_PROMPT
        self.pty = None
        self.buffer = ''

    def log(self, data=''):
        nbytes = 0
        if self.logfile and not self.logfile.closed:
            while data:
                n = self.logfile.write(data)
                nbytes += n
                data = data[n:]
            self.logfile.flush()

        return nbytes

    def flush(self, wait=0.0):
        if self.pty:
            out = self.buffer + STR(self.pty.read_all_nonblocking(readafterdelay=wait))
            self.buffer = ''
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
            pos = magic_search(exp, out, find=True)
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
            if magic_search(esc, out):
                raise_up = True
                break

        return raise_up

    def probe_read(self, command):
        

    def exec_cmd(self, command):
        
