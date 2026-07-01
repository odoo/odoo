# -*- coding: utf-8 -*-abs
from odoo import models


class PurchaseOrderCancel(models.TransientModel):
    _name = "purchase.order.cancel"
    _description = "Purchase Orders Cancel"

    def cancel_order(self):
        purchase_orders = self.env['purchase.order'].browse(
            self._context.get('active_ids', []))
        purchase_orders.write({'state': 'cancel'})
        return purchase_orders
