
# Exceptions that will block or impact test.
class SequenceError(Exception): pass
'''Test sequence related errors'''


class PtyProcessError(Exception): pass
"""Generic error class for this package."""


class RecoveryError(Exception): pass
"""Recover failed after retry."""


class AgentBaseError(Exception):
    def __init__(self, *args, **kw):
        super().__init__(*args)
        self.prompt = kw.get('prompt')
        self.output = kw.get('output')

    def __str__(self):
        s = '%s: %s\n' + %(self.__class__.__name__, self.args[0] if self.args else 'NULL')
        if self.prompt:
            s = s + 'SHELL PROMPT:\n%s\n\n' %(self.prompt)
        if self.output:
            s = s + 'READ OUTPUT:\n%s\n' %(self.output)
        return s

    def __repr__(self):
        return self.__str__()


class SendIncorrectCommand(AgentBaseError): pass
"""Incorrect sending command."""

class ErrorTryAgain(AgentBaseError): pass
"""Notify that should try again."""

class InvalidCommand(AgentBaseError): pass
'''Invalid Command.'''

class ExpectFailure(AgentBaseError): pass
'''Failed to probe the expect-items.'''

class TimeoutError(AgentBaseError): pass
"""Command timeout errors."""

class BuiltinCmdError(AgentBaseError): pass
"""Builtin command errors."""
