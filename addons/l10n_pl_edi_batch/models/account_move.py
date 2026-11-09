from odoo import api, models

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _cron_l10n_pl_edi_download_bills(self):
        # Run the batched mode for the batched companies
        self.env['l10n_pl_edi_batch.download']._cron_request_today()

        # Run the single mode for non-batched companies
        for company in self.env['res.company'].search([
            ('l10n_pl_edi_access_token', '!=', False),
            ('l10n_pl_edi_batch_enabled', '=', False),
        ]):
            self.with_company(company)._l10n_pl_edi_download_bills_from_ksef()

    def action_l10n_pl_edi_import_from_ksef(self):
        # Run for all invoices, in non-batched companies
        if not self.env.company.l10n_pl_edi_batch_enabled:
            return super().action_l10n_pl_edi_import_from_ksef()

        # Only do half-fetched invoices, in batched companies
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
