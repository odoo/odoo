# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        if not values[0].get('partner_id') \
            and (company_id.subcontracting_location_id.parent_path in self.location_dest_id.parent_path
                 or self.location_dest_id.is_subcontract()):
            move = values[0].get('move_dest_ids')
            if move and move.raw_material_production_id.subcontractor_id:
                values[0]['partner_id'] = move.raw_material_production_id.subcontractor_id.id
        return super()._prepare_purchase_order(company_id, origins, values)

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super()._make_po_get_domain(company_id, values, partner)
        if self.location_src_id.usage == 'supplier' and self.location_dest_id.is_subcontract() and values.get('partner_id', False):
            domain += (('dest_address_id', '=', values.get('partner_id')),)
        return domain
