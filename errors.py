from os import linesep as newline


# Exceptions that will block or impact test.
class SequenceError(Exception): pass
'''Test sequence related errors'''


class PtyProcessError(Exception): pass
"""Generic error class for this package."""


class RecoveryError(Exception): pass
"""Recover failed after retry."""


class SendIncorrectCommand(Exception):
    """Incorrect sending command."""
    def __init__(self, *args, **kw):
        super(SendIncorrectCommand, self).__init__(*args)
        self.prompt = kw.get('prompt')
        self.output = kw.get('output')

    def __repr__(self):
        rpr = 'Sending Command Not Found: '
        rpr = rpr + (self.args[0] if self.args else 'NULL') + newline
        if self.prompt:
            rpr = rpr + 'SHELL PROMPT:' + newline + self.prompt + newline + newline
        if self.output:
            rpr = rpr + 'READ OUTPUT:' + newline + self.output + newline
        return rpr


class ErrorTryAgain(Exception):
    """Notify that should try again."""
    def __init__(self, *args, **kw):
        super(ErrorTryAgain, self).__init__(*args)
        self.prompt = kw.get('prompt')
        self.output = kw.get('output')

    def __repr__(self):
        rpr = 'Error Try Again: '
        rpr = rpr + (self.args[0] if self.args else 'NULL') + newline
        if self.prompt:
            rpr = rpr + 'SHELL PROMPT:' + newline + self.prompt + newline + newline
        if self.output:
            rpr = rpr + 'READ OUTPUT:' + newline + self.output + newline
        return rpr


class InvalidCommand(Exception):
    '''Invalid Command.'''
    def __init__(self, *args, **kw):
        super(InvalidCommand, self).__init__(*args)
        self.prompt = kw.get('prompt')
        self.output = kw.get('output')

    def __repr__(self):
        rpr = 'Invalid Command: '
        rpr = rpr + (self.args[0] if self.args else 'NULL') + newline
        if self.prompt:
            rpr = rpr + 'SHELL PROMPT:' + newline + self.prompt + newline + newline
        if self.output:
            rpr = rpr + 'READ OUTPUT:' + newline + self.output + newline
        return rpr


#class ContextError(Exception):
#    '''Nested connections related errors, we called it Context.'''
#    def __init__(self, *args, **kw):
#        super(ContextError, self).__init__(*args)
#        self.prompt = kw.get('prompt')
#        self.output = kw.get('output')
#
#    def __repr__(self):
#        rpr = 'Context Error: '
#        rpr = rpr + (self.args[0] if self.args else 'NULL') + newline
#        if self.prompt:
#            rpr = rpr + 'SHELL PROMPT:' + newline + self.prompt + newline + newline
#        if self.output:
#            rpr = rpr + 'READ OUTPUT:' + newline + self.output + newline
#        return rpr
#

class ExpectFailure(Exception):
    '''Failed to probe the expect-items.'''
    def __init__(self, *args, **kw):
        super(ExpectError, self).__init__(*args)
        self.prompt = kw.get('prompt')
        self.output = kw.get('output')

    def __repr__(self):
        rpr = 'Expect Error: '
        rpr = rpr + (self.args[0] if self.args else 'NULL') + newline
        if self.prompt:
            rpr = rpr + 'SHELL PROMPT:' + newline + self.prompt + newline + newline
        if self.output:
            rpr = rpr + 'READ OUTPUT:' + newline + self.output + newline + newline
        return rpr


class TimeoutError(Exception):
    """Command timeout errors."""
    def __init__(self, *args, **kw):
        super(TimeoutError, self).__init__(*args)
        self.prompt = kw.get('prompt')
        self.output = kw.get('output')

    def __repr__(self):
        rpr = 'Timeout Error: '
        rpr = rpr + (self.args[0] if self.args else 'NULL') + newline
        if self.prompt:
            rpr = rpr + 'SHELL PROMPT:' + newline + self.prompt + newline + newline
        if self.output:
            rpr = rpr + 'READ OUTPUT:' + newline + self.output + newline
        return rpr

class BuiltinCmdError(Exceptions): pass
"""Builtin command errors."""
