from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    l10n_sg_ubl_line_item_ref = fields.Char(
        'Order line reference ID for UBL BIS 3 advanced order documents'
    )
