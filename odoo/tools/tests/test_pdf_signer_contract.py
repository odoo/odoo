import io
import unittest
from typing import Any
from unittest import mock

from odoo.tools import file_open
from odoo.tools.pdf import NameObject
from odoo.tools.pdf import signature as pdf_signature
from odoo.tools.pdf.signature import PdfSigner


def _sample_pdf() -> io.BytesIO:
    with file_open("base/tests/minimal.pdf", "rb") as stream:
        return io.BytesIO(stream.read())


_ANY_COMPANY: Any = object()


class _WriterWithoutClone:
    pass


class TestSignPdfKeepsItsContract(unittest.TestCase):
    def test_an_unusable_pypdf_yields_none_rather_than_raising(self):
        with mock.patch.object(pdf_signature, "PdfWriter", _WriterWithoutClone):
            signer = PdfSigner(_sample_pdf(), company=_ANY_COMPANY)
            self.assertFalse(signer.usable)
            self.assertIsNone(signer.sign_pdf())

    def test_the_object_is_never_left_half_built(self):
        with mock.patch.object(pdf_signature, "PdfWriter", _WriterWithoutClone):
            signer = PdfSigner(_sample_pdf(), company=_ANY_COMPANY)
        for attribute in ("writer", "usable", "company", "signing_time"):
            with self.subTest(attribute=attribute):
                self.assertTrue(hasattr(signer, attribute))

    def test_no_company_yields_none(self):
        self.assertIsNone(PdfSigner(_sample_pdf()).sign_pdf())

    def test_absent_cryptography_yields_none(self):
        with mock.patch.object(pdf_signature, "HAS_CRYPTOGRAPHY", False):
            signer = PdfSigner(_sample_pdf(), company=_ANY_COMPANY)
            self.assertIsNone(signer.sign_pdf())

    def test_availability_is_one_flag_not_ten_names(self):
        self.assertIsInstance(pdf_signature.HAS_CRYPTOGRAPHY, bool)
        if pdf_signature.HAS_CRYPTOGRAPHY:
            for name in (
                "hashes",
                "ec",
                "ed25519",
                "padding",
                "rsa",
                "Encoding",
                "Certificate",
                "PrivateKeyTypes",
                "load_pem_private_key",
                "load_pem_x509_certificate",
            ):
                with self.subTest(name=name):
                    self.assertIsNotNone(getattr(pdf_signature, name, None))


if __name__ == "__main__":
    unittest.main()


class TestSetIdentifier(unittest.TestCase):
    def test_the_identifier_is_stored_on_the_instance(self):
        from odoo.tools.pdf import OdooPdfFileWriter

        writer = OdooPdfFileWriter()
        writer._set_id("some-id")
        self.assertEqual(writer._ID, "some-id")

    def test_a_falsy_identifier_is_ignored(self):
        from odoo.tools.pdf import OdooPdfFileWriter

        writer = OdooPdfFileWriter()
        writer._set_id(None)
        self.assertFalse(writer._ID)

    def test_id_is_an_instance_attribute_not_a_class_one(self):
        from pypdf import PdfWriter

        self.assertFalse(hasattr(PdfWriter, "_ID"))
        self.assertTrue(hasattr(PdfWriter(), "_ID"))


class TestRotatePdf(unittest.TestCase):
    def test_every_page_is_rotated(self):
        from odoo.tools.pdf import PdfReader, rotate_pdf

        rotated = PdfReader(io.BytesIO(rotate_pdf(_sample_pdf().getvalue())))
        self.assertTrue(len(rotated.pages))
        for index, page in enumerate(rotated.pages):
            with self.subTest(page=index):
                self.assertEqual(page.get("/Rotate"), 90)


class TestByteRangeDoesNotMoveThePlaceholder(unittest.TestCase):
    PLACEHOLDER = b"<" + b"0" * (PdfSigner._CONTENTS_PLACEHOLDER_BYTES * 2) + b">"

    def _prepared_signer(self):
        signer = PdfSigner(_sample_pdf(), company=_ANY_COMPANY)
        _field, value = signer._setup_form(False, "Odoo Signature", None)
        return signer, value

    def _placeholder_span(self, data):
        start = data.find(b"Contents", data.rfind(b"/FT /Sig")) + 9
        return start, start + PdfSigner._CONTENTS_PLACEHOLDER_BYTES * 2 + 2

    def test_contents_serialises_before_byte_range(self):
        signer, _value = self._prepared_signer()
        data = signer._prepare_document_bytes()
        field = data.rfind(b"/FT /Sig")
        self.assertLess(
            data.find(b"/Contents", field),
            data.find(b"/ByteRange", field),
            "/ByteRange ahead of /Contents would move the placeholder under the digest",
        )

    def test_writing_the_real_byte_range_leaves_the_placeholder_put(self):
        signer, value = self._prepared_signer()
        data = signer._prepare_document_bytes()
        start, end = self._placeholder_span(data)
        self.assertEqual(data[start:end], self.PLACEHOLDER)

        value.update(
            {
                NameObject("/ByteRange"): signer._create_number_array_object(
                    [0, start, end, abs(len(data) - end)]
                )
            }
        )
        after = signer._prepare_document_bytes()
        self.assertGreater(len(after), len(data), "the fill-in should lengthen it")
        self.assertEqual(
            after[start:end],
            self.PLACEHOLDER,
            "writing /ByteRange moved the /Contents placeholder",
        )
