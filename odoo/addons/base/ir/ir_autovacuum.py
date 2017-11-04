# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AutoVacuum(models.AbstractModel):
    """ Expose the vacuum method to the cron jobs mechanism. """
    _name = 'ir.autovacuum'

    @api.model
    def _gc_transient_models(self):
        for mname in self.env:
            model = self.env[mname]
            if model.is_transient():
                model._transient_vacuum(force=True)

    @api.model
    def _gc_user_logs(self):
        self._cr.execute("""
            DELETE FROM res_users_log log1 WHERE EXISTS (
                SELECT 1 FROM res_users_log log2
                WHERE log1.create_uid = log2.create_uid
                AND log1.create_date < log2.create_date
            )
        """)
        _logger.info("GC'd %d user log entries", self._cr.rowcount)

    @api.model
    def power_on(self, *args, **kwargs):
        self.env['ir.attachment']._file_gc()
        self._gc_transient_models()
        self._gc_user_logs()
        return True
