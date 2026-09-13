from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    is_optional = fields.Boolean(
        string="Optional Line",
        default=False,
        copy=True,
    )

    @api.depends("product_id")
    def _compute_name(self):
        super()._compute_name()
        for line in self:
            if (
                line.product_id
                and line.order_id.sale_order_template_id
                and line._use_template_name()
            ):
                for (
                    template_line
                ) in line.order_id.sale_order_template_id.sale_order_template_line_ids:
                    if (
                        line.product_id == template_line.product_id
                        and template_line.name
                    ):
                        lang = line.order_id.partner_id.lang
                        line.name = (
                            template_line.with_context(lang=lang).name
                            + line.with_context(
                                lang=lang
                            )._get_line_multiline_description_variants()
                        )
                        break

    def _use_template_name(self):
        self.check_singleton()
        return True

    def _is_line_optional(self):
        self.check_singleton()
        return self.parent_id.is_optional or (
            self.parent_id.display_type == "line_subsection"
            and self.parent_id.parent_id.is_optional
        )

    def _can_be_edited_on_portal(self):
        return super()._can_be_edited_on_portal() and self._is_line_optional()
