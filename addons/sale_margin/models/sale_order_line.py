# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

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

    @api.onchange("margin")
    def _onchange_margin(self):
        computed_margin = self._get_subtotal() - self.purchase_price * self._get_product_qty()
        if not self.currency_id.compare_amounts(computed_margin, self.margin):
            # Nothing to do, onchange was triggered because of the compute
            return
        product_qty = self._get_product_qty()
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
        details = self.tax_ids.flatten_taxes_hierarchy().compute_all(price, handle_price_include=False, document_tax_mode=self.document_tax_mode)
        taxes = [tax["amount"] for tax in details["taxes"] if tax["price_include"]]
        # Round to remove minor precision differences introduced by tax computations
        # (e.g. 100.0004 -> 100).
        self.price_unit = self.currency_id.round(price + sum(taxes))

    def _prepare_template_line_values(self):
        vals = super()._prepare_template_line_values()
        if not self.product_id:
            vals["purchase_price"] = self.purchase_price

        return vals
