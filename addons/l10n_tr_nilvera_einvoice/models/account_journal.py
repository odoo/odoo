from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def l10n_tr_nilvera_get_documents(self):
        """ Fetches bills from Nilvera."""
        self.env['account.move']._cron_nilvera_get_new_einvoice_purchase_documents()

    def l10n_tr_nilvera_get_message_status(self):
        """Gets the status from Nilvera for all processing invoices in
        this journal and fetches E-Invoice, & E-Archive invoices from nilvera
        """
        invoices_to_update = self.env['account.move'].search([
            ('journal_id', '=', self.id),
            ('l10n_tr_nilvera_send_status', 'in', ['waiting', 'sent']),
        ])
        invoices_to_update._l10n_tr_nilvera_get_submitted_document_status()
        self.env['account.move']._cron_nilvera_get_new_einvoice_sale_documents()
        self.env['account.move']._cron_nilvera_get_new_earchive_sale_documents()
