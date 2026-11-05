import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import str2bool

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import (
    KsefApiServiceBatch as Service,
)

KSEF_WINDOW = 30
KSEF_FIRST_DAY = fields.Date.from_string('2026-01-31')
KSEF_LOG_HEADER = "KSeF download:"

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_pl_edi_trigger(self, cron_ref, seconds=5):
        retry_at = fields.Datetime.now() + relativedelta(seconds=seconds)
        _logger.info("%s Retriggering (%s)...", KSEF_LOG_HEADER, retry_at)
        self.env.ref(cron_ref)._trigger(at=retry_at)

    @api.model
    def _l10n_pl_edi_batch_is_enabled(self):
        """ The batch download replaces the single-invoice download only when explicitly enabled. """
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        value = IrConfigParameter.get_param('l10n_pl_edi_batch.enabled', 'False')
        return str2bool(value, default=False)

    @api.model
    def _cron_l10n_pl_edi_download_bills(self):
        # The batch flow is driven from the odoo shell for now; otherwise use the single-invoice download
        if self._l10n_pl_edi_batch_is_enabled():
            _logger.info("%s l10n_pl_edi_batch.enabled found: skipping the single-invoice download", KSEF_LOG_HEADER)
            return  # TODO: XXX
            # today = fields.Date.today()
            # try:
            #     for company in self.env['res.company'].search([('l10n_pl_edi_access_token', '!=', False)]):
            #         if self._l10n_pl_edi_request_bills(company, today, today + relativedelta(days=1)):
            #             self._l10n_pl_edi_trigger('l10n_pl_edi.cron_l10n_pl_edi_download_batches')
            # except KSeFRateLimitError as e:
            #     self._l10n_pl_edi_trigger('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills', e.retry_after)
        super()._cron_l10n_pl_edi_download_bills()
