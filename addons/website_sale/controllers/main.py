# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import itertools
import json

from datetime import datetime

from werkzeug import urls
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_decode, url_encode, url_parse

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.http import request, route
from odoo.tools import SQL, clean_context, float_round, groupby, lazy, str2bool
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import _, LazyTranslate

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.web_editor.tools import get_video_thumbnail
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_sale.const import SHOP_PATH
from odoo.addons.website_sale.models.website import (
    PRICELIST_SELECTED_SESSION_CACHE_KEY,
    PRICELIST_SESSION_CACHE_KEY,
)

_lt = LazyTranslate(__name__)


def handle_product_params_error(exc, product, category=None, **kwargs):
    """ Handle access and missing errors related to product or category on the eCommerce.

    This function is intended to prevent access-related exceptions when a user attempts to view a
    product or category page. It checks if the provided product and category records still exist and
    are accessible, and then attempts to redirect to a valid fallback route if possible. If no valid
    route is found, it returns a 404 response code (instead of a 403).

    :param odoo.exceptions.AccessError | odoo.exceptions.MissingError exc: The exception thrown
            by _check_access `base.models.ir_http._pre_dispatch`.
    :param product.template product: The product the user is trying to access.
    :param product.public.category category: The category the user is trying to access, if any.
    :param dict kwargs: Optional data. This parameter is not used here.
    :return: A redirect response to a valid shop or product page, or a 404 error code if no valid
             fallback is found.
    :rtype: int | Response
    """
    product = product.exists()
    if category:
        category = category.exists()

    if category and not (product and product.has_access('read')):
        return request.redirect(WebsiteSale._get_shop_path(category))

    if not category and product and product.has_access('read'):
        return request.redirect(WebsiteSale._get_product_path(product))

    return NotFound.code  # 404


class TableCompute:

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey, ppr):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= ppr:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(ppr):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=20, ppr=4):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(max(p.website_size_x, 1), ppr)
            y = min(max(p.website_size_y, 1), ppr)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % ppr, pos // ppr, x, y, ppr):
                pos += 1
            # if 21st products (index 20) and the last line is full (ppr products in it), break
            # (pos + 1.0) / ppr is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) // ppr) > maxy:
                break

            if x == 1 and y == 1:   # simple heuristic for CPU optimization
                minpos = pos // ppr

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // ppr) + y2][(pos % ppr) + x2] = False
            self.table[pos // ppr][pos % ppr] = {
                'product': p, 'x': x, 'y': y,
                'ribbon': p.sudo().website_ribbon_id,
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos // ppr))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows


class WebsiteSale(payment_portal.PaymentPortal):
    _express_checkout_route = '/shop/express_checkout'
    _express_checkout_delivery_route = '/shop/express/shipping_address_change'

    WRITABLE_PARTNER_FIELDS = [
        'name',
        'email',
        'phone',
        'street',
        'street2',
        'city',
        'zip',
        'country_id',
        'state_id',
    ]

    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        order = post.get('order') or request.env['website'].get_current_website().shop_default_sort
        return 'is_published desc, %s, id desc' % order

    def _add_search_subdomains_hook(self, search):
        return []

    def _get_shop_domain(self, search, category, attribute_value_dict, search_in_description=True):
        domains = [request.website.sale_product_domain()]
        if search:
            for srch in search.split(" "):
                subdomains = [
                    Domain('name', 'ilike', srch),
                    Domain('variants_default_code', 'ilike', srch),
                ]
                if search_in_description:
                    subdomains.extend((
                        Domain('website_description', 'ilike', srch),
                        Domain('description_sale', 'ilike', srch),
                    ))
                extra_subdomain = self._add_search_subdomains_hook(srch)
                if extra_subdomain:
                    subdomains.append(extra_subdomain)
                domains.append(Domain.OR(subdomains))

        if category:
            domains.append(Domain('public_categ_ids', 'child_of', int(category)))

        if attribute_value_dict:
            domains.extend(
                request.env['product.template']._get_attribute_value_domain(attribute_value_dict)
            )

        return Domain.AND(domains)

    def sitemap_shop(env, rule, qs):
        website = env['website'].get_current_website()
        if website and website.ecommerce_access == 'logged_in' and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        if not qs or qs.lower() in SHOP_PATH:
            yield {'loc': SHOP_PATH}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, f'{SHOP_PATH}/category', Category._rec_name)
        dom &= website.website_domain()
        for cat in Category.search(dom):
            loc = f'{SHOP_PATH}/category/{env["ir.http"]._slug(cat)}'
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def sitemap_products(env, rule, qs):
        website = env['website'].get_current_website()
        if website and website.ecommerce_access == 'logged_in' and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        ProductTemplate = env['product.template']
        dom = sitemap_qs2dom(qs, SHOP_PATH, ProductTemplate._rec_name)
        dom &= Domain(website.sale_product_domain())
        for product in ProductTemplate.search(dom):
            loc = f'{SHOP_PATH}/{env["ir.http"]._slug(product)}'
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _get_search_options(
        self,
        category=None,
        attribute_value_dict=None,
        tags=None,
        min_price=0.0,
        max_price=0.0,
        conversion_rate=1,
        **post,
    ):
        return {
            'displayDescription': True,
            'displayDetail': True,
            'displayExtraDetail': True,
            'displayExtraLink': True,
            'displayImage': True,
            'allowFuzzy': not post.get('noFuzzy'),
            'category': str(category.id) if category else None,
            'tags': tags,
            'min_price': min_price / conversion_rate,
            'max_price': max_price / conversion_rate,
            'attribute_value_dict': attribute_value_dict,
            'display_currency': post.get('display_currency'),
        }

    def _shop_lookup_products(self, options, post, search, website):
        # No limit because attributes are obtained from complete product list
        product_count, details, fuzzy_search_term = website._search_with_fuzzy("products_only", search,
                                                                               limit=None,
                                                                               order=self._get_search_order(post),
                                                                               options=options)
        search_result = details[0].get('results', request.env['product.template']).with_context(bin_size=True)

        return fuzzy_search_term, product_count, search_result

    def _shop_get_query_url_kwargs(
        self, search, min_price, max_price, order=None, tags=None, **kwargs
    ):
        attribute_values = request.session.get('attribute_values', [])
        return {
            'search': search,
            'min_price': min_price,
            'max_price': max_price,
            'order': order,
            'tags': tags,
            'attribute_values': attribute_values,
        }

    def _get_additional_shop_values(self, values, **kwargs):
        """ Hook to update values used for rendering website_sale.products template """
        return {}

    def _get_product_query_string(self, **kwargs):
        """ Hook to set the product page URL's query string. """
        return ''

    @route(
        [
            SHOP_PATH,
            f'{SHOP_PATH}/page/<int:page>',
            f'{SHOP_PATH}/category/<model("product.public.category"):category>',
            f'{SHOP_PATH}/category/<model("product.public.category"):category>/page/<int:page>',
        ],
        type='http',
        auth='public',
        website=True,
        list_as_website_content=_lt("Shop"),
        sitemap=sitemap_shop,
        # Sends a 404 error in case of any Access error instead of 403.
        handle_params_access_error=lambda e, **kwargs: NotFound.code,
    )
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, tags='', **post):
        if not request.website.has_ecommerce_access():
            return request.redirect('/web/login')

        is_category_in_query = category and isinstance(category, str)
        category = self._validate_and_get_category(category)
        # If the category is provided as a query parameter (which is deprecated), we redirect to the
        # "correct" shop URL, where the category has been removed from the query parameters and
        # added to the path.
        if is_category_in_query:
            query = self._get_filtered_query_string(
                request.httprequest.query_string.decode(), keys_to_remove=['category']
            )
            return request.redirect(f'{self._get_shop_path(category, page)}?{query}', code=301)

        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

        website = request.env['website'].get_current_website()
        website_domain = website.website_domain()

        ppg = website.shop_ppg or 20
        ppr = website.shop_ppr or 4
        gap = website.shop_gap or "16px"

        request_args = request.httprequest.args
        attribute_values = request_args.getlist('attribute_values')
        attribute_value_dict = self._get_attribute_value_dict(attribute_values)
        attribute_ids = set(attribute_value_dict.keys())
        attribute_value_ids = set(itertools.chain.from_iterable(attribute_value_dict.values()))
        if attribute_values:
            request.session['attribute_values'] = attribute_values
        else:
            request.session.pop('attribute_values', None)

        filter_by_tags_enabled = website.is_view_active('website_sale.filter_products_tags')
        if filter_by_tags_enabled:
            if tags:
                post['tags'] = tags
                tags = {self.env['ir.http']._unslug(tag)[1] for tag in tags.split(',')}
            else:
                post['tags'] = None
                tags = {}

        url = self._get_shop_path(category)
        keep = QueryURL(
            url, **self._shop_get_query_url_kwargs(search, min_price, max_price, **post)
        )

        # Check if we need to refresh the cached pricelist
        now = datetime.timestamp(datetime.now())
        if 'website_sale_pricelist_time' in request.session:
            pricelist_save_time = request.session['website_sale_pricelist_time']
            if pricelist_save_time < now - 60*60:
                request.session.pop(PRICELIST_SESSION_CACHE_KEY, None)
                # restart the counter
                request.session['website_sale_pricelist_time'] = now

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            company_currency = website.company_id.sudo().currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, website.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        if search:
            post['search'] = search

        options = self._get_search_options(
            category=category,
            attribute_value_dict=attribute_value_dict,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            display_currency=website.currency_id,
            **post
        )
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(
            options, post, search, website
        )

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            Product = request.env['product.template'].with_context(bin_size=True)
            domain = self._get_shop_domain(search, category, attribute_value_dict)

            # This is ~4 times more efficient than a search for the cheapest and most expensive products
            query = Product._search(domain)
            sql = query.select(
                SQL(
                    "COALESCE(MIN(list_price), 0) * %(conversion_rate)s, COALESCE(MAX(list_price), 0) * %(conversion_rate)s",
                    conversion_rate=conversion_rate,
                )
            )
            available_min_price, available_max_price = request.env.execute_query(sql)[0]

            if min_price or max_price:
                # The if/else condition in the min_price / max_price value assignment
                # tackles the case where we switch to a list of products with different
                # available min / max prices than the ones set in the previous page.
                # In order to have logical results and not yield empty product lists, the
                # price filter is set to their respective available prices when the specified
                # min exceeds the max, and / or the specified max is lower than the available min.
                if min_price:
                    min_price = min_price if min_price <= available_max_price else available_min_price
                    post['min_price'] = min_price
                if max_price:
                    max_price = max_price if max_price >= available_min_price else available_max_price
                    post['max_price'] = max_price

        ProductTag = request.env['product.tag']
        if filter_by_tags_enabled and search_product:
            all_tags = ProductTag.search(Domain.AND([
                Domain('product_ids.is_published', '=', True),
                Domain('visible_to_customers', '=', True),
                website_domain,
            ]))
        else:
            all_tags = ProductTag

        Category = request.env['product.public.category']
        categs_domain = Domain('parent_id', '=', False) & website_domain
        if not self.env.user._is_internal():
            categs_domain &= Domain('has_published_products', '=', True)
        if search:
            search_categories = Category.search(
                Domain('product_tmpl_ids', 'in', search_product.ids) & website_domain
            ).parents_and_self
            categs_domain &= Domain('id', 'in', search_categories.ids)
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=5, url_args=post)
        offset = pager['offset']
        products = search_product[offset:offset + ppg]

        ProductAttribute = request.env['product.attribute']
        if products:
            # get all products without limit
            attributes = lazy(lambda: ProductAttribute.search([
                ('product_tmpl_ids', 'in', search_product.ids),
                ('visibility', '=', 'visible'),
            ]))
        else:
            attributes = lazy(lambda: ProductAttribute.browse(attribute_ids).sorted())

        if website.is_view_active('website_sale.products_list_view'):
            layout_mode = 'list'
        else:
            layout_mode = 'grid'

        products_prices = lazy(lambda: products._get_sales_prices(website))

        attributes_values = request.env['product.attribute.value'].browse(attribute_value_ids)
        sorted_attributes_values = attributes_values.sorted('sequence')
        multi_attributes_values = sorted_attributes_values.filtered(lambda av: av.display_type == 'multi')
        single_attributes_values = sorted_attributes_values - multi_attributes_values
        grouped_attributes_values = list(groupby(single_attributes_values, lambda av: av.attribute_id.id))
        grouped_attributes_values.extend([(av.attribute_id.id, [av]) for av in multi_attributes_values])

        selected_attributes_hash = grouped_attributes_values and "#attribute_values=%s" % (
            ','.join(str(v[0].id) for k, v in grouped_attributes_values)
        ) or ''

        values = {
            'auto_assign_ribbons': lazy(
                lambda: self.env['product.ribbon'].sudo().search([('assign', '!=', 'manual')])
            ),
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attribute_value_dict,
            'attrib_set': attribute_value_ids,
            'pager': pager,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'gap': gap,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'selected_attributes_hash': selected_attributes_hash,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': float_round,
            'shop_path': SHOP_PATH,
            'product_query_string': self._get_product_query_string(**post),
            'previewed_attribute_values': lazy(products._get_previewed_attribute_values),
        }
        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = float_round(available_min_price, 2)
            values['available_max_price'] = float_round(available_max_price, 2)
        if filter_by_tags_enabled:
            values.update({'all_tags': all_tags, 'tags': tags})
        if category:
            values['main_object'] = category
        values.update(self._get_additional_shop_values(values, **post))
        return request.render("website_sale.products", values)

    @route(
        [
            f'{SHOP_PATH}/<model("product.template"):product>',
            f'{SHOP_PATH}/<model("product.public.category"):category>/<model("product.template"):product>',
        ],
        type='http',
        auth='public',
        website=True,
        sitemap=sitemap_products,
        handle_params_access_error=handle_product_params_error,
    )
    def product(self, product, category=None, pricelist=None, **kwargs):
        if not request.website.has_ecommerce_access():
            return request.redirect('/web/login')

        if pricelist is not None:
            try:
                pricelist_id = int(pricelist)
            except ValueError:
                raise ValidationError(request.env._(
                    "Wrong format: got `pricelist=%s`, expected an integer", pricelist,
                ))
            if not self._apply_selectable_pricelist(pricelist_id):
                return request.redirect(self._get_shop_path(category))

        is_category_in_query = category and isinstance(category, str)
        category = self._validate_and_get_category(category)
        query = self._get_filtered_query_string(
            request.httprequest.query_string.decode(), keys_to_remove=['category']
        )
        # If the product doesn't belong to the category, we redirect to the canonical product URL,
        # which doesn't include the category.
        if (
            category
            and not product.filtered_domain([('public_categ_ids', 'child_of', category.id)])
        ):
            return request.redirect(f'{self._get_product_path(product)}?{query}', code=301)
        # If the category is provided as a query parameter (which is deprecated), we redirect to the
        # "correct" shop URL, where the category has been removed from the query parameters and
        # added to the path.
        if is_category_in_query:
            return request.redirect(
                f'{self._get_product_path(product, category)}?{query}', code=301
            )
        return request.render(
            'website_sale.product', self._prepare_product_values(product, category, **kwargs)
        )

    @route(
        '/shop/<model("product.template"):product_template>/document/<int:document_id>',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
        readonly=True,
    )
    def product_document(self, product_template, document_id):
        product_template.check_access('read')

        document = request.env['product.document'].browse(document_id).sudo().exists()
        if not document or not document.active:
            return request.redirect(self._get_shop_path())

        if not document.shown_on_product_page or not (
            document.res_id == product_template.id
            and document.res_model == 'product.template'
        ):
            return request.redirect(self._get_shop_path())

        return request.env['ir.binary']._get_stream_from(
            document.ir_attachment_id,
        ).get_response(as_attachment=True)

    @route(
        [f'{SHOP_PATH}/product/<model("product.template"):product>'],
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def old_product(self, product, category='', **kwargs):
        # Compatibility pre-v14
        # Redirect to the "correct" product URL, which doesn't include `/product`, and where the
        # category has been removed from the query parameters and added to the path.
        category = int(category) if str(category).isdigit() else False
        category = self._validate_and_get_category(category)
        query = self._get_filtered_query_string(
            request.httprequest.query_string.decode(), keys_to_remove=['category']
        )
        return request.redirect(f'{self._get_product_path(product, category)}?{query}', code=301)

    @route(['/shop/product/extra-media'], type='jsonrpc', auth='user', website=True)
    def add_product_media(self, media, type, product_product_id, product_template_id, combination_ids=None):
        """
        Handles adding both images and videos to product variants or templates,
        links all of them to product.
        :param type: [...] can be either image or video
        :raises NotFound : If the user is not allowed to access Attachment model
        """

        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        if type == 'image':  # Image case
            image_ids = request.env["ir.attachment"].browse(i['id'] for i in media)
            media_create_data = [Command.create({
                'name': image.name,   # Images uploaded from url do not have any datas. This recovers them manually
                'image_1920': image.datas
                    if image.datas
                    else request.env['ir.qweb.field.image'].load_remote_url(image.url),
            }) for image in image_ids]
        elif type == 'video':  # Video case
            video_data = media[0]
            thumbnail = None
            if video_data.get('src'):  # Check if a valid video URL is provided
                try:
                    thumbnail = base64.b64encode(get_video_thumbnail(video_data['src']))
                except Exception:
                    thumbnail = None
            else:
                raise ValidationError(_("Invalid video URL provided."))
            media_create_data = [Command.create({
                'name': video_data.get('name', 'Odoo Video'),
                'video_url': video_data['src'],
                'image_1920': thumbnail,
            })]

        product_product = request.env['product.product'].browse(int(product_product_id)) if product_product_id else False
        product_template = request.env['product.template'].browse(int(product_template_id)) if product_template_id else False

        if product_product and not product_template:
            product_template = product_product.product_tmpl_id

        if not product_product and product_template and product_template.has_dynamic_attributes():
            combination = request.env['product.template.attribute.value'].browse(combination_ids)
            product_product = product_template._get_variant_for_combination(combination)
            if not product_product:
                product_product = product_template._create_product_variant(combination)
        if product_template.has_configurable_attributes and product_product and not all(pa.create_variant == 'no_variant' for pa in product_template.attribute_line_ids.attribute_id):
            product_product.write({
                'product_variant_image_ids': media_create_data
            })
        else:
            product_template.write({
                'product_template_image_ids': media_create_data
            })

    @route(['/shop/product/clear-images'], type='jsonrpc', auth='user', website=True)
    def clear_product_images(self, product_product_id, product_template_id):
        """
        Unlinks all images from the product.
        """
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        product_product = request.env['product.product'].browse(int(product_product_id)) if product_product_id else False
        product_template = request.env['product.template'].browse(int(product_template_id)) if product_template_id else False

        if product_product and not product_template:
            product_template = product_product.product_tmpl_id

        if product_product and product_product.product_variant_image_ids:
            product_product.product_variant_image_ids.unlink()
        else:
            product_template.product_template_image_ids.unlink()

    @route(['/shop/product/resequence-image'], type='jsonrpc', auth='user', website=True)
    def resequence_product_image(self, image_res_model, image_res_id, move):
        """
        Move the product image in the given direction and update all images' sequence.

        :param str image_res_model: The model of the image. It can be 'product.template',
                                    'product.product', or 'product.image'.
        :param str image_res_id: The record ID of the image to move.
        :param str move: The direction of the move. It can be 'first', 'left', 'right', or 'last'.
        :raises NotFound: If the user does not have the required permissions, if the model of the
                          image is not allowed, or if the move direction is not allowed.
        :raise ValidationError: If the product is not found.
        :raise ValidationError: If the image to move is not found in the product images.
        :raise ValidationError: If a video is moved to the first position.
        :return: None
        """
        if (
            not request.env.user.has_group('website.group_website_restricted_editor')
            or image_res_model not in ['product.product', 'product.template', 'product.image']
            or move not in ['first', 'left', 'right', 'last']
        ):
            raise NotFound()

        image_res_id = int(image_res_id)
        image_to_resequence = request.env[image_res_model].browse(image_res_id)
        if image_res_model == 'product.product':
            product = image_to_resequence
            product_template = product.product_tmpl_id
        elif image_res_model == 'product.template':
            product_template = image_to_resequence
            product = product_template.product_variant_id
        else:
            product = image_to_resequence.product_variant_id
            product_template = product.product_tmpl_id or image_to_resequence.product_tmpl_id

        if not product and not product_template:
            raise ValidationError(_("Product not found"))

        product_images = (product or product_template)._get_images()
        if image_to_resequence not in product_images:
            raise ValidationError(_("Invalid image"))

        image_idx = product_images.index(image_to_resequence)
        new_image_idx = 0
        if move == 'left':
            new_image_idx = max(0, image_idx - 1)
        elif move == 'right':
            new_image_idx = min(len(product_images) - 1, image_idx + 1)
        elif move == 'last':
            new_image_idx = len(product_images) - 1

        # no-op resequences
        if new_image_idx == image_idx:
            return

        # Reorder images locally.
        product_images.insert(new_image_idx, product_images.pop(image_idx))

        # If the main image has been reordered (i.e. it's no longer in first position), use the
        # image that's now in first position as main image instead.
        # Additional images are product.image records. The main image is a product.product or
        # product.template record.
        main_image_idx = next(
            idx for idx, image in enumerate(product_images) if image._name != 'product.image'
        )
        if main_image_idx != 0:
            main_image = product_images[main_image_idx]
            additional_image = product_images[0]
            if additional_image.video_url:
                raise ValidationError(_("You can't use a video as the product's main image."))
            # Swap records.
            product_images[main_image_idx], product_images[0] = additional_image, main_image
            # Swap image data.
            main_image.image_1920, additional_image.image_1920 = (
                additional_image.image_1920, main_image.image_1920
            )
            additional_image.name = main_image.name  # Update image name but not product name.

        # Resequence additional images according to the new ordering.
        for idx, product_image in enumerate(product_images):
            if product_image._name == 'product.image':
                product_image.sequence = idx

    @route(['/shop/product/is_add_to_cart_allowed'], type='jsonrpc', auth="public", website=True, readonly=True)
    def is_add_to_cart_allowed(self, product_id, **kwargs):
        product = request.env['product.product'].browse(product_id)
        # In sudo mode to check fields and conditions not accessible to the customer directly.
        return product.sudo()._is_add_to_cart_allowed()

    def _prepare_product_values(self, product, category, **kwargs):
        ProductCategory = request.env['product.public.category']
        product_markup_data = [product._to_markup_data(request.website)]
        category = (
            category and ProductCategory.browse(int(category)).exists()
            or product.public_categ_ids[:1]
        )
        if category:
            # Add breadcrumb's SEO data.
            product_markup_data.append(self._prepare_breadcrumb_markup_data(
                request.website.get_base_url(), category, product.name
            ))
        keep = QueryURL(
            self._get_shop_path(category),
            attribute_values=request.session.get('attribute_values', [])
        )

        # Needed to trigger the recently viewed product rpc
        view_track = request.website.viewref("website_sale.product").track

        return {
            'category': category,
            'keep': keep,
            'categories': ProductCategory.search([('parent_id', '=', False)]),
            'main_object': product,
            'optional_product_ids': [
                p.with_context(active_id=p.id) for p in product.optional_product_ids
            ],
            'product': product,
            'view_track': view_track,
            'product_markup_data': json_scriptsafe.dumps(product_markup_data, indent=2),
            'shop_path': SHOP_PATH,
        }

    def _prepare_breadcrumb_markup_data(self, base_url, category, product_name):
        """ Generate JSON-LD markup data for the given product category.

        See https://schema.org/BreadcrumbList.

        :param str base_url: The base URL of the current website.
        :param product.public.category category: The current product category.
        :param str product_name: The name of the current product.
        :return: The JSON-LD markup data.
        :rtype: dict
        """
        return {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {
                    '@type': 'ListItem',
                    'position': 1,
                    'name': 'All Products',
                    'item': f'{base_url}{self._get_shop_path()}',
                },
                {
                    '@type': 'ListItem',
                    'position': 2,
                    'name': category.name,
                    'item': f'{base_url}{self._get_shop_path(category)}',
                },
                {
                    '@type': 'ListItem',
                    'position': 3,
                    'name': product_name,
                }
            ]
        }

    @route(
        '/shop/change_pricelist/<model("product.pricelist"):pricelist>',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def pricelist_change(self, pricelist, **post):
        website = request.env['website'].get_current_website()
        redirect_url = request.httprequest.referrer
        prev_pricelist = request.pricelist
        if (
            self._apply_selectable_pricelist(pricelist.id)
            and redirect_url
            and website.is_view_active('website_sale.filter_products_price')
            and prev_pricelist != pricelist
        ):
            # Convert prices to the new priceslist currency in the query params of the referrer
            decoded_url = url_parse(redirect_url)
            args = url_decode(decoded_url.query)
            min_price = args.get('min_price')
            max_price = args.get('max_price')
            if min_price or max_price:
                try:
                    min_price = float(min_price)
                    args['min_price'] = min_price and str(prev_pricelist.currency_id._convert(
                        min_price,
                        pricelist.currency_id,
                        request.website.company_id,
                        fields.Date.today(),
                        round=False,
                    ))
                except (ValueError, TypeError):
                    pass
                try:
                    max_price = float(max_price)
                    args['max_price'] = max_price and str(prev_pricelist.currency_id._convert(
                        max_price,
                        pricelist.currency_id,
                        request.website.company_id,
                        fields.Date.today(),
                        round=False,
                    ))
                except (ValueError, TypeError):
                    pass
            redirect_url = decoded_url.replace(query=url_encode(args)).to_url()

        return request.redirect(redirect_url or self._get_shop_path())

    @route('/shop/pricelist', type='http', auth='public', website=True, sitemap=False)
    def pricelist(self, promo, **post):
        redirect = post.get('r', '/shop/cart')
        if promo:
            pricelist_sudo = request.env['product.pricelist'].sudo().search([('code', '=', promo)], limit=1)
            if not (pricelist_sudo and request.website.is_pricelist_available(pricelist_sudo.id)):
                return request.redirect("%s?code_not_available=1" % redirect)

            self._apply_pricelist(pricelist=pricelist_sudo)
        else:
            # Reset the pricelist if empty promo code is given
            self._apply_pricelist(pricelist=None)

        return request.redirect(redirect)

    def _apply_selectable_pricelist(self, pricelist_id):
        """ Change the request pricelist if selectable on the website.

        A pricelist is applied if:
        - it is available on the current website
        - it is selectable or on the current partner

        :param int pricelist_id: the pricelist ID
        :return: True or False if the pricelist was applied or not
        :rtype: bool
        """
        if (
            request.env['website'].get_current_website().is_pricelist_available(pricelist_id)
            and (pricelist := request.env['product.pricelist'].browse(pricelist_id))
            and (
                pricelist.selectable
                or pricelist == request.env.user.partner_id.property_product_pricelist
            )
        ):
            self._apply_pricelist(pricelist=pricelist)
            return True
        return False

    def _apply_pricelist(self, pricelist=None):
        """ Changes the pricelist of the request and recomputes the current cart prices.

        :param 'product.pricelist'|None pricelist: The new pricelist. If None resets the pricelist.
        """
        if pricelist is None:  # Reset the pricelist
            request.session.pop(PRICELIST_SESSION_CACHE_KEY, None)
            request.session.pop(PRICELIST_SELECTED_SESSION_CACHE_KEY, None)
            request.pricelist = lazy(request.website._get_and_cache_current_pricelist)

            if order_sudo := request.cart:
                pl_before = order_sudo.pricelist_id
                order_sudo._compute_pricelist_id()
                if order_sudo.pricelist_id != pl_before:
                    order_sudo._recompute_prices()
            return

        pricelist.ensure_one()

        if pricelist.id == request.pricelist.id:
            # Nothing to do
            return

        request.session[PRICELIST_SESSION_CACHE_KEY] = pricelist.id
        request.session[PRICELIST_SELECTED_SESSION_CACHE_KEY] = pricelist.id
        request.pricelist = pricelist.sudo()

        if order_sudo := request.cart:
            order_sudo.pricelist_id = pricelist
            order_sudo._recompute_prices()

    @route('/shop/save_shop_layout_mode', type='jsonrpc', auth='public', website=True)
    def save_shop_layout_mode(self, layout_mode):
        assert layout_mode in ('grid', 'list'), "Invalid shop layout mode"
        request.session['website_sale_shop_layout_mode'] = layout_mode

    # ------------------------------------------------------
    # Checkout
    # ------------------------------------------------------

    # === CHECKOUT FLOW - ADDRESS METHODS === #

    @route(
        '/shop/checkout', type='http', methods=['GET'], auth='public', website=True, sitemap=False, list_as_website_content=_lt("Shop Checkout")
    )
    def shop_checkout(self, try_skip_step=None, **query_params):
        """ Display the checkout page.

        :param str try_skip_step: Whether the user should immediately be redirected to the next step
                                  if no additional information (i.e., address or delivery method) is
                                  required on the checkout page. 'true' or 'false'.
        :param dict query_params: The additional query string parameters.
        :return: The rendered checkout page.
        :rtype: str
        """
        try_skip_step = str2bool(try_skip_step or 'false')
        order_sudo = request.cart
        request.session['sale_last_order_id'] = order_sudo.id

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        checkout_page_values = self._prepare_checkout_page_values(order_sudo, **query_params)

        can_skip_delivery = True  # Delivery is only needed for deliverable products.
        if order_sudo._has_deliverable_products():
            can_skip_delivery = False
            available_dms = order_sudo._get_delivery_methods()
            checkout_page_values['delivery_methods'] = available_dms
            if delivery_method := order_sudo._get_preferred_delivery_method(available_dms):
                rate = delivery_method.rate_shipment(order_sudo)
                if (
                    not order_sudo.carrier_id
                    or not rate.get('success')
                    or order_sudo.amount_delivery != rate['price']
                ):
                    order_sudo._set_delivery_method(delivery_method, rate=rate)

        checkout_page_values.update(
            request.website._get_checkout_step_values()
        )
        if try_skip_step and can_skip_delivery:
            return request.redirect(
                checkout_page_values['next_website_checkout_step_href']
            )

        return request.render('website_sale.checkout', checkout_page_values)

    def _prepare_checkout_page_values(self, order_sudo, **kwargs):
        """Provide the data used to render the /shop/checkout page.

        :param sale.order order_sudo: The current cart.
        :param dict kwargs: unused parameters available for potential overrides.
        :return: The checkout page rendering values.
        :rtype: dict
        """
        partner_sudo = order_sudo.partner_id
        return {
            'order': order_sudo,
            'website_sale_order': order_sudo,  # Compatibility with other templates.
            'use_delivery_as_billing': (
                order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            ),
            'only_services': order_sudo.only_services,
            **self._prepare_address_data(partner_sudo, **kwargs),
            'address_url': '/shop/address',
        }

    @route(
        '/shop/address', type='http', methods=['GET'], auth='public', website=True, sitemap=False
    )
    def shop_address(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=None, **query_params
    ):
        """ Display the address form.

        A partner and/or an address type can be given through the query string params to specify
        which address to update or create, and its type.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            delivery and the billing address. 'true' or 'false'.
        :param dict query_params: The additional query string parameters forwarded to
                                  `_prepare_address_form_values`.
        :return: The rendered address form.
        :rtype: str
        """
        use_delivery_as_billing = str2bool(use_delivery_as_billing or 'false')

        order_sudo = request.cart
        if redirection := self._check_cart(order_sudo):
            return redirection

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )

        use_delivery_as_billing = str2bool(use_delivery_as_billing or 'false')
        if partner_sudo:  # If editing an existing partner.
            use_delivery_as_billing = (
                partner_sudo == order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            )

        # Render the address form.
        address_form_values = self._prepare_address_form_values(
            partner_sudo,
            address_type=address_type,
            order_sudo=order_sudo,
            use_delivery_as_billing=use_delivery_as_billing,
            **query_params
        )
        address_form_values.update(
            request.website._get_checkout_step_values()
        )
        return request.render('website_sale.address', address_form_values)

    def _prepare_address_form_values(
        self,
        *args,
        callback='',
        order_sudo=False,
        **kwargs
    ):
        """Prepare the rendering values of the address form.

        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param sale.order order_sudo: The current cart.
        :return: The checkout page values.
        :rtype: dict
        """
        rendering_values = super()._prepare_address_form_values(
            *args, order_sudo=order_sudo, callback=callback, **kwargs
        )
        if not order_sudo: # Return portal address values if not order
            return rendering_values

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        # Display b2b field is feature is enabled on given website
        rendering_values['display_b2b_fields'] = (
            rendering_values.get('display_b2b_fields', False)
            or request.website.is_view_active('website_sale.address_b2b')
        )

        if rendering_values['commercial_address_update_url']:
            rendering_values['commercial_address_update_url'] = f'/shop/address?partner_id={order_sudo.partner_id.id}'

        return {
            **rendering_values,
            'is_anonymous_cart': is_anonymous_cart,
            'website_sale_order': order_sudo,
            'only_services': order_sudo.only_services,
            'discard_url': callback or (is_anonymous_cart and '/shop/cart') or '/shop/checkout',
        }

    def _get_default_country(self, order_sudo=False, **kwargs):
        """ Override `portal` to return country of customer if customer is not logged in."""
        is_anonymous_cart = order_sudo and order_sudo._is_anonymous_cart()
        if is_anonymous_cart and request.geoip.country_code:
            return request.env['res.country'].sudo().search([
                ('code', '=', request.geoip.country_code),
            ], limit=1)
        return super()._get_default_country(order_sudo=order_sudo, **kwargs)

    @route(
        '/shop/address/submit', type='http', methods=['POST'], auth='public', website=True,
        sitemap=False
    )
    def shop_address_submit(
        self,
        partner_id=None,
        address_type='billing',
        use_delivery_as_billing=None,
        callback=None,
        **form_data
    ):
        """ Create or update an address.

        If it succeeds, it returns the URL to redirect (client-side) to. If it fails (missing or
        invalid information), it highlights the problematic form input with the appropriate error
        message.

        :param str partner_id: The partner whose address to update with the address form, if any.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param str use_delivery_as_billing: Whether the provided address should be used as both the
                                            billing and the delivery address. 'true' or 'false'.
        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param dict form_data: The form data to process as address values.
        :return: A JSON-encoded feedback, with either the success URL or an error message.
        :rtype: str
        """
        order_sudo = request.cart
        if redirection := self._check_cart(order_sudo):
            return json.dumps({'redirectUrl': redirection.location})

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )

        is_new_address = not partner_sudo
        if is_new_address or order_sudo.only_services:
            callback = callback or '/shop/checkout?try_skip_step=true'
        else:
            callback = callback or '/shop/checkout'

        partner_sudo, feedback_dict = self._create_or_update_address(
            partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            callback=callback,
            order_sudo=order_sudo,
            **form_data
        )

        if feedback_dict.get('invalid_fields'):
            return json.dumps(feedback_dict) # Return if error when creating/updating partner.

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        is_main_address = is_anonymous_cart or order_sudo.partner_id.id == partner_sudo.id
        partner_fnames = set()
        if is_main_address:  # Main customer address updated.
            partner_fnames.add('partner_id')  # Force the re-computation of partner-based fields.

        if address_type == 'billing':
            partner_fnames.add('partner_invoice_id')
            if is_new_address and order_sudo.only_services:
                # The delivery address is required to make the order.
                partner_fnames.add('partner_shipping_id')
        elif address_type == 'delivery':
            partner_fnames.add('partner_shipping_id')
            if use_delivery_as_billing:
                partner_fnames.add('partner_invoice_id')

        order_sudo._update_address(partner_sudo.id, partner_fnames)

        if order_sudo._is_anonymous_cart():
            # Unsubscribe the public partner if the cart was previously anonymous.
            order_sudo.message_unsubscribe(order_sudo.website_id.partner_id.ids)

        return json.dumps(feedback_dict)

    def _needs_address(self):
        if cart := request.cart:
            return cart._needs_customer_address()
        return super()._needs_address()

    def _prepare_address_update(self, order_sudo, partner_id=None, address_type=None):
        """ Find the partner whose address to update and return it along with its address type.

        :param sale.order order_sudo: The current cart.
        :param int partner_id: The partner whose address to update, if any, as a `res.partner` id.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :return: The partner whose address to update, if any, and its address type.
        :rtype: tuple[res.partner, str]
        :raise Forbidden: If the customer is not allowed to update the given address.
        """
        PartnerSudo = request.env['res.partner'].with_context(show_address=1).sudo()
        if order_sudo._is_anonymous_cart():
            partner_sudo = PartnerSudo
        else:
            partner_sudo = PartnerSudo.browse(partner_id)
            if partner_sudo and partner_sudo not in {
                order_sudo.partner_id,
                order_sudo.partner_invoice_id,
                order_sudo.partner_shipping_id,
            }:  # The partner is not yet linked to the SO.
                partner_sudo = partner_sudo.exists()

        if partner_sudo and not address_type:  # The desired address type was not specified.
            # Identify the address type based on the cart's billing and delivery partners.
            if partner_id == order_sudo.partner_invoice_id.id:
                address_type = 'billing'
            elif partner_id == order_sudo.partner_shipping_id.id:
                address_type = 'delivery'
            else:
                address_type = 'billing'

        if (
            partner_sudo
            and not partner_sudo._can_be_edited_by_current_customer(order_sudo=order_sudo)
        ):
            raise Forbidden()

        return partner_sudo, address_type

    def _complete_address_values(
        self, address_values, *args, order_sudo=False, **kwargs
    ):
        super()._complete_address_values(
            address_values, *args, order_sudo=order_sudo, **kwargs
        )

        if order_sudo and order_sudo._is_anonymous_cart():
            address_values['type'] = 'contact'

        if address_values['lang'] not in request.website.mapped('language_ids.code'):
            address_values.pop('lang')

        if not order_sudo:
            return
        address_values['company_id'] = (
            order_sudo.website_id.company_id.id
            or address_values['company_id']
        )
        address_values['user_id'] = order_sudo.website_id.salesperson_id.id

        if order_sudo.website_id.specific_user_account:
            address_values['website_id'] = order_sudo.website_id.id

    def _create_new_address(
        self, address_values, address_type, use_delivery_as_billing, order_sudo
    ):
        """ Create a new partner, must be called after the data has been verified

        NB: to verify (and preprocess) the data, please call `_parse_form_data` first.

        :param order_sudo: the current cart, as a sudoed `sale.order` recordset
        :param str address_type: 'billing' or 'delivery'
        :param bool use_delivery_as_billing: Whether the address must be used as the billing and the
                                             delivery address.
        :param dict address_values: values to use to create the partner

        :return: The created address, as a sudoed `res.partner` recordset.
        """
        self._complete_address_values(
            address_values, address_type, use_delivery_as_billing, order_sudo=order_sudo
        )
        creation_context = clean_context(request.env.context)
        creation_context.update({
            'tracking_disable': True,
            # 'no_vat_validation': True,  # TODO VCR VAT validation or not ?
        })
        return request.env['res.partner'].sudo().with_context(
            creation_context
        ).create(address_values)

    @route(
        _express_checkout_route, type='jsonrpc', methods=['POST'], auth="public", website=True,
        sitemap=False
    )
    def process_express_checkout(
        self, billing_address, shipping_address=None, shipping_option=None, **kwargs
    ):
        """ Records the partner information on the order when using express checkout flow.

        Depending on whether the partner is registered and logged in, either creates a new partner
        or uses an existing one that matches all received data.

        :param dict billing_address: Billing information sent by the express payment form.
        :param dict shipping_address: Shipping information sent by the express payment form.
        :param dict shipping_option: Carrier information sent by the express payment form.
        :param dict kwargs: Optional data. This parameter is not used here.
        :return int: The order's partner id.
        """
        order_sudo = request.cart

        # Update the partner with all the information
        self._include_country_and_state_in_address(billing_address)
        billing_address, _side_values = self._parse_form_data(billing_address)
        if order_sudo._is_anonymous_cart():

            # Pricelist are recomputed every time the partner is changed. We don't want to recompute
            # the price with another pricelist at this state since the customer has already accepted
            # the amount and validated the payment.
            new_partner_sudo = self._create_new_address(
                billing_address,
                address_type='billing',
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )
            with request.env.protecting([order_sudo._fields['pricelist_id']], order_sudo):
                order_sudo.partner_id = new_partner_sudo
        elif not self._are_same_addresses(billing_address, order_sudo.partner_invoice_id):
            # Check if a child partner doesn't already exist with the same informations. The
            # phone isn't always checked because it isn't sent in shipping information with
            # Google Pay.
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, billing_address
            )
            order_sudo.partner_invoice_id = child_partner_id or self._create_new_address(
                billing_address,
                address_type='billing',
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )

        # In a non-express flow, `sale_last_order_id` would be added in the session before the
        # payment. As we skip all the steps with the express checkout, `sale_last_order_id` must be
        # assigned to ensure the right behavior from `shop_payment_confirmation()`.
        request.session['sale_last_order_id'] = order_sudo.id

        if shipping_address:
            #in order to not override shippig address, it's checked separately from shipping option
            self._include_country_and_state_in_address(shipping_address)
            shipping_address, _side_values = self._parse_form_data(shipping_address)

            if order_sudo.name in order_sudo.partner_shipping_id.name:
                # The existing partner was created by `process_express_checkout_delivery_choice`, it
                # means that the partner is missing information, so we update it.
                order_sudo.partner_shipping_id.write(shipping_address)
                order_sudo._update_address(
                    order_sudo.partner_shipping_id.id, ['partner_shipping_id']
                )
            elif not self._are_same_addresses(shipping_address, order_sudo.partner_shipping_id):
                # The sale order's shipping partner's address is different from the one received. If
                # all the sale order's child partners' address differs from the one received, we
                # create a new partner. The phone isn't always checked because it isn't sent in
                # shipping information with Google Pay.
                child_partner_id = self._find_child_partner(
                    order_sudo.partner_id.commercial_partner_id.id, shipping_address
                )
                order_sudo.partner_shipping_id = child_partner_id or self._create_new_address(
                    shipping_address,
                    address_type='delivery',
                    use_delivery_as_billing=False,
                    order_sudo=order_sudo,
                )
            # Process the delivery method.
            if shipping_option:
                delivery_method_sudo = request.env['delivery.carrier'].sudo().browse(
                    int(shipping_option['id'])
                ).exists()
                order_sudo._set_delivery_method(delivery_method_sudo)

        return order_sudo.partner_id.id

    def _find_child_partner(self, commercial_partner_id, address):
        """ Find a child partner for a specified address

        Compare all keys in the `address` dict with the same keys on the partner object and return
        the id of the first partner that have the same value than in the dict for all the keys.

        :param int commercial_partner_id: The commercial partner whose child to find.
        :param dict address: The address fields.
        :return: The ID of the first child partner that match the criteria, if any.
        :rtype: int
        """
        partners_sudo = request.env['res.partner'].with_context(show_address=1).sudo().search([
            ('id', 'child_of', commercial_partner_id),
        ])
        for partner_sudo in partners_sudo:
            if self._are_same_addresses(address, partner_sudo):
                return partner_sudo.id
        return False

    def _include_country_and_state_in_address(self, address):
        """ This function is used to include country_id and state_id in address.

        Fetch country and state and include the records in address. The object is included to
        simplify the comparison of addresses.

        :param dict address: An address with country and state defined in ISO 3166.
        :return None:
        """
        country = request.env["res.country"].search([
            ('code', '=', address.pop('country')),
        ], limit=1)
        state_id = False
        if state_code := address.pop('state', False):
            state_id = country.state_ids.filtered(lambda state: state.code == state_code).id
        address.update(country_id=country.id, state_id=state_id)

    @route('/shop/update_address', type='jsonrpc', auth='public', website=True)
    def shop_update_address(self, partner_id, address_type='billing', **kw):
        partner_id = int(partner_id)

        if not (order_sudo := request.cart):
            return

        ResPartner = request.env['res.partner'].sudo()
        partner_sudo = ResPartner.browse(partner_id).exists()
        children = ResPartner._search([
            ('id', 'child_of', order_sudo.partner_id.commercial_partner_id.id),
            ('type', 'in', ('invoice', 'delivery', 'other')),
        ])
        if (
            partner_sudo != order_sudo.partner_id
            and partner_sudo != order_sudo.partner_id.commercial_partner_id
            and partner_sudo.id not in children
        ):
            raise Forbidden()

        partner_fnames = set()
        if (
            address_type == 'billing'
            and partner_sudo != order_sudo.partner_invoice_id
        ):
            partner_fnames.add('partner_invoice_id')
        elif (
            address_type == 'delivery'
            and partner_sudo != order_sudo.partner_shipping_id
        ):
            partner_fnames.add('partner_shipping_id')

        order_sudo._update_address(partner_id, partner_fnames)

    # === CHECKOUT FLOW - EXTRA STEP METHODS === #

    @route(['/shop/extra_info'], type='http', auth="public", website=True, sitemap=False, list_as_website_content=_lt("Shop Checkout - Extra Information"))
    def extra_info(self, **post):
        # Check that this option is activated
        extra_step = request.website.viewref('website_sale.extra_info')
        if not extra_step.active:
            return request.redirect("/shop/payment")

        # check that cart is valid
        order_sudo = request.cart
        redirection = self._check_cart(order_sudo)
        open_editor = request.params.get('open_editor') == 'true'
        # Do not redirect if it is to edit
        # (the information is transmitted via the "open_editor" parameter in the url)
        if not open_editor and redirection:
            return redirection

        values = {
            'website_sale_order': order_sudo,
            'post': post,
            'escape': lambda x: x.replace("'", r"\'"),
            'partner': order_sudo.partner_id.id,
            'order': order_sudo,
        }

        values.update(request.website._get_checkout_step_values())

        return request.render("website_sale.extra_info", values)

    # === CHECKOUT FLOW - PAYMENT/CONFIRMATION METHODS === #

    def _get_shop_payment_values(self, order, **kwargs):
        checkout_page_values = {
            'sale_order': order,
            'website_sale_order': order,
            'errors': self._get_shop_payment_errors(order),
            'partner': order.partner_invoice_id,
            'order': order,
            'submit_button_label': _("Pay now"),
        }
        payment_form_values = {
            **sale_portal.CustomerPortal._get_payment_values(
                self, order, website_id=request.website.id
            ),
            'display_submit_button': False,  # The submit button is re-added outside the form.
            'transaction_route': f'/shop/payment/transaction/{order.id}',
            'landing_route': '/shop/payment/validate',
            'sale_order_id': order.id,  # Allow Stripe to check if tokenization is required.
        }
        return checkout_page_values | payment_form_values

    def _get_shop_payment_errors(self, order):
        """ Check that there is no error that should block the payment.

        :param sale.order order: The sales order to pay
        :return: A list of errors (error_title, error_message)
        :rtype: list[tuple]
        """
        errors = []

        if order._has_deliverable_products() and not order._get_delivery_methods():
            errors.append((
                _("Sorry, we are unable to ship your order."),
                _("No shipping method is available for your current order and shipping address."
                  " Please contact us for more information."),
            ))
        return errors

    @route('/shop/payment', type='http', auth='public', website=True, sitemap=False, list_as_website_content=_lt("Shop Payment"))
    def shop_payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.provider. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.provider website but closed the tab without
           paying / canceling
        """
        order_sudo = request.cart

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        order_sudo._recompute_cart()
        render_values = self._get_shop_payment_values(order_sudo, **post)
        render_values['only_services'] = order_sudo and order_sudo.only_services

        if render_values['errors']:
            render_values.pop('payment_methods_sudo', '')
            render_values.pop('tokens_sudo', '')

        render_values.update(request.website._get_checkout_step_values())

        return request.render("website_sale.payment", render_values)

    @route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        if sale_order_id is None:
            order_sudo = request.cart
            if not order_sudo and 'sale_last_order_id' in request.session:
                # Retrieve the last known order from the session if the session key `sale_order_id`
                # was prematurely cleared. This is done to prevent the user from updating their cart
                # after payment in case they don't return from payment through this route.
                last_order_id = request.session['sale_last_order_id']
                order_sudo = request.env['sale.order'].sudo().browse(last_order_id).exists()
        else:
            order_sudo = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order_sudo.id == request.session.get('sale_last_order_id')

        if not order_sudo:
            return request.redirect(self._get_shop_path())

        errors = self._get_shop_payment_errors(order_sudo) if order_sudo.state != 'sale' else []
        if errors:
            first_error = errors[0]  # only display first error
            error_msg = f"{first_error[0]}\n{first_error[1]}"
            raise ValidationError(error_msg)

        tx_sudo = order_sudo.get_portal_last_transaction()
        if order_sudo.amount_total and not tx_sudo:
            return request.redirect(self._get_shop_path())

        if not order_sudo.amount_total and not tx_sudo and order_sudo.state != 'sale':
            # Only confirm the order if it wasn't already confirmed.
            order_sudo._validate_order()

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx_sudo and tx_sudo.state == 'draft':
            return request.redirect(self._get_shop_path())

        return request.redirect('/shop/confirmation')

    @route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False, list_as_website_content=_lt("Shop Confirmation"))
    def shop_payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            values = self._prepare_shop_payment_confirmation_values(order)
            return request.render("website_sale.confirmation", values)
        return request.redirect(self._get_shop_path())

    def _prepare_shop_payment_confirmation_values(self, order):
        """
        This method is called in the payment process route in order to prepare the dict
        containing the values to be rendered by the confirmation template.
        """
        return {
            'order': order,
            'website_sale_order': order,
            'order_tracking_info': self.order_2_return_dict(order),
        }

    @route(['/shop/print'], type='http', auth="public", website=True, sitemap=False)
    def print_saleorder(self, **kwargs):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sale.action_report_saleorder', [sale_order_id])
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', '%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        return request.redirect(self._get_shop_path())

    # === CHECK METHODS === #

    def _check_cart_and_addresses(self, order_sudo):
        """ Check whether the cart and its addresses are valid, and redirect to the appropriate page
        if not.

        :param sale.order order_sudo: The cart to check.
        :return: None if both the cart and its addresses are valid; otherwise, a redirection to the
                 appropriate page.
        """
        if redirection := self._check_cart(order_sudo):
            return redirection

        if redirection := self._check_addresses(order_sudo):
            return redirection

    def _check_cart(self, order_sudo):
        """ Check whether the cart is a valid, and redirect to the appropriate page if not.

        The cart is only valid if:

        - it exists and is in the draft state;
        - it contains products (i.e., order lines);
        - either the user is logged in, or public orders are allowed.

        :param sale.order order_sudo: The cart to check.
        :return: None if the cart is valid; otherwise, a redirection to the appropriate page.
        """
        # Check that the cart exists and is in the draft state.
        if not order_sudo or order_sudo.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect(self._get_shop_path())

        # Check that the cart is not empty.
        if not order_sudo.order_line:
            return request.redirect('/shop/cart')

        # Check that public orders are allowed.
        if request.env.user._is_public() and request.website.account_on_checkout == 'mandatory':
            return request.redirect('/web/login?redirect=/shop/checkout')

    def _check_addresses(self, order_sudo):
        """ Check whether the cart's addresses are complete and valid.

        The addresses are complete and valid if:

        - at least one address has been added;
        - the delivery address is complete;
        - the billing address is complete.

        :param sale.order order_sudo: The cart whose addresses to check.
        None if the cart is valid; otherwise, a redirection to the appropriate page.
        :return: None if the cart's addresses are complete and valid; otherwise, a redirection to
                 the appropriate page.
        """
        # Check that an address has been added.
        if order_sudo._is_anonymous_cart():
            return request.redirect('/shop/address')

        # Check that the delivery address is complete.
        delivery_partner_sudo = order_sudo.partner_shipping_id
        if (
            not order_sudo.only_services
            and not self._check_delivery_address(delivery_partner_sudo)
            and delivery_partner_sudo._can_be_edited_by_current_customer(order_sudo=order_sudo)
        ):
            return request.redirect(
                f'/shop/address?partner_id={delivery_partner_sudo.id}&address_type=delivery'
            )
        # Check that the billing address is complete.
        invoice_partner_sudo = order_sudo.partner_invoice_id
        if (
            not self._check_billing_address(invoice_partner_sudo)
            and invoice_partner_sudo._can_be_edited_by_current_customer(order_sudo=order_sudo)
        ):
            return request.redirect(
                f'/shop/address?partner_id={invoice_partner_sudo.id}&address_type=billing'
            )

    # ------------------------------------------------------
    # Edit
    # ------------------------------------------------------

    @route(['/shop/config/product'], type='jsonrpc', auth='user')
    def change_product_config(self, product_id, **options):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        product = request.env['product.template'].browse(product_id)
        if "sequence" in options:
            sequence = options["sequence"]
            if sequence == "top":
                product.set_sequence_top()
            elif sequence == "bottom":
                product.set_sequence_bottom()
            elif sequence == "up":
                product.set_sequence_up()
            elif sequence == "down":
                product.set_sequence_down()
        if {"x", "y"} <= set(options):
            product.write({'website_size_x': options["x"], 'website_size_y': options["y"]})

    @route(['/shop/config/attribute'], type='jsonrpc', auth='user')
    def change_attribute_config(self, attribute_id, **options):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        attribute = request.env['product.attribute'].browse(attribute_id)
        if 'display_type' in options:
            attribute.write({'display_type': options['display_type']})
            request.env.registry.clear_cache('templates')

    @route(['/shop/config/website'], type='jsonrpc', auth='user')
    def _change_website_config(self, **options):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        current_website = request.env['website'].get_current_website()
        # Restrict options we can write to.
        writable_fields = {
            'shop_ppg', 'shop_ppr', 'shop_default_sort', 'shop_gap',
            'product_page_image_layout', 'product_page_image_width',
            'product_page_grid_columns', 'product_page_image_spacing'
        }
        # Default ppg to 1.
        if 'ppg' in options and not options['ppg']:
            options['ppg'] = 1
        if 'product_page_grid_columns' in options:
            options['product_page_grid_columns'] = int(options['product_page_grid_columns'])

        # Checkout Extra Step
        if 'extra_step' in options:
            extra_step_view = current_website.viewref('website_sale.extra_info')
            extra_step = current_website._get_checkout_step('/shop/extra_info')
            extra_step_view.active = extra_step.is_published = options.get('extra_step') == 'true'

        write_vals = {k: v for k, v in options.items() if k in writable_fields}
        if write_vals:
            current_website.write(write_vals)

    def order_lines_2_google_api(self, order_lines):
        """ Transforms a list of order lines into a dict for google analytics """
        ret = []
        for line in order_lines.filtered(lambda line: not line.is_delivery):
            product = line.product_id
            ret.append({
                'item_id': product.barcode or product.id,
                'item_name': product.name or '-',
                'item_category': product.categ_id.name or '-',
                'price': line.price_unit,
                'quantity': line.product_uom_qty,
            })
        return ret

    def order_2_return_dict(self, order):
        """ Returns the tracking_cart dict of the order for Google analytics basically defined to be inherited """
        tracking_cart_dict = {
            'transaction_id': order.id,
            'affiliation': order.company_id.name,
            'value': order.amount_total,
            'tax': order.amount_tax,
            'currency': order.currency_id.name,
            'items': self.order_lines_2_google_api(order.order_line),
        }
        delivery_line = order.order_line.filtered('is_delivery')
        if delivery_line:
            tracking_cart_dict['shipping'] = delivery_line.price_unit
        return tracking_cart_dict

    # --------------------------------------------------------------------------
    # Products Recently Viewed
    # --------------------------------------------------------------------------
    @route('/shop/products/recently_viewed_update', type='jsonrpc', auth='public', website=True)
    def products_recently_viewed_update(self, product_id, **kwargs):
        res = {}
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._add_viewed_product(product_id)
        return res

    @route('/shop/products/recently_viewed_delete', type='jsonrpc', auth='public', website=True)
    def products_recently_viewed_delete(self, product_id=None, product_template_id=None, **kwargs):
        if not (product_id or product_template_id):
            return
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            domain = [('visitor_id', '=', visitor_sudo.id)]
            if product_id:
                domain += [('product_id', '=', int(product_id))]
            else:
                domain += [('product_id.product_tmpl_id', '=', int(product_template_id))]
            request.env['website.track'].sudo().search(domain).unlink()
        return {}

    @route('/snippets/category/set_image', type='jsonrpc', auth='user')
    def set_category_image(self, category_id, attachment_id):
        """
        Set the cover image on the category.

        :param int category_id: ID of the category to set the cover image.
        :param int attachment_id: ID of the attachment containing the image data.
        :raise Forbidden: If the user does not have website editing access
        """
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise Forbidden()
        category = request.env['product.public.category'].browse(category_id).exists()
        if category:
            image_data = request.env['ir.attachment'].browse(attachment_id).datas
            category.cover_image = image_data

    @staticmethod
    def _populate_currency_and_pricelist(kwargs):
        website = request.website
        kwargs.update({
            'currency_id': website.currency_id.id,
            'pricelist_id': request.pricelist.id,
        })

    @staticmethod
    def _validate_and_get_category(category):
        """ Validate and return the `product.public.category` record corresponding to the provided
        category, which can be a record, a record id, or a slug.

        - If no category is provided, return an empty recordset.
        - If a category is provided, but it doesn't exist or can't be accessed, raise a 404.
        - If a valid category is provided, return the corresponding record.

        :param str|product.public.category category: The category to validate and return.
        :return: The validated category.
        :rtype: product.public.category
        """
        ProductCategory = request.env['product.public.category']
        if (
            (category := ProductCategory.browse(category and int(category)).exists())
            and category.can_access_from_current_website()
        ):
            return category
        else:
            return ProductCategory

    @staticmethod
    def _get_shop_path(category=None, page=0):
        path = SHOP_PATH
        if category:
            slug = request.env['ir.http']._slug
            path += f'/category/{slug(category)}'
        if page:
            path += f'/page/{page}'
        return path

    @staticmethod
    def _get_product_path(product, category=None):
        slug = request.env['ir.http']._slug
        path = SHOP_PATH
        if category:
            path += f'/{slug(category)}'
        path += f'/{slug(product)}'
        return path

    @staticmethod
    def _get_filtered_query_string(query_string, keys_to_remove):
        """ Return a filtered copy of the provided query string, where all keys in `keys_to_remove`
        are removed.

        Note: the query string shouldn't include the leading '?'.

        :param str query_string: The query string to filter.
        :param list(str) keys_to_remove: The keys to remove from the query string.
        :return: The filtered query string.
        :rtype: str
        """
        query = urls.url_parse(f'?{query_string}').decode_query()
        for key in keys_to_remove:
            query.pop(key, False)
        return urls.url_encode(query)

    @staticmethod
    def _get_attribute_value_dict(attribute_values):
        """ Parses a list of attribute value query params, and returns a dict grouping attribute
        value ids by attribute id.

        :param list(str) attribute_values: The list of attribute value query parameters to parse.
        :return: A dict grouping attribute value ids by attribute id.
        :rtype: dict(int, list(int))
        """
        attribute_value_pairs = [value.split('-') for value in attribute_values if value]
        return {
            int(pair[0]): [int(value_id) for value_id in pair[1].split(',')]
            for pair in attribute_value_pairs
        }
