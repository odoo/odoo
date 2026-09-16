import datetime
import logging
import re
import urllib.parse
from hashlib import md5
from itertools import islice
from pathlib import PurePosixPath
from textwrap import shorten

import requests
import werkzeug.utils
import werkzeug.wrappers
from lxml import etree, html
from werkzeug.exceptions import NotFound

import odoo
from odoo import _, fields, http, models, tools
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import SessionExpiredException, request
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet, consteq, escape_psql, py_to_js_locale
from odoo.tools import html_escape as escape
from odoo.tools.json import scriptsafe as json
from odoo.tools.translate import TRANSLATED_ELEMENTS, LazyTranslate

from .seo import WebsiteSeoRoutes
from .theme import WebsiteThemeRoutes
from odoo.addons.base.models.ir_http import EXTENSION_TO_WEB_MIMETYPES
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers.web import Home
from odoo.addons.web.controllers.binary import Binary
from odoo.addons.web.controllers.session import Session
from odoo.addons.website.tools import get_base_hostname

_lt = LazyTranslate(__name__)
logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

LOC_PER_SITEMAP = 45000
SITEMAP_CACHE_TIME = datetime.timedelta(hours=12)
MAX_PAGE_SEARCH_RESULTS = 500
# textwrap.shorten refuses a width below its placeholder, and the width comes
# straight off a public route, so it is clamped rather than trusted.
MIN_AUTOCOMPLETE_CHARS = 8
MAX_AUTOCOMPLETE_CHARS = 10000


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


def _create_sitemap_attachment(url, content, mimetype):
    _debug.lifecycle("sitemap_attachment_created", url=url, bytes=len(content))
    return (
        request.env["ir.attachment"]
        .sudo()
        .create(
            {
                "raw": content.encode(),
                "mimetype": mimetype,
                "type": "binary",
                "name": url,
                "url": url,
            }
        )
    )


class Website(WebsiteSeoRoutes, WebsiteThemeRoutes, Home):
    @http.route("/", auth="public", website=True, sitemap=True)
    def index(self, **kw):
        homepage_url = request.website._get_cached("homepage_url")
        if homepage_url and homepage_url != "/":
            _debug.logic("index_rerouted", to=homepage_url)
            request.reroute(homepage_url)

        website_page = request.env["ir.http"]._serve_page()
        if website_page:
            _debug.logic("index", by="website_page")
            return website_page

        if homepage_url and homepage_url != "/":
            _debug.logic("index_homepage_route_attempted", url=homepage_url)
            try:
                rule, args = request.env["ir.http"]._match(homepage_url)
                _debug.logic("index", by="homepage_route", url=homepage_url)
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
            _debug.logic("index", by="first_reachable_menu", url=reachable_menus[0].url)
            return request.redirect(reachable_menus[0].url)

        _debug.logic("index", by="not_found", menus=len(top_menu.child_id))
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
            _debug.logic("website_force_refused", reason="no_group", website=website_id)
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
                _debug.logic(
                    "website_force_cross_domain",
                    website=website_id,
                    host=domain_from,
                    to=domain_to,
                )
                return request.redirect(url_to, local=False)
        _debug.lifecycle("website_force", website=website_id, path=path)
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
            _debug.logic("client_action_redirect", by="backend", path=path)

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
        _debug.lifecycle("lang_changed", lang=lang, code=lang_code, to=r)
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

        dom = [("url", "=", "%s.xml" % sitemap_base_url), ("type", "=", "binary")]
        sitemap = Attachment.search(dom, limit=1)
        if sitemap:
            delta = fields.Datetime.now() - sitemap.create_date
            if delta < SITEMAP_CACHE_TIME:
                _debug.logic(
                    "sitemap", by="cache", website=current_website.id, age=delta
                )
                content = sitemap.raw

        if not content:
            dom = [
                ("type", "=", "binary"),
                ("url", "=like", "/sitemap-%d-%%" % current_website.id),
            ]
            sitemaps = Attachment.search(dom)
            _debug.lifecycle(
                "sitemap_cache_dropped",
                website=current_website.id,
                attachments=len(sitemaps),
            )
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
                    last_sitemap = _create_sitemap_attachment(
                        "%s-%d.xml" % (sitemap_base_url, pages), content, mimetype
                    )
                else:
                    break

            _debug.perf.count("sitemap_built", website=current_website.id, pages=pages)
            if not pages:
                _debug.logic("sitemap", by="empty", website=current_website.id)
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
                _create_sitemap_attachment(
                    "%s.xml" % sitemap_base_url, content, mimetype
                )

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
            _debug.logic("configurator_refused", reason="not_designer")
            raise werkzeug.exceptions.NotFound
        if request.website.configurator_done:
            _debug.logic("configurator_refused", reason="already_done")
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
            _debug.logic("social_refused", reason="unset", network=social)
            raise werkzeug.exceptions.NotFound
        _debug.logic("social_redirect", network=social)
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

        _debug.pipeline(
            "suggested_links",
            needle=needle,
            pages=len(matching_pages),
            last_modified=len(matching_last_modified),
            controllers=len(suggested_controllers),
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
        _debug.lifecycle("layout_mode_saved", view=view_id, mode=layout_mode)
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
        # Scoped to this website, like every other route here and like its own
        # sibling `get_dynamic_snippet_filters` three routes up. Without it this
        # public route answered with every website's templates: on a two-site
        # database, site A's visitors were handed the keys, names and layout of
        # templates belonging only to site B.
        domain = request.website.website_domain() & Domain(
            [["key", "ilike", ".dynamic_filter_template_"], ["type", "=", "qweb"]]
        )
        if filter_name:
            domain &= Domain("key", "ilike", escape_psql("_%s_" % filter_name))
        templates = (
            request.env["ir.ui.view"]
            .sudo()
            .search_read(domain, ["key", "name", "arch_db"])
        )

        for t in templates:
            # The first ELEMENT child, not the first child: lxml counts comments
            # and processing instructions as children, and a leading comment --
            # ordinary in a view arch -- made `children[0].attrib` empty, so the
            # snippet silently rendered with default columns, counts and thumb
            # instead of the ones its template declares. No shipped template
            # starts with one today; nothing would have said so if one did.
            first = etree.fromstring(t.pop("arch_db")).find("*")
            attribs = first.attrib if first is not None else {}
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
        offset=0,
    ):
        limit = min(max(int(limit or 0), 1), MAX_PAGE_SEARCH_RESULTS)
        offset = min(max(int(offset or 0), 0), MAX_PAGE_SEARCH_RESULTS)
        window = min(offset + limit, MAX_PAGE_SEARCH_RESULTS)
        max_nb_chars = min(
            max(int(max_nb_chars or 0), MIN_AUTOCOMPLETE_CHARS),
            MAX_AUTOCOMPLETE_CHARS,
        )
        options = self._get_page_search_options() | (options or {})
        try:
            results_count, search_results, fuzzy_term = (
                request.website._search_with_fuzzy(
                    search_type, term, window, self._get_search_order(order), options
                )
            )
        except ValueError:
            _debug.logic("autocomplete_order_rejected", order=order)
            results_count, search_results, fuzzy_term = (
                request.website._search_with_fuzzy(
                    search_type, term, window, self._get_search_order(None), options
                )
            )
        _debug.perf.count(
            "autocomplete",
            search_type=search_type,
            results=results_count,
            fuzzy=fuzzy_term or None,
        )
        if not results_count:
            return {
                "results": [],
                "results_count": 0,
                "results_reachable": 0,
                "parts": {},
                "fuzzy_search": fuzzy_term,
            }
        term = fuzzy_term or term
        highlight_terms = "|".join(map(re.escape, (term or "").split()))
        highlight_pattern = (
            re.compile(f"({highlight_terms})", re.IGNORECASE)
            if highlight_terms
            else None
        )
        search_results = request.website._search_render_results(search_results, window)

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
        # Slice to the window BEFORE rendering: every pager page used to render
        # the whole capped set through shortening, highlighting and value_to_html
        # and then throw all but its own rows away.
        results_data = results_data[offset : offset + limit]
        result = [
            self._render_autocomplete_record(
                record, max_nb_chars, highlight_pattern, options
            )
            for record in results_data
        ]

        return {
            "results": result,
            "results_count": results_count,
            "results_reachable": min(results_count, MAX_PAGE_SEARCH_RESULTS),
            "parts": {key: True for mapping in mappings for key in mapping},
            "fuzzy_search": fuzzy_term,
        }

    def _render_autocomplete_record(
        self, record, max_nb_chars, highlight_pattern, options
    ):
        mapped = {
            "_fa": record.get("_fa"),
        }
        for mapped_name, field_meta in record["_mapping"].items():
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
                value = request.env[("ir.qweb.field.%s" % field_type)].value_to_html(
                    value, opt
                )
            mapped[mapped_name] = escape(value)
        return mapped

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
            # The template reads both counts; an empty search must still supply
            # them rather than leave the names undefined.
            return request.render(
                "website.list_hybrid",
                {"search_count": 0, "search_count_reachable": 0},
            )

        step = 50
        options = self._get_hybrid_search_options(**kw)

        def fetch(offset):
            return self.autocomplete(
                search_type=search_type,
                term=search,
                order="name asc",
                limit=step,
                offset=offset,
                max_nb_chars=200,
                options=options,
            )

        # One search in the common case. Asking once for MAX_PAGE_SEARCH_RESULTS
        # rows made `len(results)` the pager's total -- a cap reported as a count
        # -- and rendered every one of them on every page view before slicing 50
        # out. The count comes back from the same search that renders the page,
        # so the pager is built from it; only a page the pager then clamps costs
        # a second search.
        try:
            requested_offset = max(int(page) - 1, 0) * step
        except TypeError, ValueError:
            requested_offset = 0
        data = fetch(requested_offset)
        search_count = data.get("results_count", 0)
        reachable = data.get("results_reachable", 0)

        pager = portal_pager(
            url="/website/search/%s" % search_type,
            url_args={"search": search},
            total=reachable,
            page=page,
            step=step,
        )
        if pager["offset"] != requested_offset:
            _debug.logic(
                "hybrid_page_clamped",
                requested=requested_offset,
                served=pager["offset"],
            )
            data = fetch(pager["offset"])

        values = {
            "pager": pager,
            "results": data.get("results", []),
            "parts": data.get("parts", {}),
            "search": search,
            "fuzzy_search": data.get("fuzzy_search"),
            "search_count": search_count,
            "search_count_reachable": reachable,
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
            _debug.lifecycle(
                "menu_bound_to_new_page", menu=menu.id, page=page["page_id"]
            )
            menu.page_id = page["page_id"]

        _debug.lifecycle(
            "pagenew", path=path, url=url, extension=ext or None, add_menu=add_menu
        )
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
                        _debug.logic(
                            "page_template_skipped",
                            reason="incompatible_theme",
                            key=template.key,
                        )
                        logger.warning(
                            "Theme not compatible with template %r: %s",
                            template.key,
                            error,
                        )
                    else:
                        raise
            if group["templates"]:
                result.append(group)
        _debug.pipeline(
            "new_page_templates",
            groups=len(result),
            templates=sum(len(group["templates"]) for group in result),
        )
        return result

    @http.route("/website/save_xml", type="jsonrpc", auth="user", website=True)
    def save_xml(self, view_id, arch):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic(
                "save_xml_refused", reason="not_restricted_editor", view=view_id
            )
            raise werkzeug.exceptions.Forbidden
        _debug.lifecycle("save_xml", view=view_id, length=len(arch or ""))
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
            _debug.logic(
                "reset_template_refused",
                reason="not_restricted_editor",
                view=view_id,
            )
            raise werkzeug.exceptions.Forbidden
        view = request.env["ir.ui.view"].browse(int(view_id))
        _debug.lifecycle("reset_template", view=view.id, key=view.key, mode=mode)
        view.with_context(website_id=None).reset_arch(mode)
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
            _debug.logic("google_console_refused", reason="not_configured")
            raise werkzeug.exceptions.NotFound
        gsc = request.website.google_search_console
        trusted = gsc.removeprefix("google").removesuffix(".html")

        if not consteq(key, trusted):
            logger.warning("Google Search Console %s not recognize", key)
            _debug.logic("google_console_refused", reason="key_mismatch")
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
            with _debug.perf("google_fonts_requested", cached=bool(metadata)) as span:
                req = request.env["ir.egress"].request(
                    "GET",
                    "https://fonts.google.com/metadata/fonts",
                    purpose="google_fonts",
                    timeout=5,
                )
                span.set(status=getattr(req, "status_code", None))
            if req.status_code != requests.codes.ok:
                _debug.logic(
                    "google_fonts_failed",
                    status=getattr(req, "status_code", None),
                )
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

        if action and action.state == "code" and action.website_published:
            with _debug.perf("server_action_run", cr=request.env.cr, action=action.id):
                action_res = ServerActions.browse(action.id).run()
            if isinstance(action_res, werkzeug.wrappers.Response):
                return action_res

        _debug.logic(
            "server_action_not_served",
            reference=path_or_xml_id_or_id,
            action=action.id if action else None,
            state=action.state if action else None,
        )
        return request.redirect("/")


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
