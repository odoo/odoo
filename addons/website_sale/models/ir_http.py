# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from lxml import html

from odoo import api, models
from odoo.http import request
from odoo.tools import lazy


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        affiliate_id = request.httprequest.args.get('affiliate_id')
        if affiliate_id:
            request.session['affiliate_id'] = int(affiliate_id)

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        session_info.update({
            'add_to_cart_action': request.website.add_to_cart_action,
        })
        return session_info

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()

        # lazy to make sure those are only evaluated when requested
        # All those records are sudoed !
        request.cart = lazy(request.website._get_and_cache_current_cart)
        request.fiscal_position = lazy(request.website._get_and_cache_current_fiscal_position)
        request.pricelist = lazy(request.website._get_and_cache_current_pricelist)

    @classmethod
    def _post_dispatch(cls, response):
        super()._post_dispatch(response)
        cls._inject_dynamic_snippet_products(response)

    @classmethod
    def _inject_dynamic_snippet_products(cls, response):
        """Server-side rendering of dynamic product snippets for SEO."""

        if not 'text/html' in response.headers.get('Content-Type'):
            return

        content = response.data
        if not content:
            return

        tree = html.fromstring(content)

        snippets = tree.xpath('//*[@data-snippet="s_dynamic_snippet_products"]')
        if not snippets:
            return

        filter_ids = set()
        for snippet in snippets:
            filter_id = snippet.get('data-filter-id')
            if filter_id:
                filter_ids.add(int(filter_id))

        filters = request.env['website.snippet.filter'].sudo().browse(list(filter_ids)).exists()
        filter_map = {f.id: f for f in filters}

        modified = False
        for snippet in snippets:
            if cls._render_snippet_products(snippet, filter_map, response, tree):
                modified = True

        if modified:
            response.data = html.tostring(tree, encoding='utf-8')

    @classmethod
    def _render_snippet_products(cls, snippet, filter_map, response, tree):
        """Render dynamic product snippet.

        :param snippet: lxml element representing the snippet
        :param filter_map: dict mapping filter IDs to filter records
        :param response: the response object
        :param tree: lxml parsed HTML tree
        :return: True if snippet was modified, False otherwise
        """

        # Extract snippet configuration
        filter_id = snippet.get('data-filter-id')
        snippet_filter = filter_map.get(int(filter_id))
        rendered_content = snippet_filter._render(
            template_key=snippet.get('data-template-key'),
            limit=int(snippet.get('data-number-of-records', 16)),
            search_domain=cls._build_product_search_domain(snippet, tree),
            with_sample=False,
        )

        template_area = snippet.xpath('.//*[contains(@class, "dynamic_snippet_template")]')[0]
        template_area.classes.add('d-none')  # hidden until client-side hydration

        wrapped_products = [
            html.fromstring(f'<div class="d-flex">{chunk}</div>')
            for chunk in rendered_content
        ]
        template_area.extend(wrapped_products)

        # Mark as server-side rendered to prevent client-side fetching
        snippet.set('data-ssr-rendered', 'true')

        return True

    @classmethod
    def _build_product_search_domain(cls, snippet, tree):
        """Build search domain from snippet attributes, mirroring client-side logic.

        :param snippet: lxml element with data attributes
        :param tree: lxml parsed HTML tree
        :return: search domain list
        """

        search_domain = []

        # Category filter
        product_category_id = snippet.get('data-product-category-id')
        if product_category_id and product_category_id not in ('all', None):
            if product_category_id == 'current':
                category_id = cls._get_current_category_id()
                if category_id:
                    search_domain.append(('public_categ_ids', 'child_of', category_id))
                else:
                    product_template_id = cls._get_current_product_template_id(tree)
                    if product_template_id:
                        search_domain.append(('public_categ_ids.product_tmpl_ids', '=', product_template_id))
            else:
                # Specific category ID provided
                category_id = int(product_category_id)
                search_domain.append(('public_categ_ids', 'child_of', category_id))

        # Tag filter
        product_tag_ids = snippet.get('data-product-tag-ids')
        if product_tag_ids:
            tag_ids = json.loads(product_tag_ids)
            tag_id_list = []
            for tag in tag_ids:
                tag_id_list.append(tag["id"])
            search_domain.append(('all_product_tag_ids', 'in', tag_id_list))

        # Product name filter (searches name, default_code and barcode)
        product_names = snippet.get('data-product-names')
        if product_names:
            name_domain = []
            for product_name in product_names.split(','):
                if not product_name:
                    continue
                if name_domain:
                    name_domain.insert(0, '|')
                name_domain.extend([
                    '|', '|',
                    ('name', 'ilike', product_name),
                    ('default_code', '=', product_name),
                    ('barcode', '=', product_name),
                ])
            if name_domain:
                search_domain.extend(name_domain)

        # Variant visibility filter
        if not snippet.get('data-show-variants'):
            search_domain.append('hide_variants')

        return search_domain

    @classmethod
    def _get_current_category_id(cls):
        """ Extract current product category ID

        :return: Category ID (int) if found, else None
        """
        path = request.httprequest.path
        if '/category/' not in path:
            return None

        category_segment = path.split('/category/')[-1].split('/')[0]
        if '-' in category_segment:
            category_id = int(category_segment.rsplit('-', 1)[-1])
            if request.env['product.public.category'].sudo().browse(category_id).exists():
                return category_id
        return None

    @classmethod
    def _get_current_product_template_id(cls, tree):
        """ Extract current product template ID from DOM.
        :param tree: lxml parsed HTML tree
        :return: Product template ID (int) if found, else None
        """

        product_elements = tree.xpath('//*[contains(@class, "js_product")]//*[@data-product-template-id]')
        if product_elements:
            template_id = product_elements[0].get('data-product-template-id')
            if template_id and int(template_id) > 0:
                return int(template_id)
        return None
