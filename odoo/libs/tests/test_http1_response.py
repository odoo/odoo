import pytest

from odoo.libs.http1 import Framing, encode_chunk, prepare_response_head


def head(status="200 OK", headers=(), method="GET", version=(1, 1), keep_alive=True):
    return prepare_response_head(
        status, list(headers), method=method, version=version, keep_alive=keep_alive
    )


def lines(response):
    return response.data.decode("latin-1").split("\r\n")


def test_sized_response_is_persistent_and_dated():
    res = head(headers=[("Content-Type", "text/plain"), ("Content-Length", "5")])
    assert res.framing is Framing.LENGTH
    assert res.keep_alive
    assert lines(res)[0] == "HTTP/1.1 200 OK"
    assert any(line.startswith("Date: ") for line in lines(res))
    assert not any(
        line.lower().startswith(("server:", "connection:")) for line in lines(res)
    )
    assert res.data.endswith(b"\r\n\r\n")


def test_unsized_response_is_chunked_for_http11_and_close_delimited_for_http10():
    assert head().framing is Framing.CHUNKED
    assert "Transfer-Encoding: chunked" in lines(head())
    res10 = head(version=(1, 0), keep_alive=False)
    assert res10.framing is Framing.CLOSE
    assert not any("Transfer-Encoding" in line for line in lines(res10))


@pytest.mark.parametrize(
    ("status", "method"),
    [("204 No Content", "GET"), ("304 Not Modified", "GET"), ("200 OK", "HEAD")],
)
def test_bodyless_responses(status, method):
    assert head(status=status, method=method).framing is Framing.NONE


def test_application_framing_headers_are_owned_by_the_server():
    res = head(
        headers=[
            ("Transfer-Encoding", "gzip"),
            ("Keep-Alive", "timeout=5"),
            ("Connection", "close"),
            ("Content-Length", "3"),
        ]
    )
    assert res.framing is Framing.LENGTH
    assert not res.keep_alive
    assert lines(res)[1:].count("Connection: close") == 1
    assert not any(
        line.startswith(("Transfer-Encoding", "Keep-Alive")) for line in lines(res)
    )


def test_application_date_is_kept():
    res = head(
        headers=[("Date", "Mon, 01 Jan 2024 00:00:00 GMT"), ("Content-Length", "0")]
    )
    assert [line for line in lines(res) if line.startswith("Date")] == [
        "Date: Mon, 01 Jan 2024 00:00:00 GMT"
    ]


def test_upgrade_passes_hop_by_hop_headers_and_never_persists():
    res = head(
        status="101 Switching Protocols",
        headers=[("Upgrade", "websocket"), ("Connection", "Upgrade")],
    )
    assert "Connection: Upgrade" in lines(res)
    assert res.framing is Framing.NONE
    assert not res.keep_alive


def test_non_persistent_http11_says_so():
    assert "Connection: close" in lines(
        head(headers=[("Content-Length", "0")], keep_alive=False)
    )


@pytest.mark.parametrize(
    "headers",
    [
        [("Bad Name", "x")],
        [("X-Split", "a\r\nInjected: 1")],
        [("Content-Length", "abc")],
        [("Content-Length", "1"), ("Content-Length", "2")],
    ],
)
def test_invalid_response_headers_are_refused(headers):
    with pytest.raises(ValueError, match="invalid"):
        head(headers=headers)


def test_invalid_status_is_refused():
    with pytest.raises(ValueError, match="status"):
        head(status="OK")


def test_chunk_encoding():
    assert encode_chunk(b"hello") == b"5\r\nhello\r\n"
    assert encode_chunk(b"") == b""


def test_a_204_carries_no_content_length_and_a_304_keeps_its_own():
    no_content = head(status="204 No Content", headers=[("Content-Length", "0")])
    assert not any(
        line.lower().startswith("content-length") for line in lines(no_content)
    )
    assert no_content.keep_alive
    not_modified = head(status="304 Not Modified", headers=[("Content-Length", "12")])
    assert "Content-Length: 12" in lines(not_modified)
    assert not_modified.framing is Framing.NONE


@pytest.mark.parametrize("status", ["100 Continue", "103 Early Hints", "199 Custom"])
def test_an_interim_status_cannot_be_the_final_response(status):
    with pytest.raises(ValueError, match="interim"):
        head(status=status)


def test_a_switching_protocols_response_is_still_accepted():
    assert (
        head(status="101 Switching Protocols", headers=[("Upgrade", "websocket")]).code
        == 101
    )
