# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_products_from_cache(self):
        loading_info = self._loader_params_product_product()
        fields_str = str(loading_info['search_params']['fields'])
        domain_str = str([list(item) if isinstance(item, (list, tuple)) else item for item in loading_info['search_params']['domain']])
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
        If limited_products_loading is active, prefer the native way of loading products.
        Otherwise, replace the way products are loaded.
            First, we only load the first 100000 products.
            Then, the UI will make further requests of the remaining products.
        """
        if self.config_id.limited_products_loading:
            return super()._get_pos_ui_product_product(params)
        records = self.get_products_from_cache()
        self._process_pos_ui_product_product(records)
        return records[:100000]

    def get_cached_products(self, start, end):
        records = self.get_products_from_cache()
        self._process_pos_ui_product_product(records)
        return records[start:end]

    def get_total_products_count(self):
        records = self.get_products_from_cache()
        return len(records)
