# -*- coding: utf-8 -*-

import re

from openerp import api, fields, models, _
from openerp.exceptions import UserError

def sanitize_account_number(acc_number):
    if acc_number:
        return re.sub(r'\W+', '', acc_number).upper()
    return False

class Bank(models.Model):
    _description = 'Bank'
    _name = 'res.bank'
    _order = 'name'

    name = fields.Char(select=True)
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    state = fields.Many2one('res.country.state', 'Fed. State', domain="[('country_id', '=', country)]")
    country = fields.Many2one('res.country')
    email = fields.Char()
    phone = fields.Char()
    fax = fields.Char()
    active = fields.Boolean(default=True)
    bic = fields.Char('Bank Identifier Code', help="Sometimes called BIC or Swift.")

    @api.multi
    @api.depends('name', 'bic')
    def name_get(self):
        result = []
        for bank in self:
            name = bank.name + (bank.bic and (' - ' + bank.bic) or '')
            result.append((bank.id, name))
        return result

class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _rec_name = 'acc_number'
    _description = 'Bank Accounts'
    _order = 'sequence'

    def _default_acc_type(self):
        return self._fields['acc_type'].get_values(self.env)[-1]

    acc_type = fields.Selection([('bank', 'Normal')], 'Bank Account Type', default=_default_acc_type, required=True)
    acc_number = fields.Char('Account Number', required=True)
    sanitized_acc_number = fields.Char(compute='_compute_sanitized_acc_number', string='Sanitized Account Number', readonly=True, store=True)
    partner_id = fields.Many2one('res.partner', 'Account Holder', ondelete='cascade', select=True, domain=['|', ('is_company', '=', True), ('parent_id', '=', False)])
    bank_id = fields.Many2one('res.bank', string='Bank')
    bank_name = fields.Char(related='bank_id.name')
    bank_bic = fields.Char(related='bank_id.bic')
    sequence = fields.Integer()
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, ondelete='cascade')

    _sql_constraints = [
        ('unique_number', 'unique(sanitized_acc_number)', 'Account Number must be unique'),
    ]

    @api.one
    @api.depends('acc_number')
    def _compute_sanitized_acc_number(self):
        self.sanitized_acc_number = sanitize_account_number(self.acc_number)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'acc_number':
                op = args[pos][1]
                value = args[pos][2]
                if hasattr(value, '__iter__'):
                    value = [sanitize_account_number(i) for i in value]
                else:
                    value = sanitize_account_number(value)
                if 'like' in op:
                    value = '%' + value + '%'
                args[pos] = ('sanitized_acc_number', op, value)
            pos += 1
        return super(ResPartnerBank, self).search(args, offset, limit, order, count=count)
