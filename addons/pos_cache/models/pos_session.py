# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_pos_ui_product_product(self, params):
        """
        Replace the way products are loaded. We only load the first 100000 products.
        The UI will make further requests of the remaining products.
        """
        domain = params['domain']
        fields = params['fields']
        records = self.config_id.get_products_from_cache(fields, domain)
        return records[:100000]

    def get_cached_products(self, domain, fields, start, end):
        records = self.config_id.get_products_from_cache(fields, domain)
        return records[start:end]

    def get_total_products_count(self, domain, fields):
        records = self.config_id.get_products_from_cache(fields, domain)
        return len(records)
