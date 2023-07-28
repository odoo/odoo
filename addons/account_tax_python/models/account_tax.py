# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
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

    def _prepare_dict_for_taxes_computation(self):
        # EXTENDS 'account'
        tax_values = super()._prepare_dict_for_taxes_computation()
        tax_values.update({
            'python_compute': self.python_compute,
            'python_applicable': self.python_applicable,
        })
        return tax_values

    @api.model
    def _ascending_process_fixed_taxes_batch(self, batch, fixed_multiplicator=1):
        # EXTENDS 'account'
        super()._ascending_process_fixed_taxes_batch(batch, fixed_multiplicator=fixed_multiplicator)

        if batch['amount_type'] == 'code':
            batch['computed'] = 'tax'

    @api.model
    def _descending_process_price_included_taxes_batch(self, batch):
        # EXTENDS 'account'
        super()._descending_process_price_included_taxes_batch(batch)

        if batch['price_include'] and batch['amount_type'] == 'code':
            batch['computed'] = True

    @api.model
    def _ascending_process_taxes_batch(self, batch):
        # EXTENDS 'account'
        super()._ascending_process_taxes_batch(batch)

        if not batch['price_include'] and batch['amount_type'] == 'code':
            batch['computed'] = True

    @api.model
    def _eval_tax_amount(self, tax_values, evaluation_context):
        amount_type = tax_values['amount_type']
        if amount_type == 'code':
            raw_base = (evaluation_context['quantity'] * evaluation_context['price_unit']) + evaluation_context['extra_base']
            local_dict = {**evaluation_context, 'base_amount': raw_base}
            try:
                safe_eval(tax_values['python_applicable'], local_dict, mode="exec", nocopy=True)
            except Exception as e: # noqa: BLE001
                raise UserError(_(
                    "You entered invalid code %r in %r taxes\n\nError : %s",
                    tax_values['python_applicable'],
                    tax_values['name'],
                    e
                )) from e
            is_applicable = local_dict.get('result', False)
            if not is_applicable:
                return

            local_dict = {**evaluation_context, 'base_amount': raw_base}
            try:
                safe_eval(tax_values['python_compute'], local_dict, mode="exec", nocopy=True)
            except Exception as e: # noqa: BLE001
                raise UserError(_(
                    "You entered invalid code %r in %r taxes\n\nError : %s",
                    tax_values['python_compute'],
                    tax_values['name'],
                    e
                )) from e
            return local_dict.get('result', 0.0)
        return super()._eval_tax_amount(tax_values, evaluation_context)
