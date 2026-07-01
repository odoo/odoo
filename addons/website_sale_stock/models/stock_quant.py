# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.model_create_multi
    def create(self, vals_list):
        quants = super().create(vals_list)
        templates = (
            quants
            .filtered(lambda q: q.location_id.usage == "internal")
            .mapped("product_id.product_tmpl_id")
            .filtered("is_storable")
        )
        templates._sync_website_published_state()
        return quants

    def write(self, vals):
        if "quantity" not in vals and "reserved_quantity" not in vals:
            return super().write(vals)
        templates = (
            self
            .filtered(lambda q: q.location_id.usage == "internal")
            .mapped("product_id.product_tmpl_id")
            .filtered("is_storable")
        )
        res = super().write(vals)
        templates._sync_website_published_state()
        return res
