import random
from http import HTTPStatus

import pytest

from odoo.libs.http1 import HeadLimits, ProtocolError, find_head, parse_request_head

LIMITS = HeadLimits()


def parse(raw: bytes):
    span = find_head(raw, LIMITS)
    assert span is not None
    return parse_request_head(bytes(raw[span[0] : span[1]]), LIMITS)


def rejects(raw: bytes) -> HTTPStatus:
    with pytest.raises(ProtocolError) as info:
        parse(raw)
    return info.value.status


def test_origin_form_request():
    head = parse(
        b"POST /web/dataset/call_kw?a=1&b=%C3%A9 HTTP/1.1\r\n"
        b"Host: example.com:8069\r\nContent-Length: 17\r\nX-Two: a\r\nX-Two: b\r\n\r\n"
    )
    assert head.method == "POST"
    assert head.path == "/web/dataset/call_kw"
    assert head.query == "a=1&b=%C3%A9"
    assert head.host == "example.com:8069"
    assert head.content_length == 17
    assert head.version == (1, 1)
    assert head.keep_alive
    assert not head.chunked
    assert head.headers[-2:] == (("X-Two", "a"), ("X-Two", "b"))


def test_path_is_percent_decoded_to_latin1_as_pep_3333_requires():
    head = parse(b"GET /caf%C3%A9/%FF HTTP/1.1\r\nHost: x\r\n\r\n")
    assert head.path == "/caf\xc3\xa9/\xff"


def test_leading_double_slash_collapses_so_path_cannot_become_protocol_relative():
    assert (
        parse(b"GET //evil.example/x HTTP/1.1\r\nHost: x\r\n\r\n").path
        == "/evil.example/x"
    )


@pytest.mark.parametrize(
    ("target", "path"),
    [
        (b"/%2Fevil.example/x", "/evil.example/x"),
        (b"/%2f%2fevil.example", "/evil.example"),
        (b"/%2F/%2Fevil.example", "/evil.example"),
        (b"/%5Cevil.example/x", "/evil.example/x"),
        (b"/%5c%5Cevil.example", "/evil.example"),
        (b"/%5C%2Fevil.example", "/evil.example"),
        (b"/%2F%5Cevil.example", "/evil.example"),
    ],
)
def test_an_encoded_double_slash_collapses_too(target, path):
    assert parse(b"GET " + target + b" HTTP/1.1\r\nHost: x\r\n\r\n").path == path


def test_an_encoded_nul_in_the_path_is_refused():
    assert rejects(b"GET /a%00b HTTP/1.1\r\nHost: x\r\n\r\n") == HTTPStatus.BAD_REQUEST


def test_fragment_is_ignored():
    head = parse(b"GET /a?b=1#frag HTTP/1.1\r\nHost: x\r\n\r\n")
    assert (head.path, head.query) == ("/a", "b=1")


def test_absolute_form_authority_overrides_host():
    head = parse(b"GET http://real.example/p?q HTTP/1.1\r\nHost: other\r\n\r\n")
    assert (head.host, head.path, head.query) == ("real.example", "/p", "q")


def test_asterisk_form_only_for_options():
    assert parse(b"OPTIONS * HTTP/1.1\r\nHost: x\r\n\r\n").path == "*"
    assert rejects(b"GET * HTTP/1.1\r\nHost: x\r\n\r\n") == HTTPStatus.BAD_REQUEST


def test_leading_empty_lines_are_ignored():
    assert parse(b"\r\n\r\nGET / HTTP/1.1\r\nHost: x\r\n\r\n").method == "GET"


def test_bare_lf_line_endings_are_accepted_in_the_head():
    assert parse(b"GET / HTTP/1.1\nHost: x\n\n").host == "x"


def test_connection_close_and_http10_are_not_persistent():
    assert not parse(
        b"GET / HTTP/1.1\r\nHost: x\r\nConnection: Close\r\n\r\n"
    ).keep_alive
    assert not parse(b"GET / HTTP/1.0\r\n\r\n").keep_alive


def test_future_minor_version_is_served_as_http11():
    assert parse(b"GET / HTTP/1.9\r\nHost: x\r\n\r\n").version == (1, 1)


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        (b"GET / HTTP/2.0\r\nHost: x\r\n\r\n", HTTPStatus.HTTP_VERSION_NOT_SUPPORTED),
        (b"GET /\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET  / HTTP/1.1\r\nHost: x\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"G(T / HTTP/1.1\r\nHost: x\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET /a\x7fb HTTP/1.1\r\nHost: x\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET a/b HTTP/1.1\r\nHost: x\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (
            b"CONNECT host:443 HTTP/1.1\r\nHost: host\r\n\r\n",
            HTTPStatus.NOT_IMPLEMENTED,
        ),
        (b"GET / HTTP/1.1\r\nHost: x\r\nX-Bad : 1\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (
            b"GET / HTTP/1.1\r\nHost: x\r\nContent-Length : 3\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"GET / HTTP/1.1\r\nHost: x\r\nX-Fold: a\r\n b\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (b"GET / HTTP/1.1\r\nHost: x\r\nX-Nul: a\x00b\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET / HTTP/1.1\r\nHost: x\r\nX-Cr: a\rb\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET / HTTP/1.1\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET / HTTP/1.0\r\nHost: a\r\nHost: a\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET / HTTP/1.1\r\nHost: a b\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (b"GET / HTTP/1.1\r\nHost: user@a\r\n\r\n", HTTPStatus.BAD_REQUEST),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 17\r\nContent-Length: 3\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 5, 6\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: -1\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 0x10\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: +5\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: gzip, chunked\r\n\r\n",
            HTTPStatus.NOT_IMPLEMENTED,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked, gzip\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked, chunked\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: identity\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.0\r\nTransfer-Encoding: chunked\r\n\r\n",
            HTTPStatus.BAD_REQUEST,
        ),
        (
            b"POST / HTTP/1.1\r\nHost: x\r\nExpect: something-else\r\n\r\n",
            HTTPStatus.EXPECTATION_FAILED,
        ),
    ],
)
def test_rejections(raw, status):
    assert rejects(raw) == status


def test_identical_duplicate_content_length_collapses():
    head = parse(
        b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\nContent-Length: 5, 5\r\n\r\n"
    )
    assert head.content_length == 5


def test_content_length_with_chunked_uses_chunked_and_closes():
    head = parse(
        b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n"
    )
    assert head.chunked
    assert head.content_length is None
    assert head.must_close


def test_transfer_coding_names_are_case_insensitive():
    assert parse(
        b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: ChUnKeD\r\n\r\n"
    ).chunked


def test_expect_100_continue_is_honoured_only_for_http11():
    assert parse(
        b"PUT / HTTP/1.1\r\nHost: x\r\nExpect: 100-Continue\r\nContent-Length: 1\r\n\r\n"
    ).expect_continue
    assert not parse(
        b"PUT / HTTP/1.0\r\nExpect: 100-continue\r\nContent-Length: 1\r\n\r\n"
    ).expect_continue


def test_find_head_waits_for_the_blank_line():
    assert find_head(b"GET / HTTP/1.1\r\nHost: x\r\n", LIMITS) is None
    raw = b"GET / HTTP/1.1\r\nHost: x\r\n\r\nNEXT"
    assert find_head(raw, LIMITS) == (0, len(raw) - 4)


def test_a_few_empty_lines_before_the_request_line_are_ignored_and_more_refused():
    assert parse(b"\r\n" * 4 + b"GET / HTTP/1.1\r\nHost: x\r\n\r\n").method == "GET"
    with pytest.raises(ProtocolError) as info:
        find_head(b"\r\n" * 5 + b"GET / HTTP/1.1\r\nHost: x\r\n\r\n", LIMITS)
    assert info.value.status == HTTPStatus.BAD_REQUEST


def test_a_stream_of_empty_lines_is_refused_before_it_can_grow():
    with pytest.raises(ProtocolError) as info:
        find_head(bytearray(b"\r\n" * 100_000), LIMITS)
    assert info.value.status == HTTPStatus.BAD_REQUEST
    assert find_head(b"\r\n\r\n", LIMITS) is None


def test_scanning_only_new_bytes_finds_what_a_full_scan_finds():
    rng = random.Random(9112)
    alphabet = [b"\r", b"\n", b"\r\n", b"a", b": ", b"GET / HTTP/1.1"]
    for _ in range(2000):
        stream = b"GET / HTTP/1.1" + b"".join(
            rng.choice(alphabet) for _ in range(rng.randint(0, 40))
        )
        buffer = bytearray()
        scanned = 0
        position = 0
        while position < len(stream):
            step = rng.randint(1, 5)
            scanned = len(buffer)
            buffer += stream[position : position + step]
            position += step
            incremental = find_head(buffer, LIMITS, scanned)
            assert incremental == find_head(buffer, LIMITS), stream
            if incremental is not None:
                break


def test_head_size_and_count_limits():
    small = HeadLimits(max_head_bytes=64, max_header_count=2)
    with pytest.raises(ProtocolError) as info:
        find_head(b"GET /" + b"a" * 100, small)
    assert info.value.status == HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE
    raw = b"GET / HTTP/1.1\r\nHost: x\r\nA: 1\r\nB: 2\r\n\r\n"
    with pytest.raises(ProtocolError) as info:
        parse_request_head(raw[:-4], small)
    assert info.value.status == HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE


def test_a_backslash_past_the_leading_run_is_part_of_the_path():
    assert (
        parse(b"GET /web/content/7/a%5Cb.txt HTTP/1.1\r\nHost: x\r\n\r\n").path
        == "/web/content/7/a\\b.txt"
    )
