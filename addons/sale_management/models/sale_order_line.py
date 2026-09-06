# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.tools import float_round


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Margin-related fields
    margin = fields.Float(
        "Margin",
        compute="_compute_margin",
        min_display_digits="Product Price",
        readonly=False,
        store=True,
        groups="base.group_user",
        copy=False,
        precompute=True,
    )
    margin_percent = fields.Float(
        "Margin (%)",
        compute="_compute_margin_percent",
        readonly=False,
        store=True,
        groups="base.group_user",
        copy=False,
        precompute=True,
    )
    purchase_price = fields.Float(
        string="Unit Cost",
        compute="_compute_purchase_price",
        min_display_digits="Product Price",
        store=True,
        readonly=False,
        copy=False,
        precompute=True,
        groups="base.group_user",
    )

    # Section-related fields
    is_optional = fields.Boolean(
        string="Optional Line", copy=True, default=False
    )  # Whether this section's lines are optional in the portal.

    # === COMPUTE METHODS ===#

    @api.depends("product_id", "company_id", "currency_id", "product_uom_id")
    def _compute_purchase_price(self):
        for line in self:
            if not line._is_product_line():
                line.purchase_price = 0.0
                continue
            if line.product_id:
                line = line.with_company(line.company_id)

                # Convert the cost to the line UoM
                product_cost = line.product_id.uom_id._compute_price(
                    line.product_id.standard_price, line.product_uom_id
                )

                line.purchase_price = line._convert_to_sol_currency(
                    product_cost, line.product_id.cost_currency_id
                )

    @api.depends("price_subtotal", "product_uom_qty", "purchase_price")
    def _compute_margin(self):
        for line in self:
            total_cost = line.purchase_price * line._get_product_qty()
            line.margin = line._get_subtotal() - total_cost

    @api.depends("margin")
    def _compute_margin_percent(self):
        for line in self:
            if line_subtotal := line._get_subtotal():
                line.margin_percent = float_round(line.margin / line_subtotal, precision_digits=4)
            else:
                line.margin_percent = None

    # === ONCHANGE METHODS ===#

    @api.onchange("margin")
    def _onchange_margin(self):
        if not (product_qty := self._get_product_qty()):
            # Nothing to do, write method raises UserError if quantity is below delivered quantity.
            return
        computed_margin = self._get_subtotal() - self.purchase_price * product_qty
        if not self.currency_id.compare_amounts(computed_margin, self.margin):
            # Nothing to do, onchange was triggered because of the compute
            return
        discount = self._get_discount()
        margin_per_qty = self.margin / product_qty
        computed_price = (margin_per_qty + self.purchase_price) / discount
        self._set_price_incl_taxes(computed_price)

    @api.onchange("margin_percent")
    def _onchange_margin_percent(self):
        subtotal = self._get_subtotal()
        if not subtotal or not self.currency_id.compare_amounts(
            self.margin_percent, self.margin / subtotal
        ):
            # Nothing to do, onchange triggered because of the compute
            return
        if self.purchase_price != 0 and self.margin_percent == 1:
            raise UserError(
                self.env._("If the cost is not 0, it is not possible to set the margin to 100%")
            )
        if self.margin_percent != 1:
            discount = self._get_discount()
            computed_price = (self.purchase_price) / ((1 - self.margin_percent) * discount)
            self._set_price_incl_taxes(computed_price)

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
            vals = {"sale_order_template_line_ids": [Command.clear(), *template_lines]}
            if existing_template.currency_id != self.order_id.currency_id:
                vals["currency_id"] = self.order_id.currency_id.id

            # .sudo because we allow salesman to update their own templates
            existing_template.sudo().write(vals)
            return existing_template.read(["id", "name", "create_uid"], load="")[0]

        # .sudo because we allow salesman to maintain and create their own templates
        new_template = (
            self
            .env["sale.order.template"]
            .sudo()
            .create({
                "name": self.name,
                "template_type": "section",
                "sale_order_template_line_ids": template_lines,
                "company_id": self.order_id.company_id.id,
                "currency_id": self.order_id.currency_id.id,
                "share_template": False,
            })
        )
        return new_template.read(["id", "name", "create_uid"], load="")[0]

    # === TOOLING ===#

    def _get_subtotal(self):
        """Return subtotal of line, used for margin calculations.
        When line is added to order from delivery, consider delivered quantity instead.

        :rtype: float
        :returns: Subtotal of the order line.
        """
        self.ensure_one()
        if self.qty_delivered and not self.product_uom_qty:
            return self.price_unit * self.qty_delivered
        return self.price_subtotal

    def _get_product_qty(self):
        """Return the quantity used for margin calculations.
        When line is added to order from delivery consider `qty_delivered` instead.

        :rtype: int
        :returns: Quantity to be considered on the current line.
        """
        self.ensure_one()
        if self.qty_delivered and not self.product_uom_qty:
            return self.qty_delivered
        return self.product_uom_qty

    def _get_discount(self):
        """Return the discount that will be applied on the order line.

        :rtype: float
        :returns: Discount applied on the order line.
        """
        self.ensure_one()
        return 1 - self.discount / 100

    def _set_price_incl_taxes(self, price):
        """Update the line price considering taxes that should be applied on.
        When margin is changed, make sure that included taxes are taken into account when updating
        the unit price.

        :param float price: The price value to assign.
        """
        self.ensure_one()
        base_line = self._prepare_base_line_for_taxes_computation(
            quantity=1, discount=0, price_unit=price, special_mode="total_excluded"
        )
        company = self.company_id or self.env.company
        self.env["account.tax"]._add_tax_details_in_base_line(base_line, company)
        self.env["account.tax"]._round_base_lines_tax_details([base_line], company)
        tax_details = base_line["tax_details"]
        self.price_unit = tax_details["raw_total_excluded_currency"] + sum(
            tax_data["raw_tax_amount_currency"]
            for tax_data in tax_details["taxes_data"]
            if tax_data["original_price_include"]
        )

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

        If the line is linked to a product, the product is stored and pricing is recomputed later.
        For product lines without a product, price, discount, and taxes are copied explicitly.

        :return: `sale.order.template.line` create values
        :rtype: dict
        """
        self.ensure_one()
        vals = {
            "sequence": self.sequence,
            "name": self.name,
            "product_id": self.product_id.id,
            "product_uom_qty": self.product_uom_qty,
            "product_uom_id": self.product_uom_id.id,
            "display_type": self.display_type,
            "is_optional": self.is_optional,
            "collapse_composition": self.collapse_composition,
            "collapse_prices": self.collapse_prices,
            "section_qty": self.section_qty,
            "section_uom_id": self.section_uom_id.id,
            "product_no_variant_attribute_value_ids": [
                Command.set(self.product_no_variant_attribute_value_ids.ids)
            ],
            "product_custom_attribute_value_ids": [
                Command.create({
                    "custom_product_template_attribute_value_id": (
                        pacv.custom_product_template_attribute_value_id.id
                    ),
                    "custom_value": pacv.custom_value,
                })
                for pacv in self.product_custom_attribute_value_ids
            ],
        }

        if not self.product_id:
            vals.update({
                "tax_ids": [Command.set(self.tax_ids.ids)],
                "discount": self.discount,
                "price_unit": self.price_unit,
                "purchase_price": self.purchase_price,
            })
        else:
            # Try to remove the default product display_name from the line name
            vals["name"] = self.name.removeprefix(f"{self.product_id.display_name}").removeprefix(
                "\n"
            )

        return vals
