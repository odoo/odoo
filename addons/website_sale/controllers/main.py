# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime

from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_decode, url_encode, url_parse

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.http import request, route
from odoo.osv import expression
from odoo.tools import clean_context, float_round, groupby, lazy, single_email_re, str2bool, SQL
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom


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
                extra_subdomain = self._add_search_subdomains_hook(srch)
                if extra_subdomain:
                    subdomains.append(extra_subdomain)
                domains.append(expression.OR(subdomains))

        if category:
            domains.append([('public_categ_ids', 'child_of', int(category))])

        if attrib_values:
            domains.extend(request.env['product.template']._get_attrib_values_domain(attrib_values))

        return expression.AND(domains)

    def sitemap_shop(env, rule, qs):
        website = env['website'].get_current_website()
        if website and website.ecommerce_access == 'logged_in' and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        if not qs or qs.lower() in '/shop':
            yield {'loc': '/shop'}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        dom += website.website_domain()
        for cat in Category.search(dom):
            loc = '/shop/category/%s' % env['ir.http']._slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def sitemap_products(env, rule, qs):
        website = env['website'].get_current_website()
        if website and website.ecommerce_access == 'logged_in' and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        ProductTemplate = env['product.template']
        dom = sitemap_qs2dom(qs, '/shop', ProductTemplate._rec_name)
        dom += website.sale_product_domain()
        for product in ProductTemplate.search(dom):
            loc = '/shop/%s' % env['ir.http']._slug(product)
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
        self, category, search, min_price, max_price, order=None, tags=None, **post
    ):
        return {
            'category': category,
            'search': search,
            'tags': tags,
            'min_price': min_price,
            'max_price': max_price,
            'order': order,
        }

    def _get_additional_shop_values(self, values):
        """ Hook to update values used for rendering website_sale.products template """
        return {}

    def _get_additional_extra_shop_values(self, values, **post):
        """ Hook to update values used for rendering website_sale.products template """
        return self._get_additional_shop_values(values)

    @route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_shop)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        if not request.website.has_ecommerce_access():
            return request.redirect('/web/login')
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

        gap = website.shop_gap or "16px"

        request_args = request.httprequest.args
        attrib_list = request_args.getlist('attribute_value')
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
            company_currency = website.company_id.sudo().currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, website.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        url = '/shop'
        if search:
            post['search'] = search

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
            url = "/shop/category/%s" % request.env['ir.http']._slug(category)

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

        products_prices = lazy(lambda: products._get_sales_prices(website))

        attributes_values = request.env['product.attribute.value'].browse(attrib_set)
        sorted_attributes_values = attributes_values.sorted('sequence')
        multi_attributes_values = sorted_attributes_values.filtered(lambda av: av.display_type == 'multi')
        single_attributes_values = sorted_attributes_values - multi_attributes_values
        grouped_attributes_values = list(groupby(single_attributes_values, lambda av: av.attribute_id.id))
        grouped_attributes_values.extend([(av.attribute_id.id, [av]) for av in multi_attributes_values])

        selected_attributes_hash = grouped_attributes_values and "#attribute_values=%s" % (
            ','.join(str(v[0].id) for k, v in grouped_attributes_values)
        ) or ''

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
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
        values.update(self._get_additional_extra_shop_values(values, **post))
        return request.render("website_sale.products", values)

    @route(['/shop/<model("product.template"):product>'], type='http', auth="public", website=True, sitemap=sitemap_products)
    def product(self, product, category='', search='', **kwargs):
        if not request.website.has_ecommerce_access():
            return request.redirect('/web/login')

        return request.render("website_sale.product", self._prepare_product_values(product, category, search, **kwargs))

    @route(
        '/shop/<model("product.template"):product_template>/document/<int:document_id>',
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def product_document(self, product_template, document_id):
        product_template.check_access('read')

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

    @route(['/shop/product/<model("product.template"):product>'], type='http', auth="public", website=True, sitemap=False)
    def old_product(self, product, category='', search='', **kwargs):
        # Compatibility pre-v14
        return request.redirect(_build_url_w_params("/shop/%s" % request.env['ir.http']._slug(product), request.params), code=301)

    @route(['/shop/product/extra-images'], type='json', auth='user', website=True)
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

    @route(['/shop/product/clear-images'], type='json', auth='user', website=True)
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

    @route(['/shop/product/resequence-image'], type='json', auth='user', website=True)
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

    @route(['/shop/product/is_add_to_cart_allowed'], type='json', auth="public", website=True)
    def is_add_to_cart_allowed(self, product_id, **kwargs):
        product = request.env['product.product'].browse(product_id)
        return product._is_add_to_cart_allowed()

    def _product_get_query_url_kwargs(self, category, search, **kwargs):
        return {
            'category': category,
            'search': search,
            'tags': kwargs.get('tags'),
            'min_price': kwargs.get('min_price'),
            'max_price': kwargs.get('max_price'),
        }

    def _prepare_product_values(self, product, category, search, **kwargs):
        ProductCategory = request.env['product.public.category']
        if category:
            category = ProductCategory.browse(int(category)).exists()
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
            'keep': keep,
            'categories': ProductCategory.search([('parent_id', '=', False)]),
            'main_object': product,
            'optional_product_ids': [
                p.with_context(active_id=p.id) for p in product.optional_product_ids
            ],
            'product': product,
            'view_track': view_track,
        }

    @route(['/shop/change_pricelist/<model("product.pricelist"):pricelist>'], type='http', auth="public", website=True, sitemap=False)
    def pricelist_change(self, pricelist, **post):
        website = request.env['website'].get_current_website()
        redirect_url = request.httprequest.referrer
        if (
            website.is_pricelist_available(pricelist.id)
            and (
                pricelist.selectable
                or pricelist == request.env.user.partner_id.property_product_pricelist
            )
        ):
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
            order_sudo = request.website.sale_get_order()
            if order_sudo:
                order_sudo._cart_update_pricelist(pricelist_id=pricelist.id)
        return request.redirect(redirect_url or '/shop')

    @route(['/shop/pricelist'], type='http', auth="public", website=True, sitemap=False)
    def pricelist(self, promo, **post):
        redirect = post.get('r', '/shop/cart')
        # empty promo code is used to reset/remove pricelist (see `sale_get_order()`)
        if promo:
            pricelist_sudo = request.env['product.pricelist'].sudo().search([('code', '=', promo)], limit=1)
            if not (pricelist_sudo and request.website.is_pricelist_available(pricelist_sudo.id)):
                return request.redirect("%s?code_not_available=1" % redirect)

            request.session['website_sale_current_pl'] = pricelist_sudo.id
            order_sudo = request.website.sale_get_order()
            if order_sudo:
                order_sudo._cart_update_pricelist(pricelist_id=pricelist_sudo.id)
        else:
            # Reset the pricelist if empty promo code is given
            request.session.pop('website_sale_current_pl', None)
            order_sudo = request.website.sale_get_order()
            if order_sudo:
                pl_before = order_sudo.pricelist_id
                order_sudo._compute_pricelist_id()
                if order_sudo.pricelist_id != pl_before:
                    order_sudo._recompute_prices()
        return request.redirect(redirect)

    def _cart_values(self, **post):
        """
        This method is a hook to pass additional values when rendering the 'website_sale.cart' template (e.g. add
        a flag to trigger a style variation)
        """
        return {}

    @route(['/shop/cart'], type='http', auth="public", website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        """
        Main cart management + abandoned cart revival
        access_token: Abandoned cart SO access token
        revive: Revival method when abandoned cart. Can be 'merge' or 'squash'
        """
        if not request.website.has_ecommerce_access():
            return request.redirect('/web/login')

        order = request.website.sale_get_order()
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
            order.order_line.filtered(lambda sol: sol.product_id and not sol.product_id.active).unlink()
            values['suggested_products'] = order._cart_accessories()
            values.update(self._get_express_shop_payment_values(order))

        values.update(self._cart_values(**post))
        return request.render("website_sale.cart", values)

    @route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(
        self, product_id, add_qty=1, set_qty=0, product_custom_attribute_values=None,
        no_variant_attribute_value_ids=None, **kwargs
    ):
        """This route is called when adding a product to cart (no options)."""
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)

        if product_custom_attribute_values:
            product_custom_attribute_values = json_scriptsafe.loads(product_custom_attribute_values)

        # old API, will be dropped soon with product configurator refactorings
        no_variant_attribute_values = kwargs.pop('no_variant_attribute_values', None)
        if no_variant_attribute_values and no_variant_attribute_value_ids is None:
            no_variants_attribute_values_data = json_scriptsafe.loads(no_variant_attribute_values)
            no_variant_attribute_value_ids = [
                int(ptav_data['value']) for ptav_data in no_variants_attribute_values_data
            ]

        sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            **kwargs
        )

        request.session['website_sale_cart_quantity'] = sale_order.cart_quantity

        return request.redirect("/shop/cart")

    @route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True)
    def cart_update_json(
        self, product_id, line_id=None, add_qty=None, set_qty=None, display=True,
        product_custom_attribute_values=None, no_variant_attribute_value_ids=None, **kwargs
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
            if kwargs.get('force_create'):
                order = request.website.sale_get_order(force_create=True)
            else:
                return {}

        if product_custom_attribute_values:
            product_custom_attribute_values = json_scriptsafe.loads(product_custom_attribute_values)

        # old API, will be dropped soon with product configurator refactorings
        no_variant_attribute_values = kwargs.pop('no_variant_attribute_values', None)
        if no_variant_attribute_values and no_variant_attribute_value_ids is None:
            no_variants_attribute_values_data = json_scriptsafe.loads(no_variant_attribute_values)
            no_variant_attribute_value_ids = [
                int(ptav_data['value']) for ptav_data in no_variants_attribute_values_data
            ]

        values = order._cart_update(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            **kwargs
        )
        # If the line is a combo product line, and it already has combo items, we need to update
        # the combo item quantities as well.
        line = request.env['sale.order.line'].browse(values['line_id'])
        if line.product_type == 'combo' and line.linked_line_ids:
            for linked_line_id in line.linked_line_ids:
                if values['quantity'] != linked_line_id.product_uom_qty:
                    order._cart_update(
                        product_id=linked_line_id.product_id.id,
                        line_id=linked_line_id.id,
                        set_qty=values['quantity'],
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
        )
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

    @route('/shop/save_shop_layout_mode', type='json', auth='public', website=True)
    def save_shop_layout_mode(self, layout_mode):
        assert layout_mode in ('grid', 'list'), "Invalid shop layout mode"
        request.session['website_sale_shop_layout_mode'] = layout_mode

    @route(['/shop/cart/quantity'], type='json', auth="public", methods=['POST'], website=True)
    def cart_quantity(self):
        if 'website_sale_cart_quantity' not in request.session:
            return request.website.sale_get_order().cart_quantity
        return request.session['website_sale_cart_quantity']

    @route(['/shop/cart/clear'], type='json', auth="public", website=True)
    def clear_cart(self):
        order = request.website.sale_get_order()
        for line in order.order_line:
            line.unlink()

    def _get_cart_notification_information(self, order, line_ids):
        """ Get the information about the sale order lines to show in the notification.

        :param recordset order: The sale order containing the lines.
        :param list(int) line_ids: The ids of the lines to display in the notification.
        :rtype: dict
        :return: A dict with the following structure:
            {
                'currency_id': int
                'lines': [{
                    'id': int
                    'linked_line_id': int
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
                    'quantity': line._get_displayed_quantity(),
                    'name': line.name_short,
                    'description': line._get_sale_order_line_multiline_description_variants(),
                    'line_price_total': line.price_total if show_tax else line.price_subtotal,
                    **self._get_additional_notification_information(line),
                } for line in lines
            ],
        }

    def _get_additional_notification_information(self, line):
        # Only set the linked line id for combo items, not for optional products.
        if line.combo_item_id:
            return {'linked_line_id': line.linked_line_id.id}
        return {}

    # ------------------------------------------------------
    # Checkout
    # ------------------------------------------------------

    # === CHECKOUT FLOW - ADDRESS METHODS === #

    @route(
        '/shop/checkout', type='http', methods=['GET'], auth='public', website=True, sitemap=False
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
        order_sudo = request.website.sale_get_order()
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

        if try_skip_step and can_skip_delivery:
            return request.redirect('/shop/confirm_order')

        return request.render('website_sale.checkout', checkout_page_values)

    def _prepare_checkout_page_values(self, order_sudo, **_kwargs):
        """ Prepare and return the values to use to render the checkout page.

        :param sale.order order_sudo: The current cart.
        :return: The checkout page values.
        :rtype: dict
        """
        PartnerSudo = order_sudo.partner_id.with_context(show_address=1)
        commercial_partner_sudo = order_sudo.partner_id.commercial_partner_id
        billing_partners_sudo = PartnerSudo.search([
            ('id', 'child_of', commercial_partner_sudo.ids),
            '|',
            ('type', 'in', ['invoice', 'other']),
            ('id', '=', commercial_partner_sudo.id),
        ], order='id desc') | order_sudo.partner_id
        delivery_partners_sudo = PartnerSudo.search([
            ('id', 'child_of', commercial_partner_sudo.ids),
            '|',
            ('type', 'in', ['delivery', 'other']),
            ('id', '=', commercial_partner_sudo.id),
        ], order='id desc') | order_sudo.partner_id

        if order_sudo.partner_id != commercial_partner_sudo:  # Child of the commercial partner.
            # Don't display the commercial partner's addresses if they are not complete, as its
            # children can't edit them.
            if not self._check_billing_address(commercial_partner_sudo):
                billing_partners_sudo = billing_partners_sudo.filtered(
                    lambda p: p.id != commercial_partner_sudo.id
                )
            if not self._check_delivery_address(commercial_partner_sudo):
                delivery_partners_sudo = delivery_partners_sudo.filtered(
                    lambda p: p.id != commercial_partner_sudo.id
                )

        return {
            'order': order_sudo,
            'website_sale_order': order_sudo,  # Compatibility with other templates.
            'billing_addresses': billing_partners_sudo,
            'delivery_addresses': delivery_partners_sudo,
            'use_delivery_as_billing': (
                order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            ),
            'only_services': order_sudo.only_services,
            'json_pickup_location_data': json.dumps(order_sudo.pickup_location_data or {}),
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
        partner_id = partner_id and int(partner_id)
        use_delivery_as_billing = str2bool(use_delivery_as_billing or 'false')
        order_sudo = request.website.sale_get_order()

        if redirection := self._check_cart(order_sudo):
            return redirection

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id, address_type=address_type
        )

        if partner_sudo:  # If editing an existing partner.
            use_delivery_as_billing = (
                order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            )

        # Render the address form.
        address_form_values = self._prepare_address_form_values(
            order_sudo,
            partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            **query_params
        )
        return request.render('website_sale.address', address_form_values)

    def _prepare_address_form_values(
        self, order_sudo, partner_sudo, address_type, use_delivery_as_billing, callback='', **kwargs
    ):
        """ Prepare and return the values to use to render the address form.

        :param sale.order order_sudo: The current cart.
        :param partner_sudo: The partner whose address to update through the address form.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the
                                             billing and the delivery address.
        :param str callback:
        :return: The checkout page values.
        :rtype: dict
        """
        can_edit_vat = (
            (address_type == 'billing' or use_delivery_as_billing)
            and (not partner_sudo or partner_sudo.can_edit_vat())
        )
        is_anonymous_cart = order_sudo._is_anonymous_cart()

        ResCountrySudo = request.env['res.country'].sudo()
        country_sudo = partner_sudo.country_id
        if not country_sudo:
            if is_anonymous_cart:
                if request.geoip.country_code:
                    country_sudo = ResCountrySudo.search([
                        ('code', '=', request.geoip.country_code),
                    ], limit=1)
                else:
                    country_sudo = order_sudo.website_id.user_id.country_id
            else:
                country_sudo = order_sudo.partner_id.country_id

        state_id = partner_sudo.state_id.id

        address_fields = country_sudo and country_sudo.get_address_fields() or ['city', 'zip']

        return {
            'website_sale_order': order_sudo,
            'partner_sudo': partner_sudo,  # If set, customer is editing an existing address
            'partner_id': partner_sudo.id,
            'address_type': address_type,  # 'billing' or 'delivery'
            'can_edit_vat': can_edit_vat,
            'callback': callback,
            'only_services': order_sudo.only_services,
            'is_anonymous_cart': is_anonymous_cart,
            'use_delivery_as_billing': use_delivery_as_billing,
            'discard_url': is_anonymous_cart and '/shop/cart' or '/shop/checkout',
            'country': country_sudo,
            'countries': ResCountrySudo.search([]),
            'state_id': state_id,
            'country_states': country_sudo.state_ids,
            'zip_before_city': (
                'zip' in address_fields
                and address_fields.index('zip') < address_fields.index('city')
            ),
            'show_vat': (
                (address_type == 'billing' or use_delivery_as_billing)
                and (
                    is_anonymous_cart  # Allow inputting VAT on the new main address.
                    or (
                        partner_sudo == order_sudo.partner_id
                        and (can_edit_vat or partner_sudo.vat)
                    )  # On the main partner only, if the VAT was set.
                )
            ),
            'vat_label': request.env._("VAT"),
        }

    @route(
        '/shop/address/submit', type='http', methods=['POST'], auth='public', website=True,
        sitemap=False
    )
    def shop_address_submit(
        self, partner_id=None, address_type='billing', use_delivery_as_billing=None, callback=None,
        required_fields=None, **form_data
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
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param dict form_data: The form data to process as address values.
        :return: A JSON-encoded feedback, with either the success URL or an error message.
        :rtype: str
        """
        order_sudo = request.website.sale_get_order()
        if redirection := self._check_cart(order_sudo):
            return redirection

        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )
        use_delivery_as_billing = str2bool(use_delivery_as_billing or 'false')
        required_fields = required_fields or ''

        # Parse form data into address values, and extract incompatible data as extra form data.
        address_values, extra_form_data = self._parse_form_data(form_data)

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        is_main_address = is_anonymous_cart or order_sudo.partner_id.id == partner_sudo.id
        # Validate the address values and highlights the problems in the form, if any.
        invalid_fields, missing_fields, error_messages = self._validate_address_values(
            address_values,
            partner_sudo,
            address_type,
            use_delivery_as_billing,
            required_fields,
            is_main_address=is_main_address,
            **extra_form_data,
        )
        if error_messages:
            return json.dumps({
                'invalid_fields': list(invalid_fields | missing_fields),
                'messages': error_messages,
            })

        is_new_address = False
        if not partner_sudo:  # Creation of a new address.
            is_new_address = True
            self._complete_address_values(
                address_values, address_type, use_delivery_as_billing, order_sudo
            )
            create_context = clean_context(request.env.context)
            create_context.update({
                'tracking_disable': True,
                'no_vat_validation': True,  # Already verified in _validate_address_values
            })
            partner_sudo = request.env['res.partner'].sudo().with_context(
                create_context
            ).create(address_values)
        elif not self._are_same_addresses(address_values, partner_sudo):
            partner_sudo.write(address_values)  # Keep the same partner if nothing changed.

        partner_fnames = set()
        if is_main_address:  # Main address updated.
            partner_fnames.add('partner_id')  # Force the re-computation of partner-based fields.

        if address_type == 'billing':
            partner_fnames.add('partner_invoice_id')
            if is_new_address and order_sudo.only_services:
                # The delivery address is required to make the order.
                partner_fnames.add('partner_shipping_id')
            callback = callback or self._get_extra_billing_info_route(order_sudo)
        elif address_type == 'delivery':
            partner_fnames.add('partner_shipping_id')
            if use_delivery_as_billing:
                partner_fnames.add('partner_invoice_id')

        order_sudo._update_address(partner_sudo.id, partner_fnames)

        if is_anonymous_cart:
            # Unsubscribe the public partner if the cart was previously anonymous.
            order_sudo.message_unsubscribe(order_sudo.website_id.partner_id.ids)

        if is_new_address or order_sudo.only_services:
            callback = callback or '/shop/checkout?try_skip_step=true'
        else:
            callback = callback or '/shop/checkout'

        self._handle_extra_form_data(extra_form_data, address_values)

        return json.dumps({
            'successUrl': callback,
        })

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

        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer(
            order_sudo, address_type
        ):
            raise Forbidden()

        return partner_sudo, address_type

    def _parse_form_data(self, form_data):
        """ Parse the form data and return them converted into address values and extra form data.

        :param dict form_data: The form data to convert to address values.
        :return: A tuple of converted address values and extra form data.
        :rtype: tuple[dict, dict]
        """
        address_values = {}
        extra_form_data = {}

        ResPartner = request.env['res.partner']
        partner_fields = ResPartner._fields
        authorized_partner_fields = set(
            request.env['ir.model']._get('res.partner')._get_form_writable_fields().keys()
        )
        for key, value in form_data.items():
            if isinstance(value, str):
                value = value.strip()
            if key in partner_fields and key in authorized_partner_fields:
                field = partner_fields[key]
                if field.type == 'many2one' and isinstance(value, str) and value.isdigit():
                    address_values[key] = field.convert_to_cache(int(value), ResPartner)
                else:
                    # Always keep field values, even if falsy, as it might be for resetting a field.
                    address_values[key] = field.convert_to_cache(value, ResPartner)
            elif value:  # The value cannot be saved on the `res.partner` model.
                extra_form_data[key] = value

        if (
            hasattr(ResPartner, 'check_vat')  # The `base_vat` module is installed.
            and address_values.get('vat')
            and address_values.get('country_id')
        ):
            address_values['vat'] = ResPartner.fix_eu_vat_number(
                address_values['country_id'],
                address_values['vat'],
            )

        return address_values, extra_form_data

    def _validate_address_values(
        self,
        address_values,
        partner_sudo,
        address_type,
        use_delivery_as_billing,
        required_fields,
        is_main_address,
        **_kwargs,
    ):
        """ Validate the address values and return the invalid fields, the missing fields, and any
        error messages.

        :param dict address_values: The address values to validates.
        :param res.partner partner_sudo: The partner whose address values to validate, if any (can
                                         be empty).
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the
                                             billing and the delivery address.
        :param str required_fields: The additional required address values, as a comma-separated
                                    list of `res.partner` fields.
        :param bool is_main_address: Whether the provided address is meant to be the main address of
                                     the customer.
        :param dict _kwargs: Locally unused parameters including the extra form data.
        :return: The invalid fields, the missing fields, and any error messages.
        :rtype: tuple[set, set, list]
        """
        # data: values after preprocess
        invalid_fields = set()
        missing_fields = set()
        error_messages = []

        if partner_sudo:
            name_change = (
                'name' in address_values
                and partner_sudo.name
                and address_values['name'] != partner_sudo.name
            )
            email_change = (
                'email' in address_values
                and partner_sudo.email
                and address_values['email'] != partner_sudo.email
            )

            # Prevent changing the partner name if invoices have been issued.
            if name_change and not partner_sudo._can_edit_name():
                invalid_fields.add('name')
                error_messages.append(_(
                    "Changing your name is not allowed once invoices have been issued for your"
                    " account. Please contact us directly for this operation."
                ))

            # Prevent changing the partner name or email if it is an internal user.
            if (name_change or email_change) and not all(partner_sudo.user_ids.mapped('share')):
                if name_change:
                    invalid_fields.add('name')
                if email_change:
                    invalid_fields.add('email')
                error_messages.append(_(
                    "If you are ordering for an external person, please place your order via the"
                    " backend. If you wish to change your name or email address, please do so in"
                    " the account settings or contact your administrator."
                ))

            # Prevent changing the VAT number if invoices have been issued.
            if (
                'vat' in address_values
                and address_values['vat'] != partner_sudo.vat
                and not partner_sudo.can_edit_vat()
            ):
                invalid_fields.add('vat')
                error_messages.append(_(
                    "Changing VAT number is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                ))

        # Validate the email.
        if address_values.get('email') and not single_email_re.match(address_values['email']):
            invalid_fields.add('email')
            error_messages.append(_("Invalid Email! Please enter a valid email address."))

        # Validate the VAT number.
        ResPartnerSudo = request.env['res.partner'].sudo()
        if (
            address_values.get('vat') and hasattr(ResPartnerSudo, 'check_vat')
            and 'vat' not in invalid_fields
        ):
            partner_dummy = ResPartnerSudo.new({
                fname: address_values[fname]
                for fname in self._get_vat_validation_fields()
                if fname in address_values
            })
            try:
                partner_dummy.check_vat()
            except ValidationError as exception:
                invalid_fields.add('vat')
                error_messages.append(exception.args[0])

        # Build the set of required fields from the address form's requirements.
        required_field_set = {f for f in required_fields.split(',') if f}

        # Complete the set of required fields based on the address type.
        country_id = address_values.get('country_id')
        country = request.env['res.country'].browse(country_id)
        if address_type == 'delivery' or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_delivery_address_fields(country)
        if address_type == 'billing' or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_billing_address_fields(country)
            if not is_main_address:
                commercial_fields = ResPartnerSudo._commercial_fields()
                for fname in commercial_fields:
                    if fname in required_field_set and fname not in address_values:
                        required_field_set.remove(fname)

        # Verify that no required field has been left empty.
        for field_name in required_field_set:
            if not address_values.get(field_name):
                missing_fields.add(field_name)
        if missing_fields:
            error_messages.append(_("Some required fields are empty."))

        return invalid_fields, missing_fields, error_messages

    def _get_vat_validation_fields(self):
        return {'country_id', 'vat'}

    def _complete_address_values(
        self, address_values, address_type, use_delivery_as_billing, order_sudo
    ):
        """ Complete the address values with the order, website, and request's contextual values.

        :param dict address_values: The address values to complete.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :param bool use_delivery_as_billing: Whether the provided address should be used as both the
                                             billing and the delivery address.
        :param sale.order order_sudo: The current cart.
        :return: None
        """
        if request.lang.code in request.website.mapped('language_ids.code'):
            address_values['lang'] = request.lang.code

        address_values['company_id'] = order_sudo.website_id.company_id.id
        address_values['user_id'] = order_sudo.website_id.salesperson_id.id

        if order_sudo.website_id.specific_user_account:
            address_values['website_id'] = order_sudo.website_id.id

        commercial_partner = order_sudo.partner_id.commercial_partner_id
        if order_sudo._is_anonymous_cart():
            address_values['type'] = 'contact'
        elif address_type == 'billing':
            address_values['type'] = 'invoice'
        elif address_type == 'delivery':
            address_values['type'] = 'other' if use_delivery_as_billing else 'delivery'

        # Avoid linking the address to the default archived 'Public user' partner.
        if commercial_partner.active:
            address_values['parent_id'] = commercial_partner.id

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
            address_values, address_type, use_delivery_as_billing, order_sudo
        )
        creation_context = clean_context(request.env.context)
        creation_context.update({
            'tracking_disable': True,
            # 'no_vat_validation': True,  # TODO VCR VAT validation or not ?
        })
        return request.env['res.partner'].sudo().with_context(
            creation_context
        ).create(address_values)

    def _get_extra_billing_info_route(self, order_sudo):
        """ Hook for localizations to request additional billing details in a specific page.

        :param sale.order order_sudo: The current cart.
        :return: The route to redirect the customer to.
        :rtype: str
        """
        return ''

    def _handle_extra_form_data(self, extra_form_data, address_values):
        """ Handling extra form data that were not processed on the address from.

        :param dict extra_form_data: The extra form data.
        :param dict address_values: The address value.
        :return: None
        """
        pass

    @route(
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
            with request.env.protecting(['pricelist_id'], order_sudo):
                order_sudo.partner_id = new_partner_sudo

            # Add the new partner as follower of the cart
            order_sudo._message_subscribe(order_sudo.partner_id.ids)
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
            shipping_address, _side_values = self._parse_form_data(billing_address)

            if order_sudo.partner_shipping_id.name.endswith(order_sudo.name):
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

    def _are_same_addresses(self, address_values, partner):
        ResPartner = request.env['res.partner']
        for key, new_val in address_values.items():
            val = ResPartner._fields[key].convert_to_cache(partner[key], ResPartner)
            if new_val != val and (val or new_val):
                # Skip falsy values if unset in values and on record
                return False
        return True

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
            ('code', '=', address.pop('country'))
        ], limit=1)
        state = request.env["res.country.state"].search([
            ('code', '=', address.pop('state', ''))
        ], limit=1)
        address.update(country_id=country.id, state_id=state.id)

    @route('/shop/update_address', type='json', auth='public', website=True)
    def shop_update_address(self, partner_id, address_type='billing', **kw):
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

    @route(['/shop/confirm_order'], type='http', auth="public", website=True, sitemap=False)
    def shop_confirm_order(self, **post):
        order_sudo = request.website.sale_get_order()

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        order_sudo._recompute_taxes()
        order_sudo._recompute_prices()
        extra_step = request.website.viewref('website_sale.extra_info')
        if extra_step.active:
            return request.redirect("/shop/extra_info")

        return request.redirect("/shop/payment")

    # === CHECKOUT FLOW - EXTRA STEP METHODS === #

    @route(['/shop/extra_info'], type='http', auth="public", website=True, sitemap=False)
    def extra_info(self, **post):
        # Check that this option is activated
        extra_step = request.website.viewref('website_sale.extra_info')
        if not extra_step.active:
            return request.redirect("/shop/payment")

        # check that cart is valid
        order = request.website.sale_get_order()
        redirection = self._check_cart(order)
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

    # === CHECKOUT FLOW - PAYMENT/CONFIRMATION METHODS === #

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
            'shipping_info_required': order._has_deliverable_products(),
            'delivery_amount': payment_utils.to_minor_currency_units(
                order.order_line.filtered(lambda l: l.is_delivery).price_total, order.currency_id
            ),
            'shipping_address_update_route': self._express_checkout_delivery_route,
        })
        if request.website.is_public_user():
            payment_form_values['partner_id'] = -1
        return payment_form_values

    def _get_shop_payment_values(self, order, **kwargs):
        checkout_page_values = {
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

    @route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.provider. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.provider website but closed the tab without
           paying / canceling
        """
        order_sudo = request.website.sale_get_order()

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        if redirection := self._check_shipping_method(order_sudo):
            return redirection

        render_values = self._get_shop_payment_values(order_sudo, **post)
        render_values['only_services'] = order_sudo and order_sudo.only_services

        if render_values['errors']:
            render_values.pop('payment_methods_sudo', '')
            render_values.pop('tokens_sudo', '')

        return request.render("website_sale.payment", render_values)

    @route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
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

        errors = self._get_shop_payment_errors(order)
        if errors:
            first_error = errors[0]  # only display first error
            error_msg = f"{first_error[0]}\n{first_error[1]}"
            raise ValidationError(error_msg)

        tx_sudo = order.get_portal_last_transaction() if order else order.env['payment.transaction']

        if not order or (order.amount_total and not tx_sudo):
            return request.redirect('/shop')

        if order and not order.amount_total and not tx_sudo:
            if order.state != 'sale':
                order._validate_order()

            # clean context and session, then redirect to the portal page
            request.website.sale_reset()
            return request.redirect(order.get_portal_url())

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx_sudo and tx_sudo.state == 'draft':
            return request.redirect('/shop')

        return request.redirect('/shop/confirmation')

    @route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
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

    @route(['/shop/print'], type='http', auth="public", website=True, sitemap=False)
    def print_saleorder(self, **kwargs):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sale.action_report_saleorder', [sale_order_id])
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', '%s' % len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        return request.redirect('/shop')

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
            return request.redirect('/shop')

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
            and delivery_partner_sudo._can_be_edited_by_current_customer(order_sudo, 'delivery')
        ):
            return request.redirect(
                f'/shop/address?partner_id={delivery_partner_sudo.id}&address_type=delivery'
            )
        # Check that the billing address is complete.
        invoice_partner_sudo = order_sudo.partner_invoice_id
        if (
            not self._check_billing_address(invoice_partner_sudo)
            and invoice_partner_sudo._can_be_edited_by_current_customer(order_sudo, 'billing')
        ):
            return request.redirect(
                f'/shop/address?partner_id={invoice_partner_sudo.id}&address_type=billing'
            )

    def _check_delivery_address(self, partner_sudo):
        """ Check that all mandatory delivery fields are filled for the given partner.

        :param res.partner: The partner whose delivery address to check.
        :return: Whether all mandatory fields are filled.
        :rtype: bool
        """
        mandatory_delivery_fields = self._get_mandatory_delivery_address_fields(
            partner_sudo.country_id
        )
        return all(partner_sudo.read(mandatory_delivery_fields)[0].values())

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        """ Return the set of mandatory delivery field names.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of mandatory delivery field names.
        :rtype: set
        """
        return self._get_mandatory_address_fields(country_sudo)

    def _check_billing_address(self, partner_sudo):
        """ Check that all mandatory billing fields are filled for the given partner.

        :param res.partner: The partner whose billing address to check.
        :return: Whether all mandatory fields are filled.
        :rtype: bool
        """
        mandatory_billing_fields = self._get_mandatory_billing_address_fields(
            partner_sudo.country_id
        )
        return all(partner_sudo.read(mandatory_billing_fields)[0].values())

    def _check_shipping_method(self, order_sudo):
        if not order_sudo._is_delivery_ready():
            return request.redirect('/shop/checkout')

    def _get_mandatory_billing_address_fields(self, country_sudo):
        """ Return the set of mandatory billing field names.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of mandatory billing field names.
        :rtype: set
        """
        field_names = self._get_mandatory_address_fields(country_sudo)
        # Include the required billing fields from the portal logic.
        field_names |= set(self._get_mandatory_fields())
        return field_names

    def _get_mandatory_address_fields(self, country_sudo):
        """ Return the set of common mandatory address fields.

        :param res.country country_sudo: The country to use to build the set of mandatory fields.
        :return: The set of common mandatory address field names.
        :rtype: set
        """
        field_names = {'name', 'street', 'city', 'country_id', 'phone'}
        if country_sudo.state_required:
            field_names.add('state_id')
        if country_sudo.zip_required:
            field_names.add('zip')
        return field_names

    # ------------------------------------------------------
    # Edit
    # ------------------------------------------------------

    @route(['/shop/config/product'], type='json', auth='user')
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

    @route(['/shop/config/attribute'], type='json', auth='user')
    def change_attribute_config(self, attribute_id, **options):
        if not request.env.user.has_group('website.group_website_restricted_editor'):
            raise NotFound()

        attribute = request.env['product.attribute'].browse(attribute_id)
        if 'display_type' in options:
            attribute.write({'display_type': options['display_type']})
            request.env.registry.clear_cache('templates')

    @route(['/shop/config/website'], type='json', auth='user')
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

    @route(['/shop/country_info/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], website=True)
    def shop_country_info(self, country, address_type, **kw):
        address_fields = country.get_address_fields()
        if address_type == 'billing':
            required_fields = self._get_mandatory_billing_address_fields(country)
        else:
            required_fields = self._get_mandatory_delivery_address_fields(country)
        return {
            'fields': address_fields,
            'zip_before_city': (
                'zip' in address_fields
                and address_fields.index('zip') < address_fields.index('city')
            ),
            'states': [(st.id, st.name, st.code) for st in country.sudo().state_ids],
            'phone_code': country.phone_code,
            'required_fields': list(required_fields),
        }

    # --------------------------------------------------------------------------
    # Products Recently Viewed
    # --------------------------------------------------------------------------
    @route('/shop/products/recently_viewed_update', type='json', auth='public', website=True)
    def products_recently_viewed_update(self, product_id, **kwargs):
        res = {}
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._add_viewed_product(product_id)
        return res

    @route('/shop/products/recently_viewed_delete', type='json', auth='public', website=True)
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

    @staticmethod
    def _populate_currency_and_pricelist(kwargs):
        website = request.website
        kwargs.update({
            'currency_id': website.currency_id.id,
            'pricelist_id': website.pricelist_id.id,
        })
