# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _run_scheduler_alert_date_exceeded(self, use_new_cursor=False):
        self.env['stock.lot']._alert_date_exceeded()
        if use_new_cursor:
            self.env['ir.cron']._commit_progress(1)

    @api.model
    def run_scheduler_alert_date_exceeded(self, use_new_cursor=False):
        """This scheduler checks for product lots whose alert date has been reached
        and schedules a reminder activity to notify responsible users.
        """
        try:
            self._run_scheduler_alert_date_exceeded(use_new_cursor=use_new_cursor)
        except Exception:
            _logger.exception("An error occurred while the product lot expiry alert scheduler.")
            raise
