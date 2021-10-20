# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def get_products_from_cache(self):
        loading_info = self._loader_info_product_product()
        fields_str = str(loading_info["fields"])
        domain_str = str([list(item) if isinstance(item, (list, tuple)) else item for item in loading_info["domain"]])
        pos_cache = self.env['pos.cache']
        cache_for_user = pos_cache.search([
            ('id', 'in', self.config_id.cache_ids.ids),
            ('compute_user_id', '=', self.env.uid),
            ('product_domain', '=', domain_str),
            ('product_fields', '=', fields_str),
        ])

        if not cache_for_user:
            cache_for_user = pos_cache.create({
                'config_id': self.config_id.id,
                'product_domain': domain_str,
                'product_fields': fields_str,
                'compute_user_id': self.env.uid
            })
            cache_for_user.refresh_cache()

        return cache_for_user.cache2json()

    def _get_pos_ui_product_product(self, params):
        """
        Replace the way products are loaded. We only load the first 100000 products.
        The UI will make further requests of the remaining products.
        """
        records = self.get_products_from_cache()
        return records[:100000]

    def get_cached_products(self, start, end):
        records = self.get_products_from_cache()
        return records[start:end]

    def get_total_products_count(self):
        records = self.get_products_from_cache()
        return len(records)
