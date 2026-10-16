from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _compute_show_fetch_in_einvoices_button(self):
        super()._compute_show_fetch_in_einvoices_button()
        self.filtered(
            lambda journal: (
                journal == journal.company_id.l10n_it_edi_purchase_journal_id
                and journal.company_id.l10n_it_edi_proxy_user_id
                and journal.company_id.l10n_it_edi_proxy_user_id.edi_mode != 'demo'
            ),
        ).show_fetch_in_einvoices_button = True

    def _compute_show_refresh_out_einvoices_status_button(self):
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(
            lambda journal: (
                journal.type == 'sale'
                and journal.company_id.l10n_it_edi_proxy_user_id
                and journal.company_id.l10n_it_edi_proxy_user_id.edi_mode != 'demo'
            ),
        ).show_refresh_out_einvoices_status_button = True

    def button_refresh_out_einvoices_status(self):
        super().button_refresh_out_einvoices_status()

        valid_companies = self.company_id.filtered(
            lambda c: (
                c.l10n_it_edi_proxy_user_id
                and c.l10n_it_edi_proxy_user_id.edi_mode != 'demo'
            ),
        )
        for company in valid_companies:
            self.env['account.move']._l10n_it_edi_check_send_state(company=company)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def button_fetch_in_einvoices(self):
        super().button_fetch_in_einvoices()
        self.env['account.move'].cron_l10n_it_edi_download_and_update(companies=self.company_id)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
