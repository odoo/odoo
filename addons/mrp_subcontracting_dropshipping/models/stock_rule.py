# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        if 'partner_id' not in values[0] and self.location_dest_id.is_subcontracting_location:
            values[0]['partner_id'] = values[0]['group_id'].partner_id.id
        return super()._prepare_purchase_order(company_id, origins, values)
