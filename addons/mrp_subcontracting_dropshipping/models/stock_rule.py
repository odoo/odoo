# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import mrp_subcontracting, stock_dropshipping


class StockRule(mrp_subcontracting.StockRule, stock_dropshipping.StockRule):

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
