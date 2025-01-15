# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def write(self, vals):
        res = super().write(vals)
        if 'scrap_reason_tag_ids' in vals:
            for scrap in self:
                for svl in scrap.move_ids.stock_valuation_layer_ids:
                    svl.description = scrap._get_svl_description()
        return res

    def _get_svl_description(self):
        self.ensure_one()
        if self.scrap_reason_tag_ids:
            return '%s - %s' % (self.name, ', '.join(self.scrap_reason_tag_ids.mapped('name')))
        return self.name
