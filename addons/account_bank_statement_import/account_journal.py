# -*- coding: utf-8 -*-

from openerp import models, fields, api

class AccountJournal(models.Model):
    _inherit = "account.journal"

    bank_statements_source = fields.Selection(selection_add=[("file_import", "File Import")])

    @api.multi
    def import_statement(self):
        """return action to import bank/cash statements. This button should be called only on journals with type =='bank'"""
        model = 'account.bank.statement'
        action_name = 'action_account_bank_statement_import'
        ir_model_obj = self.pool['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'account_bank_statement_import', action_name)
        action = self.pool[model].read(self._cr, self._uid, [action_id], context=self.env.context)[0]
        # Note: this drops action['context'], which is a dict stored as a string, which is not easy to update
        action.update({'context': (u"{'journal_id': " + str(self.id) + u"}")})
        return action
