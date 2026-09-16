from odoo.http._cookies import FutureResponse
from odoo.http.wrappers import _Response


def test_response_set_cookie_replaces_same_key_instead_of_duplicating():
    response = _Response("body")
    response.set_cookie("foo", "1")
    response.set_cookie("foo", "2")

    staged = response.headers.getlist("Set-Cookie")
    assert len(staged) == 1
    assert staged[0].startswith("foo=2")


def test_future_response_set_cookie_still_replaces_same_key():
    response = FutureResponse()
    response.set_cookie("foo", "1")
    response.set_cookie("foo", "2")

    staged = response.headers.getlist("Set-Cookie")
    assert len(staged) == 1
    assert staged[0].startswith("foo=2")
