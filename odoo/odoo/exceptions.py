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

import warnings


class UserError(Exception):
    """Generic error managed by the client.

    Typically when the user tries to do something that has no sense given the current
    state of a record. Semantically comparable to the generic 400 HTTP status codes.
    """

    def __init__(self, message):
        """
        :param message: exception message and frontend modal content
        """
        super().__init__(message)


class RedirectWarning(Exception):
    """ Warning with a possibility to redirect the user instead of simply
    displaying the warning message.

    :param str message: exception message and frontend modal content
    :param int action_id: id of the action where to perform the redirection
    :param str button_text: text to put on the button that will trigger
        the redirection.
    :param dict additional_context: parameter passed to action_id.
           Can be used to limit a view to active_ids for example.
    """
    def __init__(self, message, action, button_text, additional_context=None):
        super().__init__(message, action, button_text, additional_context)

    # using this RedirectWarning won't crash if used as an UserError
    @property
    def name(self):
        warnings.warn(
            "RedirectWarning attribute 'name' is a deprecated alias to args[0]",
            DeprecationWarning)
        return self.args[0]


class AccessDenied(UserError):
    """Login/password error.

    .. note::

        No traceback.

    .. admonition:: Example

        When you try to log with a wrong password.
    """

    def __init__(self, message="Access Denied"):
        super().__init__(message)
        self.with_traceback(None)
        self.__cause__ = None
        self.traceback = ('', '', '')


class AccessError(UserError):
    """Access rights error.

    .. admonition:: Example

        When you try to read a record that you are not allowed to.
    """


class CacheMiss(KeyError):
    """Missing value(s) in cache.

    .. admonition:: Example

        When you try to read a value in a flushed cache.
    """

    def __init__(self, record, field):
        super().__init__("%r.%s" % (record, field.name))


class MissingError(UserError):
    """Missing record(s).

    .. admonition:: Example

        When you try to write on a deleted record.
    """


class ValidationError(UserError):
    """Violation of python constraints.

    .. admonition:: Example

        When you try to create a new user with a login which already exist in the db.
    """
