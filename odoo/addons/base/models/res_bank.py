# -*- coding: utf-8 -*-

import re

import collections

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import pycompat


def sanitize_account_number(acc_number):
    if acc_number:
        return re.sub(r'\W+', '', acc_number).upper()
    return False


class Bank(models.Model):
    _description = 'Bank'
    _name = 'res.bank'
    _order = 'name'

    name = fields.Char(required=True)
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    state = fields.Many2one('res.country.state', 'Fed. State', domain="[('country_id', '=', country)]")
    country = fields.Many2one('res.country')
    email = fields.Char()
    phone = fields.Char()
    active = fields.Boolean(default=True)
    bic = fields.Char('Bank Identifier Code', index=True, help="Sometimes called BIC or Swift.")

    @api.multi
    @api.depends('name', 'bic')
    def name_get(self):
        result = []
        for bank in self:
            name = bank.name + (bank.bic and (' - ' + bank.bic) or '')
            result.append((bank.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('bic', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        bank_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(bank_ids).name_get()


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _rec_name = 'acc_number'
    _description = 'Bank Accounts'
    _order = 'sequence'

    @api.model
    def get_supported_account_types(self):
        return self._get_supported_account_types()

    @api.model
    def _get_supported_account_types(self):
        return [('bank', _('Normal'))]

    acc_type = fields.Selection(selection=lambda x: x.env['res.partner.bank'].get_supported_account_types(), compute='_compute_acc_type', string='Type', help='Bank account type: Normal or IBAN. Inferred from the bank account number.')
    acc_number = fields.Char('Account Number', required=True)
    sanitized_acc_number = fields.Char(compute='_compute_sanitized_acc_number', string='Sanitized Account Number', readonly=True, store=True)
    acc_holder_name = fields.Char(string='Account Holder Name', help="Account holder name, in case it is different than the name of the Account Holder")
    partner_id = fields.Many2one('res.partner', 'Account Holder', ondelete='cascade', index=True, domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], required=True)
    bank_id = fields.Many2one('res.bank', string='Bank')
    bank_name = fields.Char(related='bank_id.name')
    bank_bic = fields.Char(related='bank_id.bic')
    sequence = fields.Integer()
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, ondelete='cascade')

    _sql_constraints = [
        ('unique_number', 'unique(sanitized_acc_number, company_id)', 'Account Number must be unique'),
    ]

    @api.depends('acc_number')
    def _compute_sanitized_acc_number(self):
        for bank in self:
            bank.sanitized_acc_number = sanitize_account_number(bank.acc_number)

    @api.depends('acc_number')
    def _compute_acc_type(self):
        for bank in self:
            bank.acc_type = self.retrieve_acc_type(bank.acc_number)

    @api.model
    def retrieve_acc_type(self, acc_number):
        """ To be overridden by subclasses in order to support other account_types.
        """
        return 'bank'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'acc_number':
                op = args[pos][1]
                value = args[pos][2]
                if not isinstance(value, pycompat.string_types) and isinstance(value, collections.Iterable):
                    value = [sanitize_account_number(i) for i in value]
                else:
                    value = sanitize_account_number(value)
                if 'like' in op:
                    value = '%' + value + '%'
                args[pos] = ('sanitized_acc_number', op, value)
            pos += 1
        return super(ResPartnerBank, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)
