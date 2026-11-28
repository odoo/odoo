from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def open_myinvois_document(self):
        """
        Return an action to open the MyInvois Document matching this journal.
        """
        self.ensure_one()
        return {
            'name': self.env._("MyInvois Documents"),
            'type': 'ir.actions.act_window',
            'res_model': 'myinvois.document',
            'view_mode': 'list,form',
            'domain': [('is_received_document', '=', False)],
            'search_view_id': [self.env.ref('l10n_my_edi.myinvois_document_search_view').id, 'search'],
            'views': [(self.env.ref('l10n_my_edi.myinvois_document_list_view').id, 'list'), (self.env.ref('l10n_my_edi.myinvois_document_form_view').id, 'form')],
            'context': {
                'display_consolidate_invoice_button': True,
                'journal_id': self.id,
                'search_default_journal_id': self.id,
            }
        }

    def open_myinvois_received_documents(self):
        """ Return an action to open the documents received on MyInvois in this purchase journal. """
        self.ensure_one()
        return {
            'name': self.env._("Received from MyInvois"),
            'type': 'ir.actions.act_window',
            'res_model': 'myinvois.document',
            'view_mode': 'list,form',
            'domain': [('is_received_document', '=', True)],
            'search_view_id': [self.env.ref('l10n_my_edi.myinvois_received_document_search_view').id, 'search'],
            'views': [(self.env.ref('l10n_my_edi.myinvois_received_document_list_view').id, 'list'), (self.env.ref('l10n_my_edi.myinvois_document_form_view').id, 'form')],
            'context': {
                'journal_id': self.id,
                'search_default_journal_id': self.id,
                'search_default_groupby_issuance_month': True,
            },
        }
