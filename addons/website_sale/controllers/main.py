# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from datetime import datetime
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_decode, url_encode, url_parse

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.fields import Command
from odoo.http import request, route
from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.website.controllers import main
from odoo.addons.website.controllers.form import WebsiteForm
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.osv import expression
from odoo.tools import lazy, str2bool
from odoo.tools.json import scriptsafe as json_scriptsafe

_logger = logging.getLogger(__name__)


class TableCompute(object):

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


class WebsiteSaleForm(WebsiteForm):

    @http.route('/website/form/shop.sale.order', type='http', auth="public", methods=['POST'], website=True)
    def website_form_saleorder(self, **kwargs):
        model_record = request.env.ref('sale.model_sale_order')
        try:
            data = self.extract_data(model_record, kwargs)
        except ValidationError as e:
            return json.dumps({'error_fields': e.args[0]})

        order = request.website.sale_get_order()
        if not order:
            return json.dumps({'error': "No order found; please add a product to your cart."})

        if data['record']:
            order.write(data['record'])

        if data['custom']:
            order._message_log(
                body=nl2br_enclose(data['custom'], 'p'),
                message_type='comment',
            )

        if data['attachments']:
            self.insert_attachment(model_record, order.id, data['attachments'])

        return json.dumps({'id': order.id})


class Website(main.Website):

    def _login_redirect(self, uid, redirect=None):
        # If we are logging in, clear the current pricelist to be able to find
        # the pricelist that corresponds to the user afterwards.
        request.session.pop('website_sale_current_pl', None)
        return super()._login_redirect(uid, redirect=redirect)

    @http.route()
    def autocomplete(self, search_type=None, term=None, order=None, limit=5, max_nb_chars=999, options=None):
        options = options or {}
        if 'display_currency' not in options:
            options['display_currency'] = request.website.currency_id
        return super().autocomplete(search_type, term, order, limit, max_nb_chars, options)

    @http.route()
    def theme_customize_data(self, is_view_data, enable=None, disable=None, reset_view_arch=False):
        super().theme_customize_data(is_view_data, enable, disable, reset_view_arch)
        if any(key in enable or key in disable for key in ['website_sale.products_list_view', 'website_sale.add_grid_or_list_option']):
            request.session.pop('website_sale_shop_layout_mode', None)

    @http.route()
    def get_current_currency(self, **kwargs):
        return {
            'id': request.website.currency_id.id,
            'symbol': request.website.currency_id.symbol,
            'position': request.website.currency_id.position,
        }

class WebsiteSale(payment_portal.PaymentPortal):
    _express_checkout_route = '/shop/express_checkout'
    _express_checkout_shipping_route = '/shop/express/shipping_address_change'

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

    def _get_shop_domain(self, search, category, attrib_values, search_in_description=True):
        domains = [request.website.sale_product_domain()]
        if search:
            for srch in search.split(" "):
                subdomains = [
                    [('name', 'ilike', srch)],
                    [('product_variant_ids.default_code', 'ilike', srch)]
                ]
                if search_in_description:
                    subdomains.append([('website_description', 'ilike', srch)])
                    subdomains.append([('description_sale', 'ilike', srch)])
                domains.append(expression.OR(subdomains))

        if category:
            domains.append([('public_categ_ids', 'child_of', int(category))])

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

        return expression.AND(domains)

    def sitemap_shop(env, rule, qs):
        if not qs or qs.lower() in '/shop':
            yield {'loc': '/shop'}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for cat in Category.search(dom):
            loc = '/shop/category/%s' % slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _get_search_options(
        self, category=None, attrib_values=None, tags=None, min_price=0.0, max_price=0.0,
        conversion_rate=1, **post
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
            'attrib_values': attrib_values,
            'display_currency': post.get('display_currency'),
        }

    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        # No limit because attributes are obtained from complete product list
        product_count, details, fuzzy_search_term = website._search_with_fuzzy("products_only", search,
                                                                               limit=None,
                                                                               order=self._get_search_order(post),
                                                                               options=options)
        search_result = details[0].get('results', request.env['product.template']).with_context(bin_size=True)

        return fuzzy_search_term, product_count, search_result

    def _shop_get_query_url_kwargs(
        self, category, search, min_price, max_price, attrib=None, order=None, tags=None, **post
    ):
        return {
            'category': category,
            'search': search,
            'attrib': attrib,
            'tags': tags,
            'min_price': min_price,
            'max_price': max_price,
            'order': order,
        }

    def _get_additional_shop_values(self, values):
        """ Hook to update values used for rendering website_sale.products template """
        return {}

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_shop)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        website = request.env['website'].get_current_website()
        website_domain = website.website_domain()
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.shop_ppg or 20

        ppr = website.shop_ppr or 4

        request_args = request.httprequest.args
        attrib_list = request_args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        filter_by_tags_enabled = website.is_view_active('website_sale.filter_products_tags')
        if filter_by_tags_enabled:
            tags = request_args.getlist('tags')
            # Allow only numeric tag values to avoid internal error.
            if tags and all(tag.isnumeric() for tag in tags):
                post['tags'] = tags
                tags = {int(tag) for tag in tags}
            else:
                post['tags'] = None
                tags = {}

        keep = QueryURL('/shop', **self._shop_get_query_url_kwargs(category and int(category), search, min_price, max_price, **post))

        now = datetime.timestamp(datetime.now())
        pricelist = website.pricelist_id
        if 'website_sale_pricelist_time' in request.session:
            # Check if we need to refresh the cached pricelist
            pricelist_save_time = request.session['website_sale_pricelist_time']
            if pricelist_save_time < now - 60*60:
                request.session.pop('website_sale_current_pl', None)
                website.invalidate_recordset(['pricelist_id'])
                pricelist = website.pricelist_id
                request.session['website_sale_pricelist_time'] = now
                request.session['website_sale_current_pl'] = pricelist.id
        else:
            request.session['website_sale_pricelist_time'] = now
            request.session['website_sale_current_pl'] = pricelist.id

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            company_currency = website.company_id.currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, website.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        url = '/shop'
        if search:
            post['search'] = search
        if attrib_list:
            post['attrib'] = attrib_list

        options = self._get_search_options(
            category=category,
            attrib_values=attrib_values,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            display_currency=website.currency_id,
            **post
        )
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(attrib_set, options, post, search, website)

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            Product = request.env['product.template'].with_context(bin_size=True)
            domain = self._get_shop_domain(search, category, attrib_values)

            # This is ~4 times more efficient than a search for the cheapest and most expensive products
            query = Product._where_calc(domain)
            Product._apply_ir_rules(query, 'read')
            from_clause, where_clause, where_params = query.get_sql()
            query = f"""
                SELECT COALESCE(MIN(list_price), 0) * {conversion_rate}, COALESCE(MAX(list_price), 0) * {conversion_rate}
                  FROM {from_clause}
                 WHERE {where_clause}
            """
            request.env.cr.execute(query, where_params)
            available_min_price, available_max_price = request.env.cr.fetchone()

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
            all_tags = ProductTag.search(
                expression.AND([
                    [('product_ids.is_published', '=', True), ('visible_on_ecommerce', '=', True)],
                    website_domain
                ])
            )
        else:
            all_tags = ProductTag

        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain
            ).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        if category:
            url = "/shop/category/%s" % slug(category)

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
            attributes = lazy(lambda: ProductAttribute.browse(attributes_ids))

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        # Try to fetch geoip based fpos or fallback on partner one
        fiscal_position_sudo = website.fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position_sudo))

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'fiscal_position': fiscal_position_sudo,
            'add_qty': add_qty,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': tools.float_round,
        }
        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = tools.float_round(available_min_price, 2)
            values['available_max_price'] = tools.float_round(available_max_price, 2)
        if filter_by_tags_enabled:
            values.update({'all_tags': all_tags, 'tags': tags})
        if category:
            values['main_object'] = category
        values.update(self._get_additional_shop_values(values))
        return request.render("website_sale.products", values)

    @http.route(['/shop/<model("product.template"):product>'], type='http', auth="public", website=True, sitemap=True)
    def product(self, product, category='', search='', **kwargs):
        return request.render("website_sale.product", self._prepare_product_values(product, category, search, **kwargs))

    @http.route(
        '/shop/<model("product.template"):product_template>/document/<int:document_id>',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def product_document(self, product_template, document_id):
        product_template.check_access_rights('read')

        document = request.env['product.document'].browse(document_id).sudo().exists()
        if not document or not document.active:
            return request.redirect('/shop')

        if not document.shown_on_product_page or not (
            document.res_id == product_template.id
            and document.res_model == 'product.template'
        ):
            return request.redirect('/shop')

        return request.env['ir.binary']._get_stream_from(
            document.ir_attachment_id,
        ).get_response(as_attachment=True)

    @http.route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True, sitemap=False)
    def old_product(self, product, category='', search='', **kwargs):
        # Compatibility pre-v14
        return request.redirect(_build_url_w_params("/shop/%s" % slug(product), request.params), code=301)

    @http.route(['/shop/product/extra-images'], type='json', auth='user', website=True)
    def add_product_images(self, images, product_product_id, product_template_id, combination_ids=None):
        """
        Turns a list of image ids refering to ir.attachments to product.images,
        links all of them to product.
        :raises NotFound : If the user is not allowed to access Attachment model
        """

        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        image_ids = request.env["ir.attachment"].browse(i['id'] for i in images)
        image_create_data = [Command.create({
                    'name': image.name,                          # Images uploaded from url do not have any datas. This recovers them manually
                    'image_1920': image.datas if image.datas else request.env['ir.qweb.field.image'].load_remote_url(image.url),
                }) for image in image_ids]

        product_product = request.env['product.product'].browse(int(product_product_id)) if product_product_id else False
        product_template = request.env['product.template'].browse(int(product_template_id)) if product_template_id else False

        if product_product and not product_template:
            product_template = product_product.product_tmpl_id

        if not product_product and product_template and product_template.has_dynamic_attributes():
            combination = request.env['product.template.attribute.value'].browse(combination_ids)
            product_product = product_template._get_variant_for_combination(combination)
            if not product_product:
                product_product = product_template._create_product_variant(combination)
        if product_template.has_configurable_attributes and product_product:
            product_product.write({
                'product_variant_image_ids': image_create_data
            })
        else:
            product_template.write({
                'product_template_image_ids': image_create_data
            })

    @http.route(['/shop/product/clear-images'], type='json', auth='user', website=True)
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

    @http.route(['/shop/product/resequence-image'], type='json', auth='user', website=True)
    def resequence_product_image(self, image_res_model, image_res_id, move):
        if (
            not request.env.user.has_group('website.group_website_restricted_editor')
            or image_res_model not in ['product.product', 'product.template', 'product.image']
            or move not in ['first', 'left', 'right', 'last']
        ):
            raise NotFound()

        image_res_id = int(image_res_id)
        image_to_resequence = request.env[image_res_model].browse(image_res_id)
        product = request.env['product.product']
        product_template = request.env['product.template']
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
        # We can not move an embedded image to the first position (main product image)
        if image_res_model == 'product.image' and image_to_resequence.video_url and product_images[new_image_idx]._name != 'product.image':
            raise ValidationError(_("Can not resequence embedded image/video with a non compatible image."))

        # Swap images
        other_image = product_images[new_image_idx]
        source_field = hasattr(image_to_resequence, 'video_url') and image_to_resequence.video_url and 'video_url' or 'image_1920'
        target_field = hasattr(other_image, 'video_url') and other_image.video_url and 'video_url' or 'image_1920'
        if target_field == 'video_url' and image_res_model == 'product.product':
            raise ValidationError(_("Can not resequence a video at first position."))
        previous_data = other_image[target_field]
        other_image[source_field] = image_to_resequence[source_field]
        image_to_resequence[target_field] = previous_data
        if source_field == 'video_url' and target_field != 'video_url':
            image_to_resequence.video_url = False
        if target_field == 'video_url' and source_field != 'video_url':
            other_image.video_url = False

        if hasattr(other_image, 'video_url'):
            other_image._onchange_video_url()
        if hasattr(image_to_resequence, 'video_url'):
            image_to_resequence._onchange_video_url()

    @http.route(['/shop/product/is_add_to_cart_allowed'], type='json', auth="public", website=True)
    def is_add_to_cart_allowed(self, product_id, **kwargs):
        product = request.env['product.product'].browse(product_id)
        return product._is_add_to_cart_allowed()

    def _product_get_query_url_kwargs(self, category, search, attrib=None, **kwargs):
        return {
            'category': category,
            'search': search,
            'attrib': attrib,
            'tags': kwargs.get('tags'),
            'min_price': kwargs.get('min_price'),
            'max_price': kwargs.get('max_price'),
        }

    def _prepare_product_values(self, product, category, search, **kwargs):
        ProductCategory = request.env['product.public.category']

        if category:
            category = ProductCategory.browse(int(category)).exists()

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attrib_set = {v[1] for v in attrib_values}

        keep = QueryURL(
            '/shop',
            **self._product_get_query_url_kwargs(
                category=category and category.id,
                search=search,
                **kwargs,
            ),
        )

        # Needed to trigger the recently viewed product rpc
        view_track = request.website.viewref("website_sale.product").track

        return {
            'search': search,
            'category': category,
            'pricelist': request.website.pricelist_id,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': ProductCategory.search([('parent_id', '=', False)]),
            'main_object': product,
            'product': product,
            'add_qty': 1,
            'view_track': view_track,
        }

    @http.route(['/shop/change_pricelist/<model("product.pricelist"):pricelist>'], type='http', auth="public", website=True, sitemap=False)
    def pricelist_change(self, pricelist, **post):
        website = request.env['website'].get_current_website()
        redirect_url = request.httprequest.referrer
        if (pricelist.selectable or pricelist == request.env.user.partner_id.property_product_pricelist) \
                and website.is_pricelist_available(pricelist.id):
            if redirect_url and request.website.is_view_active('website_sale.filter_products_price'):
                decoded_url = url_parse(redirect_url)
                args = url_decode(decoded_url.query)
                min_price = args.get('min_price')
                max_price = args.get('max_price')
                if min_price or max_price:
                    previous_price_list = request.website.pricelist_id
                    try:
                        min_price = float(min_price)
                        args['min_price'] = min_price and str(
                            previous_price_list.currency_id._convert(min_price, pricelist.currency_id, request.website.company_id, fields.Date.today(), round=False)
                        )
                    except (ValueError, TypeError):
                        pass
                    try:
                        max_price = float(max_price)
                        args['max_price'] = max_price and str(
                            previous_price_list.currency_id._convert(max_price, pricelist.currency_id, request.website.company_id, fields.Date.today(), round=False)
                        )
                    except (ValueError, TypeError):
                        pass
                    redirect_url = decoded_url.replace(query=url_encode(args)).to_url()
            request.session['website_sale_current_pl'] = pricelist.id
            request.website.sale_get_order(update_pricelist=True)
        return request.redirect(redirect_url or '/shop')

    @http.route(['/shop/pricelist'], type='http', auth="public", website=True, sitemap=False)
    def pricelist(self, promo, **post):
        redirect = post.get('r', '/shop/cart')
        # empty promo code is used to reset/remove pricelist (see `sale_get_order()`)
        if promo:
            pricelist_sudo = request.env['product.pricelist'].sudo().search([('code', '=', promo)], limit=1)
            if not (pricelist_sudo and request.website.is_pricelist_available(pricelist_sudo.id)):
                return request.redirect("%s?code_not_available=1" % redirect)

            request.session['website_sale_current_pl'] = pricelist_sudo.id
            # TODO find the best way to create the order with the correct pricelist directly ?
            # not really necessary, but could avoid one write on SO record
            order_sudo = request.website.sale_get_order(force_create=True)
            order_sudo._cart_update_pricelist(pricelist_id=pricelist_sudo.id)
        else:
            order_sudo = request.website.sale_get_order()
            if order_sudo:
                order_sudo._cart_update_pricelist(update_pricelist=True)
        return request.redirect(redirect)

    def _cart_values(self, **post):
        """
        This method is a hook to pass additional values when rendering the 'website_sale.cart' template (e.g. add
        a flag to trigger a style variation)
        """
        return {}

    @http.route(['/shop/cart'], type='http', auth="public", website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        """
        Main cart management + abandoned cart revival
        access_token: Abandoned cart SO access token
        revive: Revival method when abandoned cart. Can be 'merge' or 'squash'
        """
        order = request.website.sale_get_order()
        if order and order.carrier_id:
            # Express checkout is based on the amout of the sale order. If there is already a
            # delivery line, Express Checkout form will display and compute the price of the
            # delivery two times (One already computed in the total amount of the SO and one added
            # in the form while selecting the delivery carrier)
            order._remove_delivery_line()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()

        request.session['website_sale_cart_quantity'] = order.cart_quantity

        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                raise NotFound()
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive == 'squash' or (revive == 'merge' and not request.session.get('sale_order_id')):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session.get('sale_order_id'):  # abandoned cart found, user have to choose what to do
                values.update({'access_token': abandoned_order.access_token})

        values.update({
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': [],
        })
        if order:
            order.order_line.filtered(lambda l: not l.product_id.active).unlink()
            values['suggested_products'] = order._cart_accessories()
            values.update(self._get_express_shop_payment_values(order))

        values.update(self._cart_values(**post))
        return request.render("website_sale.cart", values)

    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(
        self, product_id, add_qty=1, set_qty=0,
        product_custom_attribute_values=None, no_variant_attribute_values=None,
        express=False, **kwargs
    ):
        """This route is called when adding a product to cart (no options)."""
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)

        if product_custom_attribute_values:
            product_custom_attribute_values = json_scriptsafe.loads(product_custom_attribute_values)

        if no_variant_attribute_values:
            no_variant_attribute_values = json_scriptsafe.loads(no_variant_attribute_values)

        sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values,
            **kwargs
        )

        request.session['website_sale_cart_quantity'] = sale_order.cart_quantity

        if express:
            return request.redirect("/shop/checkout?express=1")

        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(
        self, product_id, line_id=None, add_qty=None, set_qty=None, display=True,
        product_custom_attribute_values=None, no_variant_attribute_values=None, **kw
    ):
        """
        This route is called :
            - When changing quantity from the cart.
            - When adding a product from the wishlist.
            - When adding a product to cart on the same page (without redirection).
        """
        order = request.website.sale_get_order(force_create=True)
        if order.state != 'draft':
            request.website.sale_reset()
            if kw.get('force_create'):
                order = request.website.sale_get_order(force_create=True)
            else:
                return {}

        if product_custom_attribute_values:
            product_custom_attribute_values = json_scriptsafe.loads(product_custom_attribute_values)

        if no_variant_attribute_values:
            no_variant_attribute_values = json_scriptsafe.loads(no_variant_attribute_values)

        values = order._cart_update(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values,
            **kw
        )

        values['notification_info'] = self._get_cart_notification_information(order, [values['line_id']])
        values['notification_info']['warning'] = values.pop('warning', '')
        request.session['website_sale_cart_quantity'] = order.cart_quantity

        if not order.cart_quantity:
            request.website.sale_reset()
            return values

        values['cart_quantity'] = order.cart_quantity
        values['minor_amount'] = payment_utils.to_minor_currency_units(
            order.amount_total, order.currency_id
        ),
        values['amount'] = order.amount_total

        if not display:
            return values

        values['cart_ready'] = order._is_cart_ready()
        values['website_sale.cart_lines'] = request.env['ir.ui.view']._render_template(
            "website_sale.cart_lines", {
                'website_sale_order': order,
                'date': fields.Date.today(),
                'suggested_products': order._cart_accessories()
            }
        )
        values['website_sale.total'] = request.env['ir.ui.view']._render_template(
            "website_sale.total", {
                'website_sale_order': order,
            }
        )
        return values

    @http.route('/shop/save_shop_layout_mode', type='json', auth='public', website=True)
    def save_shop_layout_mode(self, layout_mode):
        assert layout_mode in ('grid', 'list'), "Invalid shop layout mode"
        request.session['website_sale_shop_layout_mode'] = layout_mode

    @http.route(['/shop/cart/quantity'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_quantity(self):
        if 'website_sale_cart_quantity' not in request.session:
            return request.website.sale_get_order().cart_quantity
        return request.session['website_sale_cart_quantity']

    @http.route(['/shop/cart/clear'], type='json', auth="public", website=True)
    def clear_cart(self):
        order = request.website.sale_get_order()
        for line in order.order_line:
            line.unlink()

    def _get_cart_notification_information(self, order, line_ids):
        """ Get the information about the sale order line to show in the notification.

        :param recordset order: The sale order containing the lines.
        :param list(int) line_ids: The ids of the lines to display in the notification.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'currency_id': int
                'lines': [{
                    'id': int
                    'image_url': int
                    'quantity': float
                    'name': str
                    'description': str
                    'line_price_total': float
                }],
            }
        """
        lines = order.order_line.filtered(lambda line: line.id in line_ids)
        if not lines:
            return {}

        show_tax = order.website_id.show_line_subtotals_tax_selection == 'tax_included'
        return {
            'currency_id': order.currency_id.id,
            'lines': [
                { # For the cart_notification
                    'id': line.id,
                    'image_url': order.website_id.image_url(line.product_id, 'image_128'),
                    'quantity': line.product_uom_qty,
                    'name': line.name_short,
                    'description': line._get_sale_order_line_multiline_description_variants(),
                    'line_price_total': line.price_total if show_tax else line.price_subtotal,
                } for line in lines
            ],
        }

    # ------------------------------------------------------
    # Checkout
    # ------------------------------------------------------

    def checkout_check_address(self, order):
        partner_invoice = order.partner_invoice_id
        if not self._check_billing_partner_mandatory_fields(partner_invoice):
            return request.redirect('/shop/address?partner_id=%d&mode=billing' % partner_invoice.id)

        partner_shipping = order.partner_shipping_id
        if not order.only_services and not self._check_shipping_partner_mandatory_fields(partner_shipping):
            return request.redirect('/shop/address?partner_id=%d&mode=shipping' % partner_shipping.id)

    def checkout_redirection(self, order):
        # must have a draft sales order with lines at this point, otherwise reset
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        if order and not order.order_line:
            return request.redirect('/shop/cart')

        if request.website.is_public_user() and request.website.account_on_checkout == 'mandatory':
            return request.redirect('/web/login?redirect=/shop/checkout')

        # if transaction pending / done: redirect to confirmation
        tx = request.env.context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    def checkout_values(self, order, **kw):
        order = order or request.website.sale_get_order(force_create=True)
        bill_partners = []
        ship_partners = []
        if not order._is_public_order():
            Partner = order.partner_id.with_context(show_address=1).sudo()
            commercial_partner = order.partner_id.commercial_partner_id
            bill_partners = Partner.search([
                ("id", "child_of", commercial_partner.ids),
                '|', ("type", "in", ["invoice", "other"]), ("id", "=", commercial_partner.id)
            ], order='id desc') | order.partner_id
            ship_partners = Partner.search([
                ("id", "child_of", commercial_partner.ids),
                '|', ("type", "in", ["delivery", "other"]), ("id", "=", commercial_partner.id)
            ], order='id desc') | order.partner_id

            # do not show commercial_partner_id if its mandatory fields are not complete to children
            # as children can not edit (fill) the commercial_partner_id
            if commercial_partner != order.partner_id:
                if not self._check_billing_partner_mandatory_fields(commercial_partner):
                    bill_partners = bill_partners.filtered(lambda p: p.id != commercial_partner.id)

                if not self._check_shipping_partner_mandatory_fields(commercial_partner):
                    ship_partners = ship_partners.filtered(lambda p: p.id != commercial_partner.id)

        return {
            'order': order,
            'website_sale_order': order,
            'shippings': ship_partners,
            'billings': bill_partners,
            'only_services': order and order.only_services or False
        }

    def _check_billing_partner_mandatory_fields(self, partner_id):
        ''' return True if all mandatory fields for billing address are complete '''
        billing_fields_required = self._get_mandatory_fields_billing(partner_id.country_id.id)
        return all(partner_id.read(billing_fields_required)[0].values())

    def _get_mandatory_fields_billing(self, country_id=False):
        req = ["name", "email", "street", "city", "country_id"]
        if country_id:
            country = request.env['res.country'].browse(country_id)
            if country.state_required:
                req += ['state_id']
            if country.zip_required:
                req += ['zip']
        return req

    def _check_shipping_partner_mandatory_fields(self, partner_id):
        ''' return True if all mandatory fields for shipping address are complete '''
        shipping_fields_required = self._get_mandatory_fields_shipping(partner_id.country_id.id)
        return all(partner_id.read(shipping_fields_required)[0].values())

    def _get_mandatory_fields_shipping(self, country_id=False):
        req = ["name", "street", "city", "country_id", "phone"]
        if country_id:
            country = request.env['res.country'].browse(country_id)
            if country.state_required:
                req += ['state_id']
            if country.zip_required:
                req += ['zip']
        return req

    def checkout_form_validate(self, mode, all_form_values, data):
        # mode: tuple ('new|edit', 'billing|shipping')
        # all_form_values: all values before preprocess
        # data: values after preprocess
        error = dict()
        error_message = []

        if data.get('partner_id'):
            partner_su = request.env['res.partner'].sudo().browse(int(data['partner_id'])).exists()
            if partner_su:
                name_change = 'name' in data and partner_su.name and data['name'] != partner_su.name
                email_change = 'email' in data and partner_su.email and data['email'] != partner_su.email

                # Prevent changing the partner name if invoices have been issued.
                if name_change and not partner_su._can_edit_name():
                    error['name'] = 'error'
                    error_message.append(_(
                        "Changing your name is not allowed once invoices have been issued for your"
                        " account. Please contact us directly for this operation."
                    ))

                # Prevent change the partner name or email if it is an internal user.
                if (name_change or email_change) and not all(partner_su.user_ids.mapped('share')):
                    error.update({
                        'name': 'error' if name_change else None,
                        'email': 'error' if email_change else None,
                    })
                    error_message.append(_(
                        "If you are ordering for an external person, please place your order via the"
                        " backend. If you wish to change your name or email address, please do so in"
                        " the account settings or contact your administrator."
                    ))

        # Required fields from form
        required_fields = [f for f in (all_form_values.get('field_required') or '').split(',') if f]

        # Required fields from mandatory field function
        country_id = int(data.get('country_id', False))

        _update_mode, address_mode = mode
        if address_mode == 'shipping':
            required_fields += self._get_mandatory_fields_shipping(country_id)
        else: # 'billing'
            required_fields += self._get_mandatory_fields_billing(country_id)
            if all_form_values.get('use_same'):
                # If the billing address is also used as shipping one, the phone is required as well
                # because it's required for shipping addresses
                required_fields.append('phone')

        # error message for empty required fields
        for field_name in required_fields:
            val = data.get(field_name)
            if isinstance(val, str):
                val = val.strip()
            if not val:
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # vat validation
        Partner = request.env['res.partner']
        if data.get("vat") and hasattr(Partner, "check_vat"):
            if country_id:
                data["vat"] = Partner.fix_eu_vat_number(country_id, data.get("vat"))
            partner_dummy = Partner.new(self._get_vat_validation_fields(data))
            try:
                partner_dummy.sudo().check_vat()
            except ValidationError as exception:
                error["vat"] = 'error'
                error_message.append(exception.args[0])

        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))

        return error, error_message

    def _get_vat_validation_fields(self, data):
        return {
            'vat': data['vat'],
            'country_id': int(data['country_id']) if data.get('country_id') else False,
        }

    def _checkout_form_save(self, mode, checkout, all_values):
        Partner = request.env['res.partner']
        if mode[0] == 'new':
            partner_id = Partner.sudo().with_context(tracking_disable=True).create(checkout).id
        elif mode[0] == 'edit':
            partner_id = int(all_values.get('partner_id', 0))
            if partner_id:
                # double check
                order = request.website.sale_get_order()
                shippings = Partner.sudo().search([("id", "child_of", order.partner_id.commercial_partner_id.ids)])
                if partner_id not in shippings.mapped('id') and partner_id != order.partner_id.id:
                    return Forbidden()
                Partner.browse(partner_id).sudo().write(checkout)
        return partner_id

    def values_preprocess(self, values):
        new_values = dict()
        partner_fields = request.env['res.partner']._fields

        for k, v in values.items():
            # Convert the values for many2one fields to integer since they are used as IDs
            if k in partner_fields and partner_fields[k].type == 'many2one':
                new_values[k] = bool(v) and int(v)
            # Store empty fields as `False` instead of empty strings `''` for consistency with other applications like
            # Contacts.
            elif v == '':
                new_values[k] = False
            else:
                new_values[k] = v

        return new_values

    def values_postprocess(self, order, mode, values, errors, error_msg):
        new_values = {}
        authorized_fields = request.env['ir.model']._get('res.partner')._get_form_writable_fields()
        for k, v in values.items():
            # don't drop empty value, it could be a field to reset
            if k in authorized_fields and v is not None:
                new_values[k] = v
            else:  # DEBUG ONLY
                if k not in ('field_required', 'partner_id', 'callback', 'submitted'): # classic case
                    _logger.debug("website_sale postprocess: %s value has been dropped (empty or not writable)" % k)

        if request.website.specific_user_account:
            new_values['website_id'] = request.website.id

        update_mode, address_mode = mode
        if update_mode == 'new':
            commercial_partner = order.partner_id.commercial_partner_id
            lang = request.lang.code if request.lang.code in request.website.mapped('language_ids.code') else None
            if lang:
                new_values['lang'] = lang
            new_values['company_id'] = request.website.company_id.id
            new_values['team_id'] = request.website.salesteam_id and request.website.salesteam_id.id
            new_values['user_id'] = request.website.salesperson_id.id

            if address_mode == 'billing':
                is_public_order = order._is_public_order()
                if is_public_order:
                    # New billing address of public customer will be their contact address.
                    new_values['type'] = 'contact'
                elif values.get('use_same'):
                    new_values['type'] = 'other'
                else:
                    new_values['type'] = 'invoice'

                # for public user avoid linking to default archived 'Public user' partner
                if commercial_partner.active:
                    new_values['parent_id'] = commercial_partner.id
            elif address_mode == 'shipping':
                new_values['type'] = 'delivery'
                new_values['parent_id'] = commercial_partner.id
        return new_values, errors, error_msg

    @http.route(['/shop/address'], type='http', methods=['GET', 'POST'], auth="public", website=True, sitemap=False)
    def address(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        can_edit_vat = False
        values, errors = {}, {}

        partner_id = int(kw.get('partner_id', -1))
        if order._is_public_order():
            mode = ('new', 'billing')
            can_edit_vat = True
        else:  # IF ORDER LINKED TO A PARTNER
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    # If we modify the main customer of the SO ->
                    # 'billing' bc billing requirements are higher than shipping ones
                    can_edit_vat = order.partner_id.can_edit_vat()
                    mode = ('edit', 'billing')
                else:
                    address_mode = kw.get('mode')
                    if not address_mode:
                        if partner_id == order.partner_invoice_id.id:
                            address_mode = 'billing'
                        elif partner_id == order.partner_shipping_id.id:
                            address_mode = 'shipping'

                    # Make sure the address exists and belongs to the customer of the SO
                    partner_sudo = Partner.browse(partner_id).exists()
                    partners_sudo = Partner.search(
                        [('id', 'child_of', order.partner_id.commercial_partner_id.ids)]
                    )
                    mode = ('edit', address_mode)
                    if address_mode == 'billing':
                        billing_partners = partners_sudo.filtered(lambda p: p.type != 'delivery')
                        if partner_sudo not in billing_partners:
                            raise Forbidden()
                    elif address_mode == 'shipping':
                        shipping_partners = partners_sudo.filtered(lambda p: p.type != 'invoice')
                        if partner_sudo not in shipping_partners:
                            raise Forbidden()

                    can_edit_vat = partner_sudo.can_edit_vat()

                if mode and partner_id != -1:
                    values = Partner.browse(partner_id)
            elif partner_id == -1:
                mode = ('new', kw.get('mode') or 'shipping')
            else: # no mode - refresh without post?
                return request.redirect('/shop/checkout')

        # IF POSTED
        if 'submitted' in kw and request.httprequest.method == "POST":
            pre_values = self.values_preprocess(kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)

            if errors:
                errors['error_message'] = error_msg
                values = kw
            else:
                update_mode, address_mode = mode
                partner_id = self._checkout_form_save(mode, post, kw)
                # We need to validate _checkout_form_save return, because when partner_id not in shippings
                # it returns Forbidden() instead the partner_id
                if isinstance(partner_id, Forbidden):
                    return partner_id

                fpos_before = order.fiscal_position_id
                update_values = {}
                if update_mode == 'new':  # New address
                    if order._is_public_order():
                        update_values['partner_id'] = partner_id

                    if address_mode == 'billing':
                        update_values['partner_invoice_id'] = partner_id
                        if kw.get('use_same'):
                            update_values['partner_shipping_id'] = partner_id
                        elif (
                            order._is_public_order()
                            and not kw.get('callback')
                            and not order.only_services
                        ):
                            # Now that the billing is set, if shipping is necessary
                            # request the customer to fill the shipping address
                            kw['callback'] = '/shop/address'
                    elif address_mode == 'shipping':
                        update_values['partner_shipping_id'] = partner_id
                elif update_mode == 'edit':  # Updating an existing address
                    if order.partner_id.id == partner_id:
                        # Editing the main partner of the SO --> also trigger a partner update to
                        # recompute fpos & any partner-related fields
                        update_values['partner_id'] = partner_id

                    if address_mode == 'billing':
                        update_values['partner_invoice_id'] = partner_id
                        if not kw.get('callback') and not order.only_services:
                            kw['callback'] = '/shop/checkout'
                    elif address_mode == 'shipping':
                        update_values['partner_shipping_id'] = partner_id

                order.write(update_values)

                if order.fiscal_position_id != fpos_before:
                    # Recompute taxes on fpos change
                    # TODO recompute all prices too to correctly manage price_include taxes ?
                    order._recompute_taxes()

                if 'partner_id' in update_values:
                    # Force recomputation of pricelist on main customer address update
                    request.website.sale_get_order(update_pricelist=True)

                # TDE FIXME: don't ever do this
                # -> TDE: you are the guy that did what we should never do in commit e6f038a
                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]
                if not errors:
                    return request.redirect(kw.get('callback') or '/shop/confirm_order')

        is_public_user = request.website.is_public_user()
        render_values = {
            'website_sale_order': order,
            'partner_id': partner_id,
            'mode': mode,
            'checkout': values,
            'can_edit_vat': can_edit_vat,
            'error': errors,
            'callback': kw.get('callback'),
            'only_services': order and order.only_services,
            'account_on_checkout': request.website.account_on_checkout,
            'is_public_user': is_public_user,
            'is_public_order': order._is_public_order(),
            'use_same': is_public_user or ('use_same' in kw and str2bool(kw.get('use_same'))),
        }
        render_values.update(self._get_country_related_render_values(kw, render_values))
        return request.render("website_sale.address", render_values)

    @http.route(
        _express_checkout_route, type='json', methods=['POST'], auth="public", website=True,
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

        order_sudo = request.website.sale_get_order()
        public_partner = request.website.partner_id

        # Update the partner with all the information
        self._include_country_and_state_in_address(billing_address)
        if order_sudo.partner_id == public_partner:
            billing_partner_id = self._create_or_edit_partner(billing_address, type='invoice')
            order_sudo.partner_id = billing_partner_id
            # Pricelist are recomputed every time the partner is changed. We don't want to recompute
            # the price with another pricelist at this state since the customer has already accepted
            # the amount and validated the payment.
            order_sudo.env.remove_to_compute(
                order_sudo.env['sale.order']._fields['pricelist_id'], order_sudo
            )
            order_sudo.message_partner_ids = request.env['res.partner'].browse(billing_partner_id)
        elif any(billing_address[k] != order_sudo.partner_invoice_id[k] for k in billing_address):
            # Check if a child partner doesn't already exist with the same informations. The
            # phone isn't always checked because it isn't sent in shipping information with
            # Google Pay.
            child_partner_id = self._find_child_partner(
                order_sudo.partner_id.commercial_partner_id.id, billing_address
            )
            order_sudo.partner_invoice_id = child_partner_id or self._create_or_edit_partner(
                billing_address, type='invoice', parent_id=order_sudo.partner_id.id
            )

        # In a non-express flow, `sale_last_order_id` would be added in the session before the
        # payment. As we skip all the steps with the express checkout, `sale_last_order_id` must be
        # assigned to ensure the right behavior from `shop_payment_confirmation()`.
        request.session['sale_last_order_id'] = order_sudo.id

        if shipping_address:
            #in order to not override shippig address, it's checked separately from shipping option
            self._include_country_and_state_in_address(shipping_address)

            if order_sudo.partner_shipping_id.name.endswith(order_sudo.name):
                # The existing partner was created by `process_express_checkout_delivery_choice`, it
                # means that the partner is missing information, so we update it.
                order_sudo.partner_shipping_id = self._create_or_edit_partner(
                    shipping_address,
                    edit=True,
                    type='delivery',
                    partner_id=order_sudo.partner_shipping_id.id,
                )
            elif any(
                shipping_address[k] != order_sudo.partner_shipping_id[k] for k in shipping_address
            ):
                # The sale order's shipping partner's address is different from the one received. If
                # all the sale order's child partners' address differs from the one received, we
                # create a new partner. The phone isn't always checked because it isn't sent in
                # shipping information with Google Pay.
                child_partner_id = self._find_child_partner(
                    order_sudo.partner_id.commercial_partner_id.id, shipping_address
                )
                order_sudo.partner_shipping_id = child_partner_id or self._create_or_edit_partner(
                    shipping_address, type='delivery', parent_id=order_sudo.partner_id.id
                )
            # Process the delivery carrier
            if shipping_option:
                order_sudo._check_carrier_quotation(force_carrier_id=int(shipping_option['id']))

        return order_sudo.partner_id.id

    def _find_child_partner(self, commercial_partner_id, address):
        """ Find a child partner for a specified address

        Compare all keys in the `address` dict with the same keys on the partner object and return
        the id of the first partner that have the same value than in the dict for all the keys.

        :param int commercial_partner_id: commercial partner for whom we need to find his children.
        :param dict address: dictionary of address fields.
        :return int: id of the first child partner that match the criteria, if any.
        """
        partners_sudo = request.env['res.partner'].with_context(show_address=1).sudo().search([
            ('id', 'child_of', commercial_partner_id),
        ])
        for partner_sudo in partners_sudo:
            if all(address[k] == partner_sudo[k] for k in address):
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
        state = request.env["res.country.state"].search([
            ('code', '=', address.pop('state', '')),
        ], limit=1)
        address.update(country_id=country, state_id=state)

    def _create_or_edit_partner(self, partner_details, edit=False, **custom_values):
        """ Create or update a partner

        To create a partner, this controller usually calls `values_preprocess()`, then
        `checkout_form_validate()`, then `values_postprocess()` and finally `_checkout_form_save()`.
        Since these methods are very specific to the checkout form, this method makes it possible to
        create  a partner for more specific flows like express payment, which does not require all
        the checks carried out by the previous methods. Parts of code in this method come from those.

        :param dict partner_details: The values needed to create the partner or to edit the partner.
        :param bool edit: Whether edit an existing partner or create one, defaults to False.
        :param dict custom_values: Optional custom values for the creation or edition.
        :return int: The id of the partner created or edited
        """
        request.update_env(context=request.website.env.context)
        values = self.values_preprocess(partner_details)

        # Ensure that we won't write on unallowed fields.
        sanitized_values = {
            k: v for k, v in values.items() if k in self.WRITABLE_PARTNER_FIELDS
        }
        sanitized_custom_values = {
            k: v for k, v in custom_values.items()
            if k in self.WRITABLE_PARTNER_FIELDS + ['partner_id', 'parent_id', 'type']
        }

        if request.website.specific_user_account:
            sanitized_values['website_id'] = request.website.id

        lang = request.lang.code if request.lang.code in request.website.mapped(
            'language_ids.code'
        ) else None
        if lang:
            sanitized_values['lang'] = lang

        partner_id = sanitized_custom_values.get('partner_id')
        if edit and partner_id:
            request.env['res.partner'].browse(partner_id).sudo().write(sanitized_values)
        else:
            sanitized_values = dict(sanitized_values, **{
                'company_id': request.website.company_id.id,
                'team_id': request.website.salesteam_id and request.website.salesteam_id.id,
                'user_id': request.website.salesperson_id.id,
                **sanitized_custom_values
            })
            partner_id = request.env['res.partner'].sudo().with_context(
                tracking_disable=True
            ).create(sanitized_values).id
        return partner_id

    def _get_country_related_render_values(self, kw, render_values):
        """ Provide the fields related to the country to render the website sale form """
        values = render_values['checkout']
        mode = render_values['mode']
        order = render_values['website_sale_order']

        def_country_id = order.partner_id.country_id
        if order._is_public_order():
            if request.geoip.country_code:
                def_country_id = request.env['res.country'].search([('code', '=', request.geoip.country_code)], limit=1)
            else:
                def_country_id = request.website.user_id.sudo().country_id

        country = 'country_id' in values and values['country_id'] != '' and request.env['res.country'].browse(int(values['country_id']))
        country = country and country.exists() or def_country_id

        res = {
            'country': country,
            'country_states': country.get_website_sale_states(mode=mode[1]),
            'countries': country.get_website_sale_countries(mode=mode[1]),
        }
        return res

    @http.route(['/shop/checkout'], type='http', auth="public", website=True, sitemap=False)
    def checkout(self, **post):
        order_sudo = request.website.sale_get_order()

        redirection = self.checkout_redirection(order_sudo)
        if redirection:
            return redirection

        if order_sudo._is_public_order():
            return request.redirect('/shop/address')

        redirection = self.checkout_check_address(order_sudo)
        if redirection:
            return redirection

        if post.get('express'):
            return request.redirect('/shop/confirm_order')

        values = self.checkout_values(order_sudo, **post)

        # Avoid useless rendering if called in ajax
        if post.get('xhr'):
            return 'ok'
        return request.render("website_sale.checkout", values)

    @route('/shop/cart/update_address', type='http', auth='public', methods=['POST'], website=True)
    def update_cart_address(self, partner_id, mode='billing', **kw):
        partner_id = int(partner_id)

        order_sudo = request.website.sale_get_order()
        if not order_sudo:
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

        fpos_before = order_sudo.fiscal_position_id
        if (
            mode == 'billing'
            and partner_sudo != order_sudo.partner_invoice_id
        ):
            order_sudo.partner_invoice_id = partner_id
        elif (
            mode == 'shipping'
            and partner_sudo != order_sudo.partner_shipping_id
        ):
            order_sudo.partner_shipping_id = partner_id
        else:
            # TODO someday we should gracefully handle invalid addresses
            return

        if fpos_before != order_sudo.fiscal_position_id:
            # TODO recompute full cart amounts to correctly handle price_include taxes stuff ?
            order_sudo._recompute_taxes()

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True, sitemap=False)
    def confirm_order(self, **post):
        order = request.website.sale_get_order()

        redirection = self.checkout_redirection(order) or self.checkout_check_address(order)
        if redirection:
            return redirection

        order.order_line._compute_tax_id()
        request.session['sale_last_order_id'] = order.id
        request.website.sale_get_order(update_pricelist=True)
        extra_step = request.website.viewref('website_sale.extra_info')
        if extra_step.active:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")

    # ------------------------------------------------------
    # Extra step
    # ------------------------------------------------------
    @http.route(['/shop/extra_info'], type='http', auth="public", website=True, sitemap=False)
    def extra_info(self, **post):
        # Check that this option is activated
        extra_step = request.website.viewref('website_sale.extra_info')
        if not extra_step.active:
            return request.redirect("/shop/payment")

        # check that cart is valid
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        open_editor = request.params.get('open_editor') == 'true'
        # Do not redirect if it is to edit
        # (the information is transmitted via the "open_editor" parameter in the url)
        if not open_editor and redirection:
            return redirection

        values = {
            'website_sale_order': order,
            'post': post,
            'escape': lambda x: x.replace("'", r"\'"),
            'partner': order.partner_id.id,
            'order': order,
        }
        return request.render("website_sale.extra_info", values)

    # ------------------------------------------------------
    # Payment
    # ------------------------------------------------------

    def _get_express_shop_payment_values(self, order, **kwargs):
        payment_form_values = sale_portal.CustomerPortal._get_payment_values(
            self, order, website_id=request.website.id, is_express_checkout=True
        )
        payment_form_values.update({
            'payment_access_token': payment_form_values.pop('access_token'),  # Rename the key.
            'minor_amount': payment_utils.to_minor_currency_units(
                order.amount_total, order.currency_id
            ),
            'merchant_name': request.website.name,
            'transaction_route': f'/shop/payment/transaction/{order.id}',
            'express_checkout_route': self._express_checkout_route,
            'landing_route': '/shop/payment/validate',
            'payment_method_unknown_id': request.env.ref('payment.payment_method_unknown').id,
        })
        if request.website.is_public_user():
            payment_form_values['partner_id'] = -1
        if request.website.enabled_delivery:
            payment_form_values.update({
                'shipping_info_required': not order.only_services,
                'shipping_address_update_route': self._express_checkout_shipping_route,
            })
        return payment_form_values

    def _get_shop_payment_values(self, order, **kwargs):
        checkout_page_values = {
            'website_sale_order': order,
            'errors': [],
            'partner': order.partner_invoice_id,
            'order': order,
            'submit_button_label': _("Pay now"),
            'payment_action_id': request.env.ref('payment.action_payment_provider').id,
            'action_activate_stripe_id': request.env.ref(
                'website_payment.action_activate_stripe'
            ).id,
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
        values = {**checkout_page_values, **payment_form_values}
        if request.website.enabled_delivery:
            has_storable_products = any(
                line.product_id.type in ['consu', 'product'] for line in order.order_line
            )
            if not order._get_delivery_methods() and has_storable_products:
                values['errors'].append((
                    _('Sorry, we are unable to ship your order'),
                    _('No shipping method is available for your current order and shipping address.'
                    ' Please contact us for more information.')
                ))

            if has_storable_products:
                if order.carrier_id and not order.delivery_rating_success:
                    order._remove_delivery_line()
                    order._check_carrier_quotation()
                values['deliveries'] = order._get_delivery_methods().sudo()

            values['delivery_has_storable'] = has_storable_products
            values['delivery_action_id'] = request.env.ref(
                'delivery.action_delivery_carrier_form'
            ).id

        return values

    @http.route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.provider. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.provider website but closed the tab without
           paying / canceling
        """
        order = request.website.sale_get_order()

        if order and (request.httprequest.method == 'POST' or not order.carrier_id):
            # Update order's carrier_id (will be the one of the partner if not defined)
            # If a carrier_id is (re)defined, redirect to "/shop/payment" (GET method to avoid infinite loop)
            carrier_id = post.get('carrier_id')
            keep_carrier = post.get('keep_carrier', False)
            if keep_carrier:
                keep_carrier = bool(int(keep_carrier))
            if carrier_id:
                carrier_id = int(carrier_id)
            order._check_carrier_quotation(force_carrier_id=carrier_id, keep_carrier=keep_carrier)
            if carrier_id:
                return request.redirect("/shop/payment")

        redirection = self.checkout_redirection(order) or self.checkout_check_address(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False

        if render_values['errors']:
            render_values.pop('payment_methods_sudo', '')
            render_values.pop('tokens_sudo', '')

        return request.render("website_sale.payment", render_values)

    @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        if sale_order_id is None:
            order = request.website.sale_get_order()
            if not order and 'sale_last_order_id' in request.session:
                # Retrieve the last known order from the session if the session key `sale_order_id`
                # was prematurely cleared. This is done to prevent the user from updating their cart
                # after payment in case they don't return from payment through this route.
                last_order_id = request.session['sale_last_order_id']
                order = request.env['sale.order'].sudo().browse(last_order_id).exists()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        tx_sudo = order.get_portal_last_transaction() if order else order.env['payment.transaction']

        if not order or (order.amount_total and not tx_sudo):
            return request.redirect('/shop')

        if order and not order.amount_total and not tx_sudo:
            order.with_context(send_email=True).with_user(SUPERUSER_ID).action_confirm()
            return request.redirect(order.get_portal_url())

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx_sudo and tx_sudo.state == 'draft':
            return request.redirect('/shop')

        return request.redirect('/shop/confirmation')

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
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
        else:
            return request.redirect('/shop')

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

    @http.route(['/shop/print'], type='http', auth="public", website=True, sitemap=False)
    def print_saleorder(self, **kwargs):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sale.action_report_saleorder', [sale_order_id])
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', u'%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            return request.redirect('/shop')

    # ------------------------------------------------------
    # Edit
    # ------------------------------------------------------

    @http.route(['/shop/config/product'], type='json', auth='user')
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

    @http.route(['/shop/config/attribute'], type='json', auth='user')
    def change_attribute_config(self, attribute_id, **options):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        attribute = request.env['product.attribute'].browse(attribute_id)
        if 'display_type' in options:
            attribute.write({'display_type': options['display_type']})
            request.env.registry.clear_cache('templates')

    @http.route(['/shop/config/website'], type='json', auth='user')
    def _change_website_config(self, **options):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        current_website = request.env['website'].get_current_website()
        # Restrict options we can write to.
        writable_fields = {
            'shop_ppg', 'shop_ppr', 'shop_default_sort',
            'product_page_image_layout', 'product_page_image_width',
            'product_page_grid_columns', 'product_page_image_spacing'
        }
        # Default ppg to 1.
        if 'ppg' in options and not options['ppg']:
            options['ppg'] = 1
        if 'product_page_grid_columns' in options:
            options['product_page_grid_columns'] = int(options['product_page_grid_columns'])

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

    @http.route(['/shop/country_infos/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], website=True)
    def country_infos(self, country, mode, **kw):
        return dict(
            fields=country.get_address_fields(),
            states=[(st.id, st.name, st.code) for st in country.get_website_sale_states(mode=mode)],
            phone_code=country.phone_code,
            zip_required=country.zip_required,
            state_required=country.state_required,
        )

    # --------------------------------------------------------------------------
    # Products Recently Viewed
    # --------------------------------------------------------------------------
    @http.route('/shop/products/recently_viewed_update', type='json', auth='public', website=True)
    def products_recently_viewed_update(self, product_id, **kwargs):
        res = {}
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._add_viewed_product(product_id)
        return res

    @http.route('/shop/products/recently_viewed_delete', type='json', auth='public', website=True)
    def products_recently_viewed_delete(self, product_id, **kwargs):
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            request.env['website.track'].sudo().search([('visitor_id', '=', visitor_sudo.id), ('product_id', '=', product_id)]).unlink()
        return {}


class PaymentPortal(payment_portal.PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order_id):
        """
        Perform final checks against the transaction & sale_order.
        Override me to apply payment unrelated checks & processing
        """
        return

    @http.route(
        '/shop/payment/transaction/<int:order_id>', type='json', auth='public', website=True
    )
    def shop_payment_transaction(self, order_id, access_token, **kwargs):
        """ Create a draft transaction and return its processing values.

        :param int order_id: The sales order to pay, as a `sale.order` id
        :param str access_token: The access token used to authenticate the request
        :param dict kwargs: Locally unused data passed to `_create_transaction`
        :return: The mandatory values for the processing of the transaction
        :rtype: dict
        :raise: ValidationError if the invoice id or the access token is invalid
        """
        # Check the order id and the access token
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token)
        except MissingError as error:
            raise error
        except AccessError:
            raise ValidationError(_("The access token is invalid."))

        if order_sudo.state == "cancel":
            raise ValidationError(_("The order has been canceled."))

        order_sudo._check_cart_is_ready_to_be_paid()

        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            'partner_id': order_sudo.partner_invoice_id.id,
            'currency_id': order_sudo.currency_id.id,
            'sale_order_id': order_id,  # Include the SO to allow Subscriptions to tokenize the tx
        })
        if not kwargs.get('amount'):
            kwargs['amount'] = order_sudo.amount_total

        if tools.float_compare(kwargs['amount'], order_sudo.amount_total, precision_rounding=order_sudo.currency_id.rounding):
            raise ValidationError(_("The cart has been updated. Please refresh the page."))

        tx_sudo = self._create_transaction(
            custom_create_values={'sale_order_ids': [Command.set([order_id])]}, **kwargs,
        )

        # Store the new transaction into the transaction list and if there's an old one, we remove
        # it until the day the ecommerce supports multiple orders at the same time.
        request.session['__website_sale_last_tx_id'] = tx_sudo.id

        self._validate_transaction_for_order(tx_sudo, order_id)

        return tx_sudo._get_processing_values()


class CustomerPortal(sale_portal.CustomerPortal):

    def _get_payment_values(self, order_sudo, website_id=None, **kwargs):
        """ Override of `sale` to inject the `website_id` into the kwargs.

        :param sale.order order_sudo: The sales order being paid.
        :param int website_id: The website on which the order was made, if any, as a `website` id.
        :param dict kwargs: Locally unused keywords arguments.
        :return: The payment-specific values.
        :rtype: dict
        """
        website_id = website_id or order_sudo.website_id.id
        return super()._get_payment_values(order_sudo, website_id=website_id, **kwargs)

    def _sale_reorder_get_line_context(self):
        return {}

    @http.route('/my/orders/reorder_modal_content', type='json', auth='public', website=True)
    def my_orders_reorder_modal_content(self, order_id, access_token):
        try:
            sale_order = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        currency = request.env['website'].get_current_website().currency_id
        result = {
            'currency': currency.id,
            'products': [],
        }
        for line in sale_order.order_line:
            if line.display_type:
                continue
            if line._is_delivery():
                continue
            combination = line.product_id.product_template_attribute_value_ids | line.product_no_variant_attribute_value_ids
            res = {
                'product_template_id': line.product_id.product_tmpl_id.id,
                'product_id': line.product_id.id,
                'combination': combination.ids,
                'no_variant_attribute_values': [
                    { # Same input format as provided by product configurator
                        'value': ptav.id,
                    } for ptav in line.product_no_variant_attribute_value_ids
                ],
                'product_custom_attribute_values': [
                    { # Same input format as provided by product configurator
                        'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                        'custom_value': pcav.custom_value,
                    } for pcav in line.product_custom_attribute_value_ids
                ],
                'type': line.product_id.type,
                'name': line.name_short,
                'description_sale': line.product_id.description_sale or '' + line._get_sale_order_line_multiline_description_variants(),
                'qty': line.product_uom_qty,
                'add_to_cart_allowed': line.with_user(request.env.user).sudo()._is_reorder_allowed(),
                'has_image': bool(line.product_id.image_128),
            }
            if res['add_to_cart_allowed']:
                res['combinationInfo'] = line.product_id.product_tmpl_id.with_context(
                    **self._sale_reorder_get_line_context()
                )._get_combination_info(combination, res['product_id'], res['qty'])
            else:
                res['combinationInfo'] = {}
            result['products'].append(res)
        return result
