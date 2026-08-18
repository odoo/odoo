# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime
from urllib.parse import urlsplit

from werkzeug.exceptions import NotFound

from odoo import fields
from odoo.fields import Domain
from odoo.http import request, route
from odoo.models import BaseModel
from odoo.tools import SQL, float_round, lazy
from odoo.tools.translate import LazyTranslate

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_sale.const import MAX_EXPANDED_FILTER_SECTIONS, SHOP_PATH

_lt = LazyTranslate(__name__)

DEFAULT_PRODUCTS_PER_PAGE = 21
DEFAULT_PRODUCTS_PER_ROW = 4
DEFAULT_GRID_GAP = "16px"
PRICELIST_CACHE_LIFETIME = 60 * 60  # seconds


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

        return self._to_html_rows()

    def _to_html_rows(self):
        """Format the grid for the template: one list per row, holding the data of the products
        starting in it (empty cells and cells covered by a bigger product are skipped)."""
        return [
            [cell for _x, cell in sorted(row.items()) if cell]
            for _y, row in sorted(self.table.items())
        ]


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


def _parse_price(price):
    """Parse a price query param, defaulting to 0 when it's not a valid float."""
    try:
        return float(price)
    except ValueError:
        return 0


def _clamp_price_range(min_price, max_price, available_min_price, available_max_price):
    """Fall back to the available bounds when the requested ones are out of range.

    This happens when switching to a list of products whose available prices differ from the
    previous page's. Rather than yielding an empty product list, a min exceeding the available
    max is reset to the available min, and a max below the available min is reset to the
    available max. Unset (falsy) boundaries are left untouched.
    """
    if min_price and min_price > available_max_price:
        min_price = available_min_price
    if max_price and max_price < available_min_price:
        max_price = available_max_price
    return min_price, max_price


# ------------------------------------------------------------------------------
# Shop page data
# ------------------------------------------------------------------------------
@dataclass(frozen=True)
class ShopSearch:
    """The products matched by the shop's search, before pagination."""

    category: BaseModel  # product.public.category
    search: str
    fuzzy_search_term: str | None
    products: BaseModel  # product.template
    product_count: int

    @property
    def search_term(self):
        return self.fuzzy_search_term or self.search

    def template_values(self):
        return {
            "search": self.search_term,
            "original_search": self.fuzzy_search_term and self.search,
            "search_product": self.products,
            "search_count": self.product_count,  # common for all searchbox
        }


@dataclass(frozen=True)
class ShopAttributeFilter:
    """The attribute values selected in the shop's filters."""

    params: dict  # As in the query string, e.g. {"1": "2,3"}
    value_dict: dict  # Selected value ids by attribute id, e.g. {1: [2, 3]}
    value_ids: set
    grouped_values: dict  # product.attribute -> product.attribute.value

    def template_values(self):
        return {
            "attrib_values": self.value_dict,
            "attrib_set": self.value_ids,
            "grouped_attributes_values": self.grouped_values,
        }


@dataclass(frozen=True)
class ShopTagFilter:
    enabled: bool
    query_value: str | None = None  # The raw value to keep in the URL's query string
    tag_ids: set = field(default_factory=set)

    @property
    def domain_tag_ids(self):
        return self.tag_ids if self.enabled else None


@dataclass(frozen=True)
class ShopPriceContext:
    """The requested price boundaries, and what's needed to convert them."""

    enabled: bool
    conversion_rate: float
    tax_display: str
    sale_tax: BaseModel  # account.tax
    currency: BaseModel  # res.currency
    min_price: float
    max_price: float

    @property
    def is_requested(self):
        return bool(self.min_price or self.max_price)

    @property
    def min_price_tax_excluded(self):
        return self.to_tax_excluded(self.min_price)

    @property
    def max_price_tax_excluded(self):
        return self.to_tax_excluded(self.max_price)

    def to_tax_excluded(self, price):
        """Convert a displayed price to the tax-excluded amount stored on `list_price`."""
        if not self._displays_tax_included_prices:
            return price
        taxes = self.sale_tax.with_context(force_price_include=True).compute_all(
            price, self.currency
        )
        return taxes["total_excluded"]

    def to_tax_included(self, price):
        """Convert a `list_price` amount to the price displayed on the website."""
        if not self._displays_tax_included_prices:
            return price
        taxes = self.sale_tax.with_context(force_price_include=False).compute_all(
            price, self.currency
        )
        return taxes["total_included"]

    @property
    def _displays_tax_included_prices(self):
        return self.tax_display == "tax_included" and bool(self.sale_tax)


@dataclass(frozen=True)
class ShopPriceRange:
    """The price filter's boundaries, resolved against the prices actually available.

    The default instance stands for a disabled price filter.
    """

    enabled: bool = False
    min_price: float = 0.0
    max_price: float = 0.0
    available_min_price: float = 0.0
    available_max_price: float = 0.0
    query_params: dict = field(default_factory=dict)  # The boundaries to keep in the pager
    domain: Domain | None = None  # Only set when boundaries were requested

    @property
    def has_filter_section(self):
        return self.enabled and self.available_min_price != self.available_max_price

    def template_values(self):
        if not self.enabled:
            return {}
        return {
            "min_price": self.min_price or self.available_min_price,
            "max_price": self.max_price or self.available_max_price,
            "available_min_price": float_round(self.available_min_price, 2),
            "available_max_price": float_round(self.available_max_price, 2),
        }


@dataclass(frozen=True)
class ShopRibbonFilter:
    """The "On sale" / "In stock" filters, based on the automatically assigned ribbons."""

    auto_assign_ribbons: BaseModel  # product.ribbon
    on_sale_active: bool
    in_stock_active: bool
    has_sale_ribbon: bool
    has_out_of_stock_ribbon: bool
    on_sale_ids: frozenset = frozenset()
    sold_out_ids: frozenset = frozenset()

    @property
    def _filters_on_sale(self):
        return self.on_sale_active and self.has_sale_ribbon

    @property
    def _filters_in_stock(self):
        return self.in_stock_active and self.has_out_of_stock_ribbon

    def apply(self, shop_search):
        """Return `shop_search` restricted to the products matching the active filters."""
        if not (self.on_sale_active or self.in_stock_active):
            return shop_search
        products = shop_search.products
        if self._filters_on_sale:
            products = products.filtered(lambda p: p.id in self.on_sale_ids)
        if self._filters_in_stock:
            products = products.filtered(lambda p: p.id not in self.sold_out_ids)
        return replace(shop_search, products=products, product_count=len(products))

    def template_values(self):
        return {
            "auto_assign_ribbons": self.auto_assign_ribbons,
            "on_sale_active": self.on_sale_active,
            "in_stock_active": self.in_stock_active,
            "show_on_sale_filter": bool(self.on_sale_ids) or self._filters_on_sale,
            "show_in_stock_filter": bool(self.sold_out_ids) or self._filters_in_stock,
        }


@dataclass(frozen=True)
class ShopFilters:
    attributes: ShopAttributeFilter
    tags: ShopTagFilter
    price: ShopPriceRange
    ribbons: ShopRibbonFilter


@dataclass(frozen=True)
class ShopPage:
    """The products displayed on the current page, and how to lay them out."""

    pager: dict
    products: BaseModel  # product.template
    product_variants: dict  # product.template -> product.product
    ppg: int
    ppr: int
    gap: str

    def template_values(self):
        return {
            "pager": self.pager,
            "products": self.products,
            "product_variants": self.product_variants,
            "bins": TableCompute().process(self.products, self.ppg, self.ppr),
            "ppg": self.ppg,
            "ppr": self.ppr,
            "gap": self.gap,
        }


class Shop(payment_portal.PaymentPortal):
    # --------------------------------------------------------------------------
    # Category
    # --------------------------------------------------------------------------
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

    def _get_shop_category_redirect(self, category, page):
        """Return a 301 redirect if the current URL doesn't match `category`'s canonical URL
        (e.g. the category was given as a query parameter, or without its parents in the path).

        :param product.public.category category: The category being browsed.
        :param int page: The current page number.
        :return: The redirect response, or None if the current URL is already canonical.
        :rtype: werkzeug.wrappers.Response|None
        """
        path = category.website_url + (f"/page/{page}" if page else "")
        if path != request.httprequest.path:
            url = urlsplit(request.httprequest.url)
            return request.redirect(url._replace(path=path).geturl(), code=301)
        return None

    @staticmethod
    def _get_displayable_subcategories(website, parent, search, search_categories):
        children = parent.child_id.filtered(lambda c: c.website_id.id in (website.id, False))
        if search:
            return children.filtered(lambda c: c.id in search_categories.ids)
        return children

    def _get_category_entries(self, website, category, search, search_categories):
        """Return the subcategories of `category` to display, falling back to its siblings."""
        entries = self._get_displayable_subcategories(
            website, category, search, search_categories
        ) or self._get_displayable_subcategories(
            website, category.parent_id, search, search_categories
        )
        if not search and not self.env.user._is_internal():
            # We know the user has access to the sidebar categories and `search_categories`
            # because they come from a regular `search`, but we have not checked access to
            # `category`'s children, nor its siblings or itself.
            entries = entries.filtered("has_published_products")
        return entries

    def _get_shop_categories(self, website, category, search, shop_query):
        """Compute the sidebar category list, and the "children" entries to display for the
        current category (or the top-level categories if none is selected).

        :param website website: The current website.
        :param product.public.category category: The category being browsed, if any.
        :param str search: The search term, if any.
        :param odoo.osv.query.Query shop_query: The query matching the current search's products.
        :return: The sidebar categories, the category entries to display, and the categories
            matched by the current search (ancestors included).
        :rtype: tuple(product.public.category, product.public.category, product.public.category)
        """
        Category = self.env["product.public.category"]
        categs_domain = (
            Domain("parent_id", "=", False)
            & Domain("not_in_shop", "=", False)
            & website.website_domain()
        )
        search_categories = Category
        if search:
            # Using a sub-query is more efficient than using a query in the shape of "ids in
            # (...)" when there are 100k product ids to match.
            search_categories = Category.search(
                Domain("product_tmpl_ids", "in", shop_query)
            ).parents_and_self
            categs_domain &= Domain("id", "in", search_categories.ids)
        categs = Category.search_fetch(categs_domain)

        if not category:
            return categs, categs, search_categories
        category_entries = self._get_category_entries(website, category, search, search_categories)
        return categs, category_entries, search_categories

    # --------------------------------------------------------------------------
    # Attribute Filter
    # --------------------------------------------------------------------------
    @staticmethod
    def _get_legacy_attribute_value_params():
        """Parse the legacy `attribute_values` query param list into the current dict format.

        Before: ["1-2,3", "4-5,6"]
        After: {"1": "2,3", "4": "5,6"}
        """
        # TODO: remove support for `attribute_values` query param in version 20 (or later).
        attribute_values = request.httprequest.args.getlist("attribute_values")
        return dict(pair.split("-") for pair in attribute_values if pair and pair.count("-") == 1)

    def _resolve_attribute_value_filter(self, post):
        """Resolve the attribute value filter from the request's query params.

        :param dict post: The request's query params.
        :rtype: ShopAttributeFilter
        """
        params = self._get_attribute_value_params(post) or self._get_legacy_attribute_value_params()
        value_dict = self._get_attribute_value_dict(params)
        value_ids = set(itertools.chain.from_iterable(value_dict.values()))
        grouped_values = (
            self
            .env["product.attribute.value"]
            .browse(value_ids)
            .exists()
            .sorted()
            .grouped("attribute_id")
        )
        return ShopAttributeFilter(params, value_dict, value_ids, grouped_values)

    @staticmethod
    def _store_attribute_value_params(params):
        """Keep the attribute filter in the session, for the filter and reset links."""
        if params:
            request.session["attribute_value_params"] = params
        else:
            request.session.pop("attribute_value_params", None)

    def _get_shop_filter_attributes(self, filters_query):
        """Compute the "visible" attributes and their values available among the products
        matched by `filters_query`, for the attribute filter sidebar.

        :param odoo.osv.query.Query filters_query: The query matching the products to consider.
        :return: The attributes to display, and their values grouped by attribute.
        :rtype: tuple(product.attribute, dict(product.attribute, product.attribute.value))
        """
        ProductAttribute = self.env["product.attribute"]
        ProductAttributeValue = self.env["product.attribute.value"]
        pavs_per_attribute = defaultdict(lambda: ProductAttributeValue)

        grouped_pavs = ProductAttributeValue._read_group(
            domain=[
                ("pav_attribute_line_ids.product_tmpl_id", "in", filters_query),
                ("attribute_id.visibility", "=", "visible"),
            ],
            groupby=["attribute_id"],
            order="attribute_id",
            aggregates=["id:recordset"],
        )
        pavs_per_attribute.update({attribute: pavs.sorted() for attribute, pavs in grouped_pavs})
        # Return attributes as recordset of `product.attribute`.
        attributes = ProductAttribute.union(pavs_per_attribute.keys())
        return attributes, pavs_per_attribute

    # --------------------------------------------------------------------------
    # Redirects
    # --------------------------------------------------------------------------
    def _get_shop_redirect(self, category, page, attribute_filter):
        """Return a 301 redirect to the canonical shop URL, or None if the current one is."""
        if category and (redirect := self._get_shop_category_redirect(category, page)):
            return redirect
        # TODO: remove support for `attribute_values` query param in version 20 (or later).
        if request.httprequest.args.getlist("attribute_values"):
            redirect_url = self._get_url_with_attribute_values(attribute_filter.grouped_values)
            return request.redirect(redirect_url, code=301)
        return None

    # --------------------------------------------------------------------------
    # Price Filter
    # --------------------------------------------------------------------------
    @staticmethod
    def _parse_price_range(min_price, max_price):
        """Parse the min/max price query params, defaulting to 0 when they're not valid floats."""
        return _parse_price(min_price), _parse_price(max_price)

    def _refresh_pricelist_cache(self):
        """Invalidate the website's cached pricelist once an hour, so it gets recomputed."""
        now = datetime.timestamp(datetime.now())
        pricelist_save_time = request.session.get("website_sale_pricelist_time")
        if pricelist_save_time is not None and pricelist_save_time < now - PRICELIST_CACHE_LIFETIME:
            self.env.website.sudo().pricelist_id = False
            # restart the counter
            request.session["website_sale_pricelist_time"] = now

    def _get_shop_conversion_rate(self, website):
        company_currency = website.company_id.sudo().currency_id
        return self.env["res.currency"]._get_conversion_rate(
            company_currency, website.currency_id, website.company_id, fields.Date.today()
        )

    def _get_shop_price_filter_context(self, website, min_price, max_price):
        """Resolve everything needed to filter products by price.

        :param website website: The current website.
        :param float min_price: The requested lower price boundary.
        :param float max_price: The requested upper price boundary.
        :rtype: ShopPriceContext
        """
        enabled = website.is_view_active("website_sale.filter_products_price")
        return ShopPriceContext(
            enabled=enabled,
            conversion_rate=self._get_shop_conversion_rate(website) if enabled else 1,
            tax_display=website.tax_display,
            sale_tax=request.fiscal_position.map_tax(website.company_id.sudo().account_sale_tax_id),
            currency=website.currency_id,
            min_price=min_price,
            max_price=max_price,
        )

    def _get_shop_available_price_range(self, shop_query, price_context):
        """Return the (min, max) list price bounds, as displayed on the website, among the
        products matched by `shop_query`.

        :param odoo.osv.query.Query shop_query: The query matching the products to consider.
        :param ShopPriceContext price_context: The conversion rate and taxes to apply.
        :rtype: tuple(float, float)
        """
        # TODO Find an alternative way to obtain the domain through the search metadata.
        # This is ~4 times more efficient than a search for the cheapest and most expensive
        # products.
        sql = shop_query.select(
            SQL(
                "COALESCE(MIN(list_price), 0) * %(conversion_rate)s, COALESCE(MAX(list_price), 0) * %(conversion_rate)s",  # noqa: E501
                conversion_rate=price_context.conversion_rate,
            )
        )
        available_min_price, available_max_price = self.env.execute_query(sql)[0]
        return (
            price_context.to_tax_included(available_min_price),
            price_context.to_tax_included(available_max_price),
        )

    def _get_shop_price_range(self, shop_query, price_context):
        """Resolve the price filter's boundaries against the prices available among the products
        matched by `shop_query`.

        :param odoo.osv.query.Query shop_query: The query matching the products to consider.
        :param ShopPriceContext price_context: The requested boundaries.
        :rtype: ShopPriceRange
        """
        if not price_context.enabled:
            return ShopPriceRange()

        available_min_price, available_max_price = self._get_shop_available_price_range(
            shop_query, price_context
        )
        min_price, max_price = _clamp_price_range(
            price_context.min_price,
            price_context.max_price,
            available_min_price,
            available_max_price,
        )
        query_params = {}
        if price_context.min_price:
            query_params["min_price"] = min_price
        if price_context.max_price:
            query_params["max_price"] = max_price

        domain = None
        if price_context.is_requested:
            rate = price_context.conversion_rate
            domain = Domain.AND([
                Domain("list_price", ">=", (min_price or available_min_price) / rate),
                Domain("list_price", "<=", (max_price or available_max_price) / rate),
            ])

        return ShopPriceRange(
            enabled=True,
            min_price=min_price,
            max_price=max_price,
            available_min_price=available_min_price,
            available_max_price=available_max_price,
            query_params=query_params,
            domain=domain,
        )

    @staticmethod
    def _populate_currency_and_pricelist(kwargs):
        kwargs.update({
            "currency_id": request.env.website.currency_id.id,
            "pricelist_id": request.pricelist.id,
        })

    # --------------------------------------------------------------------------
    # Tag Filter
    # --------------------------------------------------------------------------
    def _get_shop_tags_filter(self, website, tags):
        """Resolve the "tags" filter.

        :param website website: The current website.
        :param str tags: The comma-separated, slugified tag ids, as received from the request.
        :rtype: ShopTagFilter
        """
        if not website.is_view_active("website_sale.filter_products_tags"):
            return ShopTagFilter(enabled=False)
        if not tags:
            return ShopTagFilter(enabled=True)
        unslug = self.env["ir.http"]._unslug
        tag_ids = {tag_id for tag in tags.split(",") if (tag_id := unslug(tag)[1])}
        return ShopTagFilter(enabled=True, query_value=tags, tag_ids=tag_ids)

    def _get_shop_available_tags(self, website, filters_query):
        """Return the tags available among the products matched by `filters_query`.

        :param website website: The current website.
        :param odoo.osv.query.Query filters_query: The query matching the products to consider.
        :rtype: product.tag
        """
        return self.env["product.tag"].search_fetch(
            Domain.AND([
                Domain("visible_to_customers", "=", True),
                Domain.OR([
                    Domain("product_template_ids", "in", filters_query),
                    Domain("product_product_ids.product_tmpl_id", "in", filters_query),
                ]),
                website.website_domain(),
            ])
        )

    def _get_shop_tag_values(self, website, tag_filter, filters_query):
        if not tag_filter.enabled:
            return {}
        return {
            "all_tags": self._get_shop_available_tags(website, filters_query),
            "tags": tag_filter.tag_ids,
        }

    # --------------------------------------------------------------------------
    # Filter Links & Reset
    # --------------------------------------------------------------------------
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

    def _get_shop_filter_reset_params(self):
        """Query-string params that clear the filters, for the `keep()` reset links.

        Returns the attribute-only reset (used by the attribute filter form) and the
        full reset extending it with the tag, price and ribbon filters.
        """
        reset_attribute_value_params = {
            attr: 0 for attr in request.session.get("attribute_value_params", {})
        }
        reset_filters = {
            **reset_attribute_value_params,
            "tags": 0,
            "min_price": 0,
            "max_price": 0,
            "on_sale": 0,
            "in_stock": 0,
        }
        return reset_attribute_value_params, reset_filters

    # --------------------------------------------------------------------------
    # Search & Domain
    # --------------------------------------------------------------------------
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
            product_template = request.env["product.template"]
            search_fields = product_template._get_website_sale_search_fields(search_in_description)
            for srch in search.split(" "):
                subdomains = [
                    product_template._search_get_field_domain(field, srch)
                    for field in search_fields
                ]
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
        search_result = details[0].get("results", self.env["product.template"])

        return fuzzy_search_term, product_count, search_result

    @staticmethod
    def _get_shop_visible_categories_domain():
        """Products without category, or in at least one category shown in the shop."""
        return Domain.OR([
            Domain("public_categ_ids", "=", False),
            Domain("public_categ_ids.not_in_shop", "=", False),
        ])

    def _search_shop_products(
        self, website, category, search, attribute_filter, price_context, post
    ):
        """Search the products matching the current category, search term and filters.

        :rtype: ShopSearch
        """
        options = self._get_search_options(
            category=category,
            attribute_value_dict=attribute_filter.value_dict,
            min_price=price_context.min_price_tax_excluded,
            max_price=price_context.max_price_tax_excluded,
            conversion_rate=price_context.conversion_rate,
            display_currency=website.currency_id,
            extra_domain=(
                None if (category or search) else self._get_shop_visible_categories_domain()
            ),
            **post,
        )
        fuzzy_search_term, product_count, products = self._shop_lookup_products(
            options, post, search, website
        )
        return ShopSearch(category, search, fuzzy_search_term, products, product_count)

    def _get_shop_query(self, shop_search, attribute_filter, tag_filter):
        """Query matching the products of the current search, all filters but price included."""
        domain = self._get_shop_domain(
            shop_search.search_term,
            shop_search.category,
            attribute_filter.value_dict,
            tags=tag_filter.domain_tag_ids,
        )
        return request.env["product.template"]._search(domain)

    def _get_shop_filters_query(self, shop_search, price_range):
        """Query matching the products to consider for the filters sidebar: the ones of the
        current search, ignoring the attribute and tag filters but not the price one."""
        domain = self._get_shop_domain(
            shop_search.search_term, shop_search.category, attribute_value_dict={}
        )
        if price_range.domain is not None:
            domain = Domain.AND([domain, price_range.domain])
        return request.env["product.template"]._search(domain)

    # --------------------------------------------------------------------------
    # Ribbon Filters
    # --------------------------------------------------------------------------
    def _get_products_sales_prices(self, website, products):
        return products._get_sales_prices(
            # Make sure latest context is applied (see update_context calls in overrides)
            request.pricelist.with_context(self.env.context),
            request.fiscal_position.with_context(self.env.context),
            website.with_context(self.env.context),
        )

    def _get_on_sale_product_ids(self, website, products):
        sales_prices = self._get_products_sales_prices(website, products)
        return frozenset(pid for pid, prices in sales_prices.items() if "base_price" in prices)

    def _get_shop_ribbon_filter(self, website, products, on_sale, in_stock):
        """Resolve the "On sale" / "In stock" ribbon filters for `products`.

        :param website website: The current website.
        :param product.template products: The products matched by the current search.
        :param str on_sale: Whether the "On sale" filter is active ('1' or falsy).
        :param str in_stock: Whether the "In stock" filter is active ('1' or falsy).
        :rtype: ShopRibbonFilter
        """
        auto_assign_ribbons = self.env["product.ribbon"].sudo().search([("assign", "!=", "manual")])
        assign_values = set(auto_assign_ribbons.mapped("assign"))
        has_sale_ribbon = "sale" in assign_values
        has_out_of_stock_ribbon = "out_of_stock" in assign_values
        return ShopRibbonFilter(
            auto_assign_ribbons=auto_assign_ribbons,
            on_sale_active=on_sale == "1",
            in_stock_active=in_stock == "1",
            has_sale_ribbon=has_sale_ribbon,
            has_out_of_stock_ribbon=has_out_of_stock_ribbon,
            on_sale_ids=(
                self._get_on_sale_product_ids(website, products) if has_sale_ribbon else frozenset()
            ),
            sold_out_ids=(
                frozenset(p.id for p in products if p._is_sold_out())
                if has_out_of_stock_ribbon
                else frozenset()
            ),
        )

    # --------------------------------------------------------------------------
    # Pagination
    # --------------------------------------------------------------------------
    def _get_default_variants(self, products):
        """Map each product template to its first possible variant, prefetching the variants."""
        Product = self.env["product.product"]
        variant_ids = [product._get_first_possible_variant_id() for product in products]
        variants = Product.sudo().browse(vid for vid in variant_ids if vid)
        variants.fetch()
        variant_by_id = {v.id: v for v in variants}
        return {
            product: variant_by_id.get(vid, Product)
            for product, vid in zip(products, variant_ids, strict=True)
        }

    def _get_shop_page(self, website, url, shop_search, page, post):
        """Paginate the search results, and resolve the default variant of the page's products.

        :param website website: The current website.
        :param str url: The base URL to use for the pager's links.
        :param ShopSearch shop_search: The products matched by the current search.
        :param int page: The current page number.
        :param dict post: The query string params to keep in the pager's links.
        :rtype: ShopPage
        """
        ppg = website.shop_ppg or DEFAULT_PRODUCTS_PER_PAGE
        pager = website.pager(
            url=url, total=shop_search.product_count, page=page, step=ppg, scope=5, url_args=post
        )
        offset = pager["offset"]
        products = shop_search.products[offset : offset + ppg].with_prefetch()
        products.fetch()
        return ShopPage(
            pager=pager,
            products=products,
            product_variants=self._get_default_variants(products),
            ppg=ppg,
            ppr=website.shop_ppr or DEFAULT_PRODUCTS_PER_ROW,
            gap=website.shop_gap or DEFAULT_GRID_GAP,
        )

    # --------------------------------------------------------------------------
    # Analytics
    # --------------------------------------------------------------------------
    @staticmethod
    def _get_shop_product_tracking_infos(website, shop_search, products, products_prices):
        """Build the per-product Google Analytics (GA4) tracking payload for the current page."""
        if shop_search.category:
            item_list_name = shop_search.category.with_context(lang=False).name
        elif shop_search.search_term:
            item_list_name = "Search Results"
        else:
            item_list_name = "Shop"
        # Not translated as they could be used as GA4 aggregation key.
        return products._get_google_analytics_list_data_batch(
            products_prices, website, item_list_name
        )

    # --------------------------------------------------------------------------
    # Extension Hooks
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # Template Values
    # --------------------------------------------------------------------------
    def _get_shop_category_values(self, website, shop_search, shop_query):
        category = shop_search.category
        categs, category_entries, search_categories = self._get_shop_categories(
            website, category, shop_search.search, shop_query
        )
        values = {
            "category": category,
            "categories": categs,
            "category_entries": category_entries,
            "search_categories_ids": search_categories.ids,
        }
        if category:
            values["main_object"] = category
        return values

    def _get_shop_filter_values(self, website, filters, filters_query):
        attributes, pavs_per_attribute = self._get_shop_filter_attributes(filters_query)
        tag_values = self._get_shop_tag_values(website, filters.tags, filters_query)
        reset_attribute_value_params, reset_filters = self._get_shop_filter_reset_params()
        nb_filter_sections = (
            len(attributes)
            + int(filters.price.has_filter_section)
            + int(bool(tag_values.get("all_tags")))
        )
        return {
            **filters.attributes.template_values(),
            **filters.price.template_values(),
            **filters.ribbons.template_values(),
            **tag_values,
            "attributes": attributes,
            "pavs_per_attribute": pavs_per_attribute,
            "reset_attribute_value_params": reset_attribute_value_params,
            "reset_filters": reset_filters,
            "default_expand_filter_sections": nb_filter_sections < MAX_EXPANDED_FILTER_SECTIONS,
        }

    def _get_shop_product_values(self, website, shop_search, products, post):
        products_prices = self._get_products_sales_prices(website, products)
        product_query_params = self._get_product_query_params(**post)
        category = shop_search.category
        values = {
            "get_product_prices": lambda product: products_prices[product.id],
            "product_query_params": product_query_params,
            "previewed_attribute_values": lazy(
                lambda: products._get_previewed_attribute_values(product_query_params)
            ),
            "structured_data": products.with_context(
                shop_category_id=category.id if category else False
            )._render_jsonld(),
        }
        if website.google_analytics_key:
            values["product_tracking_infos"] = self._get_shop_product_tracking_infos(
                website, shop_search, products, products_prices
            )
        return values

    # --------------------------------------------------------------------------
    # Routes
    # --------------------------------------------------------------------------
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
        website = self.env.website
        is_reload = request.httprequest.path == "/shop/reload"
        if not is_reload and not website.has_ecommerce_access():
            return request.redirect(f"/web/login?redirect={request.httprequest.path}")

        post = {k: v for k, v in post.items() if not k.startswith("_")}
        # TODO: remove support for `category` query param in version 20 (or later).
        category = self._validate_and_get_category(category)
        attribute_filter = self._resolve_attribute_value_filter(post)
        redirect = None if is_reload else self._get_shop_redirect(category, page, attribute_filter)
        if redirect:
            return redirect
        self._store_attribute_value_params(attribute_filter.params)

        min_price, max_price = self._parse_price_range(min_price, max_price)
        tag_filter = self._get_shop_tags_filter(website, tags)
        if tag_filter.enabled:
            post["tags"] = tag_filter.query_value
        # `keep` must be built before `post` receives the search and price params, as
        # `_shop_get_query_url_kwargs` takes them as explicit arguments.
        url = category.website_url if category else SHOP_PATH
        keep = QueryURL(
            url,
            **self._shop_get_query_url_kwargs(
                search, min_price, max_price, on_sale=on_sale, in_stock=in_stock, **post
            ),
        )
        if search:
            post["search"] = search
        self._refresh_pricelist_cache()

        price_context = self._get_shop_price_filter_context(website, min_price, max_price)
        shop_search = self._search_shop_products(
            website, category, search, attribute_filter, price_context, post
        )
        shop_query = self._get_shop_query(shop_search, attribute_filter, tag_filter)
        price_range = self._get_shop_price_range(shop_query, price_context)
        post.update(price_range.query_params)
        filters_query = self._get_shop_filters_query(shop_search, price_range)
        ribbon_filter = self._get_shop_ribbon_filter(
            website, shop_search.products, on_sale, in_stock
        )
        shop_search = ribbon_filter.apply(shop_search)

        shop_page = self._get_shop_page(website, url, shop_search, page, post)
        filters = ShopFilters(attribute_filter, tag_filter, price_range, ribbon_filter)
        values = {
            **shop_search.template_values(),
            **shop_page.template_values(),
            **self._get_shop_category_values(website, shop_search, shop_query),
            **self._get_shop_filter_values(website, filters, filters_query),
            **self._get_shop_product_values(website, shop_search, shop_page.products, post),
            "order": post.get("order", ""),
            "keep": keep,
            "float_round": float_round,
            "shop_path": SHOP_PATH,
        }
        values.update(self._get_additional_shop_values(values, **post))
        return request.render("website_sale.products", values)

    @route(["/shop/reload"], type="jsonrpc", auth="public", website=True)
    def shop_reload(self, *args, **kwargs):
        response = self.shop(*args, **kwargs)
        html_content = response.render()
        product_count = response.qcontext.get("search_count", 0)

        return {"product_count": product_count, "html": str(html_content)}

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
