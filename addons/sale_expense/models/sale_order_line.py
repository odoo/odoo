# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    expense_ids = fields.One2many(
        comodel_name='hr.expense',
        inverse_name='sale_order_line_id',
        string='Expenses',
        readonly=True,
    )
