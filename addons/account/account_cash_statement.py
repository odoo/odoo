# encoding: utf-8

import time

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning

class account_cashbox_line(models.Model):
    """ Cash Box Details """

    _name = 'account.cashbox.line'
    _description = 'CashBox Line'
    _rec_name = 'pieces'

    @api.multi
    @api.depends('pieces', 'number_opening', 'number_closing')
    def _sub_total(self):
        """ Calculates Sub total"""
        for line in self:
            line.subtotal_opening = line.pieces * line.number_opening
            line.subtotal_closing = line.pieces * line.number_closing

    @api.multi
    def on_change_sub_opening(self, pieces, number):
        """ Compute the subtotal for the opening """
        return {'value' : {'subtotal_opening' : (pieces * number) or 0.0 }}

    @api.multi
    def on_change_sub_closing(self, pieces, number):
        """ Compute the subtotal for the closing """
        return {'value' : {'subtotal_closing' : (pieces * number) or 0.0 }}

    pieces = fields.Float(string='Unit of Currency', digits=dp.get_precision('Account'))
    number_opening = fields.Integer(string='Number of Units', help='Opening Unit Numbers')
    number_closing = fields.Integer(string='Number of Units', help='Closing Unit Numbers')
    subtotal_opening = fields.Float(compute='_sub_total', string='Opening Subtotal', digits=dp.get_precision('Account'))
    subtotal_closing = fields.Float(compute='_sub_total', string='Closing Subtotal', digits=dp.get_precision('Account'))
    bank_statement_id = fields.Many2one('account.bank.statement', string='Bank Statement', ondelete='cascade')

class account_cash_statement(models.Model):
    _inherit = 'account.bank.statement'

    @api.multi
    def _update_balances(self):
        """
            Set starting and ending balances according to pieces count
        """
        res = {}
        for statement in self:
            if (statement.journal_id.type not in ('cash',)):
                continue
            if not statement.journal_id.cash_control:
                if statement.balance_end_real <> statement.balance_end:
                    statement.write({'balance_end_real' : statement.balance_end})
                continue
            start = end = 0
            for line in statement.details_ids:
                start += line.subtotal_opening
                end += line.subtotal_closing
            data = {
                'balance_start': start,
                'balance_end_real': end,
            }
            res[statement.id] = data
            super(account_cash_statement, self).write([statement.id], data)
        return res

    @api.multi
    @api.depends('line_ids', 'move_line_ids', 'line_ids.amount')
    def _get_sum_entry_encoding(self):
        """ Find encoding total of statements """
        for statement in self:
            statement.total_entry_encoding = sum((line.amount for line in statement.line_ids), 0.0)

    @api.model
    def _get_company(self):
        company_id = self.env.user.company_id
        if not company_id:
            company_ids = self.env['res.company'].search([])
        return company_id or company_ids and company_ids[0] or False

    @api.multi
    @api.depends('balance_end_real', 'balance_end')
    def _compute_difference(self):
        for statement in self:
            statement.difference = statement.balance_end_real - statement.balance_end

    @api.multi
    @api.depends('balance_end_real', 'balance_end')
    def _compute_last_closing_balance(self):
        for statement in self:
            if statement.state == 'draft':
                statement_ids = self.search(
                    [('journal_id', '=', statement.journal_id.id),('state', '=', 'confirm')],
                    order='create_date desc',
                    limit=1,
                )
                if statement_ids:
                    statement.last_closing_balance = self.browse(statement_ids[0]).balance_end_real

    @api.multi
    def onchange_journal_id(self, journal_id):
        result = super(account_cash_statement, self).onchange_journal_id(journal_id)

        if journal_id:
            statement_ids = self.search(
                    [('journal_id', '=', journal_id),('state', '=', 'confirm')],
                    order='create_date desc',
                    limit=1,
            )
            opening_details_ids = self._get_cash_open_box_lines(journal_id)
            if opening_details_ids:
                result['value']['opening_details_ids'] = opening_details_ids

            if statement_ids:
                result.setdefault('value', {}).update({'last_closing_balance' : self.browse(statement_ids[0]).balance_end_real})

        return result

    total_entry_encoding = fields.Float(compute='_get_sum_entry_encoding', string="Total Transactions", store=True,
        help="Total of cash transaction lines.")
    closing_date = fields.Datetime(string="Closed On")
    details_ids = fields.One2many('account.cashbox.line', 'bank_statement_id', string='CashBox Lines', copy=True)
    opening_details_ids = fields.One2many('account.cashbox.line', 'bank_statement_id', string='Opening Cashbox Lines')
    closing_details_ids = fields.One2many('account.cashbox.line', 'bank_statement_id', string='Closing Cashbox Lines')
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    difference = fields.Float(compute='_compute_difference', string="Difference",
        help="Difference between the theoretical closing balance and the real closing balance.")
    last_closing_balance = fields.Float(compute='_compute_last_closing_balance', string='Last Closing Balance')
    date = fields.Date(default=lambda self: self._context.get('date', time.strftime("%Y-%m-%d %H:%M:%S")))

    @api.model
    def _get_cash_open_box_lines(self, journal_id):
        details_ids = []
        if not journal_id:
            return details_ids
        journal = self.env['account.journal'].browse(journal_id)
        if journal and (journal.type == 'cash'):
            last_pieces = None

            if journal.with_last_closing_balance == True:
                domain = [('journal_id', '=', journal.id),
                          ('state', '=', 'confirm')]
                last_bank_statement_ids = self.search(domain, limit=1, order='create_date desc')
                last_bank_statement = last_bank_statement_ids and last_bank_statement_ids[0] or False
                if last_bank_statement:

                    last_pieces = dict(
                        (line.pieces, line.number_closing) for line in last_bank_statement.details_ids
                    )
            for value in journal.cashbox_line_ids:
                nested_values = {
                    'number_closing' : 0,
                    'number_opening' : last_pieces.get(value.pieces, 0) if isinstance(last_pieces, dict) else 0,
                    'pieces' : value.pieces
                }
                details_ids.append([0, False, nested_values])
        return details_ids

    @api.model
    def create(self, vals):
        journal_id = vals.get('journal_id')
        if journal_id and not vals.get('opening_details_ids'):
            vals['opening_details_ids'] = vals.get('opening_details_ids') or self._get_cash_open_box_lines(journal_id)
        res = super(account_cash_statement, self).create(vals)
        res._update_balances()
        return res

    @api.multi
    def write(self, vals):
        """
        @param vals: dict of new values to be set
        """
        if vals.get('journal_id', False):
            cashbox_ids = self.env['account.cashbox.line'].search([('bank_statement_id', 'in', self.ids)])
            cashbox_ids.unlink()
        res = super(account_cash_statement, self).write(vals)
        self._update_balances()
        return res

    @api.model
    def _user_allow(self, statement_id):
        return True

    @api.multi
    def button_open(self):
        """ Changes statement state to Running."""

        SequenceObj = self.pool.get('ir.sequence')
        for statement in self:
            vals = {}
            if not self._user_allow(statement.id):
                raise Warning(_('You do not have rights to open this %s journal!') % (statement.journal_id.name, ))

            if statement.name and statement.name == '/':
                context = {'fiscalyear_id': statement.period_id.fiscalyear_id.id}
                if statement.journal_id.sequence_id:
                    st_number = SequenceObj.with_context(context).next_by_id(statement.journal_id.sequence_id.id)
                else:
                    st_number = SequenceObj.with_context(context).next_by_code('account.cash.statement')
                vals.update({
                    'name': st_number
                })

            vals.update({
                'state': 'open',
            })
            statement.write(vals)
        return True

    @api.multi
    def statement_close(self, journal_type='bank'):
        if journal_type == 'bank':
            return super(account_cash_statement, self).statement_close(journal_type)
        for statement in self:
            statement.state = 'confirm'
            statement.closing_date = time.strftime("%Y-%m-%d %H:%M:%S")

    @api.model
    def check_status_condition(self, state, journal_type='bank'):
        if journal_type == 'bank':
            return super(account_cash_statement, self).check_status_condition(state, journal_type)
        return state == 'open'

    @api.multi
    def button_confirm_cash(self):

        TABLES = ((_('Profit'), 'profit_account_id'), (_('Loss'), 'loss_account_id'),)

        for obj in self:
            if obj.difference == 0.0:
                continue
            elif obj.difference < 0.0:
                account = obj.journal_id.loss_account_id
                name = _('Loss')
                if not obj.journal_id.loss_account_id:
                    raise Warning(_('There is no Loss Account on the journal %s.') % (obj.journal_id.name,))
            else: # obj.difference > 0.0
                account = obj.journal_id.profit_account_id
                name = _('Profit')
                if not obj.journal_id.profit_account_id:
                    raise Warning(_('There is no Profit Account on the journal %s.') % (obj.journal_id.name,))

            values = {
                'statement_id' : obj.id,
                'journal_id' : obj.journal_id.id,
                'account_id' : account.id,
                'amount' : obj.difference,
                'name' : name,
            }
            self.env['account.bank.statement.line'].create(values)

        return super(account_cash_statement, self).button_confirm_bank()


class account_journal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _default_cashbox_line_ids(self):
        # Return a list of coins in Euros.
        result = [
            dict(pieces=value) for value in [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
        ]
        return result

    cashbox_line_ids = fields.One2many('account.journal.cashbox.line', 'journal_id',
        string='CashBox', copy=True, default=lambda self: self._default_cashbox_line_ids())


class account_journal_cashbox_line(models.Model):
    _name = 'account.journal.cashbox.line'
    _rec_name = 'pieces'
    _order = 'pieces asc'

    pieces = fields.Float(string='Values', digits=dp.get_precision('Account'))
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, index=True, ondelete="cascade")
