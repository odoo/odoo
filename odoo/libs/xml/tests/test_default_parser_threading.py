import gzip
import threading

import pytest
from lxml import etree, objectify

from odoo.libs.xml.parsers import _strict_parser, fromstring

_EXTERNAL_ENTITY = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE r [ <!ENTITY x SYSTEM "file:///etc/hostname"> ]>'
    b"<r>&x;</r>"
)
_INTERNAL_ENTITY = (
    b'<?xml version="1.0"?><!DOCTYPE r [ <!ENTITY e "EXPANDED"> ]><r>&e;</r>'
)


def _in_thread(fn):
    box: dict[str, object] = {}

    def run():
        try:
            box["value"] = fn()
        except BaseException as exc:
            box["error"] = exc

    t = threading.Thread(target=run)
    t.start()
    t.join()
    return box.get("error", box.get("value"))


def _text(parse, document):
    try:
        return parse(document).text
    except etree.XMLSyntaxError:
        return "__refused__"


def test_the_stock_default_would_expand_an_internal_entity():
    stock = etree.XMLParser()
    assert etree.fromstring(_INTERNAL_ENTITY, parser=stock).text == "EXPANDED"
    assert _text(lambda d: etree.fromstring(d, parser=stock), _EXTERNAL_ENTITY) == (
        "__refused__"
    )


@pytest.mark.parametrize("document", [_EXTERNAL_ENTITY, _INTERNAL_ENTITY])
def test_no_entity_is_expanded_in_either_thread(document):
    assert _text(etree.fromstring, document) in (None, "", "__refused__")
    assert _in_thread(lambda: _text(etree.fromstring, document)) in (
        None,
        "",
        "__refused__",
    )


def test_objectify_default_is_hardened_in_both_threads():
    def parse():
        return str(objectify.fromstring(_EXTERNAL_ENTITY))

    assert parse() in ("", "None")
    assert _in_thread(parse) in ("", "None")


def test_a_per_thread_parser_object_is_not_per_thread_behaviour():
    assert id(etree.get_default_parser()) != _in_thread(
        lambda: id(etree.get_default_parser())
    )
    assert _text(etree.fromstring, _INTERNAL_ENTITY) == _in_thread(
        lambda: _text(etree.fromstring, _INTERNAL_ENTITY)
    )


def test_a_thread_that_predates_the_hardening_is_covered_too():
    parser = etree.XMLParser(resolve_entities=False)
    started, go = threading.Event(), threading.Event()
    box: dict[str, object] = {}

    def early():
        started.set()
        go.wait(5)
        box["text"] = _text(etree.fromstring, _INTERNAL_ENTITY)

    thread = threading.Thread(target=early)
    thread.start()
    started.wait(5)
    previous = etree.get_default_parser()
    etree.set_default_parser(parser)
    try:
        go.set()
        thread.join(5)
    finally:
        etree.set_default_parser(previous)
    assert box["text"] in (None, "", "__refused__")


def test_the_default_parser_is_global_state_anything_can_reset():
    previous = etree.get_default_parser()
    etree.set_default_parser(etree.XMLParser())
    try:
        assert etree.fromstring(_INTERNAL_ENTITY).text == "EXPANDED"
        assert _text(fromstring, _INTERNAL_ENTITY) in (None, "", "__refused__")
        assert _text(fromstring, _EXTERNAL_ENTITY) in (None, "", "__refused__")
    finally:
        etree.set_default_parser(previous)


def test_the_strict_parser_is_safe_to_share_across_threads():
    document = (
        b"<root>"
        + b"".join(b"<a n='%d'><b/></a>" % i for i in range(200))
        + (b"</root>")
    )
    problems: list[object] = []

    def hammer():
        try:
            lengths = {len(fromstring(document)) for _ in range(200)}
        except BaseException as exc:
            problems.append(exc)
        else:
            problems.extend(n for n in lengths if n != 200)

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert problems == []


def test_gzip_decompression_is_not_something_this_parser_prevents(tmp_path):
    path = tmp_path / "doc.xml.gz"
    path.write_bytes(gzip.compress(b"<r>" + b"<a/>" * 1000 + b"</r>"))
    assert path.stat().st_size < 1000
    assert len(etree.parse(str(path), parser=_strict_parser).getroot()) == 1000


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
