# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


FORMULA_ALLOWED_TOKENS = {
    '(', ')',
    '+', '-', '*', '/', ',', '<', '>', '<=', '>=',
    'and', 'or', 'None',
    'base', 'quantity', 'price_unit',
    'min', 'max',
}


class AccountTaxPython(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(
        selection_add=[('code', "Custom Formula")],
        ondelete={'code': lambda recs: recs.write({'amount_type': 'percent', 'active': False})},
    )
    formula = fields.Text(
        string="Formula",
        default="price_unit * 0.10",
        help="Compute the amount of the tax.\n\n"
             ":param base: float, actual amount on which the tax is applied\n"
             ":param price_unit: float\n"
             ":param quantity: float\n"
             ":param product: A object representing the product\n"
    )
    formula_decoded_info = fields.Json(compute='_compute_formula_decoded_info')

    @api.constrains('amount_type', 'formula')
    def _check_amount_type_code_formula(self):
        for tax in self:
            if tax.amount_type == 'code':
                tax._check_formula()

    def _eval_taxes_computation_prepare_product_fields(self):
        # EXTENDS 'account'
        field_names = super()._eval_taxes_computation_prepare_product_fields()
        for tax in self.filtered(lambda tax: tax.amount_type == 'code'):
            field_names.update(tax.formula_decoded_info['product_fields'])
        return field_names

    def _eval_taxes_computation_prepare_product_uom_fields(self):
        # EXTENDS 'account'
        field_names = super()._eval_taxes_computation_prepare_product_uom_fields()
        for tax in self.filtered(lambda tax: tax.amount_type == 'code'):
            field_names.update(tax.formula_decoded_info['product_uom_fields'])
        return field_names

    @api.depends('formula')
    def _compute_formula_decoded_info(self):
        for tax in self:
            if tax.amount_type != 'code':
                tax.formula_decoded_info = None
                continue

            formula = (tax.formula or '0.0').strip()
            formula_decoded_info = {
                'js_formula': formula,
                'py_formula': formula,
            }

            product_fields = set()
            groups = re.findall(r'((?:product\.)(?P<field>\w+))+', formula) or []
            Product = self.env['product.product']
            for group in groups:
                field_name = group[1]
                if field_name in Product and not Product._fields[field_name].relational:
                    product_fields.add(field_name)
                    formula_decoded_info['py_formula'] = formula_decoded_info['py_formula'].replace(f"product.{field_name}", f"product['{field_name}']")
            formula_decoded_info['product_fields'] = list(product_fields)

            product_uom_fields = set()
            groups = re.findall(r'((?:uom\.)(?P<field>\w+))+', formula) or []
            Uom = self.env['uom.uom']
            for group in groups:
                field_name = group[1]
                if field_name in Uom and not Uom._fields[field_name].relational:
                    product_uom_fields.add(field_name)
                    formula_decoded_info['py_formula'] = formula_decoded_info['py_formula'].replace(f"uom.{field_name}", f"uom['{field_name}']")
            formula_decoded_info['product_uom_fields'] = list(product_uom_fields)

            tax.formula_decoded_info = formula_decoded_info

    def _check_formula(self):
        """ Check the formula is passing the minimum check to ensure the compatibility between both evaluation
        in python & javascript.
        """
        self.ensure_one()

        def get_number_size(formula, i):
            starting_i = i
            seen_separator = False
            while i < len(formula):
                if formula[i].isnumeric():
                    i += 1
                elif formula[i] == '.' and (i - starting_i) > 0 and not seen_separator:
                    i += 1
                    seen_separator = True
                else:
                    break
            return i - starting_i

        formula_decoded_info = self.formula_decoded_info
        allowed_tokens = (
            FORMULA_ALLOWED_TOKENS
            .union(f"product['{field_name}']" for field_name in formula_decoded_info['product_fields'])
            .union(f"uom['{field_name}']" for field_name in formula_decoded_info['product_uom_fields'])
        )
        formula = formula_decoded_info['py_formula']

        i = 0
        while i < len(formula):

            if formula[i] == ' ':
                i += 1
                continue

            continue_needed = False
            # Token consumption should be greedy, so the set of allowed tokens should be
            # sorted from longer to shorter. Otherwise, if the set has '>' before '>=',
            # the '>=' token will raise an error. This is because the '>' is consumed and
            # then it leaves the '=' character next, wich is not in the allowed_tokens.
            for token in sorted(allowed_tokens, key=len, reverse=True):
                if formula[i:i + len(token)] == token:
                    i += len(token)
                    continue_needed = True
                    break
            if continue_needed:
                continue

            number_size = get_number_size(formula, i)
            if number_size > 0:
                i += number_size
                continue

            raise ValidationError(_("Malformed formula '%(formula)s' at position %(position)s", formula=formula, position=i))

    @api.model
    def _eval_tax_amount_formula(self, raw_base, evaluation_context):
        """ Evaluate the formula of the tax passed as parameter.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param tax_data:          The values of a tax returned by '_prepare_taxes_computation'.
        :param evaluation_context:  The context created by '_eval_taxes_computation_prepare_context'.
        :return:                    The tax base amount.
        """
        self._check_formula()

        # Safe eval.
        formula_context = {
            'price_unit': evaluation_context['price_unit'],
            'quantity': evaluation_context['quantity'],
            'product': evaluation_context['product'],
            'uom': evaluation_context['uom'],
            'base': raw_base,
            'min': min,
            'max': max,
        }
        try:
            return safe_eval(
                self.formula_decoded_info['py_formula'],
                globals_dict=formula_context,
                locals_dict={},
                locals_builtins=False,
                nocopy=True,
            )
        except ZeroDivisionError:
            return 0.0

    def _eval_tax_amount_fixed_amount(self, batch, raw_base, evaluation_context):
        # EXTENDS 'account'
        if self.amount_type == 'code':
            return self._eval_tax_amount_formula(raw_base, evaluation_context)
        return super()._eval_tax_amount_fixed_amount(batch, raw_base, evaluation_context)
