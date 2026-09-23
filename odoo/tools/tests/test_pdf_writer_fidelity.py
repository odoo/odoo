import datetime
import io
import unittest
from hashlib import md5
from unittest import mock

from pypdf import PdfWriter as PlainWriter

from odoo.tools import pdf
from odoo.tools.pdf import (
    ArrayObject,
    ByteStringObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    OdooPdfFileReader,
    OdooPdfFileWriter,
    PdfReader,
    create_string_object,
)

_XMP_PDFA_ELEMENT = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"><pdfaid:part>3</pdfaid:part><pdfaid:conformance>B</pdfaid:conformance></rdf:Description></rdf:RDF></x:xmpmeta>"""
_XMP_PDFA_ATTRIBUTE = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" pdfaid:part="2" pdfaid:conformance="B"/></rdf:RDF></x:xmpmeta>"""
_XMP_NOT_PDFA = b"""<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:format>application/pdf</dc:format></rdf:Description></rdf:RDF></x:xmpmeta>"""


def _plain_pdf(pdf_id=None, xmp=None) -> bytes:
    writer = OdooPdfFileWriter()
    writer.add_blank_page(100, 100)
    if pdf_id is not None:
        writer._ID = ArrayObject([ByteStringObject(pdf_id), ByteStringObject(pdf_id)])
    if xmp is not None:
        writer.add_file_metadata(xmp)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _clone(data: bytes) -> OdooPdfFileWriter:
    writer = OdooPdfFileWriter()
    writer.clone_reader_document_root(PdfReader(io.BytesIO(data), strict=False))
    return writer


def _written(writer: OdooPdfFileWriter) -> bytes:
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class TestPdfaIsReadFromTheXmpDeclaration(unittest.TestCase):
    def test_a_document_without_metadata_is_not_pdfa(self):
        data = _plain_pdf()
        self.assertEqual(len(data.split(b"\n", 2)[1]), 5, "the old heuristic's bait")
        self.assertFalse(_clone(data).is_pdfa)

    def test_metadata_that_declares_nothing_is_not_pdfa(self):
        self.assertFalse(_clone(_plain_pdf(xmp=_XMP_NOT_PDFA)).is_pdfa)

    def test_a_pdfaid_part_element_is_pdfa(self):
        self.assertTrue(_clone(_plain_pdf(xmp=_XMP_PDFA_ELEMENT)).is_pdfa)

    def test_a_pdfaid_part_attribute_is_pdfa(self):
        self.assertTrue(_clone(_plain_pdf(xmp=_XMP_PDFA_ATTRIBUTE)).is_pdfa)


class TestCloningKeepsTheSourceIdentity(unittest.TestCase):
    def test_the_file_identifier_survives_byte_for_byte(self):
        source_id = md5(b"odoo").digest()
        data = _plain_pdf(pdf_id=source_id)
        clone = PdfReader(io.BytesIO(_written(_clone(data))), strict=False)
        identifiers = clone.trailer.get("/ID")
        self.assertIsNotNone(identifiers, "the clone dropped the source /ID")
        for part in identifiers:
            self.assertEqual(part.original_bytes, source_id)

    def test_the_header_is_followed_by_exactly_one_eol(self):
        written = _written(_clone(_plain_pdf()))
        self.assertTrue(written.startswith(b"%PDF-1.3\n%"), written[:16])


class TestConvertToPdfa(unittest.TestCase):
    def test_a_document_without_outlines_converts(self):
        writer = _clone(_plain_pdf())
        self.assertNotIn("/Outlines", writer._root_object)
        writer.convert_to_pdfa()
        self.assertTrue(writer.is_pdfa)
        _written(writer)

    def test_a_converted_document_reads_back_as_pdfa(self):
        writer = _clone(_plain_pdf())
        writer.convert_to_pdfa()
        writer.add_file_metadata(_XMP_PDFA_ELEMENT)
        self.assertTrue(_clone(_written(writer)).is_pdfa)


class TestEmbeddedFileParameters(unittest.TestCase):
    def _embedded(self, subtype="text/xml", content=b"<x/>"):
        writer = OdooPdfFileWriter()
        writer.add_blank_page(100, 100)
        writer.add_attachment("factur-x.xml", content, subtype=subtype)
        data = _written(writer)
        reader = PdfReader(io.BytesIO(data), strict=False)
        names = reader.trailer["/Root"]["/Names"]["/EmbeddedFiles"]["/Names"]
        return data, names[1].get_object()["/EF"]["/F"].get_object()

    def test_an_escaped_subtype_is_not_escaped_twice(self):
        writer = OdooPdfFileWriter()
        self.assertEqual(writer.format_subtype("/text#2Fxml"), "/text/xml")
        self.assertEqual(writer.format_subtype("text/xml"), "/text/xml")
        data, embedded = self._embedded(subtype="/text#2Fxml")
        self.assertNotIn(b"#232F", data)
        self.assertEqual(embedded["/Subtype"], "/text/xml")

    def test_the_checksum_is_the_sixteen_byte_digest(self):
        _data, embedded = self._embedded(content=b"<invoice/>")
        checksum = embedded["/Params"]["/CheckSum"]
        self.assertEqual(checksum.original_bytes, md5(b"<invoice/>").digest())

    def test_the_modification_date_is_utc(self):
        utc_moment = datetime.datetime(2026, 1, 2, 0, 30, tzinfo=datetime.UTC)
        local_moment = datetime.datetime(2026, 1, 1, 18, 30)

        class _Clock(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return local_moment if tz is None else utc_moment.astimezone(tz)

        with mock.patch.object(pdf, "datetime", _Clock):
            _data, embedded = self._embedded()
        self.assertEqual(embedded["/Params"]["/ModDate"], "D:20260102003000+00'00'")


class TestReaderArguments(unittest.TestCase):
    def test_a_password_reaches_pypdf(self):
        writer = PlainWriter()
        writer.add_blank_page(100, 100)
        writer.encrypt("s3cret", algorithm="RC4-128")
        buffer = io.BytesIO()
        writer.write(buffer)
        reader = PdfReader(io.BytesIO(buffer.getvalue()), password="s3cret")
        self.assertEqual(len(reader.pages), 1)


class TestEmbeddedFileTreeWalk(unittest.TestCase):
    def test_a_cyclic_name_tree_yields_each_file_once(self):
        writer = PlainWriter()
        writer.add_blank_page(100, 100)
        content = DecodedStreamObject()
        content.set_data(b"<x/>")
        spec = writer._add_object(
            DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Filespec"),
                    NameObject("/F"): create_string_object("a.xml"),
                    NameObject("/EF"): DictionaryObject(
                        {NameObject("/F"): writer._add_object(content)}
                    ),
                }
            )
        )
        leaf = DictionaryObject(
            {NameObject("/Names"): ArrayObject([create_string_object("a.xml"), spec])}
        )
        leaf_ref = writer._add_object(leaf)
        leaf[NameObject("/Kids")] = ArrayObject([leaf_ref])
        writer._root_object[NameObject("/Names")] = DictionaryObject(
            {
                NameObject("/EmbeddedFiles"): DictionaryObject(
                    {NameObject("/Kids"): ArrayObject([leaf_ref])}
                )
            }
        )
        buffer = io.BytesIO()
        writer.write(buffer)
        reader = OdooPdfFileReader(io.BytesIO(buffer.getvalue()), strict=False)
        self.assertEqual(list(reader.get_attachments()), [("a.xml", b"<x/>")])


if __name__ == "__main__":
    unittest.main()
