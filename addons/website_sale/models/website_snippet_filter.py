# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter

from odoo import _, api, fields, models
from odoo.osv import expression


class WebsiteSnippetFilter(models.Model):
    _inherit = ['website.snippet.filter']

    product_cross_selling = fields.Boolean(
        string="About cross selling products",
        help="True only for product filters that require a product_id because they relate to"
            " cross selling",
    )

    def _prepare_values(self, **kwargs):
        website = self.env['website'].get_current_website()
        if self.model_name == 'product.product' and not website.has_ecommerce_access():
            return []
        hide_variants = False
        search_domain = kwargs.get('search_domain')
        if self.filter_id and search_domain and 'hide_variants' in search_domain:
            hide_variants = True
            search_domain.remove('hide_variants')
            kwargs['search_domain'] = search_domain
        return super(
            WebsiteSnippetFilter,
            self.with_context(hide_variants=hide_variants),
        )._prepare_values(**kwargs)

    @api.model
    def _get_website_currency(self):
        website = self.env['website'].get_current_website()
        return website.currency_id

    def _get_hardcoded_sample(self, model):
        samples = super()._get_hardcoded_sample(model)
        if model._name == 'product.product':
            data = [{
                'image_512': b'/product/static/img/product_chair.jpg',
                'display_name': _("Chair"),
                'description_sale': _("Sit comfortably"),
            }, {
                'image_512': b'/product/static/img/product_lamp.png',
                'display_name': _("Lamp"),
                'description_sale': _("Lightbulb sold separately"),
            }, {
                'image_512': b'/product/static/img/product_product_20-image.png',
                'display_name': _("Whiteboard"),
                'description_sale': _("With three feet"),
            }, {
                'image_512': b'/product/static/img/product_product_27-image.jpg',
                'display_name': _("Drawer"),
                'description_sale': _("On wheels"),
            }, {
                'image_512': b'/product/static/img/product_product_7-image.png',
                'display_name': _("Box"),
                'description_sale': _("Reinforced for heavy loads"),
            }, {
                'image_512': b'/product/static/img/product_product_9-image.jpg',
                'display_name': _("Bin"),
                'description_sale': _("Pedal-based opening system"),
            }]
            merged = []
            for index in range(max(len(samples), len(data))):
                merged.append({**samples[index % len(samples)], **data[index % len(data)]})
                # merge definitions
            samples = merged
        return samples

    def _filter_records_to_values(self, records, is_sample=False):
        hide_variants = self.env.context.get('hide_variants') and not isinstance(records, list)
        if hide_variants:
            records = records.product_tmpl_id
        res_products = super()._filter_records_to_values(records, is_sample)
        if self.model_name == 'product.product':
            for res_product in res_products:
                product = res_product.get('_record')
                if not is_sample:
                    if hide_variants and not product.has_configurable_attributes:
                        # Still display a product.product if the template is not configurable
                        res_product['_record'] = product = product.product_variant_id

                    # TODO VFE combination_info is only called to get the price here
                    # factorize and avoid computing the rest
                    if product.is_product_variant:
                        res_product.update(product._get_combination_info_variant())
                    else:
                        res_product.update(product._get_combination_info())

                    if records.env.context.get('add2cart_rerender'):
                        res_product['_add2cart_rerender'] = True
                else:
                    res_product.update({
                        'is_sample': True,
                    })
        return res_products

    @api.model
    def _get_products(self, mode, **kwargs):
        dynamic_filter = self.env.context.get('dynamic_filter')
        handler = getattr(self, '_get_products_%s' % mode, self._get_products_latest_sold)
        website = self.env['website'].get_current_website()
        search_domain = self.env.context.get('search_domain')
        limit = self.env.context.get('limit')
        hide_variants = False
        if search_domain and 'hide_variants' in search_domain:
            hide_variants = True
            search_domain.remove('hide_variants')
        domain = expression.AND([
            [('website_published', '=', True)] if self.env.user._is_public() or self.env.user._is_portal() else [],
            website.website_domain(),
            [('company_id', 'in', [False, website.company_id.id])],
            search_domain or [],
        ])
        products = handler(website, limit, domain, **kwargs)
        return dynamic_filter.with_context(
            hide_variants=hide_variants,
        )._filter_records_to_values(products, is_sample=False)

    def _get_products_latest_sold(self, website, limit, domain, **kwargs):
        products = self.env['product.product']
        sale_orders = self.env['sale.order'].sudo().search([
            ('website_id', '=', website.id),
            ('state', '=', 'sale'),
        ], limit=8, order='date_order DESC')
        if sale_orders:
            sold_products = [p.product_id.id for p in sale_orders.order_line]
            products_ids = [id for id, _ in Counter(sold_products).most_common()]
            if products_ids:
                domain = expression.AND([
                    domain,
                    [('id', 'in', products_ids)],
                ])
                products = self.env['product.product'].with_context(
                    display_default_code=False,
                ).search(domain)
                products = products.sorted(key=lambda p: products_ids.index(p.id))[:limit]
        return products

    def _get_products_latest_viewed(self, website, limit, domain, **kwargs):
        products = self.env['product.product']
        visitor = self.env['website.visitor']._get_visitor_from_request()
        if visitor:
            excluded_products = website.sale_get_order().order_line.product_id.ids
            tracked_products = self.env['website.track'].sudo()._read_group([
                ('visitor_id', '=', visitor.id),
                ('product_id', '!=', False),
                ('product_id.website_published', '=', True),
                ('product_id', 'not in', excluded_products),
            ], ['product_id'], limit=limit, order='visit_datetime:max DESC')
            products_ids = [product.id for [product] in tracked_products]
            if products_ids:
                domain = expression.AND([
                    domain,
                    [('id', 'in', products_ids)],
                ])
                products = self.env['product.product'].with_context(
                    display_default_code=False,
                    add2cart_rerender=True,
                ).search(domain, limit=limit)
        return products

    def _get_products_recently_sold_with(
        self, website, limit, domain, product_template_id, **kwargs,
    ):
        products = self.env['product.product']
        current_template = self.env['product.template'].browse(
            product_template_id and int(product_template_id)
        ).exists()
        if current_template:
            sale_orders = self.env['sale.order'].sudo().search([
                ('website_id', '=', website.id),
                ('state', '=', 'sale'),
                ('order_line.product_id.product_tmpl_id', '=', current_template.id),
            ], limit=8, order='date_order DESC')
            if sale_orders:
                excluded_products = website.sale_get_order().order_line.product_id.product_tmpl_id.product_variant_ids.ids
                excluded_products.extend(current_template.product_variant_ids.ids)
                included_products = []
                for sale_order in sale_orders:
                    included_products.extend(sale_order.order_line.product_id.ids)
                products_ids = list(set(included_products) - set(excluded_products))
                if products_ids:
                    domain = expression.AND([
                        domain,
                        [('id', 'in', products_ids)],
                    ])
                    products = self.env['product.product'].with_context(
                        display_default_code=False,
                    ).search(domain, limit=limit)
        return products

    def _get_products_accessories(self, website, limit, domain, product_template_id=None, **kwargs):
        products = self.env['product.product']
        current_template = self.env['product.template'].browse(
            product_template_id and int(product_template_id)
        ).exists()
        if current_template:
            excluded_products = website.sale_get_order().order_line.product_id.ids
            excluded_products.extend(current_template.product_variant_ids.ids)
            included_products = current_template._get_website_accessory_product().ids
            products_ids = list(set(included_products) - set(excluded_products))
            if products_ids:
                domain = expression.AND([
                    domain,
                    [('id', 'in', products_ids)],
                ])
                products = self.env['product.product'].with_context(
                    display_default_code=False,
                ).search(domain, limit=limit)
        return products

    def _get_products_alternative_products(
        self, website, limit, domain, product_template_id=None, **kwargs,
    ):
        products = self.env['product.product']
        current_template = self.env['product.template'].browse(
            product_template_id and int(product_template_id)
        ).exists()
        if current_template:
            excluded_products = website.sale_get_order().order_line.product_id
            excluded_products |= current_template.product_variant_ids
            included_products = current_template.alternative_product_ids.product_variant_ids
            products = included_products - excluded_products
            if website.prevent_zero_price_sale:
                products = products.filtered(lambda p: p._get_contextual_price())
            if products:
                domain = expression.AND([
                    domain,
                    [('id', 'in', products.ids)],
                ])
                products = self.env['product.product'].with_context(
                    display_default_code=False,
                ).search(domain, limit=limit)
        return products
