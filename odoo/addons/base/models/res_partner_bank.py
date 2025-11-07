import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


def sanitize_account_number(account_number):
    if account_number:
        return re.sub(r'\W+', '', account_number).upper()
    return False


class ResPartnerBank(models.Model):
    _name = 'res.partner.bank'
    _rec_name = 'account_number'
    _description = 'Bank Account'
    _order = 'sequence, id'

    active = fields.Boolean(default=True)
    account_type = fields.Selection(
        selection=[('bank', 'Normal')],
        string="Type",
        help="Bank account type: Normal, IBAN, CLABE, or other from localization. Inferred from the bank account number.",
        compute='_compute_account_type',
    )
    account_number = fields.Char('Account Number', required=True, search='_search_account_number')
    sanitized_account_number = fields.Char(
        string="Sanitized Account Number",
        compute='_compute_sanitized_account_number',
        readonly=True, store=True,
    )
    holder_name = fields.Char(
        string="Holder Name",
        help="Account holder name in case it is different than the name of the partner.",
        compute='_compute_account_holder_name',
        readonly=False, store=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Partner",
        ondelete='cascade',
        index=True,
        domain=['|', ('is_company', '=', True), ('parent_id', '=', False)],
        required=True,
    )
    allow_out_payment = fields.Boolean(
        string="Send Money",
        help="This account can be used for outgoing payments",
        default=False,
        copy=False,
        readonly=False,
    )

    # bank fields
    bank_name = fields.Char()
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one(comodel_name='res.country.state', string="Fed. State", domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one(comodel_name='res.country', compute='_compute_country_id', precompute=True, store=True, readonly=False)
    country_code = fields.Char(related='country_id.code')
    bank_bic = fields.Char(
        string="BIC/SWIFT",
        help="Bank Identifier Code for international wires in the format Bank Code (4 letters) + Country Code (2 letters) + Location Code (2 letters/numbers) + Optional Branch Code (3 letters/numbers).",
        index=True,
    )
    clearing_label_id = fields.Many2one(
        comodel_name='clearing.label',
        required=True,
        compute='_compute_clearing_label_id',
        precompute=True, store=True, readonly=False,
    )
    clearing_number = fields.Char(
        string="Clearing Number",
        help="A clearing number (or routing number) refers to a bank, branch, or location and is used by domestic money transfer protocols (from/to bank accounts in the same country).",
    )
    show_clearing_number = fields.Boolean(compute='_compute_show_clearing_number')

    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', 'Company')
    note = fields.Text('Notes')
    color = fields.Integer(compute='_compute_color')

    _unique_number = models.Constraint(
        'unique(sanitized_account_number, partner_id)',
        "The combination Account Number/Partner must be unique.",
    )

    @api.constrains('clearing_label_id', 'clearing_number')
    def _check_clearing_number(self):
        for account in self.filtered(lambda b: b.clearing_number):
            country_code = account.clearing_label_id.country_code
            if country_code == 'AU' and (test_bsb := re.sub(r'( |-)', '', account.clearing_number)) and (len(test_bsb) != 6 or not test_bsb.isdigit()):
                raise ValidationError(account.env._('BSB is not valid (expected format is "NNN-NNN"). Please rectify.'))
            if country_code == 'HK' and len(account.clearing_number) != 3:
                raise ValidationError(account.env._("Bank Code length must be 3."))
            if country_code == 'JP' and (len(account.clearing_number) != 3 or not account.clearing_number.isdecimal()):
                raise ValidationError(account.env._("Zengin Branch Code must consist of 3 digits."))
            if country_code == 'SA' and (len(account.clearing_number) != 4 or not account.clearing_number.isalpha() or not account.clearing_number.isupper()):
                raise ValidationError(account.env._("Bank SARIE ID must consist of 4 upper case English letter."))
            if country_code == 'US' and not re.match(r'^\d{1,9}$', account.clearing_number):
                raise ValidationError(account.env._("Routing Number should only contain numbers (maximum 9 digits)."))

    def _get_clearing_number(self, country_code=False):
        if not self:
            return None
        self.ensure_one()
        return self.clearing_label_id.country_code == country_code and self.clearing_number

    @api.depends('country_id')
    def _compute_clearing_label_id(self):
        country_to_clearing_label = dict(self.env['clearing.label']._read_group(
            domain=[('country_id', 'in', self.mapped('country_id').ids + [False])],
            groupby=['country_id'],
            aggregates=['id:recordset'],
        ))
        default_clearing_label = country_to_clearing_label.get(self.env['res.country'])
        for account in self:
            account.clearing_label_id = country_to_clearing_label.get(account.country_id, default_clearing_label)

    @api.depends('country_id')
    def _compute_show_clearing_number(self):
        sepa_countries = self.env.ref('base.sepa_zone').country_ids
        clearing_label_countries = self.env['clearing.label'].search([]).country_id
        excluded_countries = sepa_countries - clearing_label_countries
        for account in self:
            account.show_clearing_number = account.country_id not in excluded_countries

    @api.depends('account_number')
    def _compute_sanitized_account_number(self):
        for account in self:
            account.sanitized_account_number = sanitize_account_number(account.account_number)

    @api.depends('partner_id.country_id', 'company_id.country_id')
    def _compute_country_id(self):
        for account in self:
            if not account.country_id:
                account.country_id = account.partner_id.country_id or account.company_id.country_id or account.env.company.country_id

    def open_linked_partner_id(self):
        return self.partner_id._get_records_action()

    def _search_account_number(self, operator, value):
        if operator in ('in', 'not in'):
            value = [sanitize_account_number(i) for i in value]
        else:
            value = sanitize_account_number(value)
        return [('sanitized_account_number', operator, value)]

    @api.model
    def retrieve_account_type(self, account_number):
        """ To be overridden by subclasses in order to support other account_types.
        """
        return 'bank'

    @api.depends('account_number')
    def _compute_account_type(self):
        for account in self:
            account.account_type = account.retrieve_account_type(account.account_number)

    @api.depends('partner_id.name')
    def _compute_account_holder_name(self):
        for account in self:
            if not account.holder_name:
                account.holder_name = account.partner_id.name

    @api.depends('account_number', 'bank_name')
    def _compute_display_name(self):
        for account in self:
            account.display_name = f'{account.account_number} - {account.bank_name}' if account.bank_name else account.account_number

    @api.depends('allow_out_payment')
    def _compute_color(self):
        for account in self:
            account.color = 10 if account.allow_out_payment else 1

    def _sanitize_vals(self, vals):
        if 'sanitized_account_number' in vals:  # do not allow to write on sanitized directly
            vals['account_number'] = vals.pop('sanitized_account_number')
        if 'account_number' in vals:
            vals['sanitized_account_number'] = sanitize_account_number(vals['account_number'])
        if vals.get('bank_bic'):
            vals['bank_bic'] = vals['bank_bic'].upper()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sanitize_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._sanitize_vals(vals)
        return super().write(vals)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id
