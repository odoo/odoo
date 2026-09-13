import typing
import unittest

from odoo.libs.documents.document import (
    DEFAULT_READ_UP_TO,
    TEXT_MAX_CHARS,
    Document,
)
from odoo.libs.documents.readers import (
    ANY,
    BARCODES,
    CHEAP,
    DATA,
    EXPENSIVE,
    FREE,
    ROWS,
    TEXT,
    TREE,
    BaseReader,
    get_known_reader_names,
    get_readers,
    register_reader,
    registered_readers,
)


class _Stub(BaseReader):
    def __init__(self, name, mimetypes, yields, value=None, boom=False, cost=FREE):
        self.name = name
        self.mimetypes = frozenset(mimetypes)
        self.yields = tuple(yields)
        self.cost = cost
        self._value = value
        self._boom = boom
        self.calls = 0

    def read(self, document):
        self.calls += 1
        if self._boom:
            raise RuntimeError("no")
        return self._value


def _forget(*readers):
    from odoo.libs.documents import readers as module

    for bucket in module._READERS.values():
        for reader in readers:
            while reader in bucket:
                bucket.remove(reader)


class TestRegistry(unittest.TestCase):
    def test_a_reader_must_declare_what_it_yields(self):
        with self.assertRaises(ValueError):
            register_reader(_Stub("x", {"a/b"}, ()))

    def test_a_reader_must_declare_a_mimetype(self):
        with self.assertRaises(ValueError):
            register_reader(_Stub("x", (), (TEXT,)))

    def test_a_duck_typed_reader_with_no_cost_is_refused(self):
        class _Costless:
            name = "costless"
            mimetypes = frozenset({"a/b"})
            yields = (TEXT,)

            def read(self, document):
                return "x"

        with self.assertRaises(ValueError):
            register_reader(typing.cast("BaseReader", _Costless()))

    def test_an_unknown_representation_is_refused_at_registration(self):
        with self.assertRaises(ValueError):
            register_reader(_Stub("x", {"a/b"}, ("pixels",)))

    def test_a_reader_must_name_itself(self):
        with self.assertRaises(ValueError):
            register_reader(_Stub("", {"a/b"}, (TEXT,)))

    def test_the_shipped_readers_are_registered(self):
        for name in ("csv", "json", "xml"):
            self.assertIn(name, get_known_reader_names())

    def test_a_named_mimetype_is_tried_before_a_fallback(self):
        named = _Stub("named", {"a/b"}, (TEXT,), "named")
        fallback = _Stub("fallback", {ANY}, (TEXT,), "fallback")
        register_reader(fallback)
        register_reader(named)
        try:
            self.assertEqual(
                [r.name for r in get_readers("a/b", TEXT)], ["named", "fallback"]
            )
        finally:
            _forget(named, fallback)

    def test_no_two_library_readers_claim_one_mimetype_at_one_cost(self):
        claims: dict[tuple, list[str]] = {}
        for reader in registered_readers():
            for representation in reader.yields:
                for mimetype in reader.mimetypes:
                    key = (mimetype, representation, reader.cost)
                    claims.setdefault(key, []).append(reader.name)
        contested = {key: names for key, names in claims.items() if len(names) > 1}
        self.assertEqual(contested, {})

    def test_an_unknown_representation_is_refused_at_lookup(self):
        with self.assertRaises(ValueError):
            get_readers("a/b", "pixels")

    def test_the_cheaper_reader_is_offered_first(self):
        dear = _Stub("dear", {"a/b"}, (TEXT,), "dear", cost=EXPENSIVE)
        free = _Stub("free", {"a/b"}, (TEXT,), "free", cost=FREE)
        register_reader(dear)
        register_reader(free)
        try:
            self.assertEqual(
                [r.name for r in get_readers("a/b", TEXT)], ["free", "dear"]
            )
        finally:
            _forget(dear, free)

    def test_readers_of_one_cost_keep_the_order_they_registered_in(self):
        first = _Stub("first", {"a/b"}, (TEXT,), "1", cost=CHEAP)
        second = _Stub("second", {"a/b"}, (TEXT,), "2", cost=CHEAP)
        register_reader(first)
        register_reader(second)
        try:
            self.assertEqual(
                [r.name for r in get_readers("a/b", TEXT)], ["first", "second"]
            )
        finally:
            _forget(first, second)

    def test_a_free_fallback_never_displaces_a_reader_that_named_the_mimetype(self):
        named = _Stub("named", {"a/b"}, (TEXT,), "named", cost=EXPENSIVE)
        fallback = _Stub("fallback", {ANY}, (TEXT,), "fallback", cost=FREE)
        register_reader(fallback)
        register_reader(named)
        try:
            self.assertEqual(
                [r.name for r in get_readers("a/b", TEXT)], ["named", "fallback"]
            )
        finally:
            _forget(named, fallback)


class TestDeriving(unittest.TestCase):
    def test_derived_once_and_kept(self):
        reader = _Stub("counting", {"a/b"}, (TEXT,), "hello")
        register_reader(reader)
        try:
            doc = Document(b"...", "a/b", "x")
            self.assertEqual(doc.text, "hello")
            self.assertEqual(doc.text, "hello")
            self.assertEqual(reader.calls, 1)
        finally:
            _forget(reader)

    def test_a_reader_that_raises_lets_the_next_one_answer(self):
        broken = _Stub("broken", {"a/b"}, (TEXT,), boom=True)
        working = _Stub("working", {"a/b"}, (TEXT,), "hello")
        register_reader(broken)
        register_reader(working)
        try:
            self.assertEqual(Document(b"...", "a/b", "x").text, "hello")
            self.assertEqual(broken.calls, 1)
            self.assertEqual(working.calls, 1)
        finally:
            _forget(broken, working)

    def test_an_empty_answer_does_not_end_the_search(self):
        cheap = _Stub("cheap", {"a/b"}, (TEXT,), "", cost=FREE)
        dear = _Stub("dear", {"a/b"}, (TEXT,), "read from the pages", cost=EXPENSIVE)
        register_reader(dear)
        register_reader(cheap)
        try:
            doc = Document(b"...", "a/b", "x", read_up_to=EXPENSIVE)
            self.assertEqual(doc.text, "read from the pages")
            self.assertEqual(cheap.calls, 1)
            self.assertEqual(dear.calls, 1)
        finally:
            _forget(cheap, dear)

    def test_an_answer_ends_the_search_before_the_costly_reader_runs(self):
        cheap = _Stub("cheap", {"a/b"}, (TEXT,), "the text layer", cost=FREE)
        dear = _Stub("dear", {"a/b"}, (TEXT,), "recognised", cost=EXPENSIVE)
        register_reader(dear)
        register_reader(cheap)
        try:
            self.assertEqual(Document(b"...", "a/b", "x").text, "the text layer")
            self.assertEqual(dear.calls, 0)
        finally:
            _forget(cheap, dear)

    def test_an_empty_answer_is_kept_when_nothing_better_arrives(self):
        cheap = _Stub("cheap", {"a/b"}, (BARCODES,), [], cost=FREE)
        dear = _Stub("dear", {"a/b"}, (BARCODES,), [], cost=EXPENSIVE)
        register_reader(dear)
        register_reader(cheap)
        try:
            doc = Document(b"...", "a/b", "x")
            self.assertEqual(doc.barcodes, [])
            self.assertFalse(doc.provides(BARCODES))
        finally:
            _forget(cheap, dear)

    def test_a_childless_root_is_not_passed_over_for_a_costlier_reader(self):
        from lxml import etree

        root = etree.fromstring(b"<Invoice/>")
        cheap = _Stub("cheap", {"a/b"}, (TREE,), root, cost=FREE)
        dear = _Stub(
            "dear", {"a/b"}, (TREE,), etree.fromstring(b"<Other/>"), cost=EXPENSIVE
        )
        register_reader(dear)
        register_reader(cheap)
        try:
            self.assertIs(Document(b"...", "a/b", "x").tree, root)
            self.assertEqual(dear.calls, 0)
        finally:
            _forget(cheap, dear)

    def test_a_reader_answering_none_is_passed_over_for_one_that_answers(self):
        silent = _Stub("silent", {"a/b"}, (TEXT,), None, cost=FREE)
        answers = _Stub("answers", {"a/b"}, (TEXT,), "here", cost=EXPENSIVE)
        register_reader(answers)
        register_reader(silent)
        try:
            doc = Document(b"...", "a/b", "x", read_up_to=EXPENSIVE)
            self.assertEqual(doc.text, "here")
        finally:
            _forget(silent, answers)

    def test_a_reader_above_the_ceiling_is_not_run(self):
        dear = _Stub("dear", {"a/b"}, (TEXT,), "recognised", cost=EXPENSIVE)
        register_reader(dear)
        try:
            self.assertEqual(Document(b"...", "a/b", "x").text, "")
            self.assertEqual(dear.calls, 0)
        finally:
            _forget(dear)

    def test_provides_never_promises_what_the_ceiling_forbids(self):

        class _Probing(_Stub):
            def provides(self, document):
                return True

        dear = _Probing("dear", {"a/b"}, (TEXT,), "recognised", cost=EXPENSIVE)
        register_reader(dear)
        try:
            doc = Document(b"...", "a/b", "x")
            self.assertFalse(doc.provides(TEXT))
            self.assertEqual(doc.text, "")

            doc.options["read_up_to"] = EXPENSIVE
            self.assertTrue(doc.provides(TEXT))
        finally:
            _forget(dear)

    def test_an_empty_answer_is_re_read_when_the_ceiling_rises(self):
        cheap = _Stub("cheap", {"a/b"}, (TEXT,), "", cost=FREE)
        dear = _Stub("dear", {"a/b"}, (TEXT,), "recognised", cost=EXPENSIVE)
        register_reader(cheap)
        register_reader(dear)
        try:
            doc = Document(b"...", "a/b", "x")
            self.assertEqual(doc.text, "")
            self.assertEqual(dear.calls, 0)

            doc.options["read_up_to"] = EXPENSIVE

            self.assertEqual(doc.text, "recognised")
            self.assertEqual(dear.calls, 1)
            self.assertEqual(doc.text, "recognised")
            self.assertEqual(dear.calls, 1)
        finally:
            _forget(cheap, dear)

    def test_an_answer_that_was_read_is_never_re_read(self):
        cheap = _Stub("cheap", {"a/b"}, (TEXT,), "the text layer", cost=FREE)
        dear = _Stub("dear", {"a/b"}, (TEXT,), "recognised", cost=EXPENSIVE)
        register_reader(cheap)
        register_reader(dear)
        try:
            doc = Document(b"...", "a/b", "x")
            self.assertEqual(doc.text, "the text layer")

            doc.options["read_up_to"] = EXPENSIVE

            self.assertEqual(doc.text, "the text layer")
            self.assertEqual(cheap.calls, 1)
            self.assertEqual(dear.calls, 0)
        finally:
            _forget(cheap, dear)

    def test_a_childless_root_is_not_re_read_when_the_ceiling_rises(self):
        from lxml import etree

        root = etree.fromstring(b"<Invoice/>")
        cheap = _Stub("cheap", {"a/b"}, (TREE,), root, cost=FREE)
        dear = _Stub("dear", {"a/b"}, (TREE,), None, cost=EXPENSIVE)
        register_reader(cheap)
        register_reader(dear)
        try:
            doc = Document(b"...", "a/b", "x")
            self.assertIs(doc.tree, root)
            doc.options["read_up_to"] = EXPENSIVE
            self.assertIs(doc.tree, root)
            self.assertEqual(dear.calls, 0)
        finally:
            _forget(cheap, dear)

    def test_a_caller_may_raise_the_text_bound(self):
        long = "x" * (TEXT_MAX_CHARS + 100)
        reader = _Stub("long", {"a/b"}, (TEXT,), long, cost=FREE)
        register_reader(reader)
        try:
            self.assertEqual(len(Document(b"...", "a/b", "x").text), TEXT_MAX_CHARS)
            raised = Document(b"...", "a/b", "x", text_max_chars=TEXT_MAX_CHARS + 100)
            self.assertEqual(len(raised.text), TEXT_MAX_CHARS + 100)
        finally:
            _forget(reader)

    def test_a_bound_of_zero_is_no_bound(self):
        long = "x" * (TEXT_MAX_CHARS * 2)
        reader = _Stub("long", {"a/b"}, (TEXT,), long, cost=FREE)
        register_reader(reader)
        try:
            doc = Document(b"...", "a/b", "x", text_max_chars=0)
            self.assertEqual(len(doc.text), TEXT_MAX_CHARS * 2)
        finally:
            _forget(reader)

    def test_the_bound_reaches_the_decode_fallback_too(self):
        doc = Document(
            b"y" * (TEXT_MAX_CHARS + 50),
            "application/x-nothing",
            "x",
            text_max_chars=200,
        )

        self.assertEqual(len(doc.text), 200)

    def test_the_default_ceiling_admits_cheap_readers_and_no_dearer_ones(self):
        self.assertEqual(DEFAULT_READ_UP_TO, CHEAP)

    def test_the_ceiling_is_read_from_the_options_each_time_it_is_asked(self):
        dear = _Stub("dear", {"a/b"}, (TEXT,), "recognised", cost=EXPENSIVE)
        register_reader(dear)
        try:
            doc = Document(b"...", "a/b", "x")
            self.assertEqual(doc.read_up_to, CHEAP)
            doc.options["read_up_to"] = EXPENSIVE
            self.assertEqual(doc.read_up_to, EXPENSIVE)
            self.assertEqual(doc.text, "recognised")
        finally:
            _forget(dear)

    def test_nobody_can_read_it(self):
        doc = Document(b"\x00\x01\x02\x03", "application/x-nothing", "x")
        self.assertEqual(doc.text, "")
        self.assertIsNone(doc.tree)
        self.assertFalse(doc.provides(TEXT))


class TestShippedReaders(unittest.TestCase):
    def test_xml_yields_a_tree_even_without_a_prolog(self):
        doc = Document(b"<Invoice><Total>1</Total></Invoice>", name="cfdi.xml")
        self.assertEqual(doc.mimetype, "application/xml")
        self.assertIsNotNone(doc.tree)
        self.assertTrue(doc.provides(TREE))

    def test_a_childless_root_still_counts_as_a_tree(self):
        self.assertTrue(Document(b"<Invoice/>", name="x.xml").provides(TREE))

    def test_json_yields_data(self):
        doc = Document(b'{"total": 12.5}', name="x.json")
        self.assertEqual(doc.data_dict, {"total": 12.5})
        self.assertTrue(doc.provides(DATA))

    def test_csv_yields_rows(self):
        doc = Document(b"name,total\nACME,12\n", name="x.csv")
        self.assertEqual(doc.rows, [["name", "total"], ["ACME", "12"]])
        self.assertTrue(doc.provides(ROWS))

    def test_csv_honours_a_declared_separator(self):
        doc = Document(b"name;total\nACME;12\n", name="x.csv", separator=";")
        self.assertEqual(doc.rows, [["name", "total"], ["ACME", "12"]])

    def test_a_latin1_csv_reads_without_replacement_characters(self):
        doc = Document("name\nCafé Ñoño\n".encode("latin-1"), name="x.csv")
        self.assertEqual(doc.rows, [["name"], ["Café Ñoño"]])

    def test_text_falls_back_to_decoding_when_no_reader_claims_it(self):
        self.assertEqual(
            Document(b"plain words", "text/plain", "x.txt").text, "plain words"
        )


class TestTheAuditFoundThese(unittest.TestCase):
    def test_text_is_clamped_however_it_was_derived(self):
        doc = Document(("x" * 200_000).encode(), "text/plain", "big.txt")
        self.assertEqual(len(doc.text), 60_000)

    def test_a_mimetype_no_reader_claims_still_yields_its_text(self):
        doc = Document(b"a,b\n1,2\n", "application/csv", "x.csv")
        self.assertEqual(doc.text, "a,b\n1,2\n")
        self.assertEqual(doc.rows, [["a", "b"], ["1", "2"]])

    def test_prose_that_opens_with_a_bracket_is_not_xml(self):
        doc = Document(b"<note> this is prose, not markup", "text/plain", "n.txt")
        self.assertEqual(doc.mimetype, "text/plain")
        self.assertTrue(doc.text.startswith("<note>"))

    def test_real_xml_without_a_prolog_is_still_promoted(self):
        doc = Document(b"<Invoice><Total>1</Total></Invoice>", "text/plain", "c.xml")
        self.assertEqual(doc.mimetype, "application/xml")
        self.assertIsNotNone(doc.tree)

    def test_media_is_never_decoded_as_text(self):
        for mimetype, data in (
            ("image/png", b"\x89PNG\r\n"),
            ("audio/mpeg", b"ID3\x03\x00abc"),
            ("font/woff2", b"wOF2ok"),
        ):
            with self.subTest(mimetype=mimetype):
                self.assertEqual(Document(data, mimetype, "m").text, "")

    def test_bytes_that_decode_but_are_not_text_yield_none(self):
        for name, data in (
            ("nul and controls", b"\x00\x01\x02\x03"),
            ("whole byte range", bytes(range(256)) * 40),
        ):
            with self.subTest(name=name):
                self.assertEqual(Document(data, "application/x-nothing", name).text, "")

    def test_rows_are_not_bounded_by_the_text_clamp(self):
        source = "col_a,col_b\n" + "".join(f"value{i},{i}\n" for i in range(6000))
        doc = Document(source.encode(), "text/csv", "big.csv")
        self.assertEqual(len(doc.rows), 6001)
        self.assertEqual(doc.rows[-1], ["value5999", "5999"])
        self.assertEqual(len(doc.text), 60_000)

    def test_a_large_json_document_still_parses(self):
        import json as _json

        payload = {f"k{i}": f"v{i}" for i in range(6000)}
        doc = Document(_json.dumps(payload).encode(), "application/json", "big.json")
        rows = doc.data_dict
        assert rows is not None
        self.assertEqual(len(rows), 6000)

    def test_a_large_xml_document_still_parses(self):
        source = ("<r>" + "".join(f"<i>{i}</i>" for i in range(6000)) + "</r>").encode()
        doc = Document(source, "application/xml", "big.xml")
        self.assertEqual(len(doc.tree), 6000)
        self.assertEqual(len(doc.text), 60_000)

    def test_the_clamp_warns_once_per_document_not_once_per_read(self):
        doc = Document(("x" * 200_000).encode(), "text/plain", "big.txt")
        with self.assertLogs("odoo.libs.documents.document", level="WARNING") as caught:
            doc.text
            doc.text
            doc.text
        self.assertEqual(len(caught.records), 1)


class TestDocument(unittest.TestCase):
    def test_empty_data_is_refused(self):
        with self.assertRaises(ValueError):
            Document(b"")

    def test_of_bytes_accepts_base64(self):
        import base64 as b64

        doc = Document.of_bytes(b64.b64encode(b"<a/>").decode(), name="x.xml")
        self.assertIsNotNone(doc.tree)

    def test_an_unknown_representation_is_refused(self):
        with self.assertRaises(ValueError):
            Document(b"x", "text/plain").provides("pixels")


class TestBuiltinsAreInTheTable(unittest.TestCase):
    def test_every_builtin_reader_mimetype_is_a_registered_format(self):
        from odoo.libs.documents.formats import get_format
        from odoo.libs.documents.readers import registered_readers

        for reader in registered_readers():
            for mimetype in reader.mimetypes - {ANY}:
                with self.subTest(reader=reader.name, mimetype=mimetype):
                    self.assertIsNotNone(get_format(mimetype))

    def test_every_builtin_writer_mimetype_is_a_canonical_format(self):
        from odoo.libs.documents.formats import extension_for
        from odoo.libs.documents.writers import registered_writers

        for writer in registered_writers():
            if writer.mimetype == ANY:
                continue
            with self.subTest(writer=writer.name):
                self.assertTrue(extension_for(writer.mimetype))
