# encoding: utf-8

import time

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning

class account_cashbox_line(models.Model):
    """ Cash Box Details """
    _name = 'account.cashbox.line'
    _description = 'CashBox Line'
    _rec_name = 'coin_value'
    _order = 'coin_value'

    @api.one
    @api.depends('coin_value', 'number_opening', 'number_closing')
    def _sub_total(self):
        """ Calculates Sub total"""
        self.subtotal_opening = self.coin_value * self.number_opening
        self.subtotal_closing = self.coin_value * self.number_closing

    coin_value = fields.Float(string='Unit of Currency', digits=dp.get_precision('Account'))
    number_opening = fields.Integer(string='Number of Units', help='Opening Unit Numbers')
    number_closing = fields.Integer(string='Number of Units', help='Closing Unit Numbers')
    subtotal_opening = fields.Float(compute='_sub_total', string='Opening Subtotal', digits=dp.get_precision('Account'))
    subtotal_closing = fields.Float(compute='_sub_total', string='Closing Subtotal', digits=dp.get_precision('Account'))
    cash_statement_id = fields.Many2one('account.cash.statement', string='Bank Statement', ondelete='cascade')

class account_cash_statement(models.Model):
    _name = 'account.cash.statement'
    _inherits = {'account.bank.statement': 'statement_id'}

    statement_id = fields.Many2one('account.bank.statement', string='Bank Statement', required=True, ondelete='cascade')
    details_ids = fields.One2many('account.cashbox.line', 'cash_statement_id', string='CashBox Lines', copy=True)
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    cash_control = fields.Boolean(related='statement_id.journal_id.cash_control', string='Cash control')

    @api.model
    def _get_cash_open_box_lines(self, journal_id):
        details_ids = []
        if not journal_id:
            return details_ids
        journal = self.env['account.journal'].browse(journal_id)
        if journal and (journal.type == 'cash'):
            last_coin_value = None

            if journal.with_last_closing_balance == True:
                domain = [('journal_id', '=', journal.id),
                          ('state', '=', 'confirm')]
                last_bank_statement = self.search(domain, limit=1, order='create_date desc')
                if last_bank_statement:

                    last_coin_value = dict(
                        (line.coin_value, line.number_closing) for line in last_bank_statement.details_ids
                    )
            for value in journal.cashbox_line_ids:
                nested_values = {
                    'number_closing' : 0,
                    'number_opening' : last_coin_value.get(value.coin_value, 0) if isinstance(last_coin_value, dict) else 0,
                    'coin_value' : value.coin_value
                }
                details_ids.append([0, False, nested_values])
        return details_ids


    @api.multi
    def button_confirm_cash(self):

        TABLES = ((_('Profit'), 'profit_account_id'), (_('Loss'), 'loss_account_id'),)

        for statement in self:
            if statement.difference == 0.0:
                continue
            elif statement.difference < 0.0:
                account = statement.journal_id.loss_account_id
                name = _('Loss')
                if not statement.journal_id.loss_account_id:
                    raise Warning(_('There is no Loss Account on the journal %s.') % (statement.journal_id.name,))
            else: # statement.difference > 0.0
                account = statement.journal_id.profit_account_id
                name = _('Profit')
                if not statement.journal_id.profit_account_id:
                    raise Warning(_('There is no Profit Account on the journal %s.') % (statement.journal_id.name,))

            values = {
                'statement_id' : statement.id,
                'journal_id' : statement.journal_id.id,
                'account_id' : account.id,
                'amount' : statement.difference,
                'name' : name,
            }
            self.env['account.bank.statement.line'].create(values)

        return super(account_cash_statement, self).button_confirm_bank()


class account_journal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _default_cashbox_line_ids(self):
        result = [
            dict(coin_value=value) for value in [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
        ]
        return result

    # Fields related to bank or cash registers
    profit_account_id = fields.Many2one('account.account', string='Profit Account', domain=[('deprecated', '=', False)])
    loss_account_id = fields.Many2one('account.account', string='Loss Account', domain=[('deprecated', '=', False)])
    internal_account_id = fields.Many2one('account.account', string='Internal Transfers Account', index=True, domain=[('deprecated', '=', False)])
    cash_control = fields.Boolean(string='Cash Control', default=False,
        help='If you want the journal should be control at opening/closing, check this option')
    with_last_closing_balance = fields.Boolean(string='Opening With Last Closing Balance', default=True,
        help="For cash or bank journal, this option should be unchecked when the starting balance should always set to 0 for new documents.")

    cashbox_line_ids = fields.One2many('account.journal.cashbox.line', 'journal_id',
        string='CashBox', copy=True, default=lambda self: self._default_cashbox_line_ids())


class account_journal_cashbox_line(models.Model):
    _name = 'account.journal.cashbox.line'
    _rec_name = 'coin_value'
    _order = 'coin_value asc'

    coin_value = fields.Float(string='Values', digits=dp.get_precision('Account'))
    journal_id = fields.Many2one('account.journal', string='Journal', 
        required=True, index=True, ondelete="cascade")
