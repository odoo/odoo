# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from collections import defaultdict
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlparse

from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_decode, url_encode, url_parse

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.http import request, route
from odoo.http.stream import content_disposition
from odoo.tools import SQL, BinaryBytes, clean_context, float_round, lazy, str2bool
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.translate import LazyTranslate

from odoo.addons.html_editor.tools import get_video_thumbnail
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_sale.const import MAX_EXPANDED_FILTER_SECTIONS, SHOP_PATH
from odoo.addons.website_sale.models.website import (
    PRICELIST_SELECTED_SESSION_CACHE_KEY,
    PRICELIST_SESSION_CACHE_KEY,
)

_lt = LazyTranslate(__name__)


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
        maxy = 0
        x = 0
        for index, p in enumerate(products):
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

            if x == 1 and y == 1:  # simple heuristic for CPU optimization
                minpos = pos // ppr

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // ppr) + y2][(pos % ppr) + x2] = False
            self.table[pos // ppr][pos % ppr] = {
                "product": p,
                "x": x,
                "y": y,
                "ribbon": p.sudo().website_ribbon_id,
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos // ppr))

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows


def _get_parent_category_route(depth, param_name="_"):
    """Recursively build the parent category part of the route."""
    if depth < 1:
        return ""
    parent_path = _get_parent_category_route(depth - 1, param_name + "_")
    return f"{parent_path}/<model('product.public.category'):{param_name}>"


def _get_category_routes(suffix=""):
    """Build all category routes with a parent category depth from 0 to 4 (i.e. in addition to the
    current category, we support up to 4 nested parent categories in the route).

    Depths greater than 4 are not supported to avoid having too long URLs.

    The max depth should stay in sync with `ProductPublicCategory._compute_website_url`.
    """
    return [
        (
            f"{SHOP_PATH}/category{_get_parent_category_route(depth)}"
            f"/<model('product.public.category'):category>{suffix}"
        )
        for depth in range(5)
    ]


class WebsiteSale(payment_portal.PaymentPortal):
    _express_checkout_route = "/shop/express_checkout"
    _express_checkout_delivery_route = "/shop/express/shipping_address_change"

    WRITABLE_PARTNER_FIELDS = [
        "name",
        "email",
        "phone",
        "street",
        "street2",
        "city",
        "zip",
        "country_id",
        "state_id",
    ]

    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        order = post.get("order") or self.env["website"].get_current_website().shop_default_sort
        return "is_published desc, %s, id desc" % order

    def _add_search_subdomains_hook(self, _search):
        return []

    def _get_shop_domain(
        self, search, category, attribute_value_dict, search_in_description=True, tags=None
    ):
        domains = [request.website.sale_product_domain()]
        if search:
            for srch in search.split(" "):
                subdomains = [
                    Domain("name", "ilike", srch),
                    Domain("variants_default_code", "ilike", srch),
                ]
                if search_in_description:
                    subdomains.extend((
                        Domain("website_description", "ilike", srch),
                        Domain("description_sale", "ilike", srch),
                    ))
                extra_subdomain = self._add_search_subdomains_hook(srch)
                if extra_subdomain:
                    subdomains.append(extra_subdomain)
                domains.append(Domain.OR(subdomains))

        if category:
            domains.append(Domain("public_categ_ids", "child_of", int(category)))

        if attribute_value_dict:
            domains.extend(
                self.env["product.template"]._get_attribute_value_domain(attribute_value_dict)
            )

        if tags:
            domains.append(
                Domain.OR([
                    Domain("product_tag_ids", "in", tags),
                    Domain("product_variant_ids.additional_product_tag_ids", "in", tags),
                ])
            )

        return Domain.AND(domains)

    def sitemap_shop(env, _rule, qs):  # noqa: N805
        website = env["website"].get_current_website()
        if website and website.ecommerce_access == "logged_in" and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        if not qs or qs.lower() in SHOP_PATH:
            yield {"loc": SHOP_PATH}

        Category = env["product.public.category"]
        dom = sitemap_qs2dom(qs, f"{SHOP_PATH}/category", Category._rec_name)
        dom &= website.website_domain()
        for cat in Category.search(dom):
            loc = cat.website_url
            if not qs or qs.lower() in loc:
                yield {"loc": loc}

    def sitemap_products(env, _rule, qs):  # noqa: N805
        website = env["website"].get_current_website()
        if website and website.ecommerce_access == "logged_in" and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        ProductTemplate = env["product.template"]
        dom = sitemap_qs2dom(qs, SHOP_PATH, ProductTemplate._rec_name)
        dom &= Domain(website.sale_product_domain())
        for product in ProductTemplate.with_context(prefetch_fields=False).search(dom):
            loc = product.website_url
            if not qs or qs.lower() in loc:
                yield {"loc": loc}

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
            "allowFuzzy": not post.get("noFuzzy"),
            "category": str(category.id) if category else None,
            "tags": tags,
            "min_price": min_price / conversion_rate,
            "max_price": max_price / conversion_rate,
            "attribute_value_dict": attribute_value_dict,
            "display_currency": post.get("display_currency"),
            "extra_domain": post.get("extra_domain"),
        }

    def _shop_lookup_products(self, options, post, search, website):
        # No limit because attributes are obtained from complete product list
        product_count, details, fuzzy_search_term = website._search_with_fuzzy(
            "product_template",
            search,
            offset=0,
            limit=None,
            order=self._get_search_order(post),
            options=options,
        )
        search_result = (
            details[0].get("results", self.env["product.template"]).with_context(bin_size=True)
        )

        return fuzzy_search_term, product_count, search_result

    def _shop_get_query_url_kwargs(
        self, search, min_price, max_price, order=None, tags=None, **_kwargs
    ):
        return {
            "search": search,
            "min_price": min_price,
            "max_price": max_price,
            "order": order,
            "tags": tags,
            **request.session.get("attribute_value_params", {}),
        }

    def _get_additional_shop_values(self, _values, **_kwargs):
        """Update values used for rendering website_sale.products template."""
        wished_products = self.env["product.wishlist"].current().product_id
        return {
            # TODO lazy to avoid queries when wishlist disabled on shop page ?
            "products_in_wishlist": wished_products,
            "templates_in_wishlist": wished_products.product_tmpl_id,
        }

    def _get_product_query_params(self, **_kwargs):
        """Allow to configure the product page URL's query string."""
        return {}

    @route(
        [
            SHOP_PATH,
            f"{SHOP_PATH}/page/<int:page>",
            *_get_category_routes(),
            *_get_category_routes("/page/<int:page>"),
        ],
        type="http",
        auth="public",
        website=True,
        list_as_website_content=_lt("Shop"),
        sitemap=sitemap_shop,
        # Return a 404 instead of a 403 error in case of an access error.
        handle_params_access_error=lambda e, **_kwargs: NotFound.code,  # noqa: ARG005
    )
    def shop(self, page=0, category=None, search="", min_price=0.0, max_price=0.0, tags="", **post):
        if not request.website.has_ecommerce_access():
            return request.redirect(f"/web/login?redirect={request.httprequest.path}")

        post = {k: v for k, v in post.items() if not k.startswith("_")}
        # TODO: remove support for `category` query param in version 20 (or later).
        category = self._validate_and_get_category(category)
        if category:
            path = category.website_url + (f"/page/{page}" if page else "")
            # Redirect to the correct category URL if needed. There are 2 potential reasons for
            # redirecting:
            # - The category was given as a query parameter instead of in the path,
            # - The category's parents (if any) weren't included in the path.
            if path != request.httprequest.path:
                url = urlparse(request.httprequest.url)
                return request.redirect(url._replace(path=path).geturl(), code=301)

        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

        website = self.env["website"].get_current_website()
        website_domain = website.website_domain()

        ppg = website.shop_ppg or 21
        ppr = website.shop_ppr or 4
        gap = website.shop_gap or "16px"

        attribute_value_params = self._get_attribute_value_params(post)
        # TODO: remove support for `attribute_values` query param in version 20 (or later).
        if not attribute_value_params and (
            attribute_values := request.httprequest.args.getlist("attribute_values")
        ):
            # Transform the attribute value query params list into a dict.
            # Before: ["1-2,3", "4-5,6"]
            # After: {"1": "2,3", "4": "5,6"}
            attribute_value_params = dict([
                pair.split("-") for pair in attribute_values if pair and pair.count("-") == 1
            ])
        attribute_value_dict = self._get_attribute_value_dict(attribute_value_params)
        attribute_ids = set(attribute_value_dict.keys())
        attribute_value_ids = set(itertools.chain.from_iterable(attribute_value_dict.values()))
        grouped_attributes_values = (
            self
            .env["product.attribute.value"]
            .browse(attribute_value_ids)
            .exists()
            .sorted()
            .grouped("attribute_id")
        )
        if request.httprequest.args.getlist("attribute_values"):
            redirect_url = self._get_url_with_attribute_values(grouped_attributes_values)
            return request.redirect(redirect_url, code=301)
        if attribute_value_params:
            request.session["attribute_value_params"] = attribute_value_params
        else:
            request.session.pop("attribute_value_params", None)

        filter_by_tags_enabled = website.is_view_active("website_sale.filter_products_tags")
        if filter_by_tags_enabled:
            if tags:
                post["tags"] = tags
                unslug = self.env["ir.http"]._unslug
                tags = {tag_id for tag in tags.split(",") if (tag_id := unslug(tag)[1])}
            else:
                post["tags"] = None
                tags = {}

        url = category.website_url if category else SHOP_PATH
        keep = QueryURL(
            url, **self._shop_get_query_url_kwargs(search, min_price, max_price, **post)
        )

        # Check if we need to refresh the cached pricelist
        now = datetime.timestamp(datetime.now())
        if "website_sale_pricelist_time" in request.session:
            pricelist_save_time = request.session["website_sale_pricelist_time"]
            if pricelist_save_time < now - 60 * 60:
                request.session.pop(PRICELIST_SESSION_CACHE_KEY, None)
                # restart the counter
                request.session["website_sale_pricelist_time"] = now

        filter_by_price_enabled = website.is_view_active("website_sale.filter_products_price")
        if filter_by_price_enabled:
            company_currency = website.company_id.sudo().currency_id
            conversion_rate = self.env["res.currency"]._get_conversion_rate(
                company_currency,
                website.currency_id,
                request.website.company_id,
                fields.Date.today(),
            )
        else:
            conversion_rate = 1

        if search:
            post["search"] = search

        tax_display = website.show_line_subtotals_tax_selection
        sale_tax = request.fiscal_position.map_tax(website.company_id.sudo().account_sale_tax_id)

        if tax_display == "tax_included" and sale_tax:
            # Convert the boundaried to tax-excluded for internal processing
            min_price_tax_excluded = sale_tax.with_context(force_price_include=True).compute_all(
                min_price, website.currency_id
            )["total_excluded"]
            max_price_tax_excluded = sale_tax.with_context(force_price_include=True).compute_all(
                max_price, website.currency_id
            )["total_excluded"]
        else:
            min_price_tax_excluded = min_price
            max_price_tax_excluded = max_price

        options = self._get_search_options(
            category=category,
            attribute_value_dict=attribute_value_dict,
            min_price=min_price_tax_excluded,
            max_price=max_price_tax_excluded,
            conversion_rate=conversion_rate,
            display_currency=website.currency_id,
            extra_domain=Domain.OR([
                Domain("public_categ_ids", "=", False),
                Domain("public_categ_ids.not_in_shop", "=", False),
            ])
            if not (category or search)
            else None,
            **post,
        )
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(
            options, post, search, website
        )

        search_term = fuzzy_search_term if fuzzy_search_term else search
        shop_domain = self._get_shop_domain(
            search_term,
            category,
            attribute_value_dict,
            tags=tags if filter_by_tags_enabled else None,
        )
        shop_query = request.env["product.template"]._search(shop_domain)

        filter_by_price_enabled = website.is_view_active("website_sale.filter_products_price")
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            # This is ~4 times more efficient than a search for the cheapest and most expensive
            # products
            sql = shop_query.select(
                SQL(
                    "COALESCE(MIN(list_price), 0) * %(conversion_rate)s, COALESCE(MAX(list_price), 0) * %(conversion_rate)s",  # noqa: E501
                    conversion_rate=conversion_rate,
                )
            )
            available_min_price, available_max_price = self.env.execute_query(sql)[0]

            if tax_display == "tax_included" and sale_tax:
                available_min_price = sale_tax.with_context(force_price_include=False).compute_all(
                    available_min_price, website.currency_id
                )["total_included"]
                available_max_price = sale_tax.with_context(force_price_include=False).compute_all(
                    available_max_price, website.currency_id
                )["total_included"]

            if min_price or max_price:
                # The if/else condition in the min_price / max_price value assignment
                # tackles the case where we switch to a list of products with different
                # available min / max prices than the ones set in the previous page.
                # In order to have logical results and not yield empty product lists, the
                # price filter is set to their respective available prices when the specified
                # min exceeds the max, and / or the specified max is lower than the available min.
                if min_price:
                    min_price = (
                        min_price if min_price <= available_max_price else available_min_price
                    )
                    post["min_price"] = min_price
                if max_price:
                    max_price = (
                        max_price if max_price >= available_min_price else available_max_price
                    )
                    post["max_price"] = max_price
        if filter_by_price_enabled and (min_price or max_price):
            price_domain = Domain.AND([
                Domain("list_price", ">=", (min_price or available_min_price) / conversion_rate),
                Domain("list_price", "<=", (max_price or available_max_price) / conversion_rate),
            ])
            filtered_query = request.env["product.template"]._search(
                Domain.AND([shop_domain, price_domain])
            )
        else:
            filtered_query = shop_query

        ProductTag = self.env["product.tag"]
        if filter_by_tags_enabled and search_product:
            all_tags = ProductTag.search_fetch(
                Domain.AND([
                    Domain("visible_to_customers", "=", True),
                    Domain.OR([
                        Domain("product_template_ids", "in", filtered_query),
                        Domain("product_product_ids.product_tmpl_id", "in", filtered_query),
                    ]),
                    website_domain,
                ])
            )
        else:
            all_tags = ProductTag

        # categories

        Category = self.env["product.public.category"]
        categs_domain = (
            Domain("parent_id", "=", False) & Domain("not_in_shop", "=", False) & website_domain
        )
        if search:
            search_categories = Category.search(
                Domain("product_tmpl_ids", "in", search_product.ids) & website_domain
            ).parents_and_self
            categs_domain &= Domain("id", "in", search_categories.ids)
        else:
            search_categories = Category
        categs = Category.search_fetch(categs_domain)

        category_entries = Category
        if category:
            available_categories = category.child_id.filtered(
                lambda c: c.can_access_from_current_website()
            )
            category_entries = (
                (not search
                and available_categories)
                or available_categories.filtered(lambda c: c.id in search_categories.ids)
            )
            if not category_entries:
                parent = category.parent_id
                available_categories = parent.child_id.filtered(
                    lambda c: c.can_access_from_current_website()
                )
                category_entries = (
                    (not search
                    and available_categories)
                    or available_categories.filtered(lambda c: c.id in search_categories.ids)
                )
            if not search and not self.env.user._is_internal():
                # We know the user has access to `categs` and `search_categories` because they come
                # from a regular `search`, but we have not checked access to `category`'s children,
                # nor its siblings or itself.
                category_entries = category_entries.filtered("has_published_products")
        else:
            category_entries = categs

        # products for current pager

        pager = website.pager(
            url=url, total=product_count, page=page, step=ppg, scope=5, url_args=post
        )
        offset = pager["offset"]
        products = search_product[offset : offset + ppg].with_prefetch()
        products.fetch()

        # map each product to its variant, and prefetch the variants
        Product = self.env["product.product"]
        product_variant_ids = [product._get_first_possible_variant_id() for product in products]
        variants = Product.sudo().browse(vid for vid in product_variant_ids if vid)
        variants.fetch()
        variant_by_id = {v.id: v for v in variants}
        product_variants = dict(
            zip(products, (variant_by_id.get(vid, Product) for vid in product_variant_ids))
        )

        ProductAttribute = self.env["product.attribute"]
        ProductAttributeValue = self.env["product.attribute.value"]
        pavs_per_attribute = defaultdict(lambda: ProductAttributeValue)
        if products:
            grouped_pavs = ProductAttributeValue._read_group(
                domain=[
                    ("pav_attribute_line_ids.product_tmpl_id", "in", filtered_query),
                    ("attribute_id.visibility", "=", "visible"),
                ],
                groupby=["attribute_id"],
                order="attribute_id",
                aggregates=["id:recordset"],
            )
            pavs_per_attribute.update(grouped_pavs)
            # Return attributes as recordset of `product.attribute`
            attributes = ProductAttribute.union(pavs_per_attribute.keys())
        else:
            attributes = ProductAttribute.browse(attribute_ids).exists().sorted()
        products_prices = products._get_sales_prices(
            # Make sure latest context is applied (see update_context calls in overrides)
            request.pricelist.with_context(self.env.context),
            request.fiscal_position.with_context(self.env.context),
            website.with_context(self.env.context),
        )
        product_query_params = self._get_product_query_params(**post)

        values = {
            "auto_assign_ribbons": self
            .env["product.ribbon"]
            .sudo()
            .search([("assign", "!=", "manual")]),
            "search": fuzzy_search_term or search,
            "original_search": fuzzy_search_term and search,
            "order": post.get("order", ""),
            "category": category,
            "attrib_values": attribute_value_dict,
            "attrib_set": attribute_value_ids,
            "pager": pager,
            "products": products,
            "product_variants": product_variants,
            "search_product": search_product,
            "search_count": product_count,  # common for all searchbox
            "bins": TableCompute().process(products, ppg, ppr),
            "ppg": ppg,
            "ppr": ppr,
            "gap": gap,
            "categories": categs,
            "category_entries": category_entries,
            "attributes": attributes,
            "keep": keep,
            "search_categories_ids": search_categories.ids,
            "get_product_prices": lambda product: products_prices[product.id],
            "float_round": float_round,
            "shop_path": SHOP_PATH,
            "product_query_params": product_query_params,
            "grouped_attributes_values": grouped_attributes_values,
            "previewed_attribute_values": lazy(
                lambda: products._get_previewed_attribute_values(product_query_params)
            ),
            "pavs_per_attribute": pavs_per_attribute,
        }
        nb_filter_sections = len(attributes)
        if filter_by_price_enabled:
            values["min_price"] = min_price or available_min_price
            values["max_price"] = max_price or available_max_price
            values["available_min_price"] = float_round(available_min_price, 2)
            values["available_max_price"] = float_round(available_max_price, 2)
            if available_min_price != available_max_price:
                nb_filter_sections += 1
        if filter_by_tags_enabled:
            values.update({"all_tags": all_tags, "tags": tags})
            if all_tags:
                nb_filter_sections += 1
        if category:
            values["main_object"] = category
            values["markup_data_json"] = json_scriptsafe.dumps(
                [
                    website._prepare_ecommerce_store_markup_data(),
                    self._prepare_breadcrumb_markup_data(website.get_base_url(), category),
                ],
                indent=2,
            )
        values.update(self._get_additional_shop_values(values, **post))

        values["default_expand_filter_sections"] = nb_filter_sections < MAX_EXPANDED_FILTER_SECTIONS

        return request.render("website_sale.products", values)

    @route(
        [
            f"{SHOP_PATH}/product/<model('product.template'):product>",
            f"{SHOP_PATH}/<model('product.template'):product>",
            f"{SHOP_PATH}/<model('product.public.category'):category>/<model('product.template'):product>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_products,
        # Return a 404 instead of a 403 error in case of an access error.
        handle_params_access_error=lambda e, **_kwargs: NotFound.code,  # noqa: ARG005
    )
    def product(self, product, pricelist=None, **kwargs):
        if not request.website.has_ecommerce_access():
            return request.redirect(f"/web/login?redirect={request.httprequest.path}")

        if pricelist is not None:
            try:
                pricelist_id = int(pricelist)
            except ValueError as ve:
                raise ValidationError(
                    self.env._("Wrong format: got `pricelist=%s`, expected an integer", pricelist)
                ) from ve
            if not self._apply_selectable_pricelist(pricelist_id):
                return request.redirect(SHOP_PATH)

        request.update_context(website_sale_product_page=True)
        # TODO: remove support for deprecated paths in version 20 (or later).
        if not request.httprequest.path.startswith(f"{SHOP_PATH}/product/"):
            query = request.httprequest.args.to_dict(flat=False)
            return request.redirect(product._get_product_url(query), code=301)

        product_values = self._prepare_product_values(
            # request context must be given to ensure context updates in overrides are correctly
            # forwarded to `_get_combination_info` call
            product.with_context(self.env.context),
            **kwargs,
        )
        if "redirect_url" in product_values:
            return request.redirect(product_values["redirect_url"], code=301)
        return request.render("website_sale.product", product_values)

    @route(
        '/shop/<model("product.template"):product_template>/document/<int:document_id>',
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def product_document(self, product_template, document_id):
        product_template.check_access("read")

        document = self.env["product.document"].browse(document_id).sudo().exists()
        if not document or not document.active:
            return request.redirect(SHOP_PATH)

        if not document.shown_on_product_page or not (
            document.res_id == product_template.id and document.res_model == "product.template"
        ):
            return request.redirect(SHOP_PATH)

        return (
            self
            .env["ir.binary"]
            ._get_stream_from(document.ir_attachment_id)
            .get_response(as_attachment=True)
        )

    @route(["/shop/product/extra-media"], type="jsonrpc", auth="user", website=True)
    def add_product_media(
        self, media, type, product_product_id, product_template_id, combination_ids=None
    ):
        """
        Handle adding both images and videos to product variants or templates,
        links all of them to product.

        :param type: [...] can be either image or video
        :raises NotFound : If the user is not allowed to access Attachment model
        """
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        if type == "image":  # Image case
            image_ids = self.env["ir.attachment"].browse(i["id"] for i in media)
            media_create_data = [
                Command.create({
                    "name": image.name,  # Images uploaded from url do not have any datas.
                    # This recovers them manually.
                    "image_1920": image.raw
                    or self.env["ir.qweb.field.image"].load_remote_url(image.url),
                })
                for image in image_ids
            ]
        elif type == "video":  # Video case
            video_data = media[0]
            thumbnail = None
            if video_data.get("src"):  # Check if a valid video URL is provided
                try:
                    thumbnail = BinaryBytes(get_video_thumbnail(video_data["src"]))
                except Exception:  # noqa: BLE001
                    thumbnail = None
            else:
                raise ValidationError(self.env._("Invalid video URL provided."))
            media_create_data = [
                Command.create({
                    "name": video_data.get("name", "Odoo Video"),
                    "video_url": video_data["src"],
                    "image_1920": thumbnail,
                })
            ]

        product_product = (
            self.env["product.product"].browse(int(product_product_id))
            if product_product_id
            else False
        )
        product_template = (
            self.env["product.template"].browse(int(product_template_id))
            if product_template_id
            else False
        )

        if product_product and not product_template:
            product_template = product_product.product_tmpl_id

        if not product_product and product_template and product_template.has_dynamic_attributes():
            combination = self.env["product.template.attribute.value"].browse(combination_ids)
            product_product = product_template._get_variant_for_combination(combination)
            if not product_product:
                product_product = product_template._create_product_variant(combination)
        if (
            product_template.has_configurable_attributes
            and product_product
            and not all(
                pa.create_variant == "no_variant"
                for pa in product_template.attribute_line_ids.attribute_id
            )
        ):
            product_product.write({"product_variant_image_ids": media_create_data})
        else:
            product_template.write({"product_template_image_ids": media_create_data})

    @route(["/shop/product/clear-images"], type="jsonrpc", auth="user", website=True)
    def clear_product_images(self, product_product_id, product_template_id):
        """Unlink all images from the product."""
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        product_product = (
            self.env["product.product"].browse(int(product_product_id))
            if product_product_id
            else False
        )
        product_template = (
            self.env["product.template"].browse(int(product_template_id))
            if product_template_id
            else False
        )

        if product_product and not product_template:
            product_template = product_product.product_tmpl_id

        if product_product and product_product.product_variant_image_ids:
            product_product.product_variant_image_ids.unlink()
        else:
            product_template.product_template_image_ids.unlink()

    @route(["/shop/product/resequence-image"], type="jsonrpc", auth="user", website=True)
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
            not self.env.user.has_group("website.group_website_restricted_editor")
            or image_res_model not in {"product.product", "product.template", "product.image"}
            or move not in {"first", "left", "right", "last"}
        ):
            raise NotFound

        image_res_id = int(image_res_id)
        image_to_resequence = self.env[image_res_model].browse(image_res_id)
        if image_res_model == "product.product":
            product = image_to_resequence
            product_template = product.product_tmpl_id
        elif image_res_model == "product.template":
            product_template = image_to_resequence
            product = product_template.product_variant_id
        else:
            product = image_to_resequence.product_variant_id
            product_template = product.product_tmpl_id or image_to_resequence.product_tmpl_id

        if not product and not product_template:
            raise ValidationError(self.env._("Product not found"))

        product_images = (product or product_template)._get_images()
        if image_to_resequence not in product_images:
            raise ValidationError(self.env._("Invalid image"))

        image_idx = product_images.index(image_to_resequence)
        new_image_idx = 0
        if move == "left":
            new_image_idx = max(0, image_idx - 1)
        elif move == "right":
            new_image_idx = min(len(product_images) - 1, image_idx + 1)
        elif move == "last":
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
            idx for idx, image in enumerate(product_images) if image._name != "product.image"
        )
        if main_image_idx != 0:
            main_image = product_images[main_image_idx]
            additional_image = product_images[0]
            if additional_image.video_url:
                raise ValidationError(
                    self.env._("You can't use a video as the product's main image.")
                )
            # Swap records.
            product_images[main_image_idx], product_images[0] = additional_image, main_image
            # Swap image data.
            main_image.image_1920, additional_image.image_1920 = (
                additional_image.image_1920,
                main_image.image_1920,
            )
            additional_image.name = main_image.name  # Update image name but not product name.

        # Resequence additional images according to the new ordering.
        for idx, product_image in enumerate(product_images):
            if product_image._name == "product.image":
                product_image.sequence = idx

    @route(
        ["/shop/product/is_add_to_cart_allowed"],
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def is_add_to_cart_allowed(self, product_id, **_kwargs):
        product = self.env["product.product"].browse(product_id)
        # In sudo mode to check fields and conditions not accessible to the customer directly.
        return product.sudo()._is_add_to_cart_allowed()

    def _prepare_product_values(self, product, **kwargs):
        website = request.website
        category = product.public_categ_ids.filtered(
            lambda categ: categ.can_access_from_current_website()
        )[:1]
        markup_data = [
            website._prepare_ecommerce_store_markup_data(),
            product._to_markup_data(website),
        ]
        if category:
            # Add breadcrumb's SEO data.
            markup_data.append(
                self._prepare_breadcrumb_markup_data(website.get_base_url(), category)
            )
        keep = QueryURL(SHOP_PATH, **request.session.get("attribute_value_params", {}))

        attribute_value_params = self._get_attribute_value_params(kwargs)
        attribute_value_dict = self._get_attribute_value_dict(attribute_value_params)
        attribute_value_ids = set(itertools.chain.from_iterable(attribute_value_dict.values()))
        # TODO: remove support for `attribute_values` query param in version 20 (or later).
        if not attribute_value_ids and (attribute_values := kwargs.get("attribute_values")):
            attribute_value_ids = {
                int(value_id)
                for value_id in attribute_values.split(",")
                if value_id and value_id.isdigit()
            }
            grouped_attributes_values = (
                self
                .env["product.attribute.value"]
                .browse(attribute_value_ids)
                .exists()
                .sorted()
                .grouped("attribute_id")
            )
            return {"redirect_url": self._get_url_with_attribute_values(grouped_attributes_values)}
        if attribute_value_ids:
            combination = product.attribute_line_ids.mapped(
                lambda ptal: (
                    (
                        ptal.product_template_value_ids.filtered(
                            lambda ptav: (
                                ptav.ptav_active
                                and ptav.product_attribute_value_id.id in attribute_value_ids
                            )
                        )[:1]
                    )
                    or ptal.product_template_value_ids.filtered("ptav_active")[:1]
                )
            )
            combination_info = product._get_combination_info(
                combination=combination.with_env(self.env)
            )
            attribute_value_images = product._get_dynamic_attribute_images(
                combination.ids, request.website.id
            )
        else:
            combination_info = product._get_combination_info()
            attribute_value_images = product._get_dynamic_attribute_images([], request.website.id)

        # Needed to trigger the recently viewed product rpc
        view_track = website.viewref("website_sale.product").track

        return {
            "attribute_value_images": attribute_value_images,
            "categories": self.env["product.public.category"].search([("parent_id", "=", False)]),
            "category": category,
            "combination_info": combination_info,
            "has_available_uoms": len(product._get_available_uoms()) > 0,
            "keep": keep,
            "main_object": product,
            "product": product,
            "product_variant": self.env["product.product"].browse(combination_info["product_id"]),
            "view_track": view_track,
            "markup_data_json": json_scriptsafe.dumps(markup_data, indent=2),
            "shop_path": SHOP_PATH,
            "user_email": self.env.user.email
            or request.session.get("stock_notification_email", ""),
        }

    def _prepare_breadcrumb_markup_data(self, base_url, category):
        """Generate JSON-LD breadcrumb markup data for the given category.

        See https://schema.org/BreadcrumbList.

        :param str base_url: The base URL of the current website.
        :param product.public.category category: The current product category.
        :return: The JSON-LD markup data.
        :rtype: dict
        """
        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i,
                    "name": cat.name,
                    "item": f"{base_url}{cat.website_url}",
                }
                for i, cat in enumerate(category.parents_and_self, start=1)
            ],
        }

    @route(
        '/shop/change_pricelist/<model("product.pricelist"):pricelist>',
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def pricelist_change(self, pricelist, **_post):
        website = self.env["website"].get_current_website()
        redirect_url = request.httprequest.referrer
        prev_pricelist = request.pricelist
        if (
            self._apply_selectable_pricelist(pricelist.id)
            and redirect_url
            and website.is_view_active("website_sale.filter_products_price")
            and prev_pricelist != pricelist
        ):
            # Convert prices to the new priceslist currency in the query params of the referrer
            decoded_url = url_parse(redirect_url)
            args = url_decode(decoded_url.query)
            min_price = args.get("min_price")
            max_price = args.get("max_price")
            if min_price or max_price:
                try:
                    min_price = float(min_price)
                    args["min_price"] = min_price and str(
                        prev_pricelist.currency_id._convert(
                            min_price,
                            pricelist.currency_id,
                            request.website.company_id,
                            fields.Date.today(),
                            round=False,
                        )
                    )
                except (ValueError, TypeError):
                    pass
                try:
                    max_price = float(max_price)
                    args["max_price"] = max_price and str(
                        prev_pricelist.currency_id._convert(
                            max_price,
                            pricelist.currency_id,
                            request.website.company_id,
                            fields.Date.today(),
                            round=False,
                        )
                    )
                except (ValueError, TypeError):
                    pass
            redirect_url = decoded_url.replace(query=url_encode(args)).to_url()

        return request.redirect(redirect_url or SHOP_PATH)

    @route("/shop/pricelist", type="http", auth="public", website=True, sitemap=False)
    def pricelist(self, promo, **post):
        redirect = post.get("r", "/shop/cart")
        if promo:
            pricelist_sudo = (
                self.env["product.pricelist"].sudo().search([("code", "=", promo)], limit=1)
            )
            if not (pricelist_sudo and request.website.is_pricelist_available(pricelist_sudo.id)):
                return request.redirect("%s?code_not_available=1" % redirect)

            self._apply_pricelist(pricelist=pricelist_sudo)
        else:
            # Reset the pricelist if empty promo code is given
            self._apply_pricelist(pricelist=None)

        return request.redirect(redirect)

    def _apply_selectable_pricelist(self, pricelist_id):
        """Change the pricelist if selectable on the website.

        A pricelist is applied if:
        - it is available on the current website
        - it is selectable or on the current partner

        :param int pricelist_id: the pricelist ID
        :return: True or False if the pricelist was applied or not
        :rtype: bool
        """
        if (
            self.env["website"].get_current_website().is_pricelist_available(pricelist_id)
            and (pricelist := self.env["product.pricelist"].browse(pricelist_id))
            and (
                pricelist.selectable
                or pricelist == self.env.user.partner_id.property_product_pricelist
            )
        ):
            self._apply_pricelist(pricelist=pricelist)
            return True
        return False

    def _apply_pricelist(self, pricelist=None):
        """Change the pricelist of the request and recomputes the current cart prices.

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

    # ------------------------------------------------------
    # Checkout
    # ------------------------------------------------------

    # === CHECKOUT FLOW - ADDRESS METHODS === #

    @route(
        "/shop/checkout",
        type="http",
        methods=["GET"],
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Shop Checkout"),
    )
    def shop_checkout(self, try_skip_step=None, **query_params):
        """Display the checkout page.

        :param str try_skip_step: Whether the user should immediately be redirected to the next step
                                  if no additional information (i.e., address or delivery method) is
                                  required on the checkout page. 'true' or 'false'.
        :param dict query_params: The additional query string parameters.
        :return: The rendered checkout page.
        :rtype: str
        """
        try_skip_step = str2bool(try_skip_step or "false")
        order_sudo = request.cart

        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/checkout", order_sudo
        ):
            return request.redirect(redirect)

        request.session["sale_last_order_id"] = order_sudo.id
        checkout_page_values = self._prepare_checkout_page_values(order_sudo, **query_params)

        can_skip_delivery = True  # Delivery is only needed for deliverable products.
        if order_sudo._has_deliverable_products():
            can_skip_delivery = False
            available_dms = order_sudo._get_delivery_methods()
            checkout_page_values["delivery_methods"] = available_dms
            if delivery_method := order_sudo._get_preferred_delivery_method(available_dms):
                rate = delivery_method.rate_shipment(order_sudo)
                if (
                    not order_sudo.carrier_id
                    or not rate.get("success")
                    or order_sudo.amount_delivery != rate["price"]
                ):
                    order_sudo._set_delivery_method(delivery_method, rate=rate)

        checkout_page_values.update(request.website._get_checkout_step_values("/shop/checkout"))
        if try_skip_step and can_skip_delivery:
            return request.redirect(checkout_page_values["next_website_checkout_step_href"])

        return request.render("website_sale.checkout", checkout_page_values)

    def _prepare_checkout_page_values(self, order_sudo, **kwargs):
        """Provide the data used to render the /shop/checkout page.

        :param sale.order order_sudo: The current cart.
        :param dict kwargs: unused parameters available for potential overrides.
        :return: The checkout page rendering values.
        :rtype: dict
        """
        partner_sudo = order_sudo.partner_id
        return {
            "order": order_sudo,
            "website_sale_order": order_sudo,  # Compatibility with other templates.
            "use_delivery_as_billing": (
                order_sudo.partner_shipping_id == order_sudo.partner_invoice_id
            ),
            "only_services": order_sudo.only_services,
            **self._prepare_address_data(partner_sudo, order_sudo=order_sudo, **kwargs),
            "address_url": "/shop/address",
        }

    @route(
        "/shop/address", type="http", methods=["GET"], auth="public", website=True, sitemap=False
    )
    def shop_address(
        self, partner_id=None, address_type="billing", use_delivery_as_billing=None, **query_params
    ):
        """Display the address form.

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
        use_delivery_as_billing = str2bool(use_delivery_as_billing or "false")
        order_sudo = request.cart

        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/address", order_sudo
        ):
            return request.redirect(redirect)

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )

        use_delivery_as_billing = str2bool(use_delivery_as_billing or "false")
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
            **query_params,
        )
        address_form_values.update(request.website._get_checkout_step_values("/shop/address"))
        return request.render("website_sale.address", address_form_values)

    def _prepare_address_form_values(self, *args, callback="", order_sudo=False, **kwargs):
        """Prepare the rendering values of the address form.

        :param str callback: The URL to redirect to in case of successful address creation/update.
        :param sale.order order_sudo: The current cart.
        :return: The checkout page values.
        :rtype: dict
        """
        rendering_values = super()._prepare_address_form_values(
            *args, order_sudo=order_sudo, callback=callback, **kwargs
        )
        if not order_sudo:  # Return portal address values if not order
            return rendering_values

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        # Display b2b field is feature is enabled on given website
        rendering_values["display_b2b_fields"] = rendering_values.get(
            "display_b2b_fields", False
        ) or request.website.is_view_active("website_sale.address_b2b")

        if rendering_values["commercial_address_update_url"]:
            rendering_values["commercial_address_update_url"] = (
                f"/shop/address?partner_id={order_sudo.partner_id.id}"
            )

        return {
            **rendering_values,
            "is_anonymous_cart": is_anonymous_cart,
            "website_sale_order": order_sudo,
            "only_services": order_sudo.only_services,
            "discard_url": callback or (is_anonymous_cart and "/shop/cart") or "/shop/checkout",
        }

    def _get_default_country(self, order_sudo=False, **kwargs):
        """Override `portal` to return country of customer if customer is not logged in."""
        is_anonymous_cart = order_sudo and order_sudo._is_anonymous_cart()
        if is_anonymous_cart and request.geoip.country_code:
            return (
                self
                .env["res.country"]
                .sudo()
                .search([("code", "=", request.geoip.country_code)], limit=1)
            )
        return super()._get_default_country(order_sudo=order_sudo, **kwargs)

    @route(
        "/shop/address/submit",
        type="http",
        methods=["POST"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def shop_address_submit(
        self,
        partner_id=None,
        address_type="billing",
        use_delivery_as_billing=None,
        callback=None,
        **form_data,
    ):
        """Create or update an address.

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
        redirect_dict = {}
        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/address", order_sudo
        ):
            # Delay the redirection to save the address update
            redirect_dict["redirectUrl"] = redirect

        # Retrieve the partner whose address to update, if any, and its address type.
        partner_sudo, address_type = self._prepare_address_update(
            order_sudo, partner_id=partner_id and int(partner_id), address_type=address_type
        )

        is_new_address = not partner_sudo
        if is_new_address or order_sudo.only_services:
            callback = callback or "/shop/checkout?try_skip_step=true"
        else:
            callback = callback or "/shop/checkout"

        partner_sudo, feedback_dict = self._create_or_update_address(
            partner_sudo,
            address_type=address_type,
            use_delivery_as_billing=use_delivery_as_billing,
            callback=callback,
            order_sudo=order_sudo,
            **form_data,
        )

        if feedback_dict.get("invalid_fields"):
            # Return if error when creating/updating partner.
            return request.make_json_response(feedback_dict)

        is_anonymous_cart = order_sudo._is_anonymous_cart()
        is_main_address = is_anonymous_cart or order_sudo.partner_id.id == partner_sudo.id
        partner_fnames = set()
        if is_main_address:  # Main customer address updated.
            partner_fnames.add("partner_id")  # Force the re-computation of partner-based fields.

        if address_type == "billing":
            partner_fnames.add("partner_invoice_id")
            if is_new_address and order_sudo.only_services:
                # The delivery address is required to make the order.
                partner_fnames.add("partner_shipping_id")
        elif address_type == "delivery":
            partner_fnames.add("partner_shipping_id")
            if use_delivery_as_billing:
                partner_fnames.add("partner_invoice_id")

        order_sudo._update_address(partner_sudo.id, partner_fnames)

        if order_sudo._is_anonymous_cart():
            # Unsubscribe the public partner if the cart was previously anonymous.
            order_sudo.message_unsubscribe(order_sudo.website_id.partner_id.ids)

        if redirect_dict:
            # Redirect after the address is complete and saved
            return request.make_json_response(redirect_dict)

        return request.make_json_response(feedback_dict)

    def _prepare_address_update(self, order_sudo, partner_id=None, address_type=None):
        """Find the partner whose address to update and return it along with its address type.

        :param sale.order order_sudo: The current cart.
        :param int partner_id: The partner whose address to update, if any, as a `res.partner` id.
        :param str address_type: The type of the address: 'billing' or 'delivery'.
        :return: The partner whose address to update, if any, and its address type.
        :rtype: tuple[res.partner, str]
        :raise Forbidden: If the customer is not allowed to update the given address.
        """
        PartnerSudo = self.env["res.partner"].with_context(show_address=1).sudo()
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
                address_type = "billing"
            elif partner_id == order_sudo.partner_shipping_id.id:
                address_type = "delivery"
            else:
                address_type = "billing"

        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer(
            order_sudo=order_sudo
        ):
            raise Forbidden

        return partner_sudo, address_type

    def _complete_address_values(self, address_values, *args, order_sudo=False, **kwargs):
        super()._complete_address_values(address_values, *args, order_sudo=order_sudo, **kwargs)

        if order_sudo and order_sudo._is_anonymous_cart():
            address_values["type"] = "contact"

        if address_values["lang"] not in request.website.mapped("language_ids.code"):
            address_values.pop("lang")

        if not order_sudo:
            return
        address_values["company_id"] = (
            order_sudo.website_id.company_id.id or address_values["company_id"]
        )
        address_values["user_id"] = order_sudo.website_id.salesperson_id.id

        if order_sudo.website_id.specific_user_account:
            address_values["website_id"] = order_sudo.website_id.id

    def _create_new_address(
        self, address_values, address_type, use_delivery_as_billing, order_sudo
    ):
        """Create a new partner, must be called after the data has been verified.

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
        creation_context = clean_context(self.env.context)
        creation_context.update({
            # 'no_vat_validation': True,  # TODO VCR VAT validation or not ?
        })
        return self.env["res.partner"].sudo().with_context(creation_context).create(address_values)

    @route(
        _express_checkout_route,
        type="jsonrpc",
        methods=["POST"],
        auth="public",
        website=True,
        sitemap=False,
    )
    def process_express_checkout(
        self, billing_address, shipping_address=None, shipping_option=None, **_kwargs
    ):
        """Record the partner information on the order when using express checkout flow.

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
                address_type="billing",
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )
            with self.env.protecting([order_sudo._fields["pricelist_id"]], order_sudo):
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
                address_type="billing",
                use_delivery_as_billing=False,
                order_sudo=order_sudo,
            )

        # In a non-express flow, `sale_last_order_id` would be added in the session before the
        # payment. As we skip all the steps with the express checkout, `sale_last_order_id` must be
        # assigned to ensure the right behavior from `shop_payment_confirmation()`.
        request.session["sale_last_order_id"] = order_sudo.id

        if shipping_address:
            # in order to not override shippig address, it's checked separately from shipping option
            self._include_country_and_state_in_address(shipping_address)
            shipping_address, _side_values = self._parse_form_data(shipping_address)

            if order_sudo.name in order_sudo.partner_shipping_id.name:
                # The existing partner was created by `process_express_checkout_delivery_choice`, it
                # means that the partner is missing information, so we update it.
                order_sudo.partner_shipping_id.write(shipping_address)
                order_sudo._update_address(
                    order_sudo.partner_shipping_id.id, ["partner_shipping_id"]
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
                    address_type="delivery",
                    use_delivery_as_billing=False,
                    order_sudo=order_sudo,
                )
            # Process the delivery method.
            if shipping_option:
                dm_id = int(shipping_option["id"])
                available_dms = order_sudo._get_delivery_methods()
                order_sudo._set_delivery_method(available_dms.filtered(lambda dm: dm.id == dm_id))

        return order_sudo.partner_id.id

    def _find_child_partner(self, commercial_partner_id, address):
        """Find a child partner for a specified address.

        Compare all keys in the `address` dict with the same keys on the partner object and return
        the id of the first partner that have the same value than in the dict for all the keys.

        :param int commercial_partner_id: The commercial partner whose child to find.
        :param dict address: The address fields.
        :return: The ID of the first child partner that match the criteria, if any.
        :rtype: int
        """
        partners_sudo = (
            self
            .env["res.partner"]
            .with_context(show_address=1)
            .sudo()
            .search([("id", "child_of", commercial_partner_id)])
        )
        for partner_sudo in partners_sudo:
            if self._are_same_addresses(address, partner_sudo):
                return partner_sudo.id
        return False

    def _include_country_and_state_in_address(self, address):
        """Include country_id and state_id in address.

        Fetch country and state and include the records in address. The object is included to
        simplify the comparison of addresses.

        :param dict address: An address with country and state defined in ISO 3166.
        :return None:
        """
        country = self.env["res.country"].search([("code", "=", address.pop("country"))], limit=1)
        state_id = False
        if state_code := address.pop("state", False):
            state_id = country.state_ids.filtered(lambda state: state.code == state_code).id
        address.update(country_id=country.id, state_id=state_id)

    @route("/shop/update_address", type="jsonrpc", auth="public", website=True)
    def shop_update_address(
        self, partner_id, address_type="billing", use_delivery_as_billing=False, **_kw
    ):
        partner_id = int(partner_id)

        if not (order_sudo := request.cart):
            return

        ResPartner = self.env["res.partner"].sudo()
        partner_sudo = ResPartner.browse(partner_id).exists()
        children = ResPartner._search([
            ("id", "child_of", order_sudo.partner_id.commercial_partner_id.id),
            ("type", "in", ("invoice", "delivery", "other")),
        ])
        if (
            partner_sudo not in {order_sudo.partner_id, order_sudo.partner_id.commercial_partner_id}
            and partner_sudo.id not in children
        ):
            raise Forbidden

        partner_fnames = set()
        if (
            use_delivery_as_billing or address_type == "billing"
        ) and partner_sudo != order_sudo.partner_invoice_id:
            partner_fnames.add("partner_invoice_id")
        if address_type == "delivery" and partner_sudo != order_sudo.partner_shipping_id:
            partner_fnames.add("partner_shipping_id")

        order_sudo._update_address(partner_id, partner_fnames)

    # === CHECKOUT FLOW - EXTRA STEP METHODS === #
    def system_page_extra_info(env):  # noqa: N805
        website = env["website"].get_current_website()
        if website.is_view_active("website_sale.extra_info"):
            return _lt("Shop Checkout - Extra Information")
        return False

    @route(
        ["/shop/extra_info"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=system_page_extra_info,
    )
    def extra_info(self, **post):
        # Check that this option is activated
        extra_step = request.website.viewref("website_sale.extra_info")
        if not extra_step.active:
            return request.redirect(
                request.website._get_next_breadcrumb_step_href("/shop/extra_info")
            )

        order_sudo = request.cart
        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/extra_info", order_sudo
        ):
            return request.redirect(redirect)

        values = {
            "website_sale_order": order_sudo,
            "post": post,
            "escape": lambda x: x.replace("'", r"\'"),
            "partner": order_sudo.partner_id.id,
            "order": order_sudo,
        }

        values.update(request.website._get_checkout_step_values("/shop/extra_info"))

        return request.render("website_sale.extra_info", values)

    # === CHECKOUT FLOW - PAYMENT/CONFIRMATION METHODS === #

    def _get_shop_payment_values(self, order, **_kwargs):
        checkout_page_values = {
            "sale_order": order,
            "website_sale_order": order,
            "cart_has_blocking_alerts": order._has_blocking_alerts(),
            "partner": order.partner_invoice_id,
            "order": order,
            "only_services": order.only_services,
            **request.website._get_checkout_step_values("/shop/payment"),
        }
        payment_form_values = {
            **sale_portal.CustomerPortal._get_payment_values(
                self, order, website_id=request.website.id
            ),
            "display_submit_button": False,  # The submit button is re-added outside the form.
            "transaction_route": f"/shop/payment/transaction/{order.id}",
            "landing_route": "/shop/payment/validate",
            "sale_order_id": order.id,  # Allow Stripe to check if tokenization is required.
        }
        if checkout_page_values["cart_has_blocking_alerts"]:
            payment_form_values.pop("payment_methods_sudo", "")
            payment_form_values.pop("tokens_sudo", "")
        return checkout_page_values | payment_form_values

    @route(
        "/shop/payment",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Shop Payment"),
    )
    def shop_payment(self, **post):
        """Payment step. This page proposes several payment means based on available
        payment.provider. State at this point:
         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.provider website but closed the tab without
           paying / canceling.
        """
        order_sudo = request.cart
        if redirect := self.env["website.checkout.step"].validate_checkout_progress(
            "/shop/payment", order_sudo
        ):
            return request.redirect(redirect)

        # Ensure the prices are up to date and final
        order_sudo._update_cart_taxes_and_prices()
        return request.render(
            "website_sale.payment", self._get_shop_payment_values(order_sudo, **post)
        )

    @route("/shop/payment/validate", type="http", auth="public", website=True, sitemap=False)
    def shop_payment_validate(self, sale_order_id=None, **_post):
        """Server calls this method when receiving an update for a transaction. State at this point:
        - UDPATE ME.
        """
        if sale_order_id is None:
            order_sudo = request.cart
            if not order_sudo and "sale_last_order_id" in request.session:
                # Retrieve the last known order from the session if the session key `sale_order_id`
                # was prematurely cleared. This is done to prevent the user from updating their cart
                # after payment in case they don't return from payment through this route.
                last_order_id = request.session["sale_last_order_id"]
                order_sudo = self.env["sale.order"].sudo().browse(last_order_id).exists()
        else:
            order_sudo = self.env["sale.order"].sudo().browse(sale_order_id)
            assert order_sudo.id == request.session.get("sale_last_order_id")

        if not order_sudo:
            return request.redirect(SHOP_PATH)

        tx_sudo = order_sudo.get_portal_last_transaction()
        if order_sudo.amount_total and not tx_sudo:
            return request.redirect(SHOP_PATH)

        if not order_sudo.amount_total and not tx_sudo and order_sudo.state == "draft":
            # Customer didn't go through /shop/payment/transaction since there is nothing to pay,
            # confirm the order if it is valid.
            if redirect := self.env["website.checkout.step"].validate_checkout_progress(
                "/shop/payment/transaction", order_sudo
            ):
                return request.redirect(redirect)

            order_sudo._validate_order()

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx_sudo and tx_sudo.state == "draft":
            return request.redirect(SHOP_PATH)

        return request.redirect("/shop/confirmation")

    @route(
        ["/shop/confirmation"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        list_as_website_content=_lt("Shop Confirmation"),
    )
    def shop_payment_confirmation(self, **_post):
        """End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point:
         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore.
        """
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            order = self.env["sale.order"].sudo().browse(sale_order_id)
            values = self._prepare_shop_payment_confirmation_values(order)
            return request.render("website_sale.confirmation", values)
        return request.redirect(SHOP_PATH)

    def _prepare_shop_payment_confirmation_values(self, order):
        """Prepare the dict containing the values to be rendered by the confirmation template.
        This method is called in the payment process route.
        """
        rendering_values = {
            "order": order,
            "website_sale_order": order,
            "order_tracking_info": self.order_2_return_dict(order),
        }
        if (
            self.env["res.users"]._get_signup_invitation_scope() == "b2c"
            and request.website.is_public_user()
        ):
            order.partner_id.signup_prepare()
            signup_url = urlparse(
                order.partner_id.with_context(relative_url=True)._get_signup_url()
            )

            rendering_values["signup_url"] = signup_url._replace(
                query=urlencode(
                    dict(parse_qs(signup_url.query), redirect="/shop/unarchive_user_addresses"),
                    doseq=True,
                )
            ).geturl()

        return rendering_values

    @route("/shop/unarchive_user_addresses", type="http", auth="user", sitemap=False)
    def shop_unarchive_user_addresses(self):
        self.env["res.partner"].sudo().search([
            ("active", "=", False),
            ("parent_id", "=", self.env.user.partner_id.id),
        ]).active = True

        return request.redirect("/my")

    @route(["/shop/print"], type="http", auth="public", website=True, sitemap=False)
    def print_saleorder(self, **_kwargs):
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            sale_order = self.env["sale.order"].sudo().browse(sale_order_id)
            filename = "%s.pdf" % (f"Order - {sale_order.name}" or "Order")
            pdf, _ = (
                self
                .env["ir.actions.report"]
                .sudo()
                ._render_qweb_pdf("sale.action_report_saleorder", [sale_order_id])
            )
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", "%s" % len(pdf)),
                ("Content-Disposition", content_disposition(filename, "inline")),
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        return request.redirect(SHOP_PATH)

    @route(["/shop/print/invoice"], type="http", auth="public", website=True, sitemap=False)
    def print_invoice(self, **_kwargs):
        sale_order_id = request.session.get("sale_last_order_id")
        if sale_order_id:
            sale_order = self.env["sale.order"].sudo().browse(sale_order_id)
            invoice = sale_order.invoice_ids and sale_order.invoice_ids[0]
            if invoice:
                pdf, _ = (
                    self
                    .env["ir.actions.report"]
                    .sudo()
                    ._render_qweb_pdf("account.account_invoices", [invoice.id])
                )
                filename = "%s.pdf" % (invoice.name or "Invoice")
                pdfhttpheaders = [
                    ("Content-Type", "application/pdf"),
                    ("Content-Length", "%s" % len(pdf)),
                    ("Content-Disposition", content_disposition(filename, "inline")),
                ]
                return request.make_response(pdf, headers=pdfhttpheaders)
        return request.redirect(SHOP_PATH)

    # ------------------------------------------------------
    # Edit
    # ------------------------------------------------------

    @route(["/shop/config/product"], type="jsonrpc", auth="user")
    def change_product_config(self, product_id, **options):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        product = self.env["product.template"].browse(product_id)
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
            product.write({"website_size_x": options["x"], "website_size_y": options["y"]})

    @route(["/shop/config/attribute"], type="jsonrpc", auth="user")
    def change_attribute_config(self, attribute_id, **options):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        attribute = self.env["product.attribute"].browse(attribute_id)
        if "display_type" in options:
            attribute.write({"display_type": options["display_type"]})
            self.env.registry.clear_cache("templates")

    @route(["/shop/config/website"], type="jsonrpc", auth="user")
    def _change_website_config(self, **options):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        current_website = self.env["website"].get_current_website()
        # Restrict options we can write to.
        writable_fields = {
            "shop_page_container",
            "shop_ppg",
            "shop_ppr",
            "shop_default_sort",
            "shop_gap",
            "shop_opt_products_design_classes",
            "product_page_container",
            "product_page_image_layout",
            "product_page_image_width",
            "product_page_grid_columns",
            "product_page_image_spacing",
            "product_page_image_ratio",
            "product_page_image_ratio_mobile",
            "product_page_cols_order",
            "product_page_image_roundness",
            "product_page_cta_design",
            # wishlist
            "wishlist_opt_products_design_classes",
            "wishlist_grid_columns",
            "wishlist_mobile_columns",
            "wishlist_gap",
        }
        # Default ppg to 1.
        if "ppg" in options and not options["ppg"]:
            options["ppg"] = 1
        if "product_page_grid_columns" in options:
            options["product_page_grid_columns"] = int(options["product_page_grid_columns"])

        # Checkout Extra Step
        if "extra_step" in options:
            extra_step_view = current_website.viewref("website_sale.extra_info")
            extra_step = current_website._get_checkout_step("/shop/extra_info")
            extra_step_view.active = extra_step.is_published = options.get("extra_step") == "true"

        write_vals = {k: v for k, v in options.items() if k in writable_fields}
        if write_vals:
            current_website.write(write_vals)

    @route(["/shop/config/category"], type="jsonrpc", auth="user")
    def _change_category_config(self, category_id, **options):
        category = self.env["product.public.category"].browse(int(category_id))
        if not category.exists():
            raise NotFound

        # Restrict options we can write to.
        targeted_options = {
            "show_category_title",
            "show_category_description",
            "align_category_content",
        }
        modified_options = {
            option: value for option, value in options.items() if option in targeted_options
        }
        if modified_options:
            category.write(modified_options)

    def order_lines_2_google_api(self, order_lines):
        """Transform a list of order lines into a dict for google analytics."""
        ret = []
        for line in order_lines.filtered(lambda line: not line.is_delivery):
            product = line.product_id
            ret.append({
                "item_id": product.barcode or product.id,
                "item_name": product.name or "-",
                "item_category": product.categ_id.name or "-",
                "price": line.price_unit,
                "quantity": line.product_uom_qty,
            })
        return ret

    def order_2_return_dict(self, order):
        """Return the tracking_cart dict of the order for Google analytics basically defined to
        be inherited."""
        tracking_cart_dict = {
            "transaction_id": order.id,
            "affiliation": order.company_id.name,
            "value": order.amount_total,
            "tax": order.amount_tax,
            "currency": order.currency_id.name,
            "items": self.order_lines_2_google_api(order.order_line),
        }
        delivery_line = order.order_line.filtered("is_delivery")
        if delivery_line:
            tracking_cart_dict["shipping"] = delivery_line.price_unit
        return tracking_cart_dict

    # --------------------------------------------------------------------------
    # Products Recently Viewed
    # --------------------------------------------------------------------------
    @route("/shop/products/recently_viewed_delete", type="jsonrpc", auth="public", website=True)
    def products_recently_viewed_delete(self, product_id=None, product_template_id=None, **_kwargs):
        if not (product_id or product_template_id):
            return None
        visitor_sudo = self.env["ir.http"]._get_visitor_from_request()
        if visitor_sudo:
            domain = [("visitor_id", "=", visitor_sudo.id)]
            if product_id:
                domain += [("product_id", "=", int(product_id))]
            else:
                domain += [("product_id.product_tmpl_id", "=", int(product_template_id))]
            self.env["website.track"].sudo().search(domain).unlink()
        return {}

    @route("/snippets/category/set_image", type="jsonrpc", auth="user")
    def set_category_image(self, category_id, attachment_id):
        """
        Set the cover image on the category.

        :param int category_id: ID of the category to set the cover image.
        :param int attachment_id: ID of the attachment containing the image data.
        :raise Forbidden: If the user does not have website editing access
        """
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise Forbidden
        category = self.env["product.public.category"].browse(category_id).exists()
        if category:
            image_data = self.env["ir.attachment"].browse(attachment_id).raw
            category.cover_image = image_data

    @staticmethod
    def _populate_currency_and_pricelist(kwargs):
        website = request.website
        kwargs.update({"currency_id": website.currency_id.id, "pricelist_id": request.pricelist.id})

    @staticmethod
    def _validate_and_get_category(category):
        """Validate and return the `product.public.category` record corresponding to the provided
        category, which can be a record, a record id, or a slug.

        If the provided category is invalid, non-existing, or inaccessible, return an empty
        recordset. Otherwise, return the corresponding record.

        :param str|product.public.category category: The category to validate and return.
        :return: The validated category, or an empty recordset.
        :rtype: product.public.category
        """
        ProductCategory = request.env["product.public.category"]
        if category and isinstance(category, str) and not category.isdigit():
            return ProductCategory
        if (
            category := ProductCategory.browse(category and int(category)).exists()
        ) and category.can_access_from_current_website():
            return category
        return ProductCategory

    def _get_attribute_value_params(self, query_params):
        """Extract the attribute value query params from a dict of more general query params.

        Attribute value query params are expected to have the following format:
        `attribute-name-1=attribute-value-name-2,attribute-value-name-3`

        :param dict(str, str) query_params: The more general query params from which to extract the
            attribute value query params.
        :return: A dict of attribute value query params.
        :rtype: dict(str, str)
        """
        unslug = self.env["ir.http"]._unslug
        # Only keep the query params whose key can be unslugged (meaning that the key is an
        # attribute slug).
        return {
            attr: attr_values
            for attr, attr_values in query_params.items()
            if unslug(attr)[1] and attr_values
        }

    def _get_attribute_value_dict(self, attribute_value_params):
        """Return a dict mapping attribute IDs to lists of attribute value IDs, from a dict of
        attribute value query params.

        Attribute value query params are expected to have the following format:
        `attribute-name-1=attribute-value-name-2,attribute-value-name-3`

        This method will ignore any invalid attributes and attribute values (we don't want to raise
        errors for invalid query params). Moreover, it will only consider the first occurrence of a
        given attribute (other occurrences are ignored).

        :param dict(str, str) attribute_value_params: The attribute value query params from which to
            compute the mapping.
        :return: A dict mapping attribute IDs to lists of attribute value IDs.
        :rtype: dict(int, list(int))
        """
        unslug = self.env["ir.http"]._unslug
        # For each attribute value query param, unslug its key (attribute) and value (attribute
        # values).
        attribute_value_dict = {
            unslug(attr)[1]: [unslug(attr_value)[1] for attr_value in attr_values.split(",")]
            for attr, attr_values in attribute_value_params.items()
        }
        # Only keep the attributes and attribute values that were correctly unslugged.
        filtered_attribute_value_dict = {
            attr_id: [attr_value_id for attr_value_id in attr_value_ids if attr_value_id]
            for attr_id, attr_value_ids in attribute_value_dict.items()
            if attr_id
        }
        # Only keep attributes that have at least one attribute value.
        return {
            attr_id: attr_value_ids
            for attr_id, attr_value_ids in filtered_attribute_value_dict.items()
            if attr_value_ids
        }

    def _get_url_with_attribute_values(self, grouped_attributes_values):
        """Return the current request's URL, but replace the attribute value query params with
        `grouped_attributes_values` (formatted as query params).
        """
        query = request.httprequest.args.to_dict(flat=False)
        query.pop("attribute_values", None)
        slug = self.env["ir.http"]._slug
        for pa, pavs in grouped_attributes_values.items():
            query[slug(pa)] = ",".join([slug(pav) for pav in pavs])
        url = urlparse(request.httprequest.url)
        return url._replace(query=urlencode(query, doseq=True)).geturl()
