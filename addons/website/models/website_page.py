import logging
import re
import time
from collections import Counter
from pathlib import PurePosixPath

from odoo import api, fields, http, models, tools
from odoo.fields import Domain
from odoo.tools import SQL, escape_psql

from odoo.addons.base.models.ir_http import EXTENSION_TO_WEB_MIMETYPES
from odoo.addons.website.tools import text_from_html

logger = logging.getLogger(__name__)


class PageCannotBeCached(Exception):
    def __init__(self, result):
        self.result = result


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

    website_id = fields.Many2one(
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

    def _get_most_specific_pages(self):
        ids = []
        previous_page = None
        page_keys = (
            self.sudo()
            .with_context(prefetch_fields=False)
            .search_fetch(
                self.env["website"]
                .browse(self.env.context.get("website_id"))
                .website_domain(),
                field_names=["key"],
            )
            .mapped("key")
        )
        page_keys_counts = Counter(page_keys)

        for page in self.sorted(key=lambda p: (p.url, not p.website_id)):
            if (not previous_page or page.url != previous_page.url) and (
                page.website_id or page_keys_counts[page.key] == 1
            ):
                ids.append(page.id)
            previous_page = page
        return self.browse(ids)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if not default:
            return vals_list
        for page, vals in zip(self, vals_list, strict=False):
            if not default.get("view_id"):
                new_view = page.view_id.copy({"website_id": default.get("website_id")})
                vals["view_id"] = new_view.id
                vals["key"] = new_view.key
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

        return new_page.url

    def unlink(self):
        views_to_delete = self.view_id.filtered(
            lambda v: v.page_ids <= self and not v.inherit_children_ids
        )
        self -= views_to_delete.page_ids
        views_to_delete.unlink()

        if self:
            self.env.registry.clear_cache("templates")
        return super().unlink()

    def write(self, vals):
        if "visibility" in vals and vals["visibility"] != "restricted_group":
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
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "url", "type": "text", "truncate": False},
        }
        if with_description:
            search_fields.append("arch_db")
            fetch_fields.append("arch")
            mapping["description"] = {
                "name": "arch",
                "type": "text",
                "html": True,
                "match": True,
            }
        return {
            "model": "website.page",
            "base_domain": domain,
            "requires_sudo": requires_sudo,
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
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
        most_specific_pages = self.env["website"]._get_website_pages(
            domain=base_domain, order=order
        )
        results = most_specific_pages.filtered_domain(domain)
        v_arch_db = self.env["ir.ui.view"]._field_to_sql("v", "arch_db")

        if with_description and search and most_specific_pages:
            rows = self.env.execute_query(
                SQL(
                    """
                SELECT DISTINCT %(table)s.id
                FROM %(table)s
                LEFT JOIN ir_ui_view v ON %(table)s.view_id = v.id
                WHERE (v.name ILIKE %(search)s
                OR %(v_arch_db)s ILIKE %(search)s)
                AND %(table)s.id IN %(ids)s
                LIMIT %(limit)s
                """,
                    table=SQL.identifier(self._table),
                    search=f"%{escape_psql(search)}%",
                    v_arch_db=v_arch_db,
                    ids=tuple(most_specific_pages.ids),
                    limit=len(most_specific_pages.ids),
                )
            )
            ids = {row[0] for row in rows}
            if ids:
                ids.update(results.ids)
                domain = base_domain & Domain("id", "in", ids)
                model = self.sudo() if search_detail.get("requires_sudo") else self
                results = model.search(
                    domain, limit=len(ids), order=search_detail.get("order", order)
                )

        def is_page_accessible(search, page, all_pages):
            Rule = page.env["ir.rule"].sudo(False)
            if not page.filtered_domain(
                Rule._get_domain_accessible_records("website.page", "read")
            ):
                return False
            if not page.view_id.filtered_domain(
                Rule._get_domain_accessible_records("ir.ui.view", "read")
            ):
                return False
            if search and with_description:
                text = "%s %s %s" % (page.name, page.url, text_from_html(page.arch))
                pattern = "|".join(
                    [re.escape(search_term) for search_term in search.split()]
                )
                return (
                    re.findall("(%s)" % pattern, text, flags=re.IGNORECASE)
                    if pattern
                    else False
                )
            return True

        results = results.filtered(
            lambda result: is_page_accessible(search, result, results)
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
            except PageCannotBeCached as notCache:
                if notCache.result:
                    return notCache.result[0]

            if time.time() < response.time + self._CACHE_DURATION:
                resp = http.Response(
                    headers=response.headers.copy(),
                    mimetype=response.mimetype,
                    content_type=response.content_type,
                    status=response.status,
                    response=[response.response[0]],
                )
                self._post_process_response_from_cache(request, resp)
                return resp

            response = self._get_response_raw(request)
            if response:
                response.flatten()
                self._get_response_cached.__cache__.add_value(
                    self, request, cache_value=(response, cache_key)
                )
            return response

        return self._get_response_raw(request)

    @tools.conditional(
        "xml" not in tools.config["dev_mode"],
        tools.ormcache("self._get_cache_key(request)", cache="templates.cached_values"),
    )
    def _get_response_cached(self, request) -> tuple[http.Response, int, str]:
        cache_key = self._get_cache_key(request)
        response = self._get_response_raw(request)
        result = response, cache_key

        if not response:
            raise PageCannotBeCached(result)

        response.flatten()
        if not self._is_cache_insertion_allowed(response.response[-1]):
            raise PageCannotBeCached(result)

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

        if page:
            return {
                "id": page.id,
                "url": page.url,
                "view_id": page.view_id.id,
                "group_ids": page.group_ids.ids,
            }
        return None
