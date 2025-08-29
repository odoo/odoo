# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import float_is_zero, float_round
from odoo.tools.urls import urljoin as url_join

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

    def _prepare_gmc_items(self):
        return self._prepare_feed_items(format='gmc')

    def _prepare_meta_items(self):
        return self._prepare_feed_items(format='meta')

    def _prepare_feed_items(self, format='gmc'):
        """
        Shared feed item builder for supported platforms:
            - `gmc`: https://support.google.com/merchants/answer/7052112
            - `meta`: https://www.facebook.com/business/help/120325381656392?id=725943027795860
        Note: Depends on:
            - `request.pricelist` to compute price and shipping informations,
            - `request.website` to compute links, and
            - `request.lang` to compute text based information (name, description, etc.) and links
        :return: a dictionary for each product in this recordset.
        :rtype: dict[product.product, dict]
        """
        records = self.with_context(lang=request.lang.code)
        base_url = request.website.get_base_url()
        delivery_methods = self._get_published_delivery_methods()
        all_countries = self.env['res.country'].search([])

        def build_item(product):
            if not (
                product._is_variant_possible()
                and (price_info := product._prepare_price_info(format=format))
            ):
                return None  # Skip products with no price info
            return {
                **product._prepare_feed_item_common(base_url),
                **product._prepare_feed_additional_info(format=format),
                **price_info,
                **product._prepare_feed_shipping_info(
                    delivery_methods, all_countries,
                ),
            }

        return {product: item for product in records if (item := build_item(product))}

    @api.model
    def _get_published_delivery_methods(self):
        return request.env['delivery.carrier'].sudo().search(
            [('is_published', '=', True), ('website_id', 'in', (request.website.id, False))],
        )

    def _prepare_feed_item_common(self, base_url):
        self.ensure_one()
        pricelist_url = f'pricelist={request.pricelist.id}' if request.pricelist.id else ''
        formatted_url = urlparse(self.website_url)._replace(query=pricelist_url).geturl()
        product_url = url_join(base_url, self.env['ir.http']._url_lang(formatted_url))

        info = {
            'id': self.default_code or self.id,
            'title': self.with_context(display_default_code=False).display_name,
            'description': self.website_meta_description or self.description_sale,
            'link': product_url,
            # Don't send any image link if there isn't. Google does not allow placeholder
            'image_link': url_join(base_url, self._get_image_1920_url()) if self.image_1920 else '',
            # Supports up to 10 extra images
            'additional_image_link': [
                url_join(base_url, url) for url in self._get_extra_image_1920_urls()[:10]
            ],
            'product_type': [
                category.replace('/', '>')  # Both platforms use > for hierarchy
                for category in (
                    # up to 5 categories
                    self.public_categ_ids.sorted('sequence').mapped('display_name')[:5]
                )
            ],
            'product_detail': [
                (attr.attribute_id.name, attr.name)
                for attr in self.product_template_attribute_value_ids
            ],
        }

        if len(self.product_tmpl_id.product_variant_ids) > 1:
            info['item_group_id'] = self.product_tmpl_id.id

        if self.barcode:
            info['identifier_exists'] = 'yes'
            info['gtin'] = self.barcode
        else:
            info['identifier_exists'] = 'no'

        return info

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
            if extra_image.image_128  # only images, no video urls
        ]

    def _prepare_feed_additional_info(self, format='gmc'):
        self.ensure_one()

        match format:
            case 'gmc':
                return {
                    'is_bundle': 'yes' if self.type == 'combo' else 'no',
                    'availability': 'in_stock',
                    'custom_label': [
                        (f'custom_label_{i}', tag_name)
                        for i, tag_name in enumerate(
                            # supports up to 5 custom labels
                            self.all_product_tag_ids.sorted('sequence').mapped('name')[:5],
                        )
                    ],
                }
            case 'meta':
                return {
                    'internal_label': [
                        tag.name.lower().strip().replace(' ', '_')
                        for tag in self.all_product_tag_ids
                    ],
                    'availability': 'in stock',
                }

    def _prepare_price_info(self, format='google'):
        """ Prepare all the price related information for XML Feeds.
        :param format: 'google' or 'meta'
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
            self,
            quantity=1.0,
            uom=self.uom_id,
            date=fields.Date.context_today(self),
            website=request.website,
        )
        if combination_info['prevent_zero_price_sale']:
            return {}

        price_info = {
            'price': utils.product_feed_format_price(
                combination_info['list_price'], combination_info['currency'],
            ),
        }
        # sales/promo/discount/etc.
        if combination_info['has_discounted_price']:
            price_info['sale_price'] = utils.product_feed_format_price(
                combination_info['price'], combination_info['currency'],
            )
            start_date = combination_info['discount_start_date']
            end_date = combination_info['discount_end_date']
            if start_date and end_date:
                price_info['sale_price_effective_date'] = utils.format_sale_price_effective_date(
                    start_date, end_date
                )

        # Note: Google and Meta only supports a restricted set of unit and computes
        # the comparison prices differently than Odoo.
        # Ex: product="Pack of wine (6 bottles)", price=$65.00, uom_name="Pack".
        #   - in odoo: base_unit_count=6.0, base_unit_name="750ml"
        #       => displayed: "$10.83 / 750ml"
        #   - in google/meta: unit_pricing_measure="4500ml", unit_pricing_base_measure="750ml"
        #       => displayed: "$10.83 / 750ml"

        base_unit_name = combination_info.get('base_unit_name')
        if base_unit_name and self.base_unit_count:
            unit_name = base_unit_name.strip().lower()
            match = const.BASE_MEASURE.match(unit_name)

            if match:
                base_count = int(match['base_count'] or '1')
                base_unit = match['base_unit']
                count = self.base_unit_count * base_count

                if (
                    not float_is_zero(count, precision_digits=2)
                    and base_unit in const.PRODUCT_FEED_SUPPORTED_UOM
                ):
                    if format == 'meta':
                        price_per_unit = combination_info['price'] / count
                        price_info['unit_price'] = {
                            'value': float_round(price_per_unit, precision_digits=2),
                            'currency': combination_info['currency'].name,
                            'unit': base_unit,
                        }
                    else:
                        price_info['unit_pricing_measure'] = (
                            f'{float_round(count, precision_digits=2)}{base_unit}'
                        )
                        price_info['unit_pricing_base_measure'] = f'{base_count}{base_unit}'

        return price_info

    def _prepare_feed_shipping_info(self, delivery_methods, countries):
        """
        Prepare GMC/Meta-compliant shipping info for XML feeds.
        GMC:
        - the best price for which the product can be shipped to the country,
        - the best delivery method name shipping the product for the price,
        - if possible, the best free shipping threshold (not necessarily the same as the "best
          delivery method"),
        META:
        - 'country' is the 2-letter ISO country code.
        - 'region' is the state/region code if available, else empty.
        - 'price' is formatted as "amount currency".
        - 'service' is left empty since Odoo doesn't define service types like "Ground"/"Air".
        :return: a dictionary containing a list of shipping lines for the product.
        :rtype: dict
        .. note::
            - Google/Meta limits shipping information to 100 countries.
        """
        self.ensure_one()
        best_delivery_by_country = delivery_methods._prepare_best_delivery_by_country(
            self, request.pricelist, countries,
        )

        return {
            'shipping': [
                {
                    'country': country.code,
                    'region': state.code if state else '',
                    'service': delivery['delivery_method'].name,
                    'price': utils.product_feed_format_price(
                        delivery['price'], delivery['currency'],
                    ),
                }
                for country, delivery in best_delivery_by_country.items()
                for state in delivery['states'] or [None]
            ][:100],
            'free_shipping_threshold': [
                {
                    'country': country.code,
                    'price_threshold': utils.product_feed_format_price(
                        delivery['free_over_threshold'],
                        delivery['currency'],
                    ),
                }
                for country, delivery in best_delivery_by_country.items()
                if 'free_over_threshold' in delivery
            ][:100],
        }

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            # unlink draft lines containing the archived product
            self.env['sale.order.line'].sudo().search([
                ('state', '=', 'draft'),
                ('product_id', 'in', self.ids),
                ('order_id', 'any', [('website_id', '!=', False)]),
            ]).unlink()
        return super().write(vals)
