from collections import defaultdict
from datetime import timedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.fields import Command, Domain
from odoo.tools import float_compare, float_is_zero, format_date, groupby
from odoo.tools.translate import _

from odoo.addons.sale import const


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["analytic.mixin"]
    _description = "Sales Order Line"
    _check_company_auto = True
    _order = "order_id, sequence, id"
    _rec_names_search = ["name", "order_id.name"]

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    order_id = fields.Many2one(
        comodel_name="sale.order",
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
        string="Customer",
        store=True,
        precompute=True,
        index="btree_not_null",
    )
    user_id = fields.Many2one(
        related="order_id.user_id",
        comodel_name="res.users",
        string="Salesperson",
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
        help="Down payments are made when creating invoices from a sales order."
        " They are not copied when duplicating a sales order.",
    )
    is_expense = fields.Boolean(
        string="Is expense",
        help="Is true if the sales order line comes from an expense or a vendor bills",
    )

    # Section-related fields
    parent_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Parent Section Line",
        compute="_compute_parent_id",
        help="The section or subsection this line belongs to.",
    )
    collapse_prices = fields.Boolean(
        string="Collapse Prices",
        default=False,
        copy=True,
        help="Whether this section's lines' prices will be hidden in reports and in the portal.",
    )
    collapse_composition = fields.Boolean(
        string="Collapse Composition",
        default=False,
        copy=True,
        help="Whether this section's lines will be hidden in reports and in the portal.",
    )
    linked_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Linked Order Line",
        domain="[('order_id', '=', order_id)]",
        ondelete="cascade",
        copy=False,
        index=True,
    )
    linked_line_ids = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="linked_line_id",
        string="Linked Order Lines",
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
    service_tracking = fields.Selection(
        related="product_id.service_tracking",
        depends=["product_id"],
    )
    sale_line_warn_msg = fields.Text(
        compute="_compute_sale_line_warn_msg",
    )
    product_name_translated = fields.Text(
        compute="_compute_product_name_translated",
    )
    product_template_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        compute="_compute_product_template_id",
        readonly=False,
        search="_search_product_template_id",
        # previously related='product_id.product_tmpl_id'
        # not anymore since the field must be considered editable for product configurator logic
        # without modifying the related product_id when updated.
        # magic way to make sure the domain integrates the check_company _domain_product_id logics
        # despite not being a check_company=True field
        domain=lambda self: self._fields["product_id"]._description_domain(self.env),
    )
    is_configurable_product = fields.Boolean(
        related="product_template_id.has_configurable_attributes",
        string="Is the product configurable?",
        depends=["product_template_id"],
    )
    product_template_attribute_value_ids = fields.Many2many(
        related="product_id.product_template_attribute_value_ids",
        depends=["product_id"],
    )
    product_custom_attribute_value_ids = fields.One2many(
        comodel_name="product.attribute.custom.value",
        inverse_name="sale_order_line_id",
        string="Custom Values",
        compute="_compute_custom_attribute_values",
        store=True,
        precompute=True,
        readonly=False,
        copy=True,
    )
    # M2M holding the values of product.attribute with create_variant field set to 'no_variant'
    # It allows keeping track of the extra_price associated to those attribute values and add them to the SO line description
    product_no_variant_attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        string="Extra Values",
        compute="_compute_no_variant_attribute_values",
        store=True,
        precompute=True,
        readonly=False,
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
        domain="[('type_tax_use', '=', 'sale')]",
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
        domain='[("id", "in", allowed_uom_ids)]',
        ondelete="restrict",
    )
    product_qty = fields.Float(
        string="Base Quantity",
        digits="Product Unit",
    )
    product_uom_qty = fields.Float(
        string="Quantity UoM",
        digits="Product Unit",
        default=1.0,
        compute="_compute_product_uom_qty",
        store=True,
        precompute=True,
        readonly=False,
    )
    pricelist_item_id = fields.Many2one(
        comodel_name="product.pricelist.item",
        compute="_compute_pricelist_item_id",
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
        digits="Product Price",
        compute="_compute_price_unit",
        store=True,
        precompute=True,
        readonly=False,
        aggregator="avg",
    )
    price_unit_shadow = fields.Float(
        string="Technical Unit Price",
        digits="Product Price",
        copy=False,
        help="Shadow field tracking current pricelist price. "
        "Automatically recomputed, should not be copied.",
    )
    price_is_manual = fields.Boolean(
        string="Manual Price Override",
        default=False,
        copy=True,
        help="If True, this price was manually set and won't be updated automatically from pricelist. "
        "The price will remain fixed even when product, quantity, or UoM changes.",
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        compute="_compute_discount",
        store=True,
        precompute=True,
        readonly=False,
    )
    customer_lead = fields.Float(
        string="Lead Time",
        compute="_compute_customer_lead",
        store=True,
        precompute=True,
        readonly=False,
        help="Number of days between the order confirmation and the shipping of the products to the customer",
    )
    price_unit_discounted_taxexc = fields.Float(
        string="Unit Price Discounted Tax Excluded",
        digits="Product Price",
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
        digits="Product Price",
        compute="_compute_price_unit_discounted_taxinc",
    )

    virtual_id = fields.Char(
        help="Uniquely identifies this sale order line before "
        "the record is saved in the DB, i.e. before the record has an `id`.",
    )
    linked_virtual_id = fields.Char(
        help="Links this sale order line to another sale order line, via its `virtual_id`",
    )

    selected_combo_items = fields.Char(
        store=False,
        help="Local storage of this sale order line's selected combo items, iff this is a combo product line.",
    )
    combo_item_id = fields.Many2one(
        comodel_name="product.combo.item",
    )

    analytic_line_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="so_line",
        string="Analytic lines",
    )

    # Transfer block
    qty_transferred_method = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("analytic", "Analytic From Expenses"),
            ("stock_move", "Stock Moves"),
        ],
        string="Method to update delivered qty",
        compute="_compute_qty_transferred_method",
        store=True,
        precompute=True,
        help="""According to product configuration, the delivered quantity can
        be automatically computed by mechanism:\n
        -Manual: the quantity is set manually on the line\n
        -Analytic From expenses: the quantity is the quantity sum from posted expenses\n
        -Timesheet: the quantity is the sum of hours recorded on tasks linked to this sale line\n
        -Stock Moves: the quantity comes from confirmed pickings\n""",
    )
    qty_transferred = fields.Float(
        string="Transferred Qty",
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
        string="Delivered",
        digits="Product Unit",
        compute="_compute_qty_transferred_at_date",
    )

    # Invoice block
    invoice_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_move_line_sale_order_line_rel",
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
    qty_invoiced_at_date = fields.Float(
        string="Invoiced",
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

    # Technical field holding custom data for the taxes computation engine.
    extra_tax_data = fields.Json()

    product_is_archived = fields.Boolean(
        compute="_compute_product_is_archived",
    )
    product_readonly = fields.Boolean(
        string="Product is readonly",
        compute="_compute_product_readonly",
        help="Indicates whether the product field should be readonly based on order state, "
        "invoiced/delivered quantities, and locked status. "
        "Used in views for readonly attribute to match product_uom_readonly pattern.",
    )
    product_uom_readonly = fields.Boolean(
        compute="_compute_product_uom_readonly",
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
        "Missing required fields on accountable sale order line.",
    )
    _non_accountable_null_fields = models.Constraint(
        """CHECK(
            display_type IS NULL
            OR (
                product_id IS NULL
                AND price_unit IS NULL
                AND product_uom_id IS NULL
                AND product_uom_qty IS NULL
            )
        )""",
        "Forbidden values on non-accountable sale order line",
    )

    @api.constrains("combo_item_id")
    def _check_combo_item_id(self):
        """`combo_item_id` should never be set manually. This constraint mainly serves to avoid
        programming errors.
        """
        for line in self:
            linked_line = line._get_line_linked()
            allowed_combo_items = (
                linked_line.product_template_id.combo_ids.combo_item_ids
            )
            if line.combo_item_id and line.combo_item_id not in allowed_combo_items:
                raise ValidationError(
                    _(
                        "A sale order line's combo item must be among its linked line's available"
                        " combo items.",
                    ),
                )
            if line.combo_item_id and line.combo_item_id.product_id != line.product_id:
                raise ValidationError(
                    _(
                        "A sale order line's product must match its combo item's product.",
                    ),
                )

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("display_type") or self.default_get(["display_type"]).get(
                "display_type",
            ):
                vals.update(
                    product_id=False,
                    price_unit=False,
                    product_uom_qty=False,
                    product_uom_id=False,
                    date_planned=False,
                )

            if "price_unit_shadow" in vals and "price_unit" not in vals:
                # price_unit field was set as readonly in the view (but price_unit_shadow not)
                # the field is not sent by the client and expected to be recomputed, but isn't
                # because price_unit_shadow is set.
                vals.pop("price_unit_shadow")

        lines = super().create(vals_list)

        for line in lines:
            linked_line = line._get_line_linked()
            if linked_line:
                line.linked_line_id = linked_line

        # Hook for lines created in purchase state (handles messaging, pickings, etc.)
        lines.filtered(
            lambda l: l.order_id.state == "done",
        )._hook_on_created_confirmed_lines()

        return lines

    def write(self, vals):
        self._validate_write_vals(vals)

        if "product_uom_qty" in vals:
            precision = self.env["decimal.precision"].precision_get("Product Unit")
            self.filtered(
                lambda r: r.state == "done"
                and float_compare(
                    r.product_uom_qty,
                    vals["product_uom_qty"],
                    precision_digits=precision,
                )
                != 0,
            )._update_line_quantity(vals)

        # Detect manual price changes (when user edits price_unit directly)
        if (
            "price_unit" in vals
            and "price_is_manual" not in vals
            and not self.env.context.get("sale_write_from_compute")
        ):
            # Process each line individually to correctly detect price changes
            # This prevents incorrectly marking unchanged lines as manual in batch writes
            for line in self:
                # Create a copy of vals for each line to avoid mutations
                line_vals = dict(vals)

                # Apply shadow protection per-line
                if "price_unit_shadow" in line_vals and "price_unit" not in line_vals:
                    line_vals.pop("price_unit_shadow")

                # Only mark as manual if THIS line's price actually changed
                if line.price_unit != vals["price_unit"]:
                    line_vals["price_is_manual"] = True

                # Write to this specific line
                super(SaleOrderLine, line).write(line_vals)

            return True

        if (
            "price_unit_shadow" in vals
            and "price_unit" not in vals
            and not self.env.context.get("sale_write_from_compute")
        ):
            # price_unit field was set as readonly in the view (but price_unit_shadow not)
            # the field is not sent by the client and expected to be recomputed, but isn't
            # because price_unit_shadow is set.
            vals.pop("price_unit_shadow")

        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        """Prevent deletion of confirmed order lines that have been invoiced or delivered.

        Validates that order lines can be deleted based on:
        - Order state (cannot delete from confirmed orders)
        - Invoice status (cannot delete invoiced lines except uninvoiced down payments)
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
                    "Cannot delete a sales order line which is in state '%s'.\n"
                    "Once a sales order is confirmed, you can't remove lines that have been "
                    "invoiced or delivered (we need to track if something gets invoiced or delivered).\n"
                    "Set the quantity to 0 instead.",
                    state_label,
                ),
            )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _add_precomputed_values(self, vals_list):
        """Synchronize price fields during record creation.

        This method ensures price_unit and price_unit_shadow are properly
        synchronized and the manual price flag is set appropriately.

        Scenarios handled:
        1. Both fields explicit -> respect them (allow intentional desync)
        2. Only price_unit explicit -> sync to technical (automatic pricing)
        3. Only technical explicit -> sync to price_unit (rare case)
        4. Neither explicit -> computed by super() (automatic pricing)
        5. price_is_manual explicit -> respect it
        """
        super()._add_precomputed_values(vals_list)

        for vals in vals_list:
            has_price = "price_unit" in vals
            has_technical = "price_unit_shadow" in vals
            has_manual_flag = "price_is_manual" in vals

            # Case 1: Both fields explicitly provided - respect them
            if has_price and has_technical:
                # If they differ but manual flag not set, mark as manual
                if (
                    not has_manual_flag
                    and vals["price_unit"] != vals["price_unit_shadow"]
                ):
                    vals["price_is_manual"] = True
                continue

            # Case 2: Only price_unit provided - sync to technical
            if has_price:
                vals["price_unit_shadow"] = vals["price_unit"]
                # If manual flag not explicitly set, default to False (automatic)
                if not has_manual_flag:
                    vals["price_is_manual"] = False

            # Case 3: Only technical provided - sync to price_unit (rare)
            elif has_technical:
                vals["price_unit"] = vals["price_unit_shadow"]
                if not has_manual_flag:
                    vals["price_is_manual"] = False

            # Case 4: Neither provided - computed by super()
            # Ensure manual flag is False for computed prices
            elif not has_manual_flag:
                vals["price_is_manual"] = False

    # This computed default is necessary to have a clean computation inheritance
    # (cf sale_stock) instead of simply removing the default and specifying
    # the compute attribute & method in sale_stock.
    def _compute_customer_lead(self):
        for line in self.filtered(lambda x: not x.display_type):
            line.customer_lead = 0.0

    def _compute_parent_id(self):
        sale_order_lines = set(self)
        for order, lines in self.grouped("order_id").items():
            if not order:
                lines.parent_id = False
                continue
            last_section = False
            last_sub = False
            for line in order.line_ids.sorted("sequence"):
                if line.display_type == "line_section":
                    last_section = line
                    if line in sale_order_lines:
                        line.parent_id = False
                    last_sub = False
                elif line.display_type == "line_subsection":
                    if line in sale_order_lines:
                        line.parent_id = last_section
                    last_sub = line
                elif line in sale_order_lines:
                    line.parent_id = last_sub or last_section

    @api.depends("order_id", "partner_id", "product_id")
    def _compute_display_name(self):
        name_per_id = self._additional_name_per_id()
        for line in self.sudo():
            if line.partner_id.lang:
                line = line.with_context(lang=line.order_id._get_lang())
            if (product := line.product_id).display_name:
                default_name = line._get_line_multiline_description_sale()
                if line.name == default_name:
                    description = product.display_name
                else:
                    parts = (line.name or "").split("\n", 2)
                    description = (
                        parts[1]
                        if len(parts) > 1 and parts[1]
                        else product.display_name
                    )
            else:
                description = (line.name or "").split("\n", 1)[0]
            name = f"{line.order_id.name} - {description}"
            additional_name = name_per_id.get(line.id)
            if additional_name:
                name = f"{name} {additional_name}"
            line.display_name = name

    @api.depends("product_id.sale_line_warn_msg")
    def _compute_sale_line_warn_msg(self):
        has_warning_group = self.env.user.has_group("sale.group_warning_sale")
        for line in self:
            line.sale_line_warn_msg = (
                line.product_id.sale_line_warn_msg if has_warning_group else ""
            )

    @api.depends("company_id", "product_id")
    def _compute_tax_ids(self):
        lines_by_company = defaultdict(lambda: self.env["sale.order.line"])
        cached_taxes = {}
        for line in self.filtered(lambda l: not l.display_type):
            if not line.product_id or line.product_type == "combo":
                line.tax_ids = False
                continue
            lines_by_company[line.company_id] += line

        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = line.product_id.taxes_id._filter_taxes_by_company(
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
    def _compute_analytic_distribution(self):
        for line in self.filtered(lambda x: not x.display_type):
            distribution = line.env[
                "account.analytic.distribution.model"
            ]._get_distribution(
                {
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_categ_id.id,
                    "partner_id": line.order_id.partner_id.id,
                    "partner_category_id": line.order_id.partner_id.category_id.ids,
                    "company_id": line.company_id.id,
                },
            )
            line.analytic_distribution = distribution or line.analytic_distribution

    @api.depends("is_expense", "product_id")
    def _compute_qty_transferred_method(self):
        """Compute delivered quantities for products based on type and configuration.

        Computation Methods:
            Consumables with expense policy:
                Quantity calculated from analytic account entries (sum of unit_amount)

            Consumables without expense policy:
                Quantity set manually on the Sales Order Line

            Services (manual type):
                Quantity set manually on the Sales Order Line

        Module Dependencies:
            - Base behavior applies when only the sale module is installed
            - sale_stock module overrides consumable product behavior
            - sale_timesheet module implements timesheet-based computation for service products

        Special Cases:
            Sales Order Lines originating from expenses do not generate stock pickings,
            regardless of product type (including storable products). Stock is not managed
            for expense-based lines.
        """
        for line in self:
            if line.is_expense:
                line.qty_transferred_method = "analytic"
            elif line.product_id and line.product_type == "service":
                line.qty_transferred_method = "manual"
            elif line.product_id and line.product_type == "consu":
                line.qty_transferred_method = "stock_move"
            else:
                line.qty_transferred_method = False

    @api.depends("product_id")
    def _compute_custom_attribute_values(self):
        for line in self:
            if not line.product_id:
                line.product_custom_attribute_value_ids = False
                continue
            if not line.product_custom_attribute_value_ids:
                continue
            valid_values = line.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
            # remove the is_custom values that don't belong to this template
            for pacv in line.product_custom_attribute_value_ids:
                if pacv.custom_product_template_attribute_value_id not in valid_values:
                    line.product_custom_attribute_value_ids -= pacv

    @api.depends("product_id")
    def _compute_no_variant_attribute_values(self):
        for line in self:
            if not line.product_id:
                line.product_no_variant_attribute_value_ids = False
                continue
            if not line.product_no_variant_attribute_value_ids:
                continue
            valid_values = line.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
            # remove the no_variant attributes that don't belong to this template
            for ptav in line.product_no_variant_attribute_value_ids:
                if ptav._origin not in valid_values:
                    line.product_no_variant_attribute_value_ids -= ptav

    @api.depends("product_id")
    def _compute_product_is_archived(self):
        for line in self:
            line.product_is_archived = line.product_id and not line.product_id.active

    @api.depends("product_id")
    def _compute_product_name_translated(self):
        for line in self:
            line.product_name_translated = line.product_id.with_context(
                lang=line.order_id._get_lang(),
            ).display_name

    @api.depends("product_id")
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    @api.depends(
        "product_id",
        "product_id.uom_id",
        "product_id.uom_ids",
    )
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id.uom_id | line.product_id.uom_ids

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            if not line.product_uom_id or (
                line.product_id.uom_id.id != line.product_uom_id.id
            ):
                line.product_uom_id = line.product_id.uom_id

    @api.depends("product_id")
    def _compute_product_uom_qty(self):
        for line in self.filtered(lambda x: not x.display_type):
            if not line.product_id:
                line.product_uom_qty = False
                continue
            product_uom_qty = 1.0
            # Set quantity if not set yet OR product changed
            if not line.product_uom_qty or (
                line._origin.product_id and line._origin.product_id != line.product_id
            ):
                line.product_uom_qty = product_uom_qty

    @api.depends("product_id", "linked_line_id", "linked_line_ids")
    def _compute_name(self):
        for line in self:
            if not line.product_id and not line.is_downpayment:
                continue

            lang = line.order_id._get_lang()
            if lang != self.env.lang:
                line = line.with_context(lang=lang)

            if line.product_id:
                line.name = line._get_line_multiline_description_sale()
                continue

            if line.is_downpayment:
                line.name = line._get_downpayment_description()

    @api.depends("product_id", "product_uom_id", "product_uom_qty")
    def _compute_pricelist_item_id(self):
        for line in self:
            if (
                not line.product_id
                or line.display_type
                or not line.order_id.pricelist_id
            ):
                line.pricelist_item_id = False
            else:
                line.pricelist_item_id = line.order_id.pricelist_id._get_product_rule(
                    # No need for the price context, we're not considering the price here
                    product=line.product_id,
                    **line._get_pricelist_kwargs(),
                )

    @api.depends("product_id", "product_uom_id", "product_uom_qty")
    def _compute_price_unit(self):
        """Automatically update price from pricelist when dependencies change.

        This method updates both the visible price_unit and the shadow field
        price_unit_shadow. For manual prices, only the shadow is updated
        (keeping it fresh for debugging/UI comparisons).

        Price updates are skipped for:
        - Display lines (sections, notes)
        - Down payments
        - Global discount lines
        - Lines with manual price override (unless force_price_recomputation=True)
        - Invoiced lines (qty_invoiced > 0)
        - Expense lines with cost policy
        """
        force_recompute = self.env.context.get("force_price_recomputation")

        for line in self.filtered(lambda x: not x.display_type):
            # Skip special line types
            if not line.order_id or line.is_downpayment or line._is_global_discount():
                continue

            # Check if price update is allowed
            if not line._should_update_price(force_recompute):
                # Price is protected, but update shadow to keep it fresh
                if line.product_id and line.product_uom_id:
                    line._update_price_unit_shadow()
                continue

            # Update price from pricelist
            line._update_price_unit()

    @api.depends("product_id", "product_uom_id", "product_uom_qty")
    def _compute_discount(self):
        discount_enabled = self.env[
            "product.pricelist.item"
        ]._is_discount_feature_enabled()
        for line in self.filtered(lambda x: not x.display_type):
            if not line.product_id:
                line.discount = 0.0

            if not (line.order_id.pricelist_id and discount_enabled):
                continue

            if line.combo_item_id:
                line.discount = line._get_line_linked().discount
                continue

            line.discount = 0.0

            if not line.pricelist_item_id._show_discount():
                # No pricelist rule was found for the product
                # therefore, the pricelist didn't apply any discount/change
                # to the existing sales price.
                continue

            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()

            if base_price != 0:  # Avoid division by zero
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (
                    discount < 0 and base_price < 0
                ):
                    # only show negative discounts if price is negative
                    # otherwise it's a surcharge which shouldn't be shown to the customer
                    line.discount = discount

    @api.depends("price_unit", "discount")
    def _compute_price_unit_discounted_taxexc(self):
        for line in self.filtered(lambda x: not x.display_type):
            line.price_unit_discounted_taxexc = line.price_unit * (
                1 - (line.discount or 0.0) / 100.0
            )

    @api.depends("tax_ids", "product_uom_qty", "price_unit", "discount")
    def _compute_amounts(self):
        AccountTax = self.env["account.tax"]
        for line in self.filtered(lambda l: not l.display_type):
            company = line.company_id or self.env.company
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            line.price_subtotal = base_line["tax_details"]["total_excluded_currency"]
            line.price_total = base_line["tax_details"]["total_included_currency"]
            line.price_tax = line.price_total - line.price_subtotal

    @api.depends("product_uom_qty", "price_total")
    def _compute_price_unit_discounted_taxinc(self):
        for line in self:
            line.price_unit_discounted_taxinc = (
                line.price_total / line.product_uom_qty if line.product_uom_qty else 0.0
            )

    @api.depends(
        "qty_transferred_method",
        "analytic_line_ids.so_line",
        "analytic_line_ids.product_uom_id",
        "analytic_line_ids.unit_amount",
    )
    def _compute_qty_transferred(self):
        """This method compute the delivered quantity of the SO lines: it covers the case provide by sale module, aka
        expense/vendor bills (sum of unit_amount of AAL), and manual case.
        This method should be overridden to provide other way to automatically compute delivered qty. Overrides should
        take their concerned so lines, compute and set the `qty_transferred` field, and call super with the remaining
        records.
        """
        lines_by_analytic = self.filtered(
            lambda line: line.qty_transferred_method == "analytic",
        )
        mapping = lines_by_analytic._get_qty_delivered_by_analytic(
            [("amount", "<=", 0.0)],
        )
        for line in lines_by_analytic:
            line.qty_transferred = mapping.get(line.id or line._origin.id, 0.0)

    @api.depends_context("accrual_entry_date")
    @api.depends("qty_transferred")
    def _compute_qty_transferred_at_date(self):
        if not self._date_in_the_past():
            # Avoid useless compute if we don't look in the past.
            for line in self:
                line.qty_transferred_at_date = line.qty_transferred
            return
        delivered_qties = self._prepare_qty_transferred()
        for line in self:
            line.qty_transferred_at_date = delivered_qties[line]

    @api.depends(
        "state",
        "product_id",
        "product_id.invoice_policy",
        "product_uom_qty",
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

        Replaces three previous methods (_compute_qty_invoiced, _compute_amounts_invoice,
        _compute_amount_to_invoice) to eliminate duplication and improve performance.

        Computes in single pass:
        - qty_invoiced, qty_to_invoice
        - amount_taxexc_invoiced, amount_taxexc_to_invoice
        - amount_taxinc_invoiced, amount_taxinc_to_invoice
        """
        combo_lines = set()

        for line in self.filtered(lambda x: not x.display_type):
            qty_to_consider = (
                line.qty_transferred
                if line.product_id.invoice_policy == "transferred"
                else line.product_uom_qty  # invoice_policy == "ordered"
            )
            qty_invoiced = 0.0
            amount_taxexc_invoiced = 0.0
            amount_taxinc_invoiced = 0.0

            invoice_lines = line._get_invoice_lines().filtered(
                lambda x: x.parent_state == "posted"
            )

            for invoice_line in invoice_lines:
                # Direction: +1 for refunds (in_refund), -1 for invoices (out_invoice)
                direction_sign = -invoice_line.move_id.direction_sign

                # Quantity tracking
                qty_invoiced_unsigned = invoice_line.product_uom_id._compute_quantity(
                    invoice_line.quantity,
                    line.product_uom_id,
                )
                qty_invoiced += qty_invoiced_unsigned * direction_sign

                # Amount tracking (tax-excluded)
                amount_taxexc_unsigned = invoice_line.currency_id._convert(
                    invoice_line.price_subtotal,
                    line.currency_id,
                    line.company_id,
                    invoice_line.invoice_date or fields.Date.today(),
                )
                amount_taxexc_invoiced += amount_taxexc_unsigned * direction_sign

                # Amount tracking (tax-included)
                amount_taxinc_unsigned = invoice_line.currency_id._convert(
                    invoice_line.price_total,
                    line.currency_id,
                    line.company_id,
                    invoice_line.invoice_date or fields.Date.today(),
                )
                amount_taxinc_invoiced += amount_taxinc_unsigned * direction_sign

            line.qty_invoiced = qty_invoiced
            line.amount_taxexc_invoiced = amount_taxexc_invoiced
            line.amount_taxinc_invoiced = amount_taxinc_invoiced

            if line.state in ("draft", "cancel"):
                line.amount_taxexc_to_invoice = 0.0
                line.amount_taxinc_to_invoice = 0.0
                line.qty_to_invoice = 0.0
                continue

            # Calculate "to invoice" amounts
            # Note: do not use price_subtotal field as it returns zero when the ordered
            # quantity is zero. It causes problems for expense lines (e.g.: ordered qty = 0,
            # delivered qty = 4, price_unit = 20; subtotal is zero), but when you can invoice
            # the line, you see an amount and not zero.
            price_subtotal = line.price_unit_discounted_taxexc * qty_to_consider

            # Adjust for price-included taxes
            if len(line.tax_ids.filtered(lambda tax: tax.price_include)) > 0:
                # As included taxes are not excluded from the computed subtotal, compute_all()
                # method has to be called to retrieve the subtotal without them.
                price_subtotal = line.tax_ids.compute_all(
                    line.price_unit_discounted_taxexc,
                    currency=line.currency_id,
                    quantity=qty_to_consider,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )["total_excluded"]

            # Handle special discount cases
            # Loop needed when invoice line discount is different from sale line discount
            if any(invoice_lines.mapped(lambda l: l.discount != line.discount)):
                # In case of re-invoicing with different discount we try to calculate
                # manually the remaining amount to invoice
                amount = 0
                for invoice_line in invoice_lines:
                    # Convert invoice line price to SO currency
                    converted_price = invoice_line.currency_id._convert(
                        invoice_line.price_unit,
                        line.currency_id,
                        line.company_id,
                        invoice_line.date or fields.Date.today(),
                        round=False,
                    )

                    # Calculate amount considering taxes
                    if (
                        len(
                            invoice_line.tax_ids.filtered(
                                lambda tax: tax.price_include,
                            ),
                        )
                        > 0
                    ):
                        amount += invoice_line.tax_ids.compute_all(
                            converted_price * invoice_line.quantity,
                        )["total_excluded"]
                    else:
                        amount += converted_price * invoice_line.quantity

                line.amount_taxexc_to_invoice = max(
                    price_subtotal - amount,
                    0.0,
                )
            else:
                line.amount_taxexc_to_invoice = max(
                    price_subtotal - amount_taxexc_invoiced,
                    0.0,
                )

            # Tax-included amount to invoice
            # Reuse price_total from _compute_amounts to avoid recalculation
            unit_price_total = (
                line.price_total / line.product_uom_qty if line.product_uom_qty else 0.0
            )
            line.amount_taxinc_to_invoice = unit_price_total * (
                qty_to_consider - line.qty_invoiced
            )

            # Handle quantity to invoice (with combo logic)
            if line.product_type == "combo":
                combo_lines.add(line)
            else:
                line.qty_to_invoice = max(qty_to_consider - line.qty_invoiced, 0.0)

            if line.combo_item_id and line.linked_line_id:
                combo_lines.add(line.linked_line_id)

        # Post-processing for combo products
        for combo_line in combo_lines:
            if any(
                line.combo_item_id and line.qty_to_invoice
                for line in combo_line.linked_line_ids
            ):
                combo_line.qty_to_invoice = (
                    combo_line.product_uom_qty - combo_line.qty_invoiced
                )
            else:
                combo_line.qty_to_invoice = 0.0

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
        "qty_invoiced",
        "qty_to_invoice",
        "amount_taxexc_to_invoice",
    )
    def _compute_invoice_state(self):
        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: Nothing to invoice (zero qty or non-invoiceable line).
        - to do: Has quantity to invoice, nothing invoiced yet.
        - partially: Has quantity to invoice AND some already invoiced.
        - done: Fully invoiced (qty_invoiced == qty_ordered).
        - over done: Over-invoiced (qty_invoiced > qty_ordered).

        Note: Upselling opportunities (qty_delivered > qty_ordered) are tracked
        at the order level via the has_upsell_opportunity field.
        """
        precision = self.env["decimal.precision"].precision_get("Product Unit")
        for line in self.filtered(lambda l: not l.display_type):
            if line.is_downpayment and line.amount_taxexc_to_invoice == 0:
                line.invoice_state = "done"

            elif float_is_zero(line.product_uom_qty, precision_digits=precision):
                line.invoice_state = "no"

            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                if float_is_zero(line.qty_invoiced, precision_digits=precision):
                    # Nothing invoiced yet
                    line.invoice_state = "to do"
                elif not float_is_zero(line.qty_invoiced, precision_digits=precision):
                    # Some quantity already invoiced
                    line.invoice_state = "partial"

            elif float_is_zero(line.qty_to_invoice, precision_digits=precision):
                compare = float_compare(
                    line.qty_invoiced,
                    line.product_uom_qty,
                    precision_digits=precision,
                )
                if compare == 0:
                    line.invoice_state = "done"
                elif compare > 0:
                    line.invoice_state = "over done"

    @api.depends("state", "product_id", "qty_invoiced", "qty_transferred")
    def _compute_product_readonly(self):
        """Compute whether product field should be readonly.

        The product becomes readonly when:
        - Line is a downpayment
        - Order is cancelled
        - Order is confirmed (sale state) AND any of:
          * Order is locked
          * Line has been invoiced (qty_invoiced > 0)
          * Line has been delivered (qty_transferred > 0)

        This field provides a consistent pattern with product_uom_readonly
        for use in view readonly attributes.

        Modules extending this behavior should override this method.
        """
        self.product_readonly = False
        for line in self.filtered(lambda l: not l.display_type):
            if (
                line.is_downpayment
                or line.state == "cancel"
                or line.state == "done"
                and (
                    line.order_id.locked
                    or line.qty_invoiced > 0
                    or line.qty_transferred > 0
                )
            ):
                line.product_readonly = True

    @api.depends("state")
    def _compute_product_uom_readonly(self):
        for line in self.filtered(lambda l: not l.display_type):
            # line.ids checks whether it's a new record not yet saved
            line.product_uom_readonly = line.ids and line.state in ["done", "cancel"]

    # ------------------------------------------------------------
    # SEARCH METHODS
    # ------------------------------------------------------------

    def _search_product_template_id(self, operator, value):
        return [("product_id.product_tmpl_id", operator, value)]

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    @api.readonly
    def action_add_from_catalog(self):
        order = self.env["sale.order"].browse(self.env.context.get("order_id"))
        return order.with_context(child_field="line_ids").action_add_from_catalog()

    def action_view_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.order_id.id,
            "view_mode": "form",
        }

    # ------------------------------------------------------------
    # CATALOGUE MIXIN METHODS
    # ------------------------------------------------------------

    def _get_product_catalog_lines_data(self, **kwargs):
        """Return information about sale order lines in `self`.

        If `self` is empty, this method returns only the default value(s) needed for the product
        catalog. In this case, the quantity that equals 0.

        Otherwise, it returns a quantity and a price based on the product of the SOL(s) and whether
        the product is read-only or not.

        A product is considered read-only if the order is considered read-only (see
        ``SaleOrder._is_readonly`` for more details) or if `self` contains multiple records.

        Note: This method cannot be called with multiple records that have different products linked.

        :raise odoo.exceptions.ValueError: ``len(self.product_id) != 1``
        :rtype: dict
        :return: A dict with the following structure:
            {
                'quantity': float,
                'price': float,
                'readOnly': bool,
                'uomDisplayName': String,
            }
        """
        if len(self) == 1:
            return {
                "quantity": self.product_uom_qty,
                "price": self._get_price_discounted(),
                "readOnly": (self.order_id._is_readonly() or bool(self.combo_item_id)),
                "uomDisplayName": self.product_uom_id.display_name,
            }
        elif self:
            self.product_id.ensure_one()
            order_line = self[0]
            order = order_line.order_id
            return {
                "readOnly": True,
                "price": order.pricelist_id._get_product_price(
                    product=order_line.product_id,
                    quantity=1.0,
                    currency=order.currency_id,
                    date=order.date_order,
                    **kwargs,
                ),
                "quantity": sum(
                    self.mapped(
                        lambda line: line.product_uom_id._compute_quantity(
                            qty=line.product_uom_qty,
                            to_unit=line.product_id.uom_id,
                        ),
                    ),
                ),
                "uomDisplayName": self.product_id.uom_id.display_name,
            }
        else:
            return {
                "quantity": 0,
                # price will be computed in batch with pricelist utils so not given here
            }

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _additional_name_per_id(self):
        return {line.id: line._get_partner_display() for line in self}

    def compute_uom_qty(self, new_qty, stock_move, rounding=True):
        return self.product_uom_id._compute_quantity(
            new_qty,
            stock_move.product_uom,
            rounding,
        )

    def _convert_to_sol_currency(self, amount, currency):
        """Convert the given amount from the given currency to the SO(L) currency.

        :param float amount: the amount to convert
        :param currency: currency in which the given amount is expressed
        :type currency: `res.currency` record
        :returns: converted amount
        :rtype: float
        """
        self.ensure_one()
        to_currency = self.currency_id or self.order_id.currency_id
        if currency and to_currency and currency != to_currency:
            conversion_date = self.order_id.date_order or fields.Date.context_today(
                self,
            )
            company = self.company_id or self.order_id.company_id or self.env.company
            return currency._convert(
                from_amount=amount,
                to_currency=to_currency,
                company=company,
                date=conversion_date,
                round=False,
            )
        return amount

    def _domain_product_id(self):
        return [("sale_ok", "=", True)]

    def _get_combo_totals(self, totals_field):
        """Return the total/subtotal amount sale order lines linked to combo."""
        self.ensure_one()
        combo_item_lines = self.order_id.line_ids.filtered(
            lambda line: line.linked_line_id == self and line.combo_item_id,
        )
        return sum(combo_item_lines.mapped(totals_field))

    def _get_custom_compute_tax_cache_key(self):
        """Hook method to be able to set/get cached taxes while computing them"""
        return tuple()

    def _get_date_order(self):
        self.ensure_one()
        return self.order_id.date_order

    def _get_date_planned(self):
        self.ensure_one()
        if self.state == "done" and self.order_id.date_order:
            order_date = self.order_id.date_order
        else:
            order_date = fields.Datetime.now()
        return order_date + timedelta(days=self.customer_lead or 0.0)

    def _get_downpayment_description(self):
        self.ensure_one()

        if self.display_type:
            return _("Down Payments")

        dp_state = self._get_downpayment_state()
        name = _("Down Payment")
        if dp_state == "draft":
            name = _(
                "Down Payment: %(date)s (Draft)",
                date=format_date(self.env, self.create_date.date()),
            )
        elif dp_state == "cancel":
            name = _("Down Payment (Cancelled)")
        else:
            invoice = (
                self._get_invoice_lines()
                .filtered(lambda aml: aml.quantity >= 0)
                .move_id.filtered(lambda move: move.move_type == "out_invoice")
            )
            if len(invoice) == 1 and invoice.payment_reference and invoice.invoice_date:
                name = _(
                    "Down Payment (ref: %(reference)s on %(date)s)",
                    reference=invoice.payment_reference,
                    date=format_date(self.env, invoice.invoice_date),
                )

        return name

    def _get_downpayment_price_unit(self, invoices):
        return sum(
            l.price_unit if l.move_id.move_type == "out_invoice" else -l.price_unit
            for l in self.invoice_line_ids
            if l.move_id.state == "posted"
            and l.move_id not in invoices  # don't recompute with the final invoice
        )

    def _get_downpayment_state(self):
        self.ensure_one()

        if self.display_type:
            return ""

        invoice_lines = self._get_invoice_lines()
        if all(line.parent_state == "draft" for line in invoice_lines):
            return "draft"
        if all(line.parent_state == "cancel" for line in invoice_lines):
            return "cancel"

        return ""

    def _get_grouped_section_summary(self, display_taxes=True):
        """Return a tax-wise summary of sales order lines linked to section.

        Group lines by their tax IDs and computes subtotal and total for each group.
        """
        self.ensure_one()

        section_lines = self.order_id.line_ids.filtered(self._is_line_in_section)

        if display_taxes:
            res = [
                {
                    "tax_labels": [tax.tax_label for tax in taxes if tax.tax_label],
                    "price_subtotal": sum(lines.mapped("price_subtotal")),
                    "price_total": sum(lines.mapped("price_total")),
                }
                for taxes, lines in section_lines.grouped("tax_ids").items()
            ]
        else:
            res = [
                {
                    "tax_labels": [],
                    "price_subtotal": sum(section_lines.mapped("price_subtotal")),
                    "price_total": sum(section_lines.mapped("price_total")),
                },
            ]
        return res or [
            {
                "tax_labels": [],
                "price_subtotal": 0.0,
                "price_total": 0.0,
            },
        ]

    def _get_invoice_line_sequence(self, new=0, old=0):
        """
        Method intended to be overridden in third-party module if we want to prevent the resequencing
        of invoice lines.

        :param int new:   the new line sequence
        :param int old:   the old line sequence

        :return:          the sequence of the SO line, by default the new one.
        """
        return new or old

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

    def _get_line_linked(self):
        """Return the linked line of this line, if any.

        This method relies on either `linked_line_id` or `linked_virtual_id` to retrieve the linked
        line, depending on whether the linked line is saved in the DB.
        """
        self.ensure_one()
        return (
            self.linked_line_id
            or (
                self.linked_virtual_id
                and self.order_id.line_ids.filtered(
                    lambda line: line.virtual_id == self.linked_virtual_id,
                ).ensure_one()
            )
            or self.env["sale.order.line"]
        )

    def _get_line_multiline_description_sale(self):
        """Compute a default multiline description for this sales order line.

        In most cases the product description is enough but sometimes we need to append information that only
        exists on the sale order line itself.
        e.g:
        - custom attributes and attributes that don't create variants, both introduced by the "product configurator"
        - in event_sale we need to know specifically the sales order line as well as the product to generate the name:
          the product is not sufficient because we also need to know the event_id and the event_ticket_id (both which belong to the sale order line).
        """
        self.ensure_one()
        description = (
            self.product_id.get_product_multiline_description_sale()
            + self._get_line_multiline_description_variants()
        )
        if self.linked_line_id and not self.combo_item_id:
            description += "\n" + _(
                "Option for: %s",
                self.linked_line_id.product_id.with_context(
                    display_default_code=False,
                ).display_name,
            )
        return description

    def _get_line_multiline_description_variants(self):
        """When using no_variant attributes or is_custom values, the product
        itself is not sufficient to create the description: we need to add
        information about those special attributes and values.

        :return: the description related to special variant attributes/values
        :rtype: string
        """
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin.filtered(
            # Only describe the attributes where a choice was made by the customer
            lambda ptav: ptav.display_type == "multi"
            or ptav.attribute_line_id.value_count > 1,
        )
        if not self.product_custom_attribute_value_ids and not no_variant_ptavs:
            return ""

        name = ""

        custom_ptavs = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        multi_ptavs = no_variant_ptavs.filtered(
            lambda ptav: ptav.display_type == "multi",
        ).sorted()

        # display the no_variant attributes, except those that are also
        # displayed by a custom (avoid duplicate description)
        for ptav in no_variant_ptavs - multi_ptavs - custom_ptavs:
            name += "\n" + ptav.display_name

        # display the selected values per attribute on a single for a multi checkbox
        for pta, ptavs in groupby(multi_ptavs, lambda ptav: ptav.attribute_id):
            name += "\n" + _(
                "%(attribute)s: %(values)s",
                attribute=pta.name,
                values=", ".join(ptav.name for ptav in ptavs),
            )

        # Sort the values according to _order settings, because it doesn't work for virtual records in onchange
        sorted_custom_ptav = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id.sorted()
        for patv in sorted_custom_ptav:
            pacv = self.product_custom_attribute_value_ids.filtered(
                lambda pcav: pcav.custom_product_template_attribute_value_id == patv,
            )
            name += "\n" + pacv.display_name

        return name

    def get_line_parent_section(self):
        if not self.display_type and self.parent_id.display_type == "line_subsection":
            return self.parent_id.parent_id

        return self.parent_id

    def _get_lines_linked(self):
        """Return the linked lines of this line, if any.

        This method relies on either `linked_line_id` or `linked_virtual_id` to retrieve the linked
        lines, depending on whether this line is saved in the DB.

        Note: we can't rely on `linked_line_ids` as it will only be populated when both this line
        and its linked lines are saved in the DB, which we can't ensure.
        """
        self.ensure_one()
        return (
            (
                self._origin
                and self.order_id.line_ids.filtered(
                    lambda line: line.linked_line_id._origin == self._origin,
                )
            )
            or (
                self.virtual_id
                and self.order_id.line_ids.filtered(
                    lambda line: line.linked_virtual_id == self.virtual_id,
                )
            )
            or self.env["sale.order.line"]
        )

    def _get_lines_sellable_domain(self):
        discount_products_ids = self.env.companies.sale_discount_product_id.ids
        domain = Domain("is_downpayment", "=", False)
        if discount_products_ids:
            domain &= Domain("product_id", "not in", discount_products_ids)
        return domain

    def _get_lines_with_price(self):
        """A combo product line always has a zero price (by design). The actual price of the combo
        product can be computed by summing the prices of its combo items (i.e. its linked lines).
        """
        if self.product_type == "combo":
            # Only consider combo item lines (not optional product lines)
            return self.linked_line_ids.filtered("combo_item_id")
        return self

    def _get_partner_display(self):
        self.ensure_one()
        commercial_partner = self.sudo().partner_id.commercial_partner_id
        return f"({commercial_partner.ref or commercial_partner.name})"

    def _get_price_discounted(self):
        self.ensure_one()
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0)

    def _get_price_display(self):
        """Compute the displayed unit price for a given line.

        Overridden in custom flows:
        * where the price is not specified by the pricelist
        * where the discount is not specified by the pricelist

        Note: self.ensure_one()
        """
        self.ensure_one()

        if self.product_type == "combo":
            return 0  # The display price of a combo line should always be 0.
        if self.combo_item_id:
            return self._get_price_display_combo_item()
        return self._get_price_display_regular_item()

    def _get_price_display_combo_item(self):
        """Compute the display price of this SOL's combo item.

        A combo item's price is a fraction of its combo product's price (i.e. the product of type
        `combo` which is referenced in this SOL's linked line). It is independent of the combo
        item's product (i.e. the product referenced in this SOL). The combo's `base_price` will be
        used to prorate the price of this combo with respect to the other combos in the combo
        product.

        Note: this method will throw if this SOL has no combo item or no linked combo product.
        """
        self.ensure_one()

        # Compute the combo product's price.
        combo_line = self._get_line_linked()
        combo_product_price = combo_line._get_price_display_regular_item()
        # Compute the combos' base prices.
        combo_base_prices = {
            combo_id: combo_id.currency_id._convert(
                from_amount=combo_id.base_price,
                to_currency=self.currency_id,
                company=self.company_id,
                date=self.order_id.date_order,
            )
            for combo_id in combo_line.product_template_id.sudo().combo_ids
        }
        total_combo_base_price = sum(combo_base_prices.values())
        # Compute the prorated combo prices.
        combo_prices = {
            combo_id: self.currency_id.round(
                # Don't divide by total_combo_base_price if it's 0. This will make the prorating
                # wrong, but the delta will be fixed by combo_price_delta below.
                base_price * combo_product_price / (total_combo_base_price or 1),
            )
            for (combo_id, base_price) in combo_base_prices.items()
        }
        # Compute the delta between the combo product's price and the sum of its combo prices.
        # Ideally, this should be 0, but division in python isn't perfect, so we may need to adjust
        # the combo prices to make the delta 0.
        combo_price_delta = combo_product_price - sum(combo_prices.values())
        if combo_price_delta:
            combo_prices[combo_line.product_template_id.sudo().combo_ids[-1]] += (
                combo_price_delta
            )
        # Add the extra price of this combo item, as well as the extra prices of any `no_variant`
        # attributes to the combo price.
        return (
            combo_prices[self.combo_item_id.combo_id]
            + self.combo_item_id.extra_price
            + self.product_id._get_no_variant_attributes_price_extra(
                self.product_no_variant_attribute_value_ids,
            )
        )

    def _get_price_display_regular_item(self):
        """This helper method allows to compute the display price of a SOL, while ignoring combo
        logic.

        I.e. this method returns the display price of a SOL as if it were neither a combo line nor a
        combo item line.
        """
        self.ensure_one()

        pricelist_price = self._get_pricelist_price()

        if not self.pricelist_item_id._show_discount():
            # No pricelist rule found => no discount from pricelist
            return pricelist_price

        base_price = self._get_pricelist_price_before_discount()

        # negative discounts (= surcharge) are included in the display price
        return max(base_price, pricelist_price)

    def _get_pricelist_kwargs(self):
        return {
            "quantity": self.product_uom_qty or 1.0,
            "uom": self.product_uom_id,
            "date": self._get_date_order(),
            "currency": self.currency_id,
        }

    def _get_pricelist_price(self):
        """Compute the price given by the pricelist for the given line information.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()
        return self.pricelist_item_id._compute_price(
            product=self.product_id.with_context(**self._get_product_price_context()),
            **self._get_pricelist_kwargs(),
        )

    def _get_pricelist_price_before_discount(self):
        """Compute the price used as base for the pricelist price computation.
        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()

        return self.pricelist_item_id._compute_price_before_discount(
            product=self.product_id.with_context(**self._get_product_price_context()),
            **self._get_pricelist_kwargs(),
        )

    def _get_pricelist_price_context(self):
        """DO NOT USE in new code, this contextual logic should be dropped or heavily refactored soon"""
        self.ensure_one()
        return {
            "pricelist": self.order_id.pricelist_id.id,
            "uom": self.product_uom_id.id,
            "quantity": self.product_uom_qty,
            "date": self._get_date_order(),
        }

    def get_pricelist_price_current(self):
        """Get the current pricelist price without changing the line.

        This is useful to show users what the pricelist says even when
        they have a manual override in place.

        :return: Current pricelist price (tax-excluded), or False if no product
        :rtype: float or bool
        """
        self.ensure_one()
        if not self.product_id or not self.product_uom_id:
            return False

        # Get the display price (handles discounts, combo logic)
        # This is tax-excluded, which is what we store in price_unit
        line = self.with_company(self.company_id)
        return line._get_price_display()

    def _get_product_price_context(self):
        """Gives the context for product price computation.

        :return: additional context to consider extra prices from attributes in the base product price.
        :rtype: dict
        """
        self.ensure_one()
        return self.product_id._get_product_price_context(
            self.product_no_variant_attribute_value_ids,
        )

    def _get_protected_fields(self):
        """Give the fields that should not be modified on a locked SO.

        :returns: list of field names
        :rtype: list
        """
        return [
            "product_id",
            "name",
            "price_unit",
            "product_uom_id",
            "product_uom_qty",
            "tax_ids",
            "analytic_distribution",
            "discount",
        ]

    def _get_qty_delivered_by_analytic(self, additional_domain):
        """Compute and return the delivered quantity of current SO lines,
        based on their related analytic lines.
        :param additional_domain: domain to restrict AAL to include in computation (required since timesheet is an AAL with a project ...)
        """
        result = defaultdict(float)

        # avoid recomputation if no SO lines concerned
        if not self:
            return result

        # group analytic lines by product uom and so line
        domain = Domain.AND([[("so_line", "in", self.ids)], additional_domain])
        data = self.env["account.analytic.line"]._read_group(
            domain,
            ["product_uom_id", "so_line"],
            ["unit_amount:sum", "move_line_id:count_distinct", "__count"],
        )

        # convert uom and sum all unit_amount of analytic lines to get the delivered qty of SO lines
        for uom, line, unit_amount_sum, move_line_id_count_distinct, count in data:
            if not uom:
                continue
            # avoid counting unit_amount twice when dealing with multiple analytic lines on the same move line
            if move_line_id_count_distinct == 1 and count > 1:
                qty = unit_amount_sum / count
            else:
                qty = unit_amount_sum
            qty = uom._compute_quantity(
                qty,
                line.product_uom_id,
                rounding_method="HALF-UP",
            )
            result[line.id] += qty

        return result

    def _get_section_lines(self):
        self.ensure_one()
        return self.order_id.line_ids.filtered(self._is_line_in_section)

    def _get_section_totals(self, totals_field):
        """Return the total/subtotal amount sale order lines linked to section."""
        self.ensure_one()
        section_lines = self._get_section_lines()
        return sum(section_lines.mapped(totals_field))

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
        lines_by_order = defaultdict(lambda: self.env["sale.order.line"])
        for line in self:
            if line.product_id:  # Only post messages for product lines
                lines_by_order[line.order_id] += line

        # Post one batched message per order
        for order, order_lines in lines_by_order.items():
            count = len(order_lines)
            if count == 1:
                msg = _("Extra line with %s", order_lines.product_id.display_name)
            elif count <= 50:
                # Show all products for small batches
                product_list = (
                    "<ul>"
                    + "".join(
                        f"<li>{p}</li>"
                        for p in order_lines.mapped("product_id.display_name")
                    )
                    + "</ul>"
                )
                msg = _("Added %s extra lines: %s", count, product_list)
            else:
                # Summarize for large batches
                msg = _("Added %s extra lines to this purchase order", count)
            order.message_post(body=msg)

    def _prepare_aml_vals(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        self.ensure_one()

        if self.product_id.type == "combo":
            # If the quantity to invoice is a whole number, format it as an integer (with no decimal point)
            qty_to_invoice = (
                int(self.qty_to_invoice)
                if self.qty_to_invoice == int(self.qty_to_invoice)
                else self.qty_to_invoice
            )
            return {
                "display_type": "line_section",
                "sequence": self.sequence,
                "name": f"{self.product_id.name} x {qty_to_invoice}",
                "product_uom_id": self.product_uom_id.id,
                "quantity": self.qty_to_invoice,
                "sale_line_ids": [Command.link(self.id)],
                "collapse_prices": self.collapse_prices,
                "collapse_composition": self.collapse_composition,
                **optional_values,
            }

        res = {
            "display_type": self.display_type or "product",
            "sequence": self.sequence,
            "name": self.env["account.move.line"]._get_journal_items_full_name(
                self.name,
                self.product_id.display_name,
            ),
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom_id.id,
            "quantity": self.qty_to_invoice,
            "discount": self.discount,
            "price_unit": self.price_unit,
            "tax_ids": [Command.set(self.tax_ids.ids)],
            "sale_line_ids": [Command.link(self.id)],
            "is_downpayment": self.is_downpayment,
            "extra_tax_data": self.extra_tax_data,
            "collapse_prices": self.collapse_prices,
            "collapse_composition": self.collapse_composition,
        }
        downpayment_lines = self.invoice_line_ids.filtered("is_downpayment")
        if self.is_downpayment and downpayment_lines:
            res["account_id"] = downpayment_lines.account_id[:1].id
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res["account_id"] = False
        return res

    def _prepare_aml_vals_list(self, **optional_values):
        return [self._prepare_aml_vals(**optional_values)]

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        company = self.order_id.company_id or self.env.company
        base_values = {
            "tax_ids": self.tax_ids,
            "quantity": self.product_uom_qty,
            "partner_id": self.order_id.partner_id,
            "currency_id": self.order_id.currency_id or company.currency_id,
            "rate": self.order_id.currency_rate,
            "name": self.name,
        }
        if self._is_global_discount():
            base_values["special_type"] = "global_discount"
        elif self.is_downpayment:
            base_values["special_type"] = "down_payment"
        base_values.update(kwargs)
        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            self,
            **base_values,
        )

    def _prepare_procurement_vals(self):
        """Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        return {}

    def _prepare_qty_invoiced(self):
        invoiced_qties = defaultdict(float)
        for line in self:
            for invoice_line in line._get_invoice_lines():
                if (
                    invoice_line.move_id.state != "cancel"
                    or invoice_line.move_id.payment_state == "invoicing_legacy"
                ):
                    invoice_qty = invoice_line.product_uom_id._compute_quantity(
                        invoice_line.quantity, line.product_uom_id
                    )
                    if invoice_line.move_id.move_type == "out_invoice":
                        invoiced_qties[line] += invoice_qty
                    elif invoice_line.move_id.move_type == "out_refund":
                        invoiced_qties[line] -= invoice_qty
        return invoiced_qties

    def _reset_price_unit(self):
        """Fetch price from pricelist and reset all price-related fields.

        This method:
        - Calculates price from pricelist based on product/quantity/UoM
        - Adjusts price for tax inclusion based on fiscal position
        - Syncs price_unit and price_unit_shadow
        - Clears the manual price flag (returns to automatic pricing)
        """
        self.ensure_one()

        # Use the public API method to get current pricelist price
        price_unit = self.get_pricelist_price_current()

        self.update(
            {
                "price_unit": price_unit,
                "price_unit_shadow": price_unit,
                "price_is_manual": False,
            },
        )

    def _prepare_qty_transferred(self):
        # compute for analytic lines
        delivered_qties = defaultdict(float)
        lines_by_analytic = self.filtered(
            lambda sol: sol.qty_delivered_method == "analytic"
        )
        mapping = lines_by_analytic._get_qty_delivered_by_analytic(
            [("amount", "<=", 0.0)]
        )
        for so_line in lines_by_analytic:
            delivered_qties[so_line] = mapping.get(
                so_line.id or so_line._origin.id, 0.0
            )
        return delivered_qties

    def set_manual_price(self, price):
        """Set a manual price that will be protected from automatic updates.

        This method explicitly marks the price as manually overridden, preventing
        the system from automatically updating it when product, quantity, or UoM changes.

        The shadow field is updated to current pricelist for comparison purposes.

        To remove the manual override and return to automatic pricing, use
        reset_to_pricelist_price().

        :param float price: The manual price to set
        :raises UserError: If line is invoiced (cannot change price)
        """
        for line in self:
            if line.qty_invoiced > 0:
                raise UserError(
                    _("Cannot set manual price on invoiced line %s", line.display_name),
                )

            # Get current pricelist price for shadow (comparison)
            pricelist_price = line.get_pricelist_price_current()

            line.write(
                {
                    "price_unit": price,
                    "price_unit_shadow": pricelist_price,
                    "price_is_manual": True,
                },
            )

    def reset_to_pricelist_price(self):
        """Reset price to current pricelist price, removing manual override.

        This method forces recalculation from pricelist even if price was
        manually set. It's equivalent to clicking "Update Prices" button.

        :raises UserError: If line is invoiced (cannot change price)
        """
        for line in self:
            if line.qty_invoiced > 0:
                raise UserError(
                    _("Cannot reset price on invoiced line %s", line.display_name),
                )

        return self.with_context(force_price_recomputation=True)._compute_price_unit()

    def _set_analytic_distribution(self, inv_line_vals, **optional_values):
        if self.analytic_distribution and not self.display_type:
            inv_line_vals["analytic_distribution"] = self.analytic_distribution

    def _update_line_quantity(self, values):
        orders = self.mapped("order_id")
        for order in orders:
            order_lines = self.filtered(lambda x: x.order_id == order)
            msg = Markup("<b>%s</b><ul>") % _("The ordered quantity has been updated.")
            for line in order_lines:
                if (
                    "product_id" in values
                    and values["product_id"] != line.product_id.id
                ):
                    # tracking is meaningless if the product is changed as well.
                    continue
                msg += Markup("<li> %s: <br/>") % line.product_id.display_name
                msg += _(
                    "Ordered Quantity: %(old_qty)s -> %(new_qty)s",
                    old_qty=line.product_uom_qty,
                    new_qty=values["product_uom_qty"],
                ) + Markup("<br/>")
                if line.product_id.type == "consu":
                    msg += _("Delivered Quantity: %s", line.qty_transferred) + Markup(
                        "<br/>",
                    )
                msg += _("Invoiced Quantity: %s", line.qty_invoiced) + Markup("<br/>")
            msg += Markup("</ul>")
            order.message_post(body=msg)

    def _update_price_unit(self):
        """Update price_unit and related fields from pricelist.

        This method:
        - Fetches the current pricelist price (False if no product/uom)
        - Updates price_unit and price_unit_shadow
        - Clears the manual price flag

        Validation is delegated to get_pricelist_price_current() - single source of truth.
        """
        self.ensure_one()
        self = self.with_context(sale_write_from_compute=True)
        self._reset_price_unit()

    def _update_price_unit_shadow(self):
        """Update only price_unit_shadow to reflect current pricelist.

        This method is called for lines with manual price overrides to keep
        the shadow field fresh. This allows:
        - Debugging: see what pricelist says vs manual price
        - UI: show comparison "Pricelist: $100 / Your price: $120"
        - Analytics: track manual price deviations

        The visible price_unit field is NOT changed (manual price protected).
        """
        self.ensure_one()
        pricelist_price = self.get_pricelist_price_current()
        self.with_context(sale_write_from_compute=True).write(
            {
                "price_unit_shadow": pricelist_price,
            },
        )

    # ------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------

    # For `sale_management`, to control optional products on portal
    def _can_be_edited_on_portal(self):
        self.ensure_one()
        return self.order_id._can_be_edited_on_portal() and not self.combo_item_id

    def _can_be_invoiced_alone(self):
        """Whether a given line is meaningful to invoice alone.

        It is generally meaningless/confusing or even wrong to invoice some specific SOlines
        (delivery, discounts, rewards, ...) without others, unless they are the only left to invoice
        in the SO.
        """
        self.ensure_one()
        return self.product_id.id != self.company_id.sale_discount_product_id.id

    def _check_line_unlink(self):
        """Check whether given lines can be deleted or not.

        * Lines that have been invoiced cannot be deleted (financial tracking required).
        * Sections, subsections and notes can always be deleted.
        * Confirmed lines without invoices can be deleted (including uninvoiced down payments).

        :returns: Sales Order Lines that cannot be deleted
        :rtype: `sale.order.line` recordset
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

    def _has_taxes(self):
        """Check if a line has taxes or not. For (sub)sections, check if any child line has taxes."""
        self.ensure_one()
        return bool(
            self.tax_ids
            or (
                self.display_type
                and any(line._has_taxes() for line in self._get_section_lines())
            ),
        )

    def has_valued_move_ids(self):
        return None  # TODO: remove in master

    def _is_delivery(self):
        self.ensure_one()
        return False

    def _is_discount_line(self):
        self.ensure_one()
        return self.product_id in self.company_id.sale_discount_product_id

    def _is_global_discount(self):
        self.ensure_one()
        return self.extra_tax_data and self.extra_tax_data.get(
            "computation_key",
            "",
        ).startswith("global_discount,")

    def _is_line_in_section(self, line):
        """Return whether the line is a direct or indirect child of the section."""
        self.ensure_one()
        is_direct_child = line.parent_id == self and not line.display_type
        is_indirect_child = (
            self.display_type == "line_section"
            and line.parent_id
            and line.parent_id.display_type == "line_subsection"
            and line.parent_id.parent_id == self
        )
        return is_direct_child or is_indirect_child

    def is_manual_price(self):
        """Check if current price is a manual override (not from pricelist).

        :return: True if price was manually set, False if from pricelist
        :rtype: bool
        """
        self.ensure_one()
        return self.price_is_manual

    def _should_update_price(self, force_recompute=False):
        """Determine if price should be automatically updated from pricelist.

        :param bool force_recompute: If True, bypass manual price protection
        :return: True if price should be updated, False otherwise
        :rtype: bool
        """
        self.ensure_one()

        # Never update invoiced lines (accounting integrity)
        if self.qty_invoiced > 0:
            return False

        # Never update expense lines with cost policy
        if self.product_id.expense_policy == "cost" and self.is_expense:
            return False

        # Respect manual price override unless forced
        if not force_recompute and self.price_is_manual:
            return False

        return True

    def _validate_analytic_distribution(self):
        for line in self.filtered(
            lambda l: not l.display_type and l.state in ["draft", "sent"],
        ):
            line._validate_distribution(
                **{
                    "product": line.product_id.id,
                    "business_domain": "sale_order",
                    "company_id": line.company_id.id,
                },
            )

    def _validate_write_vals(self, write_vals):
        for method_name in self._get_validate_write_vals_methods():
            if hasattr(self, method_name):
                getattr(self, method_name)(write_vals)

    def _get_validate_write_vals_methods(self):
        return [
            "_validate_write_display_type",
            "_validate_write_locked_order",
            "_validate_write_product_and_uom",
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
                    "You cannot change the type of %s purchase order lines (%s). "
                    "Instead, delete these lines and create new lines of the proper type.",
                    len(lines),
                    error_msg,
                ),
            )

    def _validate_write_locked_order(self, write_vals):
        """Validate that protected fields are not being modified on a locked order."""
        # Filter to only lines from locked orders
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

        # Get field descriptions for error message
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

    def _validate_write_product_and_uom(self, write_vals):
        """Validate product_id and product_uom_id changes on order lines.

        This validation applies to non-locked lines and checks:
        - product_id changes against product_readonly field
        - product_uom_id changes against product_uom_readonly field

        Note: Locked order validation is handled by _validate_write_locked_order,
        which runs before this method in the validation chain.
        """
        # Validate product_id changes using product_readonly
        if "product_id" in write_vals:
            lines_blocked = self.filtered(
                lambda l: l.product_id.id != write_vals.get("product_id")
                and l.product_readonly,
            )
            if lines_blocked:
                self._raise_field_change_error(lines_blocked, "product")

        # Validate product_uom_id changes using product_uom_readonly
        if "product_uom_id" in write_vals:
            lines_blocked = self.filtered(
                lambda l: l.product_uom_id.id != write_vals.get("product_uom_id")
                and l.product_uom_readonly,
            )
            if lines_blocked:
                self._raise_field_change_error(
                    lines_blocked,
                    "unit of measure",
                    "because it is in a confirmed state",
                )

    def _raise_field_change_error(self, lines, field_description, reason=""):
        """Raise an error when a field cannot be changed.

        Args:
            lines: Recordset of lines that cannot be changed
            field_description: Human-readable field name (e.g., "product", "unit of measure")
            reason: Optional reason for the restriction (e.g., "because it is in a confirmed state")
        """
        reason_text = f" {reason}" if reason else ""

        if len(lines) == 1:
            line = lines[0]
            line_id = self._get_line_identifier(line)
            raise UserError(
                _(
                    "You cannot change the %s of order line '%s'%s.",
                    field_description,
                    line_id,
                    reason_text,
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
                    "You cannot change the %s of %s order lines (%s)%s.",
                    field_description,
                    len(lines),
                    error_msg,
                    reason_text,
                ),
            )

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
