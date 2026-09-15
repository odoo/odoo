import inspect
import io
import logging
import threading
import zipfile
from collections import OrderedDict
from datetime import date, datetime
from typing import Any

import pytest
from dateutil.relativedelta import relativedelta
from lxml import etree
from PIL import Image

from odoo.libs._vendor.useragents import UserAgentParser
from odoo.libs.barcode import is_barcode_encoding_valid
from odoo.libs.collections.frozen_dict import freehash
from odoo.libs.collections.misc import Collector
from odoo.libs.collections.ordered_set import LastOrderedSet, OrderedSet
from odoo.libs.colors.conversions import get_saturation, hex_to_rgb
from odoo.libs.datetime.tz import ZoneInfoNotFoundError, timezone
from odoo.libs.email.parsing import formataddr
from odoo.libs.filesystem.mimetypes import guess_mimetype
from odoo.libs.filesystem.osutil import zip_dir
from odoo.libs.hashing import (
    _MT_MIN_BYTES,
    CONTENT_DIGEST_LEN,
    cache_hash,
    content_hash,
    content_hash_file,
    prepare_cache_hasher,
    prepare_content_hasher,
    update_from_file,
)
from odoo.libs.image.utils import (
    IMAGE_MAX_RESOLUTION,
    ImageProcess,
    ImageTooLargeError,
    NotWebpError,
    get_webp_size,
)
from odoo.libs.json.orjson_wrapper import dumps as orjson_dumps
from odoo.libs.locale.number_format import format_number
from odoo.libs.logging import lower_logging, mute_logger
from odoo.libs.lru import LRU
from odoo.libs.numbers.float_utils import float_invert
from odoo.libs.password import CryptContext
from odoo.libs.sql.builder import SQL
from odoo.libs.sql.utils import reverse_order
from odoo.libs.text.address import street_split
from odoo.libs.text.html import html2plaintext, html_sanitize
from odoo.libs.text.strings import is_encodable
from odoo.libs.web.urls import urljoin
from odoo.libs.xml.dsig import (
    EXC_C14N_ALGORITHM,
    XmlSigError,
    _get_c14n_params_from_transforms,
    update_reference_digests,
)


class TestGuessMimetypeDefault:
    def test_default_returned_for_unidentifiable_content(self):
        assert guess_mimetype(b"\0" * 32, default="image/png") == "image/png"

    def test_default_does_not_override_a_real_identification(self):
        assert guess_mimetype(b"%PDF-1.7\n", default="image/png") == "application/pdf"

    def test_default_defaults_to_octet_stream(self):
        assert guess_mimetype(b"\0" * 32) == "application/octet-stream"


class TestCheckBarcodeEncoding:
    @pytest.mark.parametrize("encoding", ["ean8", "ean13", "gtin14", "upca", "sscc"])
    def test_empty_barcode(self, encoding):
        assert is_barcode_encoding_valid("", encoding) is False

    def test_known_good_values_still_pass(self):
        assert is_barcode_encoding_valid("20220006", "ean8")
        assert is_barcode_encoding_valid("2022071416014", "ean13")

    def test_ean13_leading_zero_still_rejected(self):
        assert is_barcode_encoding_valid("0022071416014", "ean13") is False


class TestLowerLoggingReentrancy:
    def test_nested_reuse_restores_handlers(self):
        root = logging.getLogger()
        original = root.handlers[:]
        ll = lower_logging(logging.ERROR, logging.WARNING)
        try:
            with ll, ll:
                assert root.handlers == [ll]
            assert root.handlers == original
        finally:
            root.handlers = original

    def test_nested_reuse_does_not_recurse_on_emit(self):
        root = logging.getLogger()
        original = root.handlers[:]
        ll = lower_logging(logging.WARNING, logging.INFO)
        try:
            with ll, ll:
                logging.getLogger("odoo.test.reentrant").error("boom")
            assert ll.had_error_log
        finally:
            root.handlers = original

    def test_inner_block_does_not_erase_an_outer_error(self):
        root = logging.getLogger()
        original = root.handlers[:]
        ll = lower_logging(logging.WARNING, logging.INFO)
        try:
            with ll:
                logging.getLogger("odoo.test.reentrant").error("boom")
                with ll:
                    pass
                assert ll.had_error_log
        finally:
            root.handlers = original

    def test_matches_mute_logger_semantics(self):
        logger = logging.getLogger("odoo.test.mute")
        logger.handlers, logger.propagate = [], True
        with mute_logger("odoo.test.mute") as _outer:
            pass
        assert logger.propagate is True


class TestLastOrderedSet:
    def test_update_moves_existing_element_last(self):
        s = LastOrderedSet([1, 2, 3])
        s.update([1])
        assert list(s) == [2, 3, 1]

    def test_update_matches_add(self):
        by_add = LastOrderedSet([1, 2, 3])
        for elem in (1, 4, 2):
            by_add.add(elem)
        by_update = LastOrderedSet([1, 2, 3])
        by_update.update([1, 4, 2])
        assert list(by_add) == list(by_update) == [3, 1, 4, 2]


class TestHexToRgb:
    def test_missing_hash_is_parsed_not_misread(self):
        assert hex_to_rgb("FF0000") == (255, 0, 0)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("#FF0000", (255, 0, 0)),
            ("#f00", (255, 0, 0)),
            ("#123456", (0x12, 0x34, 0x56)),
            ("#abc", (0xAA, 0xBB, 0xCC)),
        ],
    )
    def test_accepted_forms(self, value, expected):
        assert hex_to_rgb(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "#",
            "#12345",
            "nope",
            "#gg0000",
            "#1234567",
            "#ff0000ff",
            "#f00f",
        ],
    )
    def test_rejected_forms(self, value):
        with pytest.raises(ValueError, match="not a hexadecimal color"):
            hex_to_rgb(value)


class TestFloatInvert:
    def test_zero_raises_a_named_error(self):
        with pytest.raises(ZeroDivisionError, match="cannot invert 0"):
            float_invert(0.0)

    def test_known_inversions(self):
        assert float_invert(0.01) == 100.0
        assert float_invert(0.05) == 20.0


class TestStreetSplit:
    def test_street_number2_is_stripped(self):
        assert street_split("Main Street 123 - Apt B  ") == {
            "street_name": "Main Street",
            "street_number": "123",
            "street_number2": "Apt B",
        }


class TestGetWebpSizeRobustness:
    @staticmethod
    def _webp(subtype: bytes, tail: bytes) -> bytes:
        return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBPVP8" + subtype + tail

    @pytest.mark.parametrize(
        "buf",
        [
            b"RIFF\x00\x00\x00\x00WEBPVP8 ",
            b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 12,
            b"RIFF\x00\x00\x00\x00WEBPVP8X" + b"\x00" * 10,
            b"RIFF\x00\x00\x00\x00WEBPVP8L\x00\x00\x00\x00\x2f\x00\x00",
        ],
    )
    def test_truncated_returns_none(self, buf):
        assert get_webp_size(buf) is None

    @pytest.mark.parametrize("buf", [b"\x89PNG\r\n\x1a\n", b"RIFF\x00\x00\x00\x00WE"])
    def test_non_webp_raises(self, buf):
        with pytest.raises(NotWebpError):
            get_webp_size(buf)

    def test_valid_lossless_1x1_still_parsed(self):
        buf = (
            b"RIFF"
            + b"\x00" * 4
            + b"WEBPVP8L"
            + b"\x00" * 4
            + bytes([0x2F, 0x00, 0x00, 0x00, 0x00])
        )
        assert get_webp_size(buf) == (1, 1)


class TestUserAgentParseCache:
    UAS = [
        (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
        ),
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "curl/8.5.0",
        "",
    ]

    def test_cached_equals_uncached(self):
        parser = UserAgentParser()
        fresh = UserAgentParser()
        for ua in self.UAS:
            assert parser(ua) == fresh._parse(ua)

    def test_repeated_call_is_a_cache_hit(self):
        parser = UserAgentParser()
        ua = self.UAS[0]
        parser(ua)
        before = parser._parse_cached.cache_info().hits
        parser(ua)
        assert parser._parse_cached.cache_info().hits == before + 1


class TestOrjsonDumpsIntrospectable:
    def test_signature_is_introspectable(self):
        params = list(inspect.signature(orjson_dumps).parameters)
        assert params == ["obj", "default", "ensure_ascii", "option"]

    def test_ensure_ascii_true_is_rejected(self):
        with pytest.raises(ValueError, match="ASCII"):
            orjson_dumps({"a": 1}, ensure_ascii=True)


class TestFloatSplitSign:
    def test_str_form_keeps_sign_for_subunit_negative(self):
        from odoo.libs.numbers.float_utils import float_split_str

        assert float_split_str(-0.05, 2) == ("-0", "05")
        assert float_split_str(-2.675, 2) == ("-2", "68")

    def test_int_form_loses_subunit_sign_but_keeps_it_from_minus_one(self):
        from odoo.libs.numbers.float_utils import float_split

        assert float_split(-0.05, 2) == (0, 5)
        assert float_split(-2.675, 2) == (-2, 68)
        assert float_split(-0.001, 2) == (0, 0)


class TestGetWebpSize:
    @staticmethod
    def _webp_vp8x(width: int, height: int) -> bytes:
        def u24(n: int) -> bytes:
            return (n).to_bytes(4, "little")[:3]

        body = (
            b"VP8X"
            + (10).to_bytes(4, "little")
            + b"\x00"
            + b"\x00\x00\x00"
            + u24(width - 1)
            + u24(height - 1)
        )
        return b"RIFF" + (len(body) + 4).to_bytes(4, "little") + b"WEBP" + body

    def test_a_vp8x_canvas_is_read_from_the_header(self):
        side = int(IMAGE_MAX_RESOLUTION**0.5) + 100
        assert get_webp_size(self._webp_vp8x(side, side)) == (side, side)

    def test_the_lossy_upscaling_hint_is_not_read_as_a_dimension(self):
        stream = io.BytesIO()
        Image.new("RGB", (300, 200), (9, 9, 9)).save(stream, "WEBP", lossless=False)
        raw = bytearray(stream.getvalue())
        assert raw[12:16] == b"VP8 " and raw[15:16] == b" "
        assert get_webp_size(bytes(raw)) == (300, 200)

        for offset in (26, 28):
            field = raw[offset] | (raw[offset + 1] << 8)
            raw[offset + 1] = (((field & 0x3FFF) | (3 << 14)) >> 8) & 0xFF
        assert get_webp_size(bytes(raw)) == (300, 200)


class TestImageResolutionGuard:
    @staticmethod
    def _webp(size):
        stream = io.BytesIO()
        Image.new("RGB", size, (9, 9, 9)).save(stream, "WEBP")
        return stream.getvalue()

    def test_oversized_is_rejected(self, monkeypatch):
        monkeypatch.setattr("odoo.libs.image.utils.IMAGE_MAX_RESOLUTION", 100.0)
        with pytest.raises(ImageTooLargeError):
            ImageProcess(self._webp((40, 40)), verify_resolution=True)

    def test_reasonable_is_accepted_and_decoded(self):
        processed = ImageProcess(self._webp((64, 64)), verify_resolution=True)
        assert processed.image is not False
        assert processed.original_format == "WEBP"

    def test_oversized_accepted_when_not_verifying(self, monkeypatch):
        monkeypatch.setattr("odoo.libs.image.utils.IMAGE_MAX_RESOLUTION", 100.0)
        assert ImageProcess(self._webp((40, 40)), verify_resolution=False).image


class TestLruCountSetter:
    def test_shrink_evicts_down_to_new_count(self):
        lru = LRU(10, [(i, i) for i in range(10)])
        lru.count = 3
        assert len(lru) == 3
        assert set(lru) == {7, 8, 9}

    def test_shrink_keeps_the_most_recently_used(self):
        lru = LRU(10, [(i, i) for i in range(10)])
        lru[0]
        lru[1]
        lru.count = 3
        assert list(lru) == [9, 0, 1]

    def test_setter_holds_no_python_iterator_over_the_map(self):
        seen = []

        class WatchfulMap(OrderedDict):
            def __iter__(self):
                seen.append("iter")
                return super().__iter__()

        lru = LRU(10, [(i, i) for i in range(10)])
        lru._map = WatchfulMap(lru._map)
        lru.count = 3
        assert len(lru) == 3
        assert seen == [], "count setter still walks the map in Python"

    def test_rejects_a_non_positive_count(self):
        lru = LRU(4, [(1, "a")])
        for bad in (0, -1):
            with pytest.raises(ValueError, match="must be positive"):
                lru.count = bad
        assert len(lru) == 1


class TestHtmlSanitizeRecovery:
    def test_crash_input_does_not_yield_placeholder(self):
        out = str(html_sanitize("<select><style>x</style></select>"))
        assert "Unknown error when sanitizing" not in out

    def test_surrounding_content_is_preserved(self):
        out = str(
            html_sanitize("<p>keep this line</p><select><style>x</style></select>")
        )
        assert "keep this line" in out
        assert "Unknown error when sanitizing" not in out

    def test_kill_tags_still_removed_on_recovery(self):
        out = str(html_sanitize("<p>hi</p><select><style>body{x:1}</style></select>"))
        assert "<style" not in out.lower()
        assert "body{x:1}" not in out

    def test_normal_sanitization_unaffected(self):
        assert str(html_sanitize("<script>alert(1)</script>hi")) == "hi"
        assert "onerror" not in str(html_sanitize("<img src=x onerror=alert(1)>"))

    def test_silent_false_still_raises(self):
        with pytest.raises(AssertionError):
            html_sanitize("<select><style>x</style></select>", silent=False)


class TestTimezoneContract:
    @pytest.mark.parametrize("name", ["", "../etc/passwd", "Foo/Bar", "not a tz"])
    def test_bad_names_raise_zoneinfonotfound(self, name):
        with pytest.raises(ZoneInfoNotFoundError):
            timezone(name)

    def test_bad_name_is_catchable_as_keyerror(self):
        with pytest.raises(KeyError):
            timezone("")

    def test_valid_names_still_resolve(self):
        assert timezone("Europe/Paris") is not None
        assert timezone("UTC") is not None


class TestFormataddrHeaderInjection:
    def test_newline_is_stripped_from_name(self):
        out = formataddr(("Bad\r\nBcc: victim@x.com", "user@example.com"))
        assert "\n" not in out
        assert "\r" not in out
        assert out == '"BadBcc: victim@x.com" <user@example.com>'

    def test_control_only_name_collapses_to_bare_address(self):
        assert formataddr(("\r\n\t", "user@example.com")) == "user@example.com"

    def test_ordinary_name_unchanged(self):
        assert (
            formataddr(("John Doe", "john@example.com"))
            == '"John Doe" <john@example.com>'
        )


class TestReverseOrderCommas:
    def test_function_call_arglist_not_split(self):
        assert reverse_order("coalesce(a, b) desc") == "coalesce(a, b) asc"

    def test_mixed_items(self):
        assert (
            reverse_order("coalesce(a, b) desc, name asc")
            == "coalesce(a, b) asc, name desc"
        )

    def test_quoted_identifier_with_comma(self):
        assert reverse_order('"a,b" asc') == '"a,b" desc'

    def test_simple_cases_unchanged(self):
        assert reverse_order("name asc, date desc") == "name desc, date asc"
        assert reverse_order("id") == "id desc"
        assert reverse_order("name desc nulls last") == "name asc nulls first"


class TestZipDirRelativePath:
    def _tree(self, tmp_path):
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "a.txt").write_text("a")
        (tmp_path / "pkg" / "sub").mkdir()
        (tmp_path / "pkg" / "sub" / "b.txt").write_text("b")

    def test_relative_bare_name_keeps_full_member_names(self, tmp_path, monkeypatch):
        import zipfile

        self._tree(tmp_path)
        monkeypatch.chdir(tmp_path)
        buf = io.BytesIO()
        zip_dir("pkg", buf, include_dir=True)
        names = sorted(zipfile.ZipFile(io.BytesIO(buf.getvalue())).namelist())
        assert names == ["pkg/a.txt", "pkg/sub/b.txt"]

    def test_absolute_path_still_correct(self, tmp_path):
        import zipfile

        self._tree(tmp_path)
        buf = io.BytesIO()
        zip_dir(str(tmp_path / "pkg"), buf, include_dir=True)
        names = sorted(zipfile.ZipFile(io.BytesIO(buf.getvalue())).namelist())
        assert names == ["pkg/a.txt", "pkg/sub/b.txt"]


class TestOrderedSetIntersectionAliasing:
    def test_no_args_returns_copy(self):
        s = OrderedSet([1, 2, 3])
        result = s.intersection()
        assert result == s
        assert result is not s
        result.add(4)
        assert 4 not in s

    def test_with_args_still_works(self):
        s = OrderedSet([1, 2, 3])
        assert list(s.intersection([2, 3, 4])) == [2, 3]


class TestGetSaturationType:
    def test_gray_returns_float_zero(self):
        result = get_saturation((128, 128, 128))
        assert result == 0.0
        assert isinstance(result, float)

    def test_pure_color_still_one(self):
        assert get_saturation((255, 0, 0)) == 1.0


class TestFreehashOnlyCatchesUnhashability:
    def test_unhashable_still_falls_back(self):
        class Unhashable:
            __hash__ = None  # type: ignore[assignment]

        obj = Unhashable()
        assert freehash(obj) == id(obj)

    def test_a_broken_hash_propagates(self):
        class Broken:
            def __hash__(self):
                raise RuntimeError("bug in __hash__")

        with pytest.raises(RuntimeError, match="bug in __hash__"):
            freehash(Broken())

    def test_mapping_and_iterable_fallbacks_still_work(self):
        assert freehash({"a": [1, 2]}) == freehash({"a": [1, 2]})
        assert freehash([1, 2, 3]) == freehash([1, 2, 3])


class TestOrderedSetIntersectionFollowsItsOwnOrder:
    def test_order_comes_from_self_not_the_argument(self):
        s = OrderedSet([1, 2, 3, 4])
        assert list(s & [4, 3]) == [3, 4]
        assert list(s.intersection([4, 3])) == [3, 4]

    def test_reversed_operand_agrees(self):
        s = OrderedSet([1, 2, 3, 4])
        assert list([4, 3] & s) == [3, 4]

    def test_argument_order_is_irrelevant(self):
        s = OrderedSet(["c", "a", "b"])
        assert list(s & ["a", "b", "c"]) == list(s & ["c", "b", "a"]) == ["c", "a", "b"]

    def test_membership_is_unchanged(self):
        s = OrderedSet([1, 2, 3, 4])
        assert set(s & [4, 3]) == {3, 4}
        assert list(s.intersection()) == [1, 2, 3, 4]
        assert list(s.intersection([2, 3, 4], [3, 4, 5])) == [3, 4]

    def test_result_is_still_an_ordered_set(self):
        assert isinstance(OrderedSet([1, 2]) & [2], OrderedSet)
        assert isinstance(LastOrderedSet([1, 2]) & [2], LastOrderedSet)


class TestContentHashToleranceDoesNotDependOnBlake3:
    def test_empty_and_falsy_inputs_agree(self):
        assert content_hash(b"") == content_hash(None)  # type: ignore[arg-type]

    def test_it_is_the_digest_of_the_empty_input(self):
        assert content_hash(None) == content_hash(b"")  # type: ignore[arg-type]
        assert len(content_hash(b"")) == CONTENT_DIGEST_LEN

    def test_real_content_is_unaffected(self):
        assert content_hash(b"x") != content_hash(b"")


class TestIntervalsSortKeyStopsBeforeThePayload:
    class Payload:
        def __init__(self, name, ids):
            self._name, self.ids = name, ids

        def union(self, other):
            return TestIntervalsSortKeyStopsBeforeThePayload.Payload(
                self._name, self.ids | other.ids
            )

        def __lt__(self, other):
            raise AssertionError("the sort reached the payload")

        __gt__ = __lt__

    def _p(self, name, ids):
        return self.Payload(name, ids)

    def test_identical_endpoints_do_not_compare_payloads(self):
        from odoo.libs.intervals import Intervals

        a, b = datetime(2026, 1, 1), datetime(2026, 1, 2)
        result = Intervals([(a, b, self._p("m.a", {1})), (a, b, self._p("m.b", {2}))])
        assert len(result) == 1

    def test_keep_distinct_pre_sort_does_not_compare_payloads(self):
        from odoo.libs.intervals import Intervals

        a, b = datetime(2026, 1, 1), datetime(2026, 1, 2)
        result = Intervals(
            [(a, b, self._p("m.a", {1})), (a, b, self._p("m.b", {2}))],
            keep_distinct=True,
        )
        assert len(result) == 1

    def test_merge_does_not_compare_payloads(self):
        from odoo.libs.intervals import Intervals

        a, b = datetime(2026, 1, 1), datetime(2026, 1, 2)
        left = Intervals([(a, b, self._p("m.a", {1}))])
        right = Intervals([(a, b, self._p("m.b", {2}))])
        assert len(left & right) == 1
        assert len(left - right) == 0

    def test_ordinary_merging_is_unchanged(self):
        from odoo.libs.intervals import Intervals

        d = datetime
        got = Intervals(
            [
                (d(2026, 1, 1), d(2026, 1, 3), self._p("m", {1})),
                (d(2026, 1, 2), d(2026, 1, 5), self._p("m", {2})),
                (d(2026, 1, 8), d(2026, 1, 9), self._p("m", {3})),
            ]
        )
        assert [(s, e) for s, e, _ in got] == [
            (d(2026, 1, 1), d(2026, 1, 5)),
            (d(2026, 1, 8), d(2026, 1, 9)),
        ]


class TestCollectorAnswersConsistently:
    def test_absent_key_reads_as_the_empty_tuple_every_way(self):
        from odoo.libs.collections.misc import Collector

        c: Collector = Collector()
        assert c["x"] == ()
        assert c.get("x") == ()
        assert c.pop("x") == ()

    def test_an_explicit_default_still_wins(self):
        from odoo.libs.collections.misc import Collector

        c: Collector = Collector()
        assert c.get("x", None) is None
        assert c.pop("x", "sentinel") == "sentinel"

    def test_membership_still_means_a_non_empty_tuple(self):
        from odoo.libs.collections.misc import Collector

        c: Collector = Collector()
        c["a"] = (1,)
        c["b"] = ()
        assert "a" in c
        assert "b" not in c

    def test_present_keys_are_unaffected(self):
        from odoo.libs.collections.misc import Collector

        c: Collector = Collector()
        c.add("a", 1)
        c.add("a", 2)
        assert c["a"] == c.get("a") == (1, 2)
        assert c.pop("a") == (1, 2)
        assert "a" not in c


class TestStackMapIteratesInInsertionOrder:
    def test_order_is_deterministic_not_hash_order(self):
        from odoo.libs.collections.misc import StackMap

        keys = ["z", "a", "m", "q", "b", "k"]
        sm: StackMap = StackMap(dict.fromkeys(keys, 1))
        sm.push_map({"y": 2})
        assert list(sm) == [*keys, "y"]

    def test_a_shadowed_key_keeps_its_first_position(self):
        from odoo.libs.collections.misc import StackMap

        sm: StackMap = StackMap({"z": 1, "a": 2})
        sm.push_map({"z": 3, "b": 4})
        assert list(sm) == ["z", "a", "b"]
        assert sm["z"] == 3
        assert len(sm) == 3


class TestHtml2PlaintextHalvesRunsRatherThanFlatteningThem:
    def test_a_run_of_spaces_is_halved_not_flattened(self):
        assert html2plaintext("<p>a  b</p>") == "a b"
        assert html2plaintext("<p>a   b</p>") == "a  b"
        assert html2plaintext("<p>a    b</p>") == "a  b"
        assert html2plaintext("<p>a     b</p>") == "a   b"

    def test_a_single_space_is_untouched(self):
        assert html2plaintext("<p>a b</p>") == "a b"

    def test_the_exact_spacing_base_pins_over_smtp(self):
        assert html2plaintext("<p>test6      test7</p>") == "test6   test7"
        assert html2plaintext("<p>test8        test9</p>") == "test8    test9"

    def test_a_break_between_blocks_still_makes_a_blank_line(self):
        assert html2plaintext("<h2>A</h2>\n<br/>\n<h3>B</h3>") == "**A**\n\n*B*"

    def test_the_reference_list_keeps_its_blank_line(self):
        out = html2plaintext('<p>see <a href="http://x/">x</a></p>')
        assert "\n\n[1] http://x/" in out


class TestDateRangeRejectsASubDayStep:
    def test_a_sub_day_step_over_dates_names_itself(self):
        from odoo.libs.datetime.date_utils import date_range

        with pytest.raises(ValueError, match="entire days"):
            list(
                date_range(date(2024, 1, 1), date(2024, 1, 3), relativedelta(hours=13))
            )

    def test_whole_day_steps_over_dates_still_work(self):
        from odoo.libs.datetime.date_utils import date_range

        got = list(
            date_range(date(2024, 1, 1), date(2024, 1, 5), relativedelta(days=2))
        )
        assert got == [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 5)]

    def test_sub_day_steps_over_datetimes_are_still_allowed(self):
        from odoo.libs.datetime.date_utils import date_range

        got = list(
            date_range(
                datetime(2024, 1, 1, 0), datetime(2024, 1, 1, 3), relativedelta(hours=1)
            )
        )
        assert len(got) == 4


class TestEmailDomainExtractUsesTheLastAt:
    def test_a_quoted_local_part_containing_an_at(self):
        from odoo.libs.email.parsing import email_domain_extract

        assert email_domain_extract('"a@b"@example.com') == "example.com"

    def test_ordinary_addresses_are_unchanged(self):
        from odoo.libs.email.parsing import email_domain_extract

        assert email_domain_extract("x@y.com") == "y.com"
        assert email_domain_extract("not an email") is False


class TestWorkingOnDatabaseRestoresAnExplicitNone:
    def test_an_explicit_none_is_put_back_not_deleted(self):
        from odoo.libs.worker_thread import (
            current_worker_thread,
            working_on_database,
        )

        thread = current_worker_thread()
        thread.dbname = None
        try:
            with working_on_database("scratch"):
                assert thread.dbname == "scratch"
            assert hasattr(thread, "dbname"), "an explicit None was deleted"
            assert thread.dbname is None
        finally:
            del thread.dbname

    def test_an_absent_attribute_is_still_removed(self):
        from odoo.libs.worker_thread import (
            current_worker_thread,
            working_on_database,
        )

        thread = current_worker_thread()
        assert not hasattr(thread, "dbname")
        with working_on_database("scratch"):
            assert thread.dbname == "scratch"
        assert not hasattr(thread, "dbname")

    def test_a_real_previous_value_is_restored(self):
        from odoo.libs.worker_thread import (
            current_worker_thread,
            working_on_database,
        )

        thread = current_worker_thread()
        thread.dbname = "outer"
        try:
            with working_on_database("inner"):
                assert thread.dbname == "inner"
            assert thread.dbname == "outer"
        finally:
            del thread.dbname


class TestOpenContainerMimetypeIsValidated:
    @staticmethod
    def _ocf(declared: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("mimetype", declared)
            archive.writestr("content.xml", "<a/>")
        return buf.getvalue()

    @pytest.mark.parametrize(
        "declared",
        [
            "text/plain\r\nX-Injected: yes",
            "text/plain garbage",
            'text/plain; charset="a"b',
            "application/vnd.oasis.opendocument.text trailing",
        ],
    )
    def test_a_member_that_is_not_exactly_a_mimetype_is_refused(
        self, declared, monkeypatch
    ):
        monkeypatch.setattr("odoo.libs.filesystem.mimetypes.magic", None)
        assert guess_mimetype(self._ocf(declared)) == "application/zip"

    def test_a_real_open_document_is_still_identified(self, monkeypatch):
        monkeypatch.setattr("odoo.libs.filesystem.mimetypes.magic", None)
        declared = "application/vnd.oasis.opendocument.text"
        assert guess_mimetype(self._ocf(declared)) == declared


class TestFormatNumberLeavesLiteralTextAlone:
    class _Lang:
        decimal_point = ","
        thousands_sep = "."
        grouping = "[3,0]"

    @pytest.mark.parametrize(
        ("spec", "value", "expected"),
        [
            ("%.2f", 1234.5, "1.234,50"),
            ("%.2f sec.", 1234.5, "1.234,50 sec."),
            ("%.2f EUR", 1234.5, "1.234,50 EUR"),
            ("%.2f%%", 1234.5, "1.234,50%"),
            ("%d units", 1234567, "1.234.567 units"),
            ("%%%.2f", 1234.5, "%1.234,50"),
            ("%e", 1e20, "1,000000e+20"),
            ("%g", 1e20, "1e+20"),
        ],
    )
    def test_grouping(self, spec, value, expected):
        assert format_number(spec, value, self._Lang(), grouping=True) == expected

    def test_without_grouping_the_literal_period_also_survives(self):
        assert format_number("%.2f sec.", 1234.5, self._Lang()) == "1234,50 sec."


class TestUrljoinPrefixIsMeasuredInSegments:
    def test_a_sibling_path_is_refused_not_re_rooted(self):
        with pytest.raises(ValueError, match="begin with base path"):
            urljoin("http://h/a", "http://h/abc/d")

    def test_a_real_descendant_is_still_accepted(self):
        assert urljoin("http://h/a", "http://h/a/b") == "http://h/a/b"

    def test_the_base_path_itself_is_a_prefix_of_itself(self):
        assert urljoin("http://h/a", "http://h/a") == "http://h/a"

    def test_relative_extras_are_unaffected(self):
        assert urljoin("https://x.com/odoo", "/web/login") == (
            "https://x.com/odoo/web/login"
        )


class TestSqlJoinKeepsTheSeparatorsToFlush:
    class _Field:
        def __repr__(self):
            return "<field>"

    @classmethod
    def _a_field(cls) -> Any:
        return cls._Field()

    def test_a_separator_without_params_reports_its_fields(self):
        field = self._a_field()
        joined = SQL(" AND ", to_flush=field).join([SQL("a=1"), SQL("b=2")])
        assert list(joined.to_flush) == [field]
        assert joined.code == "a=1 AND b=2"

    def test_the_two_branches_agree(self):
        field = self._a_field()
        items = [SQL("a"), SQL("b"), SQL("c")]
        flat = SQL(", ", to_flush=field).join(items)
        parameterised = SQL("%s", ", ", to_flush=field).join(items)
        assert list(flat.to_flush) == list(parameterised.to_flush)


class TestCollectorInvariantHoldsForEveryWriter:
    def test_construction_from_a_mapping(self):
        collector = Collector[str, int]({"a": [], "b": [1, 2]})
        assert dict(collector) == {"b": (1, 2)}
        assert collector["a"] == ()
        assert "a" not in collector

    def test_update_and_setdefault(self):
        collector = Collector[str, int]()
        collector.update({"a": [], "b": [1]})
        collector.setdefault("c", [])
        collector.setdefault("d", [2])
        assert dict(collector) == {"b": (1,), "d": (2,)}

    def test_add_works_on_a_collector_built_from_a_mapping(self):
        collector = Collector[str, int]({"b": [1, 2]})
        collector.add("b", 3)
        assert collector["b"] == (1, 2, 3)

    def test_construction_from_pairs_still_works(self):
        assert dict(Collector([("a", [1]), ("b", ())])) == {"a": (1,)}


class TestLruViewsDoNotWalkThroughGetitem:
    def test_items_does_not_touch_the_recency_order(self):
        cache = LRU[str, int](3)
        cache["a"], cache["b"], cache["c"] = 1, 2, 3
        moved = []

        class Counting(OrderedDict):
            def move_to_end(self, key, last=True):
                moved.append(key)
                return super().move_to_end(key, last)

        cache._map = Counting(cache._map)
        assert dict(cache.items()) == {"a": 1, "b": 2, "c": 3}
        assert list(cache.values()) == [1, 2, 3]
        assert list(cache.keys()) == ["a", "b", "c"]
        assert moved == []

    def test_iteration_survives_concurrent_eviction(self):
        cache = LRU[int, int](50)
        for i in range(50):
            cache[i] = i
        errors: list[str] = []
        stop = threading.Event()

        def evict():
            i = 1000
            while not stop.is_set():
                cache[i] = i
                i += 1

        def read():
            while not stop.is_set():
                try:
                    dict(cache.items())
                except Exception as exc:
                    errors.append(type(exc).__name__)
                    return

        threads = [threading.Thread(target=evict) for _ in range(2)]
        threads += [threading.Thread(target=read) for _ in range(2)]
        for thread in threads:
            thread.start()
        stop.wait(1.5)
        stop.set()
        for thread in threads:
            thread.join()
        assert errors == []


class TestDsigTransformOrderIsIrrelevant:
    DS = "http://www.w3.org/2000/09/xmldsig#"
    ENVELOPED = f"{DS}enveloped-signature"

    def _reference(self, *algorithms: str) -> etree._Element:
        transforms = "".join(f'<Transform Algorithm="{a}"/>' for a in algorithms)
        return etree.fromstring(
            f'<Reference xmlns="{self.DS}" URI=""><Transforms>{transforms}'
            f"</Transforms></Reference>".encode()
        )

    def test_exclusive_c14n_is_found_after_an_enveloped_transform(self):
        assert _get_c14n_params_from_transforms(
            self._reference(self.ENVELOPED, EXC_C14N_ALGORITHM)
        ) == (True, [])

    def test_it_is_still_found_when_it_comes_first(self):
        assert _get_c14n_params_from_transforms(
            self._reference(EXC_C14N_ALGORITHM, self.ENVELOPED)
        ) == (True, [])

    def test_a_reference_without_it_is_still_inclusive(self):
        assert _get_c14n_params_from_transforms(self._reference(self.ENVELOPED)) == (
            False,
            [],
        )

    def test_the_prefix_list_comes_from_the_c14n_transform_not_the_first(self):
        reference = etree.fromstring(
            f'<Reference xmlns="{self.DS}" URI=""><Transforms>'
            f'<Transform Algorithm="{self.ENVELOPED}"/>'
            f'<Transform Algorithm="{EXC_C14N_ALGORITHM}">'
            f'<InclusiveNamespaces PrefixList="soap wcf"/>'
            f"</Transform></Transforms></Reference>".encode()
        )
        assert _get_c14n_params_from_transforms(reference) == (True, ["soap", "wcf"])

    def test_a_reference_with_no_digest_value_names_itself(self):
        signed_info = etree.fromstring(
            f'<SignedInfo xmlns="{self.DS}"><Reference URI="#x"/></SignedInfo>'.encode()
        )
        with pytest.raises(XmlSigError, match="no <ds:DigestValue>"):
            update_reference_digests(signed_info)


class TestIsEncodableEmptyString:
    def test_the_empty_string_encodes_in_every_charset(self):
        assert is_encodable("") is True
        assert is_encodable("", "ascii") is True

    def test_real_values_are_unaffected(self):
        assert is_encodable("abc") is True
        assert is_encodable("\u4e2d\u6587") is False


class TestHashingOneShotAgreesWithIncremental:
    SIZES = [0, 1, 11, _MT_MIN_BYTES - 1, _MT_MIN_BYTES, 2 * _MT_MIN_BYTES]

    @pytest.mark.parametrize("size", SIZES)
    def test_every_route_to_a_content_digest_agrees(self, size, tmp_path):
        data = bytes(range(256)) * (size // 256) + bytes(range(size % 256))
        assert len(data) == size
        path = tmp_path / "blob"
        path.write_bytes(data)

        incremental = prepare_content_hasher()
        incremental.update(data)
        from_file = prepare_content_hasher()
        update_from_file(from_file, path)

        digests = {
            content_hash(data),
            incremental.hexdigest(),
            content_hash_file(path),
            from_file.hexdigest(),
        }
        assert len(digests) == 1, f"four routes, {len(digests)} digests: {digests}"
        assert len(digests.pop()) == CONTENT_DIGEST_LEN

    @pytest.mark.parametrize("size", SIZES)
    def test_the_cache_digest_agrees_with_its_own_hasher(self, size):
        data = b"\xa5" * size
        incremental = prepare_cache_hasher()
        incremental.update(data)
        assert cache_hash(data) == incremental.hexdigest()

    def test_different_content_still_gives_different_digests(self):
        assert content_hash(b"a") != content_hash(b"b")
        assert content_hash(b"") != content_hash(b"\0")


class TestCryptContextCopyKeepsEverySetting:
    def test_a_copy_carries_the_settings_and_is_independent(self):
        original = CryptContext(
            ["pbkdf2_sha512", "plaintext"],
            deprecated=["auto"],
            pbkdf2_sha512__rounds=1000,
        )
        copy = original.copy()
        assert copy.schemes() == original.schemes()
        assert copy._deprecated == original._deprecated
        assert copy._rounds == original._rounds

        copy.update(pbkdf2_sha512__rounds=99, schemes=["plaintext"])
        assert original._rounds == 1000
        assert original.schemes() == ["pbkdf2_sha512", "plaintext"]

    def test_a_copy_still_hashes_and_verifies(self):
        copy = CryptContext(pbkdf2_sha512__rounds=1000).copy()
        hashed = copy.hash("secret")
        assert copy.is_password_valid("secret", hashed)
        assert not copy.is_password_valid("wrong", hashed)
        assert copy.match_and_update("secret", hashed) == (True, None)
