# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website.models import ir_http
from odoo.tools.translate import html_translate
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = [
        "product.template",
        "website.seo.metadata",
        'website.published.multi.mixin',
        'website.searchable.mixin',
        'rating.mixin',
    ]
    _name = 'product.template'
    _mail_post_access = 'read'
    _check_company_auto = True

    website_description = fields.Html(
        'Description for the website', translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False, sanitize_form=False)
    alternative_product_ids = fields.Many2many(
        'product.template', 'product_alternative_rel', 'src_id', 'dest_id', check_company=True,
        string='Alternative Products', help='Suggest alternatives to your customer (upsell strategy). '
                                            'Those products show up on the product page.')
    accessory_product_ids = fields.Many2many(
        'product.product', 'product_accessory_rel', 'src_id', 'dest_id', string='Accessory Products', check_company=True,
        help='Accessories show up when the customer reviews the cart before payment (cross-sell strategy).')
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_ribbon_id = fields.Many2one('product.ribbon', string='Ribbon')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=lambda self: self._default_website_sequence(), copy=False)
    public_categ_ids = fields.Many2many(
        'product.public.category', relation='product_public_category_product_template_rel',
        string='Website Product Category',
        help="The product will be available in each mentioned eCommerce category. Go to Shop > Edit "
             "Click on the page and enable 'Categories' to view all eCommerce categories.")

    product_template_image_ids = fields.One2many('product.image', 'product_tmpl_id', string="Extra Product Media", copy=True)

    base_unit_count = fields.Float('Base Unit Count', required=True, default=0,
                                   compute='_compute_base_unit_count', inverse='_set_base_unit_count', store=True,
                                   help="Display base unit price on your eCommerce pages. Set to 0 to hide it for this product.")
    base_unit_id = fields.Many2one('website.base.unit', string='Custom Unit of Measure',
                                   compute='_compute_base_unit_id', inverse='_set_base_unit_id', store=True,
                                   help="Define a custom unit to display in the price per unit of measure field.")
    base_unit_price = fields.Monetary("Price Per Unit", currency_field="currency_id", compute="_compute_base_unit_price")
    base_unit_name = fields.Char(compute='_compute_base_unit_name', help='Displays the custom unit for the products if defined or the selected unit of measure otherwise.')

    compare_list_price = fields.Float(
        'Compare to Price',
        digits='Product Price',
        help="The amount will be displayed strikethroughed on the eCommerce product page")

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

    @api.depends('list_price', 'base_unit_count')
    def _compute_base_unit_price(self):
        for template in self:
            template.base_unit_price = template.base_unit_count and template.list_price / template.base_unit_count

    @api.depends('uom_name', 'base_unit_id.name')
    def _compute_base_unit_name(self):
        for template in self:
            template.base_unit_name = template.base_unit_id.name or template.uom_name

    def _prepare_variant_values(self, combination):
        variant_dict = super()._prepare_variant_values(combination)
        variant_dict['base_unit_count'] = self.base_unit_count
        return variant_dict

    def _get_website_accessory_product(self):
        domain = self.env['website'].sale_product_domain()
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

    def _get_sales_prices(self, pricelist):
        pricelist.ensure_one()
        partner_sudo = self.env.user.partner_id

        # Try to fetch geoip based fpos or fallback on partner one
        fpos_id = self.env['website']._get_current_fiscal_position_id(partner_sudo)
        fiscal_position = self.env['account.fiscal.position'].sudo().browse(fpos_id)

        sales_prices = pricelist._get_products_price(self, 1.0)
        show_discount = pricelist.discount_policy == 'without_discount'

        base_sales_prices = self.price_compute('list_price', currency=pricelist.currency_id)

        res = {}
        for template in self:
            price_reduce = sales_prices[template.id]

            product_taxes = template.sudo().taxes_id.filtered(lambda t: t.company_id == t.env.company)
            taxes = fiscal_position.map_tax(product_taxes)

            price_reduce = self.env['account.tax']._fix_tax_included_price_company(
                price_reduce, product_taxes, taxes, self.env.company)

            tax_display = self.user_has_groups('account.group_show_line_subtotals_tax_excluded') and 'total_excluded' or 'total_included'
            price_reduce = taxes.compute_all(price_reduce, pricelist.currency_id, 1, template, partner_sudo)[tax_display]

            template_price_vals = {
                'price_reduce': price_reduce
            }
            base_price = None
            price_list_contains_template = price_reduce != base_sales_prices[template.id]

            if template.compare_list_price:
                # The base_price becomes the compare list price and the price_reduce becomes the price
                base_price = template.compare_list_price
                if not price_list_contains_template:
                    price_reduce = base_sales_prices[template.id]
                    template_price_vals.update(price_reduce=price_reduce)
            elif show_discount and price_list_contains_template:
                base_price = base_sales_prices[template.id]

            if base_price and base_price != price_reduce:
                base_price = self.env['account.tax']._fix_tax_included_price_company(
                    base_price, product_taxes, taxes, self.env.company)
                base_price = taxes.compute_all(base_price, pricelist.currency_id, 1, template, partner_sudo)[
                    tax_display]
                template_price_vals['base_price'] = base_price

            res[template.id] = template_price_vals

        return res

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False):
        """Override for website, where we want to:
            - take the website pricelist if no pricelist is set
            - apply the b2b/b2c setting to the result

        This will work when adding website_id to the context, which is done
        automatically when called from routes with website=True.
        """
        self.ensure_one()

        current_website = False

        if self.env.context.get('website_id'):
            current_website = self.env['website'].get_current_website()
            if not pricelist:
                pricelist = current_website.get_current_pricelist()

        combination_info = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template)

        if self.env.context.get('website_id'):
            product = self.env['product.product'].browse(combination_info['product_id']) or self
            partner = self.env.user.partner_id
            company_id = current_website.company_id

            fpos = self.env['account.fiscal.position'].sudo()._get_fiscal_position(partner)
            product_taxes = product.sudo().taxes_id.filtered(lambda x: x.company_id == company_id)
            taxes = fpos.map_tax(product_taxes)

            price = self._price_with_tax_computed(
                combination_info['price'], product_taxes, taxes, company_id, pricelist, product,
                partner
            )
            if pricelist.discount_policy == 'without_discount':
                list_price = self._price_with_tax_computed(
                    combination_info['list_price'], product_taxes, taxes, company_id, pricelist,
                    product, partner
                )
            else:
                list_price = price
            price_extra = self._price_with_tax_computed(
                combination_info['price_extra'], product_taxes, taxes, company_id, pricelist,
                product, partner
            )
            has_discounted_price = pricelist.currency_id.compare_amounts(list_price, price) == 1
            prevent_zero_price_sale = not price and current_website.prevent_zero_price_sale
            combination_info.update(
                base_unit_name=product.base_unit_name,
                base_unit_price=product.base_unit_price,
                price=price,
                list_price=list_price,
                price_extra=price_extra,
                has_discounted_price=has_discounted_price,
                prevent_zero_price_sale=prevent_zero_price_sale,
            )

        return combination_info

    def _price_with_tax_computed(
        self, price, product_taxes, taxes, company_id, pricelist, product, partner
    ):
        price = self.env['account.tax']._fix_tax_included_price_company(
            price, product_taxes, taxes, company_id
        )
        show_tax_excluded = self.user_has_groups('account.group_show_line_subtotals_tax_excluded')
        tax_display = 'total_excluded' if show_tax_excluded else 'total_included'
        # The list_price is always the price of one.
        return taxes.compute_all(price, pricelist.currency_id, 1, product, partner)[tax_display]

    def _create_first_product_variant(self, log_warning=False):
        """Create if necessary and possible and return the first product
        variant for this template.

        :param log_warning: whether a warning should be logged on fail
        :type log_warning: bool

        :return: the first product variant or none
        :rtype: recordset of `product.product`
        """
        return self._create_product_variant(self._get_first_possible_combination(), log_warning)

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


    def _get_current_company_fallback(self, **kwargs):
        """Override: if a website is set on the product or given, fallback to
        the company of the website. Otherwise use the one from parent method."""
        res = super(ProductTemplate, self)._get_current_company_fallback(**kwargs)
        website = self.website_id or kwargs.get('website')
        return website and website.company_id or res

    def _default_website_sequence(self):
        ''' We want new product to be the last (highest seq).
        Every product should ideally have an unique sequence.
        Default sequence (10000) should only be used for DB first product.
        As we don't resequence the whole tree (as `sequence` does), this field
        might have negative value.
        '''
        self._cr.execute("SELECT MAX(website_sequence) FROM %s" % self._table)
        max_sequence = self._cr.fetchone()[0]
        if max_sequence is None:
            return 10000
        return max_sequence + 5

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
        res = super(ProductTemplate, self)._default_website_meta()
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description_sale
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].image_url(self, 'image_1024')
        res['default_meta_description'] = self.description_sale
        return res

    def _compute_website_url(self):
        super(ProductTemplate, self)._compute_website_url()
        for product in self:
            if product.id:
                product.website_url = "/shop/%s" % slug(product)


    def _get_website_ribbon(self):
        if self.website_ribbon_id:
            return self.website_ribbon_id
        return self.product_tag_ids.ribbon_id[:1] or self.product_variant_ids.additional_product_tag_ids.ribbon_id[:1]

    @api.model
    def _get_alternative_product_filter(self):
        return self.env.ref('website_sale.dynamic_filter_cross_selling_alternative_products').id

    # ---------------------------------------------------------
    # Rating Mixin API
    # ---------------------------------------------------------

    def _rating_domain(self):
        """ Only take the published rating into account to compute avg and count """
        domain = super(ProductTemplate, self)._rating_domain()
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

    @api.model
    def _search_get_detail(self, website, order, options):
        with_image = options['displayImage']
        with_description = options['displayDescription']
        with_category = options['displayExtraLink']
        with_price = options['displayDetail']
        domains = [website.sale_product_domain()]
        category = options.get('category')
        min_price = options.get('min_price')
        max_price = options.get('max_price')
        attrib_values = options.get('attrib_values')
        if category:
            domains.append([('public_categ_ids', 'child_of', unslug(category)[1])])
        if min_price:
            domains.append([('list_price', '>=', min_price)])
        if max_price:
            domains.append([('list_price', '<=', max_price)])
        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domains.append([('attribute_line_ids.value_ids', 'in', ids)])
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domains.append([('attribute_line_ids.value_ids', 'in', ids)])
        search_fields = ['name', 'product_variant_ids.default_code']
        fetch_fields = ['id', 'name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
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
                    {'categories': categ_ids, 'slug': slug}
                )
        return results_data

    def _search_render_results_prices(self, mapping, combination_info):
        monetary_options = {'display_currency': mapping['detail']['display_currency']}
        if combination_info['prevent_zero_price_sale']:
            website = self.env['website'].get_current_website()
            price = website.prevent_zero_price_sale_text
        else:
            price = self.env['ir.qweb.field.monetary'].value_to_html(
                combination_info['price'], monetary_options
            )
        if combination_info['has_discounted_price']:
            list_price = self.env['ir.qweb.field.monetary'].value_to_html(
                combination_info['list_price'], monetary_options
            )

        return price, list_price if combination_info['has_discounted_price'] else None

    @api.model
    def get_google_analytics_data(self, combination):
        product = self.env['product.product'].browse(combination['product_id'])
        return {
            'item_id': product.barcode or product.id,
            'item_name': combination['display_name'],
            'item_category': product.categ_id.name or '-',
            'currency': product.currency_id.name,
            'price': combination['list_price'],
        }

    def _get_contextual_pricelist(self):
        """ Override to fallback on website current pricelist
        """
        pricelist = super()._get_contextual_pricelist()
        if pricelist:
            return pricelist
        website = ir_http.get_request_website()
        if website:
            return website.get_current_pricelist()
        return pricelist

    def _website_show_quick_add(self):
        website = self.env['website'].get_current_website()
        return self.sale_ok and (not website.prevent_zero_price_sale or self._get_contextual_price())
