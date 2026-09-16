from typing import Any

import pytest
import werkzeug.datastructures
from werkzeug.test import EnvironBuilder

from odoo.http._cookies import FutureResponse
from odoo.http.dispatcher import Dispatcher, _dispatchers
from odoo.http.request_class import Request
from odoo.http.wrappers import HTTPRequest, Response


class _FakeRequest(Request):
    session: Any

    def __init__(self):
        self.future_response = FutureResponse()
        self.env = None
        self.session = None


def test_staged_headers_override_the_response():
    req = _FakeRequest()
    req.future_response.headers.set("Content-Type", "application/json")
    response = Response("body", headers=[("Content-Type", "text/html")])

    req._update_response_from_future(response)

    assert response.headers.getlist("Content-Type") == ["application/json"]


def test_repeated_staged_headers_are_not_collapsed():
    req = _FakeRequest()
    req.future_response.headers.add("Link", "</a>; rel=preload")
    req.future_response.headers.add("Link", "</b>; rel=preload")
    response = Response("body")

    req._update_response_from_future(response)

    assert response.headers.getlist("Link") == [
        "</a>; rel=preload",
        "</b>; rel=preload",
    ]


def test_staged_cookie_keeps_cookies_set_on_the_response():
    req = _FakeRequest()
    response = Response("body")
    response.set_cookie("trusted_device", "SECRET", secure=False)
    req.future_response.set_cookie("session_id", "SID", secure=False)

    req._update_response_from_future(response)

    cookies = response.headers.getlist("Set-Cookie")
    assert any(c.startswith("trusted_device=SECRET") for c in cookies), cookies
    assert any(c.startswith("session_id=SID") for c in cookies), cookies


def test_staged_cookie_overrides_the_handlers_namesake():
    req = _FakeRequest()
    response = Response("body")
    response.set_cookie("session_id", "HANDLER", secure=False)
    response.set_cookie("content_density", "comfy", secure=False)
    req.future_response.set_cookie("session_id", "STAGED", secure=False)

    req._update_response_from_future(response)

    cookies = response.headers.getlist("Set-Cookie")
    session_cookies = [c for c in cookies if c.startswith("session_id=")]
    assert len(session_cookies) == 1, cookies
    assert session_cookies[0].startswith("session_id=STAGED"), cookies
    assert any(c.startswith("content_density=comfy") for c in cookies), cookies


def test_single_valued_staged_header_still_overrides_the_response():
    req = _FakeRequest()
    response = Response("body", headers=[("Access-Control-Allow-Origin", "evil")])
    req.future_response.headers.set("Access-Control-Allow-Origin", "*")

    req._update_response_from_future(response)

    assert response.headers.getlist("Access-Control-Allow-Origin") == ["*"]


def test_restaging_a_cookie_replaces_it_rather_than_duplicating():
    req = _FakeRequest()
    req.future_response.set_cookie("session_id", "OLD", secure=False)
    req.future_response.set_cookie("session_id", "NEW", secure=False)
    response = Response("body")

    req._update_response_from_future(response)

    cookies = response.headers.getlist("Set-Cookie")
    assert len(cookies) == 1, cookies
    assert cookies[0].startswith("session_id=NEW")


def test_set_cookie_still_accumulates():
    req = _FakeRequest()
    req.future_response.set_cookie("a", "1", secure=False)
    req.future_response.set_cookie("b", "2", secure=False)
    response = Response("body")

    req._update_response_from_future(response)

    cookies = response.headers.getlist("Set-Cookie")
    assert len(cookies) == 2
    assert cookies[0].startswith("a=1")
    assert cookies[1].startswith("b=2")


def test_reset_for_replay_drops_staged_headers():
    req = _FakeRequest()
    req.future_response.set_cookie("probe", "1", secure=False)
    assert req.future_response.headers.getlist("Set-Cookie")

    req._reset_for_replay()

    assert req.future_response.headers.getlist("Set-Cookie") == []


def test_reset_for_replay_without_env_is_a_noop_on_env():
    req = _FakeRequest()
    req._reset_for_replay()
    assert req.env is None


def test_abstract_intermediate_dispatcher_is_not_registered():
    before = dict(_dispatchers)

    class _AbstractBase(Dispatcher):
        @classmethod
        def is_compatible_with_request(cls, request):
            return False

        def dispatch(self, endpoint, args):
            return None

        def prepare_error_response(self, exc):
            return None

    assert _dispatchers == before, "an abstract base must not register itself"

    class _Concrete(_AbstractBase):
        routing_type = "_test_concrete"

    try:
        assert _dispatchers["_test_concrete"] is _Concrete
    finally:
        _dispatchers.pop("_test_concrete", None)


def _httprequest(data, content_type):
    builder = EnvironBuilder(
        method="POST", path="/x", data=data, content_type=content_type
    )
    return HTTPRequest(builder.get_environ())


def test_adopt_body_state_carries_the_parsed_form():
    original = _httprequest({"gate": "P3X-984"}, "application/x-www-form-urlencoded")
    assert original.form["gate"] == "P3X-984"

    rerouted = HTTPRequest(original.raw_environ.copy())
    rerouted._adopt_body_state(original)

    assert rerouted.form["gate"] == "P3X-984"
    assert rerouted.form is original.form


def test_adopt_body_state_copies_nothing_when_unparsed():
    original = _httprequest({"gate": "P3X-984"}, "application/x-www-form-urlencoded")
    rerouted = HTTPRequest(original.raw_environ.copy())
    rerouted._adopt_body_state(original)

    wrapped = rerouted._HTTPRequest__wrapped
    assert "form" not in wrapped.__dict__
    assert "files" not in wrapped.__dict__


@pytest.mark.parametrize("header", ["Set-Cookie", "set-cookie", "SET-COOKIE"])
def test_set_cookie_match_is_case_insensitive(header):
    req = _FakeRequest()
    req.future_response.headers.add(header, "a=1; Path=/")
    req.future_response.headers.add(header, "b=2; Path=/")
    response = Response("body")

    req._update_response_from_future(response)

    assert len(response.headers.getlist("Set-Cookie")) == 2


def test_headers_facade_accepts_werkzeug_headers():
    assert isinstance(FutureResponse().headers, werkzeug.datastructures.Headers)


def test_staged_vary_unions_with_the_handlers_own():
    req = _FakeRequest()
    response = Response("body", headers=[("Vary", "Accept-Encoding")])
    req.future_response.headers.set("Vary", "Origin")

    req._update_response_from_future(response)

    vary = response.headers.getlist("Vary")
    assert len(vary) == 1, f"must collapse to one canonical value: {vary}"
    assert {v.strip() for v in vary[0].split(",")} == {"Accept-Encoding", "Origin"}


def test_vary_union_dedupes_case_insensitively():
    req = _FakeRequest()
    response = Response("body", headers=[("Vary", "origin, Accept-Encoding")])
    req.future_response.headers.set("Vary", "Origin")

    req._update_response_from_future(response)

    assert response.headers["Vary"] == "origin, Accept-Encoding"


def test_vary_star_absorbs_named_tokens():
    req = _FakeRequest()
    response = Response("body", headers=[("Vary", "*")])
    req.future_response.headers.set("Vary", "Origin")

    req._update_response_from_future(response)

    assert response.headers["Vary"] == "*"


def test_vary_staged_alone_still_lands():
    req = _FakeRequest()
    response = Response("body")
    req.future_response.headers.set("Vary", "Origin")

    req._update_response_from_future(response)

    assert response.headers["Vary"] == "Origin"


def test_restaging_a_cookie_replaces_it_whatever_the_spacing():
    fr = FutureResponse()
    fr.headers.add("Set-Cookie", " session_id=stale; Path=/")

    fr.set_cookie("session_id", "fresh", path="/")

    staged = fr.headers.getlist("Set-Cookie")
    assert len(staged) == 1, f"the stale cookie survived: {staged}"
    assert "fresh" in staged[0]


def test_future_response_supplies_everything_werkzeug_set_cookie_touches():
    import inspect
    import re

    import werkzeug.wrappers

    source = inspect.getsource(werkzeug.wrappers.Response.set_cookie)
    touched = set(re.findall(r"self\.(\w+)", source))
    future_response = FutureResponse()

    missing = sorted(a for a in touched if not hasattr(future_response, a))
    assert not missing, (
        f"werkzeug's Response.set_cookie now reads self.{missing} too; "
        f"FutureResponse borrows that method and does not supply it."
    )
