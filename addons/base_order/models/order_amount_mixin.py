"""
Order Amount Computation Mixin

Consolidates all amount and tax calculation logic that was previously
duplicated across sale.order and purchase.order (600-800 lines).

This mixin provides:
- Unified tax computation using account.tax engine
- Standardized amount fields (untaxed, tax, total)
- Tax totals for display
- Single source of truth for all tax calculations

Key Insight:
Both sale.order and purchase.order use IDENTICAL logic for tax computation.
The only differences are:
- Sale adds early payment discount lines (hook provided)
- Field dependencies slightly different (but same compute method)

Designed for Odoo 19+ with no backward compatibility constraints.
"""

from odoo import api, fields, models


class OrderAmountMixin(models.AbstractModel):
    """Unified amount computation for all order types

    This mixin consolidates the tax computation logic that was 95-100%
    identical between sale.order and purchase.order. Both models delegate
    to the same account.tax engine with identical patterns.

    Usage:
        class SaleOrder(models.Model):
            _name = 'sale.order'
            _inherit = ['order.mixin', 'order.amount.mixin']

            # Optionally override for early payment discount
            def _get_additional_base_lines(self):
                return self._add_base_lines_for_early_payment_discount()

    Benefits:
    - 600-800 lines of duplicate code eliminated
    - Tax bugs fixed once, not twice
    - Consistent behavior across all order types
    - Single point of maintenance
    """

    _name = "order.amount.mixin"
    _description = "Order Amount Computation"

    # ============================================================
    # FIELDS - Standardized amount fields
    # ============================================================

    # Required fields from parent models
    currency_id = fields.Many2one("res.currency", required=True)
    company_id = fields.Many2one("res.company", required=True)

    # Amount fields - computed from line_ids
    amount_untaxed = fields.Monetary(
        string="Amount Untaxed",
        compute="_compute_amounts",
        store=True,
        tracking=True,
        help="Sum of untaxed amounts from all lines",
    )
    amount_tax = fields.Monetary(
        string="Tax Amount",
        compute="_compute_amounts",
        store=True,
        tracking=True,
        help="Sum of tax amounts from all lines",
    )
    amount_total = fields.Monetary(
        string="Total Amount",
        compute="_compute_amounts",
        store=True,
        tracking=True,
        help="Total amount including taxes",
    )

    # Tax totals for display (JSON structure)
    tax_totals = fields.Binary(
        string="Tax Totals",
        compute="_compute_tax_totals",
        exportable=False,
        help="Tax breakdown for display in views",
    )

    # ============================================================
    # COMPUTE METHODS - Single source of truth
    # ============================================================

    @api.depends("line_ids.price_subtotal", "currency_id", "company_id")
    def _compute_amounts(self):
        """Unified amount computation using account.tax engine

        This method is identical in sale.order and purchase.order.
        Both delegate to account.tax._get_tax_totals_summary() with
        the same pattern.

        The only difference is sale.order may add early payment discount
        lines via the _get_additional_base_lines() hook.

        Algorithm:
        1. Filter non-display lines
        2. Prepare base lines for tax computation
        3. Add any additional base lines (discounts, etc.)
        4. Run account.tax computation engine
        5. Extract and assign amounts
        """
        AccountTax = self.env["account.tax"]

        for order in self:
            # Get non-display lines (sections/notes don't have amounts)
            order_lines = order.line_ids.filtered(lambda x: not x.display_type)

            # Prepare base lines for tax computation
            # Each line provides dict with price, quantity, taxes, etc.
            base_lines = [
                line._prepare_base_line_for_taxes_computation() for line in order_lines
            ]

            # Hook for additional base lines (e.g., early payment discount)
            # Sale uses this for discounts, purchase doesn't
            base_lines.extend(order._get_additional_base_lines())

            # Run account.tax computation engine
            # This handles all the complex tax calculation logic
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)

            # Get tax totals summary
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id,
                company=order.company_id,
            )

            # Assign computed amounts
            order.amount_untaxed = tax_totals["base_amount_currency"]
            order.amount_tax = tax_totals["tax_amount_currency"]
            order.amount_total = tax_totals["total_amount_currency"]

    def _get_additional_base_lines(self):
        """Hook for additional base lines (e.g., discounts)

        Override in child models to add extra base lines for tax computation.

        Example in sale.order:
            def _get_additional_base_lines(self):
                return self._add_base_lines_for_early_payment_discount()

        Returns:
            list: Additional base lines for tax computation
        """
        return []

    @api.depends_context("lang")
    @api.depends("line_ids.price_subtotal", "currency_id", "company_id")
    def _compute_tax_totals(self):
        """Compute tax totals for display

        Creates JSON structure with tax breakdown for frontend rendering.
        This is identical in sale.order and purchase.order.

        The tax_totals structure is used by:
        - PDF reports to show tax breakdown
        - Web views to display tax details
        - Portal views for customer/vendor visibility
        """
        AccountTax = self.env["account.tax"]

        for order in self:
            # Same logic as _compute_amounts but returns full structure
            order_lines = order.line_ids.filtered(lambda x: not x.display_type)

            base_lines = [
                line._prepare_base_line_for_taxes_computation() for line in order_lines
            ]
            base_lines.extend(order._get_additional_base_lines())

            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)

            # This returns full JSON structure, not just amounts
            order.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id,
                company=order.company_id,
            )


class OrderLineAmountMixin(models.AbstractModel):
    """Unified line amount computation

    Consolidates line-level amount computation that was identical
    in sale.order.line and purchase.order.line.

    Key Fields:
    - price_unit: Unit price before discount/tax
    - discount: Discount percentage
    - quantity: Ordered quantity (standardized name!)
    - price_subtotal: Amount before tax
    - price_tax: Tax amount
    - price_total: Amount with tax

    Usage:
        class SaleOrderLine(models.Model):
            _name = 'sale.order.line'
            _inherit = ['order.line.amount.mixin']

            # Just implement _prepare_base_line_for_taxes_computation()
    """

    _name = "order.line.amount.mixin"
    _description = "Order Line Amount Computation"

    # ============================================================
    # FIELDS - Standardized naming
    # ============================================================

    # Required fields from parent models
    currency_id = fields.Many2one("res.currency", required=True)
    company_id = fields.Many2one("res.company", required=True)
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        help="Technical field for section/note lines",
    )

    # Pricing fields
    price_unit = fields.Monetary(
        string="Unit Price",
        digits="Product Price",
        required=True,
        help="Price per unit before discount and taxes",
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        default=0.0,
        help="Discount percentage applied to unit price",
    )

    # Quantity - STANDARDIZED NAME (not qty, not product_qty, not product_uom_qty)
    quantity = fields.Float(
        string="Quantity",
        digits="Product Unit",
        required=True,
        default=1.0,
        help="Ordered quantity in product UOM",
    )

    # Tax field (required for computation)
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        check_company=True,
        help="Taxes applied to this line",
    )

    # Computed amount fields
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amounts",
        store=True,
        help="Amount before taxes",
    )
    price_tax = fields.Monetary(
        string="Tax Amount",
        compute="_compute_amounts",
        store=True,
        help="Tax amount for this line",
    )
    price_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        store=True,
        help="Amount including taxes",
    )

    # ============================================================
    # COMPUTE METHODS
    # ============================================================

    @api.depends("quantity", "discount", "price_unit", "tax_ids")
    def _compute_amounts(self):
        """Compute line amounts with taxes

        This method is 100% identical in sale.order.line and purchase.order.line.
        Both use the same account.tax engine with identical logic.

        Note: Uses standardized 'quantity' field name instead of:
        - product_uom_qty (sale legacy name)
        - product_qty (purchase legacy name)

        Algorithm:
        1. Prepare base line dict with price, quantity, taxes
        2. Run account.tax computation
        3. Extract tax details
        4. Assign to price_subtotal, price_tax, price_total
        """
        AccountTax = self.env["account.tax"]

        for line in self.filtered(lambda x: not x.display_type):
            company = line.company_id or self.env.company

            # Prepare base line for tax computation
            # Child models must implement this method
            base_line = line._prepare_base_line_for_taxes_computation()

            # Compute taxes
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)

            # Extract computed amounts from tax details
            tax_details = base_line["tax_details"]
            line.price_subtotal = tax_details["total_excluded_currency"]
            line.price_total = tax_details["total_included_currency"]
            line.price_tax = line.price_total - line.price_subtotal

    # ============================================================
    # ABSTRACT METHODS - Must implement in child models
    # ============================================================

    def _prepare_base_line_for_taxes_computation(self):
        """Prepare base line dict for tax computation

        Child models must implement this to provide line data to tax engine.

        Returns:
            dict: Base line structure with keys:
                - record: self (the line)
                - quantity: quantity
                - price_unit: unit price
                - discount: discount percentage
                - tax_ids: taxes to apply
                - product: product (if applicable)
                - partner: partner (if applicable)
                - currency: currency
                - ... other tax computation parameters

        Example implementation:
            def _prepare_base_line_for_taxes_computation(self):
                return {
                    'record': self,
                    'quantity': self.quantity,
                    'price_unit': self.price_unit,
                    'discount': self.discount,
                    'tax_ids': self.tax_ids,
                    'product': self.product_id,
                    'partner': self.order_id.partner_id,
                    'currency': self.currency_id,
                    'company': self.company_id,
                }
        """
        raise NotImplementedError(
            f"{self._name} must implement _prepare_base_line_for_taxes_computation()"
        )


class OrderLineFieldsMixin(models.AbstractModel):
    """Common fields for order lines

    Provides standardized field definitions that are identical across
    all order line types (sale, purchase, etc.).

    This is separated from OrderLineAmountMixin to allow mixing them
    independently if needed.
    """

    _name = "order.line.fields.mixin"
    _description = "Common Order Line Fields"

    # ============================================================
    # FIELDS - Relationship and metadata
    # ============================================================

    # NOTE: Child models MUST define the following fields:
    #
    # order_id = fields.Many2one('sale.order'|'purchase.order'|etc., ...)
    # company_id = fields.Many2one('res.company', related='order_id.company_id', store=True)
    # currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True)
    # partner_id = fields.Many2one('res.partner', related='order_id.partner_id', store=True)
    # state = fields.Selection(related='order_id.state', store=True)
    #
    # These fields cannot be defined in the mixin because order_id has different
    # comodel_name for each order type, and related fields require a valid parent field.

    # Line metadata
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Gives the sequence order when displaying lines",
    )
    display_type = fields.Selection(
        [
            ("line_section", "Section"),
            ("line_note", "Note"),
        ],
        string="Display Type",
        default=False,
        help="Technical field for special line types",
    )

    # Product relationship
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        check_company=True,
        ondelete="restrict",
        index="btree_not_null",
        domain="[('sale_ok' if is_sale else 'purchase_ok', '=', True)]",
    )

    # Product UOM
    # NOTE: Child models should also define:
    # product_uom_category_id = fields.Many2one(
    #     'uom.category', related='product_id.uom_id.category_id', readonly=True
    # )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
        domain="[('category_id', '=', product_uom_category_id)]",
        ondelete="restrict",
    )

    # Description
    name = fields.Text(
        string="Description",
        required=True,
        help="Description of the product/service",
    )

    # Special line types
    is_downpayment = fields.Boolean(
        string="Is Down Payment",
        default=False,
        help="Technical field to identify down payment lines",
    )

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _is_sale(self):
        """Check if this is a sales line

        Override in child models or determine from order type.

        Returns:
            bool: True if this is a sale order line
        """
        return False  # Override in child models
