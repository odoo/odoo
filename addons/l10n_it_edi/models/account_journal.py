from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _compute_show_fetch_in_einvoices_button(self):
        super()._compute_show_fetch_in_einvoices_button()
        self.filtered(
            lambda journal: (
                journal == journal.company_id.l10n_it_edi_purchase_journal_id
                or journal.type == 'purchase'
        )).show_fetch_in_einvoices_button = True

    def _compute_show_refresh_out_einvoices_status_button(self):
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(
            lambda journal: journal.type == 'sale' and journal.company_id.l10n_it_edi_proxy_user_id,
        ).show_refresh_out_einvoices_status_button = True

    def button_refresh_out_einvoices_status(self):
        super().button_refresh_out_einvoices_status()
        for proxy_user in self.company_id.l10n_it_edi_proxy_user_id.filtered(
            lambda p: p.edi_mode != 'demo',
        ):
            self.env['account.move'].with_company(proxy_user.company_id)._l10n_it_edi_check_send_state()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def button_fetch_in_einvoices(self):
        super().button_fetch_in_einvoices()
        for proxy_user in self.company_id.l10n_it_edi_proxy_user_id.filtered(
            lambda p: p.edi_mode != 'demo',
        ):
            self.env['account.move']._l10n_it_edi_download_invoices(proxy_user)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
