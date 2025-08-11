# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urljoin, urlparse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import float_is_zero, float_round

from odoo.addons.website_sale import const, utils


class ProductProduct(models.Model):
    _inherit = 'product.product'
    _mail_post_access = 'read'

    variant_ribbon_id = fields.Many2one(string="Variant Ribbon", comodel_name='product.ribbon')
    website_id = fields.Many2one(related='product_tmpl_id.website_id', readonly=False)

    product_variant_image_ids = fields.One2many(
        string="Extra Variant Images",
        comodel_name='product.image',
        inverse_name='product_variant_id',
    )

    base_unit_count = fields.Float(
        string="Base Unit Count",
        help="Display base unit price on your eCommerce pages. Set to 0 to hide it for this"
             " product.",
        required=True,
        default=1,
    )
    base_unit_id = fields.Many2one(
        string="Custom Unit of Measure",
        help="Define a custom unit to display in the price per unit of measure field.",
        comodel_name='website.base.unit',
    )
    base_unit_price = fields.Monetary(
        string="Price Per Unit",
        compute='_compute_base_unit_price',
    )
    base_unit_name = fields.Char(
        help="Displays the custom unit for the products if defined or the selected unit of measure"
            " otherwise.",
        compute='_compute_base_unit_name',
    )

    website_url = fields.Char(
        string="Website URL",
        help="The full URL to access the document through the website.",
        compute='_compute_product_website_url',
    )

    #=== COMPUTE METHODS ===#

    def _get_base_unit_price(self, price):
        self.ensure_one()
        return self.base_unit_count and price / self.base_unit_count

    @api.depends('lst_price', 'base_unit_count')
    def _compute_base_unit_price(self):
        for product in self:
            if not product.id:
                product.base_unit_price = 0
            else:
                product.base_unit_price = product._get_base_unit_price(product.lst_price)

    @api.depends('uom_name', 'base_unit_id')
    def _compute_base_unit_name(self):
        for product in self:
            product.base_unit_name = product.base_unit_id.name or product.uom_name

    @api.depends_context('lang')
    @api.depends('product_tmpl_id.website_url', 'product_template_attribute_value_ids')
    def _compute_product_website_url(self):
        for product in self:
            url = product.product_tmpl_id.website_url
            if pavs := product.product_template_attribute_value_ids.product_attribute_value_id:
                pav_ids = [str(pav.id) for pav in pavs]
                url = f'{url}#attribute_values={",".join(pav_ids)}'
            product.website_url = url

    #=== CONSTRAINT METHODS ===#

    @api.constrains('base_unit_count')
    def _check_base_unit_count(self):
        if any(product.base_unit_count < 0 for product in self):
            raise ValidationError(_(
                "The value of Base Unit Count must be greater than 0."
                " Use 0 to hide the price per unit on this product."
            ))

    #=== BUSINESS METHODS ===#

    def _prepare_variant_values(self, combination):
        variant_dict = super()._prepare_variant_values(combination)
        variant_dict['base_unit_count'] = self.base_unit_count
        return variant_dict

    def website_publish_button(self):
        self.ensure_one()
        return self.product_tmpl_id.website_publish_button()

    def open_website_url(self):
        self.ensure_one()
        res = self.product_tmpl_id.open_website_url()
        res['url'] = self.website_url
        return res

    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this variant.

        This returns a list and not a recordset because the records might be
        from different models (template, variant and image).

        It contains in this order: the main image of the variant (which will fall back on the main
        image of the template, if unset), the Variant Extra Images, and the Template Extra Images.
        """
        self.ensure_one()
        variant_images = list(self.product_variant_image_ids)
        template_images = list(self.product_tmpl_id.product_template_image_ids)
        return [self] + variant_images + template_images

    def _get_combination_info_variant(self, **kwargs):
        """Return the variant info based on its combination.
        See `_get_combination_info` for more information.
        """
        self.ensure_one()
        return self.product_tmpl_id._get_combination_info(
            combination=self.product_template_attribute_value_ids,
            product_id=self.id,
            **kwargs)

    def _website_show_quick_add(self):
        self.ensure_one()
        if not self.filtered_domain(self.env['website']._product_domain()):
            return False
        return not request.website.prevent_zero_price_sale or self._get_contextual_price()

    def _is_add_to_cart_allowed(self):
        self.ensure_one()
        if self.env.user.has_group('base.group_system'):
            return True
        if not self.active or not self.website_published:
            return False
        if not self.filtered_domain(self.env['website']._product_domain()):
            return False
        return request.website.has_ecommerce_access()

    @api.onchange('public_categ_ids')
    def _onchange_public_categ_ids(self):
        if self.public_categ_ids:
            self.website_published = True
        else:
            self.website_published = False

    def _to_markup_data(self, website):
        """ Generate JSON-LD markup data for the current product.

        :param website website: The current website.
        :return: The JSON-LD markup data.
        :rtype: dict
        """
        self.ensure_one()

        base_url = website.get_base_url()
        markup_data = {
            '@context': 'https://schema.org',
            '@type': 'Product',
            'name': self.with_context(display_default_code=False).display_name,
            'url': f'{base_url}{self.website_url}',
            'image': f'{base_url}{website.image_url(self, "image_1920")}',
            'offers': {
                '@type': 'Offer',
                'price': float_round(request.pricelist._get_product_price(
                    self, quantity=1, target_currency=website.currency_id
                ), 2),
                'priceCurrency': website.currency_id.name,
            },
        }
        if self.website_meta_description or self.description_sale:
            markup_data['description'] = self.website_meta_description or self.description_sale
        if website.is_view_active('website_sale.product_comment') and self.rating_count:
            markup_data['aggregateRating'] = {
                '@type': 'AggregateRating',
                # sudo: product.product - visitor can access product average rating
                'ratingValue': self.sudo().rating_avg,
                'reviewCount': self.rating_count,
            }
        return markup_data

    def _get_image_1920_url(self):
        """ Returns the local url of the product main image.

        Note: self.ensure_one()

        :rtype: str
        """
        self.ensure_one()
        return self.env['website'].image_url(self, 'image_1920')

    def _get_extra_image_1920_urls(self):
        """ Returns the local url of the product additional images, no videos. This includes the
        variant specific images first and then the template images.

        Note: self.ensure_one()

        :rtype: list[str]
        """
        self.ensure_one()
        return [
            self.env['website'].image_url(extra_image, 'image_1920')
            for extra_image in self.product_variant_image_ids + self.product_template_image_ids
            if extra_image.image_1920  # only images, no video urls
        ]

    def _prepare_gmc_items(self):
        """ Prepare Google Merchant Center items' fields.

        See Google's (https://support.google.com/merchants/answer/7052112) documentation for more
        information about each field.

        Note: Depends on:
            - `request.pricelist` to compute price and shipping informations,
            - `request.website` to compute links, and
            - `request.lang` to compute text based information (name, description, etc.) and links

        :return: a dictionary for each product in this recordset.
        :rtype: list[dict]
        """
        self = self.with_context(lang=request.lang.code)
        base_url = request.website.get_base_url()

        def format_product_link(url_):
            url_ = urlparse(url_)._replace(query=f'pricelist={request.pricelist.id}').geturl()
            return urljoin(base_url, self.env['ir.http']._url_lang(url_))

        delivery_methods_sudo = self.env['delivery.carrier'].sudo().search(
            [('is_published', '=', True), ('website_id', 'in', (request.website.id, False))],
        )
        all_countries = self.env['res.country'].search([])

        return {
            product: {
                'id': product.default_code or product.id,
                'title': product.with_context(display_default_code=False).display_name,
                'description': product.website_meta_description or product.description_sale,
                'link': format_product_link(product.website_url),
                **product._prepare_gmc_identifier(),
                **product._prepare_gmc_image_links(base_url),
                **price_info,
                **product._prepare_gmc_shipping_info(delivery_methods_sudo, all_countries),
                **product._prepare_gmc_stock_info(),
                **product._prepare_gmc_additional_info(),
            }
            for product in self
            if product._is_variant_possible() and (price_info := product._prepare_gmc_price_info())
        }

    def _prepare_gmc_identifier(self):
        """ Prepare the product identifiers for Google Merchant Center.

        :return: The barcode of the product as GTIN
        :rtype: dict
        """
        self.ensure_one()
        if self.barcode:
            return {'gtin': self.barcode, 'identifier_exists': 'yes'}
        return {'identifier_exists': 'no'}

    def _prepare_gmc_image_links(self, base_url):
        """ Prepare the product image links for Google Merchant Center.

        :return: The main product image link, and the extra images. No videos.
        :rtype: dict
        """
        self.ensure_one()
        return {
            # Don't send any image link if there isn't. Google does not allow placeholder
            'image_link': urljoin(base_url, self._get_image_1920_url()) if self.image_128 else '',
            # Supports up to 10 extra images
            'additional_image_link': [
                urljoin(base_url, url) for url in self._get_extra_image_1920_urls()[:10]
            ],
        }

    def _prepare_gmc_price_info(self):
        """ Prepare all the price related information for Google Merchant Center.

        :return:
            - list price
            - sale price if one exists and can be shown
            - comparison prices if "Product Reference Price" is enabled (ex: $100 / ml)

        :rtype: dict
        """
        self.ensure_one()
        price_context = self._get_product_price_context(self.product_template_attribute_value_ids)
        combination_info = self.with_context(
            **price_context,
        ).product_tmpl_id._get_additionnal_combination_info(
            self, 1.0, fields.Date.context_today(self), request.website,
        )
        if combination_info['prevent_zero_price_sale']:
            return {}

        gmc_info = {
            'price': utils.gmc_format_price(
                combination_info['list_price'], combination_info['currency'],
            ),
        }
        # sales/promo/discount/etc.
        if combination_info['has_discounted_price']:
            gmc_info['sale_price'] = utils.gmc_format_price(
                combination_info['price'], combination_info['currency'],
            )
            start_date = combination_info['discount_start_date']
            end_date = combination_info['discount_end_date']
            if start_date and end_date:
                gmc_info['sale_price_effective_date'] = '/'.join(
                    map(utils.gmc_format_date, (start_date, end_date)),
                )

        # Note: Google only supports a restricted set of unit and computes the comparison prices
        # differently than Odoo.
        # Ex: product="Pack of wine (6 bottles)", price=$65.00, uom_name="Pack".
        #   - in odoo: base_unit_count=6.0, base_unit_name="750ml"
        #       => displayed: "$10.83 / 750ml"
        #   - in google: unit_pricing_measure="4500ml", unit_pricing_base_measure="750ml"
        #       => displayed: "$10.83 / 750ml"
        if (
            combination_info.get('base_unit_name')
            and self.base_unit_count
            and (match := const.GMC_BASE_MEASURE.match(
                combination_info['base_unit_name'].strip().lower()
            ))
        ):
            base_count, base_unit = match['base_count'] or '1', match['base_unit']
            count = self.base_unit_count * int(base_count)
            if (
                base_unit in const.GMC_SUPPORTED_UOM
                and not float_is_zero(count, precision_digits=2)
            ):
                gmc_info['unit_pricing_measure'] = (
                    f'{float_round(count, precision_digits=2)}{base_unit}'
                )
                gmc_info['unit_pricing_base_measure'] = f'{base_count}{base_unit}'

        return gmc_info

    def _prepare_gmc_shipping_info(self, delivery_methods_sudo, countries):
        """ Computes the best shipping method info per country. This includes, per country:

        - the best price for which the product can be shipped to the country,
        - the best delivery method name shipping the product for the price,
        - if possible, the best free shipping threshold (not necessarily the same as the "best
          delivery method"),

        Note: Google limits shipping information to 100 countries.
        """
        self.ensure_one()
        best_delivery_by_country = list(delivery_methods_sudo._prepare_best_delivery_by_country(
            self, request.pricelist, countries,
        ).items())
        return {
            'shipping': [
                {
                    'country': country.code,
                    'service': delivery['delivery_method'].name,
                    'price': utils.gmc_format_price(delivery['price'], delivery['currency']),
                }
                for country, delivery in best_delivery_by_country[:100]
            ],
            'free_shipping_threshold': [
                {
                    'country': country.code,
                    'price_threshold': utils.gmc_format_price(
                        delivery['free_over_threshold'], delivery['currency'],
                    ),
                }
                for country, delivery in best_delivery_by_country
                if 'free_over_threshold' in delivery
            ][:100],  # Apply the limit after looping to include as many results as possible.
        }

    def _prepare_gmc_stock_info(self):
        """ Intended to be overridden in stock """
        self.ensure_one()
        return {'availability': 'in_stock'}

    def _prepare_gmc_additional_info(self):
        self.ensure_one()
        gmc_info = {
            'product_detail': [
                (attr.attribute_id.name, attr.name)
                for attr in self.product_template_attribute_value_ids
            ],
            'is_bundle': 'yes' if self.type == 'combo' else 'no',
            'product_type': [
                category.replace('/', '>')  # google uses a different format
                for category in (
                    # up to 5 categories
                    self.public_categ_ids.sorted('sequence').mapped('display_name')[:5]
                )
            ],
            'custom_label': [
                (f'custom_label_{i}', tag_name)
                for i, tag_name in enumerate(
                    # supports up to 5 custom labels
                    self.all_product_tag_ids.sorted('sequence').mapped('name')[:5]
                )
            ],
        }

        # link variants together
        if len(self.product_tmpl_id.product_variant_ids) > 1:
            gmc_info['item_group_id'] = self.product_tmpl_id.id

        return gmc_info

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            # unlink draft lines containing the archived product
            self.env['sale.order.line'].sudo().search([
                ('state', '=', 'draft'),
                ('product_id', 'in', self.ids),
                ('order_id', 'any', [('website_id', '!=', False)]),
            ]).unlink()
        return super().write(vals)
