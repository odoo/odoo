from odoo import api, models

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _cron_l10n_pl_edi_download_bills(self):
        Batch = self.env['l10n_pl_edi_batch.download']
        if Batch._is_enabled():
            Batch._cron_request_today()
        else:
            super()._cron_l10n_pl_edi_download_bills()

    def action_l10n_pl_edi_import_from_ksef(self):
        """ With batches enabled, the crons download the new bills: the action only fills the bills the
            single-invoice download left half-fetched (fetch_ready, fetch_failed), one by one by KSeF number. """
        if not self.env['l10n_pl_edi_batch.download']._is_enabled():
            return super().action_l10n_pl_edi_import_from_ksef()
        half_fetched_bills = self.search([
            ('l10n_pl_edi_number', '!=', False),
            ('move_type', '=', 'in_invoice'),
            ('l10n_pl_edi_status', 'in', ('fetch_ready', 'fetch_failed')),
            *self._check_company_domain(self.env.company),
        ])
        self._fetch_bills_data(KsefApiService(self.env.company), half_fetched_bills)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
