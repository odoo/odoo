import base64
import binascii
import datetime
import logging
import re
import urllib.parse
import zipfile
import zlib
from hashlib import md5, sha256
from io import BytesIO
from itertools import islice
from pathlib import PurePosixPath
from textwrap import shorten

import requests
import werkzeug.utils
import werkzeug.wrappers
from defusedxml.ElementTree import fromstring as defused_fromstring
from lxml import etree, html
from werkzeug.exceptions import NotFound

import odoo
from odoo import _, fields, http, models, tools
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.http import SessionExpiredException, request
from odoo.tools import OrderedSet, consteq, escape_psql, py_to_js_locale
from odoo.tools import html_escape as escape
from odoo.tools.json import scriptsafe as json
from odoo.tools.translate import TRANSLATED_ELEMENTS, LazyTranslate

from odoo.addons.base.models.ir_http import EXTENSION_TO_WEB_MIMETYPES
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers.web import Home
from odoo.addons.web.controllers.binary import Binary
from odoo.addons.web.controllers.session import Session
from odoo.addons.website.tools import get_base_hostname

_lt = LazyTranslate(__name__)
logger = logging.getLogger(__name__)

LOC_PER_SITEMAP = 45000
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)
MAX_FONT_FILE_SIZE = 10 * 1024 * 1024
MAX_FONT_UPLOAD_SIZE = 100 * 1024 * 1024
MAX_FONT_ARCHIVE_SIZE = 100 * 1024 * 1024
MAX_FONT_ARCHIVE_ENTRIES = 1000
SUPPORTED_FONT_EXTENSIONS = ["ttf", "woff", "woff2", "otf"]
MAX_PAGE_SEARCH_RESULTS = 500


class QueryURL:
    def __init__(self, path="", path_args=None, **args):
        self.path = path
        self.args = args
        self.path_args = OrderedSet(path_args or [])

    def __call__(self, path=None, path_args=None, **kw):
        path_prefix = path or self.path
        path = ""
        for key, value in self.args.items():
            kw.setdefault(key, value)
        slug = request.env["ir.http"]._slug
        path_args = OrderedSet(path_args or []) | self.path_args
        paths, fragments = {}, []
        for key, value in kw.items():
            if value and key in path_args:
                if isinstance(value, models.BaseModel):
                    paths[key] = slug(value)
                else:
                    paths[key] = "%s" % value
            elif value:
                if isinstance(value, (list, set)):
                    fragments.append(
                        urllib.parse.urlencode([(key, item) for item in value if item])
                    )
                else:
                    fragments.append(urllib.parse.urlencode([(key, value)]))
        for key in path_args:
            value = paths.get(key)
            if value is not None:
                path += "/" + key + "/" + value
        if fragments:
            path += "?" + "&".join(fragments)
        if not path.startswith(path_prefix):
            path = path_prefix + path
        return path


class Website(Home):
    @http.route("/", auth="public", website=True, sitemap=True)
    def index(self, **kw):
        homepage_url = request.website._get_cached("homepage_url")
        if homepage_url and homepage_url != "/":
            request.reroute(homepage_url)

        website_page = request.env["ir.http"]._serve_page()
        if website_page:
            return website_page

        if homepage_url and homepage_url != "/":
            try:
                rule, args = request.env["ir.http"]._match(homepage_url)
                return request._serve_ir_http(rule, args)
            except AccessError, NotFound, SessionExpiredException:
                pass

        def is_reachable(menu):
            return (
                menu.is_visible
                and menu.url not in ("/", "", "#")
                and not menu.url.startswith(("/?", "/#", " "))
            )

        top_menu = request.website.menu_id

        reachable_menus = top_menu.child_id.filtered(is_reachable)
        if reachable_menus:
            return request.redirect(reachable_menus[0].url)

        raise request.prepare_not_found_error()

    @http.route(
        "/website/force/<int:website_id>",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        multilang=False,
        readonly=True,
    )
    def website_force(self, website_id, path="/", isredir=False, **kw):
        if not (
            request.env.user.has_group("website.group_multi_website")
            and request.env.user.has_group("website.group_website_restricted_editor")
        ):
            return request.redirect(path)

        website = request.env["website"].browse(website_id)

        if not isredir and website.domain:
            domain_from = request.httprequest.environ.get("HTTP_HOST", "")
            domain_to = get_base_hostname(website.domain)
            if domain_from != domain_to:
                query_params = urllib.parse.urlencode({"isredir": 1, "path": path})
                url_to = tools.urls.urljoin(
                    website.domain,
                    f"/website/force/{website.id}?{query_params}",
                )
                return request.redirect(url_to, local=False)
        website._force()
        return request.redirect(path)

    @http.route(
        ["/@/", "/@/<path:path>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        multilang=False,
        readonly=True,
    )
    def client_action_redirect(self, path="", **kw):
        path = "/" + path
        mode_edit = bool(kw.pop("enable_editor", False))
        mode_debug = kw.get("debug", 0)
        if kw:
            path += "?" + urllib.parse.urlencode(kw)

        if request.env.user._is_internal():
            path = request.website.get_client_action_url(path, mode_edit, mode_debug)

        return request.redirect(path)

    def _login_redirect(self, uid, redirect=None):
        if not redirect and request.params.get("login_success"):
            if request.env["res.users"].browse(uid)._is_internal():
                redirect = "/odoo?" + request.httprequest.query_string.decode()
            else:
                redirect = "/my"
        return super()._login_redirect(uid, redirect=redirect)

    @http.route(website=True, auth="public", sitemap=False)
    def web_login(self, *args, **kw):
        return super().web_login(*args, **kw)

    @http.route(
        "/website/get_languages",
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def website_languages(self, **kwargs):
        return [
            (py_to_js_locale(lg.code), lg.url_code, lg.name)
            for lg in request.website.language_ids
        ]

    @http.route(
        "/website/get_translated_elements", type="jsonrpc", auth="user", readonly=True
    )
    def translated_elements(self, **kwargs):
        return list(TRANSLATED_ELEMENTS)

    @http.route(
        "/website/lang/<lang>",
        type="http",
        auth="public",
        website=True,
        multilang=False,
    )
    def change_lang(self, lang, r="/", **kwargs):
        if lang == "default":
            lang = request.website.default_lang_id.url_code
            r = "/%s%s" % (lang, r or "/")
        lang_code = request.env["res.lang"]._get_data(url_code=lang).code or lang
        request.update_context(lang=lang_code)
        redirect = request.redirect(r or ("/%s" % lang))
        redirect.set_cookie("frontend_lang", lang_code)
        return redirect

    @http.route(
        ['/website/country_infos/<model("res.country"):country>'],
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        readonly=True,
    )
    def country_infos(self, country, **kw):
        fields = country.get_fields_address()
        return {
            "fields": fields,
            "states": [(st.id, st.name, st.code) for st in country.state_ids],
            "phone_code": country.phone_code,
        }

    @http.route(
        ["/robots.txt"],
        type="http",
        auth="public",
        website=True,
        multilang=False,
        sitemap=False,
    )
    def robots(self, **kwargs):
        return request.render(
            "website.robots",
            {
                "allowed_routes": self._get_allowed_robots_routes(),
                "url_root": request.httprequest.url_root,
            },
            mimetype="text/plain",
        )

    @http.route(
        "/sitemap.xml",
        type="http",
        auth="public",
        website=True,
        multilang=False,
        sitemap=False,
    )
    def sitemap_xml_index(self, **kwargs):
        current_website = request.website
        Attachment = request.env["ir.attachment"].sudo()
        View = request.env["ir.ui.view"].sudo()
        mimetype = "application/xml;charset=utf-8"
        content = None
        canonical = current_website.get_base_url()
        if current_website.domain:
            parsed = urllib.parse.urlparse(
                current_website.domain
                if "//" in current_website.domain
                else "https://" + current_website.domain
            )
            if parsed.netloc:
                canonical = f"{parsed.scheme or 'https'}://{parsed.netloc}"
        url_root = (canonical or request.httprequest.url_root).rstrip("/") + "/"
        hashed_url_root = md5(url_root.encode()).hexdigest()[:8]
        sitemap_base_url = "/sitemap-%d-%s" % (current_website.id, hashed_url_root)

        def create_sitemap(url, content):
            return Attachment.create(
                {
                    "raw": content.encode(),
                    "mimetype": mimetype,
                    "type": "binary",
                    "name": url,
                    "url": url,
                }
            )

        dom = [("url", "=", "%s.xml" % sitemap_base_url), ("type", "=", "binary")]
        sitemap = Attachment.search(dom, limit=1)
        if sitemap:
            delta = fields.Datetime.now() - sitemap.create_date
            if delta < SITEMAP_CACHE_TIME:
                content = sitemap.raw

        if not content:
            dom = [
                ("type", "=", "binary"),
                ("url", "=like", "/sitemap-%d-%%" % current_website.id),
            ]
            sitemaps = Attachment.search(dom)
            sitemaps.unlink()

            pages = 0
            locs = request.website.with_user(request.website.user_id)._enumerate_pages()
            while True:
                values = {
                    "locs": islice(locs, 0, LOC_PER_SITEMAP),
                    "url_root": url_root[:-1],
                }
                urls = View._render_template("website.sitemap_locs", values)
                if urls.strip():
                    content = View._render_template(
                        "website.sitemap_xml", {"content": urls}
                    )
                    pages += 1
                    last_sitemap = create_sitemap(
                        "%s-%d.xml" % (sitemap_base_url, pages), content
                    )
                else:
                    break

            if not pages:
                return request.prepare_not_found_error()
            elif pages == 1:
                last_sitemap.write(
                    {
                        "url": "%s.xml" % sitemap_base_url,
                        "name": "%s.xml" % sitemap_base_url,
                    }
                )
            else:
                pages_with_website = [
                    "%d-%s-%d" % (current_website.id, hashed_url_root, p)
                    for p in range(1, pages + 1)
                ]

                content = View._render_template(
                    "website.sitemap_index_xml",
                    {
                        "pages": pages_with_website,
                        "url_root": url_root,
                    },
                )
                create_sitemap("%s.xml" % sitemap_base_url, content)

        return request.prepare_response(content, [("Content-Type", mimetype)])

    @http.route(
        ["/favicon.ico"],
        type="http",
        auth="public",
        website=True,
        multilang=False,
        sitemap=False,
        readonly=True,
    )
    def favicon(self, **kw):
        website = request.website
        response = request.redirect(website.image_url(website, "favicon"), code=301)
        response.headers["Cache-Control"] = (
            "public, max-age=%s" % http.STATIC_CACHE_LONG
        )
        return response

    def sitemap_website_info(env, rule, qs):  # noqa: N805 -- sitemap callback, first arg is the env
        website = env["website"].get_current_website()
        if not (
            website.is_view_active("website.website_info")
            and website.is_view_active("website.show_website_info")
        ):
            return

        if not qs or qs.lower() in "/website/info":
            yield {"loc": "/website/info"}

    @http.route(
        "/website/info",
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_website_info,
        readonly=True,
        list_as_website_content=_lt("Website Information"),
    )
    def website_info(self, **kwargs):
        Module = request.env["ir.module.module"].sudo()
        apps = Module.search([("state", "=", "installed"), ("application", "=", True)])
        l10n = Module.search([("state", "=", "installed"), ("name", "=like", "l10n_%")])
        values = {
            "apps": apps,
            "l10n": l10n,
            "version": odoo.service.common.exp_version(),
        }
        return request.render("website.website_info", values)

    @http.route(
        ["/website/configurator", "/website/configurator/<int:step>"],
        type="http",
        auth="user",
        website=True,
        multilang=False,
    )
    def website_configurator(self, step=1, **kwargs):
        if not request.env.user.has_group("website.group_website_designer"):
            raise werkzeug.exceptions.NotFound
        if request.website.configurator_done:
            return request.redirect("/")
        if request.env.lang != request.website.default_lang_id.code:
            return request.redirect(
                request.env["ir.http"]._lang_url_prefix(
                    request.httprequest.path,
                    request.website.default_lang_id.url_code,
                )
            )
        action_url = f"/odoo/action-website.website_configurator?menu_id={request.env.ref('website.menu_website_configuration').id}"
        if step > 1:
            action_url += "&step=" + str(step)
        return request.redirect(action_url)

    @http.route(
        ["/website/social/<string:social>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def social(self, social, **kwargs):
        url = getattr(request.website, "social_%s" % social, False)
        if not url:
            raise werkzeug.exceptions.NotFound
        return request.redirect(url, local=False)

    @http.route(
        "/website/get_suggested_links",
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def get_suggested_link(self, needle, limit=10):
        current_website = request.website

        limit = None if limit == "no_limit" else int(limit)
        matching_pages = [
            {
                "value": page["loc"],
                "label": ("name" in page and "%s (%s)" % (page["loc"], page["name"]))
                or page["loc"],
            }
            for page in current_website.search_pages(needle, limit)
        ]
        matching_urls = {match["value"] for match in matching_pages}

        matching_last_modified = []
        last_modified_pages = current_website._get_website_pages(
            order="write_date desc", limit=5
        )
        for url, name in last_modified_pages.mapped(lambda p: (p.url, p.name)):
            if url not in matching_urls and (
                needle.lower() in name.lower() or needle.lower() in url.lower()
            ):
                matching_last_modified.append(
                    {
                        "value": url,
                        "label": "%s (%s)" % (url, name),
                    }
                )

        suggested_controllers = []
        for name, url, mod in current_website.get_suggested_controllers():
            if needle.lower() in name.lower() or needle.lower() in url.lower():
                module_sudo = (
                    mod and request.env.ref("base.module_%s" % mod, False).sudo()
                )
                icon = (
                    mod and "%s" % ((module_sudo and module_sudo.icon) or mod)
                ) or ""
                suggested_controllers.append(
                    {
                        "value": url,
                        "icon": icon,
                        "label": "%s (%s)" % (url, name),
                    }
                )

        return {
            "matching_pages": sorted(matching_pages, key=lambda o: o["label"]),
            "others": [
                {"title": _("Last modified pages"), "values": matching_last_modified},
                {"title": _("Apps url"), "values": suggested_controllers},
            ],
        }

    @http.route(
        "/website/check_existing_link",
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def check_existing_link(self, link):
        return request.website.is_page_existing(link)

    @http.route(
        "/website/save_session_layout_mode",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def save_session_layout_mode(self, layout_mode, view_id):
        assert layout_mode in ("grid", "list"), "Invalid layout mode"
        view_id = int(view_id)
        request.session[f"website_{view_id}_layout_mode"] = layout_mode

    @http.route(
        "/website/snippet/filters",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def get_dynamic_filter(self, filter_id, **kwargs):
        dynamic_filter_sudo = request.env["website.snippet.filter"].sudo()
        if filter_id:
            dynamic_filter_sudo = dynamic_filter_sudo.search(
                Domain("id", "=", filter_id) & request.website.website_domain()
            )
        single_record_filter = (
            kwargs.get("limit") == 1
            and kwargs.get("res_model")
            and kwargs.get("res_id")
        )
        dynamic_filter_found = single_record_filter or dynamic_filter_sudo
        return dynamic_filter_sudo._render(**kwargs) if dynamic_filter_found else []

    @http.route(
        "/website/snippet/options_filters",
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def get_dynamic_snippet_filters(self, model_name=None, search_domain=None):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.NotFound
        domain = request.website.website_domain()
        if search_domain:
            search_domain = Domain(search_domain)
            assert all(
                condition.field_expr in request.env["website.snippet.filter"]._fields
                for condition in search_domain.iter_conditions()
            )
            domain &= search_domain
        if model_name:
            domain &= Domain("filter_id.model_id", "=", model_name) | Domain(
                "action_server_id.model_id.model", "=", model_name
            )
        return (
            request.env["website.snippet.filter"]
            .sudo()
            .search_read(
                domain, ["id", "name", "limit", "model_name", "help"], order="id asc"
            )
        )

    @http.route(
        "/website/snippet/filter_templates",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def get_dynamic_snippet_templates(self, filter_name=False):
        domain = [["key", "ilike", ".dynamic_filter_template_"], ["type", "=", "qweb"]]
        if filter_name:
            domain.append(["key", "ilike", escape_psql("_%s_" % filter_name)])
        templates = (
            request.env["ir.ui.view"]
            .sudo()
            .search_read(domain, ["key", "name", "arch_db"])
        )

        for t in templates:
            children = list(etree.fromstring(t.pop("arch_db")))
            attribs = (children and children[0].attrib) or {}
            t["numOfEl"] = attribs.get("data-number-of-elements")
            t["numOfElSm"] = attribs.get("data-number-of-elements-sm")
            t["numOfElFetch"] = attribs.get("data-number-of-elements-fetch")
            t["rowPerSlide"] = attribs.get("data-row-per-slide")
            t["arrowPosition"] = attribs.get("data-arrow-position")
            t["extraClasses"] = attribs.get("data-extra-classes")
            t["extraSnippetClasses"] = attribs.get("data-extra-snippet-classes")
            t["containerClasses"] = attribs.get("data-container-classes")
            t["contentClasses"] = attribs.get("data-content-classes")
            t["columnClasses"] = attribs.get("data-column-classes")
            t["thumb"] = attribs.get("data-thumb")
        return templates

    @http.route(
        "/website/get_current_currency",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def get_current_currency(self, **kwargs):
        return {
            "id": request.website.company_id.currency_id.id,
            "symbol": request.website.company_id.currency_id.symbol,
            "position": request.website.company_id.currency_id.position,
        }

    def _get_search_order(self, order):
        order = order or "name ASC"
        return "is_published desc, %s, id desc" % order

    @http.route(
        "/website/snippet/autocomplete",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def autocomplete(
        self,
        search_type=None,
        term=None,
        order=None,
        limit=5,
        max_nb_chars=999,
        options=None,
    ):
        limit = min(max(int(limit or 0), 0), MAX_PAGE_SEARCH_RESULTS)
        options = self._get_page_search_options() | (options or {})
        try:
            results_count, search_results, fuzzy_term = (
                request.website._search_with_fuzzy(
                    search_type, term, limit, self._get_search_order(order), options
                )
            )
        except ValueError:
            results_count, search_results, fuzzy_term = (
                request.website._search_with_fuzzy(
                    search_type, term, limit, self._get_search_order(None), options
                )
            )
        if not results_count:
            return {
                "results": [],
                "results_count": 0,
                "parts": {},
            }
        term = fuzzy_term or term
        highlight_terms = "|".join(map(re.escape, (term or "").split()))
        highlight_pattern = (
            re.compile(f"({highlight_terms})", re.IGNORECASE)
            if highlight_terms
            else None
        )
        search_results = request.website._search_render_results(search_results, limit)

        mappings = []
        results_data = []
        for search_result in search_results:
            results_data += search_result["results_data"]
            mappings.append(search_result["mapping"])
        if search_type == "all":
            results_data.sort(
                key=lambda r: r.get("name", ""),
                reverse=bool(order) and "name desc" in order,
            )
        results_data = results_data[:limit]
        result = []
        for record in results_data:
            mapping = record["_mapping"]
            mapped = {
                "_fa": record.get("_fa"),
            }
            for mapped_name, field_meta in mapping.items():
                value = record.get(field_meta.get("name"))
                if not value:
                    mapped[mapped_name] = ""
                    continue
                field_type = field_meta.get("type")
                if field_type == "text":
                    if field_meta.get("truncate", True):
                        value = shorten(value, max_nb_chars, placeholder="...")
                    if field_meta.get("match") and highlight_pattern:
                        parts = highlight_pattern.split(value)
                        if len(parts) > 1:
                            value = (
                                request.env["ir.ui.view"]
                                .sudo()
                                ._render_template(
                                    "website.search_text_with_highlight",
                                    {"parts": parts},
                                )
                            )
                            field_type = "html"

                if (
                    field_type not in ("image", "binary")
                    and ("ir.qweb.field.%s" % field_type) in request.env
                ):
                    opt = {}
                    if field_type == "monetary":
                        opt["display_currency"] = options.get("display_currency")
                    value = request.env[
                        ("ir.qweb.field.%s" % field_type)
                    ].value_to_html(value, opt)
                mapped[mapped_name] = escape(value)
            result.append(mapped)

        return {
            "results": result,
            "results_count": results_count,
            "parts": {key: True for mapping in mappings for key in mapping},
            "fuzzy_search": fuzzy_term,
        }

    def _get_page_search_options(self, **post):
        return {
            "displayDescription": False,
            "displayDetail": False,
            "displayExtraDetail": False,
            "displayExtraLink": False,
            "displayImage": False,
            "allowFuzzy": not post.get("noFuzzy"),
        }

    @http.route(
        ["/pages", "/pages/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def pages_list(self, page=1, search="", **kw):
        options = self._get_page_search_options(**kw)
        step = 50
        page = min(max(int(page), 1), 100)
        pages_count, details, fuzzy_search_term = request.website._search_with_fuzzy(
            "pages",
            search,
            limit=page * step,
            order="name asc, website_id desc, id",
            options=options,
        )
        pages = details[0].get("results", request.env["website.page"])

        pager = portal_pager(
            url="/pages",
            url_args={"search": search},
            total=pages_count,
            page=page,
            step=step,
        )

        pages = pages[pager["offset"] : pager["offset"] + step]

        values = {
            "pager": pager,
            "pages": pages,
            "search": fuzzy_search_term or search,
            "search_count": pages_count,
            "original_search": fuzzy_search_term and search,
        }
        return request.render("website.list_website_public_pages", values)

    def _get_hybrid_search_options(self, **post):
        return {
            "displayDescription": True,
            "displayDetail": True,
            "displayExtraDetail": True,
            "displayExtraLink": True,
            "displayImage": True,
            "allowFuzzy": not post.get("noFuzzy"),
        }

    @http.route(
        [
            "/website/search",
            "/website/search/page/<int:page>",
            "/website/search/<string:search_type>",
            "/website/search/<string:search_type>/page/<int:page>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def hybrid_list(self, page=1, search="", search_type="all", **kw):
        if not search:
            return request.render("website.list_hybrid")

        options = self._get_hybrid_search_options(**kw)
        data = self.autocomplete(
            search_type=search_type,
            term=search,
            order="name asc",
            limit=MAX_PAGE_SEARCH_RESULTS,
            max_nb_chars=200,
            options=options,
        )

        results = data.get("results", [])
        search_count = len(results)
        parts = data.get("parts", {})

        step = 50
        pager = portal_pager(
            url="/website/search/%s" % search_type,
            url_args={"search": search},
            total=search_count,
            page=page,
            step=step,
        )

        results = results[pager["offset"] : pager["offset"] + step]

        values = {
            "pager": pager,
            "results": results,
            "parts": parts,
            "search": search,
            "fuzzy_search": data.get("fuzzy_search"),
            "search_count": search_count,
        }
        return request.render("website.list_hybrid", values)

    @http.route(
        ["/website/add", "/website/add/<path:path>"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def pagenew(
        self, path="", add_menu=False, template=False, redirect=False, **kwargs
    ):
        ext = PurePosixPath(path).suffix
        ext_special_case = ext != ".html" and ext in EXTENSION_TO_WEB_MIMETYPES

        if not template and ext_special_case:
            default_templ = "website.default_%s" % ext.lstrip(".")
            if request.env.ref(default_templ, False):
                template = default_templ

        template = (template and {"template": template}) or {}
        website_id = kwargs.get("website_id")
        if website_id:
            website = request.env["website"].browse(int(website_id))
            website._force()
        page = request.env["website"].new_page(
            path,
            add_menu=add_menu,
            sections_arch=kwargs.get("sections_arch"),
            page_title=kwargs.get("page_title"),
            **template,
        )
        url = page["url"]
        menu = request.env["website.menu"].search(
            [
                ("url", "=", "/" + path),
                ("page_id", "=", False),
                ("website_id", "in", (False, request.website.id)),
            ],
            limit=1,
        )
        if menu:
            menu.page_id = page["page_id"]

        if redirect:
            if ext_special_case:
                return request.redirect(f"/odoo/ir.ui.view/{page.get('view_id')}")
            return request.redirect(
                request.env["website"].get_client_action_url(url, True)
            )

        if ext_special_case:
            return request.prepare_json_response({"view_id": page.get("view_id")})
        return request.prepare_json_response({"url": url})

    @http.route(
        "/website/get_new_page_templates",
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def get_new_page_templates(self, **kw):
        View = request.env["ir.ui.view"]
        result = []
        groups_html = View._render_template("website.new_page_template_groups")
        groups_el = etree.fromstring(f"<data>{groups_html}</data>")
        for group_el in groups_el:
            group = {
                "id": group_el.attrib["id"],
                "title": group_el.text,
                "templates": [],
            }
            if group_el.attrib["id"] == "custom":
                for page in request.website._get_website_pages(
                    domain=[("is_new_page_template", "=", True)]
                ):
                    html_tree = html.fromstring(
                        View.with_context(inherit_branding=False)._render_template(
                            page.key,
                        )
                    )
                    wrap_el = html_tree.xpath('//div[@id="wrap"]')[0]
                    group["templates"].append(
                        {
                            "key": page.key,
                            "template": html.tostring(wrap_el),
                            "name": page.name,
                        }
                    )
                group["is_custom"] = True
                result.append(group)
                continue
            for template in View.search(  # noqa: E8507 - one query per template group; the groups are a fixed list rendered from a template
                [
                    ("mode", "=", "primary"),
                    "|",
                    (
                        "key",
                        "like",
                        escape_psql(f"new_page_template_sections_{group['id']}_"),
                    ),
                    ("key", "like", f"configurator_pages_{group['id']}"),
                    request.website.website_domain(),
                ],
                order="key",
            ):
                try:
                    html_tree = html.fromstring(
                        View.with_context(inherit_branding=False)._render_template(
                            template.key,
                        )
                    )
                    for section_el in html_tree.xpath("//section[@data-snippet]"):
                        snippet = section_el.attrib["data-snippet"]
                        if "_s_" in snippet:
                            section_el.attrib["data-snippet"] = (
                                f"s_{snippet.split('_s_')[-1]}"
                            )

                    group["templates"].append(
                        {
                            "key": template.key,
                            "template": html.tostring(html_tree),
                            "is_from_configurator": "configurator_pages"
                            in template.key,
                        }
                    )
                except Exception as error:
                    if hasattr(error, "qweb"):
                        logger.warning(
                            "Theme not compatible with template %r: %s",
                            template.key,
                            error,
                        )
                    else:
                        raise
            if group["templates"]:
                result.append(group)
        return result

    @http.route("/website/save_xml", type="jsonrpc", auth="user", website=True)
    def save_xml(self, view_id, arch):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.Forbidden
        request.env["ir.ui.view"].browse(view_id).with_context(
            lang=request.website.default_lang_id.code,
            delay_translations=True,
        ).arch = arch

    @http.route(
        "/website/get_switchable_related_views",
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def get_switchable_related_views(self, key):
        views = (
            request.env["ir.ui.view"]
            .get_related_views(key, bundles=False)
            .filtered(lambda v: v.customize_show)
        )
        views = views.sorted(key=lambda v: (v.inherit_id.id, v.name))
        return views.with_context(display_website=False).read(
            ["name", "id", "key", "xml_id", "active", "inherit_id"]
        )

    @http.route(
        "/website/reset_template", type="jsonrpc", auth="user", methods=["POST"]
    )
    def reset_template(self, view_id, mode="soft", **kwargs):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.Forbidden
        view = request.env["ir.ui.view"].browse(int(view_id))
        view.with_context(website_id=None).reset_arch(mode)
        return True

    @http.route(
        ["/website/seo_suggest"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def seo_suggest(self, keywords=None, lang=None):
        pattern = r"^([a-zA-Z]+)(?:_(\w+))?(?:@(\w+))?$"
        match = re.match(pattern, lang or "")
        language = [match.group(1), match.group(2) or ""] if match else ["en", "US"]
        url = "https://www.google.com/complete/search"
        try:
            req = request.env["ir.egress"].request(
                "GET",
                url,
                purpose="seo_suggest",
                params={
                    "ie": "utf8",
                    "oe": "utf8",
                    "output": "toolbar",
                    "q": keywords,
                    "hl": language[0],
                    "gl": language[1],
                },
                timeout=5,
            )
            req.raise_for_status()
            response = req.content
        except OSError:
            return json.dumps([])
        xmlroot = defused_fromstring(response)
        return json.dumps(
            [
                sugg[0].attrib["data"]
                for sugg in xmlroot
                if len(sugg) and sugg[0].attrib["data"]
            ]
        )

    @http.route(["/website/get_alt_images"], type="jsonrpc", auth="user", website=True)
    def get_alt_images(self, models):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.Forbidden
        result = []
        for model in models:
            record = self._get_html_record(model["model"], model["id"])
            if not record.has_access("read"):
                continue
            field_name = "arch_db" if model["field"] == "arch" else model["field"]
            tree = self._get_html_tree(record, field_name)
            if tree is None:
                continue
            for index, el in enumerate(tree.xpath("//img[@src]")):
                role = el.get("role")
                decorative = role == "presentation"
                alt = el.get("alt")
                if not decorative or alt is None:
                    result.append(
                        {
                            "src": el.get("src"),
                            "alt": alt or "",
                            "decorative": False,
                            "updated": False,
                            "res_model": model["model"],
                            "res_id": model["id"],
                            "id": f"{model['model']}-{model['id']}-{index}",
                            "field": field_name,
                        }
                    )
        return json.dumps(result)

    @http.route(
        ["/website/update_alt_images"], type="jsonrpc", auth="user", website=True
    )
    def update_alt_images(self, imgs):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.Forbidden
        self._update_html_fields(imgs, self._update_image_attributes)

    def _update_image_attributes(self, tree, imgs):
        images_by_id = {img["id"]: img for img in imgs}
        prefix = f"{imgs[0]['res_model']}-{imgs[0]['res_id']}-"
        modified = False
        elements = tree.xpath("//img[@src]") if tree is not None else ()
        for index, element in enumerate(elements):
            if img := images_by_id.pop(f"{prefix}{index}", None):
                if "src" in img and img["src"] != element.get("src"):
                    logger.debug("Stale website image target id=%s", img["id"])
                    raise UserError(
                        _(
                            "The page images have changed. Refresh the page before saving image descriptions."
                        )
                    )
                if img["decorative"]:
                    if (
                        element.get("alt") == ""
                        and element.get("role") == "presentation"
                    ):
                        continue
                    element.set("alt", "")
                    element.set("role", "presentation")
                else:
                    if (
                        element.get("alt") == img["alt"]
                        and "role" not in element.attrib
                    ):
                        continue
                    element.set("alt", img["alt"])
                    element.attrib.pop("role", None)
                modified = True
        if any("src" in img for img in images_by_id.values()):
            logger.debug("Missing website image targets count=%d", len(images_by_id))
            raise UserError(
                _(
                    "The page images have changed. Refresh the page before saving image descriptions."
                )
            )
        return modified

    @http.route(
        ["/website/update_broken_links"], type="jsonrpc", auth="user", website=True
    )
    def update_broken_links(self, links):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.Forbidden
        self._update_html_fields(links, self._update_link_urls)

    def _update_link_urls(self, tree, links):
        if tree is None:
            return False
        modified = False
        for link in links:
            for element in tree.xpath("//a"):
                href = element.get("href")
                if href and (link["oldLink"] == href or link["oldLink"] == href + "/"):
                    if link["remove"]:
                        element.drop_tag()
                    elif href != link["newLink"]:
                        element.set("href", link["newLink"])
                    else:
                        continue
                    modified = True
        return modified

    def _update_html_fields(self, updates, update_tree):
        updates_by_field = {}
        for update in updates:
            field_name = "arch_db" if update["field"] == "arch" else update["field"]
            key = (update["res_model"], update["res_id"], field_name)
            updates_by_field.setdefault(key, []).append(update)
        for (
            model_name,
            record_id,
            field_name,
        ), field_updates in updates_by_field.items():
            record = self._get_html_record(model_name, record_id)
            if not record.has_access("write"):
                continue
            field = record._fields.get(field_name)
            if not field or field.type not in ("html", "text") or not field.store:
                continue
            tree = self._get_html_tree(record, field_name)
            modified = update_tree(tree, field_updates)
            logger.debug(
                "Website HTML update model=%s record=%s field=%s updates=%d modified=%s",
                model_name,
                record_id,
                field_name,
                len(field_updates),
                modified,
            )
            if modified:
                new_html_content = html.tostring(
                    tree, encoding="unicode", method="html"
                )
                record.write({field_name: new_html_content})

    def _get_html_tree(self, record, field_name):
        content = record[field_name]
        if not content or not str(content).strip():
            logger.debug(
                "Empty website HTML model=%s record=%s field=%s",
                record._name,
                record.id,
                field_name,
            )
            return None
        return html.fromstring(str(content))

    def _get_html_record(self, model_name, record_id):
        record = request.env[model_name].browse(record_id)
        website_id = request.env.context.get("website_id")
        if (
            model_name == "ir.ui.view"
            and website_id
            and not request.env.context.get("no_cow")
            and record.has_access("read")
        ):
            if not record.website_id and record.key:
                specific = record.with_context(active_test=False).search(
                    [("key", "=", record.key), ("website_id", "=", website_id)],
                    limit=1,
                )
                if specific:
                    logger.debug(
                        "Website HTML view resolved generic=%s specific=%s website=%s",
                        record.id,
                        specific.id,
                        website_id,
                    )
                    record = specific
        return record

    @http.route(
        ["/website/get_seo_data"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def get_seo_data(self, res_id, res_model):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            try:
                record = request.env[res_model].browse(res_id)
                record.check_access("write")
            except AccessError:
                raise werkzeug.exceptions.Forbidden from None

        fields = [
            "website_meta_title",
            "website_meta_description",
            "website_meta_keywords",
            "website_meta_og_img",
        ]
        res = {"can_edit_seo": True}
        record = request.env[res_model].browse(res_id)
        if res_model == "website.page":
            fields.extend(["website_indexed", "website_id"])
            res["website_is_published"] = record.website_published

        try:
            request.website._check_access_to_modify(record)
        except AccessError:
            res["can_edit_seo"] = False
        if request.env.user.has_group("website.group_website_restricted_editor"):
            record = record.sudo()

        res.update(record.read(fields)[0])
        res["has_social_default_image"] = request.website.has_social_default_image

        if res_model not in ("website.page", "ir.ui.view") and "seo_name" in record:
            res["seo_name_default"] = request.env["ir.http"]._slugify(
                record.display_name or ""
            )
            res["seo_name"] = (
                record.seo_name and request.env["ir.http"]._slugify(record.seo_name)
            ) or ""

        return res

    @http.route(
        ["/website/check_can_modify_any"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def check_can_modify_any(self, records):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.Forbidden
        first_error = None
        for rec in records:
            try:
                record = request.env[rec["res_model"]].browse(rec["res_id"])
                request.website._check_access_to_modify(record)
                return True
            except AccessError as e:
                if not first_error:
                    first_error = e
                continue
        if first_error:
            raise first_error
        return True

    @http.route(
        ["/google<string(length=16):key>.html"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def google_console_search(self, key, **kwargs):
        if not request.website.google_search_console:
            logger.warning("Google Search Console not enable")
            raise werkzeug.exceptions.NotFound
        gsc = request.website.google_search_console
        trusted = gsc.removeprefix("google").removesuffix(".html")

        if not consteq(key, trusted):
            logger.warning("Google Search Console %s not recognize", key)
            raise werkzeug.exceptions.NotFound

        return request.prepare_response(
            "google-site-verification: %s" % request.website.google_search_console
        )

    @http.route(
        "/website/google_maps_api_key",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def google_maps_api_key(self):
        return json.dumps(
            {"google_maps_api_key": request.website.google_maps_api_key or ""}
        )

    @http.route(
        "/website/google_font_metadata", type="jsonrpc", auth="user", website=True
    )
    def google_font_metadata(self):
        Attachment = request.env["ir.attachment"]
        metadata = Attachment.search(
            [
                ("name", "=", "googleFontMetadata"),
                ("public", "=", True),
            ],
            limit=1,
        )
        yesterday = fields.Datetime.add(fields.Datetime.now(), days=-1)
        if not metadata or metadata.write_date < yesterday:
            req = request.env["ir.egress"].request(
                "GET",
                "https://fonts.google.com/metadata/fonts",
                purpose="google_fonts",
                timeout=5,
            )
            if req.status_code != requests.codes.ok:
                return {
                    "familyMetadataList": [],
                }
            json_content = req.content
            if metadata:
                metadata.raw = json_content
            else:
                metadata = Attachment.create(
                    {
                        "public": True,
                        "name": "googleFontMetadata",
                        "type": "binary",
                        "mimetype": "application/json",
                        "raw": json_content,
                    }
                )
        return json.loads(metadata.raw)

    def _get_customize_data(self, keys, is_view_data):
        model = "ir.ui.view" if is_view_data else "ir.asset"
        Model = request.env[model].with_context(active_test=False)
        domain = Domain("key", "in", keys) & request.website.website_domain()
        return Model.search(domain)._filtered_most_specific()

    @http.route(
        ["/website/theme_customize_data_get"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def theme_customize_data_get(self, keys, is_view_data):
        records = self._get_customize_data(keys, is_view_data)
        return records.filtered("active").mapped("key")

    @http.route(
        ["/website/theme_customize_data"], type="jsonrpc", auth="user", website=True
    )
    def theme_customize_data(
        self, is_view_data, enable=None, disable=None, reset_view_arch=False
    ):
        if disable:
            records = self._get_customize_data(disable, is_view_data).filtered("active")
            if reset_view_arch:
                records.reset_arch(mode="hard")
            records.write({"active": False})

        if enable:
            records = self._get_customize_data(enable, is_view_data)
            records.filtered(lambda x: not x.active).write({"active": True})

    @http.route(
        ["/website/theme_customize_bundle_reload"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def theme_customize_bundle_reload(self):
        return {
            "web.assets_frontend": request.env["ir.qweb"]._get_asset_link_urls(
                "web.assets_frontend", request.session.debug
            ),
        }

    @http.route(
        ["/website/update_footer_template"], type="jsonrpc", auth="user", website=True
    )
    def update_footer_template(self, template_key, possible_values):
        views_enable = [template_key]
        views_disable = self.theme_customize_data_get(
            possible_values, is_view_data=True
        )

        width_views = {
            "container-fluid": "website.footer_copyright_content_width_fluid",
            "o_container_small": "website.footer_copyright_content_width_small",
        }

        new_template = self._get_customize_data([template_key], is_view_data=True)
        if not new_template or not new_template[0].arch:
            return

        tree = etree.HTML(new_template[0].arch)
        container_classes = ["container", "container-fluid", "o_container_small"]
        classes_selector = " or ".join([f"hasclass('{c}')" for c in container_classes])
        res = tree.xpath(f"//div[{classes_selector}]")

        if res:
            classes = res[0].get("class").split()
            width = next((c for c in container_classes if c in classes), False)
            if width:
                view = width_views.get(width)
                if view is not None:
                    views_enable += [view]
                views_disable += [v for k, v in width_views.items() if k != width]

        self.theme_customize_data(
            is_view_data=True,
            enable=views_enable,
            disable=views_disable,
            reset_view_arch=False,
        )

    @http.route(
        ["/website/theme_upload_font"], type="jsonrpc", auth="user", website=True
    )
    def theme_upload_font(self, name, data):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            raise werkzeug.exceptions.Forbidden

        def check_content(filename, data):
            ext = filename.rsplit(".")[-1].lower()
            if ext == "otf":
                return data.startswith(b"OTTO")
            elif ext == "woff":
                return data.startswith(b"wOFF")
            elif ext == "woff2":
                return data.startswith(b"wOF2")
            elif ext == "ttf":
                TOC_OFFSET = 12
                TOC_ENTRY_LENGTH = 16
                table_size = int.from_bytes(data[4:6], "big") * TOC_ENTRY_LENGTH
                if TOC_OFFSET + table_size > len(data):
                    return False
                mandatory_tags = {
                    b"cmap",
                    b"glyf",
                    b"head",
                    b"hhea",
                    b"hmtx",
                    b"loca",
                    b"maxp",
                    b"name",
                    b"post",
                }
                for offset in range(
                    TOC_OFFSET, TOC_OFFSET + table_size, TOC_ENTRY_LENGTH
                ):
                    tag = data[offset : offset + 4]
                    mandatory_tags.discard(tag)
                return not mandatory_tags
            return False

        def create_attachment(font, data):
            ext = font["name"].rsplit(".")[-1].lower()
            font["mimetype"] = f"font/{ext}"
            attachment = request.env["ir.attachment"].create(
                {
                    "name": font["name"],
                    "mimetype": font["mimetype"],
                    "raw": data,
                    "public": True,
                }
            )
            font["id"] = attachment.id
            font["url"] = f"/web/content/{attachment.id}/{font['name']}"
            return font

        result = []
        if len(data) > 4 * ((MAX_FONT_UPLOAD_SIZE + 2) // 3):
            raise UserError(_("Font upload exceeds maximum allowed file size"))
        try:
            binary_data = base64.b64decode(data, validate=True)
        except binascii.Error, ValueError:
            raise UserError(_("Font upload is not valid base64 data")) from None
        if len(binary_data) > MAX_FONT_UPLOAD_SIZE:
            raise UserError(_("Font upload exceeds maximum allowed file size"))
        readable_data = BytesIO(binary_data)
        if zipfile.is_zipfile(readable_data):
            with zipfile.ZipFile(readable_data, "r") as zip_file:
                entries = zip_file.infolist()
                expanded_size = sum(entry.file_size for entry in entries)
                logger.debug(
                    "Font archive entries=%d expanded_bytes=%d",
                    len(entries),
                    expanded_size,
                )
                if (
                    len(entries) > MAX_FONT_ARCHIVE_ENTRIES
                    or expanded_size > MAX_FONT_ARCHIVE_SIZE
                ):
                    raise UserError(
                        _(
                            "Font archive exceeds maximum allowed size or number of files"
                        )
                    )
                for entry in entries:
                    if entry.file_size > MAX_FONT_FILE_SIZE:
                        raise UserError(
                            _(
                                "File '%s' exceeds maximum allowed file size",
                                entry.filename,
                            )
                        )
                for entry in entries:
                    if (
                        entry.filename.rsplit(".", 1)[-1].lower()
                        not in SUPPORTED_FONT_EXTENSIONS
                        or entry.filename.startswith("__MACOSX")
                        or "/." in entry.filename
                    ):
                        continue
                    try:
                        data = zip_file.read(entry)
                    except (
                        zipfile.BadZipFile,
                        EOFError,
                        OSError,
                        RuntimeError,
                        NotImplementedError,
                        zlib.error,
                    ):
                        raise UserError(
                            _("File '%s' is corrupted", entry.filename)
                        ) from None
                    if not check_content(entry.filename, data):
                        continue
                    result.append(
                        create_attachment(
                            {
                                "name": f"{name}-{entry.filename.replace('/', '-')}",
                            },
                            data,
                        )
                    )
        elif len(binary_data) > MAX_FONT_FILE_SIZE:
            logger.debug("Oversized standalone font bytes=%d", len(binary_data))
            raise UserError(_("File '%s' exceeds maximum allowed file size", name))
        elif name.rsplit(".", 1)[
            -1
        ].lower() in SUPPORTED_FONT_EXTENSIONS and check_content(name, binary_data):
            result.append(
                create_attachment(
                    {
                        "name": name,
                    },
                    binary_data,
                )
            )
        if not result:
            raise UserError(_("File '%s' is not recognized as a font", name))
        return result

    @http.route(
        [
            "/website/action/<path_or_xml_id_or_id>",
            "/website/action/<path_or_xml_id_or_id>/<path:path>",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def actions_server(self, path_or_xml_id_or_id, **post):
        ServerActions = request.env["ir.actions.server"]
        action = action_id = None

        if isinstance(path_or_xml_id_or_id, str) and "." in path_or_xml_id_or_id:
            record = request.env.ref(path_or_xml_id_or_id, raise_if_not_found=False)
            action = (
                record.sudo()
                if record is not None and record._name == "ir.actions.server"
                else None
            )
        if not action:
            action = ServerActions.sudo().search(
                [
                    ("website_path", "=", path_or_xml_id_or_id),
                    ("website_published", "=", True),
                ],
                limit=1,
            )
        if not action:
            try:
                action_id = int(path_or_xml_id_or_id)
                action = ServerActions.sudo().browse(action_id).exists()
            except ValueError:
                pass

        if action:
            if action.state == "code" and action.website_published:
                action_res = ServerActions.browse(action.id).run()
                if isinstance(action_res, werkzeug.wrappers.Response):
                    return action_res

        return request.redirect("/")

    @http.route(
        "/website/get_assets_editor_resources",
        type="jsonrpc",
        auth="user",
        website=True,
    )
    def get_assets_editor_resources(
        self,
        key,
        get_views=True,
        get_scss=True,
        get_js=True,
        bundles=False,
        bundles_restriction=None,
        only_user_custom_files=True,
    ):
        if bundles_restriction is None:
            bundles_restriction = []
        views = (
            request.env["ir.ui.view"]
            .with_context(no_primary_children=True, __views_get_original_hierarchy=[])
            .get_related_views(key, bundles=bundles)
        )
        views = views.read(
            ["name", "id", "key", "xml_id", "arch", "active", "inherit_id"]
        )

        scss_files_data_by_bundle = []
        js_files_data_by_bundle = []

        if get_scss:
            scss_files_data_by_bundle = self._load_resources(
                "scss", views, bundles_restriction, only_user_custom_files
            )
        if get_js:
            js_files_data_by_bundle = self._load_resources(
                "js", views, bundles_restriction, only_user_custom_files
            )

        return {
            "views": (get_views and views) or [],
            "scss": (get_scss and scss_files_data_by_bundle) or [],
            "js": (get_js and js_files_data_by_bundle) or [],
        }

    def _load_resources(
        self, file_type, views, bundles_restriction, only_user_custom_files
    ):
        AssetsUtils = request.env["website.assets"]

        files_data_by_bundle = []
        t_call_assets_attribute = "t-js"
        if file_type == "scss":
            t_call_assets_attribute = "t-css"

        excluded_url_matcher = re.compile(r"^(.+/lib/.+)|(.+import_bootstrap.+\.scss)$")

        url_infos = {}
        seen_bundles = set()
        seen_urls = set()
        restricted_bundles = set(bundles_restriction)
        for v in views:
            for asset_call_node in etree.fromstring(v["arch"]).xpath(
                "//t[@t-call-assets]"
            ):
                attr = asset_call_node.get(t_call_assets_attribute)
                if attr and not json.loads(attr.lower()):
                    continue
                asset_name = asset_call_node.get("t-call-assets")
                if asset_name in seen_bundles or (
                    restricted_bundles and asset_name not in restricted_bundles
                ):
                    continue
                seen_bundles.add(asset_name)

                files_data = []
                for file_info in request.env["ir.qweb"]._get_asset_content(asset_name)[
                    0
                ]:
                    if file_info["url"].rpartition(".")[2] != file_type:
                        continue
                    url = file_info["url"]

                    if url in seen_urls or excluded_url_matcher.match(url):
                        continue

                    file_data = AssetsUtils._get_data_from_url(url)
                    if not file_data:
                        continue

                    url_infos[url] = file_data

                    if (
                        "/user_custom_" in url
                        or file_data["customized"]
                        or (file_type == "scss" and not only_user_custom_files)
                    ):
                        files_data.append(url)
                        seen_urls.add(url)

                if files_data:
                    files_data_by_bundle.append([asset_name, files_data])

        urls = []
        for bundle_data in files_data_by_bundle:
            urls += bundle_data[1]
        custom_attachments = AssetsUtils._get_custom_attachment(urls, op="in")

        for bundle_data in files_data_by_bundle:
            for i in range(len(bundle_data[1])):
                url = bundle_data[1][i]
                url_info = url_infos[url]

                content = AssetsUtils._get_content_from_url(
                    url, url_info, custom_attachments
                )

                bundle_data[1][i] = {
                    "url": "/%s/%s" % (url_info["module"], url_info["resource_path"]),
                    "arch": content,
                    "customized": url_info["customized"],
                }

        return files_data_by_bundle

    @http.route(
        "/website/field/translation/update", type="jsonrpc", auth="user", website=True
    )
    def update_field_translation(self, model, record_id, field_name, translations):
        record = request.env[model].browse(record_id)
        field = record._fields[field_name]
        source_lang = None
        if callable(field.translate):
            for translation in translations.values():
                for key, value in translation.items():
                    translation[key] = field.translate.term_converter(value)
            source_lang = record._get_base_lang()
        return record._update_field_translations(
            field_name,
            translations,
            lambda old_term: sha256(old_term.encode()).hexdigest(),
            source_lang=source_lang,
        )


class WebsiteSession(Session):
    @http.route(auth="public")
    def logout(self, *args, **kw):
        return super().logout(*args, **kw)


class WebsiteBinary(Binary):
    @http.route(
        [
            "/website/image",
            "/website/image/<xmlid>",
            "/website/image/<xmlid>/<int:width>x<int:height>",
            "/website/image/<xmlid>/<field>",
            "/website/image/<xmlid>/<field>/<int:width>x<int:height>",
            "/website/image/<model>/<id>/<field>",
            "/website/image/<model>/<id>/<field>/<int:width>x<int:height>",
        ],
        type="http",
        auth="public",
        website=False,
        multilang=False,
        readonly=True,
    )
    def website_content_image(self, id=None, max_width=0, max_height=0, **kw):
        if max_width:
            kw["width"] = max_width
        if max_height:
            kw["height"] = max_height
        if id:
            identifier, _, unique = id.partition("_")
            kw["id"] = int(identifier)
            if unique:
                kw["unique"] = unique
        return self.content_image(**kw)
