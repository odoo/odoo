from collections import defaultdict
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from pytz import UTC

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.libs.numbers.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.translate import _

from odoo.addons.purchase import const


class PurchaseOrderLine(models.Model):
    _name = "purchase.order.line"
    _inherit = ["analytic.mixin"]
    _description = "Purchase Order Line"
    _check_company_auto = True
    _order = "order_id, sequence, id"
    _rec_names_search = ["name", "order_id.name"]

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Order Reference",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="order_id.company_id",
        comodel_name="res.company",
        string="Company",
        store=True,
        precompute=True,
        readonly=True,
        index=True,
    )
    company_price_include = fields.Selection(
        related="company_id.account_price_include",
    )
    currency_id = fields.Many2one(
        related="order_id.currency_id",
        comodel_name="res.currency",
        string="Currency",
        store=True,
        precompute=True,
        depends=["order_id.currency_id"],
    )
    partner_id = fields.Many2one(
        related="order_id.partner_id",
        comodel_name="res.partner",
        string="Vendor",
        store=True,
        precompute=True,
        index="btree_not_null",
    )
    user_id = fields.Many2one(
        related="order_id.user_id",
        comodel_name="res.users",
        string="Buyer",
        store=True,
        precompute=True,
        index="btree_not_null",
    )
    date_order = fields.Datetime(
        related="order_id.date_order",
        string="Order Date",
        store=True,
        precompute=True,
        index=True,
    )
    date_confirmed = fields.Datetime(
        related="order_id.date_confirmed",
        string="Confirmation Date",
        store=True,
        precompute=True,
        index=True,
    )
    state = fields.Selection(
        related="order_id.state",
        string="Order Status",
        store=True,
        precompute=True,
    )
    fiscal_position_id = fields.Many2one(
        related="order_id.fiscal_position_id",
        comodel_name="account.fiscal.position",
    )
    locked = fields.Boolean(
        related="order_id.locked",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    display_type = fields.Selection(
        selection=[
            ("line_section", "Section"),
            ("line_subsection", "Subsection"),
            ("line_note", "Note"),
        ],
        default=False,
    )
    is_downpayment = fields.Boolean(
        string="Is a down payment",
    )
    is_expense = fields.Boolean(
        string="Is expense",
        help="Is true if the sales order line comes from an expense or a vendor bills",
    )

    # Section-related fields
    parent_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="Parent Section Line",
        compute="_compute_parent_id",
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        change_default=True,
        check_company=True,
        domain=lambda self: self._domain_product_id(),
        ondelete="restrict",
        index="btree_not_null",
    )
    product_categ_id = fields.Many2one(
        related="product_id.categ_id",
    )
    product_type = fields.Selection(
        related="product_id.type",
        depends=["product_id"],
    )
    product_template_attribute_value_ids = fields.Many2many(
        related="product_id.product_template_attribute_value_ids",
        depends=["product_id"],
    )
    purchase_line_warn_msg = fields.Text(
        compute="_compute_purchase_line_warn_msg",
    )
    product_no_variant_attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        string="Product attribute values that do not create variants",
        ondelete="restrict",
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        compute="_compute_tax_ids",
        store=True,
        precompute=True,
        readonly=False,
        check_company=True,
        domain="[('type_tax_use', '=', 'purchase')]",
        context={"active_test": False, "hide_original_tax_ids": True},
    )
    allowed_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_allowed_uom_ids",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        compute="_compute_product_uom_id",
        store=True,
        precompute=True,
        readonly=False,
        domain="[('id', 'in', allowed_uom_ids)]",
        ondelete="restrict",
    )
    product_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        compute="_compute_product_qty",
        store=True,
        precompute=True,
        readonly=False,
    )
    product_uom_qty = fields.Float(
        string="Quantity (Reference UoM)",
        digits="Product Unit",
        compute="_compute_product_uom_qty",
        store=True,
        precompute=True,
    )
    selected_seller_id = fields.Many2one(
        comodel_name="product.supplierinfo",
        compute="_compute_selected_seller_id",
        store=True,
        precompute=True,
        help="The vendor pricelist entry that applies to this line based on "
        "partner, product, quantity, UoM, and date.",
    )
    name = fields.Text(
        string="Description",
        required=True,
        compute="_compute_name",
        store=True,
        precompute=True,
        readonly=False,
    )
    price_unit = fields.Float(
        string="Unit Price",
        min_display_digits="Product Price",
        compute="_compute_price_and_discount",
        store=True,
        precompute=True,
        readonly=False,
        aggregator="avg",
    )
    price_unit_auto = fields.Float(
        string="Automatic Price",
        min_display_digits="Product Price",
        compute="_compute_price_and_discount",
        store=True,
        precompute=True,
        copy=True,
        help="Price from vendor/product. Compared with price_unit to detect manual overrides. "
        "When price_unit != price_unit_auto, the price is considered manually set.",
    )
    price_unit_product_uom = fields.Float(
        string="Unit Price Product UoM",
        min_display_digits="Product Price",
        compute="_compute_price_unit_product_uom",
        help="The Price of one unit of the product's Unit of Measure",
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        compute="_compute_price_and_discount",
        store=True,
        precompute=True,
        readonly=False,
        aggregator="avg",
    )
    date_planned = fields.Datetime(
        string="Expected Arrival",
        compute="_compute_date_planned",
        store=True,
        precompute=True,
        readonly=False,
        index=True,
        help="Delivery date expected from vendor. This date respectively defaults to vendor pricelist lead time then today's date.",
    )
    date_is_manual = fields.Boolean(
        string="Date Manually Set",
        default=False,
        help="If checked, the expected arrival date was manually set and won't be "
        "automatically updated when the seller or order date changes.",
    )
    price_unit_discounted_taxexc = fields.Float(
        string="Unit Price Discounted Tax Excluded",
        min_display_digits="Product Price",
        compute="_compute_price_unit_discounted_taxexc",
    )
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
    price_unit_discounted_taxinc = fields.Float(
        string="Unit Price Discounted Tax Included",
        min_display_digits="Product Price",
        compute="_compute_price_unit_discounted_taxinc",
    )
    # Transfer block
    qty_transferred_method = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("analytic", "Analytic From Expenses"),
            ("stock_move", "Stock Moves"),
        ],
        string="Received Qty Method",
        compute="_compute_qty_transferred_method",
        store=True,
        precompute=True,
        help="According to product configuration, the received quantity can be automatically computed by mechanism:\n"
        "  - Manual: the quantity is set manually on the line\n"
        "  - Stock Moves: the quantity comes from confirmed pickings\n",
    )
    qty_transferred = fields.Float(
        string="Received Qty",
        digits="Product Unit",
        compute="_compute_qty_transferred",
        store=True,
        readonly=False,
        copy=False,
    )
    qty_to_transfer = fields.Float(
        digits="Product Unit",
        copy=False,
    )
    # Same than `qty_transferred` but non-stored and depending of the context.
    qty_transferred_at_date = fields.Float(
        string="Received",
        digits="Product Unit",
        compute="_compute_qty_transferred_at_date",
    )

    # Invoice block
    invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_move_line_purchase_order_line_rel",
        column1="order_line_id",
        column2="move_line_id",
        string="Invoice Lines",
        copy=False,
    )
    qty_invoiced = fields.Float(
        string="Invoiced Quantity",
        digits="Product Unit",
        compute="_compute_invoice_amounts",
        store=True,
    )
    qty_to_invoice = fields.Float(
        string="Quantity To Invoice",
        digits="Product Unit",
        compute="_compute_invoice_amounts",
        store=True,
    )
    # Same than `qty_to_invoice` but non-stored and depending of the context.
    qty_invoiced_at_date = fields.Float(
        string="Billed",
        digits="Product Unit",
        compute="_compute_qty_invoiced_at_date",
    )
    amount_taxexc_invoiced = fields.Monetary(
        string="Untaxed Invoiced Amount",
        compute="_compute_invoice_amounts",
        store=True,
    )
    amount_taxinc_invoiced = fields.Monetary(
        string="Invoiced Amount",
        compute="_compute_invoice_amounts",
        store=True,
    )
    amount_taxexc_to_invoice = fields.Monetary(
        string="Untaxed Amount To Invoice",
        compute="_compute_invoice_amounts",
        store=True,
    )
    amount_taxinc_to_invoice = fields.Monetary(
        string="Un-invoiced Balance",
        compute="_compute_invoice_amounts",
        store=True,
    )
    amount_to_invoice_at_date = fields.Float(
        string="Amount",
        compute="_compute_amount_to_invoice_at_date",
    )
    invoice_state = fields.Selection(
        selection=const.INVOICE_STATE,
        string="Invoice Status",
        default="no",
        compute="_compute_invoice_state",
        store=True,
    )

    # ------------------------------------------------------------
    # CONSTRAINT METHODS
    # ------------------------------------------------------------

    _accountable_required_fields = models.Constraint(
        """CHECK(
            display_type IS NOT NULL
            OR is_downpayment
            OR (
                product_id IS NOT NULL
                AND product_uom_id IS NOT NULL
            )
        )""",
        "Missing required fields on accountable purchase order line.",
    )
    _non_accountable_null_fields = models.Constraint(
        """CHECK(
            display_type IS NULL
            OR (
                product_id IS NULL
                AND (price_unit IS NULL OR price_unit = 0)
                AND product_uom_id IS NULL
                AND (product_qty IS NULL OR product_qty = 0)
                AND (product_uom_qty IS NULL OR product_uom_qty = 0)
            )
        )""",
        "Forbidden values on non-accountable purchase order line",
    )

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("display_type") or self.default_get(["display_type"]).get(
                "display_type",
            ):
                vals.update(
                    product_id=False,
                    price_unit=False,
                    product_qty=False,
                    product_uom_qty=False,
                    product_uom_id=False,
                    date_planned=False,
                )

        lines = super().create(vals_list)

        # Hook for lines created in purchase state (handles messaging, pickings, etc.)
        lines.filtered(
            lambda l: l.order_id.state == "done",
        )._hook_on_created_confirmed_lines()

        return lines

    def write(self, vals):
        self._validate_write_vals(vals)

        # Collect lines with product_qty changes before write
        if "product_qty" in vals:
            precision = self.env["decimal.precision"].precision_get("Product Unit")
            lines_with_qty_change = defaultdict(list)
            for line in self:
                if (
                    line.order_id.state == "done"
                    and float_compare(
                        line.product_qty,
                        vals["product_qty"],
                        precision_digits=precision,
                    )
                    != 0
                ):
                    lines_with_qty_change[line.order_id].append(
                        {
                            "line": line,
                            "old_qty": line.product_qty,
                            "new_qty": vals["product_qty"],
                        },
                    )

        # Collect lines with qty_transferred changes before write
        if "qty_transferred" in vals:
            lines_with_transferred_change = defaultdict(list)
            for line in self:
                if (
                    not self.env.context.get("accrual_entry_date")
                    and vals["qty_transferred"] != line.qty_transferred
                    and line.order_id.state == "done"
                ):
                    lines_with_transferred_change[line.order_id].append(
                        {
                            "line": line,
                            "old_qty": line.qty_transferred,
                            "new_qty": vals["qty_transferred"],
                        },
                    )

        result = super().write(vals)

        # Post batched messages for product_qty changes
        if "product_qty" in vals:
            for order, changes in lines_with_qty_change.items():
                self._post_batched_quantity_changes(order, changes, "product_qty")

        # Post batched messages for qty_transferred changes
        if "qty_transferred" in vals:
            for order, changes in lines_with_transferred_change.items():
                self._post_batched_quantity_changes(order, changes, "qty_transferred")

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        """Prevent deletion of confirmed order lines that have been invoiced or received.

        Validates that order lines can be deleted based on:
        - Order state (cannot delete from confirmed orders)
        - Invoice status (cannot delete invoiced lines)
        - Display type (sections/notes can always be deleted)
        """
        lines_to_block = self._check_line_unlink()
        if lines_to_block:
            # Get dynamic state description for better error messages
            state_description = dict(
                self._fields["state"]._description_selection(self.env),
            )
            # Use the state of the first blocked line for the error message
            state_label = state_description[lines_to_block[0].state]
            raise UserError(
                _(
                    "Cannot delete a purchase order line which is in state '%s'.\n"
                    "Once a purchase order is confirmed, you can't remove lines that have been "
                    "invoiced or received (we need to track if something gets invoiced or received).\n"
                    "Set the quantity to 0 instead.",
                    state_label,
                ),
            )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    def _compute_parent_id(self):
        purchase_order_lines = set(self)
        for order, lines in self.grouped("order_id").items():
            if not order:
                lines.parent_id = False
                continue
            last_section = False
            last_sub = False
            for line in order.line_ids.sorted("sequence"):
                if line.display_type == "line_section":
                    last_section = line
                    if line in purchase_order_lines:
                        line.parent_id = False
                    last_sub = False
                elif line.display_type == "line_subsection":
                    if line in purchase_order_lines:
                        line.parent_id = last_section
                    last_sub = line
                elif line in purchase_order_lines:
                    line.parent_id = last_sub or last_section

    @api.depends("product_id.purchase_line_warn_msg")
    def _compute_purchase_line_warn_msg(self):
        has_warning_group = self.env.user.has_group("purchase.group_warning_purchase")
        for line in self:
            line.purchase_line_warn_msg = (
                line.product_id.purchase_line_warn_msg if has_warning_group else ""
            )

    @api.depends(
        "product_id",
        "product_id.uom_id",
        "product_id.uom_ids",
        "product_id.seller_ids",
        "product_id.seller_ids.product_uom_id",
    )
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = (
                line.product_id.uom_id
                | line.product_id.uom_ids
                | line.product_id.seller_ids.product_uom_id
            )

    @api.depends("is_expense", "product_id")
    def _compute_qty_transferred_method(self):
        for line in self:
            if line.is_expense:
                line.qty_transferred_method = "analytic"
            elif line.product_id and line.product_type == "service":
                line.qty_transferred_method = "manual"
            elif line.product_id and line.product_type == "consu":
                line.qty_transferred_method = "stock_move"
            else:
                line.qty_transferred_method = False

    @api.depends("company_id", "fiscal_position_id", "product_id")
    def _compute_tax_ids(self):
        lines_by_company = defaultdict(lambda: self.env["purchase.order.line"])
        cached_taxes = {}
        for line in self.filtered(lambda l: not l.display_type):
            if not line.product_id:
                line.tax_ids = False
                continue
            lines_by_company[line.company_id] += line

        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = line.product_id.supplier_taxes_id._filter_taxes_by_company(
                    company,
                )
                if not taxes:
                    line.tax_ids = False
                    continue
                fiscal_position = line.order_id.fiscal_position_id
                cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                cache_key += line._get_custom_compute_tax_cache_key()
                if cache_key in cached_taxes:
                    result = cached_taxes[cache_key]
                else:
                    result = fiscal_position.map_tax(taxes)
                    cached_taxes[cache_key] = result
                # If company_id is set, always filter taxes by the company
                line.tax_ids = result

    @api.depends("partner_id", "product_id")
    def _compute_product_uom_id(self):
        """Set product UOM from seller or product default.

        - New lines: Initialize with seller's UOM (if available) or product's default UOM
        - Product/Partner change: Reset to seller's UOM or product's UOM
        - Manual edits: User can override after compute (readonly=False)
        """
        for line in self:
            # Set UOM if:
            # 1. Not set yet (new line)
            # 2. Product changed (different product than origin)
            if not line.product_uom_id or (
                line._origin.product_id and line._origin.product_id != line.product_id
            ):
                # Try to get seller's UoM for this partner using centralized helper
                seller_uom = False
                sellers = line._get_sellers_for_partner()
                if sellers and sellers[0].product_uom_id:
                    seller_uom = sellers[0].product_uom_id
                line.product_uom_id = seller_uom or line.product_id.uom_id

    @api.depends("company_id", "partner_id", "product_id")
    def _compute_analytic_distribution(self):
        for line in self:
            if line.display_type:
                continue
            distribution = line.env[
                "account.analytic.distribution.model"
            ]._get_distribution(
                {
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_categ_id.id,
                    "partner_id": line.partner_id.id,
                    "partner_category_id": line.partner_id.category_id.ids,
                    "company_id": line.company_id.id,
                },
            )
            line.analytic_distribution = distribution or line.analytic_distribution

    @api.depends(
        "partner_id", "date_order", "product_id", "product_id.seller_ids.min_qty"
    )
    def _compute_product_qty(self):
        """Set suggested quantity based on vendor's minimum order quantity.

        - New lines: Initialize with seller's min_qty or 1.0
        - Product/Partner change: Reset to new suggested quantity
        - Manual override: User can change after initial set (readonly=False)
        """
        for line in self:
            # Non-accountable lines (sections, notes) must have NULL for constraint
            if line.display_type or not line.product_id:
                line.product_qty = False
                continue

            product_qty = 1.0
            # Set quantity if not set yet OR product/partner changed
            if (
                not line.product_qty
                or (
                    line._origin.product_id
                    and line._origin.product_id != line.product_id
                )
                or (
                    line._origin.partner_id
                    and line._origin.partner_id != line.partner_id
                )
            ):
                # Get seller's minimum quantity using centralized helper
                date = (
                    line.date_order and line.date_order.date()
                ) or fields.Date.context_today(line)
                sellers = line._get_sellers_for_partner(date=date)
                # Further filter by product variant if specified
                sellers = sellers.filtered(
                    lambda s: not s.product_id or s.product_id == line.product_id
                ).sorted(key=lambda r: r.min_qty)
                if sellers:
                    line.product_qty = sellers[0].min_qty or 1.0
                else:
                    line.product_qty = product_qty

    @api.depends("product_id", "product_id.uom_id", "product_uom_id", "product_qty")
    def _compute_product_uom_qty(self):
        """Convert product_qty to product's base UOM.

        This field represents the quantity in the product's base UOM,
        regardless of the UOM selected on the line (product_uom_id).

        Example: Buying 2 Cases where 1 Case = 12 Units
            - product_qty = 2 (in Cases)
            - product_uom_qty = 24 (in Units - base UOM)
        """
        for line in self:
            # Non-accountable lines (sections, notes) must have NULL for constraint
            if line.display_type:
                line.product_uom_qty = False
                continue
            if line.product_id and line.product_id.uom_id != line.product_uom_id:
                line.product_uom_qty = line.product_uom_id._compute_quantity(
                    line.product_qty,
                    line.product_id.uom_id,
                )
            else:
                line.product_uom_qty = line.product_qty

    @api.depends(
        "partner_id",
        "date_order",
        "product_id",
        "product_id.seller_ids",
        "product_id.seller_ids.partner_id",
        "product_id.seller_ids.company_id",
        "product_id.seller_ids.min_qty",
        "product_id.seller_ids.date_start",
        "product_id.seller_ids.date_end",
        "product_id.seller_ids.product_uom_id",
        "product_uom_id",
        "product_qty",
        "company_id",
    )
    def _compute_selected_seller_id(self):
        """Select the best matching vendor pricelist entry.

        Selection criteria (handled by product._select_seller):
        - Partner matches (or parent partner)
        - Quantity >= min_qty
        - Date within validity period
        - UoM matches (if force_uom)
        - Sequence/priority ordering

        Performance optimization: Groups lines by (product, partner, order, uom)
        to cache seller lookups and avoid redundant _select_seller calls.
        For 200 lines with same product/partner, this reduces calls from 200 to 1.
        """
        # Handle non-accountable lines first
        non_accountable = self.filtered(lambda l: l.display_type or not l.product_id)
        non_accountable.selected_seller_id = False

        accountable_lines = self - non_accountable
        if not accountable_lines:
            return

        # Cache seller lookups by (product, partner, order, uom) to avoid redundant calls
        # We include order_id because date_order affects seller selection
        seller_cache = {}

        for line in accountable_lines:
            # Build cache key from factors that affect seller selection
            # Note: We use exact quantity (not bucketed) to ensure correct seller
            # selection based on min_qty thresholds. The cache still provides
            # benefit when multiple lines have identical quantities.
            qty = abs(line.product_qty) or 1.0

            cache_key = (
                line.product_id.id,
                line.partner_id.id,
                line.order_id.id,  # Includes date_order context
                line.product_uom_id.id,
                qty,  # Use exact quantity to respect min_qty thresholds
            )

            if cache_key not in seller_cache:
                params = line._get_select_sellers_params()
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=qty,
                    date=(line.order_id.date_order and line.order_id.date_order.date())
                    or fields.Date.context_today(line),
                    uom_id=line.product_uom_id,
                    params=params,
                )
                seller_cache[cache_key] = seller or False

            line.selected_seller_id = seller_cache[cache_key]

    @api.depends("partner_id", "product_id", "selected_seller_id")
    def _compute_name(self):
        """Compute product description from product/seller context.

        Sets the line description using the product name in the partner's language,
        with seller-specific context when available.
        """
        for line in self:
            if not line.product_id:
                continue
            line._set_product_description()

    @api.depends(
        "selected_seller_id",
        "selected_seller_id.price",
        "selected_seller_id.discount",
        "selected_seller_id.currency_id",
        "selected_seller_id.product_uom_id",
        "product_id.standard_price",
        "product_id.supplier_taxes_id",
        "product_id.cost_currency_id",
        "product_uom_id",
        "company_id",
        "currency_id",
        "date_order",
        "tax_ids",
    )
    def _compute_price_and_discount(self):
        """Compute price and discount from selected seller or product cost.

        Combined compute for atomic updates - price and discount always come
        from the same source (seller or product cost).

        Manual override detection via price_unit_auto:
        - price_unit == price_unit_auto → system-set, safe to update
        - price_unit != price_unit_auto → user override, preserve
        """
        for line in self:
            if line.display_type:
                line.price_unit = line.discount = line.price_unit_auto = False
                continue
            if not line.product_id:
                continue

            # Always compute what the auto price/discount would be
            if line.selected_seller_id:
                auto_price = line._get_price_from_seller()
                auto_discount = line.selected_seller_id.discount or 0.0
            else:
                auto_price = line._get_price_from_product_cost()
                auto_discount = 0.0

            # Capture old shadow BEFORE updating (for manual override detection)
            old_shadow = line.price_unit_auto

            # Always update shadow to current computed value
            line.price_unit_auto = auto_price

            # Only update price_unit/discount if not manually overridden
            if line._should_update_price(auto_price, old_shadow):
                line.price_unit = auto_price
                line.discount = auto_discount

    @api.depends("date_order", "selected_seller_id", "selected_seller_id.delay")
    def _compute_date_planned(self):
        """Compute expected delivery date from order date and seller lead time.

        The date is calculated as: order_date + seller_delay (in days).
        If no seller is selected, only the order date is used.

        Uses date_is_manual flag to preserve user-set values. When date_is_manual
        is False, the date is automatically updated when seller or order date changes.
        """
        # Skip non-accountable lines
        accountable_lines = self.filtered(lambda l: not l.display_type and l.product_id)
        if not accountable_lines:
            return

        for line in accountable_lines:
            new_date = line._get_date_planned(line.selected_seller_id)

            # Not set yet - use the computed date
            if not line.date_planned:
                line.date_planned = new_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                continue

            # Already equals the new computed date - nothing to do
            if line.date_planned.date() == new_date.date():
                continue

            # Product changed from origin - always update (reset manual flag too)
            if line._origin.product_id and line._origin.product_id != line.product_id:
                line.date_planned = new_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                line.date_is_manual = False
                continue

            # Respect manual override flag
            if line.date_is_manual:
                continue

            # For backward compatibility: check if current date matches any seller's date
            # This handles existing records that don't have date_is_manual set
            if not line._origin.date_is_manual:
                valid_dates = line._get_seller_valid_dates()
                if line.date_planned.date() in valid_dates:
                    # Current date matches a known seller default - update it
                    line.date_planned = new_date.strftime(
                        DEFAULT_SERVER_DATETIME_FORMAT
                    )

    @api.depends("product_id.uom_id", "product_uom_id", "price_unit")
    def _compute_price_unit_product_uom(self):
        for line in self:
            line.price_unit_product_uom = (
                not line.display_type
                and line.product_uom_id._compute_price(
                    line.price_unit,
                    line.product_id.uom_id,
                )
            )

    @api.depends("price_unit", "discount")
    def _compute_price_unit_discounted_taxexc(self):
        for line in self:
            if line.display_type:
                line.price_unit_discounted_taxexc = False
                continue
            line.price_unit_discounted_taxexc = line.price_unit * (
                1 - (line.discount or 0.0) / 100.0
            )

    @api.depends("product_qty", "price_unit", "discount", "tax_ids")
    def _compute_amounts(self):
        AccountTax = self.env["account.tax"]
        for line in self:
            if line.display_type:
                line.price_subtotal = False
                line.price_total = False
                line.price_tax = False
                continue
            company = line.company_id or self.env.company
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            line.price_subtotal = base_line["tax_details"]["total_excluded_currency"]
            line.price_total = base_line["tax_details"]["total_included_currency"]
            line.price_tax = line.price_total - line.price_subtotal

    @api.depends("product_qty", "price_total")
    def _compute_price_unit_discounted_taxinc(self):
        for line in self:
            line.price_unit_discounted_taxinc = (
                line.price_total / line.product_qty if line.product_qty else 0.0
            )

    @api.depends("qty_transferred_method")
    def _compute_qty_transferred(self):
        lines_manual = self.filtered(
            lambda line: line.qty_transferred_method == "manual",
        )
        lines_manual.qty_transferred = 0.0

    @api.depends_context("accrual_entry_date")
    @api.depends("qty_transferred")
    def _compute_qty_transferred_at_date(self):
        if not self._date_in_the_past():
            for line in self:
                line.qty_transferred_at_date = line.qty_transferred
            return
        received_quantities = self._prepare_qty_transferred()
        for line in self:
            line.qty_transferred_at_date = received_quantities[line]

    @api.depends(
        "state",
        "product_id.bill_policy",
        "product_qty",
        "price_unit_discounted_taxexc",
        "tax_ids",
        "price_total",
        "qty_transferred",
        "invoice_line_ids",
        "invoice_line_ids.parent_state",
        "invoice_line_ids.quantity",
        "invoice_line_ids.discount",
        "invoice_line_ids.price_subtotal",
        "invoice_line_ids.price_total",
    )
    def _compute_invoice_amounts(self):
        """Unified computation of all invoice-related quantities and amounts.

        Computes in single pass over invoice lines (for performance):
        - qty_invoiced, qty_to_invoice
        - amount_taxexc_invoiced, amount_taxexc_to_invoice
        - amount_taxinc_invoiced, amount_taxinc_to_invoice
        """
        for line in self:
            line._compute_invoice_amounts_single()

    def _compute_invoice_amounts_single(self):
        """Compute invoice amounts for a single purchase order line."""
        if self.display_type:
            self._reset_invoice_amounts()
            return

        invoice_lines = self._get_posted_invoice_lines()
        invoiced = self._sum_invoiced_amounts(invoice_lines)

        self.qty_invoiced = invoiced["qty"]
        self.amount_taxexc_invoiced = invoiced["amount_taxexc"]
        self.amount_taxinc_invoiced = invoiced["amount_taxinc"]

        if self.state in ("draft", "cancel"):
            self._reset_to_invoice_amounts()
            return

        self._compute_to_invoice_amounts(invoice_lines, invoiced)

    def _compute_to_invoice_amounts(self, invoice_lines, invoiced):
        """Compute the 'to invoice' quantities and amounts.

        Args:
            invoice_lines: recordset of posted invoice lines
            invoiced: dict with {qty, amount_taxexc, amount_taxinc} already invoiced
        """
        qty_to_consider = self._get_qty_to_consider_for_billing()
        price_subtotal = self._get_billable_subtotal(qty_to_consider)

        # Handle discount differences between PO line and invoice lines
        if self._has_discount_differences(invoice_lines):
            amount_invoiced = self._sum_invoiced_with_discount_adjustment(invoice_lines)
            self.amount_taxexc_to_invoice = max(price_subtotal - amount_invoiced, 0.0)
        else:
            self.amount_taxexc_to_invoice = max(
                price_subtotal - invoiced["amount_taxexc"],
                0.0,
            )

        # Tax-included: use unit price from price_total to avoid recalculation
        unit_price_total = (
            self.price_total / self.product_qty if self.product_qty else 0.0
        )
        self.amount_taxinc_to_invoice = unit_price_total * (
            qty_to_consider - invoiced["qty"]
        )
        self.qty_to_invoice = qty_to_consider - invoiced["qty"]

    @api.depends_context("accrual_entry_date")
    @api.depends("qty_invoiced")
    def _compute_qty_invoiced_at_date(self):
        if not self._date_in_the_past():
            for line in self:
                line.qty_invoiced_at_date = line.qty_invoiced
            return
        invoiced_quantities = self._prepare_qty_invoiced()
        for line in self:
            line.qty_invoiced_at_date = invoiced_quantities[line]

    @api.depends_context("accrual_entry_date")
    @api.depends("price_unit", "qty_invoiced_at_date", "qty_transferred_at_date")
    def _compute_amount_to_invoice_at_date(self):
        for line in self:
            line.amount_to_invoice_at_date = (
                line.qty_transferred_at_date - line.qty_invoiced_at_date
            ) * line.price_unit

    @api.depends(
        "qty_to_invoice",
        "qty_invoiced",
        "product_qty",
        "qty_transferred",
        "product_id.bill_policy",
        "amount_taxexc_to_invoice",
    )
    def _compute_invoice_state(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_compute_qty_to_invoice()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs only in state 'done', the upselling opportunity is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        """
        precision = self.env["decimal.precision"].precision_get("Product Unit")
        for line in self.filtered(lambda l: not l.display_type):
            if line.is_downpayment and line.amount_taxexc_to_invoice == 0:
                line.invoice_state = "done"

            elif float_is_zero(line.product_qty, precision_digits=precision):
                line.invoice_state = "no"

            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                if line.qty_to_invoice < 0:
                    # Negative qty_to_invoice means credit note is needed
                    line.invoice_state = "to do"
                elif float_is_zero(line.qty_invoiced, precision_digits=precision):
                    # Nothing invoiced yet
                    line.invoice_state = "to do"
                elif not float_is_zero(line.qty_invoiced, precision_digits=precision):
                    # Some quantity already invoiced
                    line.invoice_state = "partial"

            elif float_is_zero(line.qty_to_invoice, precision_digits=precision):
                # Compare against qty_to_consider based on bill_policy
                qty_to_consider = (
                    line.qty_transferred
                    if line.product_id.bill_policy == "transferred"
                    else line.product_qty
                )
                # If nothing to consider (e.g., nothing received yet for 'transferred' policy),
                # there's nothing to invoice
                if float_is_zero(qty_to_consider, precision_digits=precision):
                    line.invoice_state = "no"
                    continue
                compare = float_compare(
                    line.qty_invoiced,
                    qty_to_consider,
                    precision_digits=precision,
                )
                if compare == 0:
                    line.invoice_state = "done"
                elif compare > 0:
                    line.invoice_state = "over done"
                else:
                    # qty_invoiced < qty_to_consider
                    line.invoice_state = "partial"

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange("date_planned")
    def _onchange_date_planned(self):
        """Mark date as manually set when user changes it in the UI.

        This flag prevents automatic date updates when seller or order date
        changes, preserving the user's explicit choice.
        """
        if self._origin.date_planned and self.date_planned != self._origin.date_planned:
            self.date_is_manual = True

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------

    @api.readonly
    def action_add_from_catalog(self):
        order = self.env["purchase.order"].browse(self.env.context.get("order_id"))
        return order.with_context(child_field="line_ids").action_add_from_catalog()

    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "res_id": self.order_id.id,
            "view_mode": "form",
        }

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _convert_to_middle_of_day(self, date):
        """Return a datetime which is the noon of the input date(time) according
        to order user's time zone, convert to UTC time.
        """
        return (
            self.order_id.get_timezone()
            .localize(datetime.combine(date, time(12)))
            .astimezone(UTC)
            .replace(tzinfo=None)
        )

    def _domain_product_id(self):
        return [("purchase_ok", "=", True)]

    def _get_billable_subtotal(self, qty):
        """Calculate the billable subtotal for a given quantity.

        Handles price-included taxes by using compute_all() to extract
        the tax-excluded amount.

        Note: Cannot use price_subtotal field directly because it returns zero
        when product_qty is zero, which breaks expense lines.

        Args:
            qty: Quantity to calculate subtotal for

        Returns:
            float: Tax-excluded subtotal amount
        """
        subtotal = self.price_unit_discounted_taxexc * qty

        if self.tax_ids.filtered(lambda t: t.price_include):
            subtotal = self.tax_ids.compute_all(
                self.price_unit_discounted_taxexc,
                currency=self.currency_id,
                quantity=qty,
                product=self.product_id,
                partner=self.order_id.partner_id,
            )["total_excluded"]

        return subtotal

    def _get_custom_compute_tax_cache_key(self):
        """Hook method to be able to set/get cached taxes while computing them"""
        return tuple()

    @api.model
    def _get_date_planned(self, seller, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
        PO Lines that correspond to the given product.seller_ids,
        when ordered at `date_order_str`.

        :param Model seller: used to fetch the delivery delay (if no seller
                             is provided, the delay is 0)
        :param Model po: purchase.order, necessary only if the PO line is
                         not yet attached to a PO.
        :rtype: datetime
        :return: desired Schedule Date for the PO line
        """
        date_order = po.date_order if po else self.order_id.date_order
        if date_order:
            return date_order + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)

    def _get_invoice_lines(self):
        self.ensure_one()
        if self.env.context.get("accrual_entry_date"):
            accrual_date = fields.Date.from_string(
                self.env.context["accrual_entry_date"],
            )
            return self.invoice_line_ids.filtered(
                lambda l: l.move_id.invoice_date
                and l.move_id.invoice_date <= accrual_date,
            )
        return self.invoice_line_ids

    def _get_line_description(self, product_lang):
        """Compute a default description for this purchase order line.

        :param product_lang: product record with proper language context
        :return: the description for the purchase order line
        :rtype: string
        """
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += "\n" + product_lang.description_purchase
        return name

    def _get_line_identifier(self, line):
        """Get a human-readable identifier for a purchase order line.

        Returns product name if available, otherwise description or line sequence.
        """
        if line.product_id:
            return line.product_id.display_name
        elif line.name:
            # Truncate long descriptions
            name = line.name.split("\n")[0]  # Take first line only
            return name[:50] + "..." if len(name) > 50 else name
        else:
            return _("Line #%s", line.sequence or line.id)

    def _get_protected_fields(self):
        """Give the fields that should not be modified on a locked PO.

        :returns: list of field names
        :rtype: list
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

    def get_line_parent_section(self):
        if not self.display_type and self.parent_id.display_type == "line_subsection":
            return self.parent_id.parent_id

        return self.parent_id

    def _get_posted_invoice_lines(self):
        """Get invoice lines that should be considered for invoiced amounts.

        Returns:
            recordset: Invoice lines that are posted or in legacy invoicing state.
        """
        return self._get_invoice_lines().filtered(
            lambda l: l.parent_state == "posted"
            or l.move_id.payment_state == "invoicing_legacy"
        )

    def _get_price_precision(self):
        """Get precision for price rounding.

        Returns the maximum between currency decimal places and
        the system's Product Price decimal precision.
        """
        self.ensure_one()
        return max(
            self.currency_id.decimal_places,
            self.env["decimal.precision"].precision_get("Product Price"),
        )

    def _get_price_unit_gross(self):
        self.ensure_one()
        price_unit = self.price_unit
        if self.discount:
            price_unit = price_unit * (1 - self.discount / 100)
        if self.tax_ids:
            qty = self.product_qty or 1
            price_unit = self.tax_ids.compute_all(
                price_unit,
                currency=self.order_id.currency_id,
                quantity=qty,
                rounding_method="round_globally",
            )["total_void"]
            price_unit = price_unit / qty
        if self.product_uom_id.id != self.product_id.uom_id.id:
            price_unit *= self.product_id.uom_id.factor / self.product_uom_id.factor
        return price_unit

    def _get_product_catalog_lines_data(self, **kwargs):
        """Return information about purchase order lines in `self`.

        If `self` is empty, this method returns only the default value(s) needed for the product
        catalog. In this case, the quantity that equals 0.

        Otherwise, it returns a quantity and a price based on the product of the POL(s) and whether
        the product is read-only or not.

        A product is considered read-only if the order is considered read-only (see
        ``PurchaseOrder._is_readonly`` for more details) or if `self` contains multiple records.

        Note: This method cannot be called with multiple records that have different products linked.

        :raise odoo.exceptions.ValueError: ``len(self.product_id) != 1``
        :rtype: dict
        :return: A dict with the following structure:
            {
                'quantity': float,
                'price': float,
                'readOnly': bool,
                'uomDisplayName': String,
                'packaging': dict,
                'warning': String,
            }
        """
        if len(self) == 1:
            catalog_info = self.order_id._get_product_price_and_data(self.product_id)
            catalog_info.update(
                quantity=self.product_qty,
                price=self.price_unit * (1 - self.discount / 100),
                readOnly=self.order_id._is_readonly(),
            )
            if self.product_id.uom_id != self.product_uom_id:
                catalog_info["uomDisplayName"] = self.product_uom_id.display_name
            return catalog_info
        elif self:
            self.product_id.ensure_one()
            order_line = self[0]
            catalog_info = order_line.order_id._get_product_price_and_data(
                order_line.product_id,
            )
            catalog_info["quantity"] = sum(
                self.mapped(
                    lambda line: line.product_uom_id._compute_quantity(
                        qty=line.product_qty,
                        to_unit=line.product_id.uom_id,
                    ),
                ),
            )
            catalog_info["readOnly"] = True
            return catalog_info
        return {"quantity": 0}

    def _get_price_from_seller(self):
        """Get price from selected seller's pricelist.

        Includes:
        - Tax adjustments
        - Currency conversion
        - UoM conversion

        Returns:
            float: The computed price unit
        """
        self.ensure_one()
        seller = self.selected_seller_id

        # Get seller's base price, adjust for tax inclusion
        price_unit = self.env["account.tax"]._fix_tax_included_price_company(
            seller.price,
            self.product_id.supplier_taxes_id,
            self.tax_ids,
            self.company_id,
        )

        # Convert currency
        price_unit = seller.currency_id._convert(
            price_unit,
            self.currency_id,
            self.company_id,
            self.date_order or fields.Date.context_today(self),
            False,
        )

        # Convert UoM
        price_unit = seller.product_uom_id._compute_price(
            price_unit, self.product_uom_id
        )

        # Round to precision
        return float_round(price_unit, precision_digits=self._get_price_precision())

    def _get_price_from_product_cost(self):
        """Get price from product standard cost (fallback when no seller).

        Includes:
        - UoM conversion to line UoM
        - Tax adjustments
        - Currency conversion

        Returns:
            float: The computed price unit
        """
        self.ensure_one()

        # Determine UoM for pricing
        po_line_uom = self.product_uom_id or self.product_id.uom_id

        # Convert product cost to line UoM and adjust for taxes
        price_unit = self.env["account.tax"]._fix_tax_included_price_company(
            self.product_id.uom_id._compute_price(
                self.product_id.standard_price,
                po_line_uom,
            ),
            self.product_id.supplier_taxes_id,
            self.tax_ids,
            self.company_id,
        )

        # Convert from product cost currency to line currency
        price_unit = self.product_id.cost_currency_id._convert(
            price_unit,
            self.currency_id,
            self.company_id,
            self.date_order or fields.Date.context_today(self),
            False,
        )

        # Round and return
        return float_round(price_unit, precision_digits=self._get_price_precision())

    def _get_qty_to_consider_for_billing(self):
        """Get quantity to consider based on product's billing policy.

        Returns:
            float: qty_transferred if bill_policy is 'transferred', else product_qty
        """
        if self.product_id.bill_policy == "transferred":
            return self.qty_transferred
        return self.product_qty

    def _get_select_sellers_params(self):
        self.ensure_one()
        return {
            "order_id": self.order_id,
            "force_uom": True,
        }

    def _get_sellers_for_partner(self, date=None):
        """Get filtered sellers matching this line's partner and optional date.

        Centralizes the seller filtering logic used across multiple compute methods.
        Filters sellers by:
        - Partner matches (direct or parent company)
        - Date within validity period (if date provided)

        :param date: Optional date for validity check (date object or None)
        :return: Filtered recordset of product.supplierinfo
        :rtype: recordset
        """
        self.ensure_one()
        if not self.product_id or not self.partner_id:
            return self.env["product.supplierinfo"]

        sellers = self.product_id.seller_ids

        # Filter by partner (direct or parent company)
        partner = self.partner_id
        parent = self.partner_id.parent_id
        sellers = sellers.filtered(
            lambda s: s.partner_id == partner or s.partner_id == parent
        )

        # Filter by date validity if provided
        if date:
            sellers = sellers.filtered(
                lambda s: (not s.date_start or s.date_start <= date)
                and (not s.date_end or s.date_end >= date)
            )

        return sellers

    def _get_seller_valid_dates(self):
        """Get set of all valid planned dates from product's sellers.

        Computes the expected delivery date for each seller on this product,
        plus the no-seller default (order date only). Returns as a set for
        O(1) membership testing.

        :return: Set of date objects representing valid auto-computed dates
        :rtype: set
        """
        self.ensure_one()
        valid_dates = set()

        # Add date from each seller's delay
        for seller in self.product_id.seller_ids:
            seller_date = self._get_date_planned(seller)
            valid_dates.add(seller_date.date())

        # Add the no-seller default (order date with 0 delay)
        no_seller_date = self._get_date_planned(False)
        valid_dates.add(no_seller_date.date())

        return valid_dates

    def _hook_on_created_confirmed_lines(self):
        """Hook method called after lines are created in purchase state.

        Base implementation posts batched chatter messages to orders.
        Child modules should call super() then add their own side-effects.

        Override pattern:
            def _hook_on_created_confirmed_lines(self):
                super()._hook_on_created_confirmed_lines()  # Post messages
                # ... add your custom logic here
        """
        # Skip if context flag is set to prevent logging
        if self.env.context.get("sale_no_log_for_new_lines"):
            return

        # Group lines by order that need messages (only lines with products)
        lines_by_order = defaultdict(lambda: self.env["purchase.order.line"])
        for line in self:
            if line.product_id:  # Only post messages for product lines
                lines_by_order[line.order_id] += line

        # Post one batched message per order
        for order, order_lines in lines_by_order.items():
            count = len(order_lines)
            if count == 1:
                msg = _("Extra line with %s", order_lines.product_id.display_name)
            elif count <= const.MAX_PRODUCTS_IN_MESSAGE:
                # Show all products for small batches
                product_list = (
                    "<ul>"
                    + "".join(
                        f"<li>{p}</li>"
                        for p in order_lines.mapped("product_id.display_name")
                    )
                    + "</ul>"
                )
                msg = _(
                    "Added %(count)s extra lines: %(products)s",
                    count=count,
                    products=product_list,
                )
            else:
                # Summarize for large batches
                msg = _("Added %s extra lines to this purchase order", count)
            order.message_post(body=msg)

    def _merge_po_line(self, rfq_line):
        self.product_qty += rfq_line.product_qty
        self.price_unit = min(self.price_unit, rfq_line.price_unit)

    def _prepare_aml_vals(self, **optional_values):
        """Prepare the values to create the new invoice line for a purchase order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()
        # Pop 'move' as it's only used for context (currency, date), not as a field
        move = optional_values.pop("move", None)
        aml_currency = (move and move.currency_id) or self.currency_id
        date = (move and move.date) or fields.Date.today()
        res = {
            "display_type": self.display_type or "product",
            "name": self.env["account.move.line"]._get_journal_items_full_name(
                self.name,
                self.product_id.display_name,
            ),
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "quantity": (
                -self.qty_to_invoice
                if move and move.move_type == "in_refund"
                else self.qty_to_invoice
            ),
            "discount": self.discount,
            "price_unit": self.currency_id._convert(
                self.price_unit,
                aml_currency,
                self.company_id,
                date,
                round=False,
            ),
            "tax_ids": [Command.set(self.tax_ids.ids)],
            "purchase_line_ids": [Command.link(self.id)],
            "is_downpayment": self.is_downpayment,
        }
        res.update(optional_values)
        return res

    def _prepare_aml_vals_list(self, **optional_values):
        """Prepare the list of values to create invoice lines for purchase order lines.

        :param optional_values: any parameter that should be added to the returned invoice lines
        :rtype: list of dict
        """
        return [self._prepare_aml_vals(**optional_values)]

    def _post_batched_quantity_changes(self, order, changes, change_type):
        """Post a single batched message for quantity changes.

        :param order: purchase.order record
        :param changes: list of dicts with 'line', 'old_qty', 'new_qty' keys
        :param change_type: 'product_qty' or 'qty_transferred'
        """
        if not changes:
            return

        if len(changes) == 1:
            # Single line change - use original template for compatibility
            change = changes[0]
            if change_type == "product_qty":
                order.message_post_with_source(
                    "purchase.track_po_line_template",
                    render_values={
                        "line": change["line"],
                        "product_qty": change["new_qty"],
                    },
                    subtype_xmlid="mail.mt_note",
                )
            elif change_type == "qty_transferred":
                order.message_post_with_source(
                    "purchase.track_po_line_qty_transferred_template",
                    render_values={
                        "line": change["line"],
                        "qty_transferred": change["new_qty"],
                    },
                    subtype_xmlid="mail.mt_note",
                )
        else:
            # Multiple lines - use consolidated order-level template
            order.message_post_with_source(
                "purchase.track_po_qty_update_template",
                render_values={
                    "changes": changes,
                    "change_type": change_type,
                    "count": len(changes),
                },
                subtype_xmlid="mail.mt_note",
            )

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
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

    @api.model
    def _prepare_purchase_order_line(
        self,
        product_id,
        product_qty,
        product_uom,
        company_id,
        partner_id,
        po,
    ):
        values = self.env.context.get("procurement_values", {})
        uom_po_qty = product_uom._compute_quantity(
            product_qty,
            product_id.uom_id,
            rounding_method="HALF-UP",
        )
        # _select_seller is used if the supplier have different price depending
        # the quantities ordered.
        today = fields.Date.today()
        seller = product_id.with_company(company_id)._select_seller(
            partner_id=partner_id,
            quantity=product_qty if values.get("force_uom") else uom_po_qty,
            date=po.date_order and max(po.date_order.date(), today) or today,
            uom_id=product_uom if values.get("force_uom") else product_id.uom_id,
            params={"force_uom": values.get("force_uom")},
        )
        if (
            seller
            and (seller.product_uom_id or seller.product_tmpl_id.uom_id) != product_uom
        ):
            uom_po_qty = product_id.uom_id._compute_quantity(
                uom_po_qty,
                seller.product_uom_id,
                rounding_method="HALF-UP",
            )

        tax_domain = self.env["account.tax"]._check_company_domain(company_id)
        product_taxes = product_id.supplier_taxes_id.filtered_domain(tax_domain)
        taxes = po.fiscal_position_id.map_tax(product_taxes)

        if seller:
            price_unit = (
                seller.product_uom_id._compute_price(seller.price, product_uom)
                if product_uom
                else seller.price
            )
            price_unit = self.env["account.tax"]._fix_tax_included_price_company(
                price_unit,
                product_taxes,
                taxes,
                company_id,
            )
        else:
            price_unit = 0
        if (
            price_unit
            and seller
            and po.currency_id
            and seller.currency_id != po.currency_id
        ):
            price_unit = seller.currency_id._convert(
                price_unit,
                po.currency_id,
                po.company_id,
                po.date_order or fields.Date.today(),
            )

        product_lang = product_id.with_prefetch().with_context(
            lang=partner_id.lang,
            partner_id=partner_id.id,
        )
        name = product_lang.with_context(seller_id=seller.id).display_name
        if product_lang.description_purchase:
            name += "\n" + product_lang.description_purchase

        date_planned = self.order_id.date_planned or self._get_date_planned(
            seller,
            po=po,
        )
        discount = seller.discount or 0.0

        return {
            "name": name,
            "product_qty": product_qty if product_uom else uom_po_qty,
            "product_id": product_id.id,
            "product_uom_id": product_uom.id or seller.product_uom_id.id,
            "price_unit": price_unit,
            "date_planned": date_planned,
            "tax_ids": [Command.set(taxes.ids)],
            "order_id": po.id,
            "discount": discount,
        }

    def _prepare_qty_invoiced(self):
        # Compute qty_invoiced
        invoiced_qties = defaultdict(float)
        for line in self:
            for inv_line in line._get_invoice_lines():
                if (
                    inv_line.move_id.state not in ["cancel"]
                    or inv_line.move_id.payment_state == "invoicing_legacy"
                ):
                    if inv_line.move_id.move_type == "in_invoice":
                        invoiced_qties[
                            line
                        ] += inv_line.product_uom_id._compute_quantity(
                            inv_line.quantity,
                            line.product_uom_id,
                        )
                    elif inv_line.move_id.move_type == "in_refund":
                        invoiced_qties[
                            line
                        ] -= inv_line.product_uom_id._compute_quantity(
                            inv_line.quantity,
                            line.product_uom_id,
                        )
        return invoiced_qties

    def _prepare_qty_transferred(self):
        received_qties = defaultdict(float)
        for line in self:
            if line.qty_transferred_method == "manual":
                received_qties[line] = line.qty_transferred or 0.0
            else:
                received_qties[line] = 0.0
        return received_qties

    def _reset_invoice_amounts(self):
        """Reset all invoice-related amounts to zero (for display_type lines)."""
        self.qty_invoiced = False
        self.qty_to_invoice = False
        self.amount_taxexc_invoiced = False
        self.amount_taxexc_to_invoice = False
        self.amount_taxinc_invoiced = False
        self.amount_taxinc_to_invoice = False

    def _reset_to_invoice_amounts(self):
        """Reset 'to invoice' amounts to zero (for draft/cancel states)."""
        self.amount_taxexc_to_invoice = 0.0
        self.amount_taxinc_to_invoice = 0.0
        self.qty_to_invoice = 0.0

    def _set_product_description(self):
        """Set line description from product in partner's language.

        Uses selected seller context for vendor-specific descriptions.
        Updates when:
        - Name is empty
        - Product changed (user selected a different product)
        - Name matches a known default for current product (not manually customized)
        """
        self.ensure_one()

        lang = get_lang(self.env, self.partner_id.lang).code

        # Build product context with current seller
        seller_id = self.selected_seller_id.id if self.selected_seller_id else None
        product_ctx = {"seller_id": seller_id, "lang": lang}
        new_default = self._get_line_description(
            self.product_id.with_context(product_ctx),
        )

        # No name set yet, use the default
        if not self.name:
            self.name = new_default
            return

        # Name already equals new default - nothing to do
        if self.name == new_default:
            return

        # Always update if product changed from origin (different product = new description)
        if self._origin.product_id and self._origin.product_id != self.product_id:
            self.name = new_default
            return

        # Check if current name matches ANY seller's default description for CURRENT product
        # If so, it's not manually customized - update to new seller's description
        for seller in self.product_id.seller_ids:
            seller_ctx = {"seller_id": seller.id, "lang": lang}
            seller_default = self._get_line_description(
                self.product_id.with_context(seller_ctx),
            )
            if self.name == seller_default:
                # Current name is a seller default (not customized) - update it
                self.name = new_default
                return

        # Also check the no-seller default (generic product description)
        no_seller_ctx = {"seller_id": None, "lang": lang}
        generic_default = self._get_line_description(
            self.product_id.with_context(no_seller_ctx),
        )
        if self.name == generic_default:
            self.name = new_default
            return

        # Name differs from all defaults - user customized it, preserve it

    def _sum_invoiced_amounts(self, invoice_lines):
        """Sum quantities and amounts from invoice lines in a single pass.

        Aggregates quantity, tax-excluded amount, and tax-included amount
        from all posted invoice lines, converting to line's UoM and currency.

        Args:
            invoice_lines: recordset of account.move.line

        Returns:
            dict: {qty, amount_taxexc, amount_taxinc}
        """
        qty = 0.0
        amount_taxexc = 0.0
        amount_taxinc = 0.0

        for inv_line in invoice_lines:
            sign = inv_line.move_id.direction_sign
            date = inv_line.invoice_date or fields.Date.today()

            qty += sign * inv_line.product_uom_id._compute_quantity(
                inv_line.quantity,
                self.product_uom_id,
            )
            amount_taxexc += sign * inv_line.currency_id._convert(
                inv_line.price_subtotal,
                self.currency_id,
                self.company_id,
                date,
            )
            amount_taxinc += sign * inv_line.currency_id._convert(
                inv_line.price_total,
                self.currency_id,
                self.company_id,
                date,
            )

        return {
            "qty": qty,
            "amount_taxexc": amount_taxexc,
            "amount_taxinc": amount_taxinc,
        }

    def _sum_invoiced_with_discount_adjustment(self, invoice_lines):
        """Sum invoiced amounts when discounts differ between PO and invoices.

        When re-invoicing with different discounts, calculate based on
        invoice line prices rather than aggregated amounts.

        Args:
            invoice_lines: recordset of account.move.line

        Returns:
            float: Total tax-excluded amount invoiced
        """
        total = 0.0

        for inv_line in invoice_lines:
            converted_price = inv_line.currency_id._convert(
                inv_line.price_unit,
                self.currency_id,
                self.company_id,
                inv_line.date or fields.Date.today(),
                round=False,
            )
            line_amount = converted_price * inv_line.quantity

            if inv_line.tax_ids.filtered(lambda t: t.price_include):
                line_amount = inv_line.tax_ids.compute_all(line_amount)[
                    "total_excluded"
                ]

            total += line_amount

        return total

    def _update_date_planned(self, updated_date):
        self.date_planned = updated_date

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    def _check_line_unlink(self):
        """Check whether given lines can be deleted or not.

        * Lines that have been invoiced cannot be deleted (financial tracking required).
        * Sections, subsections and notes can always be deleted.
        * Confirmed lines without invoices can be deleted.

        :returns: Purchase Order Lines that cannot be deleted
        :rtype: `purchase.order.line` recordset
        """
        return self.filtered(
            lambda line: line.state == "done" and not line.display_type,
        )

    @api.model
    def _date_in_the_past(self):
        if not "accrual_entry_date" in self.env.context:
            return False
        accrual_date = fields.Date.from_string(self.env.context["accrual_entry_date"])
        return accrual_date < fields.Date.today()

    def _has_discount_differences(self, invoice_lines):
        """Check if any invoice line has a different discount than the PO line."""
        return any(inv_line.discount != self.discount for inv_line in invoice_lines)

    def is_manual_price(self):
        """Check if current price is a manual override (not from vendor pricelist).

        Manual price detection is based on comparison: if price_unit differs
        from price_unit_auto, the price is considered manually set.

        :return: True if price differs from automatic vendor/product price
        :rtype: bool
        """
        self.ensure_one()
        if not self.price_unit_auto:
            return False
        precision = self._get_price_precision()
        return (
            float_compare(
                self.price_unit,
                self.price_unit_auto,
                precision_digits=precision,
            )
            != 0
        )

    def _should_update_price(self, new_auto_price, old_auto):
        """Determine if price_unit should be updated.

        Returns True if:
        - New line without baseline (no price_unit_auto)
        - Product changed (always reset for new product)
        - Current price matches auto price (not manually overridden)

        Returns False if:
        - Line is linked to invoice lines (price locked after invoicing)
        - Currency changed on confirmed order (preserve historical amounts)
        - Price differs from auto (manual override, including 0.0 for free products)

        :param new_auto_price: The newly computed automatic price
        :param old_auto: The previous price_unit_auto value (before this compute)
        :return: True if price should be updated, False to preserve manual override

        Performance note: Uses _origin for currency comparison instead of direct SQL,
        eliminating N+1 query pattern when processing multiple lines.
        """
        self.ensure_one()

        # Don't update if line is linked to invoices
        if self.invoice_line_ids:
            return False

        # On confirmed orders, block price updates when only currency changed
        # (prevents recalculation when changing display currency)
        # Use _origin to compare against database state without SQL query
        if self.state == "done" and self._origin.id:
            original_currency = self._origin.currency_id
            if original_currency and original_currency != self.currency_id:
                # Currency changed - don't update prices
                return False

        # Product changed - always reset to new product's price
        if self._origin.product_id and self._origin.product_id != self.product_id:
            return True

        # Check if current price is manual (differs from auto)
        # IMPORTANT: Check old_auto first because 0.0 is a valid intentional
        # price (e.g., free products). We can't use "not self.price_unit" as it
        # would treat 0.0 as "no price".
        #
        # Logic:
        # - old_auto is non-zero: we have a baseline, use comparison
        #   (allows detecting 0.0 as intentional free product when auto is different)
        # - old_auto is 0.0: this is a new line, always update
        price_precision = self._get_price_precision()
        if old_auto:
            is_manual = (
                float_compare(
                    self.price_unit,
                    old_auto,
                    precision_digits=price_precision,
                )
                != 0
            )
            return not is_manual

        # New line without baseline (initial creation / precompute)
        # Check if current price was explicitly provided in vals
        # During precompute, vals values are loaded into cache before compute runs
        # If price_unit is non-zero and differs from auto, user provided explicit value
        if (
            self.price_unit
            and float_compare(
                self.price_unit, new_auto_price, precision_digits=price_precision
            )
            != 0
        ):
            # Explicit non-zero price during creation, preserve it
            return False

        # Default (0.0) or matching auto price - set to auto
        return True

    def _validate_analytic_distribution(self):
        for line in self:
            if line.display_type:
                continue
            line._validate_distribution(
                product=line.product_id.id,
                business_domain="purchase_order",
                company_id=line.company_id.id,
            )

    def _validate_write_vals(self, write_vals):
        for method_name in self._get_validate_write_vals_methods():
            if hasattr(self, method_name):
                getattr(self, method_name)(write_vals)

    def _get_validate_write_vals_methods(self):
        return [
            "_validate_write_display_type",
            "_validate_write_locked_order",
        ]

    def _validate_write_display_type(self, write_vals):
        """Validate that display_type is not being changed on existing lines."""
        if "display_type" not in write_vals:
            return

        lines = self.filtered(
            lambda l: l.display_type != write_vals.get("display_type"),
        )
        if not lines:
            return

        # Build error message with line identification
        if len(lines) == 1:
            line = lines[0]
            line_id = self._get_line_identifier(line)
            raise UserError(
                _(
                    "You cannot change the type of purchase order line '%s'. "
                    "Instead, delete the current line and create a new line of the proper type.",
                    line_id,
                ),
            )
        else:
            # Multiple lines - show first 5 and count
            line_ids = [self._get_line_identifier(l) for l in lines[:5]]
            error_msg = ", ".join(line_ids)
            if len(lines) > 5:
                error_msg += _(" and %s more", len(lines) - 5)

            raise UserError(
                _(
                    "You cannot change the type of %(count)s purchase order lines (%(lines)s). "
                    "Instead, delete these lines and create new lines of the proper type.",
                    count=len(lines),
                    lines=error_msg,
                ),
            )

    def _validate_write_locked_order(self, write_vals):
        """Validate that protected fields are not being modified on a locked order."""
        locked_lines = self.filtered(lambda l: l.locked)
        if not locked_lines:
            return

        protected_fields = self._get_protected_fields()
        if not any(f in write_vals.keys() for f in protected_fields):
            return

        protected_fields_modified = list(set(protected_fields) & set(write_vals.keys()))

        # Special case: allow changing name for downpayment lines
        if "name" in protected_fields_modified and all(
            locked_lines.mapped("is_downpayment"),
        ):
            protected_fields_modified.remove("name")

        if not protected_fields_modified:
            return

        fields = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [
                    ("name", "in", protected_fields_modified),
                    ("model", "=", self._name),
                ],
            )
        )
        if fields:
            raise UserError(
                _(
                    "It is forbidden to modify the following fields in a locked order:\n%s",
                    "\n".join(fields.mapped("field_description")),
                ),
            )
