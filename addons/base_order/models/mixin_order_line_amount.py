from collections import defaultdict

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare

_debug = DebugLog(__name__)


class MixinOrderLineAmount(models.AbstractModel):
    _name = "mixin.order.line.amount"
    _description = "Order Line Amount Computation"

    _product_tax_field = ""
    _price_direction = 0

    currency_id = fields.Many2one(comodel_name="res.currency")

    product_qty = fields.Float(
        string="Quantity",
        digits="Product Unit",
        compute="_compute_product_qty",
        precompute=True,
        store=True,
        readonly=False,
    )
    product_uom_qty = fields.Float(
        string="Quantity (Reference UoM)",
        digits="Product Unit",
        compute="_compute_product_uom_qty",
        precompute=True,
        store=True,
    )
    price_unit = fields.Float(
        string="Unit Price",
        min_display_digits="Product Price",
        compute="_compute_price_and_discount",
        precompute=True,
        store=True,
        readonly=False,
        aggregator="avg",
    )
    price_unit_auto = fields.Float(
        string="Automatic Price",
        min_display_digits="Product Price",
        compute="_compute_price_and_discount",
        precompute=True,
        store=True,
        copy=True,
        help="Price from the pricelist/seller. Compared with price_unit to "
        "detect manual overrides.",
    )
    discount = fields.Float(
        string="Discount (%)",
        digits="Discount",
        compute="_compute_price_and_discount",
        precompute=True,
        store=True,
        readonly=False,
    )
    discount_auto = fields.Float(
        string="Automatic Discount",
        digits="Discount",
        compute="_compute_price_and_discount",
        precompute=True,
        store=True,
        copy=True,
        help="Discount from the pricelist/seller. Compared with discount to "
        "detect manual overrides.",
    )
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        context={"active_test": False, "hide_original_tax_ids": True},
        check_company=True,
    )

    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute="_compute_amounts",
        precompute=True,
        store=True,
    )
    price_tax = fields.Monetary(
        string="Total Tax",
        compute="_compute_amounts",
        precompute=True,
        store=True,
    )
    price_total = fields.Monetary(
        string="Total",
        compute="_compute_amounts",
        precompute=True,
        store=True,
    )

    @api.depends("tax_ids", "product_qty", "price_unit", "discount")
    def _compute_amounts(self):
        AccountTax = self.env["account.tax"]
        lines = self.env[self._name]
        for line in self:
            if line.display_type:
                line.price_subtotal = False
                line.price_total = False
                line.price_tax = False
            else:
                lines += line
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

    @api.depends("product_id", "display_type")
    def _compute_product_qty(self):
        for line in self:
            if line.display_type:
                line.product_qty = False
                continue
            # A line with no product (an imported charge, a product the import
            # could not match) has no default to fall back on, so a recompute
            # triggered by its order keeps the quantity it was given.
            if not line.product_id:
                continue
            if not line.product_qty or line._is_product_qty_reset_triggered():
                line.product_qty = line._get_default_product_qty()

    def _is_product_qty_reset_triggered(self):
        return bool(
            self._origin.product_id and self._origin.product_id != self.product_id
        )

    def _get_default_product_qty(self):
        return 1.0

    @api.depends("product_id", "product_id.uom_id", "product_uom_id", "product_qty")
    def _compute_product_uom_qty(self):
        for line in self:
            if line.display_type:
                line.product_uom_qty = False
            elif (
                line.product_uom_id
                and line.product_id
                and line.product_id.uom_id != line.product_uom_id
                and line.product_uom_id._has_common_reference(line.product_id.uom_id)
            ):
                line.product_uom_qty = line.product_uom_id._get_quantity_in_unit(
                    line.product_qty,
                    line.product_id.uom_id,
                )
            else:
                line.product_uom_qty = line.product_qty

    def _check_write_derived_quantity(self, write_vals):
        if "product_uom_qty" not in write_vals:
            return
        _debug.logic("derived_quantity_write_refused", model=self._name)
        raise ValueError(
            f"{self._name}.product_uom_qty is computed from product_qty and "
            f"cannot be written; set product_qty instead.",
        )

    def _get_price_unit_gross(self):
        self.check_singleton()
        price_unit = self.price_unit
        if self.discount:
            price_unit *= 1 - self.discount / 100
        if self.tax_ids:
            qty = self.product_qty or 1
            price_unit = self.tax_ids.compute_all(
                price_unit,
                currency=self.order_id.currency_id,
                quantity=qty,
                rounding_method="round_globally",
            )["total_void"]
            price_unit /= qty
        if self.product_uom_id.id != self.product_id.uom_id.id:
            price_unit = self.product_uom_id._get_price_in_unit(
                price_unit, self.product_id.uom_id
            )
        return price_unit

    @api.depends("product_id", "product_uom_id", "product_qty", "display_type")
    def _compute_price_and_discount(self):
        force_recompute = self.env.context.get("force_price_recomputation")
        origin_shadows = {
            origin.id: (origin.price_unit_auto, origin.discount_auto)
            for origin in self._origin
        }
        for line in self:
            if line.display_type:
                line.price_unit = False
                line.discount = False
                line.price_unit_auto = False
                line.discount_auto = False
                continue
            if not line.product_id:
                continue
            auto_price, auto_discount = line._get_auto_price_and_discount()
            old_price_shadow = line.price_unit_auto
            old_discount_shadow = line.discount_auto
            if not old_price_shadow or not old_discount_shadow:
                saved_price, saved_discount = origin_shadows.get(
                    line._origin.id, (0.0, 0.0)
                )
                old_price_shadow = old_price_shadow or saved_price
                old_discount_shadow = old_discount_shadow or saved_discount
            line.price_unit_auto = auto_price
            line.discount_auto = auto_discount
            if line._is_price_update_required(
                auto_price, old_price_shadow, force_recompute
            ):
                line.price_unit = auto_price
                if line._is_discount_update_required(
                    auto_discount, old_discount_shadow, force_recompute
                ):
                    line.discount = auto_discount

    def _get_auto_price_and_discount(self):
        raise NotImplementedError(
            f"{self._name} must implement _get_auto_price_and_discount()"
        )

    def _is_price_update_required(
        self, new_auto_price, old_auto_price, force_recompute=False
    ):
        self.check_singleton()
        precision = self._get_price_precision()

        if self._is_price_update_blocked():
            _debug.logic("price_update", line=self, update=False, by="blocked")
            return False

        if force_recompute:
            _debug.logic("price_update", line=self, update=True, by="forced")
            return True

        if self._origin.product_id and self._origin.product_id != self.product_id:
            _debug.logic(
                "price_update",
                line=self,
                update=True,
                by="product_changed",
                origin_product=self._origin.product_id,
            )
            return True

        has_baseline = self._origin.id or old_auto_price
        if has_baseline:
            is_manual = (
                float_compare(
                    self.price_unit,
                    old_auto_price,
                    precision_digits=precision,
                )
                != 0
            )
            _debug.logic(
                "price_update",
                line=self,
                update=not is_manual,
                by="baseline",
                manual=is_manual,
                origin_is_self=self._origin.id == self.id,
                price=self.price_unit,
                old_auto=old_auto_price,
            )
            return not is_manual

        _debug.logic(
            "price_update",
            line=self,
            by="no_baseline",
            price=self.price_unit,
            new_auto=new_auto_price,
        )
        return not (
            self.price_unit
            and float_compare(
                self.price_unit,
                new_auto_price,
                precision_digits=precision,
            )
            != 0
        )

    def _is_discount_update_required(
        self, new_auto_discount, old_auto_discount, force_recompute=False
    ):
        self.check_singleton()
        if force_recompute:
            _debug.logic("discount_update", line=self, update=True, by="forced")
            return True
        precision = self.env["decimal.precision"].get_precision("Discount")

        has_baseline = self._origin.id or old_auto_discount
        if has_baseline:
            is_manual = (
                float_compare(
                    self.discount,
                    old_auto_discount,
                    precision_digits=precision,
                )
                != 0
            )
            _debug.logic(
                "discount_update",
                line=self,
                update=not is_manual,
                by="baseline",
                manual=is_manual,
                origin_is_self=self._origin.id == self.id,
            )
            return not is_manual

        return not (
            self.discount
            and float_compare(
                self.discount,
                new_auto_discount,
                precision_digits=precision,
            )
            != 0
        )

    def _is_price_update_blocked(self):
        return False

    def _get_base_line_special_type(self):
        self.check_singleton()
        return "down_payment" if self.is_downpayment else False

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        self.check_singleton()
        company = self.order_id.company_id or self.env.company
        base_values = {
            "tax_ids": self.tax_ids,
            "quantity": self.product_qty,
            "partner_id": self.order_id.partner_id,
            "currency_id": self.order_id.currency_id or company.currency_id,
            "rate": self.order_id.currency_rate,
            "name": self.name,
        }
        special_type = self._get_base_line_special_type()
        if special_type:
            base_values["special_type"] = special_type
        base_values.update(kwargs)
        return self.env["account.tax"]._prepare_base_line_for_taxes_computation(
            self,
            **base_values,
        )

    price_unit_discounted_taxexc = fields.Float(
        string="Unit Price Discounted Tax Excluded",
        min_display_digits="Product Price",
        compute="_compute_price_unit_discounted_taxexc",
    )
    price_unit_discounted_taxinc = fields.Float(
        string="Unit Price Discounted Tax Included",
        min_display_digits="Product Price",
        compute="_compute_price_unit_discounted_taxinc",
    )
    price_unit_product_uom = fields.Float(
        string="Unit Price Product UoM",
        min_display_digits="Product Price",
        compute="_compute_price_unit_product_uom",
        precompute=True,
        store=True,
        help="The price of one unit of the product's own unit of measure. "
        "Comparable across lines that were bought or sold in different units.",
    )
    price_unit_discounted_taxexc_product_uom = fields.Float(
        string="Net Unit Price Product UoM",
        min_display_digits="Product Price",
        compute="_compute_price_unit_discounted_taxexc_product_uom",
        precompute=True,
        store=True,
        help="`price_unit_discounted_taxexc` expressed in the product's own "
        "unit of measure: the discount applied, taxes excluded, units "
        "normalized. The only per-line price that compares across both, which "
        "is why it is stored rather than computed -- price statistics read it "
        "with MIN/MAX in SQL instead of looping over a capped sample.",
    )

    def _get_price_discounted(self):
        self.check_singleton()
        return self.price_unit * (1 - (self.discount or 0.0) / 100.0)

    @api.depends("price_unit", "discount")
    def _compute_price_unit_discounted_taxexc(self):
        for line in self:
            if line.display_type:
                line.price_unit_discounted_taxexc = False
                continue
            line.price_unit_discounted_taxexc = line._get_price_discounted()

    @api.depends("product_qty", "price_total")
    def _compute_price_unit_discounted_taxinc(self):
        for line in self:
            if line.display_type:
                line.price_unit_discounted_taxinc = False
                continue
            line.price_unit_discounted_taxinc = (
                line.price_total / line.product_qty if line.product_qty else 0.0
            )

    @api.depends("product_id.uom_id", "product_uom_id", "price_unit")
    def _compute_price_unit_product_uom(self):
        for line in self:
            if line.display_type or line.is_downpayment:
                line.price_unit_product_uom = False
                continue
            line.price_unit_product_uom = line.product_uom_id._get_price_report(
                line.price_unit,
                line.product_id.uom_id,
            )

    @api.depends("product_qty", "product_uom_qty", "price_subtotal")
    def _compute_price_unit_discounted_taxexc_product_uom(self):
        for line in self:
            if line.display_type or not line.product_uom_qty:
                line.price_unit_discounted_taxexc_product_uom = False
                continue
            line.price_unit_discounted_taxexc_product_uom = (
                line.price_subtotal / line.product_uom_qty
            )

    def _get_product_tax_field(self):
        return self._product_tax_field

    def _get_custom_compute_tax_cache_key(self):
        return ()

    @api.depends("company_id", "product_id", "order_id.fiscal_position_id")
    def _compute_tax_ids(self):
        lines_by_company = defaultdict(lambda: self.env[self._name])
        cached_taxes = {}
        tax_field = self._get_product_tax_field()
        for line in self.filtered(lambda l: not l.display_type):
            if not line.product_id:
                # Nothing to map from: keep the taxes a productless line was given,
                # unless it just lost the product they came from.
                if line._origin.product_id:
                    line.tax_ids = False
                continue
            if not line._is_product_taxable(line):
                line.tax_ids = False
                continue
            lines_by_company[line.company_id] += line

        _debug.perf.count(
            "tax_ids_computed", lines=len(self), companies=len(lines_by_company)
        )
        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = line.product_id[tax_field]._filter_taxes_by_company(
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
                    _debug.logic(
                        "taxes_mapped",
                        line=line,
                        fiscal_position=fiscal_position,
                        taxes=result,
                    )
                line.tax_ids = result

    def _is_product_taxable(self, line):
        return True

    @api.depends(
        "company_id",
        "partner_id",
        "product_id",
        "product_categ_id",
        "order_id.partner_id.tag_ids",
    )
    def _compute_analytic_distribution(self):
        cache = {}
        AnalyticModel = self.env["account.analytic.distribution.model"]

        for line in self.filtered(lambda l: not l.display_type):
            partner = line.order_id.partner_id
            partner_tag_ids = tuple(partner.tag_ids.ids)
            cache_key = (
                line.product_id.id,
                line.product_categ_id.id,
                partner.id,
                partner_tag_ids,
                line.company_id.id,
            )
            if cache_key not in cache:
                cache[cache_key] = AnalyticModel._get_distribution(
                    {
                        "product_id": line.product_id.id,
                        "product_categ_id": line.product_categ_id.id,
                        "partner_id": partner.id,
                        "partner_tag_id": list(partner_tag_ids),
                        "company_id": line.company_id.id,
                    },
                )
            distribution = cache[cache_key]
            line.analytic_distribution = distribution or line.analytic_distribution
            if _debug.logic.enabled and distribution:
                _debug.logic(
                    "analytic_distribution_from_model",
                    line=line,
                    plans=len(distribution),
                )

    def _get_price_precision(self):
        return self.env["decimal.precision"].get_precision("Product Price")

    def is_manual_price(self):
        self.check_singleton()
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

    def _merge_order_line(self, source_line):
        _debug.lifecycle("order_line_merged", target=self, source=source_line)
        self.product_qty += source_line.product_qty
        self.price_unit = min(self.price_unit, source_line.price_unit)
