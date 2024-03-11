# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    def _prepare_procurement_values(self, date=False, group=False):
        vals = super()._prepare_procurement_values(date, group)
        if not vals.get('partner_id') and self.location_id.is_subcontracting_location:
            subcontractors = self.location_id.subcontractor_ids
            vals['partner_id'] = subcontractors.id if len(subcontractors) == 1 else False
        return vals
