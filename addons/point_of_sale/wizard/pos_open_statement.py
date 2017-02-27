# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class PosOpenStatement(models.TransientModel):
    _name = 'pos.open.statement'
    _description = 'Open Statements'

    @api.multi
    def open_statement(self):
        self.ensure_one()
        BankStatement = self.env['account.bank.statement']
        journals = self.env['account.journal'].search([('journal_user', '=', True)])
        if not journals:
            raise UserError(_('You have to define which payment method must be available in the point of sale by reusing existing bank and cash through "Accounting / Configuration / Journals / Journals". Select a journal and check the field "PoS Payment Method" from the "Point of Sale" tab. You can also create new payment methods directly from menu "PoS Backend / Configuration / Payment Methods".'))

        for journal in journals:
            if journal.sequence_id:
                number = journal.sequence_id.next_by_id()
            else:
                raise UserError(_("No sequence defined on the journal"))
            BankStatement += BankStatement.create({'journal_id': journal.id, 'user_id': self.env.uid, 'name': number})

        tree_id = self.env.ref('account.view_bank_statement_tree').id
        form_id = self.env.ref('account.view_bank_statement_form').id
        search_id = self.env.ref('account.view_bank_statement_search').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('List of Cash Registers'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.bank.statement',
            'domain': str([('id', 'in', BankStatement.ids)]),
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'search_view_id': search_id,
        }
