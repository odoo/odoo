from unittest import mock

import pytest

from odoo.http import settings as http_settings
from odoo.http.tests import _wsgi
from odoo.http.tests._wsgi import Harness, environ

ADDON = "cost_probe"

PROBE = """
from odoo.http import Controller, request, route

class Probe(Controller):
    @route("/cost/public", auth="public", methods=["GET"])
    def public(self):
        return "ok"

    @route("/cost/nodb", auth="none", methods=["GET"])
    def nodb(self):
        return "ok"

    @route("/cost/remember", auth="public", methods=["GET"])
    def remember(self):
        request.session["k"] = 1
        return "ok"
"""


@pytest.fixture(scope="module")
def addon():
    _wsgi.install_addon(ADDON, PROBE)
    yield ADDON
    _wsgi.uninstall_addon(ADDON)


@pytest.fixture
def harness(tmp_path, addon):
    return Harness(tmp_path, addon)


def _count(store, method):
    real = getattr(store, method)
    calls = []

    def counting(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    return mock.patch.object(store, method, counting), calls


def test_a_request_derives_the_settings_at_most_once_when_config_is_unchanged(
    harness,
):
    harness.serve(environ("/cost/public"))  # warm the memo
    with mock.patch.object(
        http_settings,
        "_get_settings_from_live_config",
        wraps=http_settings._get_settings_from_live_config,
    ) as derive:
        harness.serve(environ("/cost/public"))
        harness.serve(environ("/cost/nodb"))
    assert derive.call_count == 0, (
        "HttpSettings is memoised on config.generation; a request reads it "
        "several times and must derive it zero times"
    )


def test_a_request_reads_the_session_store_at_most_once(harness):
    first = harness.serve(environ("/cost/remember"))
    sid = first.cookie("session_id")
    assert sid

    reads_patch, reads = _count(harness.store, "_read")
    with reads_patch:
        harness.serve(environ("/cost/public", cookies={"session_id": sid}))
    assert len(reads) == 1, "one cookie, one read; the session is not re-fetched"

    reads_patch, reads = _count(harness.store, "_read")
    with reads_patch:
        harness.serve(environ("/cost/public"))
    assert reads == [], "no cookie, no read: a fresh session costs no I/O"


def test_a_request_asks_for_the_served_databases_at_most_once(harness):
    harness.serve(environ("/cost/public"))
    assert len(harness.db_list_calls) == 1


def test_a_request_opens_at_most_one_cursor_without_a_replica(harness):
    harness.serve(environ("/cost/public"))
    harness.serve(environ("/cost/remember"))
    assert len(harness.registry.cursors) == 2, "one cursor per database request"
    harness.served_dbs = []
    harness.serve(environ("/cost/nodb"))
    assert len(harness.registry.cursors) == 2, "none for a database-free one"
