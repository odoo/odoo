# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

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

    @api.model
    def _ascending_process_fixed_taxes_batch(self, batch):
        # EXTENDS 'account'
        super()._ascending_process_fixed_taxes_batch(batch)

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
        # EXTENDS 'account'
        amount_type = tax_values['amount_type']
        if amount_type == 'code':
            tax = self.browse(tax_values['id'])
            raw_base = (evaluation_context['quantity'] * evaluation_context['price_unit']) + evaluation_context['extra_base']
            local_dict = {**evaluation_context, 'base_amount': raw_base}
            json.dumps(local_dict)  # Ensure it contains only json serializable data (security).
            try:
                safe_eval(tax.python_applicable, local_dict, mode="exec", nocopy=True)
            except Exception as e:
                raise UserError(_(
                    "You entered invalid code %r in %r taxes\n\nError : %s",
                    tax.python_applicable,
                    tax_values['name'],
                    e
                )) from e
            is_applicable = local_dict.get('result', False)
            if not is_applicable:
                return

            try:
                safe_eval(tax.python_compute, local_dict, mode="exec", nocopy=True)
            except Exception as e:
                raise UserError(_(
                    "You entered invalid code %r in %r taxes\n\nError : %s",
                    tax.python_compute,
                    tax_values['name'],
                    e
                )) from e
            return local_dict.get('result', 0.0)
        return super()._eval_tax_amount(tax_values, evaluation_context)
