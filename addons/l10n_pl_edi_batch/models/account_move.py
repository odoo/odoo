from odoo import api, models

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _cron_l10n_pl_edi_download_bills(self):
        self.env['l10n_pl_edi_batch.download']._cron_request_today()

    def action_l10n_pl_edi_import_from_ksef(self):
        # Request yesterday and today's bills: the batch crons then import them
        self.env['l10n_pl_edi_batch.download'].sudo()._request_today(self.env.company)

        # Only do half-fetched invoices
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
