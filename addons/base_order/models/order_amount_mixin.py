"""
Order Amount Computation Mixins

Three abstract mixins that consolidate amount/tax computation logic shared
between sale.order/sale.order.line and purchase.order/purchase.order.line.

Classes:
    OrderAmountMixin — order-level amounts and tax totals
    OrderLineAmountMixin — line-level pricing and tax computation
    OrderLineFieldsMixin — common structural fields and validation
"""

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


# ════════════════════════════════════════════════════════════════════
# ORDER-LEVEL AMOUNT MIXIN
# ════════════════════════════════════════════════════════════════════


class OrderAmountMixin(models.AbstractModel):
    """Order-level amount computation and tax totals.

    Consolidates the tax computation pattern that is identical in sale.order
    and purchase.order — both delegate to ``account.tax._get_tax_totals_summary()``
    via a shared helper ``_build_tax_totals_data()``.

    Hook: ``_get_additional_base_lines()`` — returns ``[]`` by default.
    Sale overrides to add early payment discount lines.

    Requires ``order.mixin`` fields: ``currency_id``, ``company_id``,
    ``payment_term_id``.  Requires ``line_ids`` from the concrete model.
    """

    _name = "order.amount.mixin"
    _description = "Order Amount Computation"

    # ─── Currency (required for Monetary fields) ───────────────────

    currency_id = fields.Many2one("res.currency")

    # ─── Amount Fields ─────────────────────────────────────────────

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount",
        compute="_compute_amounts",
        store=True,
        tracking=True,
    )
    amount_tax = fields.Monetary(
        string="Taxes",
        compute="_compute_amounts",
        store=True,
        tracking=True,
    )
    amount_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        store=True,
        tracking=True,
    )
    tax_totals = fields.Binary(
        compute="_compute_tax_totals",
        exportable=False,
    )

    # ─── Invoice Amount Fields (order-level sums) ──────────────────

    amount_taxexc_invoiced = fields.Monetary(
        string="Already Invoiced (Tax Excl.)",
        compute="_compute_amounts_invoice",
    )
    amount_taxinc_invoiced = fields.Monetary(
        string="Already Invoiced (Tax Incl.)",
        compute="_compute_amounts_invoice",
    )
    amount_taxexc_to_invoice = fields.Monetary(
        string="Un-invoiced Balance (Tax Excl.)",
        compute="_compute_amounts_invoice",
    )
    amount_taxinc_to_invoice = fields.Monetary(
        string="Un-invoiced Balance (Tax Incl.)",
        compute="_compute_amounts_invoice",
    )

    # ─── Tax Computation ───────────────────────────────────────────

    def _build_tax_totals_data(self):
        """Compute tax totals summary for a single order.

        Shared helper called by both ``_compute_amounts`` (stored monetary fields)
        and ``_compute_tax_totals`` (non-stored display field).

        Hook: override ``_get_additional_base_lines()`` to inject extra base
        lines (e.g. early payment discount in sale.order).

        :returns: dict with ``base_amount_currency``, ``tax_amount_currency``,
                  ``total_amount_currency``, and detailed tax breakdown.
        """
        self.ensure_one()
        AccountTax = self.env["account.tax"]
        order_lines = self.line_ids.filtered(lambda x: not x.display_type)
        base_lines = [
            line._prepare_base_line_for_taxes_computation() for line in order_lines
        ]
        base_lines += self._get_additional_base_lines()
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        return AccountTax._get_tax_totals_summary(
            base_lines=base_lines,
            currency=self.currency_id or self.company_id.currency_id,
            company=self.company_id,
        )

    def _get_additional_base_lines(self):
        """Hook for additional base lines in tax computation.

        Override in child models to add extra base lines.
        Sale uses this for early payment discount lines.

        :returns: list of base line dicts for tax computation
        """
        return []

    @api.depends_context("lang")
    @api.depends(
        "company_id", "currency_id", "payment_term_id", "line_ids.price_subtotal"
    )
    def _compute_amounts(self):
        """Compute stored amount fields from tax totals."""
        for order in self:
            tax_totals = order._build_tax_totals_data()
            order.amount_untaxed = tax_totals["base_amount_currency"]
            order.amount_tax = tax_totals["tax_amount_currency"]
            order.amount_total = tax_totals["total_amount_currency"]

    @api.depends_context("lang")
    @api.depends(
        "company_id", "currency_id", "payment_term_id", "line_ids.price_subtotal"
    )
    def _compute_tax_totals(self):
        """Compute the non-stored ``tax_totals`` display field.

        Separated from ``_compute_amounts`` to avoid inconsistent store
        attribute warnings (Binary, not stored).
        """
        for order in self:
            order.tax_totals = order._build_tax_totals_data()

    # ─── Invoice Amounts ───────────────────────────────────────────

    @api.depends(
        "line_ids.amount_taxexc_invoiced",
        "line_ids.amount_taxexc_to_invoice",
        "line_ids.amount_taxinc_invoiced",
        "line_ids.amount_taxinc_to_invoice",
    )
    def _compute_amounts_invoice(self):
        """Compute order-level invoice amounts as sum of line amounts.

        Single-pass iteration — identical in sale.order and purchase.order.
        """
        for order in self:
            taxexc_invoiced = 0.0
            taxexc_to_invoice = 0.0
            taxinc_invoiced = 0.0
            taxinc_to_invoice = 0.0

            for line in order.line_ids:
                taxexc_invoiced += line.amount_taxexc_invoiced
                taxexc_to_invoice += line.amount_taxexc_to_invoice
                taxinc_invoiced += line.amount_taxinc_invoiced
                taxinc_to_invoice += line.amount_taxinc_to_invoice

            order.amount_taxexc_invoiced = taxexc_invoiced
            order.amount_taxexc_to_invoice = taxexc_to_invoice
            order.amount_taxinc_invoiced = taxinc_invoiced
            order.amount_taxinc_to_invoice = taxinc_to_invoice


# ════════════════════════════════════════════════════════════════════
# LINE-LEVEL AMOUNT MIXIN
# ════════════════════════════════════════════════════════════════════


class OrderLineAmountMixin(models.AbstractModel):
    """Line-level amount computation and tax calculation.

    Provides:
    - Standard pricing fields (``product_qty``, ``price_unit``, ``discount``,
      ``tax_ids``)
    - Batched tax computation (``_compute_amounts``, grouped by company)
    - UoM quantity conversion (``product_uom_qty``)
    - Base line preparation for the tax engine

    Fields defined **without** compute — each concrete model provides its own:
    ``product_qty``, ``price_unit``, ``discount``, ``tax_ids``.
    These share the same structure but have model-specific compute logic
    (pricelist vs supplier info, sale taxes vs purchase taxes).

    Requires ``order_id``, ``company_id``, ``currency_id`` from the concrete
    model (typically as related fields).
    """

    _name = "order.line.amount.mixin"
    _description = "Order Line Amount Computation"

    # ─── Currency (required for Monetary fields) ───────────────────

    currency_id = fields.Many2one("res.currency")

    # ─── Pricing Fields (compute provided by concrete models) ──────

    product_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
    )
    product_uom_qty = fields.Float(
        string="Quantity (Reference UoM)",
        digits="Product Unit",
        compute="_compute_product_uom_qty",
        store=True,
        precompute=True,
    )
    price_unit = fields.Float(
        string="Unit Price",
        min_display_digits="Product Price",
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        check_company=True,
    )

    # ─── Computed Amount Fields ────────────────────────────────────

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amounts",
        store=True,
        precompute=True,
    )
    price_tax = fields.Monetary(
        string="Total Tax",
        compute="_compute_amounts",
        store=True,
        precompute=True,
    )
    price_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        store=True,
        precompute=True,
    )

    # ─── Compute Methods ───────────────────────────────────────────

    @api.depends("tax_ids", "product_qty", "price_unit", "discount")
    def _compute_amounts(self):
        """Compute line amounts with taxes, batched by company.

        Uses the optimized pattern from sale.order.line — groups base lines
        by company for batch tax computation instead of per-line calls.
        """
        AccountTax = self.env["account.tax"]
        lines = self.filtered(lambda l: not l.display_type)
        if not lines:
            return

        base_lines_by_company = defaultdict(list)
        line_to_base = {}
        for line in lines:
            base_line = line._prepare_base_line_for_taxes_computation()
            company = line.company_id or self.env.company
            base_lines_by_company[company].append(base_line)
            line_to_base[line.id] = base_line

        for company, base_lines in base_lines_by_company.items():
            AccountTax._add_tax_details_in_base_lines(base_lines, company)
            AccountTax._round_base_lines_tax_details(base_lines, company)

        for line in lines:
            base_line = line_to_base[line.id]
            line.price_subtotal = base_line["tax_details"]["total_excluded_currency"]
            line.price_total = base_line["tax_details"]["total_included_currency"]
            line.price_tax = line.price_total - line.price_subtotal

    @api.depends("product_id", "product_id.uom_id", "product_uom_id", "product_qty")
    def _compute_product_uom_qty(self):
        """Convert ``product_qty`` to the product's reference UoM.

        Example: 2 Cases where 1 Case = 12 Units →
        ``product_qty = 2`` (Cases), ``product_uom_qty = 24`` (Units).
        """
        for line in self:
            if line.display_type:
                line.product_uom_qty = False
                continue
            if not line.product_uom_id or not line.product_id:
                line.product_uom_qty = line.product_qty
            elif line.product_id.uom_id != line.product_uom_id:
                line.product_uom_qty = line.product_uom_id._compute_quantity(
                    line.product_qty,
                    line.product_id.uom_id,
                )
            else:
                line.product_uom_qty = line.product_qty

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """Prepare a base line dict for the ``account.tax`` computation engine.

        Provides the shared structure used by both sale and purchase.
        Sale overrides to add ``global_discount`` special type.

        :returns: dict suitable for ``account.tax._add_tax_details_in_base_lines()``
        """
        self.ensure_one()
        company = self.order_id.company_id or self.env.company
        base_values = {
            "tax_ids": self.tax_ids,
            "quantity": self.product_qty,
            "partner_id": self.order_id.partner_id,
            "currency_id": self.order_id.currency_id or company.currency_id,
            "rate": self.order_id.currency_rate,
            "name": self.name,
        }
        if self.is_downpayment:
            base_values["special_type"] = "down_payment"
        base_values.update(kwargs)
        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            self,
            **base_values,
        )


# ════════════════════════════════════════════════════════════════════
# LINE-LEVEL STRUCTURAL FIELDS MIXIN
# ════════════════════════════════════════════════════════════════════


class OrderLineFieldsMixin(models.AbstractModel):
    """Common structural fields and validation for order lines.

    Provides:
    - Standard fields (``sequence``, ``display_type``, ``product_id``, etc.)
    - Section/subsection hierarchy (``_compute_parent_id``)
    - Write validation framework (protected fields, locked orders)
    - Unlink validation (prevent deletion of confirmed lines)

    Fields that **must** be defined by concrete models:

    - ``order_id``: Many2one to the parent order
    - ``company_id``: ``related='order_id.company_id'``
    - ``currency_id``: ``related='order_id.currency_id'``
    - ``partner_id``: ``related='order_id.partner_id'``
    - ``state``: ``related='order_id.state'``
    - ``locked``: ``related='order_id.locked'`` or Boolean
    - ``parent_id``: Many2one to self (with ``compute='_compute_parent_id'``)
    """

    _name = "order.line.fields.mixin"
    _description = "Common Order Line Fields"

    # ─── Structural Fields ─────────────────────────────────────────

    sequence = fields.Integer(string="Sequence", default=10)

    display_type = fields.Selection(
        selection=[
            ("line_section", "Section"),
            ("line_subsection", "Subsection"),
            ("line_note", "Note"),
        ],
        default=False,
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        check_company=True,
        ondelete="restrict",
        index="btree_not_null",
    )

    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        ondelete="restrict",
    )

    name = fields.Text(
        string="Description",
        required=True,
    )

    is_downpayment = fields.Boolean(
        string="Is a down payment",
    )

    is_expense = fields.Boolean(
        string="Is expense",
        help="Is true if the order line comes from an expense or a vendor bill",
    )

    # ─── Section/Subsection Hierarchy ──────────────────────────────

    def _compute_parent_id(self):
        """Compute the parent section/subsection for each line.

        Hierarchy: section → subsection → product lines.
        Identical in sale.order.line and purchase.order.line.
        """
        target_lines = set(self)
        for order, lines in self.grouped("order_id").items():
            if not order:
                lines.parent_id = False
                continue
            last_section = False
            last_sub = False
            for line in order.line_ids.sorted("sequence"):
                if line.display_type == "line_section":
                    last_section = line
                    if line in target_lines:
                        line.parent_id = False
                    last_sub = False
                elif line.display_type == "line_subsection":
                    if line in target_lines:
                        line.parent_id = last_section
                    last_sub = line
                elif line in target_lines:
                    line.parent_id = last_sub or last_section

    # ─── Write Validation ──────────────────────────────────────────

    def write(self, vals):
        """Validate write operations before persisting.

        Dispatches to validation methods registered via
        ``_get_validate_write_vals_methods()``.
        """
        self._validate_write_vals(vals)
        return super().write(vals)

    def _validate_write_vals(self, write_vals):
        """Run all registered write validators."""
        for method_name in self._get_validate_write_vals_methods():
            if hasattr(self, method_name):
                getattr(self, method_name)(write_vals)

    def _get_validate_write_vals_methods(self):
        """Return validator method names for write operations.

        Override in child models to add model-specific validators.
        Sale adds ``'_validate_write_product_and_uom'``.
        """
        return [
            "_validate_write_display_type",
            "_validate_write_locked_order",
        ]

    def _validate_write_display_type(self, write_vals):
        """Prevent changing ``display_type`` on existing lines."""
        if "display_type" not in write_vals:
            return

        new_type = write_vals.get("display_type")
        lines = self.filtered(lambda l: l.display_type != new_type)
        if not lines:
            return

        if len(lines) == 1:
            raise UserError(
                _(
                    "You cannot change the type of %(line_type)s '%(line_id)s'. "
                    "Instead, delete the current line and create a new line of the proper type.",
                    line_type=self._description.lower(),
                    line_id=self._get_line_identifier(lines[0]),
                ),
            )
        line_ids = [self._get_line_identifier(l) for l in lines[:5]]
        error_msg = ", ".join(line_ids)
        if len(lines) > 5:
            error_msg += _(" and %s more", len(lines) - 5)
        raise UserError(
            _(
                "You cannot change the type of %(count)s %(line_type)s lines (%(lines)s). "
                "Instead, delete these lines and create new lines of the proper type.",
                count=len(lines),
                line_type=self._description.lower(),
                lines=error_msg,
            ),
        )

    def _validate_write_locked_order(self, write_vals):
        """Prevent modification of protected fields on locked orders."""
        locked_lines = self.filtered(lambda l: l.locked)
        if not locked_lines:
            return

        protected_fields = self._get_protected_fields()
        protected_fields_modified = list(set(protected_fields) & set(write_vals.keys()))
        if not protected_fields_modified:
            return

        # Allow changing name for downpayment lines
        if "name" in protected_fields_modified and all(
            locked_lines.mapped("is_downpayment"),
        ):
            protected_fields_modified.remove("name")

        if not protected_fields_modified:
            return

        fields_info = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [
                    ("name", "in", protected_fields_modified),
                    ("model", "=", self._name),
                ]
            )
        )
        if fields_info:
            raise UserError(
                _(
                    "It is forbidden to modify the following fields in a locked order:\n%s",
                    "\n".join(fields_info.mapped("field_description")),
                ),
            )

    def _get_protected_fields(self):
        """Fields that should not be modified on a locked order.

        Identical in sale.order.line and purchase.order.line.
        """
        return [
            "product_id",
            "name",
            "price_unit",
            "product_uom_id",
            "product_qty",
            "tax_ids",
            "analytic_distribution",
            "discount",
        ]

    @staticmethod
    def _get_line_identifier(line):
        """Return a human-readable identifier for error messages."""
        if line.product_id:
            return line.product_id.display_name
        return line.name or str(line.id)

    # ─── Unlink Validation ─────────────────────────────────────────

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        """Prevent deletion of confirmed order lines."""
        lines_to_block = self._check_line_unlink()
        if lines_to_block:
            state_description = dict(
                self._fields["state"]._description_selection(self.env),
            )
            state_label = state_description.get(
                lines_to_block[0].state,
                lines_to_block[0].state,
            )
            raise UserError(
                _(
                    "Cannot delete a %(line_type)s which is in state '%(state)s'.",
                    line_type=self._description.lower(),
                    state=state_label,
                ),
            )

    def _check_line_unlink(self):
        """Return lines that cannot be deleted.

        Confirmed (``done``) lines without ``display_type`` cannot be deleted.
        Identical in sale.order.line and purchase.order.line.
        """
        return self.filtered(
            lambda line: line.state == "done" and not line.display_type,
        )

    # ─── Merge Support ─────────────────────────────────────────────

    def _merge_order_line(self, source_line):
        """Merge a source line into this line by combining quantities.

        Takes the best (lowest) price between the two lines.
        Identical in sale.order.line and purchase.order.line.
        Called by ``order.merge.mixin._merge_lines()``.
        """
        self.product_qty += source_line.product_qty
        self.price_unit = min(self.price_unit, source_line.price_unit)
