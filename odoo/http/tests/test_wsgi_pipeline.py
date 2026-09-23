import json
import sys

import pytest

from odoo.http.tests import _wsgi
from odoo.http.tests._wsgi import Harness, environ

ADDON = "wsgi_probe"

PROBE = """
import dataclasses

import psycopg.errors

from odoo.exceptions import UserError
from odoo.http import Controller, Response, request, route


ARGUMENTS_SEEN = []
POSTCOMMIT_RAN = []


def refuse_origin(request):
    return None


@dataclasses.dataclass
class Corner:
    x: int
    y: int = 1


class Probe(Controller):
    @route("/probe/nodb", auth="none", methods=["GET"])
    def nodb(self):
        return "nodb:" + str(request.db)

    @route("/probe/public", auth="public", methods=["GET"])
    def public(self):
        return f"uid={request.env.uid} ro={request.env.cr.readonly}"

    @route("/probe/user", auth="user", methods=["GET"])
    def user(self):
        return f"uid={request.env.uid}"

    @route("/probe/remember", auth="public", methods=["GET"])
    def remember(self, value="1"):
        request.session["remembered"] = value
        return "ok"

    @route("/probe/remember-then-fail", auth="public", methods=["GET"])
    def remember_then_fail(self):
        request.session["remembered"] = "lost"
        raise UserError("no")

    @route("/probe/form", auth="public", methods=["POST"])
    def form(self, **kw):
        return "posted:" + ",".join(sorted(kw))

    @route("/probe/token", auth="public", methods=["GET"])
    def token(self):
        return request.csrf_token()

    @route("/probe/rpc", type="jsonrpc", auth="none", methods=["POST"])
    def rpc(self, a=0, b=0):
        return {"sum": a + b}

    @route("/probe/json2", type="json2", auth="none")
    def json2(self, **kw):
        return {"echo": kw}

    @route("/probe/typed", auth="none", methods=["GET"], typed=True)
    def typed(self, n: int, flag: bool = False):
        return f"{n!r}:{flag!r}"

    @route("/probe/thing/<int:thing_id>/<string:token>", auth="public")
    def thing(self, thing_id, token):
        return f"{thing_id}:{token}"

    @route("/probe/shape", type="json2", auth="none", typed=True)
    def shape(self, corners: list[Corner], label: str = "none") -> dict:
        return {"label": label, "area": sum(c.x * c.y for c in corners)}

    @route("/probe/readonly-write", auth="public", methods=["GET"], readonly=True)
    def readonly_write(self):
        request.session["attempts"] = request.session.get("attempts", 0) + 1
        if request.env.cr.readonly:
            raise psycopg.errors.ReadOnlySqlTransaction(
                "cannot execute UPDATE in a read-only transaction"
            )
        return f"promoted attempts={request.session['attempts']}"

    @route("/probe/rpc-mutates", type="jsonrpc", auth="none", methods=["POST"])
    def rpc_mutates(self, vals):
        ARGUMENTS_SEEN.append(dict(vals))
        vals["attempt"] = len(ARGUMENTS_SEEN)
        if len(ARGUMENTS_SEEN) == 1:
            raise psycopg.errors.SerializationFailure("could not serialize access")
        return vals

    @route(
        "/probe/json2-mutates-readonly",
        type="json2",
        auth="public",
        methods=["POST"],
        readonly=True,
    )
    def json2_mutates_readonly(self, vals):
        ARGUMENTS_SEEN.append(dict(vals))
        vals["attempt"] = len(ARGUMENTS_SEEN)
        if request.env.cr.readonly:
            raise psycopg.errors.ReadOnlySqlTransaction(
                "cannot execute INSERT in a read-only transaction"
            )
        return vals

    @route("/probe/cors-refused", type="json2", auth="none", cors=refuse_origin)
    def cors_refused(self):
        return {}

    @route("/probe/postcommit", auth="public", methods=["GET"])
    def postcommit(self):
        request.session["touched"] = 1
        request.env.cr.postcommit.add(lambda: POSTCOMMIT_RAN.append(True))
        return "committed"

    @route("/probe/json2-ids", type="json2", auth="none", methods=["GET"], typed=True)
    def json2_ids(self, ids: list[int]):
        return {"ids": ids}

    @route("/probe/boom", auth="public", methods=["GET"])
    def boom(self):
        raise RuntimeError("controller bug")

    @route("/probe/budgeted", auth="public", methods=["GET"], statement_timeout=2.5)
    def budgeted(self):
        return "budgeted"
"""


@pytest.fixture(scope="module")
def addon():
    _wsgi.install_addon(ADDON, PROBE)
    yield ADDON
    _wsgi.uninstall_addon(ADDON)


@pytest.fixture
def harness(tmp_path, addon):
    return Harness(tmp_path, addon)


@pytest.fixture
def replica_harness(tmp_path, addon):
    return Harness(tmp_path, addon, replica=True)


def test_a_nodb_route_is_served_without_a_registry(harness):
    harness.served_dbs = []
    served = harness.serve(environ("/probe/nodb"))
    assert served.status_code == 200
    assert served.body == b"nodb:None"
    assert harness.registry.cursors == [], "no cursor for a database-free request"
    assert served.header("X-Content-Type-Options") == "nosniff"


def test_a_public_route_runs_in_a_committed_transaction(harness):
    served = harness.serve(environ("/probe/public"))
    assert served.status_code == 200
    assert served.body == b"uid=3 ro=False"
    (cr,) = harness.registry.cursors
    assert cr.commit_count == 1 and cr.closed
    assert harness.registry.signals == 1
    assert served.cookie("session_id") is None, "an untouched session sets no cookie"


def test_a_session_write_is_persisted_only_after_commit_and_sets_the_cookie(harness):
    served = harness.serve(environ("/probe/remember", query="value=42"))
    assert served.status_code == 200
    sid = served.cookie("session_id")
    assert sid, "a dirty new session publishes its cookie"
    assert harness.store.get(sid)["remembered"] == "42"

    again = harness.serve(environ("/probe/public", cookies={"session_id": sid}))
    assert again.status_code == 200
    assert again.cookie("session_id") is None, "the same session, nothing changed"


def test_a_failed_handler_rolls_the_session_back_with_the_transaction(harness):
    served = harness.serve(environ("/probe/remember-then-fail"))
    assert served.status_code == 422, served.body
    assert served.cookie("session_id") is None
    (cr,) = harness.registry.cursors
    assert cr.commit_count == 0 and cr.rollbacks >= 1
    assert isinstance(harness.ir_http.errors_handled[-1], Exception)


def test_a_user_route_without_a_login_is_a_redirect_to_login(harness):
    served = harness.serve(environ("/probe/user"))
    assert served.status_code == 303
    assert "/web/login" in (served.header("Location") or "")


def test_a_logged_in_session_reaches_a_user_route(harness):
    sid = harness.login(7)
    served = harness.serve(environ("/probe/user", cookies={"session_id": sid}))
    assert served.status_code == 200
    assert served.body == b"uid=7"


def test_an_unmatched_path_is_negotiated_by_media_type(harness):
    html = harness.serve(environ("/nope"))
    assert html.status_code == 404
    assert (html.header("Content-Type") or "").startswith("text/html")

    as_json = harness.serve(
        environ("/nope", content_type="application/json", body=b"{}")
    )
    assert as_json.status_code == 404
    assert (as_json.header("Content-Type") or "").startswith("application/problem+json")
    payload = json.loads(as_json.body)
    assert payload["name"].endswith("NotFound")
    assert payload["type"] == "about:blank"
    assert payload["title"] == "Not Found"
    assert payload["status"] == 404
    assert payload["detail"] == payload["message"]
    assert [type(e).__name__ for e in harness.ir_http.errors_handled] == [
        "NotFound",
        "NotFound",
    ], "the fallback 404 is rendered by ir.http after the rollback, like any error"


def test_a_form_post_without_a_csrf_token_is_refused_and_with_one_accepted(harness):
    refused = harness.serve(environ("/probe/form", "POST", body=b"a=1", cookies=None))
    assert refused.status_code == 400
    assert b"CSRF" in refused.body or b"Session expired" in refused.body

    token_response = harness.serve(environ("/probe/token"))
    sid = token_response.cookie("session_id")
    token = token_response.body.decode()
    accepted = harness.serve(
        environ(
            "/probe/form",
            "POST",
            body=f"a=1&csrf_token={token}".encode(),
            cookies={"session_id": sid},
        )
    )
    assert accepted.status_code == 200
    assert accepted.body == b"posted:a"


def test_jsonrpc_and_json2_round_trip(harness):
    rpc = harness.serve(
        environ(
            "/probe/rpc",
            "POST",
            body=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "call",
                    "params": {"a": 2, "b": 3},
                }
            ).encode(),
            content_type="application/json",
        )
    )
    assert rpc.status_code == 200
    assert json.loads(rpc.body) == {"jsonrpc": "2.0", "id": 9, "result": {"sum": 5}}

    j2 = harness.serve(
        environ(
            "/probe/json2",
            "POST",
            body=json.dumps({"x": 1}).encode(),
            content_type="application/json",
        )
    )
    assert j2.status_code == 200
    assert json.loads(j2.body) == {"echo": {"x": 1}}


def test_a_typed_route_coerces_and_refuses(harness):
    ok = harness.serve(environ("/probe/typed", query="n=7&flag=yes"))
    assert ok.status_code == 200 and ok.body == b"7:True"
    bad = harness.serve(environ("/probe/typed", query="n=seven"))
    assert bad.status_code == 400
    missing = harness.serve(environ("/probe/typed"))
    assert missing.status_code == 400


def test_the_matched_path_variables_are_on_the_request_before_authentication(harness):
    """An auth method that resolves the caller from the path (`auth="receiver"`)
    reads `request.path_args`; it is set before `_authenticate`, not at dispatch."""
    ok = harness.serve(environ("/probe/thing/7/abc"))
    assert ok.status_code == 200 and ok.body == b"7:abc"
    assert harness.ir_http.path_args_at_authentication == {
        "thing_id": 7,
        "token": "abc",
    }


def test_a_json2_body_is_built_into_dataclasses_and_refused_when_malformed(harness):
    ok = harness.serve(
        environ(
            "/probe/shape",
            "POST",
            body=json.dumps({"corners": [{"x": 2, "y": 3}, {"x": "4"}]}).encode(),
            content_type="application/json",
        )
    )
    assert ok.status_code == 200, ok.body
    assert json.loads(ok.body) == {"label": "none", "area": 10}

    bad = harness.serve(
        environ(
            "/probe/shape",
            "POST",
            body=json.dumps({"corners": [{"x": 1, "z": 9}]}).encode(),
            content_type="application/json",
        )
    )
    assert bad.status_code == 400
    assert b"unknown field" in bad.body


def test_a_readonly_route_that_writes_is_replayed_read_write(replica_harness):
    served = replica_harness.serve(environ("/probe/readonly-write"))
    assert served.status_code == 200, served.body
    assert served.body == b"promoted attempts=1", (
        "the rollback restored the session, so the replay saw a fresh count"
    )
    modes = [cr.readonly for cr in replica_harness.registry.cursors]
    assert modes == [True, False], "one read-only attempt, one read/write replay"
    ro, rw = replica_harness.registry.cursors
    assert ro.closed and rw.commit_count == 1


def test_without_a_replica_a_readonly_route_runs_read_write_at_once(harness):
    served = harness.serve(environ("/probe/readonly-write"))
    assert served.status_code == 200
    assert [cr.readonly for cr in harness.registry.cursors] == [False]


@pytest.fixture
def arguments_seen(addon):
    seen = sys.modules[f"odoo.addons.{addon}"].ARGUMENTS_SEEN
    seen.clear()
    yield seen
    seen.clear()


def test_a_retried_jsonrpc_call_replays_the_body_the_client_sent(
    harness, arguments_seen
):
    served = harness.serve(
        environ(
            "/probe/rpc-mutates",
            "POST",
            body=json.dumps(
                {"jsonrpc": "2.0", "id": 1, "params": {"vals": {"qty": 1}}}
            ).encode(),
            content_type="application/json",
        )
    )
    assert served.status_code == 200, served.body
    assert arguments_seen == [{"qty": 1}, {"qty": 1}], (
        "the serialization retry must not see what the failed attempt wrote "
        "into its arguments"
    )
    assert json.loads(served.body)["result"] == {"qty": 1, "attempt": 2}


def test_a_promoted_json2_call_replays_the_body_the_client_sent(
    replica_harness, arguments_seen
):
    served = replica_harness.serve(
        environ(
            "/probe/json2-mutates-readonly",
            "POST",
            body=json.dumps({"vals": {"qty": 1}}).encode(),
            content_type="application/json",
        )
    )
    assert served.status_code == 200, served.body
    assert arguments_seen == [{"qty": 1}, {"qty": 1}]
    assert [cr.readonly for cr in replica_harness.registry.cursors] == [True, False]


def test_a_controller_bug_is_a_500_built_by_ir_http(harness):
    served = harness.serve(environ("/probe/boom"))
    assert served.status_code == 500
    assert type(harness.ir_http.errors_handled[-1]).__name__ == "RuntimeError"
    (cr,) = harness.registry.cursors
    assert cr.commit_count == 0


def test_a_route_statement_budget_is_set_on_the_request_transaction(harness):
    served = harness.serve(environ("/probe/budgeted"))
    assert served.status_code == 200
    (cr,) = harness.registry.cursors
    assert cr.statement_timeouts == [2.5]

    plain = harness.serve(environ("/probe/public"))
    assert plain.status_code == 200
    assert harness.registry.cursors[-1].statement_timeouts == [], (
        "no route budget and no dispatcher default: the server default stands"
    )


def test_every_response_carries_a_request_id_and_a_well_formed_one_is_kept(harness):
    minted = harness.serve(environ("/probe/public"))
    assert minted.status_code == 200
    rid = minted.header("X-Request-Id")
    assert rid and len(rid) >= 12

    kept = harness.serve(
        environ("/probe/public", headers={"X-Request-Id": "trace-42.abc:def"})
    )
    assert kept.header("X-Request-Id") == "trace-42.abc:def"

    replaced = harness.serve(
        environ("/probe/public", headers={"X-Request-Id": "bad id\nwith junk"})
    )
    assert replaced.header("X-Request-Id") not in (None, "bad id\nwith junk")

    error = harness.serve(environ("/probe/boom"))
    assert error.status_code == 500 and error.header("X-Request-Id")
    harness.served_dbs = []
    nodb = harness.serve(environ("/probe/nodb"))
    assert nodb.header("X-Request-Id")


def test_a_rejected_method_never_reaches_the_router(harness):
    served = harness.serve(environ("/probe/public", "TRACE"))
    assert served.status_code == 405
    assert harness.registry.cursors == []


def test_the_header_database_conflicting_with_the_session_is_forbidden(harness):
    sid = harness.login(7)
    served = harness.serve(
        environ(
            "/probe/user",
            cookies={"session_id": sid},
            headers={"X-Odoo-Database": "other"},
        )
    )
    assert served.status_code == 403


def test_a_preflight_from_a_refused_origin_grants_no_headers(harness):
    served = harness.serve(
        environ(
            "/probe/cors-refused",
            "OPTIONS",
            headers={
                "Origin": "https://elsewhere.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Evil, Authorization",
            },
        )
    )
    assert served.status_code == 204
    assert served.header("Access-Control-Allow-Origin") is None
    assert served.header("Access-Control-Allow-Headers") is None
    assert served.header("Access-Control-Max-Age") is None
    assert served.header("Vary") == "Origin"


def test_a_session_store_outage_after_commit_spares_the_response_and_later_hooks(
    harness,
):
    from unittest import mock

    import odoo.db
    from odoo.http._session_store import PostgresSessionStore
    from odoo.http.session import Session

    ran = sys.modules[f"odoo.addons.{ADDON}"].POSTCOMMIT_RAN
    ran.clear()
    harness.app.__dict__["session_store"] = PostgresSessionStore("unreachable", Session)

    def refuse(dbname):
        raise odoo.db.PoolError("session database unreachable")

    with mock.patch.object(odoo.db, "db_connect", refuse):
        served = harness.serve(environ("/probe/postcommit"))

    assert served.status_code == 200, served.body
    assert served.body == b"committed"
    assert ran == [True], "a hook registered after the session's must still run"


def test_a_repeated_query_parameter_reaches_a_json2_list_whole(harness):
    served = harness.serve(environ("/probe/json2-ids", query="ids=1&ids=2&ids=3"))
    assert served.status_code == 200, served.body
    assert json.loads(served.body) == {"ids": [1, 2, 3]}


@pytest.mark.parametrize(
    ("catalogue", "path", "status"),
    [([_wsgi.DB], "/probe/json2", 503), ([], "/probe/public", 404)],
    ids=["listed", "gone"],
)
def test_an_unreachable_database_is_a_503_only_while_it_still_exists(
    harness, catalogue, path, status
):
    from unittest import mock

    import psycopg

    def refuse(*args, **kwargs):
        raise psycopg.OperationalError("connection refused")

    with (
        mock.patch.object(harness.registry, "cursor", refuse),
        mock.patch("odoo.http._serve.list_dbs", return_value=catalogue),
        mock.patch("odoo.http._serve.Registry.clear_database_state"),
        mock.patch("odoo.http._serve.close_db"),
    ):
        served = harness.serve(
            environ(path, "POST", body=b"{}", content_type="application/json")
            if path == "/probe/json2"
            else environ(path)
        )
    assert served.status_code == status, served.body
    if status == 503:
        assert served.header("Retry-After") == "5"
        assert json.loads(served.body)["status"] == 503
