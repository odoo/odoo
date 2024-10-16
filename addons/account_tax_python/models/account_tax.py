# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


REGEX_FORMULA_OBJECT = re.compile(r'((?:product\[\')(?P<field>\w+)(?:\'\]))+')

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

    @api.constrains('amount_type', 'formula')
    def _check_amount_type_code_formula(self):
        for tax in self:
            if tax.amount_type != 'code':
                continue

            tax_data = tax._prepare_dict_for_taxes_computation()
            product_fields = self._eval_taxes_computation_prepare_product_fields([tax_data])
            default_product_values = self._eval_taxes_computation_prepare_product_default_values(product_fields)
            product_values = self._eval_taxes_computation_prepare_product_values(default_product_values)
            evaluation_context = self._eval_taxes_computation_prepare_context(0.0, 0.0, product_values)
            evaluation_context['extra_base'] = 0.0

            # Even we are evaluated the formula with an empty code, the compiler will check for malformed expression.
            self._eval_tax_amount(tax_data, evaluation_context)

    def _prepare_dict_for_taxes_computation(self):
        # EXTENDS 'account'
        values = super()._prepare_dict_for_taxes_computation()

        if self.amount_type == 'code':
            values.update(self._decode_formula(self.formula))

        return values

    @api.model
    def _process_as_fixed_tax_amount_batch(self, batch):
        # EXTENDS 'account'
        return batch['amount_type'] == 'code' or super()._process_as_fixed_tax_amount_batch(batch)

    @api.model
    def _eval_taxes_computation_prepare_product_fields(self, taxes_data):
        # EXTENDS 'account'
        field_names = super()._eval_taxes_computation_prepare_product_fields(taxes_data)
        for tax_data in taxes_data:
            if tax_data['amount_type'] == 'code':
                field_names.update(tax_data['_product_fields'])
        return field_names

    def _decode_formula(self, formula):
        """ Decode the formula and extract relevant values from it.

        :param formula: The value of the 'formula' field.
        """
        self.ensure_one()

        if self.amount_type != 'code':
            return {}

        formula = (formula or '0.0').strip()
        results = {
            '_js_formula': formula,
            '_py_formula': formula,
        }
        product_fields = set()

        groups = re.findall(r'((?:product\.)(?P<field>\w+))+', formula) or []
        Product = self.env['product.product']
        for group in groups:
            field_name = group[1]
            if field_name in Product and not Product._fields[field_name].relational:
                product_fields.add(field_name)
                results['_py_formula'] = results['_py_formula'].replace(f"product.{field_name}", f"product['{field_name}']")

        results['_product_fields'] = list(product_fields)
        return results

    @api.model
    def _check_formula(self, tax_data):
        """ Check the formula is passing the minimum check to ensure the compatibility between both evaluation
        in python & javascript.

        :param tax_data: The values returned by '_prepare_dict_for_taxes_computation'.
        """
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

        allowed_tokens = FORMULA_ALLOWED_TOKENS.union(f"product['{field_name}']" for field_name in tax_data['_product_fields'])
        formula = tax_data['_py_formula']

        i = 0
        while i < len(formula):

            if formula[i] == ' ':
                i += 1
                continue

            continue_needed = False
            for token in allowed_tokens:
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
    def _eval_tax_amount_formula(self, tax_data, evaluation_context):
        """ Evaluate the formula of the tax passed as parameter.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param tax_data:          The values of a tax returned by '_prepare_taxes_computation'.
        :param evaluation_context:  The context created by '_eval_taxes_computation_prepare_context'.
        :return:                    The tax base amount.
        """
        self._check_formula(tax_data)

        # Safe eval.
        raw_base = evaluation_context['raw_price'] + evaluation_context['extra_base']
        formula_context = {
            'price_unit': evaluation_context['price_unit'],
            'quantity': evaluation_context['quantity'],
            'product': evaluation_context['product'],
            'base': raw_base,
            'min': min,
            'max': max,
        }
        try:
            return safe_eval(
                tax_data['_py_formula'],
                globals_dict=formula_context,
                locals_dict={},
                locals_builtins=False,
                nocopy=True,
            )
        except ZeroDivisionError:
            return 0.0

    @api.model
    def _eval_tax_amount(self, tax_data, evaluation_context):
        # EXTENDS 'account'
        if tax_data['amount_type'] == 'code':
            return self._eval_tax_amount_formula(tax_data, evaluation_context)
        return super()._eval_tax_amount(tax_data, evaluation_context)
