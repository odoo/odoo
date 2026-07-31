# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import float_round, format_amount, format_datetime, formatLang, get_lang


class ProductPricelistItem(models.Model):
    _name = 'product.pricelist.item'
    _description = "Pricelist Rule"
    _order = "applied_on, min_quantity desc, categ_id desc, id desc"
    _check_company_auto = True

    def _default_pricelist_id(self):
        return self.env['product.pricelist'].search([
            '|', ('company_id', '=', False),
            ('company_id', '=', self.env.company.id)], limit=1)

    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        index=True,
        ondelete='cascade',
        # Standard flows do not handle rules without pricelists (but some custom modules do)!
        required=False,
        default=_default_pricelist_id,
    )

    is_pricelist_required = fields.Boolean(compute='_compute_is_pricelist_required')

    company_id = fields.Many2one(comodel_name='res.company', compute='_compute_company_id', store=True)
    currency_id = fields.Many2one(comodel_name='res.currency', compute='_compute_currency_id', store=True)

    date_start = fields.Datetime(
        string="Start Date",
        help="Starting datetime for the pricelist item validation\n"
            "The displayed value depends on the timezone set in your preferences.")
    date_end = fields.Datetime(
        string="End Date",
        help="Ending datetime for the pricelist item validation\n"
            "The displayed value depends on the timezone set in your preferences.")

    min_quantity = fields.Float(
        string="Min. Quantity",
        default=0,
        digits='Product Unit',
        help="For the rule to apply, bought/sold quantity must be greater "
             "than or equal to the minimum quantity specified in this field.\n"
             "Expressed in the default unit of measure of the product.")

    applied_on = fields.Selection(
        selection=[
            ('0_product_variant', "Product Variant"),
            ('1_product', "Product"),
            ('2_product_category', "Product Category"),
            ('3_global', "All Products"),
        ],
        string="Apply On",
        compute='_compute_applied_on',
        store=True,
        precompute=True,
        required=True,
        help="Pricelist Item applicable on selected option")

    # Product Related Fields
    categ_id = fields.Many2one(
        string="Category",
        help="Specify a product category if this rule only applies to products belonging to this"
        " category or its children categories. Keep empty otherwise.",
        comodel_name='product.category',
        ondelete='cascade',
        check_company=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Product",
        ondelete='cascade', check_company=True, index='btree_not_null',
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Variant",
        ondelete='cascade', check_company=True, index='btree_not_null',
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
    product_uom_name = fields.Char(related='product_tmpl_id.uom_name')
    product_variant_count = fields.Integer(related='product_tmpl_id.product_variant_count')
    uom_id = fields.Many2one(string="Packaging", comodel_name='uom.uom')
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')

    # Price Related Fields
    base = fields.Selection(
        selection=[
            ('list_price', 'Sales Price'),
            ('standard_price', 'Cost'),
            ('pricelist', 'Other Pricelist'),
        ],
        string="Based on",
        default='list_price',
        required=True,
        help="Base price for computation.\n"
             "Sales Price: The base price will be the Sales Price.\n"
             "Cost Price: The base price will be the cost price.\n"
             "Other Pricelist: Computation of the base price based on another Pricelist.")
    base_pricelist_id = fields.Many2one('product.pricelist', 'Other Pricelist', check_company=True)

    compute_price = fields.Selection(
        selection=[
            ('discount', "Discount"),
            ('markup', "Surcharge"),
            ('fixed', "Fixed Price"),
        ],
        help="How the price is derived from the base price.\n"
             "Discount: a percentage taken off it.\n"
             "Surcharge: a percentage added on top of it.\n"
             "Fixed Price: a set amount, ignoring the base price entirely.\n"
             "Activate the discount settings to show the discount to the customer.",
        index=True,
        default='fixed',
        required=True,
    )

    fixed_price = fields.Float(string="Fixed Price", min_display_digits='Product Price')

    price_discount = fields.Float(
        string="Price Discount",
        default=0,
        digits=(16, 2),
    )
    price_round = fields.Float(
        string="Price Rounding",
        min_display_digits='Product Price',
        help="Sets the price so that it is a multiple of this value.\n"
             "Rounding is applied after the discount and before the surcharge.\n"
             "To have prices that end in 9.99, round off to 10.00 and set an extra at -0.01")
    price_surcharge = fields.Float(
        string="Extra Fee",
        min_display_digits='Product Price',
        help="Specify the fixed amount to add or subtract (if negative) to the amount calculated with the discount.")

    price_markup = fields.Float(
        string="Surcharge",
        digits=(16, 2),
        compute='_compute_price_markup',
        inverse='_inverse_price_markup',
    )

    price_min_margin = fields.Float(
        string="Min. Price Margin",
        min_display_digits='Product Price',
        help="Specify the minimum amount of margin over the base price.")
    price_max_margin = fields.Float(
        string="Max. Price Margin",
        min_display_digits='Product Price',
        help="Specify the maximum amount of margin over the base price.")

    # functional fields used for usability purposes
    name = fields.Char(
        string="Name",
        compute='_compute_name',
        help="Explicit rule name for this pricelist line.")
    price = fields.Char(
        string="Price",
        compute='_compute_price_label',
        help="Explicit rule name for this pricelist line.")
    rule_tip = fields.Char(compute='_compute_rule_tip')
    is_plain_discount = fields.Boolean(
        string="Plain Discount",
        compute='_compute_is_plain_discount',
        search='_search_is_plain_discount',
        help="Whether the rule lowers the price by exactly its discount percentage.")

    #=== COMPUTE METHODS ===#

    def _compute_is_pricelist_required(self):
        self.is_pricelist_required = True

    @api.depends('pricelist_id.company_id', 'product_tmpl_id')
    def _compute_company_id(self):
        for item in self:
            item.company_id = item.pricelist_id.company_id or item.product_tmpl_id.company_id

    @api.depends('pricelist_id.currency_id', 'company_id')
    def _compute_currency_id(self):
        for item in self:
            item.currency_id = (
                item.pricelist_id.currency_id
                or item.company_id.currency_id
                or item.env.company.currency_id
            )

    @api.depends('product_tmpl_id', 'product_tmpl_id.uom_id', 'product_tmpl_id.uom_ids')
    def _compute_allowed_uom_ids(self):
        for item in self:
            item.allowed_uom_ids = item.product_tmpl_id.uom_id | item.product_tmpl_id.uom_ids

    @api.depends('categ_id', 'product_id', 'product_tmpl_id')
    def _compute_applied_on(self):
        for item in self:
            if item.categ_id:
                item.applied_on = '2_product_category'
            elif item.product_tmpl_id:
                item.applied_on = '0_product_variant' if item.product_id else '1_product'
            else:
                item.applied_on = '3_global'

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id')
    def _compute_name(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = item.categ_id.display_name
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = item.product_tmpl_id.display_name
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = item.product_id.display_name
            else:
                item.name = item.env._("All Products")

    @api.depends('name', 'price')
    def _compute_display_name(self):
        for item in self:
            item.display_name = f"{item.price} - {item.name}"

    def _get_price_label_base_str(self):
        """This method allows you to extend it to other modules with other
        options in the base field to return a different text.
        """
        self.ensure_one()
        base_str = ""
        if self.base == 'pricelist' and self.base_pricelist_id:
            base_str = self.base_pricelist_id.display_name
        elif self.base == 'standard_price':
            base_str = self.env._("product cost")
        else:
            base_str = self.env._("sales price")
        return base_str

    @api.depends(
        'compute_price', 'fixed_price', 'pricelist_id', 'price_discount',
        'price_markup', 'price_surcharge', 'base', 'base_pricelist_id',
    )
    def _compute_price_label(self):
        for item in self:
            if item.compute_price == 'fixed':
                item.price = formatLang(
                    item.env, item.fixed_price, dp="Product Price", currency_obj=item.currency_id)
            else:
                base_str = item._get_price_label_base_str()

                extra_fee_str = ""
                if item.price_surcharge > 0:
                    extra_fee_str = item.env._(
                        "+ %(amount)s extra fee",
                        amount=format_amount(
                            item.env,
                            abs(item.price_surcharge),
                            currency=item.currency_id,
                        ),
                    )
                elif item.price_surcharge < 0:
                    extra_fee_str = item.env._(
                        "- %(amount)s rebate",
                        amount=format_amount(
                            item.env,
                            abs(item.price_surcharge),
                            currency=item.currency_id,
                        ),
                    )
                discount_type, percentage = self._get_displayed_discount(item)
                item.price = item.env._("%(percentage)s %% %(discount_type)s on %(base)s %(extra)s",
                    percentage=percentage,
                    discount_type=discount_type,
                    base=base_str,
                    extra=extra_fee_str,
                )

    @api.depends('price_discount')
    def _compute_price_markup(self):
        for item in self:
            item.price_markup = -item.price_discount

    def _inverse_price_markup(self):
        for item in self:
            item.price_discount = -item.price_markup

    @api.depends_context('lang')
    @api.depends('base', 'compute_price', 'price_discount', 'price_round', 'price_surcharge')
    def _compute_rule_tip(self):
        self.rule_tip = False
        lang = self.env['res.lang'].browse(get_lang(self.env).id)
        for item in self:
            if item.compute_price == 'fixed' or not item.base:
                continue
            base_amount = 100
            discount_factor = (100 - item.price_discount) / 100
            discounted_price = base_amount * discount_factor
            if item.price_round:
                discounted_price = float_round(discounted_price, precision_rounding=item.price_round)

            amount = format_amount(item.env, base_amount, item.currency_id)
            # %g keeps only the decimals the factor uses and rounds the float noise off.
            factor = lang.format('%g', discount_factor, grouping=True)
            surcharge = format_amount(item.env, item.price_surcharge, item.currency_id)
            total = format_amount(
                item.env, discounted_price + item.price_surcharge, item.currency_id
            )
            item.rule_tip = f"{amount} × {factor} + {surcharge} = {total}"

    @api.depends(
        'compute_price', 'price_discount', 'price_round', 'price_surcharge',
        'price_min_margin', 'price_max_margin',
    )
    def _compute_is_plain_discount(self):
        for item in self:
            item.is_plain_discount = item._is_discount_rule() and not (
                item.price_round
                or item.price_surcharge
                or item.price_min_margin
                or item.price_max_margin
            )

    def _search_is_plain_discount(self, operator, value):  # noqa: ARG002
        # Mirrors `_compute_is_plain_discount`, keep both in sync.
        plain_discount = Domain.AND([
            Domain('compute_price', '=', 'discount'),
            Domain('price_discount', '>', 0),
            Domain('price_round', '=', 0),
            Domain('price_surcharge', '=', 0),
            Domain('price_min_margin', '=', 0),
            Domain('price_max_margin', '=', 0),
        ])
        return plain_discount if operator == 'in' else ~plain_discount

    def _get_integer(self, percentage):
        return int(percentage) if percentage == int(percentage) else percentage

    def _get_displayed_discount(self, item):
        if item.compute_price == 'markup':
            return self.env._("surcharge"), self._get_integer(item.price_markup)
        return self.env._("discount"), self._get_integer(item.price_discount)

    #=== CONSTRAINT METHODS ===#

    @api.constrains('base_pricelist_id', 'base')
    def _check_base_pricelist_id(self):
        if any(item.base == 'pricelist' and not item.base_pricelist_id for item in self):
            raise ValidationError(self.env._('A pricelist item with "Other Pricelist" as base must have a base_pricelist_id.'))

    @api.constrains('base_pricelist_id', 'pricelist_id', 'base')
    def _check_pricelist_recursion(self):
        def dfs_path(from_pl, to_pl, path, seen):
            if (from_pl, to_pl) in seen:
                # If another pricelist rule from the same pricelist has the same target,
                # there is no need to test that path again.
                return path.browse()

            if to_pl in path:
                return path + to_pl

            seen.add((from_pl, to_pl))
            pricelist_based_items = self.env["product.pricelist.item"]._read_group(
                domain=[("pricelist_id", "=", to_pl.id), ("base", "=", "pricelist")],
                groupby=["base_pricelist_id"],
                aggregates=["id:recordset"],
            )
            new_path = path + to_pl
            for pricelist, _to_items in pricelist_based_items:
                if res := dfs_path(to_pl, pricelist, new_path, seen):
                    return res
            return path.browse()

        seen = set()
        for item in self:
            # Skip validation for rules not based on other pricelists.
            if item.base != "pricelist" or not item.base_pricelist_id or not item.pricelist_id:
                continue
            if path := dfs_path(item.pricelist_id, item.base_pricelist_id, item.pricelist_id, seen):
                raise ValidationError(
                    item.env._("Recursive pricelist rules detected: %s", " ⇒ ".join(path.mapped("name")))
                )

    @api.constrains('date_start', 'date_end')
    def _check_date_range(self):
        for item in self:
            if item.date_start and item.date_end and item.date_start >= item.date_end:
                raise ValidationError(item.env._(
                    '%(item_name)s: end date (%(end_date)s) should be after start date (%(start_date)s)',
                    item_name=item.display_name,
                    end_date=format_datetime(self.env, item.date_end),
                    start_date=format_datetime(self.env, item.date_start),
                ))
        return True

    @api.constrains('price_min_margin', 'price_max_margin')
    def _check_margin(self):
        if any(item.price_min_margin > item.price_max_margin for item in self):
            raise ValidationError(self.env._('The minimum margin should be lower than the maximum margin.'))

    @api.constrains('product_id', 'product_tmpl_id', 'categ_id')
    def _check_product_consistency(self):
        for item in self:
            if item.applied_on == "2_product_category" and not item.categ_id:
                raise ValidationError(item.env._("Please specify the category for which this rule should be applied"))
            if item.applied_on == "1_product" and not item.product_tmpl_id:
                raise ValidationError(item.env._("Please specify the product for which this rule should be applied"))
            if item.applied_on == "0_product_variant" and not item.product_id:
                raise ValidationError(item.env._("Please specify the product variant for which this rule should be applied"))

    #=== ONCHANGE METHODS ===#

    @api.onchange('base_pricelist_id')
    def _onchange_base_pricelist_id(self):
        if self.compute_price == 'discount':
            self.base = 'pricelist' if self.base_pricelist_id else 'list_price'

    @api.onchange('compute_price')
    def _onchange_compute_price(self):
        if self.compute_price != 'fixed':
            self.fixed_price = 0.0
        if self.compute_price == 'fixed':
            self.update({
                'base': 'list_price',
                'base_pricelist_id': False,
                'price_surcharge': 0.0,
                'price_round': 0.0,
                'price_min_margin': 0.0,
                'price_max_margin': 0.0,
            })
        elif self.compute_price == 'discount' and self.base == 'standard_price':
            # A discount offers no base selector, only the pricelist it is taken from.
            # A cost carried over from a surcharge would be neither visible nor editable.
            self.base = 'list_price'
        self.price_discount = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for item in self.filtered('product_id'):
            item.product_tmpl_id = item.product_id.product_tmpl_id

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_id and self.product_id.product_tmpl_id != self.product_tmpl_id:
            self.product_id = False
        if self.product_tmpl_id:
            self.categ_id = False

    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        if self.categ_id:
            self.product_id = False
            self.product_tmpl_id = False

    @api.onchange('price_markup')
    def _onchange_price_markup(self):
        # The inverse only runs on write, and everything else reads the discount.
        self.price_discount = -self.price_markup

    @api.onchange('price_round')
    def _onchange_price_round(self):
        if any(item.price_round and item.price_round < 0.0 for item in self):
            raise ValidationError(self.env._("The rounding method must be strictly positive."))

    @api.onchange('date_start', 'date_end')
    def _onchange_validity_period(self):
        self._check_date_range()

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('product_id') and not values.get('product_tmpl_id'):
                # Deduce product template from product variant if not specified.
                # Ensures that the pricelist rule is properly configured and displayed in the UX
                # even in case of partial/incomplete data (mostly for imports).
                values['product_tmpl_id'] = self.env['product.product'].browse(
                    values.get('product_id')
                ).product_tmpl_id.id
        return super().create(vals_list)

    #=== BUSINESS METHODS ===#

    def _is_discount_rule(self):
        """Whether the rule lowers the price it is based on."""
        self.ensure_one()
        return self.compute_price == 'discount' and self.price_discount > 0

    def _is_applicable_for(self, product, quantity, *, uom=None, **kwargs):
        """Check whether the current rule is valid for the given product, qty and uom.

        Note: self.ensure_one()

        :param product: product record (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param uom: Selected unit of measure (uom.uom record)

        :returns: Whether rules is valid or not
        :rtype: bool
        """
        self.ensure_one()
        product.ensure_one()
        res = True

        is_product_template = product._name == 'product.template'
        product_uom = product.uom_id
        uom = uom or product_uom

        # Filter the rules restricted to specific units of measure.
        if self.uom_id and uom != self.uom_id:
            return False

        qty_to_consider = quantity
        if uom not in product_uom + self.uom_id:
            # Convert the quantity to consider to the product base uom if the requested uom is not
            # in the rule allowed unit of measures.
            qty_to_consider = uom._compute_quantity(quantity, product_uom)

        if self.min_quantity and qty_to_consider < self.min_quantity:
            res = False
        elif self.applied_on == "2_product_category":
            if not product.categ_id or (
                product.categ_id != self.categ_id
                and not product.categ_id.parent_path.startswith(self.categ_id.parent_path)
            ):
                res = False
        # Applied on a specific product template/variant
        elif is_product_template:
            if self.applied_on == "1_product" and product.id != self.product_tmpl_id.id:
                res = False
            elif self.applied_on == "0_product_variant" and not (
                product.product_variant_count == 1
                and product.product_variant_id.id == self.product_id.id
            ):
                # product self acceptable on template if has only one variant
                res = False
        elif (
            self.applied_on == "1_product"
            and product.product_tmpl_id.id != self.product_tmpl_id.id
        ) or (
            self.applied_on == "0_product_variant" and product.id != self.product_id.id
        ):
            res = False

        return res

    def _compute_price(self, product, quantity, uom, **kwargs):
        """Compute the unit price of a product in the context of a pricelist application.

        Note: self and self.ensure_one()

        :param product: recordset of product (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency (for the case where self is empty)
        :param dict kwargs: unused parameters available for overrides

        :returns: price according to pricelist rule or the product price, expressed in the param
                  currency, the pricelist currency or the company currency
        :rtype: float
        """
        self and self.ensure_one()  # self is at most one record
        product.ensure_one()

        uom = uom or product._get_main_uom()
        uom.ensure_one()

        if self.compute_price == 'fixed':
            return product.uom_id._compute_price(self.fixed_price, uom)

        base_price = self._compute_base_price(product, quantity, uom, **kwargs)
        if self.compute_price in ('discount', 'markup'):
            product_uom = product.uom_id
            price = base_price - (base_price * (self.price_discount / 100))
            if self.price_round:
                price = float_round(price, precision_rounding=self.price_round)

            if self.price_surcharge:
                price += product_uom._compute_price(self.price_surcharge, uom)

            if self.price_min_margin:
                price = max(
                    price, base_price + product_uom._compute_price(self.price_min_margin, uom)
                )

            if self.price_max_margin:
                price = min(
                    price, base_price + product_uom._compute_price(self.price_max_margin, uom)
                )
        else:  # empty self, or extended pricelist price computation logic
            price = base_price

        return price

    def _compute_base_price(
        self, product, quantity, uom, *, currency=None, date=False, depth=0, base_prices=None, **kwargs
    ):
        """Compute the base price for a given rule.

        :param product: recordset of product (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency in which the returned price must be expressed
        :param int depth: Technical flag tracking the current recursion depth

        :returns: base price, expressed in provided pricelist currency
        :rtype: float
        """
        rule_base = self.base or 'list_price'
        if rule_base == 'pricelist' and self.base_pricelist_id:
            if base_prices:
                price = base_prices[product.id]
            else:
                price = self.base_pricelist_id._get_product_price(
                    product,
                    quantity,
                    currency=self.base_pricelist_id.currency_id,
                    uom=uom,
                    date=date,
                    depth=depth + 1,
                    **kwargs,
                )
            src_currency = self.base_pricelist_id.currency_id
        elif rule_base == "standard_price":
            src_currency = product.cost_currency_id
            price = product._price_compute(rule_base, uom=uom)[product.id]
        else: # list_price
            src_currency = product.currency_id
            price = product._price_compute(rule_base, uom=uom)[product.id]

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()
        if src_currency != currency:
            price = src_currency._convert(price, currency, date=date, round=False)

        return price

    def _compute_price_before_discount(self, *args, **kwargs):
        """Compute the base price of the given rule, considering chained pricelists.

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency in which the returned price must be expressed

        :returns: base price, expressed in provided pricelist currency
        :rtype: float
        """
        pricelist_item = self
        # Find the lowest pricelist rule whose pricelist is configured to show the discount to the
        # customer.
        while pricelist_item.base == 'pricelist':
            rule_id = pricelist_item.base_pricelist_id._get_product_rule(*args, **kwargs)
            rule_pricelist_item = self.env['product.pricelist.item'].browse(rule_id)
            if rule_pricelist_item.is_plain_discount:
                pricelist_item = rule_pricelist_item
            else:
                break

        return pricelist_item._compute_base_price(*args, **kwargs)
