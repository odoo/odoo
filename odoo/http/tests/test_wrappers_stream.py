import pytest
import werkzeug.wrappers

from odoo.http.stream import Stream
from odoo.http.wrappers import Response, _Response


def test_response_load_always_returns_facade():
    raw = werkzeug.wrappers.Response("hi", status=201)
    loaded = Response.from_endpoint_result(raw)
    assert isinstance(loaded, Response)
    assert loaded.status_code == 201
    for result in ("txt", b"bytes", None):
        assert isinstance(Response.from_endpoint_result(result), Response)
    facade = Response("x", status=202)
    assert Response.from_endpoint_result(facade) is facade


def test_response_ctor_from_werkzeug_response_is_not_double_wrapped():
    r = Response(werkzeug.wrappers.Response("hi", status=203))
    assert type(r._wrapped__) is _Response
    assert r.status_code == 203


def test_response_wrapping_rejects_dropped_kwargs():
    base = Response("hi", status=200)
    with pytest.raises(TypeError, match="ignores keyword arguments"):
        Response(base, status=404)
    with pytest.raises(TypeError, match="ignores keyword arguments"):
        Response(_Response("hi"), headers=[("X", "1")])


def test_response_plain_wrapping_still_works():
    assert Response(_Response("hi", status=201)).status_code == 201
    assert Response(Response("hi", status=202)).status_code == 202


def test_response_normal_construction():
    r = Response("body", status=418, headers=[("X-A", "1")])
    assert r.status_code == 418
    assert r.headers.get("X-A") == "1"


def test_stream_read_missing_path_raises_value_error():
    with pytest.raises(ValueError, match="missing 'path'"):
        Stream(type="path").read()


def test_stream_read_missing_data_raises_value_error():
    with pytest.raises(ValueError, match="missing 'data'"):
        Stream(type="data").read()


def test_stream_read_url_raises_value_error():
    with pytest.raises(ValueError, match="Cannot read an URL"):
        Stream(type="url", url="http://x").read()


def test_stream_read_path_roundtrip(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"payload")
    assert Stream(type="path", path=str(p)).read() == b"payload"


def test_stream_rejects_unknown_kwargs():
    with pytest.raises(TypeError, match="unexpected keyword"):
        Stream(as_attatchment=True)


def test_stream_read_data_roundtrip():
    assert Stream(type="data", data=b"abc").read() == b"abc"


def test_flatten_keeps_the_template_name_in_qcontext():
    from odoo.http.wrappers import _Response

    response = _Response("body", template="website.page_x", qcontext={})
    response.response.append(b"")
    response.template = None

    assert response.qcontext["response_template"] == "website.page_x"


def test_from_binary_field_accepts_a_str_field_value():
    from odoo.http.stream import Stream

    class _Record:
        _log_access = False
        write_date = None

        def __getitem__(self, _name):
            return "aGVsbG8="

        class env:
            class _Attachment:
                @staticmethod
                def _get_content_checksum(data):
                    return "sum"

            class _User:
                @staticmethod
                def _is_public():
                    return True

            user = _User()

            def __class_getitem__(cls, _name):
                return cls._Attachment

    stream = Stream.from_binary_field(_Record(), "f")

    assert stream.data == b"hello"


def test_from_endpoint_result_keeps_a_bare_response_template():
    raw = _Response(template="web.layout", qcontext={"k": 1})
    out = Response.from_endpoint_result(raw)
    assert out.template == "web.layout"
    assert out.qcontext["k"] == 1


def test_from_endpoint_result_gives_a_werkzeug_response_fresh_qweb_state():
    out = Response.from_endpoint_result(werkzeug.wrappers.Response(b"x", status=201))
    assert out.template is None
    assert out.status_code == 201
    assert out.data == b"x"
