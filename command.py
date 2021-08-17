import os
import re
from multiprocessing import Process

import utils
import worker
from worker import get_this_worker
from globs import *
from errors import *
import uds
from uds import MESSAGES as MSGS
from sequence import get_this_seqfile, get_this_seqreader


__all__ = [
    'make_shellcmd_args_by_line',
    'make_bltincmd_args_by_line',
    'BuiltinCmd',
    'ShellCmd',
    'CTRL_C',
    'RUN',
    'RUN_WAIT',
    'CLOSE',
    'ENTER',
    'WAIT',
    'PULSE',
    'SETPROMPT',
    'FIND',
    'SUBSEQUENCE',
    'LOOP',
    'PASSWD',
    ]

# to make args as [cmd, (argx1, argx2...), (argy1, argy2)...]
# args are separated by ';'
# subargs are separated by ','
def make_shellcmd_args_by_line(line):
    item_delimiter = ';'
    subitem_delimiter = ','
    escapes = {
        "\\;": chr(127 + 1),    # semicolon, used to separate items
        "\\,": chr(127 + 2),    # comma, used to separate subitems
        "\\ ": chr(127 + 3),    # space, used to separate builtin command args
        }
    for esc, c in escapes.items():
        line = line.replace(esc, c)

    items = [x.strip(' ') for x in line.split(item_delimiter) if x]

    if items:
        cmd = items[0]
        items = items[1:]
    else:
        cmd = ''

    for i, item in enumerate(items):
        item = item.replace(chr(128), ";")
        items[i] = [y.strip(' ') for y in item.split(subitem_delimiter) if y]
        for j, subitem in enumerate(items[i]):
            subitem = subitem.replace(chr(129), ",")
            subitem = subitem.replace(chr(130), " ")
            items[i][j] = subitem

    makeargs = [cmd, ] + [tuple(x) for x in items]

    return makeargs

# to make args as [cmd, arg1, arg2...]
# args are separated by ' '
def make_bltincmd_args_by_line(line):
    delimiter = ' '
    escapes = {
        "\\ ": chr(127 + 3),    # space, used to separate builtin command args
        }
    for esc, c in escapes.items():
        line = line.replace(esc, c)

    makeargs = [x for x in line.split(delimiter) if x]

    for i, arg in enumerate(makeargs):
        makeargs[i] = arg.replace(chr(130), ' ')    # swap back to space

    return makeargs


class Cmd(object):
    """Base command class"""
    def __init__(self, **kw):
        # each command must contain following args
        self.command = None
        self.terminator = None  # string to probe the termination of execution
        self.probe_count = 0    # how many times we need to probe
        self.output = ''        # command output, for later populating

        for k, v in kw,items():
            if k and v:
                setattr(self, k, v)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            return None

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        if isinstance(self, BuiltinCmd)
            return self.token + ': ' + self.description
        if isinstance(self, ShellCmd)
            return self.command

    def __repr__(self):
        if isinstance(self, BuiltinCmd)
            rpr1 = str(self)
            rpr2 = 'usage: ' + self.usage
            cmd_rpr = utils.concat_text_lines(rpr1, rpr2)
        else:
            cmd_rpr = 'shell command: ' + self.command + '\n'

        arg_rpr = 'args: ' + repr(self.args)
        dict_rpr = 'dict: ' + repr(self.dict)

        return utils.concat_text_lines(cmd_rpr, arg_rpr, dict_rpr, self.output)

    @property
    def dict(self):
        if self.__dict__:
            return self.__dict__
        else:
            return 'NUL'        # return this for concatenating strings


class ShellCmd(Cmd):
    """Normal shell command class"""
    def __init__(self, args):
        super().__init__()

        if isinstance(args, type('')):
            args = [args,]
            self.command = args[0]
        else:
            self.command = args[0]

        if len(args) > 4:
            raise SequenceError("Normal Command Syntax Error, Args: %r" %(args))

        self.args = args
        # get timeout arg firstly
        self.timeout = DEFAULT_SHELLCMD_TIMEOUT
        if len(args[-1]) == 1:
            arg = args[-1][0]
            try:
                self.timeout = float(arg)
                del args[-1]
            except ValueError:
                pass
        # get expects and escapes args secondly
        # these args are list like [arg1, arg2,...]
        f = lambda x, i: x[i] if i < len(x) else None
        self.expects = f(args, 1)
        self.escapes = f(args, 2)

        self.enterchar = None

#
#
# NOTE: for `discovery` method, we only use `get_this_seqreader` to retrieve sequence info,
# because at this moment, the module `sequence` contains the latest sequence.
#       for `exec` method, we only use `get_this_worker` to retrieve sequence info,
# because at this moment, the module `worker` contains the latest sequence.
class BuiltinCmd(Cmd):
    """Builtin command class"""
    def __init__(self, args, **kw):
        super().__init__(self, **kw)
        self.is_seq_cmd = True  # if this command is sequence command, if not, don't append it to the sequence
        self.timeout = DEFAULT_BLTINCMD_TIMEOUT
        self.args = args

    @classmethod
    def discovery(cls, line):   # line is a concatenated raw line
        inst = None
        args = make_bltincmd_args_by_line(line)

        if args:  # at least contain 1 arg
            subclasses = cls.__subclasses__()

            for subcls in subclasses:
                inst = subcls.discovery(args)
                if inst: break

        return inst

    def exec(self):
        print("Warning: command `%s` doesn't implement exec method, bypassed.")
        return False

"""
CTRL-C
"""
class CTRL_C(BuiltinCmd):
    """CTRL-C definition class"""
    token = 'CTRL-C'
    usage = 'CTRL-C'
    argc = (1,)
    description = 'send a intr(known as ctrl-c) signal to current pty.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)
        #self.command = 'CTRL-C'

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_parse(args):
            return cls(args)

        return None

#    def exec(self):
#        this_agent = get_this_worker().agent
#        return this_agent.send_control('c')
#        return True
#
"""
RUN
"""
class RUN(BuiltCmd):
    """Spawn a new sequence worker and dont wait"""
    token = 'RUN'
    usage = 'RUN [seq_file] [loops]'
    argc = (2, 3,)
    description = 'spawn process running a new sequence and doesn\'t wait for it to end.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)

        if not hasattr(self, 'seq_loops'):
            self.seq_loops = 1
        self.seq_file = utils.fix_seqfile_path(self.seq_file)

        if self.seq_loops <= 1:
            self.seq_loops = 1

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            seq_file = args[1]
            seq_loops = int(args[2]) if len(args) > 2 else 1

            return cls(args, seq_file=seq_file, seq_loops=seq_loops)

        return None

    def exec(self):
        new_worker = Process(target = worker.run_sequence_worker,
                             args = (self.seq_file,
                                     self.seq_loops))
        new_worker.start()  # start the sequence worker
        # notify server that new worker has started
        msg = {
            'MSG': MSGS.worker_run_start.value,
            'NAME': self.seq_file.split(os.sep)[-1].split('.')[0],
            'LOOPS': self.seq_loops,
            }
        this_uds = uds.get_this_uds()
        this_uds.send_server_msg(msg)
        this_worker = get_this_worker()
        this_worker.spawned_workers.append(new_worker)
        return True

"""
RUN_WAIT
"""
class RUN_WAIT(BuiltinCmd):
    """Spawn a new sequence worker and wait for it to end"""
    token = 'RUN_WAIT'
    usage = 'RUN_WAIT [seq_file] [loops]'
    argc = (2, 3,)
    description = 'spawn process running a new sequence and wait for it to end.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)

        if not hasattr(self, 'seq_loops'):
            self.seq_loops = 1
        self.seq_file = utils.fix_seqfile_path(self.seq_file)

        if self.seq_loops <= 1:
            self.seq_loops = 1

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            seq_file = args[1]
            seq_loops = int(args[2]) if len(args) > 2 else 1

            return cls(args, seq_file=seq_file, seq_loops=seq_loops)

        return None

    def exec(self):
        new_worker = Process(target = worker.run_sequence_worker,
                             args = (self.seq_file,
                                     self.seq_loops))
        new_worker.start()  # start the sequence worker
        # notify server that new worker has started
        msg = {
            'MSG': MSGS.worker_run_start.value,
            'NAME': self.seq_file.split(os.sep)[-1].split('.')[0],
            'LOOPS': self.seq_loops,
            }
        this_uds = worker.get_this_uds()
        this_uds.send_server_msg(msg)
        this_worker = get_this_worker()
        this_worker.spawned_workers.append(new_worker)
        new_worker.join()  # wait for the new process to complete
        return True

"""
CLOSE
"""
class CLOSE(BuiltinCmd):
    """Close THIS pty"""
    token = 'CLOSE'
    usage = 'CLOSE'
    argc = (1,)
    description = 'close current running pty.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            return cls(args)

        return None

    def exec(self):
        this_agent = get_this_worker().agent
        this_agent.close_pty()
        return True

"""
ENTER
"""
class ENTER(BuiltinCmd):
    """Press an enter button"""
    token = 'ENTER'
    usage = 'ENTER'
    argc = (1,)
    description = 'send a newline, to fake pressing the enter button.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)
        self.command = ''

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            return cls(args)

        return None

#    def exec(self):
#        this_worker = get_this_worker()
#        return this_worker.exec_command(ShellCmd(('',)))
#
"""
WAIT
"""
class WAIT(BuiltinCmd):
    """Wait for some time"""
    token = 'WAIT'
    usage = 'WAIT [time]'
    argc = (2,)
    description = 'sleep for some time, in seconds.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)
        self.waitsec = utils.convert_time(self.time)

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            strtime = args[1]
            return cls(args, time=strtime)

        return None

    def exec(self):
        time.sleep(self.waitsec)
        return True

"""
PULSE
"""
class PULSE(BuiltinCmd):
    """Send the pulse shell command in case that remote connection drops"""
    token = 'PULSE'
    usage = 'PULSE'
    argc = (1,)
    description = 'send a pulse shell command.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)
        self.timeout = -1
        self.command = "while :; do echo ''; sleep 3600; done"

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            return cls(args)

        return None

#    def exec(self):
#        this_worker = get_this_worker()
#        pulse_cmd = "while :; do echo ''; sleep 3600; done"
#        return this_worker.exec_command(ShellCmd(pulse_cmd,))
#
"""
SETPROMPT
"""
class SETPROMPT(BuiltinCmd):
    """Set THIS agent's pty prompt"""
    token = 'SETPROMPT'
    usage = 'SETPROMPT [promptstr]'
    argc = (2,)
    description = 'set current agent\'s pty prompt.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)
        self.promptstr = self.prompt

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            prompt = args[1]
            return cls(args, prompt=prompt)

        return None

    def exec(self):
        this_agent = get_this_worker().agent
        this_agent.set_pty_prompt(self.promptstr)
        return True

"""
FIND
"""
class FIND(BuiltinCmd):
    """Find a certain file under a set of directories"""
    token = 'FIND'
    usage = 'FIND [filename] [list of directories, separated by comma]'
    argc = (3,)
    description = 'find a certain file under a set of directories.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            fname = args[1]
            paths = utils.split_text_by_delimiter(args[2], ',')
            return cls(args, fname=fname, paths=paths)

        return None

    def exec(self):
        efi_path_pat = r'^FS\d+:$'
        this_worker = get_this_worker()
        for d in self.paths:
            if 'cd' in d or re.search(efi_path_pat, d):
                command = ShellCmd((d, ))
            else:
                command = ShellCmd(('cd ' + d, ))

            r, m, o = this_worker.exec_command(command)

            if utils.magic_search(self.fname, o):
                return (True, o)

        return (False, o)

"""
SUBSEQUENCE
"""
class SUBSEQUENCE(BuiltinCmd):
    """Define a subsequence by specifying a symbol name"""
    token = r'^SUBSEQUENCE$|^ENDSUBSEQUENCE$'
    usage = 'SUBSEQUENCE [symbol] / ENDSUBSEQUENCE'
    argc = (1, 2,)
    description = 'define a subsequnce of the completed sequence as a symbol.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)
        self.is_seq_cmd = False     # we won't append subsequence command to the command sequence

    def __str__(self):
        '''since we use a regex to match this command, we need to define its own __str__'''
        return self.args[0]

    @classmethod
    def syntax_check(cls, args):
        if re.search(cls.token, args[0]):
            if (args[0] == 'SUBSEQUENCE' and len(args) == 2) or \
                    (args[0] == 'ENDSUBSEQUENCE' and len(args) == 1):
                return True

            raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            this_seqreader = get_this_seqreader()
            if args[0] == 'SUBSEQUENCE':
                if this_seqreader.subsequence_probe is not None:
                    raise BuiltinCmdError('Do not use SUBSEQUENCE command recursively, usage: %s', %(cls.usage))
                else:
                    symbol = args[1]
                    this_seqreader.subsequence_probe = (symbol, this_seqreader.cmd_counter)
            else:
                if this_seqreader.subsequence_probe is None:
                    raise BuiltinCmdError('No previous pair SUBSEQUENCE command found, usage: %s', %(cls.usage))
                else:
                    symbol = this_seqreader.subsequence_probe[0]
                    start = this_seqreader.subsequence_probe[1]
                    subsequence = this_seqreader.sequence[start:]
                    this_seqreader.subsequences.update({symbol : subsequence})
                    this_seqreader.subsequence_probe = None

            return cls(args)    # return to caller, telling it to take this command as a builtin command

        return None

"""
LOOP
"""
class LOOP(BuiltinCmd):
    """Loop a subsequence defined previously by user"""
    token = 'LOOP'
    usage = 'LOOP [subsequence symbol] [loops]'
    argc = (3,)
    description = 'loop a user defined subsequence for specified loops.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            symbol = args[1]
            loops = int(args[2])
            this_seqreader = get_this_seqreader()
            if symbol not in this_seqreader.subsequences:
                raise BuiltinCmdError('Invalid subsequence symbol: %s' %(symbol))
            return cls(args, symbol=symbol, loops=loops)

        return None

    def exec(self):
        this_worker = get_this_worker()
        sequence = this_worker.subsequences[self.symbol]
        this_worker.run_sequence(sequence=sequence, loops=self.loops)
        return True

"""
PASSWD
"""
class PASSWD(BuiltinCmd):
    """Indicate that this command arg is to send a password string, which should be invisble"""
    token = 'PASSWD'
    usage = 'PASSWD [password]'
    argc = (2,)
    description = 'send the command argument as an invisible password string.'

    def __init__(self, args, **kw):
        super().__init__(args, **kw)

    @classmethod
    def syntax_check(cls, args):
        if args[0] == cls.token:
            if len(args) not in cls.argc:   # check argument count
                raise SequenceError("Builtin Command Syntax Error, Usage: %r" %(cls.usage))
            return True

        return False

    @classmethod
    def discovery(cls, args):
        if cls.syntax_check(args):
            passwd = args[1]
            return cls(args, passwd=passwd)

        return None

    def exec(self):
        this_worker = get_this_worker()
        this_agent = this_worker.agent
        this_command = this_worker.running_command
        passwd_retry = 3
        _raise = None

        while passwd_retry > 0:
            this_agent.send_command(self.passwd)
            try:
                return this_agent.probe_terminator(this_command)
            except TimeoutError as error:
                passwd_retry -= 1
                _raise = error

        raise _raise

