# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models, _
from openerp.exceptions import UserError


class PosOpenStatement(models.TransientModel):
    _name = 'pos.open.statement'
    _description = 'Open Statements'

    @api.multi
    def open_statement(self):
        """
             Open the statements
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Blank Directory
        """
        self.ensure_one()
        data = {}
        Statement = self.env['account.bank.statement']
        Journal = self.env['account.journal']

        st_ids = []
        account_journal = Journal.search([('journal_user', '=', True)])
        if not account_journal:
            raise UserError(_('You have to define which payment method must be available in the point of sale by reusing existing bank and cash through "Accounting / Configuration / Journals / Journals". Select a journal and check the field "PoS Payment Method" from the "Point of Sale" tab. You can also create new payment methods directly from menu "PoS Backend / Configuration / Payment Methods".'))

        for journal in account_journal:

            if journal.sequence_id:
                number = journal.sequence_id.next_by_id()
            else:
                raise UserError(_("No sequence defined on the journal"))

            data.update({
                'journal_id': journal.id,
                'user_id': self.env.uid,
                'name': number
            })
            statement_id = Statement.create(data)
            st_ids.append(int(statement_id))

        tree_id = self.env.ref('account.view_bank_statement_tree').id or False
        form_id = self.env.ref('account.view_bank_statement_form').id or False
        search_id = self.env.ref('account.view_bank_statement_search').id or False

        return {
            'type': 'ir.actions.act_window',
            'name': _('List of Cash Registers'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.bank.statement',
            'domain': str([('id', 'in', st_ids)]),
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'search_view_id': search_id,
        }
