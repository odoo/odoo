# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.safe_eval import safe_eval

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
        if self.amount_type == 'code':
            company = self.env.user.company_id
            localdict = {'base_amount': base_amount, 'price_unit':price_unit, 'quantity': quantity, 'product':product, 'partner':partner, 'company': company}
            safe_eval(self.python_compute, localdict, mode="exec", nocopy=True)
            return localdict['result']
        return super(AccountTaxPython, self)._compute_amount(base_amount, price_unit, quantity, product, partner)

    @api.v8
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        taxes = self.env['account.tax']
        company = self.env.user.company_id
        for tax in self:
            localdict = {'price_unit':price_unit, 'quantity': quantity, 'product':product, 'partner':partner, 'company': company}
            safe_eval(tax.python_applicable, localdict, mode="exec", nocopy=True)
            if localdict.get('result', False):
                taxes += tax
        return super(AccountTaxPython, taxes).compute_all(price_unit, currency, quantity, product, partner)

    @api.v7
    def compute_all(self, cr, uid, ids, price_unit, currency_id=None, quantity=1.0, product_id=None, partner_id=None, context=None):
        currency = currency_id and self.pool.get('res.currency').browse(cr, uid, currency_id, context=context) or None
        product = product_id and self.pool.get('product.product').browse(cr, uid, product_id, context=context) or None
        partner = partner_id and self.pool.get('res.partner').browse(cr, uid, partner_id, context=context) or None
        ids = isinstance(ids, (int, long)) and [ids] or ids
        recs = self.browse(cr, uid, ids, context=context)
        return recs.compute_all(price_unit, currency, quantity, product, partner)

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

    def _get_tax_vals(self, company):
        """ This method generates a dictionnary of all the values for the tax that will be created.
        """
        self.ensure_one()
        res = super(AccountTaxTemplatePython, self)._get_tax_vals(company)
        res['python_compute'] = self.python_compute
        res['python_applicable'] = self.python_applicable
        return res
