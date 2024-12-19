# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from urllib.parse import urljoin
from pytz import UTC

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import lazy

GMC_SUPPORTED_UOM = {
    'oz',
    'lb',
    'mg',
    'g',
    'kg',
    'floz',
    'pt',
    'qt',
    'gal',
    'ml',
    'cl',
    'l',
    'cbm',
    'in',
    'ft',
    'yd',
    'cm',
    'm',
    'sqft',
    'sqm',
}


class ProductProduct(models.Model):
    _inherit = 'product.product'

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
    # === COMPUTE METHODS ===#
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
    # === CONSTRAINT METHODS ===#
    @api.constrains('base_unit_count')
    def _check_base_unit_count(self):
        if any(product.base_unit_count < 0 for product in self):
            raise ValidationError(_(
                "The value of Base Unit Count must be greater than 0."
                " Use 0 to hide the price per unit on this product."
            ))
    # === BUSINESS METHODS ===#
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

    def _get_image_link(self, website_id=None):
        self.ensure_one()
        website_id = website_id or self.website_id
        return website_id.image_url(self, 'image_1920')

    def _get_extra_image_links(self, website_id=None):
        self.ensure_one()
        website_id = website_id or self.website_id
        return [
            website_id.image_url(extra_image, 'image_1920')
            for extra_image in self.product_variant_image_ids + self.product_template_image_ids
            if extra_image.image_1920  # only images, no video urls
        ]

    def _get_gmc_items(self):
        """Compute Google Merchant Center items' fields.

        See [Google](https://support.google.com/merchants/answer/7052112)'s documentation for more
        information about each field.

        :return: a dictionary for each non-service product in this recordset.
        :rtype: list[dict]
        """
        dict_items = super()._get_gmc_items()

        if not (request and request.website.domain):
            raise ValidationError(
                _(
                    "No domain set for this website. Please consider adding a domain name for your "
                    "website in the settings."
                )
            )

        pricelist_id = request.website.pricelist_id.id
        currency = request.website.currency_id
        IrHttp = request.env['ir.http']
        base_url = request.website.get_base_url()

        def format_link(url):
            return urljoin(base_url, IrHttp._url_lang(url))

        def format_product_link(url):
            return format_link(f'/shop/change_pricelist/{pricelist_id}?r={url}')

        def format_price(price):
            return f"{currency.round(price)} {currency.name}"

        def format_date(dt):
            return UTC.localize(dt).isoformat(timespec='minutes')

        delivery_carriers = (
            self.env['delivery.carrier'].sudo().search([('is_published', '=', True)])
        )
        all_countries = lazy(lambda: self.env['res.country'].search([]))
        dummy_partner = self.env['res.partner'].new({})
        dummy_order = self.env['sale.order'].new({
            'partner_id': dummy_partner.id,
            'pricelist_id': request.website.pricelist_id,
            'order_line': [{'product_uom_qty': 1.0}],
        })
        order_line = dummy_order.order_line[0]
        for product, items in dict_items.items():
            combination_info = product.product_tmpl_id._get_combination_info(
                combination=product.product_template_attribute_value_ids,
            )
            if not combination_info['is_combination_possible']:
                continue
            # Compute best shipping service for each country this product can ship to
            order_line.product_id = product
            best_carrier_by_country = defaultdict(lambda: (float('inf'), None))
            best_free_shipping_threshold = defaultdict(lambda: float('inf'))
            for carrier in delivery_carriers:
                for country in carrier.country_ids or all_countries:
                    dummy_partner.country_id = country
                    if not carrier._is_available_for_order(dummy_order):
                        continue
                    shipment_rate = carrier.rate_shipment(dummy_order)
                    if not shipment_rate['success']:
                        continue
                    best_carrier_by_country[country] = min(
                        best_carrier_by_country[country], (shipment_rate['price'], carrier)
                    )
                    if carrier.free_over:
                        best_free_shipping_threshold[country] = min(
                            best_free_shipping_threshold[country],
                            carrier.amount,
                        )
            items.update({
                # Required
                'description': product.description_ecommerce or "",
                'link': format_product_link(product.website_url),
                'image_link': (
                    # don't send any image link if there isn't. Google does not allow placeholder
                    format_link(product._get_image_link())
                    if product.image_1920
                    else ""
                ),
                'price': format_price(combination_info['list_price']),
                'identifier_exists': "no",
                'shipping': [
                    {
                        'country': country.code,
                        'service': carrier.name,
                        'price': format_price(best_price),
                    }
                    for country, (best_price, carrier) in best_carrier_by_country.items()
                ],
                # Optional
                'product_detail': [
                    (attr.attribute_id.name, attr.name)
                    for attr in product.product_template_attribute_value_ids
                ],
                'is_bundle': "yes" if product.type == 'combo' else "no",
                'additionnal_image_link': [
                    format_link(link)
                    # supports up to 10 extra images
                    for link in product._get_extra_image_links()[:10]
                ],
                'product_type': [
                    category.replace('/', '>')  # google uses a different format
                    for i, category in zip(
                        range(5),  # up to 5 categories
                        product.public_categ_ids.sorted('sequence').mapped('display_name'),
                    )
                ],
                'custom_label': [
                    (f'custom_label_{i}', tag_name)
                    for i, tag_name in zip(
                        range(5),  # supports up to 5 custom labels
                        product.all_product_tag_ids.sorted('sequence').mapped('name'),
                    )
                ],
                'free_shipping_threshold': [
                    {
                        'country': country.code,
                        'price_threshold': format_price(best_threshold),
                    }
                    for country, best_threshold in best_free_shipping_threshold.items()
                ],
            })
            # prefer barcode over record id
            if product.barcode:
                items.update({'gtin': product.barcode, 'identifier_exists': "yes"})
            # link variants together
            if len(product.product_tmpl_id.product_variant_ids) > 1:
                items['item_group_id'] = product.product_tmpl_id.id
            # sales/promo/discount/etc.
            if combination_info['has_discounted_price']:
                items['sale_price'] = format_price(combination_info['price'])
                effective_date = combination_info['discounted_price_effective_date']
                if all(effective_date):  # if there is start and end date
                    items['sale_price_effective_date'] = "/".join(map(format_date, effective_date))
            # ex: $100 / 125ml
            # note: google only supports a restricted set of unit, plus it is required
            # that the base unit count is an integer. Therefore, we exclude non-integer
            # `base_unit_count`. ex: $2 / 1.5l != $2 / 1l
            if (
                'base_unit_name' in combination_info
                and product.base_unit_count is not False
                and product.base_unit_count.is_integer()
                and combination_info['base_unit_name'] in GMC_SUPPORTED_UOM
            ):
                items['unit_pricing_measure'] = (
                    f"{int(product.base_unit_count)}{combination_info['base_unit_name']}"
                )

        return dict_items
