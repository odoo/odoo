# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sendcloud_parcel_ref = fields.Json("Sendcloud Parcel Reference", copy=False) # List of : int (common shipping) or List<int> (multicollo shipping)
    sendcloud_return_parcel_ref = fields.Json("Sendcloud Return Parcel Ref", copy=False)

    def _retrieve_warehouse_name(self):
        self.ensure_one()
        return self.location_id.warehouse_id.name
