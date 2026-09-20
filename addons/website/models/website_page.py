import logging
import re
import time
from collections import Counter
from pathlib import PurePosixPath

from odoo import api, fields, http, models, tools
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, escape_psql

from odoo.addons.base.models.ir_http import EXTENSION_TO_WEB_MIMETYPES
from odoo.addons.website.tools import text_from_html

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class PageCannotBeCached(Exception):
    """Raised with the response that was rendered but must not be cached.

    `rendered_response` is what the caller returns; it is None when the page
    produced no response at all.
    """

    def __init__(self, rendered_response):
        super().__init__(rendered_response)
        self.rendered_response = rendered_response


class WebsitePage(models.Model):
    _name = "website.page"
    _inherits = {"ir.ui.view": "view_id"}
    _inherit = [
        "mixin.website.published.multi",
        "mixin.website.searchable",
        "mixin.website.page_options",
    ]
    _description = "Page"
    _order = "website_id"

    _CACHE_DURATION = 3600

    _NON_RENDERING_FIELDS = frozenset({"view_write_uid", "view_write_date"})

    url = fields.Char(
        string="Page URL",
        required=True,
    )
    view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        index=True,
        required=True,
        ondelete="cascade",
    )

    view_write_uid = fields.Many2one(
        comodel_name="res.users",
        related="view_id.write_uid",
        string="Last Content Update by",
    )
    view_write_date = fields.Datetime(
        related="view_id.write_date",
        string="Last Content Update on",
    )

    website_indexed = fields.Boolean(
        string="Is Indexed",
        default=True,
    )
    date_publish = fields.Datetime(string="Publishing Date")
    menu_ids = fields.One2many(
        comodel_name="website.menu",
        inverse_name="page_id",
        string="Related Menus",
    )
    is_in_menu = fields.Boolean(compute="_compute_is_in_menu")
    is_homepage = fields.Boolean(
        string="Homepage",
        compute="_compute_is_homepage",
    )
    is_visible = fields.Boolean(compute="_compute_is_visible")
    is_new_page_template = fields.Boolean(
        string="New Page Template",
        help='Add this page to the "+New" page templates. It will be added to the "Custom" category.',
    )

    website_id = fields.Many2one(  # noqa: E8529  page serving filters and orders on it; TestWebsitePerformance's query pins rise through ir_ui_view
        related="view_id.website_id",
        store=True,
        readonly=False,
        ondelete="cascade",
    )
    arch = fields.Text(
        related="view_id.arch",
        depends_context=("website_id",),
        readonly=False,
    )

    @api.depends("url", "website_id")
    @api.depends_context("website_id")
    def _compute_is_homepage(self):
        website = self.env["website"].get_current_website()
        for page in self:
            page.is_homepage = page.url == (
                website.homepage_url or (page.website_id == website and "/")
            )

    @api.depends("website_published", "date_publish")
    @api.depends_context("website_id")
    def _compute_is_visible(self):
        now = fields.Datetime.now()
        for page in self:
            page.is_visible = page.website_published and (
                not page.date_publish or page.date_publish <= now
            )

    @api.depends("menu_ids")
    def _compute_is_in_menu(self):
        for page in self:
            page.is_in_menu = bool(page.menu_ids)

    @api.depends("url")
    def _compute_website_url(self):
        for page in self:
            page.website_url = page.url

    @api.depends_context("uid")
    def _compute_can_publish(self):
        if self.env.user.has_group("website.group_website_designer"):
            for record in self:
                record.can_publish = True
        else:
            super()._compute_can_publish()

    _MOST_SPECIFIC_COLUMNS = ("url", "website_id", "key")

    def _get_most_specific_pages(self):
        if not self:
            return self
        # Three columns, read once, as rows. Reading `url`, `website_id` and the
        # `_inherits`-related `key` through the ORM descriptor once per record
        # is what this method cost: profiled behind the editor's link picker it
        # was 1.05 s of 1.13 s over 2,624 pages, and it also sits behind the
        # sitemap and site search.
        rows = (
            self.sudo()
            .with_context(prefetch_fields=False)
            .read(list(self._MOST_SPECIFIC_COLUMNS))
        )
        by_id = {row["id"]: row for row in rows}
        position = {page_id: index for index, page_id in enumerate(self.ids)}

        # Only the keys carried by `self` are ever looked up below, so the count
        # is taken over those keys and not over every page of the website: this
        # runs behind site search, the sitemap and the page list, where the
        # candidate set is a handful of rows and the table is the whole site.
        website_domain = (
            self.env["website"]
            .browse(self.env.context.get("website_id"))
            .website_domain()
        )
        page_keys_counts = Counter(
            self.sudo()
            .with_context(prefetch_fields=False)
            .search_fetch(
                website_domain
                & Domain("key", "in", list({row["key"] for row in rows})),
                field_names=["key"],
            )
            .mapped("key")
        )

        # The url sort exists to put a website-specific page ahead of the generic
        # one it shadows, so that the first row of each url group decides the
        # group. It is a decision order, not an output order: the result is
        # filtered out of `self`, which keeps the caller's `order=`. Returning
        # `browse(ids)` here handed every caller its pages in url order instead
        # -- site search ignored the requested sort, and the link picker's
        # "last modified" list was not sorted by date. The explicit `position`
        # tie-break reproduces the stable sort over `self` that it replaces.
        kept_ids = set()
        previous_url = None
        for row in sorted(
            by_id.values(),
            key=lambda row: (
                row["url"] or "",
                not row["website_id"],
                position[row["id"]],
            ),
        ):
            if previous_url is None or row["url"] != previous_url:
                if row["website_id"] or page_keys_counts[row["key"]] == 1:
                    kept_ids.add(row["id"])
            previous_url = row["url"]
        _debug.perf.count(
            "most_specific_pages",
            website=self.env.context.get("website_id"),
            candidates=len(self),
            kept=len(kept_ids),
        )
        return self.filtered(lambda page: page.id in kept_ids)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if not default:
            return vals_list
        for page, vals in zip(self, vals_list, strict=False):
            if not default.get("view_id"):
                new_view = page.view_id.copy({"website_id": default.get("website_id")})
                vals["view_id"] = new_view.id
                vals["key"] = new_view.key
                _debug.lifecycle(
                    "page_view_copied",
                    page=page.id,
                    view=page.view_id.id,
                    copy=new_view.id,
                )
            vals["url"] = default.get(
                "url", self.env["website"].get_unique_path(page.url)
            )
        return vals_list

    @api.model
    def clone_page(self, page_id, page_name=None, clone_menu=True):
        page = self.browse(int(page_id))
        copy_param = {
            "name": page_name or page.name,
            "website_id": self.env["website"].get_current_website().id,
        }
        if page_name:
            url = "/" + self.env["ir.http"]._slugify(
                page_name, max_length=1024, path=True
            )
            copy_param["url"] = self.env["website"].get_unique_path(url)

        new_page = page.copy(copy_param)
        if clone_menu and new_page.website_id == page.website_id:
            menu = self.env["website.menu"].search([("page_id", "=", page_id)], limit=1)
            if menu:
                menu.copy(
                    {"url": new_page.url, "name": new_page.name, "page_id": new_page.id}
                )

        _debug.lifecycle(
            "page_cloned",
            page=int(page_id),
            clone=new_page.id,
            url=new_page.url,
            clone_menu=clone_menu,
        )
        return new_page.url

    def unlink(self):
        views_to_delete = self.view_id.filtered(
            lambda v: v.page_ids <= self and not v.inherit_children_ids
        )
        self -= views_to_delete.page_ids
        _debug.lifecycle(
            "unlink", pages=self, count=len(self), views=len(views_to_delete)
        )
        views_to_delete.unlink()

        had_pages = bool(self)
        result = super().unlink()
        if had_pages:
            self.env.registry.clear_cache("templates")
        return result

    def write(self, vals):
        _debug.lifecycle("write", pages=self, count=len(self), fields=sorted(vals))
        if "visibility" in vals and vals["visibility"] != "restricted_group":
            _debug.logic(
                "page_groups_cleared",
                reason="visibility",
                visibility=vals["visibility"],
            )
            vals["group_ids"] = False

        if "url" in vals or "name" in vals:
            shared_vals = {k: v for k, v in vals.items() if k != "url"}
            for page in self:
                page_vals = dict(shared_vals)
                website_id = vals.get("website_id") or page.website_id.id or False

                if "url" in vals:
                    url = vals["url"] or ""
                    url = "/" + self.env["ir.http"]._slugify(
                        url, max_length=1024, path=True
                    )
                    if page.url != url:
                        url = (
                            self.env["website"]
                            .with_context(website_id=website_id)
                            .get_unique_path(url)
                        )
                        page.menu_ids.write({"url": url})
                        old_url = page.url
                        old_url_normalized = {"homepage_url": old_url}
                        self.env["website"]._update_vals_homepage_url(
                            old_url_normalized
                        )
                        websites = self.env["website"].search(  # noqa: E8507 - url renames are sequential: each page's unique path and homepage rewrite depend on the previous page's write
                            [("homepage_url", "=", old_url_normalized["homepage_url"])]
                        )
                        if page.website_id:
                            websites &= page.website_id
                        else:
                            websites -= self.search(  # noqa: E8507 - url renames are sequential: each page's unique path and homepage rewrite depend on the previous page's write
                                [("url", "=", old_url), ("website_id", "!=", False)]
                            ).website_id
                        _debug.lifecycle(
                            "page_url_changed",
                            page=page.id,
                            old=old_url,
                            new=url,
                            homepages=len(websites),
                            menus=len(page.menu_ids),
                        )
                        websites.homepage_url = url
                    page_vals["url"] = url

                if "key" not in vals and "name" in vals and page.name != vals["name"]:
                    page_vals["key"] = (
                        self.env["website"]
                        .with_context(website_id=website_id)
                        .get_unique_key(
                            self.env["ir.http"]._slugify(vals["name"] or "")
                        )
                    )
                super(WebsitePage, page).write(page_vals)
            res = True
        else:
            res = super().write(vals)

        if not vals.keys() <= self._NON_RENDERING_FIELDS:
            _debug.lifecycle(
                "templates_cache_cleared",
                by=sorted(vals.keys() - self._NON_RENDERING_FIELDS),
            )
            self.env.registry.clear_cache("templates")

        return res

    def get_website_meta(self):
        self.check_singleton()
        return self.view_id.get_website_meta()

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options["displayDescription"]
        requires_sudo = True
        domain = [website.website_domain()]
        if not self.env.user.has_group("website.group_website_designer"):
            domain.append(
                [
                    ("website_published", "=", True),
                    ("website_indexed", "=", True),
                ]
            )
            domain.append([("visibility", "!=", "password")])
            domain.append(
                Domain("date_publish", "=", False)
                | Domain("date_publish", "<=", fields.Datetime.now())
            )
            if website.is_public_user():
                domain.append([("visibility", "!=", "connected")])
            domain.append(
                Domain.OR(
                    [
                        [("group_ids", "=", False)],
                        [("group_ids", "in", self.env.user.group_ids.ids)],
                    ]
                )
            )

        search_fields = ["name", "url"]
        fetch_fields = ["id", "name", "url"]
        html_fields = set()
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "url", "type": "text", "truncate": False},
        }
        if with_description:
            search_fields.append("arch_db")
            fetch_fields.append("arch")
            # A page searches its stored `arch_db` and renders the related
            # `arch`, so the mapping cannot name the field the enumerators read.
            html_fields.add("arch_db")
            mapping["description"] = {
                "name": "arch",
                "type": "text",
                "html": True,
                # `arch` comes out of a stored XML document, so its entities are
                # escaped once more than an ordinary html field's.
                "escaped_twice": True,
                "match": True,
            }
        return {
            "model": "website.page",
            "base_domain": domain,
            "requires_sudo": requires_sudo,
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "html_fields": html_fields,
            "mapping": mapping,
            "icon": "fa-regular fa-file",
        }

    @api.model
    def _search_fetch(self, search_detail, search, limit, order):
        with_description = "description" in search_detail["mapping"]
        fields = search_detail["search_fields"]
        base_domain = Domain.AND(search_detail["base_domain"])
        domain = self._search_build_domain(
            [base_domain], search, fields, search_detail.get("search_extra")
        )
        # Let SQL do the matching. This used to fetch every page the base domain
        # admits and then `filtered_domain(domain)` in Python, which reads
        # `arch_db` -- the whole stored html of every page on the site -- for a
        # search that matches three of them. Profiled at 2,624 pages, the ORM
        # field reads behind that filter were the entire cost of a public
        # search.
        #
        # Equivalent because the dedup only ever needs the url groups it will
        # answer for: a group with no match contributes nothing either way, and
        # a group with one is expanded in full below before the dedup runs, so
        # the dedup sees exactly the rows it used to see for that url.
        result_order = search_detail.get("order", order)

        # Every candidate is selected in SQL. This used to fetch every page the
        # base domain admits and filter it with `filtered_domain(domain)` in
        # Python -- which reads `arch_db`, the whole stored html of every page
        # on the site, to answer a search matching three of them. Profiled at
        # 2,624 pages, those ORM field reads were the entire cost of a public
        # search.
        candidate_ids = set(self.sudo()._search(domain))
        if with_description and search:
            # The term-split domain above requires every term; this adds the
            # pages carrying the phrase, over the same base domain it always
            # scanned -- in SQL, so widening it costs one query and no records.
            v_arch_db = self.env["ir.ui.view"]._field_to_sql("v", "arch_db")
            rows = self.env.execute_query(
                SQL(
                    """
                SELECT DISTINCT %(table)s.id
                FROM %(table)s
                LEFT JOIN ir_ui_view v ON %(table)s.view_id = v.id
                WHERE (v.name ILIKE %(search)s
                OR %(v_arch_db)s ILIKE %(search)s)
                AND %(table)s.id IN %(base)s
                """,
                    table=SQL.identifier(self._table),
                    search=f"%{escape_psql(search)}%",
                    v_arch_db=v_arch_db,
                    base=self.sudo()._search(base_domain).subselect(),
                )
            )
            candidate_ids.update(row[0] for row in rows)

        # The dedup only ever needs the url groups it will answer for: a group
        # with no candidate contributes nothing, and a group with one is
        # expanded in full here, so the dedup sees exactly the rows it used to.
        candidates = self.sudo().search(
            base_domain & Domain("id", "in", list(candidate_ids)), order=result_order
        )
        most_specific_pages = self.env["website"]._get_website_pages(
            domain=base_domain
            & Domain("url", "in", list({page.url for page in candidates})),
            order=result_order,
        )
        results = most_specific_pages.filtered(lambda page: page.id in candidate_ids)

        # The reader's record rules do not change between two pages, so they are
        # resolved once for the whole candidate set rather than per page.
        Rule = self.env["ir.rule"].sudo(False)
        page_rule_domain = Rule._get_domain_accessible_records("website.page", "read")
        view_rule_domain = Rule._get_domain_accessible_records("ir.ui.view", "read")
        search_pattern = None
        if search and with_description:
            terms = "|".join(re.escape(term) for term in search.split())
            search_pattern = terms and re.compile(f"({terms})", re.IGNORECASE)

        def is_page_accessible(page):
            if not page.filtered_domain(page_rule_domain):
                return False
            if not page.view_id.filtered_domain(view_rule_domain):
                return False
            if search and with_description:
                if not search_pattern:
                    return False
                text = "%s %s %s" % (page.name, page.url, text_from_html(page.arch))
                return bool(search_pattern.search(text))
            return True

        results = results.filtered(is_page_accessible)
        _debug.pipeline(
            "page_search",
            search=search or None,
            candidates=len(most_specific_pages),
            accessible=len(results),
        )
        return results[:limit], len(results)

    def action_page_debug_view(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.ui.view",
            "res_id": self.view_id.id,
            "view_mode": "form",
            "view_id": self.env.ref("website.view_view_form_extend").id,
        }

    @api.model
    def _is_cache_usable(self, request):
        page_info = self._get_page_info(request) or {}
        return (
            request.httprequest.method == "GET"
            and not request.params
            and request.env.user._is_public()
            and not page_info.get("group_ids")
            and not (
                page_info
                and self.env["ir.ui.view"]
                ._get_cached_template_info(page_info["view_id"])
                .get("visibility")
            )
        )

    @api.model
    def _is_cache_insertion_allowed(self, layout):
        return True

    @api.model
    def _post_process_response_from_cache(
        self, request: http.Request, response: http.Response
    ) -> None:
        csrf_token = request.csrf_token(None)
        html = response.response[0]
        html = re.sub(r'csrf_token: "[^"]+"', f"csrf_token: {csrf_token!r}", html)
        html = re.sub(
            r'name="csrf_token" value="[^"]+"',
            f'name="csrf_token" value={csrf_token!r}',
            html,
        )
        response.response = [html]

        response._cached_view_id = self._get_page_info(request)["view_id"]
        response._cached_page = self

    @api.model
    def _get_cache_key(self, request):
        return (
            request.website.id,
            request.lang.code,
            request.httprequest.path,
            request.session.debug,
            request.env["ir.http"]._is_allowed_cookie("optional"),
        )

    def _get_response(self, request):
        self.check_singleton()
        if self._is_cache_usable(request):
            try:
                response, cache_key = self._get_response_cached(request)
            except PageCannotBeCached as not_cached:
                # Both raise sites carry (response, cache_key); the response may
                # be None, the tuple never is. Returning here is the only exit:
                # falling through would read `response` and `cache_key` unbound.
                _debug.logic(
                    "page_response",
                    by="uncacheable",
                    page=self.id,
                    rendered=bool(not_cached.rendered_response),
                )
                return not_cached.rendered_response

            if time.time() < response.time + self._CACHE_DURATION:
                resp = http.Response(
                    headers=response.headers.copy(),
                    mimetype=response.mimetype,
                    content_type=response.content_type,
                    status=response.status,
                    response=[response.response[0]],
                )
                self._post_process_response_from_cache(request, resp)
                _debug.logic("page_response", by="cache", page=self.id)
                return resp

            _debug.logic("page_response", by="cache_expired", page=self.id)
            response = self._get_response_raw(request)
            if response:
                response.flatten()
                self._get_response_cached.__cache__.add_value(
                    self, request, cache_value=(response, cache_key)
                )
            return response

        _debug.logic("page_response", by="uncached", page=self.id)
        return self._get_response_raw(request)

    @tools.conditional(
        "xml" not in tools.config["dev_mode"],
        tools.ormcache("self._get_cache_key(request)", cache="templates.cached_values"),
    )
    def _get_response_cached(self, request) -> tuple[http.Response, int, str]:
        cache_key = self._get_cache_key(request)
        with _debug.perf(
            "page_response_cache_miss", cr=self.env.cr, page=self.id
        ) as span:
            response = self._get_response_raw(request)
            span.set(rendered=bool(response))
        result = response, cache_key

        if not response:
            _debug.logic("page_not_cached", reason="no_response", page=self.id)
            raise PageCannotBeCached(response)

        response.flatten()
        if not self._is_cache_insertion_allowed(response.response[-1]):
            _debug.logic("page_not_cached", reason="layout_refused", page=self.id)
            raise PageCannotBeCached(response)

        return result

    def _get_response_raw(self, request) -> http.Response | None:
        req_page = request.httprequest.path

        fields_to_fetch = [
            name for name, field in self._fields.items() if field.prefetch
        ]
        self.fetch(fields_to_fetch)

        fields_to_fetch = [
            name for name, field in self.view_id._fields.items() if field.prefetch
        ]
        self.view_id.fetch(fields_to_fetch)

        if (
            self.env.user.has_group("website.group_website_designer") or self.is_visible
        ) and (
            self.website_id
            or self.view_id.id
            == self.env["ir.ui.view"]
            .with_context(website_id=request.website.id)
            ._get_cached_template_info(self.view_id.key)["id"]
        ):
            ext = PurePosixPath(req_page).suffix
            response = request.render(
                self.view_id.id,
                {
                    "main_object": self,
                },
                mimetype=EXTENSION_TO_WEB_MIMETYPES.get(ext, "text/html"),
            )
            response.time = time.time()
            return response

        _debug.logic(
            "page_render_skipped",
            page=self.id,
            path=req_page,
            visible=self.is_visible,
            specific=bool(self.website_id),
        )
        return None

    @tools.conditional(
        "xml" not in tools.config["dev_mode"],
        tools.ormcache(
            '(request.httprequest.path, self.env.context.get("website_id"))',
            cache="templates.cached_values",
        ),
    )
    @api.model
    def _get_page_info(self, request) -> dict | None:
        req_page = request.httprequest.path

        page_domain = Domain("url", "=", req_page) & request.website.website_domain()
        page = self.sudo().search_fetch(page_domain, order="website_id asc", limit=1)

        if not page:
            page_domain = (
                Domain("url", "=ilike", escape_psql(req_page))
                & request.website.website_domain()
            )
            page = self.sudo().search_fetch(
                page_domain, order="website_id asc", limit=1
            )
            _debug.logic(
                "page_info", by="case_insensitive_url", path=req_page, page=page.id
            )

        if page:
            return {
                "id": page.id,
                "url": page.url,
                "view_id": page.view_id.id,
                "group_ids": page.group_ids.ids,
            }
        return None
