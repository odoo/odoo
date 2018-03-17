# -*- coding: utf-8 -*-
# © 2016 ABF OSIELL <http://osiell.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from datetime import datetime, timedelta

from odoo import models, fields, api


_logger = logging.getLogger(__name__)


class AuditlogAutovacuum(models.TransientModel):
    _name = 'auditlog.autovacuum'
    _description = "Auditlog - Delete old logs"

    @api.model
    def autovacuum(self, days):
        """Delete all logs older than ``days``. This includes:
            - CRUD logs (create, read, write, unlink)
            - HTTP requests
            - HTTP user sessions

        Called from a cron.
        """
        days = (days > 0) and int(days) or 0
        deadline = datetime.now() - timedelta(days=days)
        data_models = (
            'auditlog.log',
            'auditlog.http.request',
            'auditlog.http.session',
        )
        for data_model in data_models:
            records = self.env[data_model].search(
                [('create_date', '<=', fields.Datetime.to_string(deadline))])
            nb_records = len(records)
            records.unlink()
            _logger.info(
                u"AUTOVACUUM - %s '%s' records deleted",
                nb_records, data_model)
        return True
