# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval


class AccountTaxPython(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(selection_add=[('code', 'Python Code')])

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

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        self.ensure_one()
        if product and product._name == 'product.template':
            product = product.product_variant_id
        if self.amount_type == 'code':
            company = self.env.user.company_id
            localdict = {'base_amount': base_amount, 'price_unit':price_unit, 'quantity': quantity, 'product':product, 'partner':partner, 'company': company}
            safe_eval(self.python_compute, localdict, mode="exec", nocopy=True)
            return localdict['result']
        return super(AccountTaxPython, self)._compute_amount(base_amount, price_unit, quantity, product, partner)

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        taxes = self.filtered(lambda r: r.amount_type != 'code')
        company = self.env.user.company_id
        if product and product._name == 'product.template':
            product = product.product_variant_id
        for tax in self.filtered(lambda r: r.amount_type == 'code'):
            localdict = self._context.get('tax_computation_context', {})
            localdict.update({'price_unit': price_unit, 'quantity': quantity, 'product': product, 'partner': partner, 'company': company})
            safe_eval(tax.python_applicable, localdict, mode="exec", nocopy=True)
            if localdict.get('result', False):
                taxes += tax
        return super(AccountTaxPython, taxes).compute_all(price_unit, currency, quantity, product, partner)


class AccountTaxTemplatePython(models.Model):
    _inherit = 'account.tax.template'

    amount_type = fields.Selection(selection_add=[('code', 'Python Code')])

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
