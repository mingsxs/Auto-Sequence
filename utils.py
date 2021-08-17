import os
import re
import sys
import datetime
import subprocess
from subprocess import Popen, PIPE

import worker
import sequence
import uds
from globs import *


PY3 = (sys.version_info[0] >= 3) # if currently we are in Python3.

def BYTES(text, encoding="utf-8", errors='strict'):
    if text is None:
        return bytes('', encoding=encoding, errors=errors)

    try:
        return bytes(text, encoding=encoding, errors=errors)
    except:
        return bytes(text)


def STR(text, encoding="utf-8", errors="ignore"):
    if text is None:
        return ''

    try:
        return text.decode(encoding, errors=errors)
    except:
        return str(text)


def split_text_lines(text):
    text = STR(text)

    return text.splitlines()


def get_text_last_line(text):
    lines = split_text_lines(text)

    lines = [line for line in lines if line]

    return lines[-1] if lines else None


def make_cmd_args(cmd):
    cmd = STR(cmd).strip()

    items = [item for item in cmd.split(' ') if item]

    return items


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

    if magic_search('failure', suffix): base = './log/failure'
    elif in_search('errordump', suffix): base = './log/errordump'
    else: base = './log'

    if suffix: logpath = '%s/%s_%s_%s.log' %(base, now, sequence, suffix)
    else: logpath = '%s/%s_%s.log' %(base, now, sequence)

    return logpath


def new_uds_path(sequence=''):
    suffix = sequence.split(os.sep)[-1].split('.')[0]
    if suffix:
        udspath = './.uds_' + suffix + '.sock'
    else:
        udspath = './.uds.sock'

    if os.path.exists(udspath):
        now = datetime.datetime.now().strftime('%b-%d-%H%M%S')
        udspath = './.uds_' + suffix + '_' + now + '.sock'

    return udspath


def convert_time(text):
    rates = {
        'h': 3600,
        'm': 60,
        's': 1,
        }

    text = text.strip().lower()
    lst = re.findall(r"[^\W\d_]|\d*\.?\d+", text)

    n = len(lst)
    i = 1
    seconds = 0.0
    while i < n:
        if lst[i].isalpha():
            try:
                coeffi = float(lst[i-1])
                seconds += coeffi*rates[lst[i][0]]
            except ValueError:
                pass
        i += 1

    try:
        sec = float(lst[-1])
        seconds += sec
    except ValueError:
        pass

    return int(seconds) if seconds > 0 else 0


def strip_text_date(text):
    rgx = r"[A-Za-z]{3} [A-Za-z]{3} \d{2} \d{2}:\d{2}:\d{2} "
    text = STR(text)

    match = re.search(rgx, text)
    if match is not None:
        text = text[match.end():]

    return text


def local_exec(cmd, timeout=None):
    with Popen(cmd.strip(), stdout=PIPE, stderr=PIPE, shell=True, close_fds=(os.name=='posix')) as p:
        timeout = timeout if timeout and timeout > 0 else None
        try:
            stdout, stderr = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            p.kill()
            if subprocess._mswindows:
                exc.stdout, exc.stderr = p.communicate()
            else:
                p.wait()
            raise TimeoutError(msg='Command exceeded time limit: %rsec' %(timeout))
        except:
            p.kill()
            raise

    return STR(stdout), STR(stderr)


def is_cisco_serial_telnet(command):
    cmd = command.args[0]
    nargs = len(command.args)

    if cmd == 'telnet' and nargs == 3:
        try:
            port = int(command.args[-1])
        except ValueError:
            return False

        if 2003 <= port <= 2035:
            return True

    return False


def concat_text_lines(*lines):
    text = ''
    for line in lines:
        text = text + STR(line) + newline

    return text
