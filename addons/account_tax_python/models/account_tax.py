# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

from odoo.addons.account_tax_python.tools.formula_utils import check_formula, normalize_formula


class AccountTax(models.Model):
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
                self._check_and_normalize_formula(tax.formula)

    @api.model
    def _eval_taxes_computation_prepare_product_fields(self):
        # EXTENDS 'account'
        field_names = super()._eval_taxes_computation_prepare_product_fields()
        for tax in self.filtered(lambda tax: tax.amount_type == 'code'):
            field_names.update(tax.formula_decoded_info['product_fields'])
        return field_names

    @api.depends('formula')
    def _compute_formula_decoded_info(self):
        for tax in self:
            if tax.amount_type != 'code':
                tax.formula_decoded_info = None
                continue

            py_formula, accessed_fields = self._check_and_normalize_formula(tax.formula)

            tax.formula_decoded_info = {
                'js_formula': py_formula,
                'py_formula': py_formula,
                'product_fields': list(accessed_fields),
            }

    @api.model
    def _check_and_normalize_formula(self, formula):
        """ Check the formula is passing the minimum check to ensure the compatibility between both evaluation
        in python & javascript.
        """

        def is_field_serializable(field_name):
            assert isinstance(field_name, str), "Field name must be a string"
            field = self.env['product.product']._fields.get(field_name)
            return isinstance(field, fields.Field) and not field.relational

        transformed_formula, accessed_fields = normalize_formula(
            self.env,
            (formula or '0.0').strip(),
            field_predicate=is_field_serializable,
        )
        check_formula(self.env, transformed_formula)
        return transformed_formula, accessed_fields

    def _eval_tax_amount_formula(self, raw_base, evaluation_context):
        """ Evaluate the formula of the tax passed as parameter.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param raw_base:
        :param evaluation_context:  The context created by '_eval_taxes_computation_prepare_context'.
        :return:                    The tax base amount.
        """
        normalized_formula, accessed_fields = self._check_and_normalize_formula(self.formula_decoded_info['py_formula'])

        # Safe eval.
        formula_context = {
            'price_unit': evaluation_context['price_unit'],
            'quantity': evaluation_context['quantity'],
            'product': evaluation_context['product'],
            'base': raw_base,
        }
        assert accessed_fields <= formula_context['product'].keys(), "product fields used in formula must be present in the product dict"
        try:
            formula_context = json.loads(json.dumps(formula_context))
        except TypeError:
            raise ValidationError(_("Only primitive types are allowed in python tax formula context."))
        try:
            return safe_eval(normalized_formula, formula_context)
        except ZeroDivisionError:
            return 0.0

    def _eval_tax_amount_fixed_amount(self, batch, raw_base, evaluation_context):
        # EXTENDS 'account'
        if self.amount_type == 'code':
            return self._eval_tax_amount_formula(raw_base, evaluation_context)
        return super()._eval_tax_amount_fixed_amount(batch, raw_base, evaluation_context)
