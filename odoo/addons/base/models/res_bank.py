# -*- coding: utf-8 -*-

import re

from collections.abc import Iterable

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import pycompat

import werkzeug.urls

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
    state = fields.Many2one('res.country.state', 'Fed. State', domain="[('country_id', '=?', country)]")
    country = fields.Many2one('res.country')
    email = fields.Char()
    phone = fields.Char()
    active = fields.Boolean(default=True)
    bic = fields.Char('Bank Identifier Code', index=True, help="Sometimes called BIC or Swift.")

    @api.multi
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
        
    @api.onchange('country')
    def _onchange_country_id(self):
        if self.country and self.country != self.state.country_id:
            self.state = False
            
    @api.onchange('state')
    def _onchange_state(self):
        if self.state.country_id:
            self.country = self.state.country_id


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _rec_name = 'acc_number'
    _description = 'Bank Accounts'
    _order = 'sequence, id'

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
    bank_name = fields.Char(related='bank_id.name', readonly=False)
    bank_bic = fields.Char(related='bank_id.bic', readonly=False)
    sequence = fields.Integer(default=10)
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, ondelete='cascade')
    qr_code_valid = fields.Boolean(string="Has all required arguments", compute="_validate_qr_code_arguments")

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
                if not isinstance(value, pycompat.string_types) and isinstance(value, Iterable):
                    value = [sanitize_account_number(i) for i in value]
                else:
                    value = sanitize_account_number(value)
                if 'like' in op:
                    value = '%' + value + '%'
                args[pos] = ('sanitized_acc_number', op, value)
            pos += 1
        return super(ResPartnerBank, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)

    @api.model
    def build_qr_code_url(self, amount, comment):
        communication = ""
        if comment:
            communication = (comment[:137] + '...') if len(comment) > 140 else comment
        qr_code_string = 'BCD\n001\n1\nSCT\n%s\n%s\n%s\nEUR%s\n\n\n%s' % (self.bank_bic, self.company_id.name, self.acc_number, amount, communication)
        qr_code_url = '/report/barcode/?type=%s&value=%s&width=%s&height=%s&humanreadable=1' % ('QR', werkzeug.url_quote_plus(qr_code_string), 128, 128)
        return qr_code_url

    @api.multi
    def _validate_qr_code_arguments(self):
        for bank in self:
            bank.qr_code_valid = (bank.bank_bic
                                            and bank.company_id.name
                                            and bank.acc_number)
