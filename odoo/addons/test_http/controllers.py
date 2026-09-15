import json
import logging

import werkzeug
from psycopg.errors import SerializationFailure

from odoo import http
from odoo.db.replica import is_readonly_cursor_enabled
from odoo.exceptions import AccessError, ConcurrencyError, UserError
from odoo.http import request
from odoo.tools import replace_exceptions, str2bool

from odoo.addons.web.controllers.utils import select_db

SERIALIZATION_FAILURE = "40001"

_logger = logging.getLogger(__name__)


CT_JSON = {"Content-Type": "application/json; charset=utf-8"}
WSGI_SAFE_KEYS = {
    "PATH_INFO",
    "QUERY_STRING",
    "RAW_URI",
    "SCRIPT_NAME",
    "wsgi.url_scheme",
}


should_fail = None

reroute_upload_files = []

replay_observations = []

su_on_entry = []

promotion_upload_reads = []


class TestHttp(http.Controller):
    def _readonly(self, rule, args):
        return str2bool(request.httprequest.args.get("readonly", True))

    def _max_content_length_1kiB(self):
        return 1024

    @http.route(
        ("/test_http/greeting", "/test_http/greeting-none"),
        type="http",
        auth="none",
    )
    def greeting_none(self):
        return "Tek'ma'te"

    @http.route(
        "/test_http/greeting-public",
        type="http",
        auth="public",
        readonly=_readonly,
    )
    def greeting_public(self, readonly=True):
        assert self.env.user, "ORM should be initialized"
        assert self.env.cr.readonly == (
            str2bool(readonly) and is_readonly_cursor_enabled()
        )
        return "Tek'ma'te"

    @http.route(
        "/test_http/greeting-user", type="http", auth="user", readonly=_readonly
    )
    def greeting_user(self, readonly=True):
        assert self.env.user, "ORM should be initialized"
        assert self.env.cr.readonly == (
            str2bool(readonly) and is_readonly_cursor_enabled()
        )
        return "Tek'ma'te"

    @http.route(
        "/test_http/greeting-bearer",
        type="http",
        auth="bearer",
        readonly=_readonly,
    )
    def greeting_bearer(self, readonly=True):
        assert self.env.user, "ORM should be initialized"
        assert self.env.cr.readonly == (
            str2bool(readonly) and is_readonly_cursor_enabled()
        )
        return f"Tek'ma'te; user={self.env.user.login}"

    @http.route("/test_http/wsgi_environ", type="http", auth="none")
    def wsgi_environ(self):
        environ = {
            key: val
            for key, val in request.httprequest.environ.items()
            if (
                key.startswith(
                    ("HTTP_", "REMOTE_", "REQUEST_", "SERVER_", "werkzeug.proxy_fix.")
                )
                or key in WSGI_SAFE_KEYS
            )
        }

        return request.prepare_response(
            json.dumps(environ, indent=4), headers=list(CT_JSON.items())
        )

    @http.route("/test_http/echo-http-get", type="http", auth="none", methods=["GET"])
    def echo_http_get(self, **kwargs):
        return str(kwargs)

    @http.route(
        "/test_http/typed-echo", type="http", auth="none", methods=["GET"], typed=True
    )
    def typed_echo(self, n: int, flag: bool = False, **kwargs):
        return f"{n}:{type(n).__name__}:{flag}:{type(flag).__name__}"

    @http.route(
        "/test_http/typed-list", type="http", auth="none", methods=["GET"], typed=True
    )
    def typed_list(self, vals: list[int] | None = None):
        return repr(vals)

    @http.route("/test_http/echo-json2", type="json2", auth="none")
    def echo_json2(self, **kwargs):
        return kwargs

    @http.route(
        "/test_http/cors-resolver",
        type="http",
        auth="none",
        cors=http.resolve_cors_same_host,
        cors_credentials=True,
    )
    def cors_resolver(self):
        return "resolved"

    @http.route("/test_http/openapi.json", type="http", auth="none", methods=["GET"])
    def openapi_json(self):
        spec = http.prepare_openapi_from_map(
            request.app.nodb_routing_map, title="test_http API", typed_only=True
        )
        return request.prepare_json_response(spec)

    @http.route(
        "/test_http/echo-http-post",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def echo_http_post(self, **kwargs):
        return str(kwargs)

    @http.route(
        "/test_http/echo-http-csrf",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=True,
    )
    def echo_http_csrf(self, **kwargs):
        return str(kwargs)

    @http.route(
        "/test_http/csrf-token",
        type="http",
        auth="none",
        methods=["GET"],
        csrf=False,
    )
    def csrf_token(self, **kwargs):
        return request.csrf_token()

    @http.route(
        "/test_http/echo-http-context-lang",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def echo_http_context_lang(self, **kwargs):
        return self.env.context.get("lang", "")

    @http.route(
        "/test_http/echo-json",
        type="jsonrpc",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def echo_json(self, **kwargs):
        return kwargs

    @http.route(
        "/test_http/echo-json-context",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        csrf=False,
        readonly=True,
    )
    def echo_json_context(self, **kwargs):
        return self.env.context

    @http.route(
        "/test_http/echo-json-over-http",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def echo_json_over_http(self):
        try:
            data = request.get_json_data()
        except ValueError as exc:
            raise werkzeug.exceptions.BadRequest("Invalid JSON data") from exc
        return request.prepare_json_response(data)

    @http.route(
        '/test_http/<model("test_http.galaxy"):galaxy>',
        auth="public",
        readonly=True,
    )
    def galaxy(self, galaxy):
        if not galaxy.exists():
            raise UserError("The Ancients did not settle there.")

        return http.request.render(
            "test_http.tmpl_galaxy",
            {
                "galaxy": galaxy,
                "stargates": http.request.env["test_http.stargate"].search(
                    [("galaxy_id", "=", galaxy.id)]
                ),
            },
        )

    @http.route(
        '/test_http/<model("test_http.galaxy"):galaxy>/setname',
        methods=["GET", "POST"],
        type="http",
        auth="user",
        readonly=_readonly,
        max_content_length=_max_content_length_1kiB,
    )
    def galaxy_set_name(self, galaxy, name, readonly=True):
        galaxy.name = name
        return galaxy.name

    @http.route(
        '/test_http/<model("test_http.galaxy"):galaxy>/<model("test_http.stargate"):gate>',
        auth="user",
        readonly=True,
    )
    def stargate(self, galaxy, gate):
        if not gate.exists():
            raise UserError("The goauld destroyed the gate")

        return http.request.render("test_http.tmpl_stargate", {"gate": gate})

    @http.route("/test_http/cors_http_default", type="http", auth="none", cors="*")
    def cors_http(self):
        return "Hello"

    @http.route(
        "/test_http/cors_http_methods",
        type="http",
        auth="none",
        methods=("GET", "PUT"),
        cors="*",
    )
    def cors_http_verbs(self, **kwargs):
        return "Hello"

    @http.route("/test_http/cors_json", type="jsonrpc", auth="none", cors="*")
    def cors_json(self, **kwargs):
        return {}

    @http.route("/test_http/session_then_error", type="http", auth="none")
    def session_then_error(self, **kwargs):
        request.session["gate_address"] = "P3X-984"
        raise UserError("Chevron seven, locked.")

    @http.route("/test_http/expire_session", type="http", auth="user")
    def expire_session(self, **kwargs):
        raise http.SessionExpiredException("Gate address scrambled.")

    @http.route("/test_http/expire_session_json", type="jsonrpc", auth="user")
    def expire_session_json(self, **kwargs):
        raise http.SessionExpiredException("Gate address scrambled.")

    @http.route("/test_http/cors_http_error", type="http", auth="none", cors="*")
    def cors_http_error(self, **kwargs):
        raise UserError("Chevron seven, locked.")

    @http.route("/test_http/ensure_db", type="http", auth="none")
    def select_db_endpoint(self, db=None):
        select_db()
        assert request.db, "There should be a database"
        return request.db

    @http.route("/test_http/geoip", type="http", auth="none")
    def geoip(self):
        return json.dumps(
            {
                "city": request.geoip.city.name,
                "country_code": request.geoip.country.iso_code
                or request.geoip.continent.code,
                "country_name": request.geoip.country.name
                or request.geoip.continent.name,
                "latitude": request.geoip.location.latitude,
                "longitude": request.geoip.location.longitude,
                "region": (
                    request.geoip.subdivisions[0].iso_code
                    if request.geoip.subdivisions
                    else None
                ),
                "time_zone": request.geoip.location.time_zone,
            }
        )

    @http.route("/test_http/save_session", type="http", auth="none")
    def touch(self):
        request.session.mark_dirty()
        return ""

    @http.route("/test_http/fail", type="http", auth="none")
    def fail(self):
        _logger.error(
            "The /test_http/fail route should never be called, referrer: %s",
            http.request.httprequest.headers.get("referer"),
        )
        raise request.prepare_not_found_error()

    @http.route("/test_http/json_value_error", type="jsonrpc", auth="none")
    def json_value_error(self):
        raise ValueError("Unknown destination")

    @http.route("/test_http/hide_errors/decorator", type="http", auth="none")
    @replace_exceptions(AccessError, by=werkzeug.exceptions.NotFound())
    def hide_errors_decorator(self, error):
        if error == "AccessError":
            raise AccessError("Wrong iris code")
        if error == "UserError":
            raise UserError("Walter is AFK")

    @http.route("/test_http/hide_errors/context-manager", type="http", auth="none")
    def hide_errors_context_manager(self, error):
        with replace_exceptions(AccessError, by=werkzeug.exceptions.NotFound()):
            if error == "AccessError":
                raise AccessError("Wrong iris code")
            if error == "UserError":
                raise UserError("Walter is AFK")

    @http.route(
        "/test_http/upload_file",
        methods=["POST"],
        type="http",
        auth="none",
        csrf=False,
    )
    def upload_file_retry(self, ufile):
        global should_fail  # noqa: PLW0603  test fixture toggle, single-threaded by construction
        if should_fail is None:
            raise ValueError("should_fail should be set.")

        data = ufile.read()
        if should_fail:
            should_fail = False
            sf = SerializationFailure()
            sf.__setstate__({"pgcode": SERIALIZATION_FAILURE})
            raise sf

        return data.decode()

    @http.route(
        '/test_http/<model("test_http.galaxy"):galaxy>/su_setname',
        methods=["POST"],
        type="http",
        auth="user",
        readonly=True,
        csrf=False,
    )
    def galaxy_su_setname(self, galaxy, name):
        su_on_entry.append(request.env.su)
        request.update_env(su=True)
        galaxy.sudo().name = name
        return name

    @http.route(
        "/test_http/promotion_upload",
        methods=["POST"],
        type="http",
        auth="none",
        readonly=True,
        csrf=False,
    )
    def promotion_upload(self, ufile):
        promotion_upload_reads.append(ufile.read())
        request.env["ir.config_parameter"].sudo().set_param(
            "test_http.promotion_upload", str(len(promotion_upload_reads))
        )
        return str(len(promotion_upload_reads))

    @http.route(
        "/test_http/reroute_upload",
        methods=["POST"],
        type="http",
        auth="none",
        csrf=False,
    )
    def reroute_upload(self, ufile):
        if not request.httprequest.headers.get("X-Test-Reroute"):
            request.reroute("/test_http/reroute_upload")
        reroute_upload_files.append(request.httprequest.files["ufile"])
        return request.httprequest.files["ufile"].read().decode()

    @http.route("/test_http/retry_replay", type="http", auth="user")
    def retry_replay(self):
        global should_fail  # noqa: PLW0603  test fixture toggle, as above
        default_env = request.env.transaction.default_env
        replay_observations.append(
            {
                "su": request.env.su,
                "default_env_su": default_env.su if default_env is not None else None,
                "staged_cookies": len(
                    request.future_response.headers.getlist("Set-Cookie")
                ),
            }
        )
        request.update_env(su=True)
        request.future_response.set_cookie("probe", "1")
        if should_fail:
            should_fail = False
            e = "A dummy concurrency error occurred"
            raise ConcurrencyError(e)
        return "ok"

    @http.route("/test_http/concurrency_error", type="http", auth="none")
    def concurrency_error(self):
        global should_fail  # noqa: PLW0603  test fixture toggle, as above
        if should_fail is None:
            e = "should_fail must be set."
            raise ValueError(e)

        if should_fail:
            should_fail = False
            e = "A dummy concurrency error occurred"
            raise ConcurrencyError(e)

        return ""

    @http.route("/test_http/httprequest_attrs", type="http", auth="none")
    def request_attrs(self):
        return json.dumps(dir(request.httprequest))

    @http.route("/test_http/httprequest_environ", type="http", auth="none")
    def request_environ(self):
        return json.dumps(list(request.httprequest.environ.keys()))
