# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductCatalogLineMixin(models.AbstractModel):
    _inherit = 'product.catalog.line.mixin'

    def _consider_in_catalog(self, parent_record, *, section_id=None, **kwargs) -> bool:
        # Only consider the lines in the current section (if any)
        return super()._consider_in_catalog(parent_record, **kwargs) and (
            not parent_record._has_sections()
            or self.get_parent_section_line().id == (section_id or False)
        )
