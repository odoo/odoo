# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = [
        "sale.order.line",
        # Add global alert to the order lines, rendered on the checkout page.
        # Note: alerts are transient, they are cleared after being rendered.
        "website.checkout.alert.mixin",
    ]

    name_short = fields.Char(compute="_compute_name_short")
    is_donation = fields.Boolean(compute="_compute_is_donation")

    # === COMPUTE METHODS ===#

    @api.depends("product_id.display_name")
    def _compute_name_short(self):
        """Compute a short name for this sale order line, to be used on the website where we don't
        have much space. To keep it short, instead of using the first line of the description,
        we take the product name without the internal reference.
        """
        for record in self:
            record.name_short = record.product_id.with_context(
                display_default_code=False
            ).display_name

    # === BUSINESS METHODS ===#

    def get_description_following_lines(self):
        return self.name.splitlines()[1:]

    def _get_combination_name(self):
        return self.product_id.product_template_attribute_value_ids._get_combination_name()

    def _get_line_header(self):
        if not self.product_template_attribute_value_ids:
            return self.name_short
        # not display_name because we don't want the combination name or the code.
        return self.product_id.name

    def _get_order_date(self):
        self.ensure_one()
        if self.order_id.website_id and self.state == "draft":
            # cart prices must always be computed based on the current time, not on the order
            # creation date.
            return fields.Datetime.now()
        return super()._get_order_date()

    def _get_displayed_unit_price(self):
        show_tax = self.order_id.website_id.show_line_subtotals_tax_selection
        tax_display = "total_excluded" if show_tax == "tax_excluded" else "total_included"
        is_combo = self.product_type == "combo"
        unit_price = self._get_display_price_ignore_combo() if is_combo else self.price_unit

        return self.tax_ids.compute_all(
            unit_price, self.currency_id, 1, self.product_id, self.order_partner_id
        )[tax_display]

    def _get_selected_combo_items(self):
        if self.product_id.type == "combo":
            return [
                {
                    "id": linked_line.combo_item_id.id,
                    "no_variant_ptav_ids": linked_line.product_no_variant_attribute_value_ids.ids,
                    "custom_ptavs": [
                        {
                            "id": pcav.custom_product_template_attribute_value_id.id,
                            "value": pcav.custom_value,
                        }
                        for pcav in linked_line.product_custom_attribute_value_ids
                    ],
                }
                for linked_line in self.linked_line_ids
            ]

        return None

    def _get_displayed_quantity(self):
        rounded_uom_qty = round(
            self.product_uom_qty, self.env["decimal.precision"].precision_get("Product Unit")
        )
        return (int(rounded_uom_qty) == rounded_uom_qty and int(rounded_uom_qty)) or rounded_uom_qty

    def _is_reorder_allowed(self):
        self.ensure_one()
        return (
            bool(self.product_id)
            and self.product_id._is_add_to_cart_allowed()
            and self._is_product_line()
            and not self.combo_item_id
        )

    def _get_cart_display_price(self):
        self.ensure_one()
        price_type = (
            "price_subtotal"
            if self.order_id.website_id.show_line_subtotals_tax_selection == "tax_excluded"
            else "price_total"
        )
        return sum(self._get_lines_with_price().mapped(price_type))

    def _check_validity(self):
        website = self.order_id.website_id
        if (
            not self.combo_item_id
            and website.prevent_sale
            and website._prevent_product_sale(
                self.product_template_id,
                sum(self._get_lines_with_price().mapped("price_unit")) == 0,
            )
            # Only allow zero-price exemption for zero_price mode, not for category-based prevention
            and not (
                website.prevent_sale_for == "zero_price"
                and self.product_template_id.service_tracking
                in self.env["product.template"]._get_product_types_allow_zero_price()
            )
        ):
            raise UserError(
                self.env._(
                    "The given product does not have a price therefore it cannot be added to cart."
                )
            )

    def _should_show_strikethrough_price(self):
        """Compute whether the strikethrough price should be shown.

        The strikethrough price should be shown if there is a discount on a sellable line for
        which a price unit is non-zero.

        :return: Whether the strikethrough price should be shown.
        :rtype: bool
        """
        return self.discount and self._is_sellable() and self._get_displayed_unit_price()

    def _is_sellable(self):
        """Check if a line is sellable or not, i.e the link is clickable in the cart or not.

        A line is sellable if the product is published and not a delivery line.

        :return: Whether the line is sellable or not.
        :rtype: bool
        """
        return (
            self.env.user.has_group("base.group_system") or self.product_id.is_published
        ) and not self.is_delivery

    @api.depends("product_id")
    def _compute_is_donation(self):
        for line in self:
            line.is_donation = bool(line.product_id and line.product_id._is_donation())

    def _compute_price_unit(self):
        """Override of `sale` to prevent recomputing the price of donation lines.

        Donation lines have a user-selected price that must never be overwritten by pricelist rules.
        """
        donation_lines = self.filtered("is_donation")
        super(SaleOrderLine, self - donation_lines)._compute_price_unit()

    def _compute_discount(self):
        donation_lines = self.filtered("is_donation")
        donation_lines.discount = 0.0
        super(SaleOrderLine, self - donation_lines)._compute_discount()

    def _get_max_line_qty(self):
        max_quantity = self._get_max_available_qty()
        return self.product_uom_qty + max_quantity if (max_quantity is not None) else None

    def _get_max_available_qty(self):
        """Return the max quantity of a combo product.

        It is the max quantity of its selected combo item with the lowest max quantity. If none of
        the combo items has a max quantity, then the combo product also has no max quantity.
        """
        self.ensure_one()
        cart_and_free_quantities = [
            line.order_id._get_cart_and_free_qty(line.product_id)
            for line in self._get_lines_with_price()
            if line.product_id.is_storable and not line.product_id.allow_out_of_stock_order
        ]
        max_quantities = [free_qty - cart_qty for cart_qty, free_qty in cart_and_free_quantities]
        return min(max_quantities, default=None)

    def _get_shop_warning_stock(self, desired_quantity, available_quantity):
        self.ensure_one()
        if available_quantity <= 0.0:
            return self.env._("This product is no longer available.")
        return self.env._(
            "You requested %(desired)g %(product_name)s, but only %(available)g are available in"
            " stock.",
            desired=desired_quantity,
            product_name=self.product_id.display_name,
            available=available_quantity,
        )

    def _check_availability(self):
        """Check there is sufficient stock to fulfill the cart quantity for the product in the
        current line.

        Note: `self.ensure_one()`.

        :return: True if the product is available, False otherwise.
        :rtype: bool
        """
        self.ensure_one()
        if self.product_id.is_storable and not self.product_id.allow_out_of_stock_order:
            cart_qty, avl_qty = self.order_id._get_cart_and_free_qty(self.product_id)
            if cart_qty > avl_qty:
                self._add_warning_alert(self._get_shop_warning_stock(cart_qty, max(avl_qty, 0)))
                return False
        return True

    def _show_line_in_cart(self):
        self.ensure_one()
        return self._is_product_line() and not self.combo_item_id
