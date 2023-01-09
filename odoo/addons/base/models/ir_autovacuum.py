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
            cls = type(model)
            for attr, func in inspect.getmembers(cls, is_autovacuum):
                _logger.debug('Calling %s.%s()', model, attr)
                try:
                    func(model)
                    self.env.cr.commit()
                except Exception:
                    _logger.exception("Failed %s.%s()", model, attr)
                    self.env.cr.rollback()
