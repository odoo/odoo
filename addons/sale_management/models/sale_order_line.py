# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Command, Domain


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Section-related fields
    is_optional = fields.Boolean(
        string="Optional Line", copy=True, default=False
    )  # Whether this section's lines are optional in the portal.

    # === COMPUTE METHODS === #

    @api.depends("product_id")
    def _compute_name(self):
        # Take the description on the order template if the product is present in it
        super()._compute_name()
        for line in self:
            order = line.order_id
            if line.product_id and order.sale_order_template_id and line._use_template_name():
                for template_line in order.sale_order_template_id.sale_order_template_line_ids:
                    if line.product_id == template_line.product_id and template_line.name:
                        # If a specific description was set on the template, use it
                        # Otherwise the description is handled by the super call
                        lang = order.partner_id.lang
                        line.name = (
                            template_line.with_context(lang=lang).name
                            + line.with_context(
                                lang=lang
                            )._get_sale_order_line_multiline_description_variants()
                        )
                        break

    def _use_template_name(self):
        """Decide whether the quotation template description should be used for this line (if any
        template line matches the current one).
        """
        self.ensure_one()
        return True

    # === PUBLIC === #

    def save_section_template(self):
        """Create a `sale.order.template` from a section and its related lines.

        Given a section line of a sale order, this method collects the section
        itself and all its related lines, and stores them as an inactive
        ``sale.order.template`` with template_type ``section``. If a template with
        the same name and user already exists, its lines are replaced;
        otherwise, a new template is created.

        :return: created/updated section template values
        """
        self.ensure_one()
        section_lines = self.order_id.order_line.filtered(
            lambda line: (
                line.product_type != "combo"
                and not line.combo_item_id
                and self._is_line_in_section(line)
            )
        )

        domain = (
            Domain("name", "=", self.name)
            & Domain("company_id", "=", self.order_id.company_id.id)
            & Domain("template_type", "=", "section")
            & Domain("create_uid", "=", self.env.user.id)
        )

        existing_template = self.env["sale.order.template"].search(domain, limit=1)

        template_lines = [
            Command.create(section_line._prepare_template_line_values())
            for section_line in self + section_lines
        ]

        if existing_template:
            template_lines_data = [Command.clear(), *template_lines]
            # .sudo because we allow salesman to update their own templates
            existing_template.sudo().sale_order_template_line_ids = template_lines_data
            return existing_template.read(["id", "name", "create_uid"], load="")[0]

        # .sudo because we allow salesman to and maintaincreate their own templates
        new_template = (
            self
            .env["sale.order.template"]
            .sudo()
            .create({
                "name": self.name,
                "template_type": "section",
                "sale_order_template_line_ids": template_lines,
                "company_id": self.order_id.company_id.id,
                "share_template": False,
            })
        )
        return new_template.read(["id", "name", "create_uid"], load="")[0]

    # === TOOLING ===#

    def _is_line_optional(self):
        """Return whether the line is optional or not.

        A line is optional if it is directly under an optional (sub)section, or under a subsection
        which is itself under an optional section.
        """
        self.ensure_one()
        return self.parent_id.is_optional or (
            self.parent_id.display_type == "line_subsection"
            and self.parent_id.parent_id.is_optional
        )

    def _can_be_edited_on_portal(self):
        return super()._can_be_edited_on_portal() and self._is_line_optional()

    def _prepare_template_line_values(self):
        """Prepare create values for a sale order template line from a sale order line.

        :return: `sale.order.template.line` create values
        :rtype: dict
        """
        self.ensure_one()
        return {
            "name": self.name,
            "product_uom_qty": self.product_uom_qty,
            "product_uom_id": self.product_uom_id.id,
            "display_type": self.display_type,
            "is_optional": self.is_optional,
            "product_id": self.product_id.id,
            "collapse_composition": self.collapse_composition,
            "collapse_prices": self.collapse_prices,
        }
