# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_procurement_values(self):
        vals = super()._prepare_procurement_values()
        partner = self.group_id.partner_id
        if not vals.get('partner_id') and partner and self.location_id.is_subcontracting_location:
            vals['partner_id'] = partner.id
        return vals

    def _is_purchase_return(self):
        res = super()._is_purchase_return()
        return res or self._is_dropshipped_returned()

    def _is_dropshipped(self):
        res = super()._is_dropshipped()
        return res or (
                self.partner_id.property_stock_subcontractor.parent_path
                and self.partner_id.property_stock_subcontractor.parent_path in self.location_id.parent_path
                and self.location_dest_id.usage == 'customer'
        )

    def _is_dropshipped_returned(self):
        res = super()._is_dropshipped_returned()
        return res or (
                self.location_id.usage == 'customer'
                and self.partner_id.property_stock_subcontractor.parent_path
                and self.partner_id.property_stock_subcontractor.parent_path in self.location_dest_id.parent_path
        )
