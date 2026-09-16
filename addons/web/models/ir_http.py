import json
import logging
import re
from typing import Any

import odoo
from odoo import api, fields, models
from odoo.http import DEFAULT_LANG, DEFAULT_MAX_CONTENT_LENGTH, request
from odoo.tools import config, html_sanitize, ormcache
from odoo.tools.misc import hmac, str2bool

_logger = logging.getLogger(__name__)

ALLOWED_DEBUG_MODES = ["", "1", "assets", "tests"]

CRAWLER_USER_AGENTS = (
    "bot",
    "crawl",
    "slurp",
    "spider",
    "curl",
    "wget",
    "facebookexternalhit",
    "whatsapp",
    "trendsmapresolver",
    "pinterest",
    "instagram",
    "google-pagerenderer",
    "preview",
)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def is_a_bot(cls) -> bool:
        user_agent = request.httprequest.user_agent.string.lower()
        return any(bot in user_agent for bot in CRAWLER_USER_AGENTS)

    @classmethod
    def _update_cookies(cls, cookies: dict) -> None:
        super()._update_cookies(cookies)
        if cids := cookies.get("cids"):
            cookies["cids"] = "-".join(cids.split(","))

    @classmethod
    def _handle_debug(cls) -> None:
        debug = request.httprequest.args.get("debug")
        if debug is not None:
            request.session.debug = ",".join(
                (
                    mode
                    if mode in ALLOWED_DEBUG_MODES
                    else "1"
                    if str2bool(mode, mode)
                    else ""
                )
                for mode in (debug or "").split(",")
            )

    @classmethod
    def _pre_dispatch(cls, rule: Any, args: dict) -> None:
        super()._pre_dispatch(rule, args)
        cls._handle_debug()

    @classmethod
    def _post_logout(cls) -> None:
        super()._post_logout()
        request.future_response.set_cookie("cids", max_age=0)
        request.future_response.set_cookie("content_density", max_age=0)
        request.future_response.set_cookie("color_scheme", max_age=0)

    def webclient_rendering_context(self) -> dict[str, Any]:
        return {
            "color_scheme": self.color_scheme(),
            "color_scheme_preference": self.color_scheme_preference(),
            "content_density": self.content_density(),
            "session_info": self.session_info(),
        }

    def color_scheme_preference(self) -> str:
        user = request.env.user
        if not user or user._is_public():
            return "light"
        return user.res_users_settings_id.color_scheme or "system"

    def color_scheme(self) -> str:
        user = request.env.user
        if not user or user._is_public():
            return "light"
        scheme = user.res_users_settings_id.color_scheme
        if scheme in ("light", "dark"):
            return scheme
        cookie_scheme = request.httprequest.cookies.get("color_scheme")
        return cookie_scheme if cookie_scheme in ("light", "dark") else "light"

    def content_density(self) -> str:
        cookie_density = request.httprequest.cookies.get("content_density")
        if cookie_density in ("compact", "condensed"):
            return cookie_density
        if not request.env.user._is_public():
            density = request.env.user.res_users_settings_id.density
            if density in ("compact", "condensed"):
                return density
        return "default"

    @api.model
    def lazy_session_info(self) -> dict[str, Any]:
        return {
            "profile_session": request.session.get("profile_session"),
            "profile_collectors": request.session.get("profile_collectors"),
            "profile_params": request.session.get("profile_params"),
        }

    def _get_session_info_base(self) -> dict[str, Any]:
        user = self.env.user
        session_uid = request.session.uid
        ir_config_sudo = self.env["ir.config_parameter"].sudo()

        try:
            cwv_sample_rate = float(
                ir_config_sudo.get_param("web.cwv.sample_rate", default="1.0"),
            )
        except ValueError, TypeError:
            cwv_sample_rate = 1.0
        cwv_sample_rate = max(0.0, min(1.0, cwv_sample_rate))

        registry_hash = hmac(
            self.env(su=True),
            "webclient-cache",
            self.env.registry.registry_sequence,
        )

        info = {
            "uid": session_uid,
            "is_system": user._is_system() if session_uid else False,
            "is_admin": user._is_admin() if session_uid else False,
            "is_public": user._is_public(),
            "is_internal_user": user._is_internal(),
            "registry_hash": registry_hash,
            "menus_cache_version": f"{registry_hash}:{session_uid}",
            "show_effect": bool(ir_config_sudo.get_param("base.show_effect")),
            "currencies": self.env["res.currency"].get_all_currencies(),
            "quick_login": str2bool(
                ir_config_sudo.get_param("web.quick_login", default=True), True
            ),
            "bundle_params": {
                "lang": request.session.context.get("lang", DEFAULT_LANG),
            },
            "test_mode": config["test_enable"],
            "cwv_sample_rate": cwv_sample_rate,
            "feature_flags": self._get_feature_flags(),
            "has_unaccent": bool(self.env.registry.has_unaccent),
        }
        if request.session.debug:
            info["bundle_params"]["debug"] = request.session.debug
        if session_uid:
            version_info = odoo.service.common.exp_version()
            info["server_version"] = version_info.get("server_version")
            info["server_version_info"] = version_info.get("server_version_info")
        return info

    _FEATURE_FLAG_PREFIX = "web.feature."

    def _get_feature_flags(self) -> dict[str, Any]:
        return dict(self._get_feature_flags_cached())

    @ormcache(cache="stable")
    def _get_feature_flags_cached(self) -> tuple[tuple[str, Any], ...]:
        rows = (
            self.env["ir.config_parameter"]
            .sudo()
            .search_fetch(
                [("key", "=like", self._FEATURE_FLAG_PREFIX + "%")],
                ["key", "value"],
            )
        )
        prefix_len = len(self._FEATURE_FLAG_PREFIX)
        return tuple(
            (row.key[prefix_len:], self._parse_feature_flag_value(row.value))
            for row in rows
        )

    _NUMERIC_RE = re.compile(r"^-?(\d+\.?\d*|\.\d+)$")

    @classmethod
    def _parse_feature_flag_value(cls, raw: str) -> Any:
        if raw == "true":
            return True
        if raw == "false":
            return False
        if raw == "null":
            return None
        trimmed = raw.strip() if raw else ""
        if not trimmed:
            return True
        if not cls._NUMERIC_RE.match(trimmed):
            return raw
        if "." in trimmed:
            return float(trimmed)
        return int(trimmed)

    def _get_config_limits(self, ir_config_sudo: Any) -> dict[str, int]:
        try:
            max_file_upload_size = int(
                ir_config_sudo.get_param(
                    "web.max_file_upload_size",
                    default=DEFAULT_MAX_CONTENT_LENGTH,
                )
            )
        except ValueError, TypeError:
            max_file_upload_size = DEFAULT_MAX_CONTENT_LENGTH
        try:
            active_ids_limit = int(
                ir_config_sudo.get_param("web.active_ids_limit", default="20000")
            )
        except ValueError, TypeError:
            active_ids_limit = 20000
        return {
            "max_file_upload_size": max_file_upload_size,
            "active_ids_limit": active_ids_limit,
        }

    def _get_user_companies_info(self) -> dict[str, Any]:
        user = self.env.user
        user_companies = (
            self.env(context=dict(self.env.context, prefetch_fields=False))[
                "res.company"
            ]
            .browse(user._get_company_ids())
            .sudo()
        )
        disallowed_ancestors = user_companies.parent_ids - user_companies
        full_hierarchy = disallowed_ancestors + user_companies

        hierarchy_ids = set(full_hierarchy._ids)
        children_in_hierarchy = {
            comp.id: [cid for cid in comp.child_ids._ids if cid in hierarchy_ids]
            for comp in full_hierarchy
        }
        return {
            "current_company": user.company_id.id,
            "allowed_companies": {
                comp.id: {
                    "id": comp.id,
                    "name": comp.name,
                    "sequence": comp.sequence,
                    "child_ids": children_in_hierarchy.get(comp.id, []),
                    "parent_id": comp.parent_id.id,
                    "currency_id": comp.currency_id.id,
                }
                for comp in user_companies
            },
            "disallowed_ancestor_companies": {
                comp.id: {
                    "id": comp.id,
                    "name": comp.name,
                    "sequence": comp.sequence,
                    "child_ids": children_in_hierarchy.get(comp.id, []),
                    "parent_id": comp.parent_id.id,
                }
                for comp in disallowed_ancestors
            },
        }

    def _get_home_menu_default(self) -> dict[str, Any] | None:
        user = self.env.user
        allowed = set(user._get_company_ids())
        selected = (
            request.httprequest.cookies.get("cids", "").replace(",", "-").split("-")
        )
        company_id = next(
            (
                int(value)
                for value in selected
                if value.isascii() and value.isdigit() and int(value) in allowed
            ),
            user.company_id.id,
        )
        return (
            self.env["res.company"].browse(company_id).homemenu_default_config or None
        )

    def session_info(self) -> dict[str, Any]:
        user = self.env.user
        session_uid = request.session.uid

        if session_uid:
            user_context = dict(self.env["res.users"].context_get())
            if user_context != request.session.context:
                request.session.context = user_context
        else:
            user_context = {}

        info = self._get_session_info_base()
        ir_config_sudo = self.env["ir.config_parameter"].sudo()
        info.update(self._get_expiration_info(ir_config_sudo))

        if "server_version" not in info:
            version_info = odoo.service.common.exp_version()
            info["server_version"] = version_info.get("server_version")
            info["server_version_info"] = version_info.get("server_version_info")

        info.update(
            self._get_config_limits(ir_config_sudo),
            user_context=user_context,
            db=self.env.cr.dbname,
            user_settings=(
                self.env["res.users.settings"]
                ._get_or_create_for_user(user)
                ._res_users_settings_format()
            ),
            homemenu_default_config=self._get_home_menu_default(),
            support_url="https://www.odoo.com/help",
            name=user.name,
            username=user.login,
            partner_write_date=fields.Datetime.to_string(user.partner_id.write_date),
            partner_display_name=user.partner_id.display_name,
            partner_id=(
                user.partner_id.id if session_uid and user.partner_id else None
            ),
            home_action_id=user.action_id.id,
            view_info=self.env["ir.ui.view"].get_view_info(),
            groups={
                "base.group_allow_export": (
                    user.has_group("base.group_allow_export") if session_uid else False
                ),
            },
        )
        info["web.base.url"] = ir_config_sudo.get_param("web.base.url", default="")

        if info["is_internal_user"]:
            info["user_companies"] = self._get_user_companies_info()
        return info

    def _get_expiration_info(self, ir_config_sudo: Any) -> dict[str, Any]:
        user = self.env.user
        if user.has_group("base.group_system"):
            warning = "admin"
        elif user._is_internal():
            warning = "user"
        else:
            return {}
        info = {
            "warning": warning,
            "expiration_date": ir_config_sudo.get_param("database.expiration_date"),
            "expiration_reason": ir_config_sudo.get_param("database.expiration_reason"),
        }
        raw_message = ir_config_sudo.get_param("sysadmin.message")
        if raw_message:
            try:
                sysadmin_message = json.loads(raw_message)
                if "message" in sysadmin_message:
                    sysadmin_message["message"] = html_sanitize(
                        sysadmin_message["message"], sanitize_tags=False
                    )
                info["sysadmin_message"] = sysadmin_message
            except ValueError, TypeError:
                _logger.exception(
                    "Failed to load sysadmin.message in ir.config_parameter"
                )
        return info

    @api.model
    def get_frontend_session_info(self) -> dict[str, Any]:
        info = self._get_session_info_base()
        info.update(
            is_website_user=self.env.user._is_public(),
            is_frontend=True,
        )
        return info

    @api.deprecated("Deprecated since 19.0, use get_all_currencies on 'res.currency'")
    def get_currencies(self) -> list[dict[str, Any]]:
        return self.env["res.currency"].get_all_currencies()
