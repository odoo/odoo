from odoo import models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def create_document_from_attachment(self, attachment_ids=None):
        """ When running an action on several documents, this method is called
            in a loop (because of the "multi" server action). When it is the
            case, we try to redirect to a list of all created journal entries
            instead of just the last one, using the context. """

        action = super().create_document_from_attachment(attachment_ids)
        documents_active_ids = self.env.context.get('documents_active_ids', [])
        if self.env.context.get('active_model') != 'documents.document' or len(documents_active_ids) <= 1:
            return action

        account_move_ids = self.env['documents.document'].browse(documents_active_ids).mapped('res_id')
        action.update({
            'name': _("Generated Bank Statements") if action.get('res_model', '') == 'account.bank.statement' else action.get('name', ''),
            'domain': [('id', 'in', account_move_ids)],
            'views': [[False, 'list'], [False, 'kanban'], [False, 'form']],
            'view_mode': 'list,kanban,form',
        })
        return action
