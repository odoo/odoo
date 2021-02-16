# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from datetime import date


class BankingAccount(models.Model):
    _name = "school.account"
    _description = "Account com"

    name = fields.Char(string='Account Name', required=True, translate=True)
    balance = fields.Integer(string="Current Balance", readonly=True, compute='_balance', default=0)
    note = fields.Text(string='Description')
    code = fields.Char('Code', required=True, readonly=True, default='New')
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    today = fields.Date(require=True, readonly=True, default=lambda self: date.today())
    transaction = fields.Text(compute='_trans', readonly=True, required=True, default='')
    operations = fields.Selection([('none', 'None'), ('deposit', 'Deposit'), ('debit', 'Debit')], default='none')
    deposit = fields.Integer('Deposit', default=0)
    debit = fields.Integer('Debit', default=0)

    trans = []

    @api.depends('transaction')
    def _trans(self, val):
        self.trans.append(val)
        self.write({
            'transaction': self.trans,
        })

    @api.model
    def create(self, vals_list):
        vals_list['code'] = self.env['ir.sequence'].next_by_code('banking.account') or 'New'
        return super(BankingAccount, self).create(vals_list)

    @api.depends('operations', 'balance')
    def _balance(self):
        for rec in self:
            if rec.operations == 'deposit':
                rec.balance += rec.deposit
                t = ('Deposit', date.today(), rec.deposit, rec.balance)
                self._trans(t)
            elif rec.operations == 'debit':
                rec.balance -= rec.deposit
                t = ('Debit', date.today(), rec.debit, rec.balance)
                self._trans(t)
            else:
                rec.balance = rec.balance
