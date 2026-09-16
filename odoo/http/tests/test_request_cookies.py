import types
from typing import Any

import pytest
import werkzeug.datastructures

from odoo.http.request_class import Request


class _Registry(dict):
    def __init__(self, dropped):
        super().__init__()
        self.dropped = dropped
        self.calls = 0
        self["ir.http"] = self

    def _update_cookies(self, cookies):
        self.calls += 1
        for name in self.dropped:
            cookies.poplist(name)


def _request(**cookies) -> Any:
    httprequest: Any = types.SimpleNamespace(
        remote_addr=None, cookies=werkzeug.datastructures.MultiDict(cookies)
    )
    return Request(httprequest, app=None)


def test_without_a_registry_every_cookie_is_visible():
    request = _request(session_id="s", tracking="t")
    assert request.cookies["tracking"] == "t"


def test_a_read_before_the_registry_does_not_pin_the_unsanitised_answer():
    request = _request(session_id="s", tracking="t")
    assert "tracking" in request.cookies

    request.registry = _Registry({"tracking"})
    assert "tracking" not in request.cookies
    assert request.cookies["session_id"] == "s"


def test_the_sanitised_answer_is_computed_once():
    request = _request(session_id="s", tracking="t")
    registry = _Registry({"tracking"})
    request.registry = registry

    for _ in range(5):
        assert "tracking" not in request.cookies
    assert registry.calls == 1


def test_the_answer_is_still_immutable():
    request = _request(session_id="s")
    cookies = request.cookies
    assert isinstance(cookies, werkzeug.datastructures.ImmutableMultiDict)
    with pytest.raises(TypeError):
        cookies["session_id"] = "other"


def test_dropping_the_registry_again_reexposes_nothing_stale():
    request = _request(session_id="s", tracking="t")
    request.registry = _Registry({"tracking"})
    assert "tracking" not in request.cookies

    request.registry = None
    assert "tracking" in request.cookies
