import datetime
import hashlib
import io
import re
import unittest
from typing import TYPE_CHECKING, cast
from unittest import mock

from odoo.tools import file_open
from odoo.tools.pdf import signature as pdf_signature
from odoo.tools.pdf.signature import PdfSigner

if TYPE_CHECKING:
    from odoo.addons.base.models.res_company import ResCompany

if pdf_signature.HAS_CRYPTOGRAPHY:
    from asn1crypto import cms
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
    from cryptography.x509.oid import NameOID

_BYTE_RANGE_RE = re.compile(rb"/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]")
_CONTENTS_RE = re.compile(rb"/Contents\s*<([0-9A-Fa-f]+)>")


def _self_signed(key):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pdf signature probe")])
    algorithm = None if isinstance(key, ed25519.Ed25519PrivateKey) else hashes.SHA256()
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime(2020, 1, 1))
        .not_valid_after(datetime.datetime(2040, 1, 1))
        .sign(key, algorithm)
    )


def _sample_pdf() -> io.BytesIO:
    with file_open("base/tests/minimal.pdf", "rb") as stream:
        return io.BytesIO(stream.read())


@unittest.skipUnless(
    pdf_signature.HAS_CRYPTOGRAPHY, "cryptography is not installed here"
)
class TestTheSignatureVerifies(unittest.TestCase):
    def _sign_with(self, key):
        certificate = _self_signed(key)
        signer = PdfSigner(_sample_pdf(), company=cast("ResCompany", object()))
        with mock.patch.object(
            PdfSigner,
            "_load_key_and_certificate",
            lambda _self: (key, certificate),
        ):
            signed = signer.sign_pdf()
        assert signed is not None, "the signer refused a key it declares support for"
        return signed.getvalue(), certificate

    def _parts(self, data):
        match = _BYTE_RANGE_RE.search(data)
        assert match is not None, "no /ByteRange in the signed document"
        start_a, len_a, start_b, len_b = (int(g) for g in match.groups())
        covered = data[start_a : start_a + len_a] + data[start_b : start_b + len_b]

        contents = _CONTENTS_RE.search(data)
        assert contents is not None, "no /Contents blob in the signed document"
        blob = bytes.fromhex(contents.group(1).decode())
        content_info = cms.ContentInfo.load(blob)
        padding = blob[len(content_info.dump()) :]
        assert padding.strip(b"\x00") == b"", (
            "the /Contents placeholder is padded with something other than NUL"
        )
        return (start_a, len_a, start_b, len_b), covered, content_info

    def _verify(self, key):
        data, certificate = self._sign_with(key)
        (_a, _la, start_b, len_b), covered, content_info = self._parts(data)

        self.assertEqual(
            start_b + len_b,
            len(data),
            "/ByteRange stops short of the end: the tail is unsigned",
        )

        signer_info = content_info["content"]["signer_infos"][0]
        attributes = signer_info["signed_attrs"]

        digest_name = signer_info["digest_algorithm"]["algorithm"].native
        declared = next(
            attr["values"][0].native
            for attr in attributes
            if attr["type"].native == "message_digest"
        )
        self.assertEqual(
            declared,
            hashlib.new(digest_name, covered).digest(),
            "message_digest does not describe the bytes /ByteRange covers",
        )

        tagged = bytearray(attributes.dump())
        tagged[0] = 0x31
        payload = bytes(tagged)

        public_key = certificate.public_key()
        signature = signer_info["signature"].native
        if isinstance(public_key, rsa.RSAPublicKey):
            public_key.verify(signature, payload, padding.PKCS1v15(), hashes.SHA256())
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
        else:
            public_key.verify(signature, payload)

    def test_rsa(self):
        self._verify(rsa.generate_private_key(public_exponent=65537, key_size=2048))

    def test_elliptic_curve(self):
        self._verify(ec.generate_private_key(ec.SECP256R1()))

    def test_ed25519(self):
        self._verify(ed25519.Ed25519PrivateKey.generate())

    def test_a_tampered_document_fails_the_digest(self):
        key = ec.generate_private_key(ec.SECP256R1())
        data, _certificate = self._sign_with(key)
        (start_a, len_a, start_b, len_b), _covered, content_info = self._parts(data)

        tampered = bytearray(data)
        tampered[start_a + len_a - 1] ^= 0xFF
        recovered = bytes(tampered[start_a : start_a + len_a]) + bytes(
            tampered[start_b : start_b + len_b]
        )

        signer_info = content_info["content"]["signer_infos"][0]
        declared = next(
            attr["values"][0].native
            for attr in signer_info["signed_attrs"]
            if attr["type"].native == "message_digest"
        )
        digest_name = signer_info["digest_algorithm"]["algorithm"].native
        self.assertNotEqual(
            declared,
            hashlib.new(digest_name, recovered).digest(),
            "an edit inside /ByteRange must change the digest, or the range "
            "does not cover what it claims to",
        )
