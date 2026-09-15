from odoo import models

from ..tools import debug_log as dbg


class MixinProductCatalog(models.AbstractModel):
    _inherit = "mixin.product.catalog"

    def _prepare_catalog_extra_context(self):
        display_stock = self._is_display_stock_in_catalog()
        dbg.logic.debug(
            "[catalog:%s] extra context display_stock=%s",
            dbg.rec(self),
            display_stock,
        )
        return {
            **super()._prepare_catalog_extra_context(),
            "display_stock": display_stock,
        }

    def _is_display_stock_in_catalog(self):
        return False
