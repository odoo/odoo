# -*- coding: utf-8 -*-

from openerp import models, fields, api

class account_tax_python(models.Model):
    _inherit = "account.tax"

    def __init__(self, parent, cr):
        super(account_tax_python, self).__init__(parent, cr)
        option = ('code', 'Python Code')
        type_selection = self._columns['amount_type'].selection
        if option not in type_selection:
            type_selection.append(option)

    python_compute = fields.Text(string='Python Code', default="result = price_unit * 0.10",
        help="Compute the amount of the tax by setting the variable 'result'."
            ":param base_amount: float, actual amount on which the tax is applied\n"
            ":param price_unit: float\n"
            ":param quantity: float\n"
            ":param product: product.product recordset singleton or None\n"
            ":param partner: res.partner recordset singleton or None")
    python_applicable = fields.Text(string='Applicable Code', default="result = True",
        help="Determine if the tax will be applied by setting the variable 'result' to True or False."
            ":param price_unit: float\n"
            ":param quantity: float\n"
            ":param product: product.product recordset singleton or None\n"
            ":param partner: res.partner recordset singleton or None")


    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        self.ensure_one()
        if self.amount_type == 'code':
            localdict = {'base_amount': base_amount, 'price_unit':price_unit, 'quantity': quantity, 'product':product, 'partner':partner}
            exec self.python_compute in localdict
            return localdict['result']
        return super(account_tax_python, self)._unit_compute(base_amount, price_unit, quantity, product, partner)

    @api.v8
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        taxes = self.env['account.tax']
        for tax in self:
            localdict = {'price_unit':price_unit, 'quantity': quantity, 'product':product, 'partner':partner}
            exec tax.python_applicable in localdict
            if localdict.get('result', False):
                taxes += tax
        return super(account_tax_python, taxes).compute_all(price_unit, currency, quantity, product, partner)
