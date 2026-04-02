# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductCatalogLineMixin(models.AbstractModel):
    _inherit = 'product.catalog.line.mixin'

    def _consider_in_catalog(self, parent_record, *, section_id=None, **kwargs) -> bool:
        # Only consider the lines in the current section (if any)
        return super()._consider_in_catalog(parent_record, **kwargs) and (
            not parent_record._has_sections() or self._is_in_section(section_id)
        )

    def _is_in_section(self, section_id=None) -> bool:
        """Check if line belongs to given section or subsection in catalog."""
        self.ensure_one()

        section_id = section_id or self.env.context.get('section_id')
        if not section_id:
            # Line should not belong to any section.
            return not self.parent_id

        return self.browse(section_id)._is_line_in_section(self)

    def _get_product_catalog_lines_data(self, parent_record, **kwargs) -> dict:
        """Override of `product` to add the subtotal."""
        vals = super()._get_product_catalog_lines_data(parent_record, **kwargs)

        if parent_record._has_sections():
            vals["subtotal"] = sum(self.mapped("price_subtotal"))

        return vals

    # TODO VFE make (sub)section mixin
    def _is_line_in_section(self, line):
        """Return whether the line is a direct or indirect child of the section."""
        self.ensure_one()
        is_direct_child = line.parent_id == self
        is_indirect_child = (
            self.display_type == "line_section"
            and line.parent_id
            and line.parent_id.display_type == "line_subsection"
            and line.parent_id.parent_id == self
        )
        return is_direct_child or is_indirect_child
