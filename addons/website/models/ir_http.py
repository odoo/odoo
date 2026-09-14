import contextlib
import functools
import logging
from zoneinfo import ZoneInfoNotFoundError

import werkzeug
from lxml import etree

import odoo
from odoo import SUPERUSER_ID, api, models, tools
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.datetime import timezone
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.safe_eval import safe_eval

from odoo.addons.http_routing.models import ir_http
from odoo.addons.portal.utils import get_url_with_params

logger = logging.getLogger(__name__)


def sitemap_qs2dom(qs, route, field="name"):
    if qs and qs.lower() not in route:
        needles = qs.strip("/").split("/")
        for segment in route.strip("/").split("/"):
            with contextlib.suppress(ValueError):
                needles.remove(segment)
        if len(needles) == 1:
            return Domain(field, "ilike", needles[0])
        else:
            return Domain.FALSE
    return Domain.TRUE


def get_request_website():
    return (request and getattr(request, "website", False)) or False


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def routing_map(self, key=None):
        return super().routing_map(key=key or self._routing_map_key())

    @api.model
    def _routing_map_key(self):
        return getattr(request, "website_routing", None) if request else None

    @classmethod
    def _slug(cls, value: models.BaseModel | tuple[int, str]) -> str:
        try:
            if value.id and value.seo_name:
                return super()._slug((value.id, value.seo_name))
        except AttributeError:
            pass
        return super()._slug(value)

    @classmethod
    def _slug_matching(cls, adapter, endpoint, **kw):
        for arg, value in kw.items():
            if isinstance(value, models.BaseModel):
                kw[arg] = value.with_context(slug_matching=True)
        qs = request.httprequest.query_string.decode("utf-8")
        return adapter.build(endpoint, kw) + ((qs and "?%s" % qs) or "")

    @classmethod
    def _url_for(cls, url_from: str, lang_code: str | None = None) -> str:
        head, hash_, fragment = (url_from or "").partition("#")
        path, qmark, query = head.partition("?")
        suffix = qmark + query + hash_ + fragment

        if (
            path
            and request.env["ir.http"]._get_rewrite_count(request.website_routing)
            and (
                len(path) > 1
                and path.startswith("/")
                and "/static/" not in path
                and not path.startswith("/web/")
            )
        ):
            rewritten, _ = request.env["ir.http"].url_rewrite(path)
            url_from = rewritten + suffix

        return super()._url_for(url_from, lang_code)

    @tools.ormcache("website_id", cache="routing")
    def _get_rewrite_count(self, website_id: int) -> int:
        rewrites = self._get_rewrites(website_id)
        return len(rewrites)

    def _get_rewrites(self, website_id):
        domain = [
            ("redirect_type", "in", ("308", "404")),
            "|",
            ("website_id", "=", False),
            ("website_id", "=", website_id),
        ]
        return {
            x.url_from: x for x in self.env["website.rewrite"].sudo().search(domain)
        }

    def _generate_routing_rules(self, modules):
        if not request:
            yield from super()._generate_routing_rules(modules)
            return
        website_id = self._routing_map_key() or False
        logger.debug("_generate_routing_rules for website: %s", website_id)
        rewrites = self._get_rewrites(website_id)
        self._get_rewrite_count.__cache__.add_value(
            self, website_id, cache_value=len(rewrites)
        )

        for url, endpoint in super()._generate_routing_rules(modules):
            if url in rewrites:
                rewrite = rewrites[url]
                url_to = rewrite.url_to
                if rewrite.redirect_type == "308":
                    logger.debug("Add rule %s for %s", url_to, website_id)
                    yield url_to, endpoint

                    if url != url_to:
                        logger.debug(
                            "Redirect from %s to %s for website %s",
                            url,
                            url_to,
                            website_id,
                        )
                        redirect_endpoint = functools.partial(endpoint)
                        functools.update_wrapper(redirect_endpoint, endpoint)
                        _slug_matching = functools.partial(
                            self._slug_matching, endpoint=endpoint
                        )
                        redirect_endpoint.routing = dict(
                            endpoint.routing, redirect_to=_slug_matching
                        )
                        yield (
                            url,
                            redirect_endpoint,
                        )
                elif rewrite.redirect_type == "404":
                    logger.debug("Return 404 for %s for website %s", url, website_id)
                    continue
            else:
                yield url, endpoint

    @classmethod
    def _get_converters(cls) -> dict[str, type]:
        return dict(
            super()._get_converters(),
            model=ModelConverter,
        )

    @classmethod
    def _get_public_users(cls):
        public_users = super()._get_public_users()
        website = (
            request.env(user=SUPERUSER_ID)["website"]
            .with_context(lang="en_US")
            .get_current_website()
        )
        if website:
            public_users.append(website._get_cached("user_id"))
        return public_users

    @classmethod
    def _auth_method_public(cls):
        if not request.session.uid:
            website = (
                request.env(user=SUPERUSER_ID)["website"]
                .with_context(lang="en_US")
                .get_current_website()
            )
            if website:
                request.update_env(user=website._get_cached("user_id"))

        if not request.env.uid:
            super()._auth_method_public()

    @classmethod
    def _register_website_track(cls, response):
        if request.env["ir.http"].is_a_bot():
            return False
        if (
            getattr(response, "status_code", 0) != 200
            or request.httprequest.headers.get("X-Disable-Tracking") == "1"
        ):
            return False
        template = False
        if hasattr(response, "_cached_page"):
            website_page, template = response._cached_page, response._cached_view_id
        elif hasattr(response, "qcontext"):
            main_object = response.qcontext.get("main_object")
            website_page = (
                getattr(main_object, "_name", False) == "website.page" and main_object
            )
            template = response.qcontext.get("response_template")
            if isinstance(template, str) and "." not in template:
                template = "website.%s" % template

        if (
            template
            and not request.env.cr.readonly
            and request.env["ir.ui.view"]._get_cached_template_info(template)["track"]
        ):
            request.env["website.visitor"]._handle_webpage_dispatch(website_page)

        return False

    @classmethod
    def _match(cls, path):
        if not hasattr(request, "website_routing"):
            website = (
                request.env["website"].with_context(lang=None).get_current_website()
            )
            request.website_routing = website.id

        return super()._match(path)

    @classmethod
    def _pre_dispatch(cls, rule, arguments):
        super()._pre_dispatch(rule, arguments)

        for record in arguments.values():
            if isinstance(record, models.BaseModel) and hasattr(
                record, "can_access_from_current_website"
            ):
                try:
                    if not record.can_access_from_current_website():
                        raise werkzeug.exceptions.NotFound
                except AccessError:
                    raise werkzeug.exceptions.NotFound from None

    @classmethod
    def _get_editor_context(cls):
        ctx = super()._get_editor_context()
        if (
            request.is_frontend_multilang
            and request.lang == request.env["ir.http"]._get_default_lang()
        ):
            ctx["edit_translations"] = False
        return ctx

    @classmethod
    def _frontend_pre_dispatch(cls):
        super()._frontend_pre_dispatch()

        if not request.env.context.get("tz"):
            geoip_tz = request.geoip.location.time_zone
            if geoip_tz:
                with contextlib.suppress(ZoneInfoNotFoundError):
                    request.update_context(tz=timezone(geoip_tz).key)

        website = request.env["website"].get_current_website()
        user = request.env.user

        website_company_id = website._get_cached("company_id")
        if (
            user.id == website._get_cached("user_id")
            or website_company_id in user._get_company_ids()
        ):
            allowed_company_ids = [website_company_id]
        else:
            allowed_company_ids = user.company_id.ids

        request.update_context(
            allowed_company_ids=allowed_company_ids,
            website_id=website.id,
            **cls._get_editor_context(),
        )

        request.website = website.with_context(request.env.context)

    @classmethod
    def _post_dispatch(cls, response):
        super()._post_dispatch(response)
        cls._register_website_track(response)

    @api.model
    def get_nearest_lang(self, lang_code):
        website_id = False
        if request and getattr(request, "is_frontend", True):
            website_id = self.env.context.get("website_id") or getattr(
                request, "website_routing", False
            )
        return super(IrHttp, self.with_context(website_id=website_id)).get_nearest_lang(
            lang_code
        )

    @api.model
    def _get_default_lang(self):
        if request and getattr(request, "is_frontend", True):
            website = self.env["website"].sudo().get_current_website()
            return self.env["res.lang"]._get_data(
                id=website._get_cached("default_lang_id")
            )
        return super()._get_default_lang()

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        installed = request.registry.loaded_modules.union(
            odoo.tools.config["server_wide_modules"]
        )
        return mods + [
            mod for mod in installed if mod == "website" or mod.startswith("website_")
        ]

    @classmethod
    def _serve_page(cls):
        req_page = request.httprequest.path
        WebsitePage = request.env["website.page"].sudo()
        page_info = WebsitePage._get_page_info(request)

        if page_info and page_info["url"] != req_page:
            logger.info(
                "Page %r not found, redirecting to existing page %r",
                req_page,
                page_info["url"],
            )
            return request.redirect(page_info["url"])

        if not page_info and req_page != "/" and req_page.endswith("/"):
            path = request.httprequest.path[:-1]
            if request.lang != request.env["ir.http"]._get_default_lang():
                path = request.env["ir.http"]._lang_url_prefix(
                    path, request.lang.url_code
                )
            if request.httprequest.query_string:
                path += "?" + request.httprequest.query_string.decode("utf-8")
            return request.redirect(path, code=301)

        if page_info:
            return WebsitePage.browse(page_info["id"])._get_response(request)

        return False

    @classmethod
    def _serve_redirect(cls):
        req_page = request.httprequest.path
        req_page_with_qs = request.httprequest.environ["REQUEST_URI"]
        domain = Domain("redirect_type", "in", ("301", "302")) & Domain(
            "url_from",
            "in",
            [req_page_with_qs, req_page.rstrip("/"), req_page + "/"],
        )
        Rewrite = request.env["website.rewrite"].sudo()
        return Rewrite.search(
            domain & Domain("website_id", "=", request.website.id),
            order="url_from DESC",
            limit=1,
        ) or Rewrite.search(
            domain & Domain("website_id", "=", False),
            order="url_from DESC",
            limit=1,
        )

    @classmethod
    def _serve_fallback(cls):
        parent = super()._serve_fallback()
        if parent:
            return parent

        cls._frontend_pre_dispatch()
        cls._handle_debug()

        website_page = cls._serve_page()
        if website_page:
            website_page.flatten()
            return website_page

        redirect = cls._serve_redirect()
        if redirect:
            return request.redirect(
                get_url_with_params(redirect.url_to, request.params),
                code=redirect.redirect_type,
                local=False,
            )
        return None

    @classmethod
    def _is_designer_404(cls, exception):
        return (
            isinstance(exception, werkzeug.exceptions.NotFound)
            and request
            and request.env.user.has_group("website.group_website_designer")
        )

    @classmethod
    def _is_password_protected_403(cls, exception):
        return (
            isinstance(exception, werkzeug.exceptions.Forbidden)
            and exception.description == "website_visibility_password_required"
        )

    @classmethod
    def _get_exception_code_values(cls, exception):
        code, values = super()._get_exception_code_values(exception)
        if cls._is_designer_404(exception):
            values["path"] = request.httprequest.path[1:]
        if request and cls._is_password_protected_403(exception):
            values["path"] = request.httprequest.path
        return (code, values)

    @classmethod
    def _get_error_template(cls, code, values):
        exception = values.get("exception")
        if cls._is_designer_404(exception):
            return "website.page_404"
        if cls._is_password_protected_403(exception):
            return "website.protected_403"
        return super()._get_error_template(code, values)

    @classmethod
    def _get_values_500_error(cls, env, values, exception):
        values = super()._get_values_500_error(env, values, exception)
        if hasattr(exception, "qweb"):
            qweb_error = exception.qweb
            exception_template = qweb_error.ref
            View = env["ir.ui.view"].sudo()
            view = exception_template and View._get_template_view(exception_template)
            if not view or (qweb_error.element and qweb_error.element in view.arch):
                values["view"] = view
            else:
                et = view.with_context(inherit_branding=False)._get_combined_arch()
                node = et.xpath(qweb_error.path) if qweb_error.path else et
                line = (
                    node is not None
                    and len(node) > 0
                    and etree.tostring(node[0], encoding="unicode")
                )
                if line:
                    values["view"] = View._views_get(view.id).filtered(
                        lambda v: line in v.arch
                    )
                    values["view"] = values["view"] and values["view"][0]
        values["editable"] = request.env.uid and request.env.user.has_group(
            "website.group_website_designer"
        )
        return values

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        geoip_country_code = request.geoip.country_code
        geoip_phone_code = (
            request.env["res.country"]._get_phone_code_by_code(geoip_country_code)
            if geoip_country_code
            else None
        )
        session_info.update(
            {
                "is_website_user": request.env.user.id == request.website.user_id.id,
                "geoip_country_code": geoip_country_code,
                "geoip_phone_code": geoip_phone_code,
                "lang_url_code": request.lang.url_code,
            }
        )
        if request.env.user.has_group("website.group_website_restricted_editor"):
            session_info.update(
                {
                    "website_id": request.website.id,
                    "website_company_id": request.website._get_cached("company_id"),
                }
            )
        session_info["bundle_params"]["website_id"] = request.website.id
        return session_info

    @classmethod
    def _is_allowed_cookie(cls, cookie_type):
        result = super()._is_allowed_cookie(cookie_type)
        if result and cookie_type == "optional":
            website = request.env["website"].get_current_website()
            if not website or not website._get_cached("cookies_bar"):
                return True
            try:
                accepted_cookie_types = json_scriptsafe.loads(
                    request.cookies.get("website_cookies_bar", "{}")
                )
            except ValueError:
                request.future_response.set_cookie("website_cookies_bar", max_age=0)
                return False

            if not isinstance(accepted_cookie_types, dict):
                request.future_response.set_cookie("website_cookies_bar", max_age=0)
                return False

            if "optional" in accepted_cookie_types:
                return accepted_cookie_types["optional"]
            return False

        return result


class ModelConverter(ir_http.ModelConverter):
    def to_url(self, value: models.BaseModel) -> str:
        if value.env.context.get("slug_matching"):
            return value.env.context.get("_converter_value", str(value.id))
        return super().to_url(value)

    def generate(self, env, args, dom=None, domain=None):
        Model = env[self.model]
        args["current_website_id"] = env["website"].get_current_website().id
        domain = safe_eval(self.domain if domain is None else domain, args)
        if dom:
            domain += dom
        yield from Model.search(domain)
