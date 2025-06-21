# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.tools import format_amount, format_datetime, formatLang


class PricelistItem(models.Model):
    _name = "product.pricelist.item"
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
        index=True, ondelete='cascade',
        required=True,
        default=_default_pricelist_id)

    company_id = fields.Many2one(related='pricelist_id.company_id', store=True)
    currency_id = fields.Many2one(related='pricelist_id.currency_id', store=True)

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
        digits='Product Unit of Measure',
        help="For the rule to apply, bought/sold quantity must be greater "
             "than or equal to the minimum quantity specified in this field.\n"
             "Expressed in the default unit of measure of the product.")

    applied_on = fields.Selection(
        selection=[
            ('3_global', "All Products"),
            ('2_product_category', "Product Category"),
            ('1_product', "Product"),
            ('0_product_variant', "Product Variant"),
        ],
        string="Apply On",
        default='3_global',
        required=True,
        help="Pricelist Item applicable on selected option")

    display_applied_on = fields.Selection(
        selection=[
            ('1_product', "Product"),
            ('2_product_category', "Category"),
        ],
        default='1_product',
        required=True,
        help="Pricelist Item applicable on selected option")

    categ_id = fields.Many2one(
        comodel_name='product.category',
        string="Category",
        ondelete='cascade',
        help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Product",
        ondelete='cascade', check_company=True,
        help="Specify a template if this rule only applies to one product template. Keep empty otherwise.")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Variant",
        ondelete='cascade', check_company=True,
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
    product_uom = fields.Char(related='product_tmpl_id.uom_name')
    product_variant_count = fields.Integer(related='product_tmpl_id.product_variant_count')

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
            ('percentage', "Discount"),
            ('formula', "Formula"),
            ('fixed', "Fixed Price"),
        ],
        help="Use the discount rules and activate the discount settings"
             " in order to show discount to customer.",
        index=True, default='fixed', required=True)

    fixed_price = fields.Float(string="Fixed Price", digits='Product Price')
    percent_price = fields.Float(
        string="Percentage Price",
        help="You can apply a mark-up by setting a negative discount.")

    price_discount = fields.Float(
        string="Price Discount",
        default=0,
        digits=(16, 2),
        help="You can apply a mark-up by setting a negative discount.")
    price_round = fields.Float(
        string="Price Rounding",
        digits='Product Price',
        help="Sets the price so that it is a multiple of this value.\n"
             "Rounding is applied after the discount and before the surcharge.\n"
             "To have prices that end in 9.99, round off to 10.00 and set an extra at -0.01")
    price_surcharge = fields.Float(
        string="Extra Fee",
        digits='Product Price',
        help="Specify the fixed amount to add or subtract (if negative) to the amount calculated with the discount.")

    price_markup = fields.Float(
        string="Markup",
        digits=(16, 2),
        compute='_compute_price_markup',
        inverse='_inverse_price_markup',
        store=True,
        help="You can apply a mark-up on the cost")

    price_min_margin = fields.Float(
        string="Min. Price Margin",
        digits='Product Price',
        help="Specify the minimum amount of margin over the base price.")
    price_max_margin = fields.Float(
        string="Max. Price Margin",
        digits='Product Price',
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

    #=== COMPUTE METHODS ===#

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id')
    def _compute_name(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s", item.categ_id.display_name)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = item.product_tmpl_id.display_name
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = _("Variant: %s", item.product_id.display_name)
            elif item.display_applied_on == '2_product_category':
                item.name = _("All Categories")
            else:
                item.name = _("All Products")

    @api.depends(
        'compute_price', 'fixed_price', 'pricelist_id', 'percent_price', 'price_discount',
        'price_markup', 'price_surcharge', 'base', 'base_pricelist_id',
    )
    def _compute_price_label(self):
        for item in self:
            if item.compute_price == 'fixed':
                item.price = formatLang(
                    item.env, item.fixed_price, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                percentage = self._get_integer(item.percent_price)
                if item.base_pricelist_id:
                    item.price = _(
                        "%(percentage)s %% discount on %(pricelist)s",
                        percentage=percentage,
                        pricelist=item.base_pricelist_id.display_name
                    )
                else:
                    item.price = _(
                        "%(percentage)s %% discount on sales price",
                        percentage=percentage
                    )
            else:
                base_str = ""
                if item.base == 'pricelist' and item.base_pricelist_id:
                    base_str = item.base_pricelist_id.display_name
                elif item.base == 'standard_price':
                    base_str = _("product cost")
                else:
                    base_str = _("sales price")

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
                discount_type, percentage = self._get_displayed_discount(item)
                item.price = _("%(percentage)s %% %(discount_type)s on %(base)s %(extra)s",
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
    @api.depends(
        'base', 'compute_price', 'price_discount', 'price_markup', 'price_round', 'price_surcharge',
    )
    def _compute_rule_tip(self):
        base_selection_vals = {elem[0]: elem[1] for elem in self._fields['base']._description_selection(self.env)}
        self.rule_tip = False
        for item in self:
            if item.compute_price != 'formula':
                continue
            base_amount = 100
            discount = item.price_discount if item.base != 'standard_price' else -item.price_markup
            discount_factor = (100 - discount) / 100
            discounted_price = base_amount * discount_factor
            if item.price_round:
                discounted_price = tools.float_round(discounted_price, precision_rounding=item.price_round)
            surcharge = tools.format_amount(item.env, item.price_surcharge, item.currency_id)
            discount_type, discount = self._get_displayed_discount(item)

            item.rule_tip = _(
                "%(base)s with a %(discount)s %% %(discount_type)s and %(surcharge)s extra fee\n"
                "Example: %(amount)s * %(discount_charge)s + %(price_surcharge)s → %(total_amount)s",
                base=base_selection_vals[item.base],
                discount=discount,
                discount_type=discount_type,
                surcharge=surcharge,
                amount=tools.format_amount(item.env, 100, item.currency_id),
                discount_charge=discount_factor,
                price_surcharge=surcharge,
                total_amount=tools.format_amount(
                    item.env, discounted_price + item.price_surcharge, item.currency_id),
            )

    def _get_integer(self, percentage):
        return int(percentage) if percentage.is_integer() else percentage

    def _get_displayed_discount(self, item):
        if item.base == 'standard_price':
            return _("markup"), self._get_integer(item.price_markup)
        return _("discount"), self._get_integer(item.price_discount)

    #=== CONSTRAINT METHODS ===#

    @api.constrains('base_pricelist_id', 'pricelist_id', 'base')
    def _check_pricelist_recursion(self):
        if any(item.base == 'pricelist' and item.pricelist_id and item.pricelist_id == item.base_pricelist_id for item in self):
            raise ValidationError(_('You cannot assign the Main Pricelist as Other Pricelist in PriceList Item'))

    @api.constrains('date_start', 'date_end')
    def _check_date_range(self):
        for item in self:
            if item.date_start and item.date_end and item.date_start >= item.date_end:
                raise ValidationError(_(
                    '%(item_name)s: end date (%(end_date)s) should be after start date (%(start_date)s)',
                    item_name=item.display_name,
                    end_date=format_datetime(self.env, item.date_end),
                    start_date=format_datetime(self.env, item.date_start),
                ))
        return True

    @api.constrains('price_min_margin', 'price_max_margin')
    def _check_margin(self):
        if any(item.price_min_margin > item.price_max_margin for item in self):
            raise ValidationError(_('The minimum margin should be lower than the maximum margin.'))

    @api.constrains('product_id', 'product_tmpl_id', 'categ_id')
    def _check_product_consistency(self):
        for item in self:
            if item.applied_on == "2_product_category" and not item.categ_id:
                raise ValidationError(_("Please specify the category for which this rule should be applied"))
            elif item.applied_on == "1_product" and not item.product_tmpl_id:
                raise ValidationError(_("Please specify the product for which this rule should be applied"))
            elif item.applied_on == "0_product_variant" and not item.product_id:
                raise ValidationError(_("Please specify the product variant for which this rule should be applied"))

    #=== ONCHANGE METHODS ===#

    @api.onchange('base')
    def _onchange_base(self):
        for item in self:
            item.update({
                'price_discount': 0.0,
                'price_markup': 0.0,
            })

    @api.onchange('base_pricelist_id')
    def _onchange_base_pricelist_id(self):
        for item in self:
            if item.compute_price == 'percentage':
                item.base = bool(item.base_pricelist_id) and 'pricelist' or 'list_price'

    @api.onchange('compute_price')
    def _onchange_compute_price(self):
        self.base_pricelist_id = False
        if self.compute_price != 'fixed':
            self.fixed_price = 0.0
        if self.compute_price != 'percentage':
            self.percent_price = 0.0
        if self.compute_price != 'formula':
            self.update({
                'base': 'list_price',
                'price_discount': 0.0,
                'price_surcharge': 0.0,
                'price_markup': 0.0,
                'price_round': 0.0,
                'price_min_margin': 0.0,
                'price_max_margin': 0.0,
            })

    @api.onchange('display_applied_on')
    def _onchange_display_applied_on(self):
        for item in self:
            if not (item.product_tmpl_id or item.categ_id):
                item.update(dict(
                    applied_on='3_global',
                ))
            elif item.display_applied_on == '1_product':
                item.update(dict(
                    applied_on='1_product',
                    categ_id=None,
                ))
            elif item.display_applied_on == '2_product_category':
                item.update(dict(
                    product_id=None,
                    product_tmpl_id=None,
                    applied_on='2_product_category',
                    product_uom=None,
                ))

    @api.onchange('price_markup')
    def _onchange_price_markup(self):
        pass  # TODO: remove in master

    @api.onchange('product_id')
    def _onchange_product_id(self):
        has_product_id = self.filtered('product_id')
        for item in has_product_id:
            item.product_tmpl_id = item.product_id.product_tmpl_id
        if self.env.context.get('default_applied_on', False) == '1_product':
            # If a product variant is specified, apply on variants instead
            # Reset if product variant is removed
            has_product_id.update({'applied_on': '0_product_variant'})
            (self - has_product_id).update({'applied_on': '1_product'})

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        has_tmpl_id = self.filtered('product_tmpl_id')
        for item in has_tmpl_id:
            if item.product_id and item.product_id.product_tmpl_id != item.product_tmpl_id:
                item.product_id = None

    @api.onchange('product_id', 'product_tmpl_id', 'categ_id')
    def _onchange_rule_content(self):
        if not self.env.context.get('default_applied_on', False):
            # If we aren't coming from a specific product template/variant.
            variants_rules = self.filtered('product_id')
            template_rules = (self-variants_rules).filtered('product_tmpl_id')
            category_rules = self.filtered(lambda cat: cat.categ_id and cat.categ_id.name != 'All')
            variants_rules.update({'applied_on': '0_product_variant'})
            template_rules.update({'applied_on': '1_product'})
            category_rules.update({'applied_on': '2_product_category'})
            global_rules = self - variants_rules - template_rules - category_rules
            global_rules.update({'applied_on': '3_global'})

    @api.onchange('price_round')
    def _onchange_price_round(self):
        if any(item.price_round and item.price_round < 0.0 for item in self):
            raise ValidationError(_("The rounding method must be strictly positive."))

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

            if not values.get('applied_on'):
                values['applied_on'] = (
                    '0_product_variant' if values.get('product_id') else
                    '1_product' if values.get('product_tmpl_id') else
                    '2_product_category' if values.get('categ_id') else
                    '3_global'
                )

            # Ensure item consistency for later searches.
            applied_on = values['applied_on']
            if applied_on == '3_global':
                values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None))
            elif applied_on == '2_product_category':
                values.update(dict(product_id=None, product_tmpl_id=None))
            elif applied_on == '1_product':
                values.update(dict(product_id=None, categ_id=None))
            elif applied_on == '0_product_variant':
                values.update(dict(categ_id=None))
        return super().create(vals_list)

    def write(self, values):
        if values.get('applied_on', False):
            # Ensure item consistency for later searches.
            applied_on = values['applied_on']
            if applied_on == '3_global':
                values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None))
            elif applied_on == '2_product_category':
                values.update(dict(product_id=None, product_tmpl_id=None))
            elif applied_on == '1_product':
                values.update(dict(product_id=None, categ_id=None))
            elif applied_on == '0_product_variant':
                values.update(dict(categ_id=None))
        return super().write(values)

    #=== BUSINESS METHODS ===#

    def _is_applicable_for(self, product, qty_in_product_uom):
        """Check whether the current rule is valid for the given product & qty.

        Note: self.ensure_one()

        :param product: product record (product.product/product.template)
        :param float qty_in_product_uom: quantity, expressed in product UoM
        :returns: Whether rules is valid or not
        :rtype: bool
        """
        self.ensure_one()
        product.ensure_one()
        res = True

        is_product_template = product._name == 'product.template'
        if self.min_quantity and qty_in_product_uom < self.min_quantity:
            res = False

        elif self.applied_on == "2_product_category":
            if (
                product.categ_id != self.categ_id
                and not product.categ_id.parent_path.startswith(self.categ_id.parent_path)
            ):
                res = False
        else:
            # Applied on a specific product template/variant
            if is_product_template:
                if self.applied_on == "1_product" and product.id != self.product_tmpl_id.id:
                    res = False
                elif self.applied_on == "0_product_variant" and not (
                    product.product_variant_count == 1
                    and product.product_variant_id.id == self.product_id.id
                ):
                    # product self acceptable on template if has only one variant
                    res = False
            else:
                if self.applied_on == "1_product" and product.product_tmpl_id.id != self.product_tmpl_id.id:
                    res = False
                elif self.applied_on == "0_product_variant" and product.id != self.product_id.id:
                    res = False

        return res

    def _compute_price(self, product, quantity, uom, date, currency=None):
        """Compute the unit price of a product in the context of a pricelist application.

        Note: self and self.ensure_one()

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency (for the case where self is empty)

        :returns: price according to pricelist rule or the product price, expressed in the param
                  currency, the pricelist currency or the company currency
        :rtype: float
        """
        self and self.ensure_one()  # self is at most one record
        product.ensure_one()
        uom.ensure_one()

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        # Pricelist specific values are specified according to product UoM
        # and must be multiplied according to the factor between uoms
        product_uom = product.uom_id
        if product_uom != uom:
            convert = lambda p: product_uom._compute_price(p, uom)
        else:
            convert = lambda p: p

        if self.compute_price == 'fixed':
            price = convert(self.fixed_price)
        elif self.compute_price == 'percentage':
            base_price = self._compute_base_price(product, quantity, uom, date, currency)
            price = (base_price - (base_price * (self.percent_price / 100))) or 0.0
        elif self.compute_price == 'formula':
            base_price = self._compute_base_price(product, quantity, uom, date, currency)
            # complete formula
            price_limit = base_price
            discount = self.price_discount if self.base != 'standard_price' else -self.price_markup
            price = base_price - (base_price * (discount / 100))
            if self.price_round:
                price = tools.float_round(price, precision_rounding=self.price_round)

            if self.price_surcharge:
                price += convert(self.price_surcharge)

            if self.price_min_margin:
                price = max(price, price_limit + convert(self.price_min_margin))

            if self.price_max_margin:
                price = min(price, price_limit + convert(self.price_max_margin))
        else:  # empty self, or extended pricelist price computation logic
            price = self._compute_base_price(product, quantity, uom, date, currency)

        return price

    def _compute_base_price(self, product, quantity, uom, date, currency):
        """ Compute the base price for a given rule

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency in which the returned price must be expressed

        :returns: base price, expressed in provided pricelist currency
        :rtype: float
        """
        currency.ensure_one()

        rule_base = self.base or 'list_price'
        if rule_base == 'pricelist' and self.base_pricelist_id:
            price = self.base_pricelist_id._get_product_price(
                product, quantity, currency=self.base_pricelist_id.currency_id, uom=uom, date=date
            )
            src_currency = self.base_pricelist_id.currency_id
        elif rule_base == "standard_price":
            src_currency = product.cost_currency_id
            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]
        else: # list_price
            src_currency = product.currency_id
            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]

        if src_currency != currency:
            price = src_currency._convert(price, currency, self.env.company, date, round=False)

        return price

    def _compute_price_before_discount(self, *args, **kwargs):
        """Compute the base price of the lowest pricelist rule,
        discount is shown by default if computation method is a percentage rule.

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
            if rule_pricelist_item and rule_pricelist_item.compute_price == 'percentage':
                pricelist_item = rule_pricelist_item
            else:
                break

        return pricelist_item._compute_base_price(*args, **kwargs)

    @api.model
    def _is_discount_feature_enabled(self):
        superuser = self.env['res.users'].browse(SUPERUSER_ID)
        return superuser.has_group('sale.group_discount_per_so_line')

    def _show_discount(self):
        if not self:
            return False

        self.ensure_one()
        return self._is_discount_feature_enabled() and self.compute_price == 'percentage'
