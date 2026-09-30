# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductCatalogMixin(models.AbstractModel):
    _inherit = "product.catalog.mixin"

    def _get_action_add_from_catalog_extra_context(self):
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            'display_stock': self._is_display_stock_in_catalog(),
        }

    def _is_display_stock_in_catalog(self):
        return False
