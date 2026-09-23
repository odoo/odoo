import datetime
import io
import types
import unittest
from typing import TYPE_CHECKING, Any, cast
from unittest import mock

from odoo.tools.pdf import PdfReader
from odoo.tools.pdf import signature as pdf_signature
from odoo.tools.pdf.signature import PdfSigner

if TYPE_CHECKING:
    from odoo.addons.base.models.res_company import ResCompany

if pdf_signature.HAS_CRYPTOGRAPHY:
    from asn1crypto import cms
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

_ANY_COMPANY = cast("ResCompany", object())


def _form_pdf() -> io.BytesIO:
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    page.acroForm.textfield(name="customer_name", x=50, y=700, width=200, height=20)
    page.showPage()
    page.save()
    buffer.seek(0)
    return buffer


def _field_names(data: bytes) -> list[str]:
    reader = PdfReader(io.BytesIO(data), strict=False)
    fields = reader.trailer["/Root"]["/AcroForm"]["/Fields"]
    return [field.get_object()["/T"] for field in fields]


def _signature_annotation(data: bytes) -> Any:
    reader = PdfReader(io.BytesIO(data), strict=False)
    return next(
        annot.get_object()
        for annot in reader.pages[0]["/Annots"]
        if annot.get_object().get("/FT") == "/Sig"
    )


class _Signer:
    name = "José Pérez"
    email = "jp@example.mx"


@unittest.skipUnless(
    pdf_signature.HAS_CRYPTOGRAPHY, "cryptography is not installed here"
)
class TestSigningAFilledForm(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "form probe")])
        self.certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(self.key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime(2020, 1, 1))
            .not_valid_after(datetime.datetime(2040, 1, 1))
            .sign(self.key, hashes.SHA256())
        )

    def _sign(self, signer: PdfSigner, **kwargs) -> bytes:
        with mock.patch.object(
            PdfSigner,
            "_load_key_and_certificate",
            lambda _self: (self.key, self.certificate),
        ):
            signed = signer.sign_pdf(**kwargs)
        assert signed is not None
        return signed.getvalue()

    def test_the_form_keeps_its_fields(self):
        self.assertEqual(_field_names(_form_pdf().getvalue()), ["customer_name"])
        data = self._sign(PdfSigner(_form_pdf(), company=_ANY_COMPANY))
        self.assertEqual(_field_names(data), ["customer_name", "Odoo Signature"])

    def test_one_moment_names_the_signature_everywhere(self):
        ticks = iter(
            [
                datetime.datetime(2026, 3, 4, 5, 6, 7, tzinfo=datetime.UTC),
                datetime.datetime(2026, 3, 4, 5, 6, 59, tzinfo=datetime.UTC),
            ]
        )

        class _Clock(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return next(ticks)

        clock = types.SimpleNamespace(datetime=_Clock, UTC=datetime.UTC)
        with mock.patch.object(pdf_signature, "datetime", clock):
            signer = PdfSigner(_form_pdf(), company=_ANY_COMPANY)
            data = self._sign(signer)

        self.assertEqual(
            _signature_annotation(data)["/V"].get_object()["/M"], "D:20260304050607Z"
        )
        blob = bytes(_signature_annotation(data)["/V"].get_object()["/Contents"])
        content_info = cms.ContentInfo.load(blob)
        attributes = content_info["content"]["signer_infos"][0]["signed_attrs"]
        signing_time = next(
            attr["values"][0].native
            for attr in attributes
            if attr["type"].native == "signing_time"
        )
        self.assertEqual(
            signing_time, datetime.datetime(2026, 3, 4, 5, 6, 7, tzinfo=datetime.UTC)
        )

    def test_a_naive_signing_time_is_read_as_utc(self):
        signer = PdfSigner(
            _form_pdf(),
            company=_ANY_COMPANY,
            signing_time=datetime.datetime(2026, 1, 2, 3, 4, 5),
        )
        data = self._sign(signer)
        self.assertEqual(
            _signature_annotation(data)["/V"].get_object()["/M"], "D:20260102030405Z"
        )


class TestVisibleAppearanceEncoding(unittest.TestCase):
    def test_accented_names_are_drawn_in_the_declared_encoding(self):
        signer = PdfSigner(_form_pdf(), company=_ANY_COMPANY)
        field, _value = signer._setup_form(True, "Odoo Signature", cast("Any", _Signer))
        appearance = field["/AP"]["/N"]
        font = appearance["/Resources"]["/Font"]["/F1"]
        self.assertEqual(font["/Encoding"], "/WinAnsiEncoding")
        self.assertIn(
            "Digitally signed by José Pérez <jp@example.mx>".encode("cp1252"),
            appearance._data,
        )
        self.assertNotIn("é".encode(), appearance._data)


if __name__ == "__main__":
    unittest.main()
