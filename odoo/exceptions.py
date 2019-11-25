# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""The Odoo Exceptions module defines a few core exception types.

Those types are understood by the RPC layer.
Any other exception type bubbling until the RPC layer will be
treated as a 'Server error'.

.. note::
    If you consider introducing new exceptions,
    check out the :mod:`odoo.addons.test_exceptions` module.
"""

import logging

_logger = logging.getLogger(__name__)


class OdooException(Exception):

    def __init__(self, *args, **kwargs):
        """
        Base exception for all Odoo-related exceptions, shouldn't be instantiated manually.

        :param List[str] args: args[0] is a message to display whereas args[1:] are assumed to be
            arguments to interpolate into the message.
        :param kwargs: any "technical" arguments that may be necessary for post-processing of
            the error but are not necessary to display the message and thus won't be interpolated
            into it.
        """
        # TODO: def __init__(self, message, *args, **kwargs) ?
        if type(self) is OdooException:
            raise NotImplementedError("OdooException should not be manually instanced")
        super().__init__(*args)
        self.kwargs = kwargs

    def __str__(self):
        return self.args[0] % tuple(self.args[1:])

    def __getattr__(self, key):
        try:
            return self.kwargs[key]
        except KeyError:
            raise AttributeError


class UserError(OdooException):
    """Used for invalid user-submitted input"""
    pass


class RedirectWarning(OdooException):
    """ Warning with a possibility to redirect the user instead of simply
    displaying the warning message.

    :param int act_id: id of the action where to perform the redirection
    :param str label: text to put on the button that will trigger the redirection.
    """
    def __init__(self, message, *args, act_id, label):
        super().__init__(message, *args, act_id=act_id, label=label)


class AccessDenied(OdooException):
    """Login/password error.

    .. note::

        No traceback.

    .. admonition:: Example

        When you try to log with a wrong password.
    """

    def __init__(self, message='Access denied', *args):
        super().__init__(message, *args)
        self.with_traceback(None)
        self.__cause__ = None
        self.traceback = ('', '', '')


class AccessError(OdooException):
    """ Access rights error.
    Example: When you try to read a record that you are not allowed to."""
    pass


class MissingError(OdooException):
    """ Missing record(s).
    Example: When you try to write on a deleted record."""
    pass


class ValidationError(OdooException):
    """ Violation of python constraints
    Example: When you try to create a new user with a login which already exist in the db."""
    pass


class CacheMiss(KeyError):
    """ Missing value(s) in cache.
    Example: When you try to read a value in a flushed cache."""
    pass


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
