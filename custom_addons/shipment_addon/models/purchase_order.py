from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection(selection_add=[("temptative", "Temptative")])


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    qty_min = fields.Float(string="Quantity min")
    qty_max = fields.Float(string="Quantity max")

    batch_id = fields.Many2one("ag.batch", string="Batch ID")
