import datetime
import json
import unittest

from odoo.libs.documents.document import Document
from odoo.libs.documents.readers import ANY, DATA, ROWS, TEXT, TREE
from odoo.libs.documents.writers import (
    _WRITERS,
    BaseWriter,
    get_known_writer_names,
    get_writers,
    register_writer,
)


class TestRegistry(unittest.TestCase):
    def test_the_built_in_writers_are_registered(self):
        self.assertEqual(
            get_known_writer_names(),
            ("csv", "json", "srt", "text", "vtt", "xlsx_sheets", "xml"),
        )

    def test_a_writer_is_found_by_mimetype_and_representation(self):
        writers = get_writers("text/csv", ROWS)
        self.assertEqual([w.name for w in writers], ["csv"])

    def test_a_mimetype_nobody_writes_yields_nothing(self):
        self.assertEqual(get_writers("application/pdf", ROWS), ())

    def test_a_wildcard_writer_is_a_fallback(self):
        writers = get_writers("text/anything", TEXT)
        self.assertEqual([w.name for w in writers], ["text"])

    def test_an_unknown_representation_is_refused(self):
        with self.assertRaises(ValueError):
            get_writers("text/csv", "spreadsheet")

    def test_a_writer_must_name_itself(self):
        writer = BaseWriter()
        writer.mimetype = "text/csv"
        writer.consumes = ROWS
        with self.assertRaises(ValueError):
            register_writer(writer)

    def test_a_writer_must_consume_a_known_representation(self):
        writer = BaseWriter()
        writer.name = "bogus"
        writer.mimetype = "text/csv"
        writer.consumes = "spreadsheet"
        with self.assertRaises(ValueError):
            register_writer(writer)

    def test_a_writer_must_emit_a_mimetype(self):
        writer = BaseWriter()
        writer.name = "bogus"
        writer.consumes = ROWS
        with self.assertRaises(ValueError):
            register_writer(writer)

    def test_the_base_writer_writes_nothing(self):
        with self.assertRaises(NotImplementedError):
            BaseWriter().write(None)

    def test_a_wildcard_writer_applies_to_anything(self):
        writer = BaseWriter()
        writer.mimetype = ANY
        self.assertTrue(writer.applies_to("application/pdf"))


class TestOutsideRegistration(unittest.TestCase):
    def setUp(self):
        writer = BaseWriter()
        writer.name = "tsv"
        writer.mimetype = "text/tab-separated-values"
        writer.consumes = ROWS
        writer.write = lambda value, **options: "\n".join(  # type: ignore[method-assign]
            "\t".join(str(cell) for cell in row) for row in value
        ).encode()
        self.writer = register_writer(writer)
        self.addCleanup(_WRITERS[ROWS].remove, self.writer)

    def test_it_is_reachable_through_the_registry(self):
        found = get_writers("text/tab-separated-values", ROWS)
        self.assertEqual([w.name for w in found], ["tsv"])

    def test_it_does_not_displace_the_built_in(self):
        self.assertEqual([w.name for w in get_writers("text/csv", ROWS)], ["csv"])

    def test_a_document_can_be_written_through_it(self):
        document = Document.of(rows=[["a", "b"]], mimetype="text/tab-separated-values")
        self.assertEqual(document.data, b"a\tb")


class TestWriteCsv(unittest.TestCase):
    def _write(self, rows, **options):
        return get_writers("text/csv", ROWS)[0].write(rows, **options)

    def test_rows_become_csv(self):
        self.assertEqual(self._write([["a", "b"], ["c", "d"]]), b"a,b\r\nc,d\r\n")

    def test_a_separator_is_honoured(self):
        self.assertEqual(self._write([["a", "b"]], separator=";"), b"a;b\r\n")

    def test_values_go_through_the_format_layer(self):
        rows = [[datetime.date(2026, 8, 29), 1234.5, None, True]]
        self.assertEqual(self._write(rows), b"2026-08-29,1234.50,,1\r\n")

    def test_cell_options_reach_the_format_layer(self):
        rows = [[1234.5]]
        written = self._write(rows, cells={"thousand": ".", "decimal": ","})
        self.assertEqual(written, b'"1.234,50"\r\n')

    def test_a_separator_in_a_value_is_quoted(self):
        self.assertEqual(self._write([["a,b"]]), b'"a,b"\r\n')

    def test_non_ascii_survives(self):
        self.assertEqual(self._write([["Café"]]), "Café\r\n".encode())


class TestWriteJson(unittest.TestCase):
    def test_data_becomes_json(self):
        written = get_writers("application/json", DATA)[0].write({"a": 1})
        self.assertEqual(json.loads(written), {"a": 1})

    def test_non_ascii_is_not_escaped(self):
        written = get_writers("application/json", DATA)[0].write({"n": "Café"})
        self.assertIn("Café", written.decode())

    def test_a_date_falls_back_to_its_string(self):
        written = get_writers("application/json", DATA)[0].write(
            {"d": datetime.date(2026, 8, 29)}
        )
        self.assertEqual(json.loads(written), {"d": "2026-08-29"})


class TestWriteTree(unittest.TestCase):
    def test_a_tree_becomes_xml(self):
        from lxml import etree

        root = etree.Element("Invoice")
        etree.SubElement(root, "Total").text = "10.00"
        written = get_writers("application/xml", TREE)[0].write(root)
        self.assertIn(b"<Total>10.00</Total>", written)
        self.assertTrue(written.startswith(b"<?xml"))

    def test_the_declaration_can_be_dropped(self):
        from lxml import etree

        written = get_writers("application/xml", TREE)[0].write(
            etree.Element("a"), xml_declaration=False
        )
        self.assertEqual(written, b"<a/>")


class TestDocumentOf(unittest.TestCase):
    def test_rows_round_trip_through_bytes(self):
        rows = [["ref", "amount"], ["INV/1", "10.00"]]
        document = Document.of(rows=rows, name="export.csv")
        self.assertEqual(document.mimetype, "text/csv")
        self.assertEqual(document.data, b"ref,amount\r\nINV/1,10.00\r\n")

    def test_the_bytes_read_back_as_the_same_rows(self):
        rows = [["ref", "amount"], ["INV/1", "10.00"]]
        written = Document.of(rows=rows).data
        self.assertEqual(Document(written, "text/csv").rows, rows)

    def test_data_round_trips(self):
        document = Document.of(data={"total": 10})
        self.assertEqual(document.mimetype, "application/json")
        self.assertEqual(Document(document.data).data_dict, {"total": 10})

    def test_tree_round_trips(self):
        from lxml import etree

        root = etree.Element("Invoice")
        etree.SubElement(root, "Total").text = "10.00"
        document = Document.of(tree=root)
        self.assertEqual(document.mimetype, "application/xml")
        self.assertEqual(Document(document.data).tree.find("Total").text, "10.00")

    def test_text_round_trips(self):
        document = Document.of(text="Café au lait")
        self.assertEqual(document.text, "Café au lait")

    def test_the_representation_is_kept_not_reparsed(self):
        rows = [["a", 1]]
        document = Document.of(rows=rows)
        self.assertIs(document.rows, rows)

    def test_exactly_one_representation(self):
        with self.assertRaises(ValueError):
            Document.of()
        with self.assertRaises(ValueError):
            Document.of(rows=[["a"]], text="a")

    def test_a_mimetype_nobody_writes_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            Document.of(rows=[["a"]], mimetype="application/pdf")
        self.assertIn("Nothing writes rows", str(caught.exception))
