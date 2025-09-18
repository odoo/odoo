"""Logging utilities for Odoo.

This module provides utilities for:
- Temporarily suppressing log output (mute_logger)
- Temporarily lowering log levels (lower_logging)
- Special string representation (unquote)
- Custom log record formatting
"""

import logging
from functools import wraps


class unquote(str):
    """A string subclass with repr() that returns the string unquoted.

    Useful for preserving or inserting bare variable names within dicts
    during eval() of a dict's repr(). The name comes from Lisp's unquote.
    Use with care.

    Examples::

        >>> unquote('active_id')
        active_id
        >>> d = {'test': unquote('active_id')}
        >>> d
        {'test': active_id}
        >>> print(d)
        {'test': active_id}
    """

    __slots__ = ()

    def __repr__(self):
        return self


class mute_logger(logging.Handler):
    """Temporarily suppress logging output.

    Can be used as a context manager or decorator to silence specific
    loggers during test execution or when expected errors would pollute
    the log output.

    Examples::

        @mute_logger('odoo.plic.ploc')
        def do_stuff():
            blahblah()

        with mute_logger('odoo.foo.bar'):
            do_stuff()
    """

    def __init__(self, *loggers):
        """Initialize the mute_logger.

        :param loggers: Logger names to mute (e.g., 'odoo.models', 'odoo.db')
        """
        super().__init__()
        self.loggers = loggers
        self.old_params = {}

    def __enter__(self):
        for logger_name in self.loggers:
            logger = logging.getLogger(logger_name)
            self.old_params[logger_name] = (logger.handlers, logger.propagate)
            logger.propagate = False
            logger.handlers = [self]

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        for logger_name in self.loggers:
            logger = logging.getLogger(logger_name)
            logger.handlers, logger.propagate = self.old_params[logger_name]

    def __call__(self, func):
        @wraps(func)
        def deco(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return deco

    def emit(self, record):
        pass


class MungedTracebackLogRecord(logging.LogRecord):
    """Log record that modifies traceback display.

    Used by lower_logging to mark tracebacks that were logged at
    a lower level than originally intended.
    """

    def getMessage(self):
        return (
            super()
            .getMessage()
            .replace(
                "Traceback (most recent call last):",
                "_Traceback_ (most recent call last):",
            )
        )


class lower_logging(logging.Handler):
    """Temporarily lower the maximum logging level.

    Logs above max_level are reduced to to_level, allowing tests to
    verify that errors are logged without polluting test output.

    The `had_error_log` attribute can be checked after exiting to
    verify that an error was logged.

    Example::

        with lower_logging(logging.ERROR, logging.WARNING) as ll:
            # Code that logs errors...
            pass
        assert ll.had_error_log  # Verify an error was logged
    """

    def __init__(self, max_level, to_level=None):
        """Initialize the lower_logging handler.

        :param max_level: Maximum log level to allow (higher levels are reduced)
        :param to_level: Level to reduce high logs to (default: same as max_level)
        """
        super().__init__()
        self.old_handlers = None
        self.old_propagate = None
        self.had_error_log = False
        self.max_level = max_level
        self.to_level = to_level or max_level

    def __enter__(self):
        logger = logging.getLogger()
        self.old_handlers = logger.handlers[:]
        self.old_propagate = logger.propagate
        logger.propagate = False
        logger.handlers = [self]
        self.had_error_log = False
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        logger = logging.getLogger()
        logger.handlers = self.old_handlers
        logger.propagate = self.old_propagate

    def emit(self, record):
        if record.levelno > self.max_level:
            record.levelname = f"_{record.levelname}"
            record.levelno = self.to_level
            self.had_error_log = True
            if MungedTracebackLogRecord.__base__ is logging.LogRecord:
                MungedTracebackLogRecord.__bases__ = (record.__class__,)
            record.__class__ = MungedTracebackLogRecord

        if logging.getLogger(record.name).isEnabledFor(record.levelno):
            for handler in self.old_handlers:
                if handler.level <= record.levelno:
                    handler.emit(record)
