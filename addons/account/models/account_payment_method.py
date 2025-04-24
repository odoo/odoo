# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.fields import Domain


class AccountPaymentMethod(models.Model):
    _name = 'account.payment.method'
    _description = "Payment Methods"
    _order = 'sequence, code, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Selection(
        selection=[('manual', 'manual')],
        required=True,
        ondelete={'manual': 'cascade'},
    )
    sequence = fields.Integer(default=10)
    available_payment_method_codes = fields.Char(
        string="Available Payment Method Codes",
        compute='_compute_available_payment_method_codes',
        help="Technical field to enable a dynamic selection of the field code",
    )
    payment_type = fields.Selection(
        selection=[
            ('inbound', 'Inbound'),
            ('outbound', 'Outbound')
        ],
        required=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        readonly=True,
        index=True,
        default=lambda self: self.env.company,
    )
    default_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Default Journal',
        domain="[('id', 'in', available_journal_ids)]",
    )
    available_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_journal_ids'
    )
    default_outstanding_payment_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Default Outstanding Payment Account',
    )
    active = fields.Boolean(default=True)

    _name_code_payment_type_company_unique = models.Constraint(
        'unique (name, code, payment_type, company_id)',
        'The combination name/code/payment type/company already exists!',
    )

    @api.model
    def _get_payment_method_domain(self, code, with_currency=True, with_country=True):
        """
        :param code: string of the payment method code to check.
        :param with_currency: if False (default True), ignore the currency_id domain if it exists.
        :return: The domain specifying which journal can accommodate this payment method.
        """
        if not code:
            return Domain.TRUE
        information = self._get_payment_method_information().get(code)
        journal_types = information.get('type', ('bank', 'cash', 'credit'))
        domain = Domain('type', 'in', journal_types)

        if with_currency and (currency_ids := information.get('currency_ids')):
            domain &= (
                Domain('currency_id', '=', False) & Domain('company_id.currency_id', 'in', currency_ids)
            ) | Domain('currency_id', 'in', currency_ids)

        if with_country and (country_id := information.get('country_id')):
            domain &= Domain('company_id.account_fiscal_country_id', '=', country_id)

        return domain

    @api.model
    def _get_payment_method_information(self):
        """
        Contains details about how to initialize a payment method with the code x.
        The contained info are:

        - ``type``: Tuple containing one or both of these items: "bank" and "cash"
        - ``currency_ids``: The ids of the currency necessary on the journal (or company) for it to be eligible.
        - ``country_id``: The id of the country needed on the company for it to be eligible.
        """
        return {
            'manual': {'type': ('bank', 'cash', 'credit')},
        }

    @api.model
    def _get_sdd_payment_method_code(self):
        """
        TO OVERRIDE
        This hook will be used to return the list of sdd payment method codes
        """
        return []

    @api.model
    def _get_available(self, payment_type=None, country=None, currency=None, current_journal=None):
        payment_methods = self.search([
                '|', '|',
                ('company_id', 'parent_of', self.env.company.id),
                ('company_id', 'child_of', self.env.company.id),
                ('company_id', '=', None),
            ] + [('payment_type', '=', payment_type)] if payment_type else [])

        if country or currency:
            for method in payment_methods:
                if information := self._get_payment_method_information().get(method.code):
                    if information.get('country_id') and (information.get('country_id') != country.id):
                        payment_methods -= method
                    if information.get('currency_ids') and currency and (currency.id not in information.get('currency_ids')):
                        payment_methods -= method

        if current_journal:
            payment_methods = payment_methods.filtered(lambda m: current_journal._is_payment_method_available(m.code))
        return payment_methods

    @api.depends('payment_type')
    def _compute_available_journal_ids(self):
        """
        Get all journals that fit the payment method domain.
        """
        journals = self.env['account.journal'].search([
            '|',
            ('company_id', 'parent_of', self.env.company.id),
            ('company_id', 'child_of', self.env.company.id),
            ('type', 'in', ('bank', 'cash', 'credit')),
        ])
        for method in self:
            method.available_journal_ids = journals.filtered(lambda j: j._is_payment_method_available(method.code))

    @api.model
    def _compute_available_payment_method_codes(self):
        """
        TO OVERRIDE
        For payment methods whose codes we don't want to show up in the selection field code.
        """
        available_method_codes = self._get_payment_method_information().keys()
        for method in self:
            method.available_payment_method_codes = ','.join(available_method_codes)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)

        for payment_method, vals in zip(self, vals_list):
            vals.update(
                name=_("%s (copy)", payment_method.name or ''))
        return vals_list

    def unlink(self):
        """
        Payment methods which are used in a payment should not be deleted from the database,
        they will just be archived.
        """
        unused_payment_methods = self
        for method in self:
            payment_count = self.env['account.payment'].sudo().search_count([('payment_method_id', '=', method.id)])
            if payment_count > 0:
                unused_payment_methods -= method

        (self - unused_payment_methods).action_archive()

        return super(AccountPaymentMethod, unused_payment_methods).unlink()
