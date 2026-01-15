from odoo import api, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.depends('is_nilvera_journal', 'l10n_tr_nilvera_api_key', 'type')
    def _compute_show_fetch_in_einvoices_button(self):
        # EXTENDS 'account'
        super()._compute_show_fetch_in_einvoices_button()
        self.filtered(
            lambda j: j.is_nilvera_journal and
                      j.l10n_tr_nilvera_api_key and
                      j.type == 'purchase'
        ).show_fetch_in_einvoices_button = True

    @api.depends('l10n_tr_nilvera_api_key', 'type')
    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(
            lambda j: j.l10n_tr_nilvera_api_key and
                      j.type == 'sale'
        ).show_refresh_out_einvoices_status_button = True

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        """ Fetches bills from Nilvera."""
        super().button_fetch_in_einvoices()
        self.env['account.move']._cron_nilvera_get_new_einvoice_purchase_documents()

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        super().button_refresh_out_einvoices_status()
        self.env['account.move']._cron_nilvera_get_invoice_status()
