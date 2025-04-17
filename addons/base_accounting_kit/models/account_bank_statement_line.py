# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.http import request


class AccountBankStatementLine(models.Model):
    """Update the 'rowdata' field for the specified record."""
    _name = 'account.bank.statement.line'
    _inherit = ['account.bank.statement.line', 'mail.thread',
                'mail.activity.mixin', 'analytic.mixin']

    lines_widget = fields.Char(string="Lines Widget")
    account_id = fields.Many2one('account.account', string='Account')
    tax_ids = fields.Many2many('account.tax')
    form_name = fields.Char()
    form_balance = fields.Monetary(currency_field='currency_id')
    rowdata = fields.Json(string="RowData")
    matchRowdata = fields.Json(string="MatchRowData")
    record_id = fields.Integer()
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', readonly=True,
    )
    bank_state = fields.Selection(selection=[('invalid', 'Invalid'),
                                             ('valid', 'Valid'),
                                             ('reconciled', 'Reconciled')],
                                  compute='_compute_state', store=True)
    reconcile_models_widget = fields.Char()
    lines_widget_json = fields.Json(store=True)

    @api.model
    def update_rowdata(self, record_id):
        """Update the 'rowdata' field for the specified record."""
        request.session['record_id'] = record_id

    @api.model
    def update_match_row_data(self, resId):
        """Update the match row data for a specific record identified by the given resId."""
        request.session['resId'] = resId
        move_record = self.env['account.move.line'].browse(resId)
        move_record_values = {
            'id': move_record.id,
            'account_id': move_record.account_id.id,
            'account_name': move_record.account_id.name,
            'account_code': move_record.account_id.code,
            'partner_id': move_record.partner_id,
            'partner_name': move_record.partner_id.name,
            'date': move_record.date,
            'move_id': move_record.move_id,
            'move_name': move_record.move_id.name,
            'name': move_record.name,
            'amount_residual_currency': move_record.amount_residual_currency,
            'amount_residual': move_record.amount_residual,
            'currency_id': move_record.currency_id.id,
            'currency_symbol': move_record.currency_id.symbol
        }
        return move_record_values

    def button_validation(self, async_action=False):
        """Ensure the current recordset holds a single record and mark it as reconciled."""
        self.ensure_one()
        self.is_reconciled = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def button_reset(self):
        """Reset the current bank statement line if it is in a 'reconciled' state."""
        self.ensure_one()
        if self.bank_state == 'reconciled':
            self.action_undo_reconciliation()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def button_to_check(self, async_action=True):
        """Ensure the current recordset holds a single record, validate the bank
        state, and mark the move as 'to check'."""
        self.ensure_one()
        if self.bank_state == 'valid':
            self.button_validation(async_action=async_action)
            self.move_id.to_check = True
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def button_set_as_checked(self):
        """Mark the associated move as 'not to check' by setting 'to_check' to False."""
        self.ensure_one()
        self.move_id.to_check = False
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def get_statement_line(self, record_id):
        """Retrieve and format bank statement line details based on the provided record ID."""
        statement_line_records = self.env[
            'account.bank.statement.line'].search_read([('id', '=', record_id)])
        result_list = []
        for record in statement_line_records:
            move_id = record.get('move_id', False)
            partner_id = record.get('partner_id', False)
            date = record.get('date', False)
            amount = record.get('amount', False)
            currency_id = record.get('currency_id', False)
            payment_ref = record.get("payment_ref", False)
            bank_state = record.get("bank_state", False)
            id = record.get("id", False)
            if move_id:
                move_record = self.env['account.move.line'].search(
                    [('move_id', '=', move_id[0])], limit=1)
                currency_symbol = self.env['res.currency'].browse(
                    currency_id[0])
                account_id = move_record.account_id
                date_str = date.strftime('%Y-%m-%d') if date else None
                result_list.append({
                    'id': id,
                    'move_id': move_id,
                    'partner_id': partner_id,
                    'account_id': account_id.id,
                    'account_name': account_id.name,
                    'account_code': account_id.code,
                    'date': date_str,
                    'amount': amount,
                    'currency_symbol': currency_symbol.symbol,
                    'payment_ref': payment_ref,
                    'bank_state': bank_state,
                })
                # Update the account_id for the current record
                self.env['account.bank.statement.line'].browse(
                    record['id']).write({'account_id': account_id.id})
        return result_list

    @api.depends('account_id')
    def _compute_state(self):
        """Compute the state of bank transactions based on the account's
         reconciliation status and journal settings."""
        for record in self:
            if record.is_reconciled:
                record.bank_state = 'reconciled'
            else:
                suspense_account = record.journal_id.suspense_account_id
                if suspense_account in record.account_id:
                    record.bank_state = 'invalid'
                else:
                    record.bank_state = 'valid'
