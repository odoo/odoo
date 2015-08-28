# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class ProductProduct(models.Model):
    _inherit = "product.template"

    expense_policy = fields.Selection(
        [('cost', 'At Cost'), ('sales_price', 'At Sales Price')],
        string='Expense Invoice Policy',
        help="If you invoice at cost, the expense will be invoiced on the sale order at the cost of the analytic line;"
        "if you invoice at sales price, the price of the product will be used instead.",
        default='cost')
