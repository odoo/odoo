# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.point_of_sale.models.pos_session import pos_loader


class PosSession(models.Model):
    _inherit = "pos.session"

    @pos_loader.load('product.product')
    def _load_product_product(self, model, meta_values):
        """
        Replace the way products are loaded. We only load the first 100000 products.
        The UI will make further requests of the remaining products.
        """
        domain = meta_values['domain']
        fields = meta_values['fields']
        records = self.config_id.get_products_from_cache(fields, domain)
        return records[:100000]

    def get_cached_products(self, domain, fields, start, end):
        records = self.config_id.get_products_from_cache(fields, domain)
        return records[start:end]

    def get_total_products_count(self, domain, fields):
        records = self.config_id.get_products_from_cache(fields, domain)
        return len(records)
