import time

import pytest

from odoo.libs.http1 import (
    BodyError,
    BodyLimits,
    BufferedSource,
    ChunkedReader,
    LengthReader,
)


def source(*pieces: bytes, buffered: bytes = b"") -> BufferedSource:
    return sourced(*pieces, buffered=buffered)[0]


def sourced(
    *pieces: bytes, buffered: bytes = b""
) -> tuple[BufferedSource, list[bytes]]:
    queue = list(pieces)

    def recv(size: int) -> bytes:
        return queue.pop(0) if queue else b""

    return BufferedSource(recv, bytearray(buffered)), queue


def test_length_reader_reads_exactly_and_leaves_the_pipelined_remainder():
    src = source(b"llo wor", b"ldGET /next", buffered=b"he")
    reader = LengthReader(src, 11)
    assert reader.read() == b"hello world"
    assert reader.exhausted
    assert reader.read(10) == b""
    assert bytes(src.buffer) == b"GET /next"


def test_length_reader_truncated_body_is_an_error():
    reader = LengthReader(source(b"abc"), 10)
    with pytest.raises(BodyError):
        reader.read()


def test_length_reader_readline_and_iteration():
    reader = LengthReader(source(b"a\nbb\n", b"ccc"), 8)
    assert list(reader) == [b"a\n", b"bb\n", b"ccc"]


def test_length_reader_readinto_is_what_werkzeug_limitedstream_calls():
    reader = LengthReader(source(b"abcdef"), 6)
    buf = bytearray(4)
    assert reader.readinto(buf) == 4
    assert bytes(buf) == b"abcd"


def test_first_read_callback_fires_once_and_only_when_the_body_is_read():
    calls = []
    reader = LengthReader(source(b"xy"), 2, on_first_read=lambda: calls.append(1))
    assert calls == []
    reader.read(1)
    reader.read(1)
    assert calls == [1]


def test_chunked_reader_decodes_across_arbitrary_splits_and_trailers():
    wire = b"5\r\nhello\r\n6;ext=1\r\n world\r\n0\r\nX-Trailer: t\r\n\r\nGET /next"
    for split in range(1, len(wire)):
        src, unreceived = sourced(wire[:split], wire[split:])
        reader = ChunkedReader(src, BodyLimits())
        assert reader.read() == b"hello world"
        assert reader.exhausted
        assert bytes(src.buffer) + b"".join(unreceived) == b"GET /next"


def test_chunked_readline_spans_chunks():
    reader = ChunkedReader(source(b"2\r\nab\r\n3\r\nc\nd\r\n0\r\n\r\n"), BodyLimits())
    assert reader.readline() == b"abc\n"
    assert reader.readline() == b"d"
    assert reader.readline() == b""


@pytest.mark.parametrize(
    "wire",
    [
        b"5\nhello\r\n0\r\n\r\n",
        b"5\r\nhello\n0\r\n\r\n",
        b"zz\r\nhello\r\n0\r\n\r\n",
        b"-5\r\nhello\r\n0\r\n\r\n",
        b" 5\r\nhello\r\n0\r\n\r\n",
        b"5\r\nhelloEXTRA\r\n0\r\n\r\n",
        b"11111111111111111\r\n",
        b"5\r\nhel",
    ],
)
def test_chunked_framing_errors(wire):
    reader = ChunkedReader(source(wire), BodyLimits())
    with pytest.raises(BodyError):
        reader.read()


def test_chunked_line_and_trailer_limits():
    reader = ChunkedReader(
        source(b"5;" + b"e" * 100 + b"\r\n"), BodyLimits(max_chunk_line=32)
    )
    with pytest.raises(BodyError):
        reader.read()
    wire = b"0\r\n" + b"X: " + b"y" * 100 + b"\r\n\r\n"
    reader = ChunkedReader(source(wire), BodyLimits(max_trailer_bytes=32))
    with pytest.raises(BodyError):
        reader.read()


def test_an_overlong_chunk_line_is_refused_when_it_arrives_whole():
    wire = b"5;" + b"e" * 60_000 + b"\r\nhello\r\n0\r\n\r\n"
    reader = ChunkedReader(source(wire), BodyLimits(max_chunk_line=4096))
    with pytest.raises(BodyError, match="too long"):
        reader.read()


def test_a_chunk_line_at_the_limit_is_accepted():
    wire = b"5;" + b"e" * 28 + b"\r\nhello\r\n0\r\n\r\n"
    reader = ChunkedReader(source(wire), BodyLimits(max_chunk_line=32))
    assert reader.read() == b"hello"


def test_drain_discards_no_more_than_its_budget_and_one_byte():
    src = source(b"x" * 65536)
    reader = LengthReader(src, 65536)
    assert not reader.drain(max_bytes=100, deadline=time.monotonic() + 5)
    assert reader.bytes_read == 101


def test_drain_respects_byte_and_time_budgets():
    reader = LengthReader(source(*[b"x" * 1000] * 10), 10_000)
    assert not reader.drain(max_bytes=2_000, deadline=time.monotonic() + 5)
    reader = LengthReader(source(b"x" * 500), 500)
    assert reader.drain(max_bytes=2_000, deadline=time.monotonic() + 5)
    reader = LengthReader(source(b"x" * 500), 500)
    assert not reader.drain(max_bytes=2_000, deadline=time.monotonic() - 1)
