# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class account_bank_statement(models.Model):
    _inherit = 'account.bank.statement'

    @api.multi
    def write(self, vals):
        # bypass obsolete statement line resequencing
        if vals.get('line_ids') or self._context.get('ebanking_import'):
            res = super(models.Model, self).write(vals)
        else:
            res = super(account_bank_statement, self).write(vals)
        return res

    @api.multi
    def button_confirm_bank(self):
        super(account_bank_statement, self).button_confirm_bank()
        for st in self:
            st.line_ids.write({'state': 'confirm'})

    @api.multi
    def button_cancel(self):
        super(account_bank_statement, self).button_cancel()
        for st in self:
            st.line_ids.write({'state': 'draft'})


class AccountBankStatementLineGlobal(models.Model):
    _name = 'account.bank.statement.line.global'
    _description = 'Batch Payment Info'
    _rec_name = 'code'

    name = fields.Char(string='OBI', required=True, default='/', help="Originator to Beneficiary Information")
    code = fields.Char(size=64, required=True, default=lambda self: self.env['ir.sequence'].next_by_code('account.bank.statement.line.global'))
    parent_id = fields.Many2one('account.bank.statement.line.global', string='Parent Code', ondelete='cascade')
    child_ids = fields.One2many('account.bank.statement.line.global', 'parent_id', string='Child Codes', copy=True)
    type = fields.Selection([('iso20022', 'ISO 20022'), ('coda', 'CODA'), ('manual', 'Manual')], required=True)
    amount = fields.Float(digits=0)
    bank_statement_line_ids = fields.One2many('account.bank.statement.line', 'globalisation_id', string='Bank Statement Lines')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code must be unique !'),
    ]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        statment_global_lines = []
        if name:
            statment_global_lines = self.search([('code', 'ilike', name)] + args, limit=limit)
            if not statment_global_lines:
                statment_global_lines = self.search([('name', operator, name)] + args, limit=limit)
            if not statment_global_lines and len(name.split()) >= 2:
                #Separating code and name for searching
                operand1, operand2 = name.split(' ', 1)  # name can contain spaces
                statment_global_lines = self.search([('code', 'like', operand1), ('name', operator, operand2)] + args, limit=limit)
        else:
            statment_global_lines = self.search(args, limit=limit)
        return statment_global_lines.name_get()


class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'

    val_date = fields.Date(string='Value Date', states={'confirm': [('readonly', True)]})
    globalisation_id = fields.Many2one('account.bank.statement.line.global', string='Globalisation ID', states={'confirm': [('readonly', True)]}, help="Code to identify transactions belonging to the same globalisation level within a batch payment")
    globalisation_amount = fields.Float(related='globalisation_id.amount', string='Glob. Amount', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed')], string='Status', required=True, readonly=True, copy=False, default='draft')
    counterparty_name = fields.Char(size=35)
    counterparty_bic = fields.Char(size=11)
    counterparty_number = fields.Char(size=34)
    counterparty_currency = fields.Char(size=3)

    @api.multi
    def unlink(self):
        if self._context.get('block_statement_line_delete'):
            raise UserError(_('Delete operation not allowed. Please go to the associated bank statement in order to delete and/or modify bank statement line.'))
        return super(account_bank_statement_line, self).unlink()
