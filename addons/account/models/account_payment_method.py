# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class AccountPaymentMethod(models.Model):
    _name = 'account.payment.method'
    _description = "Payment Methods"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection(selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)
    country_id = fields.Many2one(comodel_name='res.country')

    _name_code_unique = models.Constraint(
        'unique (code, payment_type)',
        'The combination code/payment type already exists!',
    )

    @api.model
    def _get_payment_method_domain(self, code, with_currency=True, with_country=True):
        """
        :param code: string of the payment method code to check.
        :param with_currency: if False (default True), ignore the currency_id domain if it exists.
        :return: The domain specifying which journal can accommodate this payment method.
        """
        if not code:
            return []
        information = self._get_payment_method_information().get(code)
        journal_types = information.get('type', ('bank', 'cash', 'credit'))
        domains = [[('type', 'in', journal_types)]]

        if with_currency and (currency_ids := information.get('currency_ids')):
            domains += [expression.OR([
                [('currency_id', '=', False), ('company_id.currency_id', 'in', currency_ids)],
                [('currency_id', 'in', currency_ids)],
            ])]

        if with_country and (country_id := information.get('country_id')):
            domains += [[('company_id.account_fiscal_country_id', '=', country_id)]]

        return expression.AND(domains)

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
        payment_methods = self.search([('payment_type', '=', payment_type)] if payment_type else [])
        if country or currency:
            for method in payment_methods:
                information = self._get_payment_method_information().get(method.code)
                if information.get('country_id') and (information.get('country_id') != country.id):
                    payment_methods -= method
                if information.get('currency_ids') and currency and (currency.id not in information.get('currency_ids')):
                    payment_methods -= method
        if current_journal:
            payment_methods = payment_methods.filtered(lambda m: current_journal._is_payment_method_available(m.code))
        return payment_methods
