
import utils
import command
from errors import *
from command import ShellCmd, BuiltinCmd

THIS_SEQUENCE_FILE = ''
THIS_SEQUENCE_READER = None

class SequenceReader(object):
    """Read and parse commands from a sequence file"""
    continue_nextline = '\\'
    comment_header = '#'

    def __init__(self, fname):
        self.fname = utils.fix_seqfile_path(fname)
        self.fp = None
        self.sequence = []
        self.subsequence_probe = None
        self.subsequences = {}
        self.cmd_counter = 0

    def strip_line_comment(self, line):
        pos = line.find(self.comment_header)
        if pos >= 0:
            line = line[:pos]
        line = line.rstrip()

        return line

    def open(self, mode='r'):
        if self.fp is None:
            self.fp = open(self.fname, mode=mode)

    def lines(self):
        self.open()
        concat = ''
        for line in self.fp:
            line = utils.STR(line)
            line = self.strip_line_comment(line)   # skip comments

            if not line:  # skip null lines
                continue

            if line[-1] == self.continue_nextline: # need to concatenate next line
                concat = concat + line[:-1]
                continue

            concat = concat + line
            yield concat
            concat = ''

        self.fp.close()
        self.fp = None

    def parse_lines(self):
        # update globals only when we start parsing
        global THIS_SEQUENCE_READER, THIS_SEQUENCE_FILE
        THIS_SEQUENCE_FILE = self.fname
        THIS_SEQUENCE_READER = self

        for seqline in self.lines():
            builtincmd = BuiltinCmd.discovery(seqline)  # check if this a builtin command first
            if builtincmd:
                if builtincmd.is_seq_cmd:
                    self.sequence.append(builtincmd)
                    self.cmd_counter += 1
            else:
                shellargs = command.make_shellcmd_args_by_line(seqline)
                self.sequence.append(ShellCmd(shellargs))
                self.cmd_counter += 1



def get_this_seqfile():
    return THIS_SEQUENCE_FILE


def get_this_seqreader():
    return THIS_SEQUENCE_READER
