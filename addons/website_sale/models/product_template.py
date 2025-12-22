# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.tools import float_is_zero, is_html_empty
from odoo.tools.translate import html_translate

from odoo.addons.website.models import ir_http

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = [
        'rating.mixin',
        'product.template',
        'website.seo.metadata',
        'website.published.multi.mixin',
        'website.searchable.mixin',
    ]
    _name = 'product.template'
    _mail_post_access = 'read'
    _check_company_auto = True

    #=== DEFAULT METHODS ===#

    @api.model
    def _default_website_sequence(self):
        """ We want new product to be the last (highest seq).
        Every product should ideally have an unique sequence.
        Default sequence (10000) should only be used for DB first product.
        As we don't resequence the whole tree (as `sequence` does), this field
        might have negative value.
        """
        self.env.cr.execute('SELECT MAX(website_sequence) FROM %s' % self._table)
        max_sequence = self.env.cr.fetchone()[0]
        if max_sequence is None:
            return 10000
        return max_sequence + 5

    #=== FIELDS ===#

    website_description = fields.Html(
        string="Description for the website",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
    )
    description_ecommerce = fields.Html(
        string="eCommerce Description",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
    )

    alternative_product_ids = fields.Many2many(
        string="Alternative Products",
        comodel_name='product.template',
        relation='product_alternative_rel',
        column1='src_id', column2='dest_id',
        check_company=True,
        help="Suggest alternatives to your customer (upsell strategy)."
            " Those products show up on the product page.",
    )
    accessory_product_ids = fields.Many2many(
        string="Accessory Products",
        comodel_name='product.product',
        relation='product_accessory_rel',
        column1='src_id', column2='dest_id',
        check_company=True,
        help="Accessories show up when the customer reviews the cart before payment"
            " (cross-sell strategy).",
    )

    website_size_x = fields.Integer(string="Size X", default=1)
    website_size_y = fields.Integer(string="Size Y", default=1)
    website_ribbon_id = fields.Many2one(string="Ribbon", comodel_name='product.ribbon')
    website_sequence = fields.Integer(
        string="Website Sequence",
        help="Determine the display order in the Website E-commerce",
        default=_default_website_sequence,
        copy=False,
        index=True,
    )
    public_categ_ids = fields.Many2many(
        string="Website Product Category",
        help="The product will be available in each mentioned eCommerce category. Go to Shop > Edit"
             " Click on the page and enable 'Categories' to view all eCommerce categories.",
        comodel_name='product.public.category',
        relation='product_public_category_product_template_rel',
    )

    product_template_image_ids = fields.One2many(
        string="Extra Product Media",
        comodel_name='product.image',
        inverse_name='product_tmpl_id',
        copy=True,
    )

    base_unit_count = fields.Float(
        string="Base Unit Count",
        help="Display base unit price on your eCommerce pages. Set to 0 to hide it for this product.",
        compute='_compute_base_unit_count',
        inverse='_set_base_unit_count',
        store=True,
        required=True,
        default=0,
    )
    base_unit_id = fields.Many2one(
        string="Custom Unit of Measure",
        help="Define a custom unit to display in the price per unit of measure field.",
        comodel_name='website.base.unit',
        compute='_compute_base_unit_id',
        inverse='_set_base_unit_id',
        store=True,
    )
    base_unit_price = fields.Monetary(string="Price Per Unit", compute="_compute_base_unit_price")
    base_unit_name = fields.Char(
        compute='_compute_base_unit_name',
        help="Displays the custom unit for the products if defined or the selected unit of measure"
            " otherwise.",
    )

    compare_list_price = fields.Monetary(
        string="Compare to Price",
        help="Add a strikethrough price to your /shop and product pages for comparison purposes."
             "It will not be displayed if pricelists apply.",
    )

    #=== COMPUTE METHODS ===#

    @api.depends('product_variant_ids', 'product_variant_ids.base_unit_count')
    def _compute_base_unit_count(self):
        self.base_unit_count = 0
        for template in self.filtered(lambda template: len(template.product_variant_ids) == 1):
            template.base_unit_count = template.product_variant_ids.base_unit_count

    def _set_base_unit_count(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.base_unit_count = template.base_unit_count

    @api.depends('product_variant_ids', 'product_variant_ids.base_unit_count')
    def _compute_base_unit_id(self):
        self.base_unit_id = self.env['website.base.unit']
        for template in self.filtered(lambda template: len(template.product_variant_ids) == 1):
            template.base_unit_id = template.product_variant_ids.base_unit_id

    def _set_base_unit_id(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.base_unit_id = template.base_unit_id

    def _get_base_unit_price(self, price):
        self.ensure_one()
        return self.base_unit_count and price / self.base_unit_count

    @api.depends('list_price', 'base_unit_count')
    def _compute_base_unit_price(self):
        for template in self:
            template.base_unit_price = template._get_base_unit_price(template.list_price)

    @api.depends('uom_name', 'base_unit_id.name')
    def _compute_base_unit_name(self):
        for template in self:
            template.base_unit_name = template.base_unit_id.name or template.uom_name

    def _compute_website_url(self):
        super()._compute_website_url()
        for product in self:
            if product.id:
                product.website_url = "/shop/%s" % self.env['ir.http']._slug(product)

    #=== CRUD METHODS ===#

    def write(self, vals):
        # Clear empty ecommerce description content to avoid side-effects on product pages
        # when there is no content to display anyway.
        if (
            (description_ecommerce := vals.get('description_ecommerce'))
            and is_html_empty(description_ecommerce)
            and 'media_iframe_video' not in description_ecommerce  # don't remove "empty" video div
        ):
            vals['description_ecommerce'] = ''
        return super().write(vals)

    #=== BUSINESS METHODS ===#

    def _prepare_variant_values(self, combination):
        variant_dict = super()._prepare_variant_values(combination)
        variant_dict['base_unit_count'] = self.base_unit_count
        return variant_dict

    def _get_website_accessory_product(self):
        domain = self.env['website'].sale_product_domain()
        if not self.env.user._is_internal():
            domain = expression.AND([domain, [('is_published', '=', True)]])
        return self.accessory_product_ids.filtered_domain(domain)

    def _get_website_alternative_product(self):
        domain = self.env['website'].sale_product_domain()
        return self.alternative_product_ids.filtered_domain(domain)

    def _has_no_variant_attributes(self):
        """Return whether this `product.template` has at least one no_variant
        attribute.

        :return: True if at least one no_variant attribute, False otherwise
        :rtype: bool
        """
        self.ensure_one()
        return any(a.create_variant == 'no_variant' for a in self.valid_product_template_attribute_line_ids.attribute_id)

    def _has_is_custom_values(self):
        self.ensure_one()
        """Return whether this `product.template` has at least one is_custom
        attribute value.

        :return: True if at least one is_custom attribute value, False otherwise
        :rtype: bool
        """
        return any(v.is_custom for v in self.valid_product_template_attribute_line_ids.product_template_value_ids._only_active())

    def _get_possible_variants_sorted(self, parent_combination=None):
        """Return the sorted recordset of variants that are possible.

        The order is based on the order of the attributes and their values.

        See `_get_possible_variants` for the limitations of this method with
        dynamic or no_variant attributes, and also for a warning about
        performances.

        :param parent_combination: combination from which `self` is an
            optional or accessory product
        :type parent_combination: recordset `product.template.attribute.value`

        :return: the sorted variants that are possible
        :rtype: recordset of `product.product`
        """
        self.ensure_one()

        def _sort_key_attribute_value(value):
            # if you change this order, keep it in sync with _order from `product.attribute`
            return (value.attribute_id.sequence, value.attribute_id.id)

        def _sort_key_variant(variant):
            """
                We assume all variants will have the same attributes, with only one value for each.
                    - first level sort: same as "product.attribute"._order
                    - second level sort: same as "product.attribute.value"._order
            """
            keys = []
            for attribute in variant.product_template_attribute_value_ids.sorted(_sort_key_attribute_value):
                # if you change this order, keep it in sync with _order from `product.attribute.value`
                keys.append(attribute.product_attribute_value_id.sequence)
                keys.append(attribute.id)
            return keys

        return self._get_possible_variants(parent_combination).sorted(_sort_key_variant)

    def _get_sales_prices(self, website):
        if not self:
            return {}

        pricelist = website.pricelist_id
        currency = website.currency_id
        fiscal_position = website.fiscal_position_id.sudo()
        date = fields.Date.context_today(self)

        pricelist_prices = pricelist._compute_price_rule(self, 1.0)
        comparison_prices_enabled = self.env.user.has_group('website_sale.group_product_price_comparison')

        res = {}
        for template in self:
            pricelist_price, pricelist_rule_id = pricelist_prices[template.id]

            product_taxes = template.sudo().taxes_id._filter_taxes_by_company(self.env.company)
            taxes = fiscal_position.map_tax(product_taxes)

            base_price = None
            template_price_vals = {
                'price_reduce': self._apply_taxes_to_price(
                    pricelist_price, currency, product_taxes, taxes, template, website=website,
                ),
            }
            pricelist_item = template.env['product.pricelist.item'].browse(pricelist_rule_id)
            if pricelist_item._show_discount_on_shop():
                pricelist_base_price = pricelist_item._compute_price_before_discount(
                    product=template,
                    quantity=1.0,
                    date=date,
                    uom=template.uom_id,
                    currency=currency,
                )
                if currency.compare_amounts(pricelist_base_price, pricelist_price) == 1:
                    base_price = pricelist_base_price
                    template_price_vals['base_price'] = self._apply_taxes_to_price(
                        base_price, currency, product_taxes, taxes, template, website=website,
                    )

            if not base_price and comparison_prices_enabled and template.compare_list_price:
                template_price_vals['base_price'] = template.currency_id._convert(
                    template.compare_list_price,
                    currency,
                    self.env.company,
                    date,
                    round=False,
                )

            res[template.id] = template_price_vals

        return res

    def _can_be_added_to_cart(self):
        """
        Pre-check to `_is_add_to_cart_possible` to know if product can be sold.
        """
        return self.sale_ok

    def _is_add_to_cart_possible(self, parent_combination=None):
        """
        It's possible to add to cart (potentially after configuration) if
        there is at least one possible combination.

        :param parent_combination: the combination from which `self` is an
            optional or accessory product.
        :type parent_combination: recordset `product.template.attribute.value`

        :return: True if it's possible to add to cart, else False
        :rtype: bool
        """
        self.ensure_one()
        if not self.active or not self._can_be_added_to_cart():
            # for performance: avoid calling `_get_possible_combinations`
            return False
        return next(self._get_possible_combinations(parent_combination), False) is not False

    def _get_combination_info(
        self, combination=False, product_id=False, add_qty=1.0,
        parent_combination=False, only_template=False,
    ):
        """ Return info about a given combination.

        Note: this method does not take into account whether the combination is
        actually possible.

        :param combination: recordset of `product.template.attribute.value`

        :param int product_id: `product.product` id. If no `combination`
            is set, the method will try to load the variant `product_id` if
            it exists instead of finding a variant based on the combination.

            If there is no combination, that means we definitely want a
            variant and not something that will have no_variant set.

        :param float add_qty: the quantity for which to get the info,
            indeed some pricelist rules might depend on it.

        :param parent_combination: if no combination and no product_id are
            given, it will try to find the first possible combination, taking
            into account parent_combination (if set) for the exclusion rules.

        :param only_template: boolean, if set to True, get the info for the
            template only: ignore combination and don't try to find variant

        :return: dict with product/combination info:

            - product_id: the variant id matching the combination (if it exists)

            - product_template_id: the current template id

            - display_name: the name of the combination

            - price: the computed price of the combination, take the catalog
                price if no pricelist is given

            - price_extra: the computed extra price of the combination

            - list_price: the catalog price of the combination, but this is
                not the "real" list_price, it has price_extra included (so
                it's actually more closely related to `lst_price`), and it
                is converted to the pricelist currency (if given)

            - has_discounted_price: True if the pricelist discount policy says
                the price does not include the discount and there is actually a
                discount applied (price < list_price), else False
        """
        self.ensure_one()

        combination = combination or self.env['product.template.attribute.value']
        parent_combination = parent_combination or self.env['product.template.attribute.value']
        website = self.env['website'].get_current_website().with_context(self.env.context)

        if not product_id and not combination and not only_template:
            combination = self._get_first_possible_combination(parent_combination)

        if only_template:
            product = self.env['product.product']
        elif product_id:
            product = self.env['product.product'].browse(product_id)
            if (combination - product.product_template_attribute_value_ids):
                # If the combination is not fully represented in the given product
                #   make sure to fetch the right product for the given combination
                product = self._get_variant_for_combination(combination)
        else:
            product = self._get_variant_for_combination(combination)

        product_or_template = product or self
        combination = combination or product.product_template_attribute_value_ids

        display_name = product_or_template.with_context(display_default_code=False).display_name
        if not product:
            combination_name = combination._get_combination_name()
            if combination_name:
                display_name = f"{display_name} ({combination_name})"

        price_context = product_or_template._get_product_price_context(combination)
        product_or_template = product_or_template.with_context(**price_context)

        combination_info = {
            'combination': combination,
            'product_id': product.id,
            'product_template_id': self.id,
            'display_name': display_name,
            'display_image': bool(product_or_template.image_128),
            'is_combination_possible': self._is_combination_possible(combination=combination, parent_combination=parent_combination),
            'parent_exclusions': self._get_parent_attribute_exclusions(parent_combination=parent_combination),

            **self._get_additionnal_combination_info(
                product_or_template=product_or_template,
                quantity=add_qty or 1.0,
                date=fields.Date.context_today(self),
                website=website,
            )
        }

        if website.google_analytics_key:
            combination_info['product_tracking_info'] = self._get_google_analytics_data(
                product,
                combination_info,
            )

        if (
            product_or_template.type == 'combo'
            and website.show_line_subtotals_tax_selection == 'tax_included'
            and not all(
                tax.price_include
                for tax
                in product_or_template.combo_ids.sudo().combo_item_ids.product_id.taxes_id
            )
        ):
            combination_info['tax_disclaimer'] = _(
                "Final price may vary based on selection. Tax will be calculated at checkout."
            )

        return combination_info

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        """Computes additional combination info, based on given parameters

        :param product_or_template: `product.product` or `product.template` record
            as variant values must take precedence over template values (when we have a variant)
        :param float quantity:
        :param date date: today's date, avoids useless calls to today/context_today and harmonize
            behavior
        :param website: `website` record holding the current website of the request (if any),
            or the contextual website (tests, ...)
        :returns: additional product/template information
        :rtype: dict
        """
        pricelist = website.pricelist_id
        currency = website.currency_id

        # Pricelist price doesn't have to be converted
        pricelist_price, pricelist_rule_id = pricelist._get_product_price_rule(
            product=product_or_template,
            quantity=quantity,
            target_currency=currency,
        )

        price_before_discount = pricelist_price
        pricelist_item = self.env['product.pricelist.item'].browse(pricelist_rule_id)
        if pricelist_item._show_discount_on_shop():
            price_before_discount = pricelist_item._compute_price_before_discount(
                product=product_or_template,
                quantity=quantity or 1.0,
                date=date,
                uom=product_or_template.uom_id,
                currency=currency,
            )

        has_discounted_price = price_before_discount > pricelist_price
        combination_info = {
            'list_price': max(pricelist_price, price_before_discount),
            'price': pricelist_price,
            'has_discounted_price': has_discounted_price,
        }

        comparison_price = None
        if (
            not has_discounted_price
            and product_or_template.compare_list_price
            and self.env.user.has_group('website_sale.group_product_price_comparison')
        ):
            comparison_price = product_or_template.currency_id._convert(
                from_amount=product_or_template.compare_list_price,
                to_currency=currency,
                company=self.env.company,
                date=date,
                round=False)
        combination_info['compare_list_price'] = comparison_price

        combination_info['price_extra'] = product_or_template.currency_id._convert(
            from_amount=product_or_template._get_attributes_extra_price(),
            to_currency=currency,
            company=self.env.company,
            date=date,
            round=False,
        )

        # Apply taxes
        fiscal_position = website.fiscal_position_id.sudo()

        product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(self.env.company)
        taxes = self.env['account.tax']
        if product_taxes:
            taxes = fiscal_position.map_tax(product_taxes)
            # We do not apply taxes on the compare_list_price value because it's meant to be
            # a strict value displayed as is.
            for price_key in ('price', 'list_price', 'price_extra'):
                combination_info[price_key] = self._apply_taxes_to_price(
                    combination_info[price_key],
                    currency,
                    product_taxes,
                    taxes,
                    product_or_template,
                    website=website,
                )

        combination_info.update({
            'prevent_zero_price_sale': website.prevent_zero_price_sale and float_is_zero(
                combination_info['price'],
                precision_rounding=currency.rounding,
            ),

            'base_unit_name': product_or_template.base_unit_name,
            'base_unit_price': product_or_template._get_base_unit_price(combination_info['price']),

            # additional info to simplify overrides
            'currency': currency,  # displayed currency
            'date': date,
            'product_taxes': product_taxes,  # taxes before fpos mapping
            'taxes': taxes,  # taxes after fpos mapping
        })

        if combination_info['prevent_zero_price_sale']:
            combination_info['compare_list_price'] = 0

        return combination_info

    @api.model
    def _apply_taxes_to_price(
        self, price, currency, product_taxes, taxes, product_or_template,
        website=None,
    ):
        website = website or self.env['website'].get_current_website()
        price = self.env['product.product']._get_tax_included_unit_price_from_price(
            price,
            product_taxes,
            product_taxes_after_fp=taxes,
        )
        show_tax = website.show_line_subtotals_tax_selection
        tax_display = 'total_excluded' if show_tax == 'tax_excluded' else 'total_included'

        # The list_price is always the price of one.
        return taxes.compute_all(
            price, currency, 1, product_or_template, self.env.user.partner_id
        )[tax_display]

    def create_product_variant(self, product_template_attribute_value_ids):
        """ Create if necessary and possible and return the id of the product
        variant matching the given combination for this template.

        Note AWA: Known "exploit" issues with this method:

        - This method could be used by an unauthenticated user to generate a
            lot of useless variants. Unfortunately, after discussing the
            matter with ODO, there's no easy and user-friendly way to block
            that behavior.

            We would have to use captcha/server actions to clean/... that
            are all not user-friendly/overkill mechanisms.

        - This method could be used to try to guess what product variant ids
            are created in the system and what product template ids are
            configured as "dynamic", but that does not seem like a big deal.

        The error messages are identical on purpose to avoid giving too much
        information to a potential attacker:
            - returning 0 when failing
            - returning the variant id whether it already existed or not

        :param product_template_attribute_value_ids: the combination for which
            to get or create variant
        :type product_template_attribute_value_ids: list of id
            of `product.template.attribute.value`

        :return: id of the product variant matching the combination or 0
        :rtype: int
        """
        combination = self.env['product.template.attribute.value'].browse(
            product_template_attribute_value_ids)

        return self._create_product_variant(combination, log_warning=True).id or 0

    def _get_image_holder(self):
        """Returns the holder of the image to use as default representation.
        If the product template has an image it is the product template,
        otherwise if the product has variants it is the first variant

        :return: this product template or the first product variant
        :rtype: recordset of 'product.template' or recordset of 'product.product'
        """
        self.ensure_one()
        if self.image_128:
            return self
        variant = self.env['product.product'].browse(self._get_first_possible_variant_id())
        # if the variant has no image anyway, spare some queries by using template
        return variant if variant.image_variant_128 else self

    def _get_suitable_image_size(self, columns, x_size, y_size):
        if x_size == 1 and y_size == 1 and columns >= 3:
            return 'image_512'
        return 'image_1024'

    def _init_column(self, column_name):
        # to avoid generating a single default website_sequence when installing the module,
        # we need to set the default row by row for this column
        if column_name == "website_sequence":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row", self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE website_sequence IS NULL" % self._table)
            prod_tmpl_ids = self.env.cr.dictfetchall()
            max_seq = self._default_website_sequence()
            query = """
                UPDATE {table}
                SET website_sequence = p.web_seq
                FROM (VALUES %s) AS p(p_id, web_seq)
                WHERE id = p.p_id
            """.format(table=self._table)
            values_args = [(prod_tmpl['id'], max_seq + i * 5) for i, prod_tmpl in enumerate(prod_tmpl_ids)]
            self.env.cr.execute_values(query, values_args)
        else:
            super()._init_column(column_name)

    def set_sequence_top(self):
        min_sequence = self.sudo().search([], order='website_sequence ASC', limit=1)
        self.website_sequence = min_sequence.website_sequence - 5

    def set_sequence_bottom(self):
        max_sequence = self.sudo().search([], order='website_sequence DESC', limit=1)
        self.website_sequence = max_sequence.website_sequence + 5

    def set_sequence_up(self):
        previous_product_tmpl = self.sudo().search([
            ('website_sequence', '<', self.website_sequence),
            ('website_published', '=', self.website_published),
        ], order='website_sequence DESC', limit=1)
        if previous_product_tmpl:
            previous_product_tmpl.website_sequence, self.website_sequence = self.website_sequence, previous_product_tmpl.website_sequence
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_prodcut_tmpl = self.search([
            ('website_sequence', '>', self.website_sequence),
            ('website_published', '=', self.website_published),
        ], order='website_sequence ASC', limit=1)
        if next_prodcut_tmpl:
            next_prodcut_tmpl.website_sequence, self.website_sequence = self.website_sequence, next_prodcut_tmpl.website_sequence
        else:
            return self.set_sequence_bottom()

    def _default_website_meta(self):
        res = super()._default_website_meta()
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description_sale
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].image_url(self, 'image_1024')
        res['default_meta_description'] = self.description_sale
        return res

    @api.model
    def _get_alternative_product_filter(self):
        return self.env.ref('website_sale.dynamic_filter_cross_selling_alternative_products').id

    @api.model
    def _get_product_types_allow_zero_price(self):
        """
        Returns a list of service_tracking (`product.template.service_tracking`) that can ignore the
        `prevent_zero_price_sale` rule when buying products on a website.
        """
        return []

    # ---------------------------------------------------------
    # Rating Mixin API
    # ---------------------------------------------------------

    def _rating_domain(self):
        """ Only take the published rating into account to compute avg and count """
        domain = super()._rating_domain()
        return expression.AND([domain, [('is_internal', '=', False)]])

    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this template.

        This returns a list and not a recordset because the records might be
        from different models (template and image).

        It contains in this order: the main image of the template and the
        Template Extra Images.
        """
        self.ensure_one()
        return [self] + list(self.product_template_image_ids)

    def _get_attrib_values_domain(self, attribute_values):
        attribute_id = None
        attribute_value_ids = []
        domains = []
        for value in attribute_values:
            if not attribute_id:
                attribute_id = value[0]
                attribute_value_ids.append(value[1])
            elif value[0] == attribute_id:
                attribute_value_ids.append(value[1])
            else:
                domains.append([('attribute_line_ids.value_ids', 'in', attribute_value_ids)])
                attribute_id = value[0]
                attribute_value_ids = [value[1]]
        if attribute_id:
            domains.append([('attribute_line_ids.value_ids', 'in', attribute_value_ids)])
        return domains

    @api.model
    def _search_get_detail(self, website, order, options):
        with_image = options['displayImage']
        with_description = options['displayDescription']
        with_category = options['displayExtraLink']
        with_price = options['displayDetail']
        domains = [website.sale_product_domain()]
        category = options.get('category')
        tags = options.get('tags')
        min_price = options.get('min_price')
        max_price = options.get('max_price')
        attrib_values = options.get('attrib_values')
        if category:
            domains.append([('public_categ_ids', 'child_of', self.env['ir.http']._unslug(category)[1])])
        if tags:
            if isinstance(tags, str):
                tags = tags.split(',')
            domains.append([
                '|',
                ('product_tag_ids', 'in', tags),
                ('product_variant_ids.additional_product_tag_ids', 'in', tags),
            ])
        if min_price:
            domains.append([('list_price', '>=', min_price)])
        if max_price:
            domains.append([('list_price', '<=', max_price)])
        if attrib_values:
            domains.extend(self._get_attrib_values_domain(attrib_values))
        search_fields = ['name', 'default_code', 'product_variant_ids.default_code']
        fetch_fields = ['id', 'name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'default_code': {'name': 'default_code', 'type': 'text', 'match': True},
            'product_variant_ids.default_code': {'name': 'product_variant_ids.default_code', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }
        if with_image:
            mapping['image_url'] = {'name': 'image_url', 'type': 'html'}
        if with_description:
            # Internal note is not part of the rendering.
            search_fields.append('description')
            fetch_fields.append('description')
            search_fields.append('description_sale')
            fetch_fields.append('description_sale')
            mapping['description'] = {'name': 'description_sale', 'type': 'text', 'match': True}
        if with_price:
            mapping['detail'] = {'name': 'price', 'type': 'html', 'display_currency': options['display_currency']}
            mapping['detail_strike'] = {'name': 'list_price', 'type': 'html', 'display_currency': options['display_currency']}
        if with_category:
            mapping['extra_link'] = {'name': 'category', 'type': 'html'}
        return {
            'model': 'product.template',
            'base_domain': domains,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-shopping-cart',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        with_image = 'image_url' in mapping
        with_category = 'extra_link' in mapping
        with_price = 'detail' in mapping
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        current_website = self.env['website'].get_current_website()
        for product, data in zip(self, results_data):
            categ_ids = product.public_categ_ids.filtered(lambda c: not c.website_id or c.website_id == current_website)
            if with_price:
                combination_info = product._get_combination_info(only_template=True)
                data['price'], list_price = self._search_render_results_prices(
                    mapping, combination_info
                )
                if list_price:
                    data['list_price'] = list_price

            if with_image:
                data['image_url'] = '/web/image/product.template/%s/image_128' % data['id']
            if with_category and categ_ids:
                data['category'] = self.env['ir.ui.view'].sudo()._render_template(
                    "website_sale.product_category_extra_link",
                    {'categories': categ_ids, 'slug': self.env['ir.http']._slug}
                )
        return results_data

    def _search_render_results_prices(self, mapping, combination_info):
        if combination_info.get('prevent_zero_price_sale'):
            website = self.env['website'].get_current_website()
            return website.prevent_zero_price_sale_text, None

        monetary_options = {'display_currency': mapping['detail']['display_currency']}
        price = self.env['ir.qweb.field.monetary'].value_to_html(
            combination_info['price'], monetary_options
        )
        list_price = None
        if combination_info['has_discounted_price']:
            list_price = self.env['ir.qweb.field.monetary'].value_to_html(
                combination_info['list_price'], monetary_options
            )
        if combination_info['compare_list_price']:
            list_price = self.env['ir.qweb.field.monetary'].value_to_html(
                combination_info['compare_list_price'], monetary_options
            )

        return price, list_price

    def _get_google_analytics_data(self, product, combination_info):
        self.ensure_one()
        return {
            'item_id': product.barcode or product.id,
            'item_name': combination_info['display_name'],
            'item_category': self.categ_id.name,
            'currency': combination_info['currency'].name,
            'price': combination_info['list_price'],
        }

    def _get_contextual_pricelist(self):
        """ Override to fallback on website current pricelist """
        pricelist = super()._get_contextual_pricelist()
        if not pricelist:
            website = ir_http.get_request_website()
            if website:
                return website.pricelist_id
        return pricelist

    def _website_show_quick_add(self):
        self.ensure_one()
        # TODO VFE pass website as param and avoid existence check
        website = self.env['website'].get_current_website()
        return self.sale_ok and (not website.prevent_zero_price_sale or self._get_contextual_price())

    @api.model
    def _get_configurator_display_price(
        self, product_or_template, quantity, date, currency, pricelist, **kwargs
    ):
        """ Override of `sale` to apply taxes.

        :param product.product|product.template product_or_template: The product for which to get
            the price.
        :param int quantity: The quantity of the product.
        :param datetime date: The date to use to compute the price.
        :param res.currency currency: The currency to use to compute the price.
        :param product.pricelist pricelist: The pricelist to use to compute the price.
        :param dict kwargs: Locally unused data passed to `super`.
        :rtype: tuple(float, int or False)
        :return: The specified product's display price (and the applied pricelist rule)
        """
        price, pricelist_rule_id = super()._get_configurator_display_price(
            product_or_template, quantity, date, currency, pricelist, **kwargs
        )

        if website := ir_http.get_request_website():
            product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(
                self.env.company
            )
            if product_taxes:
                fiscal_position = website.fiscal_position_id.sudo()
                taxes = fiscal_position.map_tax(product_taxes)
                return self._apply_taxes_to_price(
                    price, currency, product_taxes, taxes, product_or_template, website=website
                ), pricelist_rule_id
        return price, pricelist_rule_id

    @api.model
    def _get_additional_configurator_data(
        self, product_or_template, date, currency, pricelist, **kwargs
    ):
        """ Override of `sale` to append tracking data.

        :param product.product|product.template product_or_template: The product for which to get
            additional data.
        :param datetime date: The date to use to compute prices.
        :param res.currency currency: The currency to use to compute prices.
        :param product.pricelist pricelist: The pricelist to use to compute prices.
        :param dict kwargs: Locally unused data passed to `super`.
        :rtype: dict
        :return: A dict containing additional data about the specified product.
        """
        data = super()._get_additional_configurator_data(
            product_or_template, date, currency, pricelist, **kwargs
        )

        if ir_http.get_request_website():
            data.update({
                # The following fields are needed for tracking.
                'category_name': product_or_template.categ_id.name,
                'currency_name': currency.name,
            })
        return data

    @api.model
    def _allow_publish_rating_stats(self):
        return True

    def _get_access_action(self, access_uid=None, force_website=False):
        """ Instead of the classic form view, redirect to website if it is published. """
        self.ensure_one()
        if force_website or (self.website_published and self.env.user.share):
            return {
                "type": "ir.actions.act_url",
                "url": self.website_url,
                "target": "self",
                "target_type": "public",
            }
        return super()._get_access_action(access_uid=access_uid, force_website=force_website)
