from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from types import SimpleNamespace

import pytest
from werkzeug.test import EnvironBuilder

from odoo.http._cookies import FutureResponse
from odoo.http.stream import Stream
from odoo.http.wrappers import HTTPRequest


def test_a_filename_with_line_breaks_is_served_not_a_500():
    environ = EnvironBuilder(path="/x").get_environ()
    stream = Stream(
        type="data",
        data=b"hello",
        download_name="a\r\nX-Evil: 1\n.pdf",
        mimetype="application/pdf",
        size=5,
    )

    response = stream.prepare_response(environ=environ, as_attachment=True)

    disposition = response.headers["Content-Disposition"]
    assert response.status_code == 200
    assert "\r" not in disposition and "\n" not in disposition
    assert "a__X-Evil: 1_.pdf" in disposition


def _expiry_of(header):
    attribute = next(
        part.strip()
        for part in header.split(";")
        if part.strip().startswith("Expires=")
    )
    return parsedate_to_datetime(attribute.removeprefix("Expires="))


@pytest.mark.parametrize("max_age", [0, 60])
def test_a_cookie_expiry_agrees_with_its_max_age(max_age):
    staged = FutureResponse()
    staged.set_cookie("a", "1", max_age=max_age, secure=False)
    (header,) = staged.headers.getlist("Set-Cookie")
    assert f"Max-Age={max_age}" in header
    expiry = _expiry_of(header)
    assert expiry <= datetime.now(tz=UTC) + timedelta(seconds=max_age + 5), header


def test_a_cookie_without_a_lifetime_still_defaults_to_a_year():
    staged = FutureResponse()
    staged.set_cookie("a", "1", secure=False)
    (header,) = staged.headers.getlist("Set-Cookie")
    assert "Expires=" in header and "Max-Age" not in header


def test_form_limits_reach_werkzeug_and_unknown_attributes_raise():
    httprequest = HTTPRequest(EnvironBuilder(path="/x").get_environ())
    httprequest.max_form_parts = 5
    httprequest.max_form_memory_size = 7
    wrapped = httprequest._HTTPRequest__wrapped
    assert (wrapped.max_form_parts, wrapped.max_form_memory_size) == (5, 7)
    with pytest.raises(AttributeError):
        httprequest.max_form_part = 5


class _BinaryRecord:
    _name = "x.model"
    _log_access = False

    def __init__(self, context=None):
        self.context = context or {}
        self.env = _BinaryEnv()

    def with_context(self, **overrides):
        return _BinaryRecord({**self.context, **overrides})

    def __getitem__(self, name):
        if self.context.get("bin_size") or self.context.get(f"bin_size_{name}"):
            return b"12.50 Kb"
        return b"raw file bytes"


class _BinaryEnv:
    user = SimpleNamespace(_is_public=lambda: False)

    def __getitem__(self, model):
        return SimpleNamespace(_get_content_checksum=lambda data: "etag")


def test_a_bin_size_context_never_streams_the_size_as_the_file():
    for context in ({"bin_size": True}, {"bin_size_datas": True}):
        stream = Stream.from_binary_field(_BinaryRecord(context), "datas")
        assert stream.data == b"raw file bytes", context
