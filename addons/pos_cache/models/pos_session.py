# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.point_of_sale.models.pos_session import get_fields_to_load


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_product_domain_and_fields(self):
        domain = self._get_product_product_domain()
        fields = [*get_fields_to_load("product.product")]
        fields.sort()
        return domain, fields

    def _load_product_product(self, lcontext):
        """
        Replace the way products are loaded. We only load the first 100000 products.
        The UI will make further requests of the remaining products.
        """
        domain, fields = self._get_product_domain_and_fields()
        records = self.config_id.get_products_from_cache(fields, domain)
        for record in records[:100000]:
            lcontext.contents[record["id"]] = record

    def get_cached_products(self, start, end):
        domain, fields = self._get_product_domain_and_fields()
        records = self.config_id.get_products_from_cache(fields, domain)
        return records[start:end]

    def get_total_products_count(self):
        domain, fields = self._get_product_domain_and_fields()
        records = self.config_id.get_products_from_cache(fields, domain)
        return len(records)
