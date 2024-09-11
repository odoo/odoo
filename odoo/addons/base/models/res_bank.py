import re

from collections.abc import Iterable

from odoo import api, fields, models
from odoo.tools import _, SQL


def sanitize_account_number(acc_number):
    if acc_number:
        return re.sub(r'\W+', '', acc_number).upper()
    return False


class Bank(models.Model):
    _description = 'Bank'
    _name = 'res.bank'
    _order = 'name'
    _rec_names_search = ['name', 'bic']

    name = fields.Char(required=True)
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    state = fields.Many2one('res.country.state', 'Fed. State', domain="[('country_id', '=?', country)]")
    country = fields.Many2one('res.country')
    country_code = fields.Char(related='country.code', string='Country Code')
    email = fields.Char()
    phone = fields.Char()
    active = fields.Boolean(default=True)
    bic = fields.Char('Bank Identifier Code', index=True, help="Sometimes called BIC or Swift.")

    @api.depends('bic')
    def _compute_display_name(self):
        for bank in self:
            name = (bank.name or '') + (bank.bic and (' - ' + bank.bic) or '')
            bank.display_name = name

    @api.model
    def _search_display_name(self, operator, value):
        if operator in ('ilike', 'not ilike') and value:
            domain = ['|', ('bic', '=ilike', value + '%'), ('name', 'ilike', value)]
            if operator == 'not ilike':
                domain = ['!', *domain]
            return domain
        return super()._search_display_name(operator, value)

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
    acc_holder_name = fields.Char(string='Account Holder Name', help="Account holder name, in case it is different than the name of the Account Holder", compute='_compute_account_holder_name', readonly=False, store=True)
    partner_id = fields.Many2one('res.partner', 'Account Holder', ondelete='cascade', index=True, domain=['|', ('is_company', '=', True), ('parent_id', '=', False)], required=True)
    allow_out_payment = fields.Boolean('Send Money', help='This account can be used for outgoing payments', default=False, copy=False, readonly=False)
    bank_id = fields.Many2one('res.bank', string='Bank')
    bank_name = fields.Char(related='bank_id.name', readonly=False)
    bank_bic = fields.Char(related='bank_id.bic', readonly=False)
    sequence = fields.Integer(default=10)
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', 'Company', related='partner_id.company_id', store=True, readonly=True)
    country_code = fields.Char(related='partner_id.country_code', string="Country Code")

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

    @api.depends('partner_id')
    def _compute_account_holder_name(self):
        for bank in self:
            bank.acc_holder_name = bank.partner_id.name

    @api.model
    def retrieve_acc_type(self, acc_number):
        """ To be overridden by subclasses in order to support other account_types.
        """
        return 'bank'

    @api.depends('acc_number', 'bank_id')
    def _compute_display_name(self):
        for acc in self:
            acc.display_name = f'{acc.acc_number} - {acc.bank_id.name}' if acc.bank_id else acc.acc_number

    def _condition_to_sql(self, alias: str, fname: str, operator: str, value, query) -> SQL:
        if fname == 'acc_number':
            fname = 'sanitized_acc_number'
            if not isinstance(value, str) and isinstance(value, Iterable):
                value = [sanitize_account_number(i) for i in value]
            else:
                value = sanitize_account_number(value)
        return super()._condition_to_sql(alias, fname, operator, value, query)
