# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_procurement_values(self, move_vals, product, old_values):
        vals = super()._prepare_procurement_values(move_vals, product, old_values)
        partner = self.env['procurement.group'].browse(move_vals['group_id']).partner_id
        if not vals.get('partner_id') and partner and self.location_src_id.is_subcontracting_location:
            vals['partner_id'] = partner.id
        return vals

    def _prepare_purchase_order(self, company_id, origins, values):
        if 'partner_id' not in values[0] \
            and (company_id.subcontracting_location_id.parent_path in self.location_dest_id.parent_path
                 or self.location_dest_id.is_subcontracting_location):
            values[0]['partner_id'] = values[0]['group_id'].partner_id.id
        return super()._prepare_purchase_order(company_id, origins, values)

    def _make_po_get_domain(self, company_id, values, partner):
        domain = super()._make_po_get_domain(company_id, values, partner)
        if values.get('partner_id', False):
            domain += (('dest_address_id', '=', values.get('partner_id')),)
        return domain
