# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import gzip
import uuid

from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode, url_parse

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools import float_is_zero, float_round, urls

from odoo.addons.website_sale import const, utils


class ProductFeed(models.Model):
    _name = 'product.feed'
    _inherit = ['mail.thread']
    _description = "Product Feed"

    name = fields.Char(required=True)
    website_id = fields.Many2one('website', required=True)
    pricelist_id = fields.Many2one(
        'product.pricelist',
        help="Specify a pricelist to localize the feed with a specific currency."
        " If not set, the default website pricelist will be used."
        "\nNote that the pricelist must be selectable on the website.",
        domain="[('website_id', 'in', (False, website_id)), ('selectable', '=', True)]",
    )
    lang_id = fields.Many2one(
        'res.lang',
        string="Language",
        help="Select the language to translate product names, descriptions,"
        " and other text in the feed.",
        compute='_compute_lang_id',
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('id', 'in', website_lang_ids)]",
    )
    website_lang_ids = fields.Many2many(related='website_id.language_ids')
    product_category_ids = fields.Many2many('product.public.category', string="Categories")
    target = fields.Selection(
        selection=[
            ('gmc', "Google Merchant Center"),
        ],
        required=True,
        default='gmc',
    )
    access_token = fields.Char(
        readonly=True,
        required=True,
        default=lambda _: uuid.uuid4().hex,
        copy=False,
    )
    url = fields.Char(compute='_compute_url')

    last_notification_date = fields.Date()

    # Caching mechanism (technical fields)
    feed_cache = fields.Binary(compute='_compute_feed_cache', store=True, readonly=True)
    cache_expiry = fields.Datetime(readonly=True, required=True, default=fields.Datetime.now)

    @api.depends('target')
    def _compute_url(self):
        """Compute the full feed url."""
        for feed in self:
            match feed.target:
                case 'gmc':
                    path = '/gmc.xml'
                case _:
                    raise NotImplementedError

            feed.url = urls.urljoin(
                feed.website_id.get_base_url(),
                f'{path}?feed_id={feed.id}&access_token={feed.access_token}',
            )

    @api.depends('website_id')
    def _compute_lang_id(self):
        for feed in self.filtered(lambda f: not f.lang_id):
            feed.lang_id = feed.website_id.default_lang_id

    @api.depends(
        'website_id', 'pricelist_id', 'lang_id', 'product_category_ids'
    )
    def _compute_feed_cache(self):
        """Invalidate cache on feed parameter changes."""
        self.action_invalidate_cache()

    @api.constrains('product_category_ids', 'website_id')
    def _check_product_limit(self):
        """Add a soft limit on the number of products a feed can contain.

        A strong limit of 6000 is applied during the feed rendering phase.
        """
        for feed in self:
            product_count = feed.env['product.product'].search_count(
                feed._get_feed_product_domain(), limit=const.PRODUCT_FEED_SOFT_LIMIT + 1
            )
            if product_count > const.PRODUCT_FEED_SOFT_LIMIT:
                raise ValidationError(feed.env._(
                    "A single feed cannot contain more than %(limit)s products."
                    " Please separate products with Categories.",
                    limit=f"{const.PRODUCT_FEED_SOFT_LIMIT:,}",  # Format to 5,000
                ))

    def action_invalidate_cache(self):
        self.cache_expiry = fields.Datetime.now() - relativedelta(days=1)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._("Feed cache successfully reset."),
            },
        }

    def _render_and_cache_compressed_gmc_feed(self):
        """Render and cache the Google Merchant Center feed.

        This method ensures that the feed is rendered only once per day and caches the result. If
        the feed parameters change, the cache is invalidated, and the feed is re-rendered.

        :raises LockError: If the feed is already being rendered by another request.
        :return: The rendered feed compressed using gzip.
        :rtype: bytes
        """
        self.ensure_one()

        if not self.feed_cache or self.cache_expiry < fields.Datetime.now():
            # Lock the record to prevent concurrent rendering
            self.lock_for_update()
            gmc_xml = self._render_gmc_feed()
            compressed_gmc_xml = gzip.compress(gmc_xml.encode())
            # The binary field stores the data in the `datas` field of an `ir.attachment` which is a
            # base64 view of its `raw` data, therefore we encode the gzip content before saving it.
            self.feed_cache = base64.b64encode(compressed_gmc_xml)
            self.cache_expiry = fields.Datetime.today() + relativedelta(days=1)
            return compressed_gmc_xml  # Avoid encoding and directly decoding

        return base64.b64decode(self.feed_cache)

    def _render_gmc_feed(self):
        """Render the Google Merchant Center feed.

        See also https://support.google.com/merchants/answer/7052112 for the XML format.

        :return: The rendered XML feed.
        :rtype: str
        """
        self.ensure_one()
        # Set the language context for rendering.
        # Ensures all links, product names, descriptions, etc., are localized.
        self = self.with_context(lang=self.lang_id.code)  # noqa: PLW0642

        # Override the pricelist of the request to localize the currency and prices, otherwise, uses
        # the website default pricelist.
        if self.pricelist_id:
            request.pricelist = self.pricelist_id

        homepage_url = self.website_id.homepage_url or '/'
        website_homepage = self.website_id._get_website_pages(
            Domain([('url', '=', homepage_url), ('website_id', '!=', False)]), limit=1
        )

        gmc_data = {
            'title': website_homepage.website_meta_title or self.website_id.name,
            'link': urls.urljoin(
                self.website_id.get_base_url(),
                self.env['ir.http']._url_lang(homepage_url, lang_code=self.lang_id.code),
            ),
            'description': website_homepage.website_meta_description or self.website_id,
            'items': self._prepare_gmc_items(),
        }

        return self.env['ir.ui.view'].sudo()._render_template(
            'website_sale.gmc_xml', gmc_data,
        )

    def _prepare_gmc_items(self):
        """Prepare Google Merchant Center items' fields.

        See Google's (https://support.google.com/merchants/answer/7052112) documentation for more
        information about each field.

        :return: a dictionary for each product in this recordset.
        :rtype: list[dict]
        """
        products = self._get_feed_products()
        base_url = self.website_id.get_base_url()

        def format_product_link(url_):
            if self.pricelist_id:
                parsed_url = url_parse(url_)
                query = parsed_url.decode_query()
                query['pricelist'] = self.pricelist_id.id
                url_ = parsed_url._replace(query=url_encode(query)).to_url()
            return urls.urljoin(
                base_url, self.env['ir.http']._url_lang(url_, lang_code=self.lang_id.code)
            )

        return {
            product: {
                'id': product.default_code or product.id,
                'title': product.with_context(display_default_code=False).display_name,
                'description': product.website_meta_description or product.description_sale,
                'link': format_product_link(product.website_url),
                **self._prepare_gmc_identifier(product),
                **self._prepare_gmc_image_links(product, base_url),
                **price_info,
                **self._prepare_gmc_stock_info(product),
                **self._prepare_gmc_additional_info(product),
            }
            for product in products
            if product._is_variant_possible()
            and (price_info := self._prepare_gmc_price_info(product))
        }

    def _get_feed_product_domain(self):
        product_domain = self.website_id._get_basic_feed_product_domain()
        if self.product_category_ids:
            product_domain &= Domain('public_categ_ids', 'child_of', self.product_category_ids.ids)

        return product_domain

    def _get_feed_products(self):
        product_domain = self._get_feed_product_domain()

        products = self.env['product.product'].search(
            product_domain, limit=const.PRODUCT_FEED_HARD_LIMIT
        )

        # Send an early warning to the website manager if the number of products exceeds the
        # midpoint between the soft and hard limit.
        if len(products) > (const.PRODUCT_FEED_SOFT_LIMIT + const.PRODUCT_FEED_HARD_LIMIT) / 2:
            today = fields.Date.today()
            if (
                not self.last_notification_date
                or relativedelta(today, self.last_notification_date).weeks > 0
            ):
                self._notify_website_manager(
                    subject=self.env._("GMC: Product Limit Exceeded"),
                    body=self.env._(
                        "The feed %(feed_name)s contains more than %(limit)s products,"
                        " which may not be fully updated. Consider refining the feed by adjusting"
                        " the product categories.",
                        feed_name=self.display_name,
                        limit=f"{const.PRODUCT_FEED_SOFT_LIMIT:,}",  # Format to 5,000
                    ),
                )
                self.last_notification_date = today

        return products

    def _prepare_gmc_identifier(self, product):
        """Prepare the product identifiers for Google Merchant Center.

        :return: The barcode of the product as GTIN
        :rtype: dict
        """
        if product.barcode:
            return {'gtin': product.barcode, 'identifier_exists': 'yes'}
        return {'identifier_exists': 'no'}

    def _prepare_gmc_image_links(self, product, base_url):
        """Prepare the product image links for Google Merchant Center.

        :return: The main product image link, and the extra images. No videos.
        :rtype: dict
        """
        return {
            # Don't send any image link if there isn't. Google does not allow placeholder
            'image_link': (
                urls.urljoin(base_url, product._get_image_1920_url()) if product.image_128 else ''
            ),
            # Supports up to 10 extra images
            'additional_image_link': [
                urls.urljoin(base_url, url) for url in product._get_extra_image_1920_urls()[:10]
            ],
        }

    def _prepare_gmc_price_info(self, product):
        """Prepare price-related information for Google Merchant Center.

        Note: If the product is flagged to prevent zero price sales, an empty dictionary is
        returned.

        :return: A dictionary containing nothing if the product is "prevent zero price sale", or:
            - List price,
            - Sale price (if applicable), and
            - Comparison prices (e.g., $100 / ml) if "Product Reference Price" is enabled.
        :rtype: dict
        """
        price_context = product._get_product_price_context(
            product.product_template_attribute_value_ids
        )
        combination_info = product.with_context(
            **price_context,
        ).product_tmpl_id._get_additionnal_combination_info(
            product,
            quantity=1.0,
            uom=product.uom_id,
            date=fields.Date.context_today(self),
            website=self.website_id,
        )
        if combination_info['prevent_zero_price_sale']:
            return {}

        price_info = {
            'price': utils.gmc_format_price(
                combination_info['list_price'], combination_info['currency'],
            ),
        }

        if combination_info['has_discounted_price']:
            price_info['sale_price'] = utils.gmc_format_price(
                combination_info['price'], combination_info['currency'],
            )
            start_date = combination_info['discount_start_date']
            end_date = combination_info['discount_end_date']
            if start_date and end_date:
                price_info['sale_price_effective_date'] = '/'.join(
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
            and product.base_unit_count
            and (match := const.GMC_BASE_MEASURE.match(
                combination_info['base_unit_name'].strip().lower()
            ))
        ):
            base_count, base_unit = match['base_count'] or '1', match['base_unit']
            count = product.base_unit_count * int(base_count)
            if (
                base_unit in const.GMC_SUPPORTED_UOM
                and not float_is_zero(count, precision_digits=2)
            ):
                price_info['unit_pricing_measure'] = (
                    f'{float_round(count, precision_digits=2)}{base_unit}'
                )
                price_info['unit_pricing_base_measure'] = f'{base_count}{base_unit}'

        return price_info

    def _prepare_gmc_stock_info(self, _product):
        """Intended to be overridden in stock."""
        return {'availability': 'in_stock'}

    def _prepare_gmc_additional_info(self, product):
        additional_info = {
            'product_detail': [
                (attr.attribute_id.name, attr.name)
                for attr in product.product_template_attribute_value_ids
            ],
            'is_bundle': 'yes' if product.type == 'combo' else 'no',
            'product_type': [
                category.replace('/', '>')  # Google uses a different format
                for category in (
                    # Up to 5 categories
                    product.public_categ_ids.sorted('sequence').mapped('display_name')[:5]
                )
            ],
            'custom_label': [
                (f'custom_label_{i}', tag_name)
                for i, tag_name in enumerate(
                    # Supports up to 5 custom labels
                    product.all_product_tag_ids.sorted('sequence').mapped('name')[:5]
                )
            ],
        }

        # Link variants together
        if len(product.product_tmpl_id.product_variant_ids) > 1:
            additional_info['item_group_id'] = product.product_tmpl_id.id

        return additional_info

    def _notify_website_manager(self, **kwargs):
        """Send a notification to the website manager using OdooBot.

        This method wraps around `message_notify` to notify the manager of the feed's website.

        :param dict kwargs: Additional arguments passed to `message_notify`.
        :return: The created `mail.message` record.
        :rtype: mail.message
        """
        return self.with_user(SUPERUSER_ID).message_notify(
            partner_ids=self.website_id.salesperson_id.partner_id.ids, **kwargs
        )
