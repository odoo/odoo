from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _compute_show_fetch_in_einvoices_button(self):
        # EXTENDS 'account'
        super()._compute_show_fetch_in_einvoices_button()
        if journal := (
            self.company_id.l10n_it_edi_purchase_journal_id
            or self.filtered(lambda x: x.type == 'purchase')[:1]
        ):
            journal.show_fetch_in_einvoices_button = True

    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        if journals := (self.filtered(lambda j:
            j.type == 'sale'
            and j.company_id.l10n_it_edi_proxy_user_id
        )):
            journals.show_refresh_out_einvoices_status_button = True

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        super().button_fetch_in_einvoices()
        self.env['account.move']._l10n_it_edi_download_invoices(self.company_id.l10n_it_edi_proxy_user_id)

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        super().button_refresh_out_einvoices_status()
        self.env['account.move']._l10n_it_edi_update_all_send_state(domain=[('journal_id', '=', self.id)])
