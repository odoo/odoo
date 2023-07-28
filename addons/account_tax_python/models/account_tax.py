# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class AccountTaxPython(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(selection_add=[
        ('code', 'Python Code')
    ], ondelete={'code': lambda recs: recs.write({'amount_type': 'percent', 'active': False})})

    python_compute = fields.Text(string='Python Code', default="result = price_unit * 0.10",
        help="Compute the amount of the tax by setting the variable 'result'.\n\n"
            ":param base_amount: float, actual amount on which the tax is applied\n"
            ":param price_unit: float\n"
            ":param quantity: float\n"
            ":param company: res.company recordset singleton\n"
            ":param product: product.product recordset singleton or None\n"
            ":param partner: res.partner recordset singleton or None")
    python_applicable = fields.Text(string='Applicable Code', default="result = True",
        help="Determine if the tax will be applied by setting the variable 'result' to True or False.\n\n"
            ":param price_unit: float\n"
            ":param quantity: float\n"
            ":param company: res.company recordset singleton\n"
            ":param product: product.product recordset singleton or None\n"
            ":param partner: res.partner recordset singleton or None")

    @api.model
    def _ascending_process_fixed_taxes_batch(self, batch, tax_computer, extra_base_variable, fixed_multiplicator=1):
        # EXTENDS 'account'
        super()._ascending_process_fixed_taxes_batch(batch, tax_computer, extra_base_variable, fixed_multiplicator=fixed_multiplicator)

        if batch['amount_type'] == 'code':
            batch['computed'] = 'tax'
            for tax_values in batch['taxes']:
                tax_computer.new_equation(tax_values['tax'].python_compute, standalone=True)
                tax_values['tax_amount'] = tax_computer.new_equation('result')
                tax_values['tax_amount_factorized'] = tax_computer.new_equation(
                    f"{tax_values['tax_amount']} * {tax_values['factor']}"
                )

    @api.model
    def _descending_process_price_included_taxes_batch(self, batch, tax_computer, extra_base_variable):
        # EXTENDS 'account'
        super()._descending_process_price_included_taxes_batch(batch, tax_computer, extra_base_variable)
        if batch['price_include'] and batch['amount_type'] == 'code':
            batch['computed'] = True
            amounts_variable = [tax_values['tax_amount_factorized'] for tax_values in batch['taxes']]
            batch_base_variable = tax_computer.new_equation(
                f"((price_unit * quantity) + {extra_base_variable}) - {' - '.join(amounts_variable)}"
            )
            for tax_values in batch['taxes']:
                tax_values['base'] = tax_values['display_base'] = batch_base_variable

    @api.model
    def _ascending_process_taxes_batch(self, batch, tax_computer, extra_base_variable):
        # EXTENDS 'account'
        super()._ascending_process_taxes_batch(batch, tax_computer, extra_base_variable)
        if not batch['price_include'] and batch['amount_type'] == 'code':
            batch['computed'] = True
            base_variable = tax_computer.new_equation(
                f"(price_unit * quantity) + {extra_base_variable}"
            )
            for tax_values in batch['taxes']:
                tax_values['base'] = tax_values['display_base'] = base_variable
