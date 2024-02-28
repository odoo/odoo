# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
import warnings
import traceback

from odoo import api, models
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)


def is_autovacuum(func):
    """ Return whether ``func`` is an autovacuum method. """
    return callable(func) and getattr(func, '_autovacuum', False)


class AutoVacuum(models.AbstractModel):
    """ Helper model to the ``@api.autovacuum`` method decorator. """
    _name = 'ir.autovacuum'
    _description = 'Automatic Vacuum'

    def _run_vacuum_cleaner(self):
        """
        Perform a complete database cleanup by safely calling every
        ``@api.autovacuum`` decorated method.
        """
        if not self.env.is_admin():
            raise AccessDenied()

        for model in self.env.values():
            cls = self.env.registry[model._name]
            for attr, func in inspect.getmembers(cls, is_autovacuum):
                _logger.debug('Calling %s.%s()', model, attr)
                try:
                    func(model)
                    self.env.cr.commit()
                except Exception:
                    _logger.exception("Failed %s.%s()", model, attr)
                    self.env.cr.rollback()

        # Ensure backward compatibility with the previous autovacuum API
        try:
            self.power_on()
            self.env.cr.commit()
        except Exception:
            _logger.exception("Failed power_on")
            self.env.cr.rollback()

    # Deprecated API
    @api.model
    def power_on(self, *args, **kwargs):
        tb = traceback.extract_stack(limit=2)
        if tb[-2].name == 'power_on':
            warnings.warn(
                "You are extending the 'power_on' ir.autovacuum method"
                f"in {tb[-2].filename} around line {tb[-2].lineno}. "
                "You should instead use the @api.autovacuum decorator "
                "on your garbage collecting method.", DeprecationWarning, stacklevel=2)
