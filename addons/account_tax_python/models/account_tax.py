# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.tools.float_utils import float_round
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


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

    def _ascending_process_fixed_taxes_batch(self, batch, base, precision_rounding, extra_computation_values, fixed_multiplicator=1):
        # EXTENDS 'account'
        super()._ascending_process_fixed_taxes_batch(batch, base, precision_rounding, extra_computation_values, fixed_multiplicator=fixed_multiplicator)

        if batch['amount_type'] == 'code':
            batch['computed'] = True
            for tax_values in batch['taxes']:
                localdict = {**extra_computation_values, 'base_amount': base}
                tax = tax_values['tax']
                try:
                    safe_eval(tax.python_compute, localdict, mode="exec", nocopy=True)
                except Exception as e:
                    raise UserError(_(
                        "You entered invalid code %r in %r taxes\n\nError : %s",
                        tax.python_compute,
                        tax.name,
                        e,
                    ))
                tax_values['tax_amount'] = localdict['result']
                tax_values['tax_amount_factorized'] = float_round(
                    tax_values['tax_amount'] * tax_values['factor'],
                    precision_rounding=precision_rounding,
                )

    def _descending_process_price_included_taxes_batch(self, batch, base, precision_rounding, extra_computation_values):
        # EXTENDS 'account'
        super()._descending_process_price_included_taxes_batch(batch, base, precision_rounding, extra_computation_values)
        if batch['price_include'] and batch['amount_type'] == 'code':
            batch['computed'] = True
            tax_values_list = batch['taxes']
            batch_base = base - sum(tax_values['tax_amount_factorized'] for tax_values in tax_values_list)
            for tax_values in tax_values_list:
                tax_values['base'] = tax_values['batch_base'] = tax_values['grouping_base'] = batch_base

    def _ascending_process_taxes_batch(self, batch, base, precision_rounding, extra_computation_values):
        # EXTENDS 'account'
        super()._ascending_process_taxes_batch(batch, base, precision_rounding, extra_computation_values)
        if not batch['price_include'] and batch['amount_type'] == 'code':
            batch['computed'] = True
            for tax_values in batch['taxes']:
                tax_values['base'] = tax_values['batch_base'] = tax_values['grouping_base'] = base


class AccountTaxTemplatePython(models.Model):
    _inherit = 'account.tax.template'

    amount_type = fields.Selection(selection_add=[
        ('code', 'Python Code')
    ], ondelete={'code': 'cascade'})

    python_compute = fields.Text(string='Python Code', default="result = price_unit * 0.10",
        help="Compute the amount of the tax by setting the variable 'result'.\n\n"
            ":param base_amount: float, actual amount on which the tax is applied\n"
            ":param price_unit: float\n"
            ":param quantity: float\n"
            ":param product: product.product recordset singleton or None\n"
            ":param partner: res.partner recordset singleton or None")
    python_applicable = fields.Text(string='Applicable Code', default="result = True",
        help="Determine if the tax will be applied by setting the variable 'result' to True or False.\n\n"
            ":param price_unit: float\n"
            ":param quantity: float\n"
            ":param product: product.product recordset singleton or None\n"
            ":param partner: res.partner recordset singleton or None")

    def _get_tax_vals(self, company, tax_template_to_tax):
        """ This method generates a dictionnary of all the values for the tax that will be created.
        """
        self.ensure_one()
        res = super(AccountTaxTemplatePython, self)._get_tax_vals(company, tax_template_to_tax)
        res['python_compute'] = self.python_compute
        res['python_applicable'] = self.python_applicable
        return res
