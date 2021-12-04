# -*- coding: utf-8 -*-

from odoo import models


class Picking(models.Model):
    _inherit = "stock.picking"

    def _send_confirmation_email(self):
        # Avoid sending Mail/SMS for POS deliveries
        pickings = self.filtered(lambda p: p.picking_type_id != p.picking_type_id.warehouse_id.pos_type_id)
        return super(Picking, pickings)._send_confirmation_email()
