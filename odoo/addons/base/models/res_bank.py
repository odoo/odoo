# -*- coding: utf-8 -*-

import re

from collections.abc import Iterable

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import clean_context

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
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

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

    active = fields.Boolean(default=True)
    acc_type = fields.Selection(selection=lambda x: x.env['res.partner.bank'].get_supported_account_types(), compute='_compute_acc_type', string='Type', help='Bank account type: Normal or IBAN. Inferred from the bank account number.')
    acc_number = fields.Char('Account Number', required=True)
    sanitized_acc_number = fields.Char(compute='_compute_sanitized_acc_number', string='Sanitized Account Number', readonly=True, store=True)
    acc_holder_name = fields.Char(string='Account Holder Name', help="Account holder name, in case it is different than the name of the Account Holder")
    partner_id = fields.Many2one('res.partner', 'Account Holder', ondelete='cascade', index=True, domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], required=True)
    allow_out_payment = fields.Boolean('Send Money', help='This account can be used for outgoing payments', default=False, copy=False, readonly=False)
    bank_id = fields.Many2one('res.bank', string='Bank')
    bank_name = fields.Char(related='bank_id.name', readonly=False)
    bank_bic = fields.Char(related='bank_id.bic', readonly=False)
    sequence = fields.Integer(default=10)
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', 'Company', related='partner_id.company_id', store=True, readonly=True)

    _sql_constraints = [(
        'unique_number',
        'unique(sanitized_acc_number, partner_id)',
        'The combination Account Number/Partner must be unique.'
    )]

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

    def name_get(self):
        return [(acc.id, '{} - {}'.format(acc.acc_number, acc.bank_id.name) if acc.bank_id else acc.acc_number)
                for acc in self]

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        pos = 0
        while pos < len(args):
            # DLE P14
            if args[pos][0] == 'acc_number':
                op = args[pos][1]
                value = args[pos][2]
                if not isinstance(value, str) and isinstance(value, Iterable):
                    value = [sanitize_account_number(i) for i in value]
                else:
                    value = sanitize_account_number(value)
                if 'like' in op:
                    value = '%' + value + '%'
                args[pos] = ('sanitized_acc_number', op, value)
            pos += 1
        return super(ResPartnerBank, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)

    def _find_or_create_bank_account(self, account_number, partner, company=None, allow_company=False, extra_create_vals=None):
        # There is a sql constraint on res.partner.bank ensuring an unique pair <partner, account number>.
        # Since it's not dependent of the company, we need to search on others company too to avoid the creation
        # of an extra res.partner.bank raising an error coming from this constraint.
        # However, at the end, we need to filter out the results to not trigger the check_company when trying to
        # assign a res.partner.bank owned by another company.
        bank_account = self.env['res.partner.bank'].sudo().with_context(active_test=False).search([
            ('acc_number', '=', account_number),
            ('partner_id', 'child_of', partner.id),
        ])
        if not bank_account:
            if not allow_company and partner.id in self.env['res.company']._get_company_partner_ids():
                raise UserError(_("Please add your own bank account manually."))
            bank_account = self.env['res.partner.bank'].with_context(clean_context(self.env.context)).create({
                **(extra_create_vals or {}),
                'acc_number': account_number,
                'partner_id': partner.id,
                'allow_out_payment': False,
            })
        return bank_account.filtered(lambda x: x.company_id.id in (False, company.id if company else False)).sudo(False)
