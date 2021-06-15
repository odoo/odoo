# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class AccountPaymentMethod(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection(selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)

    _sql_constraints = [
        ('name_code_unique', 'unique (code, payment_type)', 'The combination code/payment type already exists!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        payment_methods = super().create(vals_list)
        methods_info = self._get_payment_method_information()
        for method in payment_methods:
            information = methods_info.get(method.code)
            limit = None if information.get('mode') == 'multi' else 1

            method_domain = method._get_payment_method_domain()

            journals = self.env['account.journal'].search(method_domain, limit=limit)

            self.env['account.payment.method.line'].create([{
                'name': method.name,
                'payment_method_id': method.id,
                'journal_id': journal.id
            } for journal in journals])
        return payment_methods

    def _get_payment_method_domain(self):
        """
        :return: The domain specyfying which journal can accomodate this payment method.
        """
        self.ensure_one()
        information = self._get_payment_method_information().get(self.code)

        unique = information.get('mode') == 'unique'
        currency_id = information.get('currency_id')
        country_id = information.get('country_id')
        default_domain = [('type', 'in', ('bank', 'cash'))]
        domains = [information.get('domain', default_domain)]

        if currency_id:
            domains += [expression.OR([
                [('currency_id', '=', False), ('company_id.currency_id', '=', currency_id)],
                [('currency_id', '=', currency_id)]],
            )]

        if country_id:
            domains += [[('company_id.account_fiscal_country_id', '=', country_id)]]

        if unique:
            company_ids = self.env['payment.acquirer'].search([('provider', '=', self.code)]).mapped('company_id')
            if company_ids:
                domains += [[('company_id', 'in', company_ids.ids)]]

        return expression.AND(domains)

    @api.model
    def _get_payment_method_information(self):
        """
        Contains details about how to initialize a payment method with the code x.
        The contained info are:
            mode: Either unique if we only want one of them at a single time (payment acquirers for example)
                   or multi if we want the method on each journal fitting the domain.
            domain: The domain defining the eligible journals.
            currency_id: The id of the currency necessary on the journal (or company) for it to be eligible.
            country_id: The id of the country needed on the company for it to be eligible.
            hidden: If set to true, the method will not be automatically added to the journal,
                    and will not be selectable by the user.
        """
        return {
            'manual': {'mode': 'multi', 'domain': [('type', 'in', ('bank', 'cash'))]},
        }


class AccountPaymentMethodLine(models.Model):
    _name = "account.payment.method.line"
    _description = "Payment Methods"

    # == Business fields ==
    name = fields.Char(compute='_compute_name', readonly=False, store=True)
    sequence = fields.Integer(default=10)
    payment_method_id = fields.Many2one(
        string='Payment Method',
        comodel_name='account.payment.method',
        domain="[('payment_type', '=?', payment_type), ('id', 'in', available_payment_method_ids)]",
        required=True
    )
    payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        domain=lambda self: "[('deprecated', '=', False), "
                            "('company_id', '=', company_id), "
                            "('user_type_id.type', 'not in', ('receivable', 'payable')), "
                            "('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_current_assets').id
    )
    journal_id = fields.Many2one(comodel_name='account.journal', required=True, ondelete="cascade")

    # == Display purpose fields ==
    code = fields.Char(related='payment_method_id.code')
    payment_type = fields.Selection(related='payment_method_id.payment_type')
    company_id = fields.Many2one(related='journal_id.company_id')
    available_payment_method_ids = fields.Many2many(related='journal_id.available_payment_method_ids')

    @api.depends('payment_method_id.name')
    def _compute_name(self):
        for method in self:
            method.name = method.payment_method_id.name
