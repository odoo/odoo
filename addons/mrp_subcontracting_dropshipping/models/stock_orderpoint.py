# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    def _prepare_procurement_values(self, date=False):
        vals = super()._prepare_procurement_values(date)
        if not vals.get('partner_id') and self.location_id.is_subcontract() and len(self.location_id.subcontractor_ids) == 1:
            vals['partner_id'] = self.location_id.subcontractor_ids.id
        return vals
