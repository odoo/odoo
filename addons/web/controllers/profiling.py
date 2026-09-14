import base64

from odoo.exceptions import UserError
from odoo.http import (
    Controller,
    Response,
    prepare_content_disposition_header,
    request,
    route,
)
from odoo.libs.documents import extension_for, mimetype_for
from odoo.libs.json import dumps as json_dumps
from odoo.libs.json import dumps_bytes as json_dumps_bytes

from ..tools import debug_log as dbg

JSON_MIMETYPE = mimetype_for("json")


def _get_profiles(profile: str, purpose: str):
    try:
        profile_ids = [int(p) for p in profile.split(",")]
    except ValueError, AttributeError:
        dbg.logic.debug("[profile:%s] %s: unparsable ids -> 404", profile, purpose)
        raise request.prepare_not_found_error() from None
    profiles = request.env["ir.profile"].browse(profile_ids).exists()
    if not profiles:
        dbg.logic.debug("[profile:%s] %s: no such profiles -> 404", profile, purpose)
        raise request.prepare_not_found_error()
    return profiles


class Profiling(Controller):
    @route("/web/set_profiling", type="http", auth="public", sitemap=False)
    def profile(
        self,
        profile: str | None = None,
        collectors: str | None = None,
        **params,
    ) -> Response:
        if collectors is not None:
            collectors = collectors.split(",")
        else:
            collectors = ["sql", "traces_async"]
        profile = profile and profile != "0"
        dbg.lifecycle.debug(
            "[profiling] set: %s enable=%s collectors=%s params=%s",
            dbg.req(),
            bool(profile),
            collectors,
            dbg.keys(params),
        )
        try:
            state = request.env["ir.profile"].set_profiling(
                profile, collectors=collectors, params=params
            )
            dbg.logic.debug("[profiling] set: state keys=%s", dbg.keys(state))
            return Response(json_dumps(state), mimetype="application/json")
        except UserError as e:
            dbg.logic.debug("[profiling] set: refused (%s)", e)
            return Response(response=f"error: {e}", status=500, mimetype="text/plain")

    @route(
        [
            "/web/speedscope/<profile>",
        ],
        type="http",
        sitemap=False,
        auth="user",
        readonly=True,
    )
    def speedscope(
        self, profile: str, action: str | bool = False, **kwargs
    ) -> Response:
        dbg.lifecycle.debug(
            "[profile:%s] speedscope: %s action=%s params=%s",
            profile,
            dbg.req(),
            action,
            dbg.keys(kwargs),
        )
        profiles = _get_profiles(profile, "speedscope")
        params = kwargs or profiles._prepare_profile_params_default()
        dbg.logic.debug(
            "[profile:%s] speedscope: %s params, %s",
            profile,
            "explicit" if kwargs else "default",
            dbg.rec(profiles),
        )
        with dbg.timer(request.env, "[profile:%s] generate speedscope", profile):
            speedscope_result = profiles._generate_speedscope(
                profiles._parse_params(params)
            )
        dbg.performance.debug(
            "[profile:%s] speedscope: %d bytes", profile, len(speedscope_result)
        )
        if action == "speedscope_download_json":
            headers = [
                ("Content-Type", JSON_MIMETYPE),
                ("X-Content-Type-Options", "nosniff"),
                (
                    "Content-Disposition",
                    prepare_content_disposition_header(
                        f"profile_{profile}.{extension_for(JSON_MIMETYPE)}"
                    ),
                ),
            ]
            return request.prepare_response(speedscope_result, headers)
        icp = request.env["ir.config_parameter"]
        context = {
            "profiles": profiles,
            "speedscope_base64": base64.b64encode(speedscope_result).decode("utf-8"),
            "url_root": request.httprequest.url_root,
            "cdn": icp.sudo().get_param(
                "speedscope_cdn",
                "https://cdn.jsdelivr.net/npm/speedscope@1.13.0/dist/release/",
            ),
        }
        with dbg.timer(request.env, "[profile:%s] render speedscope index", profile):
            response = request.render("web.view_speedscope_index", context)
        if action == "speedscope_download_html":
            response.headers["Content-Disposition"] = (
                prepare_content_disposition_header(f"profile_{profile}.html")
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Content-Type"] = "text/html"
        return response

    @route(
        [
            "/web/profile_config/<profile>",
        ],
        type="http",
        sitemap=False,
        auth="user",
        readonly=True,
    )
    def profile_config(
        self, profile: str, action: str | bool = False, **kwargs
    ) -> Response:
        dbg.lifecycle.debug(
            "[profile:%s] config: %s action=%s params=%s",
            profile,
            dbg.req(),
            action,
            dbg.keys(kwargs),
        )
        profiles = _get_profiles(profile, "config")

        if action == "memory_open":
            with dbg.timer(
                request.env, "[profile:%s] generate memory profile", profile
            ):
                memory_profile = profiles._generate_memory_profile(
                    profiles._parse_params(kwargs)
                )
            encoded_memory_profile = json_dumps_bytes(memory_profile)
            dbg.performance.debug(
                "[profile:%s] memory profile: %d bytes",
                profile,
                len(encoded_memory_profile),
            )
            context = {
                "profile": profiles,
                "memory_graph": base64.b64encode(encoded_memory_profile).decode(
                    "utf-8"
                ),
            }
            return request.render("web.view_memory", context)

        context = {
            "default_params": profiles._prepare_profile_params_default(),
            "profile_str": profile,
            "profiles": profiles,
        }
        return request.render("web.config_speedscope_index", context)
