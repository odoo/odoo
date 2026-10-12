import logging
from functools import wraps

from odoo import models

_logger = logging.getLogger(__name__)


def after_commit(func):
    """ Decorator postponing the call of a model method until the current transaction is committed.

    This is useful when the method has side effects outside of the database (e.g. sending an invoice
    to the government), to make sure the records it works on are correctly stored in the database first.
    The method is called in a new cursor, with all the records given as arguments bound to it.
    Errors are logged, not raised, as the transaction that triggered the call is already committed.
    If committing is not allowed (e.g. during tests), the method is called directly.
    """
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        if self.env['account.move']._can_commit():
            @self.env.cr.postcommit.add
            def called_after():
                try:
                    with self.env.registry.cursor() as cr:
                        def with_cr(value):
                            if isinstance(value, models.BaseModel):
                                return value.with_env(value.env(cr=cr))
                            return value

                        func(
                            with_cr(self),
                            *(with_cr(arg) for arg in args),
                            **{key: with_cr(value) for key, value in kwargs.items()},
                        )
                except Exception:
                    _logger.exception("Error in post-commit call of %s(%s, %s, %s)", func.__qualname__, self, args, kwargs)
        else:
            func(self, *args, **kwargs)
    return wrapped
