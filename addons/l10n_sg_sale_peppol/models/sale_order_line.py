from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    l10n_sg_ubl_line_item_ref = fields.Char("Order line reference ID for UBL BIS 3 advanced order documents")
    l10n_sg_delivery_start = fields.Datetime("Requested Delivery From", copy=False)
    l10n_sg_delivery_end = fields.Datetime("Requested Delivery By", copy=False)
    l10n_sg_line_note = fields.Text("Order Line Note", copy=False)
