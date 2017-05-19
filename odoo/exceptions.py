# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" OpenERP core exceptions.

This module defines a few exception types. Those types are understood by the
RPC layer. Any other exception type bubbling until the RPC layer will be
treated as a 'Server error'.

If you consider introducing new exceptions, check out the test_exceptions addon.
"""

import logging
from inspect import currentframe
from .tools.func import frame_codeinfo

_logger = logging.getLogger(__name__)


# kept for backward compatibility
class except_orm(Exception):
    def __init__(self, name, value=None):
        if type(self) == except_orm:
            caller = frame_codeinfo(currentframe(), 1)
            _logger.warn('except_orm is deprecated. Please use specific exceptions like UserError or AccessError. Caller: %s:%s', *caller)
        self.name = name
        self.value = value
        self.args = (name, value)


class UserError(except_orm):
    def __init__(self, msg):
        super(UserError, self).__init__(msg)


# deprecated due to collision with builtins, kept for compatibility
Warning = UserError


class RedirectWarning(Exception):
    """ Warning with a possibility to redirect the user instead of simply
    diplaying the warning message.

    Should receive as parameters:
      :param int action_id: id of the action where to perform the redirection
      :param string button_text: text to put on the button that will trigger
          the redirection.
    """


class AccessDenied(Exception):
    """ Login/password error. No message, no traceback.
    Example: When you try to log with a wrong password."""
    def __init__(self):
        super(AccessDenied, self).__init__('Access denied')
        self.traceback = ('', '', '')


class AccessError(except_orm):
    """ Access rights error.
    Example: When you try to read a record that you are not allowed to."""
    def __init__(self, msg):
        super(AccessError, self).__init__(msg)


class MissingError(except_orm):
    """ Missing record(s).
    Example: When you try to write on a deleted record."""
    def __init__(self, msg):
        super(MissingError, self).__init__(msg)


class ValidationError(except_orm):
    """ Violation of python constraints
    Example: When you try to create a new user with a login which already exist in the db."""
    def __init__(self, msg):
        super(ValidationError, self).__init__(msg)


class DeferredException(Exception):
    """ Exception object holding a traceback for asynchronous reporting.

    Some RPC calls (database creation and report generation) happen with
    an initial request followed by multiple, polling requests. This class
    is used to store the possible exception occuring in the thread serving
    the first request, and is then sent to a polling request.

    ('Traceback' is misleading, this is really a exc_info() triple.)
    """
    def __init__(self, msg, tb):
        self.message = msg
        self.traceback = tb


class QWebException(Exception):
    pass
