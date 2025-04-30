from odoo import models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.depends('is_nilvera_journal', 'l10n_tr_nilvera_api_key', 'type')
    def _compute_show_fetch_in_einvoices_button(self):
        # EXTENDS 'account'
        super()._compute_show_fetch_in_einvoices_button()
        self.filtered(
            lambda j: j.is_nilvera_journal and
                      j.l10n_tr_nilvera_api_key and
                      j.l10n_tr_nilvera_api_key.raw_value and
                      j.type == 'purchase'
        ).show_fetch_in_einvoices_button = True

    @api.depends('l10n_tr_nilvera_api_key', 'type')
    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(
            lambda j: j.l10n_tr_nilvera_api_key and
                      j.l10n_tr_nilvera_api_key.raw_value and
                      j.type == 'sale'
        ).show_refresh_out_einvoices_status_button = True

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        super().button_fetch_in_einvoices()
        self.env['account.move']._l10n_tr_nilvera_get_documents()

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        """ Gets the status from Nilvera for all processing invoices in this journal. """
        super().button_refresh_out_einvoices_status()
        invoices_to_update = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('l10n_tr_nilvera_send_status', 'in', ['waiting', 'sent']),
        ])
        invoices_to_update._l10n_tr_nilvera_get_submitted_document_status()
