# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from openerp import models
from openerp.exceptions import AccessDenied

_logger = logging.getLogger(__name__)

class AutoVacuum(models.TransientModel):
    """ Expose the vacuum method to the cron jobs mechanism. """
    _name = 'ir.autovacuum'


    def _gc_transient_models(self, cr, uid, *args, **kwargs):
        for model in self.pool.itervalues():
            if model.is_transient():
                model._transient_vacuum(cr, uid, force=True)

    def _gc_user_logs(self, cr, uid, *args, **kwargs):
        cr.execute("""
            DELETE FROM res_users_log log1 WHERE EXISTS (
                SELECT 1 FROM res_users_log log2
                WHERE log1.create_uid = log2.create_uid
                AND log1.create_date < log2.create_date
            )
        """)
        _logger.info("GC'd %d user log entries", cr.rowcount)

    def power_on(self, cr, uid, *args, **kwargs):
        if not self.pool['res.users']._is_admin(cr, uid, [uid]):
            raise AccessDenied()
        self._gc_transient_models(cr, uid, *args, **kwargs)
        self._gc_user_logs(cr, uid, *args, **kwargs)
        return True
