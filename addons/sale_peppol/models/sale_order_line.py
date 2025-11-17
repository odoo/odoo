from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order.line'

    ubl_line_item_ref = fields.Char("Order line reference ID for UBL BIS 3 advanced order documents")
