import os
import re
import sys
import datetime
import subprocess
from subprocess import Popen, PIPE

import worker
import sequence
import uds
import globs
from globs import *


PY3 = (sys.version_info[0] >= 3) # if currently we are in Python3.

# BYTES and STR methods.
if PY3:

    def BYTES(text, encoding="utf-8", errors='strict'):
        try:
            return bytes(text, encoding=encoding, errors=errors)
        except:
            return bytes(text)

    def STR(text, encoding="utf-8", errors="ignore"):
        try:
            return text.decode(encoding, errors=errors)
        except:
            return str(text)

else:

    def STR(text, encoding='utf-8', errors='ignore'):
        try:
            return text.encode(encoding, errors=errors)
        except:
            return str(text)

    def BYTES(text): # In Python2, builtin method `bytes` is `str`.
        return STR(text)


# which method.
try:
    from shutil import which  # Python >= 3.3
except ImportError:
    import os, sys
    
    # This is copied from Python 3.4.1
    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.
    
        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.
    
        """
        # Check that a given file can be accessed with the correct mode.
        # Additionally check that `file` is not a directory, as on Windows
        # directories pass the os.access check.
        def _access_check(fn, mode):
            return (os.path.exists(fn) and os.access(fn, mode)
                    and not os.path.isdir(fn))
    
        # If we're given a path with a directory part, look it up directly rather
        # than referring to PATH directories. This includes checking relative to the
        # current directory, e.g. ./script
        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None
    
        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)
    
        if sys.platform == "win32":
            # The current directory takes precedence on Windows.
            if not os.curdir in path:
                path.insert(0, os.curdir)
    
            # PATHEXT is necessary to check on Windows.
            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            # See if the given file matches any of the expected path extensions.
            # This will allow us to short circuit when given "python.exe".
            # If it does match, only test that one, otherwise we have to try
            # others.
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            # On other platforms you don't have things like PATHEXT to tell you
            # what file suffixes are executable, so just pass on cmd as-is.
            files = [cmd]
    
        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if not normdir in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None



# method that gets the prompt text.
def get_text_prompt_line(text):
    out = STR(out)
    
    out = out.rstrip()
    promptline = ''
    if out:
        promptline = out.splitlines()[-1].lstrip()
    
    return promptline


def split_out_lines(out):
    out = STR(out)
    
    lines = [line for line in out.splitlines() if line.strip()]
    
    return lines


def get_command_word(line):
    line = STR(line)
    line = line.lstrip(' ')
    command = ''
    if line:
        command = line.split(' ')[0]
    return command


def split_command_args(command):
    command = STR(command)
    
    return [x.strip() for x in command.split(' ') if x.strip()]

def ucs_fuzzy_complement(p, s):
    p = p.lstrip()
    s = s.lstrip(' ')
    if p and s and '\n' not in p:
        if s.startswith(p): return s[len(p):]
        # serail console will flush a '\r' when one line console buffer is overflowed
        if p.count('\r') == 1:
            left, right = p.split('\r')
            rlen = len(right)
            if s.startswith(left) and rlen >= 2:
                rsub = s[len(left):]
                rpos = rsub.find(right)
                if rpos > -1: return rsub[rpos+rlen:]
                cursor = 1
                while cursor <= rlen - 1:
                    rleft = right[:cursor]
                    rright = right[cursor:]
                    if rsub.startswith(rright) and left[::-1].startswith(rleft[::-1]):
                        return rsub[len(rright):]
                    cursor += 1
    return ''


def ucs_output_search_command(cmd, out):
    cmd = cmd.strip()
    out = out.lstrip()
    if not cmd or not out: return False
    if out.startswith(cmd): return True

    cmdpos = linepos = 0
    cmdlen = len(cmd)
    linelen = len(out)
    reversecheck = False
    while 0 <= cmdpos < cmdlen and linepos < linelen:
        if cmd[cmdpos] == out[linepos]:
            cmdpos += 1
            linepos += 1
        else:
            if out[linepos] == '\r':
                linepos += 1
                reversecheck = True
            elif out[linepos] == ' ' and out[linepos+1] == '\r':
                linepos += 2
                reversecheck = True
            elif reversecheck:
                cmdpos -= 1
            else:
                break

    return (cmdpos == cmdlen)


#def ucs_output_search_command(cmd, out):
#    sep = '\r\n' if '\r\n' in out else '\n'
#    cmd = cmd.strip()
#    out = out.lstrip()
#
#    if out.startswith(cmd): return True
#
#    parts = out.split(sep)[0].split('\r')
#    if not parts: return False
#
#    parts_pos = []
#    for part in parts:
#        part_pos = find_line_part(part, cmd)
#        if part_pos is None:
#            return False
#        parts_pos.append(part_pos)
#
#
#
#def find_line_part(part, line):
#    pos = line.find(part)
#    while pos < 0 and part[-1] == ' ':
#        part = part[:-1]
#        pos = line.find(part)
#
#    if pos < 0: return None
#
#    return (pos, pos+len(part))
#

def ucs_dupsubstr_verify(s):
    s = s.strip(' ')
    if s and len(s) >= 4:
        pos = len(s)//2 - 2
        mid = (len(s)-1)//2
        left = s[:pos].strip(' ')
        right = s[pos:].strip(' ')
        while -3 <= (pos - mid) <= 3:
            if left and right and left == right:
                return True
            pos += 1
            left = s[:pos].strip(' ')
            right = s[pos:].strip(' ')

    return False


def reversed_find_term(startpos, p, s):
    cursor = startpos + len(p)
    slen = len(s)
    while cursor < slen:
        if s[cursor] in ' \r\n': cursor += 1
        else: break

    return (cursor - slen)


def sequence_item_split(line, delimiter=';'):
    line = STR(line).strip(delimiter)
    items = [item for item in line.split(delimiter) if item]

    # parse items containing escape charater
    cur = len(items) - 1
    while cur >= 0:
        cur = cur - 1
        if ord(items[cur][-1]) == 92:
            items[cur] = items[cur][0:-1] + delimiter + items[cur+1]
            del items[cur+1]

    return items


def local_exec(cmd, timeout=None):
    with Popen(cmd.strip(), stdout=PIPE, stderr=PIPE, shell=True, close_fds=(os.name=='posix')) as process:
        timeout = timeout if timeout and timeout > 0 else None
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            if subprocess._mswindows:
                exc.stdout, exc.stderr = process.communicate()
            else:
                process.wait()
            raise TimeoutError(msg='Command exceeded time limit: %rsec' %(timeout))
        except:
            process.kill()
            raise

    return STR(stdout), STR(stderr)


def fix_seqfile_path(filename):
    """fix given sequence file's path"""
    this_worker = worker.get_this_worker()
    if this_worker and os.sep not in filename:
        this_seqfile = this_worker.seq_file
        filename = this_seqfile[:this_seqfile.rfind(os.sep)+1] + filename
    if filename.startswith('.' + os.sep):
        filename = TOPDIR + filename[1:]

    return filename


def split_text_by_delimiter(text, delimiter=' '):
    escape = '\\' + delimiter
    text.replace(escape, chr(128))
    splits = [x for x in text.split(delimiter) if x]
    for i, sp in enumerate(splits):
        splits[i] = sp.replace(chr(128), delimiter)

    return splits


def magic_search(p, s, find=False):
    if not p: return -1 if find else False
    # find, return match position
    if find:
        pos = s.find(p)
        if pos < 0:
            try:
                pos = re.search(p, s, re.M).start()
            except:
                pass
        return pos
    # search, return True/False existence
    if p in s: return True
    try:
        return (re.search(p, s, re.M | re.I) is not None)
    except:
        return False


# method that strips all ansi escapes.
def strip_ansi_escapes(text):
    if text and isinstance(text, type('')):
        text = strip_ansi_escapes.ANSI_ESCAPES.sub('', text)
    return text
# 7-bit C1 ANSI sequences
strip_ansi_escapes.ANSI_ESCAPES = re.compile(r'''
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
''', re.VERBOSE)


def new_log_path(sequence='', suffix=''):
    now = datetime.datetime.now().strftime('%b-%d-%H%M-%G')
    if not sequence: sequence = 'unknown'
    sequence = sequence.split('.')[0]

    if in_search('failure', suffix): base = './log/failure'
    elif in_search('errordump', suffix): base = './log/errordump'
    else: base = './log'

    if suffix: logpath = '%s/%s_%s_%s.log' %(base, now, sequence, suffix)
    else: logpath = '%s/%s_%s.log' %(base, now, sequence)

    return logpath


def new_uds_name(sequence=''):
    suffix = sequence.split(os.sep)[-1].split('.')[0]
    if suffix:
        uds_name = './.uds_' + suffix + '.sock'
    else:
        uds_name = './.uds.sock'

    if os.path.exists(uds_name):
        now = datetime.datetime.now().strftime('%b-%d-%H%M%S')
        uds_name = './.uds_' + suffix + '_' + now + '.sock'

    return uds_name


def time2sec(t):
    rates = {
        'h': 3600,
        'm': 60,
        's': 1,
        }

    t = t.strip().lower()
    t_list = re.findall(r"[^\W\d_]|\d*\.?\d+", t)

    t_len = len(t_list)
    t_index = 1
    seconds = 0.0
    while t_index < t_len:
        if t_list[t_index].isalpha():
            try:
                coeffi = float(t_list[t_index-1])
                seconds += coeffi*rates[t_list[t_index][0]]
            except ValueError:
                pass
        t_index += 1

    try:
        sec = float(t_list[-1])
        seconds += sec
    except ValueError:
        pass

    return int(seconds) if seconds > 0 else 0


def text_strip_date(text):
    regex = r"[A-Za-z]{3} [A-Za-z]{3} \d{2} \d{2}:\d{2}:\d{2} "
    text = STR(text)

    match = re.search(regex, text)
    if match is not None:
        text = text[match.end():]

    return text
