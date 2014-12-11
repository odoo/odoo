# -*- coding: utf-8 -*-

from openerp import models, fields, api

# class account_tax_python(models.Model):
#     _name = 'account_tax_python.account_tax_python'

#     name = fields.Char()

class account_tax(models.Model):
    _inherit = "account.tax"

    python_compute = fields.Text(string='Python Code',
        default='''# price_unit\n# or False\n# product: product.product object or None\n# partner: res.partner object or None\n\nresult = price_unit * 0.10''')
    python_compute_inv = fields.Text(string='Python Code (reverse)',
        default='''# price_unit\n# product: product.product object or False\n\nresult = price_unit * 0.10''')
    applicable_type = fields.Selection([('true', 'Always'), ('code', 'Given by Python Code')], string='Applicability', required=True, default='true',
        help="If not applicable (computed through a Python code), the tax won't appear on the invoice.")
    python_applicable = fields.Text(string='Applicable Code')

    @api.multi
    def _applicable(self, price_unit, product=None, partner=None):
        res = []
        for tax in self:
            if tax.applicable_type == 'code':
                localdict = {'price_unit': price_unit, 'product': product, 'partner': partner}
                exec tax.python_applicable in localdict
                if localdict.get('result', False):
                    res.append(tax)
            else:
                res.append(tax)
        return res

    @api.multi
    def _unit_compute(self, price_unit, product=None, partner=None, quantity=0):
        taxes = self._applicable(price_unit ,product, partner)
        return super(account_tax, taxes)._unit_compute(price_unit, product=product, partner=partner, quantity=quantity)

    @api.multi
    def _unit_compute_inv(self, price_unit, product=None, partner=None):
        taxes = self._applicable(price_unit,  product, partner)
        return super(account_tax, taxes)._unit_compute_inv(price_unit, product=product, partner=partner)
        