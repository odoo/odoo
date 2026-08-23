# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlencode, urlsplit

from werkzeug.exceptions import NotFound
from werkzeug.urls import url_decode, url_encode, url_parse

from odoo import fields
from odoo.fields import Domain
from odoo.http import request, route
from odoo.tools import SQL, float_round, lazy
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment.controllers import portal as payment_portal
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


class Shop(payment_portal.PaymentPortal):
    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        order = post.get("order") or self.env.website.shop_default_sort
        return "is_published desc, %s, id desc" % order

    def _add_search_subdomains_hook(self, _search):
        return []

    def _get_shop_domain(
        self, search, category, attribute_value_dict, search_in_description=True, tags=None
    ):
        domains = [self.env.website.sale_product_domain()]
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
        if env.website and env.website.ecommerce_access == "logged_in" and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        if not qs or qs.lower() in SHOP_PATH:
            yield {"loc": SHOP_PATH}

        Category = env["product.public.category"]
        dom = sitemap_qs2dom(qs, f"{SHOP_PATH}/category", Category._rec_name)
        dom &= env.website.website_domain()
        for cat in Category.search(dom):
            loc = cat.website_url
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
        self,
        search,
        min_price,
        max_price,
        order=None,
        tags=None,
        on_sale=None,
        in_stock=None,
        **_kwargs,
    ):
        return {
            "search": search,
            "min_price": min_price,
            "max_price": max_price,
            "order": order,
            "tags": tags,
            "on_sale": on_sale,
            "in_stock": in_stock,
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
        ) and category.website_id.id in (request.env.website.id, False):
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
        url = urlsplit(request.httprequest.url)
        return url._replace(query=urlencode(query, doseq=True)).geturl()

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
    def shop(
        self,
        page=0,
        category=None,
        search="",
        min_price=0.0,
        max_price=0.0,
        tags="",
        on_sale=None,
        in_stock=None,
        **post,
    ):
        not_reload_request = request.httprequest.path != "/shop/reload"
        website = self.env.website
        if not_reload_request and not website.has_ecommerce_access():
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
            if not_reload_request and path != request.httprequest.path:
                url = urlsplit(request.httprequest.url)
                return request.redirect(url._replace(path=path).geturl(), code=301)

        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

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
        if not_reload_request and request.httprequest.args.getlist("attribute_values"):
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
            url,
            **self._shop_get_query_url_kwargs(
                search, min_price, max_price, on_sale=on_sale, in_stock=in_stock, **post
            ),
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
                company_currency, website.currency_id, website.company_id, fields.Date.today()
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

        # Dynamic ribbon filters ("On sale" / "In stock")
        on_sale_active = on_sale == "1"
        in_stock_active = in_stock == "1"
        auto_assign_ribbons = self.env["product.ribbon"].sudo().search([("assign", "!=", "manual")])
        ribbon_assign_values = set(auto_assign_ribbons.mapped("assign"))

        on_sale_ids = set()
        sold_out_ids = set()
        if "sale" in ribbon_assign_values:
            sales_prices = search_product._get_sales_prices(
                request.pricelist.with_context(self.env.context),
                request.fiscal_position.with_context(self.env.context),
                website.with_context(self.env.context),
            )
            on_sale_ids = {pid for pid, prices in sales_prices.items() if "base_price" in prices}
        if "out_of_stock" in ribbon_assign_values:
            sold_out_ids = {p.id for p in search_product if p._is_sold_out()}

        show_on_sale_filter = bool(on_sale_ids) or (
            on_sale_active and "sale" in ribbon_assign_values
        )
        show_in_stock_filter = bool(sold_out_ids) or (
            in_stock_active and "out_of_stock" in ribbon_assign_values
        )

        if on_sale_active and "sale" in ribbon_assign_values:
            search_product = search_product.filtered(lambda p: p.id in on_sale_ids)
        if in_stock_active and "out_of_stock" in ribbon_assign_values:
            search_product = search_product.filtered(lambda p: p.id not in sold_out_ids)
        if on_sale_active or in_stock_active:
            product_count = len(search_product)

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
            # using a sub-query is more efficient than using a query in the shape of "ids in (...)"
            # when there are 100k product ids to match.
            search_categories = Category.search(
                Domain("product_tmpl_ids", "in", shop_query)
            ).parents_and_self
            categs_domain &= Domain("id", "in", search_categories.ids)
        else:
            search_categories = Category
        categs = Category.search_fetch(categs_domain)

        category_entries = Category
        if category:
            available_categories = category.child_id.filtered(
                lambda c: c.website_id.id in (website.id, False)
            )
            category_entries = (
                not search and available_categories
            ) or available_categories.filtered(lambda c: c.id in search_categories.ids)
            if not category_entries:
                parent = category.parent_id
                available_categories = parent.child_id.filtered(
                    lambda c: c.website_id.id in (website.id, False)
                )
                category_entries = (
                    not search and available_categories
                ) or available_categories.filtered(lambda c: c.id in search_categories.ids)
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
            pavs_per_attribute.update({
                attribute: pavs.sorted() for attribute, pavs in grouped_pavs
            })
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
            "auto_assign_ribbons": auto_assign_ribbons,
            "show_on_sale_filter": show_on_sale_filter,
            "show_in_stock_filter": show_in_stock_filter,
            "on_sale_active": on_sale_active,
            "in_stock_active": in_stock_active,
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
        values["structured_data"] = products.with_context(
            shop_category_id=category.id if category else False
        )._render_jsonld()

        if website.google_analytics_key:
            if category:
                item_list_name = category.with_context(lang=False).name
            elif fuzzy_search_term or search:
                item_list_name = "Search Results"
            else:
                item_list_name = "Shop"
            # Not translated as they could be used as GA4 aggregation key
            values["product_tracking_infos"] = products._get_google_analytics_list_data_batch(
                products_prices, website, item_list_name
            )

        values.update(self._get_additional_shop_values(values, **post))

        values["default_expand_filter_sections"] = nb_filter_sections < MAX_EXPANDED_FILTER_SECTIONS

        return request.render("website_sale.products", values)

    @route(["/shop/reload"], type="jsonrpc", auth="public", website=True)
    def shop_reload(self, *args, **kwargs):
        response = self.shop(*args, **kwargs)
        html_content = response.render()
        product_count = response.qcontext.get("search_count", 0)

        return {"product_count": product_count, "html": str(html_content)}

    def _apply_pricelist(self, pricelist=None):
        """Change the pricelist of the request and recomputes the current cart prices.

        :param 'product.pricelist'|None pricelist: The new pricelist. If None resets the pricelist.
        """
        if pricelist is None:  # Reset the pricelist
            request.session.pop(PRICELIST_SESSION_CACHE_KEY, None)
            request.session.pop(PRICELIST_SELECTED_SESSION_CACHE_KEY, None)
            request.pricelist = lazy(self.env.website._get_and_cache_current_pricelist)

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
            self.env.website.is_pricelist_available(pricelist_id)
            and (pricelist := self.env["product.pricelist"].browse(pricelist_id))
            and (
                pricelist.selectable
                or pricelist == self.env.user.partner_id.property_product_pricelist
            )
        ):
            self._apply_pricelist(pricelist=pricelist)
            return True
        return False

    @route(
        '/shop/change_pricelist/<model("product.pricelist"):pricelist>',
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def pricelist_change(self, pricelist, **_post):
        website = self.env.website
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
                            min_price, pricelist.currency_id, website.company_id, round=False
                        )
                    )
                except (ValueError, TypeError):
                    pass
                try:
                    max_price = float(max_price)
                    args["max_price"] = max_price and str(
                        prev_pricelist.currency_id._convert(
                            max_price, pricelist.currency_id, website.company_id, round=False
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
            if not (pricelist_sudo and self.env.website.is_pricelist_available(pricelist_sudo.id)):
                return request.redirect("%s?code_not_available=1" % redirect)

            self._apply_pricelist(pricelist=pricelist_sudo)
        else:
            # Reset the pricelist if empty promo code is given
            self._apply_pricelist(pricelist=None)

        return request.redirect(redirect)

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

    @staticmethod
    def _populate_currency_and_pricelist(kwargs):
        kwargs.update({
            "currency_id": request.env.website.currency_id.id,
            "pricelist_id": request.pricelist.id,
        })
