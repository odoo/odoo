# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from functools import partial

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.http import request


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    product_cross_selling = fields.Boolean(
        string="About cross selling products",
        help="True only for product filters that require a product_id because they relate to"
            " cross selling",
    )

    def _prepare_values(self, limit=None, search_domain=None, **kwargs):
        website = self.env['website'].get_current_website()
        if (
            (self.model_name or kwargs.get('res_model')) in ('product.product', 'product.public.category')
            and not website.has_ecommerce_access()
        ):
            return []
        hide_variants = False
        if search_domain and 'hide_variants' in search_domain:
            hide_variants = True
            search_domain.remove('hide_variants')
        update_limit_cache = False
        product_limit = limit or self.limit
        if hide_variants and self.filter_id.model_id == 'product.product':
            # When hiding variants, temporarily update cache to increase `self.limit`
            # so we hopefully end up with the correct amount of product templates
            update_limit_cache = partial(
                self.env.cache.set,
                record=self,
                field=self._fields['limit'],
            )
            limit = product_limit ** 2  # heuristic, may still be inadequate in some cases
            stored_limit = self.limit
            update_limit_cache(value=limit)
        res = super(
            WebsiteSnippetFilter,
            self.with_context(hide_variants=hide_variants, product_limit=product_limit),
        )._prepare_values(limit=limit, search_domain=search_domain, **kwargs)
        if update_limit_cache:
            update_limit_cache(value=stored_limit)
        return res

    @api.model
    def _get_website_currency(self):
        website = self.env['website'].get_current_website()
        return website.currency_id

    def _get_hardcoded_sample(self, model):
        samples = super()._get_hardcoded_sample(model)

        def merge_samples_with_data(data_):
            return [
                {**samples[i % len(samples)], **data_[i % len(data_)]}
                for i in range(max(len(samples), len(data_)))
            ]
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
            samples = merge_samples_with_data(data)
        elif model._name == 'product.public.category':
            data = [{
                'id': 1,
                'cover_image': b'/website_sale/static/src/img/categories/desks.jpg',
                'name': _("Desks"),
            }, {
                'id': 2,
                'cover_image': b'/website_sale/static/src/img/categories/furnitures.jpg',
                'name': _("Furnitures"),
            }, {
                'id': 3,
                'cover_image': b'/website_sale/static/src/img/categories/boxes.jpg',
                'name': _("Boxes"),
            }, {
                'id': 4,
                'cover_image': b'/website_sale/static/src/img/categories/drawers.jpg',
                'name': _("Drawers"),
            }]
            samples = merge_samples_with_data(data)
        return samples

    def _filter_records_to_values(self, records, **options):
        hide_variants = self.env.context.get('hide_variants') and not isinstance(records, list)
        if hide_variants:
            product_limit = self.env.context.get('product_limit') or self.limit
            records = records.product_tmpl_id[:product_limit]
        res_products = super()._filter_records_to_values(records, **options)
        if (self.model_name or options.get('res_model')) == 'product.product':
            for res_product in res_products:
                product = res_product.get('_record')
                if not options.get('is_sample'):
                    if hide_variants and not product.has_configurable_attributes:
                        # Still display a product.product if the template is not configurable
                        res_product['_record'] = product = product.product_variant_id

                    # TODO VFE combination_info is only called to get the price here
                    # factorize and avoid computing the rest
                    if product.is_product_variant:
                        res_product.update(product._get_combination_info_variant())
                    elif hide_variants:
                        res_product.update(product._get_combination_info(only_template=True))
                        # Re-add product_id since it is set to false and required by some tests
                        res_product['product_id'] = product.product_variant_id.id
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
    def _prepare_category_list_data(self, parent_id=None):
        """Return a list of categories to be displayed in the category list snippet.
        If `parent_id` is provided, return it with its children, otherwise top-level categories.

        :param int parent_id: ID of the parent category, if any.
        :return: List of dictionaries containing category ID, name, and cover image URL.
        :rtype: list[dict]
        """
        CategorySudo = request.env['product.public.category'].sudo()
        domain = CategorySudo._get_available_category_domain(request.website.id)
        if parent_id:
            parent_category = CategorySudo.browse(parent_id)
            # Parent category should be first.
            categories = parent_category | parent_category.child_id.filtered_domain(domain)
        else:  # Only top-level categories
            categories = CategorySudo.search(domain & Domain('parent_id', '=', False))

        base_url = CategorySudo.get_base_url()
        default_img_path = request.env['product.template']._get_product_placeholder_filename()
        default_img_url = f'{base_url}/{default_img_path}'
        return [{
            'id': cat.id,
            'name': cat.name,
            'unpublished': not cat.has_published_products,
            'cover_image': (
                f'{base_url}{request.website.image_url(cat, "cover_image")}'
                if cat.cover_image else default_img_url
            ),
        } for cat in categories]

    @api.model
    def _get_products(self, mode, **kwargs):
        dynamic_filter = self.env.context.get('dynamic_filter')
        handler = getattr(self, '_get_products_%s' % mode, self._get_products_latest_sold)
        website = self.env['website'].get_current_website()
        search_domain = self.env.context.get('search_domain')
        limit = self.env.context.get('limit')
        hide_variants = self.env.context.get('hide_variants')
        domain = Domain.AND([
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
            ('company_id', '=', website.company_id.id),
            ('state', '=', 'sale'),
        ], limit=8, order='date_order DESC')
        if sale_orders:
            if self.env.context.get('hide_variants'):
                sold_products = Counter(
                    sol.product_id.product_tmpl_id.product_variant_id
                    for sol in sale_orders.order_line
                )
            else:
                sold_products = Counter(sol.product_id for sol in sale_orders.order_line)
            if sold_products:
                domain = Domain(domain) & Domain('id', 'in', [p.id for p, _ in sold_products.most_common(limit)])
                products = self.env['product.product'].with_context(
                    display_default_code=False,
                ).search(domain, limit=limit)
                products = products.sorted(key=sold_products.get, reverse=True)
        return products

    def _get_products_latest_viewed(self, website, limit, domain, **kwargs):
        products = self.env['product.product']
        visitor = self.env['website.visitor']._get_visitor_from_request()
        if visitor:
            excluded_products = request.cart.order_line.product_id.ids
            tracked_products = self.env['website.track'].sudo()._read_group([
                ('visitor_id', '=', visitor.id),
                ('product_id', '!=', False),
                ('product_id.website_published', '=', True),
                ('product_id', 'not in', excluded_products),
            ], ['product_id'], limit=limit, order='visit_datetime:max DESC')
            if self.env.context.get('hide_variants'):
                product_ids = [
                    product.product_tmpl_id.product_variant_id.id
                    for [product] in tracked_products
                ]
            else:
                product_ids = [product.id for [product] in tracked_products]
            if product_ids:
                domain = Domain(domain) & Domain('id', 'in', product_ids)
                filtered_ids = set(self.env['product.product']._search(domain, limit=limit))
                # `search` will not keep the order of tracked products; however, we want to keep
                # that order (latest viewed first).
                products = self.env['product.product'].with_context(
                    display_default_code=False, add2cart_rerender=True,
                ).browse([product_id for product_id in product_ids if product_id in filtered_ids])

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
                ('company_id', '=', website.company_id.id),
                ('state', '=', 'sale'),
                ('order_line.product_id.product_tmpl_id', '=', current_template.id),
            ], limit=8, order='date_order DESC')
            if sale_orders:
                cart_products = request.cart.order_line.product_id
                excluded_products = cart_products.product_tmpl_id.product_variant_ids
                excluded_products |= current_template.product_variant_ids
                included_products = sale_orders.order_line.product_id
                if self.env.context.get('hide_variants'):
                    included_products = included_products.product_tmpl_id.product_variant_id
                if products := included_products - excluded_products:
                    domain = Domain(domain) & Domain('id', 'in', products.ids)
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
            cart_products = request.cart.order_line.product_id
            excluded_products = cart_products.product_tmpl_id.product_variant_ids
            excluded_products |= current_template.product_variant_ids
            included_products = current_template._get_website_accessory_product()
            if self.env.context.get('hide_variants'):
                included_products = included_products.product_tmpl_id.product_variant_id
            if products := included_products - excluded_products:
                domain = Domain(domain) & Domain('id', 'in', products.ids)
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
            cart_products = request.cart.order_line.product_id
            excluded_products = cart_products.product_tmpl_id.product_variant_ids
            excluded_products |= current_template.product_variant_ids
            alternative_products = current_template._get_website_alternative_product()
            if self.env.context.get('hide_variants'):
                included_products = alternative_products.product_variant_id
            else:
                included_products = alternative_products.product_variant_ids
            products = included_products - excluded_products
            if products:
                domain = Domain(domain) & Domain('id', 'in', products.ids)
                products = self.env['product.product'].with_context(
                    display_default_code=False,
                ).search(domain, limit=limit)
        return products

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if 'field_names' in defaults and self.env.context.get('model') == 'product.product':
            defaults['field_names'] = 'display_name,description_sale,image_512'
        return defaults
