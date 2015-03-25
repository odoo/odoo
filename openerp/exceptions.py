# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

""" OpenERP core exceptions.

This module defines a few exception types. Those types are understood by the
RPC layer. Any other exception type bubbling until the RPC layer will be
treated as a 'Server error'.

If you consider introducing new exceptions, check out the test_exceptions addon.
"""

from inspect import currentframe
import logging
from tools.func import frame_codeinfo

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
        self.name = msg
        self.args = (msg,)


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
