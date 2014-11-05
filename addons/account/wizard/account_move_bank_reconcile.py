# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class account_move_bank_reconcile(models.TransientModel):
    """
        Bank Reconciliation
    """
    _name = "account.move.bank.reconcile"
    _description = "Move bank reconcile"

    journal_id = fields.Many2one('account.journal', string='Journal', required=True)

    @api.multi
    def action_open_window(self):
        """
       @return: dictionary of  Open  account move line   on given journal_id.
        """
        data = self.read()[0]
        self._cr.execute('select default_credit_account_id \
                        from account_journal where id=%s', (data['journal_id'],))
        account_id = self._cr.fetchone()[0]
        if not account_id:
             raise Warning(_('You have to define the bank account in the journal definition for reconciliation.'))
        return {
            'domain': "[('journal_id', '=', %d), ('account_id', '=' ,%d), ('state', '!=', 'draft')]" % (data['journal_id'], account_id),
            'name': _('Standard Encoding'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'context': "{'journal_id': %d}" % (data['journal_id'],),
            'type': 'ir.actions.act_window'
        }
