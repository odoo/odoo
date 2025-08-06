# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = "Sales Order Line"

    # Section-related fields
    is_optional = fields.Boolean(
        string="Optional Line",
        copy=True,
        default=False,
    )  # Whether this section's lines are optional in the portal.

    # === COMPUTE METHODS === #

    @api.depends('product_id')
    def _compute_name(self):
        # Take the description on the order template if the product is present in it
        super()._compute_name()
        for line in self:
            if line.product_id and line.order_id.sale_order_template_id and line._use_template_name():
                for template_line in line.order_id.sale_order_template_id.sale_order_template_line_ids:
                    if line.product_id == template_line.product_id and template_line.name:
                        # If a specific description was set on the template, use it
                        # Otherwise the description is handled by the super call
                        lang = line.order_id.partner_id.lang
                        line.name = template_line.with_context(lang=lang).name + line.with_context(lang=lang)._get_sale_order_line_multiline_description_variants()
                        break

    def _use_template_name(self):
        """ Allows overriding to avoid using the template lines descriptions for the sale order lines descriptions.
    This is typically useful for 'configured' products, such as event_ticket or event_booth, where we need to have
    specific configuration information inside description instead of the default values.
    """
        self.ensure_one()
        return True

    # === TOOLING ===#

    def _is_line_optional(self):
        """ Returns whether the line is optional or not.

        A line is optional if it is directly under an optional (sub)section, or under a subsection
        which is itself under an optional section.
        """
        self.ensure_one()
        return (
            self.parent_id.is_optional
            or (
                self.parent_id.display_type == 'line_subsection'
                and self.parent_id.parent_id.is_optional
            )
        )

    def _can_be_edited_on_portal(self):
        return super()._can_be_edited_on_portal() and self._is_line_optional()
