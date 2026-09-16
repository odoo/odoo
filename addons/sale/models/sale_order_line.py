from collections import defaultdict
from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare, float_is_zero, format_date, groupby
from odoo.tools.translate import _

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = [
        "mixin.order.line.fields",
        "mixin.order.line.amount",
        "mixin.order.line.invoice",
        "mixin.analytic",
    ]
    _description = "Sales Order Line"
    _check_company_auto = True
    _order = "order_id, sequence, id"
    _rec_names_search = ["name", "order_id.name"]

    _order_type = "sale"
    _product_ok_field = "sale_ok"
    _analytic_business_domain = "sale_order"
    _transfer_verb = "delivered"
    _product_tax_field = "taxes_id"
    _invoice_move_direction = "out"
    _invoice_policy_field = "invoice_policy"
    _price_direction = 1

    order_id = fields.Many2one(comodel_name="sale.order")
    partner_id = fields.Many2one(string="Customer")
    user_id = fields.Many2one(string="Salesperson")

    is_downpayment = fields.Boolean(
        help="Down payments are made when creating invoices from a sales order."
        " They are not copied when duplicating a sales order."
    )
    is_expense = fields.Boolean(
        help="Is true if the sales order line comes from an expense or a vendor bills"
    )
    is_optional = fields.Boolean(
        string="Optional Line",
        default=False,
        copy=True,
    )

    parent_id = fields.Many2one(
        comodel_name="sale.order.line",
        help="The section or subsection this line belongs to.",
    )
    collapse_prices = fields.Boolean(
        default=False,
        copy=True,
        help="Whether this section's lines' prices will be hidden in reports and in the portal.",
    )
    collapse_composition = fields.Boolean(
        default=False,
        copy=True,
        help="Whether this section's lines will be hidden in reports and in the portal.",
    )
    linked_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Linked Order Line",
        index=True,
        copy=False,
        domain="[('order_id', '=', order_id)]",
        ondelete="cascade",
    )
    linked_line_ids = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="linked_line_id",
        string="Linked Order Lines",
    )

    service_tracking = fields.Selection(
        related="product_id.service_tracking",
        depends=["product_id"],
    )
    sale_line_warn_msg = fields.Text(
        compute="_compute_sale_line_warn_msg",
        depends_context=("uid",),
    )
    product_template_id = fields.Many2one(
        comodel_name="product.template",
        compute="_compute_product_template_id",
        search="_search_product_template_id",
        readonly=False,
        domain=lambda self: self._fields["product_id"]._description_domain(self.env),
    )
    is_configurable_product = fields.Boolean(
        related="product_template_id.has_configurable_attributes",
        string="Is the product configurable?",
        depends=["product_template_id"],
    )
    product_custom_attribute_value_ids = fields.One2many(
        comodel_name="product.attribute.custom.value",
        inverse_name="sale_order_line_id",
        string="Custom Values",
        compute="_compute_custom_attribute_values",
        precompute=True,
        store=True,
        copy=True,
        readonly=False,
    )
    product_no_variant_attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        string="Extra Values",
        compute="_compute_custom_attribute_values",
        precompute=True,
        store=True,
        readonly=False,
        ondelete="restrict",
    )
    tax_ids = fields.Many2many(
        compute="_compute_tax_ids",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('type_tax_use', '=', 'sale'), ('country_id', '=', tax_country_id)]",
    )
    pricelist_item_id = fields.Many2one(
        comodel_name="product.pricelist.item",
        compute="_compute_pricelist_item_id",
    )
    price_unit_auto = fields.Float(
        string="Automatic Price",
        min_display_digits="Product Price",
        compute="_compute_price_and_discount",
        precompute=True,
        store=True,
        copy=True,
        help="Price from pricelist. Compared with price_unit to detect manual overrides. "
        "When price_unit != price_unit_auto, the price is considered manually set.",
    )
    discount = fields.Float(recursive=True)
    customer_lead = fields.Float(
        string="Lead Time",
        compute="_compute_customer_lead",
        precompute=True,
        store=True,
        readonly=False,
        help="Number of days between the order confirmation and the shipping of the products to the customer",
    )
    virtual_id = fields.Char(
        help="Uniquely identifies this sale order line before "
        "the record is saved in the DB, i.e. before the record has an `id`."
    )
    linked_virtual_id = fields.Char(
        help="Links this sale order line to another sale order line, via its `virtual_id`"
    )

    selected_combo_items = fields.Char(
        store=False,
        help="Local storage of this sale order line's selected combo items, iff this is a combo product line.",
    )
    combo_item_id = fields.Many2one(comodel_name="product.combo.item")

    analytic_line_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="so_line",
        string="Analytic lines",
    )

    qty_transferred_method = fields.Selection(
        string="Delivered Qty Method",
        help="""According to product configuration, the delivered quantity can
        be automatically computed by mechanism:\n
        -Manual: the quantity is set manually on the line\n
        -Analytic From expenses: the quantity is the quantity sum from posted expenses\n
        -Timesheet: the quantity is the sum of hours recorded on tasks linked to this sale line\n
        -Stock Moves: the quantity comes from confirmed pickings\n""",
    )
    qty_transferred = fields.Float(string="Delivered Qty")
    qty_transferred_at_date = fields.Float(string="Delivered")

    invoice_line_ids = fields.Many2many(
        relation="account_move_line_sale_order_line_rel",
        column1="order_line_id",
        column2="move_line_id",
    )
    extra_tax_data = fields.Json()

    product_readonly = fields.Boolean(
        string="Product is readonly",
        compute="_compute_product_readonly",
        help="Indicates whether the product field should be readonly based on order state, "
        "invoiced/delivered quantities, and locked status. "
        "Used in views for readonly attribute to match product_uom_readonly pattern.",
    )
    product_uom_readonly = fields.Boolean(compute="_compute_product_uom_readonly")

    @api.constrains("combo_item_id")
    def _check_combo_item_id(self):
        for line in self:
            linked_line = line._get_line_linked()
            allowed_combo_items = (
                linked_line.product_template_id.combo_ids.combo_item_ids
            )
            if line.combo_item_id and line.combo_item_id not in allowed_combo_items:
                _debug.logic(
                    "combo_item_rejected",
                    line=line,
                    reason="not_in_linked_line_combos",
                    combo_item=line.combo_item_id,
                )
                raise ValidationError(
                    _(
                        "A sale order line's combo item must be among its linked line's available"
                        " combo items.",
                    ),
                )
            if line.combo_item_id and line.combo_item_id.product_id != line.product_id:
                _debug.logic(
                    "combo_item_rejected",
                    line=line,
                    reason="product_mismatch",
                    combo_item=line.combo_item_id,
                )
                raise ValidationError(
                    _(
                        "A sale order line's product must match its combo item's product.",
                    ),
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "price_unit_auto" in vals and "price_unit" not in vals:
                vals.pop("price_unit_auto")
                _debug.logic("price_unit_auto_dropped", stage="create")

        lines = super().create(vals_list)
        _debug.lifecycle("create", lines=lines, rows=len(vals_list))

        for line in lines:
            linked_line = line._get_line_linked()
            if linked_line:
                line.linked_line_id = linked_line
                _debug.lifecycle("line_linked", line=line, linked_to=linked_line)

        return lines

    def write(self, vals):
        _debug.lifecycle("write", lines=self, fields=list(vals))
        if "product_qty" in vals:
            precision = self.env["decimal.precision"].get_precision("Product Unit")
            self.filtered(
                lambda r: (
                    r.state == "done"
                    and float_compare(
                        r.product_qty,
                        vals["product_qty"],
                        precision_digits=precision,
                    )
                    != 0
                ),
            )._update_line_quantity(vals)

        if (
            "price_unit_auto" in vals
            and "price_unit" not in vals
            and not self.env.context.get("sale_write_from_compute")
        ):
            vals.pop("price_unit_auto")
            _debug.logic("price_unit_auto_dropped", stage="write", lines=self)

        return super().write(vals)

    def _add_precomputed_values(self, vals_list):
        original_values = [
            {
                "price_unit": vals.get("price_unit"),
                "price_unit_auto": vals.get("price_unit_auto"),
            }
            for vals in vals_list
        ]

        super()._add_precomputed_values(vals_list)

        for i, vals in enumerate(vals_list):
            orig = original_values[i]
            orig_price = orig["price_unit"]
            orig_auto = orig["price_unit_auto"]

            if orig_price is not None and orig_auto is not None:
                vals["price_unit"] = orig_price
                vals["price_unit_auto"] = orig_auto
                continue

            if orig_price is not None:
                vals["price_unit"] = orig_price
                if vals.get("price_unit_auto") is None:
                    vals["price_unit_auto"] = orig_price
            elif orig_auto is not None:
                vals["price_unit"] = orig_auto
                vals["price_unit_auto"] = orig_auto
            else:
                computed_price = vals.get("price_unit")
                if computed_price is not None:
                    vals["price_unit_auto"] = computed_price
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "precomputed_prices",
                rows=len(vals_list),
                manual=sum(
                    1 for orig in original_values if orig["price_unit"] is not None
                ),
            )

    def _compute_customer_lead(self):
        for line in self.filtered(lambda x: not x.display_type):
            line.customer_lead = 0.0

    @api.depends(
        "sequence",
        "display_type",
        "order_id.line_ids.sequence",
        "order_id.line_ids.display_type",
    )
    def _compute_parent_id(self):
        super()._compute_parent_id()

    @api.depends("order_id", "partner_id", "product_id")
    def _compute_display_name(self):
        name_per_id = self._get_additional_name_per_id()
        for line in self:
            if line.sudo().partner_id.lang:
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
        self._compute_line_warn_msg("sale_line_warn_msg")

    def _get_warning_group(self):
        return "sale.group_warning_sale"

    def _get_product_warn_field(self):
        return "sale_line_warn_msg"

    def _is_product_taxable(self, line):
        return line.product_type != "combo"

    @api.depends("product_id")
    def _compute_custom_attribute_values(self):
        for line in self:
            if not line.product_id:
                line.product_custom_attribute_value_ids = False
                line.product_no_variant_attribute_value_ids = False
                continue

            has_custom = bool(line.product_custom_attribute_value_ids)
            has_no_variant = bool(line.product_no_variant_attribute_value_ids)

            if not has_custom and not has_no_variant:
                continue

            valid_values = line.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids

            if has_custom:
                invalid_custom = line.product_custom_attribute_value_ids.browse()
                for pacv in line.product_custom_attribute_value_ids:
                    if (
                        pacv.custom_product_template_attribute_value_id
                        not in valid_values
                    ):
                        invalid_custom |= pacv
                line.product_custom_attribute_value_ids -= invalid_custom
                if _debug.logic.enabled and invalid_custom:
                    _debug.logic(
                        "attribute_values_dropped",
                        line=line,
                        kind="custom",
                        dropped=invalid_custom,
                    )

            if has_no_variant:
                invalid_no_variant = (
                    line.product_no_variant_attribute_value_ids.browse()
                )
                for ptav in line.product_no_variant_attribute_value_ids:
                    if ptav._origin not in valid_values:
                        invalid_no_variant |= ptav
                line.product_no_variant_attribute_value_ids -= invalid_no_variant
                if _debug.logic.enabled and invalid_no_variant:
                    _debug.logic(
                        "attribute_values_dropped",
                        line=line,
                        kind="no_variant",
                        dropped=invalid_no_variant,
                    )

    @api.depends("product_id")
    def _compute_product_name_translated(self):
        lines_by_order = {}
        for line in self:
            order_id = line.order_id.id
            if order_id not in lines_by_order:
                lines_by_order[order_id] = {
                    "order": line.order_id,
                    "lines": [],
                }
            lines_by_order[order_id]["lines"].append(line)

        for data in lines_by_order.values():
            lang = data["order"]._get_lang()
            for line in data["lines"]:
                line.product_name_translated = line.product_id.with_context(
                    lang=lang,
                ).display_name
        _debug.perf.count(
            "product_names_translated", lines=len(self), orders=len(lines_by_order)
        )

    @api.depends("product_id")
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    @api.depends("product_template_id")
    def _compute_product_qty(self):
        super()._compute_product_qty()
        for line in self:
            if (
                not line.display_type
                and not line.product_id
                and line.product_template_id
                and not line.product_qty
            ):
                line.product_qty = line._get_default_product_qty()

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            if not line.product_uom_id or (
                line.product_id.uom_id.id != line.product_uom_id.id
            ):
                _debug.logic(
                    "uom_realigned",
                    line=line,
                    before=line.product_uom_id,
                    after=line.product_id.uom_id,
                )
                line.product_uom_id = line.product_id.uom_id

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

        for line in self:
            if not (
                line.product_id
                and line.order_id.sale_order_template_id
                and line._use_template_name()
            ):
                continue
            template_lines = (
                line.order_id.sale_order_template_id.sale_order_template_line_ids
            )
            for template_line in template_lines:
                if line.product_id == template_line.product_id and template_line.name:
                    lang = line.order_id.partner_id.lang
                    line.name = (
                        template_line.with_context(lang=lang).name
                        + line.with_context(
                            lang=lang
                        )._get_line_multiline_description_variants()
                    )
                    _debug.logic(
                        "line_name_from_template",
                        line=line,
                        template=line.order_id.sale_order_template_id,
                    )
                    break

    @api.depends("product_id", "product_uom_id", "product_qty")
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
                    product=line.product_id,
                    **line._get_pricelist_kwargs(),
                )
        _debug.perf.count("pricelist_rules_resolved", lines=len(self))

    @api.depends(
        "product_id",
        "product_uom_id",
        "product_qty",
        "display_type",
        "linked_line_id.discount",
    )
    def _compute_price_and_discount(self):
        force_recompute = self.env.context.get("force_price_recomputation")
        discount_enabled = self.env[
            "product.pricelist.item"
        ]._is_discount_feature_enabled()

        origin_price_auto = {
            origin.id: origin.price_unit_auto for origin in self._origin
        }
        origin_discount_auto = {
            origin.id: origin.discount_auto for origin in self._origin
        }

        for line in self:
            if line.display_type:
                line.price_unit = False
                line.discount = False
                continue

            is_special_line = (
                not line.order_id or line.is_downpayment or line._is_global_discount()
            )

            pricelist_price = False
            base_price = False
            is_combo_item = bool(line.combo_item_id)

            if not is_special_line and line.product_id and line.product_uom_id:
                line_with_company = line.with_company(line.company_id)

                if is_combo_item or line.product_type == "combo":
                    display_price = line_with_company._get_price_display()
                else:
                    pricelist_price = line_with_company._get_pricelist_price()
                    if line.pricelist_item_id._is_discount_shown():
                        base_price = (
                            line_with_company._get_pricelist_price_before_discount()
                        )
                    display_price = line_with_company._get_price_display(
                        pricelist_price=pricelist_price, base_price=base_price
                    )

                auto_price = display_price
                if auto_price and line.order_id.fiscal_position_id:
                    product_taxes = line.product_id.taxes_id._filter_taxes_by_company(
                        line.company_id
                    )
                    if product_taxes:
                        auto_price = (
                            line.product_id._get_tax_included_unit_price_from_price(
                                auto_price,
                                product_taxes,
                                fiscal_position=line.order_id.fiscal_position_id,
                            )
                        )

                old_auto_price = line.price_unit_auto
                if not old_auto_price and line._origin.id:
                    old_auto_price = origin_price_auto.get(line._origin.id, 0.0)

                should_update = line._is_price_update_required(
                    auto_price, old_auto_price, force_recompute
                )

                line.price_unit_auto = auto_price

                if should_update:
                    line.price_unit = auto_price

            if not line.product_id:
                line.discount = 0.0
                line.discount_auto = 0.0
                continue

            if not (
                line.order_id.pricelist_id and discount_enabled and line.product_uom_id
            ):
                continue

            if is_combo_item:
                line.discount = line._get_line_linked().discount
                continue

            auto_discount = 0.0
            if line.pricelist_item_id._is_discount_shown():
                if not pricelist_price:
                    line_with_company = line.with_company(line.company_id)
                    pricelist_price = line_with_company._get_pricelist_price()
                    base_price = (
                        line_with_company._get_pricelist_price_before_discount()
                    )

                if base_price and base_price != 0:
                    discount = (base_price - pricelist_price) / base_price * 100
                    if (discount > 0 and base_price > 0) or (
                        discount < 0 and base_price < 0
                    ):
                        auto_discount = discount

            old_auto_discount = line.discount_auto
            if not old_auto_discount and line._origin.id:
                old_auto_discount = origin_discount_auto.get(line._origin.id, 0.0)

            should_update_discount = line._is_discount_update_required(
                auto_discount, old_auto_discount, force_recompute
            )
            line.discount_auto = auto_discount
            if should_update_discount:
                line.discount = auto_discount

    @api.depends(
        "qty_transferred_method",
        "analytic_line_ids.so_line",
        "analytic_line_ids.product_uom_id",
        "analytic_line_ids.unit_amount",
    )
    def _compute_qty_transferred(self):
        lines_by_analytic = self.filtered(
            lambda line: line.qty_transferred_method == "analytic",
        )
        mapping = lines_by_analytic._get_qty_delivered_by_analytic(
            [("amount", "<=", 0.0)],
        )
        _debug.perf.count(
            "qty_transferred_from_analytic",
            lines=len(self),
            analytic=len(lines_by_analytic),
        )
        for line in lines_by_analytic:
            line.qty_transferred = mapping.get(line.id or line._origin.id, 0.0)

    @api.depends(
        "state",
        "product_id",
        "product_id.invoice_policy",
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
        combo_lines = set()
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        discount_precision = self.env["decimal.precision"].get_precision("Discount")
        invoiced_outside_moves = self._get_invoiced_outside_account_moves()
        _debug.perf.count("invoice_amounts", lines=len(self))

        for line in self.filtered(lambda x: not x.display_type):
            qty_to_consider = (
                line.qty_transferred
                if line.product_id.invoice_policy == "transferred"
                else line.product_qty
            )
            qty_invoiced = 0.0
            qty_invoiced_posted = 0.0
            amount_taxexc_invoiced = 0.0
            amount_taxinc_invoiced = 0.0
            has_different_discount = False

            for invoice_line in line._get_open_invoice_lines():
                qty_invoiced -= (
                    invoice_line.move_id.direction_sign
                    * invoice_line.product_uom_id._get_quantity_reconcile(
                        invoice_line.quantity,
                        line.product_uom_id,
                    )
                )

            invoice_lines = line._get_posted_invoice_lines()
            for invoice_line in invoice_lines:
                direction_sign = -invoice_line.move_id.direction_sign
                qty_invoiced_posted += (
                    direction_sign
                    * invoice_line.product_uom_id._get_quantity_reconcile(
                        invoice_line.quantity,
                        line.product_uom_id,
                    )
                )

                amount_taxexc_unsigned = invoice_line.currency_id._convert(
                    invoice_line.price_subtotal,
                    line.currency_id,
                    line.company_id,
                    invoice_line.invoice_date or fields.Date.today(),
                )
                amount_taxexc_invoiced += amount_taxexc_unsigned * direction_sign

                amount_taxinc_unsigned = invoice_line.currency_id._convert(
                    invoice_line.price_total,
                    line.currency_id,
                    line.company_id,
                    invoice_line.invoice_date or fields.Date.today(),
                )
                amount_taxinc_invoiced += amount_taxinc_unsigned * direction_sign

                if not has_different_discount and float_compare(
                    invoice_line.discount,
                    line.discount,
                    precision_digits=discount_precision,
                ):
                    has_different_discount = True

            outside_qty, outside_amount_taxexc = invoiced_outside_moves.get(
                line, (0.0, 0.0)
            )
            qty_invoiced += outside_qty
            amount_taxexc_invoiced += outside_amount_taxexc

            line.qty_invoiced = qty_invoiced
            line.amount_taxexc_invoiced = amount_taxexc_invoiced
            line.amount_taxinc_invoiced = amount_taxinc_invoiced

            if line.state in ("draft", "cancel"):
                line.amount_taxexc_to_invoice = 0.0
                line.amount_taxinc_to_invoice = 0.0
                line.qty_to_invoice = 0.0
                continue

            price_unit_discounted = line.price_unit_discounted_taxexc
            raw_subtotal = price_unit_discounted * qty_to_consider
            price_subtotal = (
                line.currency_id.round(raw_subtotal)
                if line.currency_id
                else raw_subtotal
            )

            if any(tax.price_include for tax in line.tax_ids):
                price_subtotal = line.tax_ids.compute_all(
                    price_unit_discounted,
                    currency=line.currency_id,
                    quantity=qty_to_consider,
                    product=line.product_id,
                    partner=line.order_id.partner_shipping_id,
                )["total_excluded"]

            if has_different_discount:
                amount = 0
                for invoice_line in invoice_lines:
                    converted_price = invoice_line.currency_id._convert(
                        invoice_line.price_unit,
                        line.currency_id,
                        line.company_id,
                        invoice_line.date or fields.Date.today(),
                        round=False,
                    )

                    if any(tax.price_include for tax in invoice_line.tax_ids):
                        amount += invoice_line.tax_ids.compute_all(
                            converted_price * invoice_line.quantity,
                        )["total_excluded"]
                    else:
                        amount += converted_price * invoice_line.quantity

                amount_to_invoice = price_subtotal - amount - outside_amount_taxexc
            else:
                amount_to_invoice = price_subtotal - amount_taxexc_invoiced

            if line.is_downpayment:
                line.amount_taxexc_to_invoice = amount_to_invoice
            else:
                line.amount_taxexc_to_invoice = max(amount_to_invoice, 0.0)

            unit_price_total = (
                0.0
                if float_is_zero(line.product_qty, precision_digits=precision)
                else line.price_total / line.product_qty
            )
            line.amount_taxinc_to_invoice = unit_price_total * (
                qty_to_consider - qty_invoiced_posted
            )

            if line.product_type == "combo":
                combo_lines.add(line)
            else:
                line.qty_to_invoice = qty_to_consider - line.qty_invoiced

            if line.combo_item_id and line.linked_line_id:
                combo_lines.add(line.linked_line_id)

        for combo_line in combo_lines:
            if any(
                line.combo_item_id and line.qty_to_invoice
                for line in combo_line.linked_line_ids
            ):
                combo_line.qty_to_invoice = (
                    combo_line.product_qty - combo_line.qty_invoiced
                )
            else:
                combo_line.qty_to_invoice = 0.0

    @api.depends(
        "qty_invoiced",
        "qty_to_invoice",
        "amount_taxexc_to_invoice",
    )
    def _compute_invoice_state(self):
        return super()._compute_invoice_state()

    @api.depends(
        "state",
        "product_id",
        "qty_invoiced",
        "qty_transferred",
        "is_downpayment",
        "order_id.locked",
    )
    def _compute_product_readonly(self):
        self.product_readonly = False
        for line in self.filtered(lambda l: not l.display_type):
            if (
                line.is_downpayment
                or line.state == "cancel"
                or (
                    line.state == "done"
                    and (
                        line.order_id.locked
                        or line.qty_invoiced > 0
                        or line.qty_transferred > 0
                    )
                )
            ):
                line.product_readonly = True

    @api.depends("state")
    def _compute_product_uom_readonly(self):
        self.product_uom_readonly = False
        for line in self.filtered(lambda l: not l.display_type):
            line.product_uom_readonly = line.ids and line.state in ["done", "cancel"]

    def _search_product_template_id(self, operator, value):
        return [("product_id.product_tmpl_id", operator, value)]

    def _get_catalog_single_line_data(self, **kwargs):
        return {
            "quantity": self.product_qty,
            "price": self._get_price_discounted(),
            "readOnly": (self.order_id._is_readonly() or bool(self.combo_item_id)),
            "uomDisplayName": self.product_uom_id.display_name,
        }

    def _get_catalog_multi_line_data(self, **kwargs):
        order = self.order_id
        return {
            "price": order.pricelist_id._get_product_price(
                product=self.product_id,
                quantity=1.0,
                currency=order.currency_id,
                date=order.date_order,
                **kwargs,
            ),
            "uomDisplayName": self.product_id.uom_id.display_name,
        }

    def _get_additional_name_per_id(self):
        return {line.id: line._get_partner_display() for line in self}

    def compute_uom_qty(self, new_qty, stock_move, rounding=True):
        return self.product_uom_id._get_quantity_in_unit(
            new_qty,
            stock_move.product_uom_id,
            rounding,
        )

    def _convert_to_sol_currency(self, amount, currency):
        self.check_singleton()
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

    def _get_combo_totals(self, totals_field):
        self.check_singleton()
        combo_item_lines = self.order_id.line_ids.filtered(
            lambda line: line.linked_line_id == self and line.combo_item_id,
        )
        return sum(combo_item_lines.mapped(totals_field))

    def _get_date_order(self):
        self.check_singleton()
        return self.order_id.date_order

    def _get_date_planned(self):
        self.check_singleton()
        if self.state == "done" and self.order_id.date_order:
            order_date = self.order_id.date_order
        else:
            order_date = fields.Datetime.now()
        return order_date + timedelta(days=self.customer_lead or 0.0)

    def _get_downpayment_description(self):
        self.check_singleton()

        if self.display_type:
            return _("Down Payments")

        dp_state = self._get_downpayment_state()
        _debug.logic("downpayment_description", line=self, state=dp_state or "invoiced")
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
            if l.move_id.state == "posted" and l.move_id not in invoices
        )

    def _get_downpayment_state(self):
        self.check_singleton()

        if self.display_type:
            return ""

        invoice_lines = self._get_invoice_lines()
        _debug.perf.count(
            "downpayment_state", line=self, invoice_lines=len(invoice_lines)
        )
        if all(line.parent_state == "draft" for line in invoice_lines):
            return "draft"
        if all(line.parent_state == "cancel" for line in invoice_lines):
            return "cancel"

        return ""

    def _get_grouped_section_summary(self, display_taxes=True):
        self.check_singleton()

        section_lines = self.order_id.line_ids.filtered(
            lambda line: line.product_type != "combo" and self._is_line_in_section(line)
        )

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
        return new or old

    def _get_line_linked(self):
        self.check_singleton()
        return (
            self.linked_line_id
            or (
                self.linked_virtual_id
                and self.order_id.line_ids.filtered(
                    lambda line: line.virtual_id == self.linked_virtual_id,
                )[:1]
            )
            or self.env["sale.order.line"]
        )

    def _get_line_multiline_description_sale(self):
        self.check_singleton()
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
        no_variant_ptavs = self.product_no_variant_attribute_value_ids._origin.filtered(
            lambda ptav: (
                ptav.display_type == "multi" or ptav.attribute_line_id.value_count > 1
            ),
        )
        if not self.product_custom_attribute_value_ids and not no_variant_ptavs:
            return ""

        name = ""

        custom_ptavs = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id
        multi_ptavs = no_variant_ptavs.filtered(
            lambda ptav: ptav.display_type == "multi",
        ).sorted()

        for ptav in no_variant_ptavs - multi_ptavs - custom_ptavs:
            name += "\n" + ptav.display_name

        for pta, ptavs in groupby(multi_ptavs, lambda ptav: ptav.attribute_id):
            name += "\n" + _(
                "%(attribute)s: %(values)s",
                attribute=pta.name,
                values=", ".join(ptav.name for ptav in ptavs),
            )

        sorted_custom_ptav = self.product_custom_attribute_value_ids.custom_product_template_attribute_value_id.sorted()
        for patv in sorted_custom_ptav:
            pacv = self.product_custom_attribute_value_ids.filtered(
                lambda pcav, patv=patv: (
                    pcav.custom_product_template_attribute_value_id == patv
                ),
            )
            name += "\n" + pacv.display_name

        return name

    def _get_lines_linked(self):
        self.check_singleton()
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

    def _get_domain_lines_sellable(self):
        discount_products_ids = self.env.companies.sale_discount_product_id.ids
        domain = Domain("is_downpayment", "=", False)
        if discount_products_ids:
            domain &= Domain("product_id", "not in", discount_products_ids)
        return domain

    def _get_lines_with_price(self):
        if self.product_type == "combo":
            return self.linked_line_ids.filtered("combo_item_id")
        return self

    def _get_partner_display(self):
        self.check_singleton()
        commercial_partner = self.sudo().partner_id.commercial_partner_id
        return f"({commercial_partner.ref or commercial_partner.name})"

    def _get_price_display(self, pricelist_price=None, base_price=None):
        self.check_singleton()

        if self.product_type == "combo":
            _debug.logic("price_display", line=self, by="combo_parent")
            return 0
        if self.combo_item_id:
            _debug.logic("price_display", line=self, by="combo_item")
            return self._get_price_display_combo_item()
        _debug.logic("price_display", line=self, by="regular")
        return self._get_price_display_regular_item(
            pricelist_price=pricelist_price, base_price=base_price
        )

    def _get_price_display_combo_item(self):
        self.check_singleton()

        combo_line = self._get_line_linked()
        if not combo_line:
            _debug.logic("combo_item_price", line=self, by="no_linked_line")
            return 0.0
        combo_product_price = combo_line._get_price_display_regular_item()
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
        if total_combo_base_price:
            combo_prices = {
                combo_id: self.currency_id.round(
                    base_price * combo_product_price / total_combo_base_price,
                )
                for (combo_id, base_price) in combo_base_prices.items()
            }
        else:
            even_share = self.currency_id.round(
                combo_product_price / len(combo_base_prices)
            )
            combo_prices = dict.fromkeys(combo_base_prices, even_share)
            _debug.logic(
                "combo_item_price",
                line=self,
                by="even_share",
                combos=len(combo_base_prices),
            )
        combo_price_delta = combo_product_price - sum(combo_prices.values())
        if _debug.logic.enabled and combo_price_delta:
            _debug.logic("combo_rounding_delta", line=self, delta=combo_price_delta)
        if combo_price_delta:
            combo_prices[combo_line.product_template_id.sudo().combo_ids[-1]] += (
                combo_price_delta
            )
        extra_price = self.combo_item_id.currency_id._convert(
            from_amount=self.combo_item_id.extra_price
            + self.product_id._get_no_variant_attributes_price_extra(
                self.product_no_variant_attribute_value_ids,
            ),
            to_currency=self.currency_id,
            company=self.company_id,
            date=self.order_id.date_order,
        )
        return combo_prices[self.combo_item_id.combo_id] + extra_price

    def _get_price_display_regular_item(self, pricelist_price=None, base_price=None):
        self.check_singleton()

        if pricelist_price is None:
            pricelist_price = self._get_pricelist_price()

        if not self.pricelist_item_id._is_discount_shown():
            _debug.logic("regular_item_price", line=self, by="pricelist_price")
            return pricelist_price

        if base_price is None:
            base_price = self._get_pricelist_price_before_discount()

        _debug.logic(
            "regular_item_price",
            line=self,
            by="max_of_base_and_pricelist",
            base=base_price,
            pricelist=pricelist_price,
        )
        return max(base_price, pricelist_price)

    def _get_pricelist_kwargs(self):
        return {
            "quantity": self.product_qty or 1.0,
            "uom": self.product_uom_id,
            "date": self._get_date_order(),
            "currency": self.currency_id,
        }

    def _get_pricelist_price(self):
        self.check_singleton()
        self.product_id.check_singleton()
        _debug.perf.count("pricelist_price", line=self, rule=self.pricelist_item_id)
        return self.pricelist_item_id._get_price(
            product=self.product_id.with_context(
                **self._prepare_product_price_context()
            ),
            **self._get_pricelist_kwargs(),
        )

    def _get_pricelist_price_before_discount(self):
        self.check_singleton()
        self.product_id.check_singleton()

        _debug.perf.count(
            "pricelist_price_before_discount", line=self, rule=self.pricelist_item_id
        )
        return self.pricelist_item_id._get_price_before_discount(
            product=self.product_id.with_context(
                **self._prepare_product_price_context()
            ),
            **self._get_pricelist_kwargs(),
        )

    def _get_pricelist_price_context(self):
        self.check_singleton()
        return {
            "pricelist": self.order_id.pricelist_id.id,
            "uom": self.product_uom_id.id,
            "quantity": self.product_qty,
            "date": self._get_date_order(),
        }

    def get_pricelist_price_current(self):
        self.check_singleton()
        if not self.product_id or not self.product_uom_id:
            return False

        line = self.with_company(self.company_id)
        _debug.logic("pricelist_price_current", line=self)
        return line._get_price_display()

    def _prepare_product_price_context(self):
        self.check_singleton()
        return self.product_id._prepare_product_price_context(
            self.product_no_variant_attribute_value_ids,
        )

    def _get_qty_delivered_by_analytic(self, additional_domain):
        result = defaultdict(float)

        if not self:
            return result

        domain = Domain.AND([[("so_line", "in", self.ids)], additional_domain])
        with _debug.perf("qty_delivered_by_analytic", cr=self.env.cr, lines=self):
            data = self.env["account.analytic.line"]._read_group(
                domain,
                ["product_uom_id", "so_line"],
                ["unit_amount:sum", "move_line_id:count_distinct", "__count"],
            )

        for uom, line, unit_amount_sum, move_line_id_count_distinct, count in data:
            if not uom:
                continue
            if move_line_id_count_distinct == 1 and count > 1:
                qty = unit_amount_sum / count
            else:
                qty = unit_amount_sum
            qty = uom._get_quantity_reconcile(
                qty,
                line.product_uom_id,
                rounding_method="HALF-UP",
            )
            result[line.id] += qty

        _debug.perf.count(
            "qty_delivered_by_analytic_rows", groups=len(data), lines=len(result)
        )
        return result

    def _get_section_lines(self):
        self.check_singleton()
        return self.order_id.line_ids.filtered(self._is_line_in_section)

    def _get_section_totals(self, totals_field):
        self.check_singleton()
        section_lines = self._get_section_lines()
        return sum(section_lines.mapped(totals_field))

    def _is_invoiced_on_transferred(self):
        return self.product_id.invoice_policy == "transferred"

    def _is_upsell_opportunity(self):
        self.check_singleton()
        if self._is_invoiced_on_transferred() or self.product_qty <= 0:
            return False
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        return (
            float_compare(
                self.qty_transferred, self.product_qty, precision_digits=precision
            )
            > 0
        )

    def _prepare_aml_vals(self, **optional_values):
        self.check_singleton()
        move = optional_values.pop("move", None)

        if self.product_id.type == "combo":
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
        if move:
            res["quantity"] = (
                -self.qty_to_invoice
                if move.move_type == "out_refund"
                else self.qty_to_invoice
            )
            res["price_unit"] = self.currency_id._convert(
                self.price_unit,
                move.currency_id or self.currency_id,
                self.company_id,
                move.date or fields.Date.today(),
                round=False,
            )
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res["account_id"] = False
        return res

    def _get_base_line_special_type(self):
        self.check_singleton()
        if self._is_global_discount():
            return "global_discount"
        return super()._get_base_line_special_type()

    def _prepare_procurement_vals(self):
        return {}

    def _get_invoiced_outside_account_moves(self):
        return {}

    def _prepare_qty_invoiced(self):
        invoiced_qties = defaultdict(float)
        for line in self:
            for invoice_line in line._get_invoice_lines():
                if (
                    invoice_line.move_id.state != "cancel"
                    or invoice_line.move_id.payment_state == "invoicing_legacy"
                ):
                    invoice_qty = invoice_line.product_uom_id._get_quantity_in_unit(
                        invoice_line.quantity, line.product_uom_id, round=False
                    )
                    if invoice_line.move_id.move_type == "out_invoice":
                        invoiced_qties[line] += invoice_qty
                    elif invoice_line.move_id.move_type == "out_refund":
                        invoiced_qties[line] -= invoice_qty
        return invoiced_qties

    def _reset_price_unit(self):
        self.check_singleton()

        price_unit = self.get_pricelist_price_current()

        if price_unit and self.product_id and self.order_id.fiscal_position_id:
            product_taxes = self.product_id.taxes_id._filter_taxes_by_company(
                self.company_id
            )
            if product_taxes:
                price_unit = self.product_id._get_tax_included_unit_price_from_price(
                    price_unit,
                    product_taxes,
                    fiscal_position=self.order_id.fiscal_position_id,
                )

        _debug.lifecycle("price_unit_reset", line=self, price=price_unit)
        self.update(
            {
                "price_unit": price_unit,
                "price_unit_auto": price_unit,
            },
        )

    def _prepare_qty_transferred(self):
        delivered_qties = defaultdict(float)
        lines_by_analytic = self.filtered(
            lambda sol: sol.qty_transferred_method == "analytic"
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
        for line in self:
            if line.qty_invoiced > 0:
                _debug.logic(
                    "manual_price_refused", line=line, reason="already_invoiced"
                )
                raise UserError(
                    _("Cannot set manual price on invoiced line %s", line.display_name),
                )

            _debug.lifecycle("manual_price_set", line=line, price=price)
            line.write({"price_unit": price})

    def reset_to_pricelist_price(self):
        for line in self:
            if line.qty_invoiced > 0:
                _debug.logic(
                    "price_reset_refused", line=line, reason="already_invoiced"
                )
                raise UserError(
                    _("Cannot reset price on invoiced line %s", line.display_name),
                )

        _debug.lifecycle("price_reset_to_pricelist", lines=self)
        return self.with_context(
            force_price_recomputation=True
        )._compute_price_and_discount()

    def _set_analytic_distribution(self, inv_line_vals, **optional_values):
        if self.analytic_distribution and not self.display_type:
            inv_line_vals["analytic_distribution"] = self.analytic_distribution

    def _update_line_quantity(self, values):
        orders = self.mapped("order_id")
        for order in orders:
            order_lines = self.filtered(lambda x, order=order: x.order_id == order)
            msg = Markup("<b>%s</b><ul>") % _("The ordered quantity has been updated.")
            for line in order_lines:
                if (
                    "product_id" in values
                    and values["product_id"] != line.product_id.id
                ):
                    continue
                msg += Markup("<li> %s: <br/>") % line.product_id.display_name
                msg += _(
                    "Ordered Quantity: %(old_qty)s -> %(new_qty)s",
                    old_qty=line.product_qty,
                    new_qty=values["product_qty"],
                ) + Markup("<br/>")
                if line.product_id.type == "consu":
                    msg += _("Delivered Quantity: %s", line.qty_transferred) + Markup(
                        "<br/>",
                    )
                msg += _("Invoiced Quantity: %s", line.qty_invoiced) + Markup("<br/>")
            msg += Markup("</ul>")
            _debug.lifecycle(
                "ordered_quantity_updated",
                order=order,
                lines=order_lines,
                new_qty=values.get("product_qty"),
            )
            order.message_post(body=msg)

    def _update_price_unit(self):
        self.check_singleton()
        self = self.with_context(sale_write_from_compute=True)
        self._reset_price_unit()

    def _can_be_edited_on_portal(self):
        self.check_singleton()
        return (
            self.order_id._can_be_edited_on_portal()
            and not self.combo_item_id
            and self.product_id != self.company_id.sale_discount_product_id
            and self._is_line_optional()
        )

    def _use_template_name(self):
        self.check_singleton()
        return True

    def _is_line_optional(self):
        self.check_singleton()
        return self.parent_id.is_optional or (
            self.parent_id.display_type == "line_subsection"
            and self.parent_id.parent_id.is_optional
        )

    def _can_be_invoiced_alone(self):
        self.check_singleton()
        return self.product_id.id != self.company_id.sale_discount_product_id.id

    def _has_taxes(self):
        self.check_singleton()
        return bool(
            self.tax_ids
            or (
                self.display_type
                and any(line._has_taxes() for line in self._get_section_lines())
            ),
        )

    def has_valued_move_ids(self):
        return None

    def _is_delivery(self):
        self.check_singleton()
        return False

    def _is_discount_line(self):
        self.check_singleton()
        return self.product_id in self.company_id.sale_discount_product_id

    def _is_global_discount(self):
        self.check_singleton()
        return self.extra_tax_data and self.extra_tax_data.get(
            "computation_key",
            "",
        ).startswith("global_discount,")

    def _is_line_in_section(self, line):
        self.check_singleton()
        is_direct_child = line.parent_id == self and not line.display_type
        is_indirect_child = (
            self.display_type == "line_section"
            and line.parent_id
            and line.parent_id.display_type == "line_subsection"
            and line.parent_id.parent_id == self
        )
        return is_direct_child or is_indirect_child

    def _is_price_update_blocked(self):
        if any(aml.move_id.state != "cancel" for aml in self.invoice_line_ids):
            _debug.logic("price_update_blocked", line=self, reason="invoiced")
            return True
        if self.product_id.expense_policy == "cost" and self.is_expense:
            _debug.logic("price_update_blocked", line=self, reason="expense_at_cost")
            return True
        return super()._is_price_update_blocked()

    def _filtered_to_check_analytic_distribution(self):
        return self.filtered(
            lambda line: not line.display_type and line.state == "draft",
        )

    def _get_check_write_guards(self):
        return super()._get_check_write_guards() + [
            "_check_write_product_and_uom",
        ]

    def _is_display_type_change_allowed(self, line, new_type):
        return line.display_type == "line_subsection" and new_type == "line_section"

    def _check_write_product_and_uom(self, write_vals):
        if "product_id" in write_vals:
            lines_blocked = self.filtered(
                lambda l: (
                    l.product_id.id != write_vals.get("product_id")
                    and l.product_readonly
                ),
            )
            if lines_blocked:
                _debug.logic(
                    "field_change_blocked", lines=lines_blocked, field="product_id"
                )
                self._raise_field_change_error(lines_blocked, "product")

        if "product_uom_id" in write_vals:
            lines_blocked = self.filtered(
                lambda l: (
                    l.product_uom_id.id != write_vals.get("product_uom_id")
                    and l.product_uom_readonly
                ),
            )
            if lines_blocked:
                _debug.logic(
                    "field_change_blocked", lines=lines_blocked, field="product_uom_id"
                )
                self._raise_field_change_error(
                    lines_blocked,
                    "unit of measure",
                    "because it is in a confirmed state",
                )

    def _raise_field_change_error(self, lines, field_description, reason=""):
        reason_text = f" {reason}" if reason else ""

        if len(lines) == 1:
            line = lines[0]
            line_id = self._get_line_identifier(line)
            raise UserError(
                _(
                    "You cannot change the %(field)s of order line '%(line)s'%(reason)s.",
                    field=field_description,
                    line=line_id,
                    reason=reason_text,
                ),
            )
        line_ids = [self._get_line_identifier(l) for l in lines[:5]]
        error_msg = ", ".join(line_ids)
        if len(lines) > 5:
            error_msg += _(" and %s more", len(lines) - 5)

        raise UserError(
            _(
                "You cannot change the %(field)s of %(count)s order lines (%(lines)s)%(reason)s.",
                field=field_description,
                count=len(lines),
                lines=error_msg,
                reason=reason_text,
            ),
        )
