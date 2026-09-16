import logging
import re
from urllib.parse import parse_qsl, urljoin, urlsplit

import werkzeug

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.portal.controllers.portal import _get_url_with_params

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class WebsiteRoute(models.Model):
    _name = "website.route"
    _rec_name = "path"
    _description = "All Website Route"
    _order = "path"

    path = fields.Char(string="Route")

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if not self.search_count(domain, limit=1):
            _debug.logic("routes_refresh", by="search_display_name")
            self._refresh()
        return domain

    @api.model
    @api.readonly
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        result = super().name_search(
            name, domain=domain, operator=operator, limit=limit
        )
        if not result:
            _debug.logic("routes_refresh", by="name_search")
            self._refresh()
            result = super().name_search(
                name, domain=domain, operator=operator, limit=limit
            )
        return result

    def _refresh(self):
        ir_http = self.env["ir.http"]
        routes = self.search([])
        paths = {
            url
            for url, endpoint in ir_http._generate_routing_rules(
                self.pool.loaded_modules
            )
            if "GET" in (endpoint.routing.get("methods") or ["GET"])
        }
        missing_paths = paths.difference(routes.mapped("path"))
        obsolete_routes = routes.filtered(lambda route: route.path not in paths)
        _logger.debug(
            "Refreshing website.route: existing=%s current=%s new=%s obsolete=%s",
            len(routes),
            len(paths),
            len(missing_paths),
            len(obsolete_routes),
        )
        _debug.lifecycle(
            "routes_refreshed",
            existing=len(routes),
            current=len(paths),
            created=len(missing_paths),
            obsolete=len(obsolete_routes),
        )
        if missing_paths:
            self.create([{"path": path} for path in sorted(missing_paths)])
        obsolete_routes.unlink()


class WebsiteRewrite(models.Model):
    _name = "website.rewrite"
    _description = "Website rewrite"
    _order = "sequence"

    name = fields.Char(required=True)
    website_id = fields.Many2one(
        comodel_name="website",
        index=True,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)
    url_from = fields.Char(
        string="URL from",
        index=True,
    )
    route_id = fields.Many2one(comodel_name="website.route")
    url_to = fields.Char(string="URL to")
    redirect_type = fields.Selection(
        selection=[
            ("404", "404 Not Found"),
            ("301", "301 Moved permanently"),
            ("302", "302 Moved temporarily"),
            ("308", "308 Redirect / Rewrite"),
        ],
        string="Action",
        default="302",
        help="""Type of redirect/Rewrite:\n
        301 Moved permanently: The browser will keep in cache the new url.
        302 Moved temporarily: The browser will not keep in cache the new url and ask again the next time the new url.
        404 Not Found: If you want remove a specific page/controller (e.g. Ecommerce is installed, but you don't want /shop on a specific website)
        308 Redirect / Rewrite: If you want rename a controller with a new url. (Eg: /shop -> /garden - Both url will be accessible but /shop will automatically be redirected to /garden)
    """,
    )

    sequence = fields.Integer()

    @api.onchange("route_id")
    def _onchange_route_id(self):
        self.url_from = self.route_id.path
        self.url_to = self.route_id.path

    @api.constrains("url_to", "url_from", "redirect_type")
    def _check_url_to(self):
        for rewrite in self:
            if rewrite.redirect_type in ["301", "302", "308"]:
                if not rewrite.url_to:
                    _debug.logic(
                        "rewrite_refused", reason="no_url_to", rewrite=rewrite.id
                    )
                    raise ValidationError(_('"URL to" can not be empty.'))
                if not rewrite.url_from:
                    _debug.logic(
                        "rewrite_refused", reason="no_url_from", rewrite=rewrite.id
                    )
                    raise ValidationError(_('"URL from" can not be empty.'))
                if rewrite.url_to.startswith("#") or rewrite.url_from.startswith("#"):
                    _debug.logic(
                        "rewrite_refused", reason="fragment_url", rewrite=rewrite.id
                    )
                    raise ValidationError(_("URL must not start with '#'."))
                if rewrite.url_to.split("#")[0] == rewrite.url_from.split("#")[0]:
                    _debug.logic(
                        "rewrite_refused", reason="self_redirect", rewrite=rewrite.id
                    )
                    raise ValidationError(
                        _("base URL of 'URL to' should not be same as 'URL from'.")
                    )

            if rewrite.redirect_type == "308":
                rewrite._check_url_to_rewrite()

    def _check_url_to_rewrite(self):
        for rewrite in self:
            if not rewrite.url_to.startswith("/"):
                _debug.logic(
                    "rewrite_refused",
                    reason="url_to_not_absolute",
                    rewrite=rewrite.id,
                )
                raise ValidationError(_('"URL to" must start with a leading slash.'))
            for param in re.findall(r"/<.*?>", rewrite.url_from):
                if param not in rewrite.url_to:
                    _debug.logic(
                        "rewrite_refused",
                        reason="param_missing_in_url_to",
                        rewrite=rewrite.id,
                        param=param,
                    )
                    raise ValidationError(
                        _(
                            '"URL to" must contain parameter %s used in "URL from".',
                            param,
                        )
                    )
            for param in re.findall(r"/<.*?>", rewrite.url_to):
                if param not in rewrite.url_from:
                    _debug.logic(
                        "rewrite_refused",
                        reason="param_missing_in_url_from",
                        rewrite=rewrite.id,
                        param=param,
                    )
                    raise ValidationError(
                        _(
                            '"URL to" cannot contain parameter %s which is not used in "URL from".',
                            param,
                        )
                    )

            if rewrite.url_to == "/":
                _debug.logic(
                    "rewrite_refused", reason="url_to_is_root", rewrite=rewrite.id
                )
                raise ValidationError(
                    _(
                        '"URL to" cannot be set to "/". To change the homepage content, use the "Homepage URL" field in the website settings or the page properties on any custom page.'
                    )
                )

            if any(
                rule
                for rule in self.env["ir.http"].routing_map().iter_rules()
                if rule.rule.rstrip("/") == rewrite.url_to.rstrip("/")
            ):
                _debug.logic(
                    "rewrite_refused",
                    reason="url_to_is_a_route",
                    rewrite=rewrite.id,
                    url=rewrite.url_to,
                )
                raise ValidationError(_('"URL to" cannot be set to an existing page.'))

            try:
                converters = self.env["ir.http"]._get_converters()
                routing_map = werkzeug.routing.Map(
                    strict_slashes=False, converters=converters
                )
                rule = werkzeug.routing.Rule(rewrite.url_to)
                routing_map.add(rule)
            except ValueError as e:
                _debug.logic(
                    "rewrite_refused",
                    reason="url_to_unparseable",
                    rewrite=rewrite.id,
                )
                raise ValidationError(_('"URL to" is invalid: %s', e)) from e

    @staticmethod
    def _get_redirect_source_urls(path, full_path):
        """Source spellings accepted by the HTTP fallback redirect resolver."""
        return (full_path, path.rstrip("/"), path + "/")

    @api.constrains("url_to", "url_from", "redirect_type", "active", "website_id")
    def _check_no_redirect_cycle(self):
        self._check_redirect_cycles()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_redirect_cycle(self):
        self._check_redirect_cycles(excluded_ids=self.ids)

    def _check_redirect_cycles(self, excluded_ids=()):
        # Check the resulting configuration, including chains unmasked by an
        # override being archived, renamed, moved to another site, or deleted.
        # Read rows, not records. This runs as a constraint on every create,
        # write and unlink of any redirect, so it rebuilds the whole graph each
        # time; browsing the recordset cost ~19 us per existing redirect, which
        # made a row-at-a-time import quadratic in wall time and not just in
        # work. The chain walk below needs four scalars per redirect and no ORM.
        redirects = self.search_read(
            [("active", "=", True), ("id", "not in", excluded_ids)],
            ["website_id", "redirect_type", "url_from", "url_to"],
            order="id",
        )
        fallbacks_by_website = {}
        routing_by_website = {}
        for redirect in redirects:
            website_id = (redirect["website_id"] or (False,))[0]
            redirect["website_id"] = website_id
            url_from, url_to = redirect["url_from"], redirect["url_to"]
            if redirect["redirect_type"] in ("301", "302"):
                if (
                    not url_from
                    or not url_to
                    or url_from.startswith("#")
                    or url_to.startswith("#")
                    or url_from.split("#")[0] == url_to.split("#")[0]
                ):
                    # The structural constraint owns these diagnostics.
                    continue
                fallbacks_by_website.setdefault(website_id, {}).setdefault(
                    url_from, redirect
                )
            elif redirect["redirect_type"] in ("308", "404"):
                routing_by_website.setdefault(website_id, {})[url_from] = redirect
        if not fallbacks_by_website:
            return
        website_ids = self.env["website"].search([]).ids
        generic_fallbacks = fallbacks_by_website.get(False, {})
        generic_routing = routing_by_website.get(False, {})
        _logger.debug(
            "Checking redirect configuration: candidates=%s websites=%s excluded=%s",
            len(redirects),
            len(website_ids),
            len(excluded_ids),
        )
        _debug.pipeline(
            "redirect_cycle_check",
            candidates=len(redirects),
            websites=len(website_ids),
            excluded=len(excluded_ids),
            fallback_scopes=len(fallbacks_by_website),
        )
        for website_id in website_ids:
            specific_fallbacks = fallbacks_by_website.get(website_id, {})
            routing = generic_routing | routing_by_website.get(website_id, {})
            # A 308 publishes its controller at the destination. A 301/302
            # fallback there does not redirect the newly published controller.
            controller_paths = {
                redirect["url_to"]
                for redirect in routing.values()
                if redirect["redirect_type"] == "308"
            }
            checked_urls = set()
            for redirect in (generic_fallbacks | specific_fallbacks).values():
                self._check_redirect_chain(
                    redirect,
                    generic_fallbacks,
                    specific_fallbacks,
                    controller_paths,
                    website_id,
                    checked_urls,
                )

    def _check_redirect_chain(
        self,
        start,
        generic_fallbacks,
        specific_fallbacks,
        controller_paths,
        website_id,
        checked_urls,
    ):
        """`start` and the mapping values are `search_read` rows, not records."""
        current_url = start["url_from"] or ""
        # `checked_urls` holds urls already walked to a dead end in this website.
        # Re-entering the loop for one of them parses and normalises it again
        # before the memo is consulted, which is most of this constraint's cost:
        # it is called once per fallback per website, so on 1,500 redirects a
        # single create ran it 1,505 times and spent 0.56 s of 0.69 s here.
        if current_url in checked_urls:
            return
        seen = set()
        while current_url:
            # A plain path -- no scheme, authority, query or fragment -- is what
            # redirects overwhelmingly are, and for it the urlsplit/urlunsplit/
            # parse_qsl/urljoin round trip below is pure overhead: four
            # `_urlsplit` calls per hop, which profiled as 0.48 s of this
            # constraint's 0.59 s on 1,500 redirects. Anything else still takes
            # the general path.
            if (
                ":" not in current_url
                and "?" not in current_url
                and "#" not in current_url
                and not current_url.startswith("//")
            ):
                path, query = current_url, ""
            else:
                url = urlsplit(current_url)
                if url.scheme or url.netloc:
                    break
                path, query = url.path, url.query
                current_url = url._replace(fragment="").geturl()
            if path in controller_paths:
                break
            if current_url in checked_urls:
                break
            sources = sorted(
                self._get_redirect_source_urls(path, current_url), reverse=True
            )
            redirect = next(
                (
                    mapping[source]
                    for mapping in (specific_fallbacks, generic_fallbacks)
                    for source in sources
                    if source in mapping
                ),
                None,
            )
            if not redirect:
                break
            target = redirect["url_to"] or ""
            if target.split("#")[0] == redirect["url_from"].split("#")[0]:
                # Structural validation owns invalid/self-referencing URLs.
                break
            if current_url in seen:
                _logger.debug(
                    "Redirect cycle: website=%s start=%s repeated=%s hops=%s",
                    website_id,
                    start["id"],
                    redirect["id"],
                    len(seen),
                )
                _debug.logic(
                    "rewrite_refused",
                    reason="redirect_cycle",
                    rewrite=start["id"],
                    website=website_id,
                    repeated=redirect["id"],
                    hops=len(seen),
                )
                raise ValidationError(
                    _("This redirect creates a cycle with another active redirect.")
                )
            seen.add(current_url)
            if query:
                params = dict(
                    werkzeug.datastructures.MultiDict(
                        parse_qsl(query, keep_blank_values=True)
                    )
                )
                target = _get_url_with_params(target, params)
            if target.startswith("/") and not target.startswith("//"):
                # urljoin of an absolute path onto any base is that path.
                current_url = target
            else:
                current_url = urljoin(current_url, target)
        checked_urls.update(seen)

    @api.depends("redirect_type")
    def _compute_display_name(self):
        for rewrite in self:
            rewrite.display_name = f"{rewrite.redirect_type} - {rewrite.name}"

    @api.model_create_multi
    def create(self, vals_list):
        rewrites = super().create(vals_list)
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                rewrites=rewrites,
                count=len(rewrites),
                types=sorted({t or "" for t in rewrites.mapped("redirect_type")}),
            )
        if set(rewrites.mapped("redirect_type")) & {"308", "404"}:
            self._invalidate_routing()
        return rewrites

    def write(self, vals):
        _debug.lifecycle("write", rewrites=self, count=len(self), fields=sorted(vals))
        need_invalidate = set(self.mapped("redirect_type")) & {"308", "404"}
        res = super().write(vals)
        need_invalidate |= set(self.mapped("redirect_type")) & {"308", "404"}
        if need_invalidate:
            self._invalidate_routing()
        return res

    def unlink(self):
        _debug.lifecycle("unlink", rewrites=self, count=len(self))
        need_invalidate = set(self.mapped("redirect_type")) & {"308", "404"}
        res = super().unlink()
        if need_invalidate:
            self._invalidate_routing()
        return res

    def _invalidate_routing(self):
        _debug.lifecycle("routing_cache_cleared")
        self.env.registry.clear_cache("routing")

    def refresh_routes(self):
        self.env["website.route"]._refresh()

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Redirects"),
                "template": "/website/static/xls/redirects_import_template.xlsx",
            }
        ]
