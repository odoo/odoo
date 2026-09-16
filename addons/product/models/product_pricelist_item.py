from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round, format_amount, format_datetime, formatLang


class ProductPricelistItem(models.Model):
    _name = "product.pricelist.item"
    _description = "Pricelist Rule"
    _order = "applied_on, min_quantity desc, categ_id desc, id desc"
    _check_company_auto = True

    _TARGETING_FIELDS = ("product_id", "product_tmpl_id", "categ_id")

    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        default=lambda self: self._default_pricelist_id(),
        index=True,
        required=False,
        ondelete="cascade",
    )
    is_pricelist_required = fields.Boolean(compute="_compute_is_pricelist_required")
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        store=True,
    )
    date_start = fields.Datetime(
        string="Start Date",
        help="Starting datetime for the pricelist item validation\n"
        "The displayed value depends on the timezone set in your preferences.",
    )
    date_end = fields.Datetime(
        string="End Date",
        help="Ending datetime for the pricelist item validation\n"
        "The displayed value depends on the timezone set in your preferences.",
    )
    min_quantity = fields.Float(
        string="Min. Quantity",
        digits="Product Unit",
        default=0,
        help="For the rule to apply, bought/sold quantity must be greater "
        "than or equal to the minimum quantity specified in this field.\n"
        "Expressed in the default unit of measure of the product.",
    )

    applied_on = fields.Selection(
        selection=[
            ("3_global", "All Products"),
            ("2_product_category", "Product Category"),
            ("1_product", "Product"),
            ("0_product_variant", "Product Variant"),
        ],
        string="Apply On",
        default="3_global",
        required=True,
        help="Pricelist Item applicable on selected option",
    )

    display_applied_on = fields.Selection(
        selection=[
            ("1_product", "Product"),
            ("2_product_category", "Category"),
        ],
        default="1_product",
        required=True,
        help="Pricelist Item applicable on selected option",
    )

    categ_id = fields.Many2one(
        comodel_name="product.category",
        string="Category",
        ondelete="cascade",
        check_company=True,
        help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.",
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        index="btree_not_null",
        ondelete="cascade",
        check_company=True,
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.",
    )
    product_uom_name = fields.Char(related="product_tmpl_id.uom_name")
    product_variant_count = fields.Integer(
        related="product_tmpl_id.product_variant_count"
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Variant",
        index="btree_not_null",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        ondelete="cascade",
        check_company=True,
        help="Specify a product if this rule only applies to one product. Keep empty otherwise.",
    )

    base = fields.Selection(
        selection=[
            ("list_price", "Sales Price"),
            ("standard_price", "Cost"),
            ("pricelist", "Other Pricelist"),
        ],
        string="Based on",
        default="list_price",
        required=True,
        help="Base price for computation.\n"
        "Sales Price: The base price will be the Sales Price.\n"
        "Cost Price: The base price will be the cost price.\n"
        "Other Pricelist: Computation of the base price based on another Pricelist.",
    )
    base_pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Other Pricelist",
        check_company=True,
    )

    compute_price = fields.Selection(
        selection=[
            ("percentage", "Discount"),
            ("formula", "Formula"),
            ("fixed", "Fixed Price"),
        ],
        default="fixed",
        index=True,
        required=True,
        help="Use the discount rules and activate the discount settings in order to show discount to customer.",
    )

    fixed_price = fields.Float(min_display_digits="Product Price")
    percent_price = fields.Float(
        string="Percentage Price",
        help="You can apply a mark-up by setting a negative discount.",
    )

    price_discount = fields.Float(
        digits=(16, 2),
        default=0,
        help="You can apply a mark-up by setting a negative discount.",
    )
    price_round = fields.Float(
        string="Price Rounding",
        min_display_digits="Product Price",
        help="Sets the price so that it is a multiple of this value.\n"
        "Rounding is applied after the discount and before the surcharge.\n"
        "To have prices that end in 9.99, round off to 10.00 and set an extra at -0.01",
    )
    price_surcharge = fields.Float(
        string="Extra Fee",
        min_display_digits="Product Price",
        help="Specify the fixed amount to add or subtract (if negative) to the amount calculated with the discount.",
    )

    price_markup = fields.Float(
        string="Markup",
        digits=(16, 2),
        compute="_compute_price_markup",
        inverse="_inverse_price_markup",
        help="You can apply a mark-up on the cost",
    )

    price_min_margin = fields.Float(
        string="Min. Price Margin",
        min_display_digits="Product Price",
        help="Specify the minimum amount of margin over the base price.",
    )
    price_max_margin = fields.Float(
        string="Max. Price Margin",
        min_display_digits="Product Price",
        help="Specify the maximum amount of margin over the base price.",
    )

    name = fields.Char(
        compute="_compute_name",
        help="Explicit rule name for this pricelist line.",
    )
    price = fields.Char(
        compute="_compute_price",
        help="Human-readable summary of the price this rule computes.",
    )
    rule_tip = fields.Char(compute="_compute_rule_tip")

    @api.constrains("base_pricelist_id", "pricelist_id", "base")
    def _check_pricelist_recursion(self):
        def dfs_path(from_pl, to_pl, path, seen):
            if (from_pl, to_pl) in seen:
                return path.browse()
            if to_pl in path:
                return path + to_pl
            seen.add((from_pl, to_pl))
            target_pricelists = self.env["product.pricelist.item"]._read_group(
                domain=[("pricelist_id", "=", to_pl.id), ("base", "=", "pricelist")],
                groupby=["base_pricelist_id"],
            )
            new_path = path + to_pl
            for (pricelist,) in target_pricelists:
                if pricelist and (res := dfs_path(to_pl, pricelist, new_path, seen)):
                    return res
            return path.browse()

        seen = set()
        for item in self:
            if (
                item.base != "pricelist"
                or not item.base_pricelist_id
                or not item.pricelist_id
            ):
                continue
            if path := dfs_path(
                item.pricelist_id, item.base_pricelist_id, item.pricelist_id, seen
            ):
                raise ValidationError(
                    _(
                        "Recursive pricelist rules detected: %s",
                        " ⇒ ".join(path.mapped("name")),
                    ),
                )

    @api.constrains("date_start", "date_end")
    def _check_date_range(self):
        for item in self:
            if item.date_start and item.date_end and item.date_start >= item.date_end:
                raise ValidationError(
                    _(
                        "%(item_name)s: end date (%(end_date)s) should be after start date (%(start_date)s)",
                        item_name=item.display_name,
                        end_date=format_datetime(self.env, item.date_end),
                        start_date=format_datetime(self.env, item.date_start),
                    ),
                )

    @api.constrains("price_min_margin", "price_max_margin")
    def _check_margin(self):
        for item in self:
            if item.price_max_margin and item.price_min_margin > item.price_max_margin:
                raise ValidationError(
                    _(
                        "%(rule)s: the minimum margin (%(min)s) must be lower than"
                        " the maximum margin (%(max)s).",
                        rule=item.display_name,
                        min=item.price_min_margin,
                        max=item.price_max_margin,
                    ),
                )

    @api.constrains("product_id", "product_tmpl_id")
    def _check_product_variant_consistency(self):
        for item in self:
            if (
                item.product_id
                and item.product_tmpl_id
                and item.product_id.product_tmpl_id != item.product_tmpl_id
            ):
                raise ValidationError(
                    _(
                        "The product variant %(variant)s does not belong to the"
                        " product %(product)s.",
                        variant=item.product_id.display_name,
                        product=item.product_tmpl_id.display_name,
                    ),
                )

    @api.constrains("product_id", "product_tmpl_id", "categ_id")
    def _check_product_consistency(self):
        for item in self:
            if item.applied_on == "2_product_category" and not item.categ_id:
                raise ValidationError(
                    _(
                        "Please specify the category for which this rule should be applied"
                    ),
                )
            if item.applied_on == "1_product" and not item.product_tmpl_id:
                raise ValidationError(
                    _(
                        "Please specify the product for which this rule should be applied"
                    ),
                )
            if item.applied_on == "0_product_variant" and not item.product_id:
                raise ValidationError(
                    _(
                        "Please specify the product variant for which this rule should be applied"
                    ),
                )

    @api.constrains("base_pricelist_id", "base")
    def _check_base_pricelist_id(self):
        if any(
            item.base == "pricelist" and not item.base_pricelist_id for item in self
        ):
            raise ValidationError(
                _(
                    'A pricelist item with "Other Pricelist" as base must have a base_pricelist_id.'
                ),
            )

    @api.constrains("price_round")
    def _check_price_round(self):
        for item in self:
            if item.price_round and item.price_round < 0:
                raise ValidationError(
                    _(
                        "%(rule)s: the price rounding cannot be negative.",
                        rule=item.display_name,
                    ),
                )

    @api.model_create_multi
    def create(self, vals_list):
        missing_tmpl_ids = [
            vals["product_id"]
            for vals in vals_list
            if vals.get("product_id") and not vals.get("product_tmpl_id")
        ]
        tmpl_by_variant = {
            variant.id: variant.product_tmpl_id.id
            for variant in self.env["product.product"].browse(missing_tmpl_ids)
        }

        new_vals_list = []
        for vals in vals_list:
            values = dict(vals)
            if values.get("product_id") and not values.get("product_tmpl_id"):
                values["product_tmpl_id"] = tmpl_by_variant.get(values["product_id"])

            if not values.get("applied_on"):
                values["applied_on"] = self._deduce_applied_on(
                    **{field: values.get(field) for field in self._TARGETING_FIELDS}
                )

            self._update_applied_on_vals(values)
            new_vals_list.append(values)
        return super().create(new_vals_list)

    def write(self, vals):
        if vals.get("applied_on"):
            vals = dict(vals)
            self._update_applied_on_vals(vals)
            return super().write(vals)

        if not any(field in vals for field in self._TARGETING_FIELDS):
            return super().write(vals)

        writes = {}
        for item in self:
            applied_on, template_id = item._targeting_after_write(vals)
            override = (
                None
                if "product_tmpl_id" in vals or template_id == item.product_tmpl_id.id
                else template_id
            )
            writes.setdefault((applied_on, override), []).append(item.id)

        result = True
        for (applied_on, override), item_ids in writes.items():
            item_vals = {**vals, "applied_on": applied_on}
            if override is not None:
                item_vals["product_tmpl_id"] = override
            self._update_applied_on_vals(item_vals)
            result = (
                super(ProductPricelistItem, self.browse(item_ids)).write(item_vals)
                and result
            )
        return result

    def _targeting_after_write(self, vals):
        self.check_singleton()
        product = (
            self.env["product.product"].browse(vals["product_id"])
            if "product_id" in vals
            else self.product_id
        )
        if "product_tmpl_id" in vals:
            template_id = vals["product_tmpl_id"]
        elif product:
            template_id = product.product_tmpl_id.id
        else:
            template_id = self.product_tmpl_id.id
        categ_id = vals.get("categ_id", self.categ_id.id)
        applied_on = self._deduce_applied_on(
            product_id=product.id,
            product_tmpl_id=template_id,
            categ_id=categ_id,
        )
        return applied_on, template_id

    @api.model
    def _deduce_applied_on(
        self, product_id=False, product_tmpl_id=False, categ_id=False
    ):
        if product_id:
            return "0_product_variant"
        if product_tmpl_id:
            return "1_product"
        if categ_id:
            return "2_product_category"
        return "3_global"

    @api.model
    def _update_applied_on_vals(self, vals):
        applied_on = vals.get("applied_on")
        if applied_on == "3_global":
            vals.update({"product_id": None, "product_tmpl_id": None, "categ_id": None})
        elif applied_on == "2_product_category":
            vals.update({"product_id": None, "product_tmpl_id": None})
        elif applied_on == "1_product":
            vals.update({"product_id": None, "categ_id": None})
        elif applied_on == "0_product_variant":
            vals.update({"categ_id": None})

    def _compute_is_pricelist_required(self):
        self.is_pricelist_required = True

    @api.depends("pricelist_id.company_id", "product_tmpl_id")
    def _compute_company_id(self):
        for item in self:
            item.company_id = (
                item.pricelist_id.company_id or item.product_tmpl_id.company_id
            )

    @api.depends("pricelist_id.currency_id", "company_id")
    def _compute_currency_id(self):
        for item in self:
            item.currency_id = (
                item.pricelist_id.currency_id
                or item.company_id.currency_id
                or item.env.company.currency_id
            )

    @api.depends(
        "applied_on", "categ_id", "product_tmpl_id", "product_id", "display_applied_on"
    )
    def _compute_name(self):
        for item in self:
            if item.categ_id and item.applied_on == "2_product_category":
                item.name = _("Category: %s", item.categ_id.display_name)
            elif item.product_tmpl_id and item.applied_on == "1_product":
                item.name = item.product_tmpl_id.display_name
            elif item.product_id and item.applied_on == "0_product_variant":
                item.name = _("Variant: %s", item.product_id.display_name)
            elif item.display_applied_on == "2_product_category":
                item.name = _("All Categories")
            else:
                item.name = _("All Products")

    @api.depends(
        "compute_price",
        "fixed_price",
        "pricelist_id",
        "percent_price",
        "price_discount",
        "price_markup",
        "price_surcharge",
        "base",
        "base_pricelist_id",
        "currency_id",
    )
    def _compute_price(self):
        for item in self:
            if item.compute_price == "fixed":
                item.price = formatLang(
                    item.env,
                    item.fixed_price,
                    dp="Product Price",
                    currency_obj=item.currency_id,
                )
            elif item.compute_price == "percentage":
                percentage = self._int_if_whole(item.percent_price)
                if item.base_pricelist_id:
                    item.price = _(
                        "%(percentage)s %% discount on %(pricelist)s",
                        percentage=percentage,
                        pricelist=item.base_pricelist_id.display_name,
                    )
                else:
                    item.price = _(
                        "%(percentage)s %% discount on sales price",
                        percentage=percentage,
                    )
            else:
                base_str = item._get_price_label_base_str()

                extra_fee_str = ""
                if item.price_surcharge > 0:
                    extra_fee_str = _(
                        "+ %(amount)s extra fee",
                        amount=format_amount(
                            item.env,
                            abs(item.price_surcharge),
                            currency=item.currency_id,
                        ),
                    )
                elif item.price_surcharge < 0:
                    extra_fee_str = _(
                        "- %(amount)s rebate",
                        amount=format_amount(
                            item.env,
                            abs(item.price_surcharge),
                            currency=item.currency_id,
                        ),
                    )
                discount_type, percentage = item._get_displayed_discount()
                item.price = _(
                    "%(percentage)s %% %(discount_type)s on %(base)s %(extra)s",
                    percentage=percentage,
                    discount_type=discount_type,
                    base=base_str,
                    extra=extra_fee_str,
                )

    @api.depends("price_discount")
    def _compute_price_markup(self):
        for item in self:
            item.price_markup = -item.price_discount

    def _inverse_price_markup(self):
        for item in self:
            item.price_discount = -item.price_markup

    @api.depends_context("lang")
    @api.depends(
        "base",
        "compute_price",
        "price_discount",
        "price_markup",
        "price_round",
        "price_surcharge",
        "currency_id",
    )
    def _compute_rule_tip(self):
        base_selection_vals = dict(
            self._fields["base"]._description_selection(self.env)
        )
        self.rule_tip = False
        for item in self:
            if item.compute_price != "formula" or not item.base:
                continue
            base_amount = 100
            discount = item.price_discount
            discount_factor = (100 - discount) / 100
            discounted_price = base_amount * discount_factor
            if item.price_round:
                discounted_price = float_round(
                    discounted_price, precision_rounding=item.price_round
                )
            surcharge = format_amount(item.env, item.price_surcharge, item.currency_id)
            discount_type, discount = item._get_displayed_discount()

            item.rule_tip = _(
                "%(base)s with a %(discount)s %% %(discount_type)s and %(surcharge)s extra fee\n"
                "Example: %(amount)s * %(discount_charge)s + %(price_surcharge)s → %(total_amount)s",
                base=base_selection_vals[item.base],
                discount=discount,
                discount_type=discount_type,
                surcharge=surcharge,
                amount=format_amount(item.env, 100, item.currency_id),
                discount_charge=discount_factor,
                price_surcharge=surcharge,
                total_amount=format_amount(
                    item.env, discounted_price + item.price_surcharge, item.currency_id
                ),
            )

    def _get_displayed_discount(self):
        self.check_singleton()
        if self.base == "standard_price":
            return _("markup"), self._int_if_whole(self.price_markup)
        return _("discount"), self._int_if_whole(self.price_discount)

    def _int_if_whole(self, percentage):
        return int(percentage) if percentage == int(percentage) else percentage

    def _get_price_label_base_str(self):
        self.check_singleton()
        base_str = ""
        if self.base == "pricelist" and self.base_pricelist_id:
            base_str = self.base_pricelist_id.display_name
        elif self.base == "standard_price":
            base_str = _("product cost")
        else:
            base_str = _("sales price")
        return base_str

    def _default_pricelist_id(self):
        return self.env["product.pricelist"].search(
            ["|", ("company_id", "=", False), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

    @api.onchange("base")
    def _onchange_base(self):
        for item in self:
            item.update(
                {
                    "price_discount": 0.0,
                    "price_markup": 0.0,
                }
            )

    @api.onchange("base_pricelist_id")
    def _onchange_base_pricelist_id(self):
        for item in self:
            if item.compute_price == "percentage":
                item.base = (
                    bool(item.base_pricelist_id) and "pricelist"
                ) or "list_price"

    @api.onchange("compute_price")
    def _onchange_compute_price(self):
        self.base_pricelist_id = False
        if self.compute_price != "fixed":
            self.fixed_price = 0.0
        if self.compute_price != "percentage":
            self.percent_price = 0.0
        if self.compute_price != "formula":
            self.update(
                {
                    "base": "list_price",
                    "price_discount": 0.0,
                    "price_surcharge": 0.0,
                    "price_markup": 0.0,
                    "price_round": 0.0,
                    "price_min_margin": 0.0,
                    "price_max_margin": 0.0,
                }
            )

    @api.onchange("display_applied_on")
    def _onchange_display_applied_on(self):
        for item in self:
            if not (item.product_tmpl_id or item.categ_id):
                item.update({"applied_on": "3_global"})
            elif item.display_applied_on == "1_product":
                item.update(
                    {
                        "applied_on": "1_product",
                        "categ_id": None,
                    }
                )
            elif item.display_applied_on == "2_product_category":
                item.update(
                    {
                        "product_id": None,
                        "product_tmpl_id": None,
                        "applied_on": "2_product_category",
                    }
                )

    @api.onchange("product_id")
    def _onchange_product_id(self):
        has_product_id = self.filtered("product_id")
        for item in has_product_id:
            item.product_tmpl_id = item.product_id.product_tmpl_id
        if self.env.context.get("default_applied_on", False) == "1_product":
            has_product_id.update({"applied_on": "0_product_variant"})
            (self - has_product_id).update({"applied_on": "1_product"})

    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_id(self):
        has_tmpl_id = self.filtered("product_tmpl_id")
        for item in has_tmpl_id:
            if (
                item.product_id
                and item.product_id.product_tmpl_id != item.product_tmpl_id
            ):
                item.product_id = None

    @api.onchange("product_id", "product_tmpl_id", "categ_id")
    def _onchange_rule_content(self):
        if not self.env.context.get("default_applied_on", False):
            variants_rules = self.filtered(
                lambda r: bool(r.product_id) and bool(r.product_tmpl_id)
            )
            template_rules = (self - variants_rules).filtered("product_tmpl_id")
            category_rules = self.filtered("categ_id")
            variants_rules.update({"applied_on": "0_product_variant"})
            template_rules.update({"applied_on": "1_product"})
            category_rules.update({"applied_on": "2_product_category"})
            global_rules = self - variants_rules - template_rules - category_rules
            global_rules.update({"applied_on": "3_global"})

    @api.onchange("price_round")
    def _onchange_price_round(self):
        self._check_price_round()

    @api.onchange("date_start", "date_end")
    def _onchange_validity_period(self):
        self._check_date_range()

    def _is_applicable_for(self, product, qty_in_product_uom):
        self.check_singleton()
        product.check_singleton()

        if self.min_quantity and qty_in_product_uom < self.min_quantity:
            return False

        if self.applied_on == "2_product_category":
            if not product.categ_id:
                return False
            return product.categ_id._is_descendant_of(self.categ_id)

        if product._name == "product.template":
            if self.applied_on == "1_product":
                return product.id == self.product_tmpl_id.id
            if self.applied_on == "0_product_variant":
                return (
                    product.product_variant_count == 1
                    and product.product_variant_id.id == self.product_id.id
                )
            return True

        if self.applied_on == "1_product":
            return product.product_tmpl_id.id == self.product_tmpl_id.id
        if self.applied_on == "0_product_variant":
            return product.id == self.product_id.id
        return True

    def _get_price(
        self, product, quantity, uom, date, currency=None, *, base_price=None, **kwargs
    ):
        self and self.check_singleton()
        product.check_singleton()
        uom.check_singleton()

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.check_singleton()

        product_uom_id = product.uom_id
        rule_currency = self.currency_id or currency

        def convert(price):
            if rule_currency != currency:
                price = rule_currency._convert(
                    price, currency, self.env.company, date, round=False
                )
            if product_uom_id != uom:
                price = product._convert_price_to_uom(price, uom)
            return price

        if self.compute_price == "fixed":
            return convert(self.fixed_price)

        if base_price is None:
            base_price = self._get_base_price(
                product, quantity, uom, date, currency, **kwargs
            )

        if self.compute_price == "percentage":
            return base_price - (base_price * (self.percent_price / 100))

        if self.compute_price == "formula":
            price_limit = base_price
            discount = self.price_discount
            price = base_price - (base_price * (discount / 100))
            if self.price_round:
                price = float_round(price, precision_rounding=convert(self.price_round))
            if self.price_surcharge:
                price += convert(self.price_surcharge)
            if self.price_min_margin:
                price = max(price, price_limit + convert(self.price_min_margin))
            if self.price_max_margin:
                price = min(price, price_limit + convert(self.price_max_margin))
            return price

        return base_price

    def _get_base_price(self, product, quantity, uom, date, currency, **kwargs):
        currency.check_singleton()

        rule_base = self.base or "list_price"
        if rule_base == "pricelist" and self.base_pricelist_id:
            price = self.base_pricelist_id._get_product_price(
                product,
                quantity,
                currency=self.base_pricelist_id.currency_id,
                uom=uom,
                date=date,
                **kwargs,
            )
            src_currency = self.base_pricelist_id.currency_id
        elif rule_base == "standard_price":
            src_currency = product.cost_currency_id
            price = product._get_prices(rule_base, uom=uom, date=date)[product.id]
        else:
            if rule_base != "list_price":
                raise ValidationError(
                    _(
                        "%(rule)s cannot be priced: %(base)s is not a base this"
                        " pricelist knows how to compute from.",
                        rule=self.display_name,
                        base=rule_base,
                    ),
                )
            src_currency = product.currency_id
            price = product._get_prices(rule_base, uom=uom, date=date)[product.id]

        if src_currency != currency:
            price = src_currency._convert(
                price, currency, self.env.company, date, round=False
            )

        return price

    def _get_price_before_discount(
        self, product, quantity, uom, date, currency=None, **kwargs
    ):
        pricelist_item = self
        while pricelist_item.base == "pricelist":
            rule_id = pricelist_item.base_pricelist_id._get_product_rule(
                product, quantity, currency=currency, uom=uom, date=date, **kwargs
            )
            rule_pricelist_item = self.env["product.pricelist.item"].browse(rule_id)
            if (
                rule_pricelist_item
                and rule_pricelist_item.compute_price == "percentage"
            ):
                pricelist_item = rule_pricelist_item
            else:
                break

        return pricelist_item._get_base_price(
            product, quantity, uom, date, currency, **kwargs
        )
