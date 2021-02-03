# newline
from os import linesep as newline

# top directory
import os
TOPDIR = os.path.dirname(__file__)

## prompts indicating login process
#R_PROMPT_LOGIN_WAIT = [r": {0,2}$",     # need to input username/passcode
#                       r"\? {0,2}$",    # need to input yes/no ?
#                       ]

# prompts indicating ready for input
R_PROMPT_INPUT_REDY = [r"\$ ?$",    # BMC linux, typically racks, and normal linux
                       r"# ?$",     # BMC linux, typically blades, CMCs, and normal linux
                       r"> ?$",     # Uefi, cisco terminal servers, switches, etc
                       ]

# regexes that can reach to a new shell
CONNECT_SH_CMDS     = ["telnet",    # telnet to a new shell env
                       "ssh",       # ssh to a new shell env
                       "connect",   # `connect host/debug-shell` in cimc utility
                       "solshell",  # `solshell` to connect host in BMC
                       ]

# regexes to quit current shell
R_SH_QUIT_CMDS      = [r"^quit$",   # `quit` command
                       r"^exit$",   # `exit` command
                       r"^ctrl.?(\]|x)$", # `ctrl-x`, `ctrl-]` to quit solshell or telnet
                       ]

# commands that doesn't need to check error message
ERR_BYPASS_CMDS     = ['rm',
                       'ls',
                       '',
                       ]

# shell command error message
CMD_ERR_MSGS        = ['command not found',         # command not found
                       'no such file or directory', # target file not found
                       'is a directory',            # invalid file type
                       'is not recognized as an internal or external command',  # command not found
                       'invalid input detected',    # invalid input
                       'invalid pass phrase',       # invalid pass phrase
                       'permission denied',         # permission denied
                       ]

# diag shell info
diagshell_info      = {
    'bmcdiag': {'name': r"udibmc_.*(\.strippped)?$",
                'exit_cmd': 'exit',
                'init_delay': 5.0,
                'terminator': r"% ?"},

    'efidiag': {'name': r"Dsh.efi$",
                'exit_cmd': 'exit',
                'init_delay': 3.0,
                'terminator': r"> ?"},

    'i2cuart': {'name': r"i2c_uart.*",
                 'exit_cmd': 'ctrl+p+d',
                 'init_delay': 0.0,
                 'terminator': r"# ?$"}
    }


DEBUG_MODE_ON = False                       # if debug mode enabled
LOGGING_ENABLED = True                      # if log is enabled
STOP_ON_FAILURE = False                     # if test stops when failure is detected
LOOP_ITERATIONS = 1                         # test loop iterations
MAIN_SEQUENCE_FILE = ''                     # entry sequence file, the sequence to start all tests

#print_window_message = True
LOCAL_SHELL_PROMPT = '>>>'                  # local shell prompt string
SESSION_CONNECT_RETRY = 3                   # session connect retry count
TEST_RECOVER_RETRY = 3                      # test recover retry count
SESSION_PROMPT_RETRY = 4                    # session prompt set/get retry count
SESSION_PROMPT_RETRY_TIMEOUT = 5            # session prompt set/get retry timeout
BUILTIN_MONITOR_INTERVAL = 3.0              # time period for builtin monitor command
PROMPT_OFFSET_RANGE = 16                    # offset range to check if prompt string is reached
BASE_SERIAL_PORT = 2003                     # base serial port for telnet connection


DELAY_AFTER_QUIT = 0.8                      # internal delay const
DELAY_BEFORE_PROMPT_FLUSH = 0.2             # internal delay const

BOOTUP_WATCH_PERIOD = 30.0                  # watch period to watch if target system is booting up
BOOTUP_WATCH_TIMEOUT = 600.0                # timeout for watching system booting up


DEFAULT_BLTINCMD_TIMEOUT = 30.0             # default timeout for builtin command
DEFAULT_SHELLCMD_TIMEOUT = 60.0             # default timeout for shell command
