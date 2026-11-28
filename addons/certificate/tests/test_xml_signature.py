import base64
import hashlib
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

from odoo.tests import TransactionCase, tagged

from odoo.addons.certificate.tools.xml_signature import NSMAP

DOCUMENT = b"""<Document xmlns="urn:test:document"><Header><Number>0001</Number></Header><Line amount="10.50">Service</Line></Document>"""
POLICY = {
    'identifier': 'https://example.com/signature_policy.pdf',
    'digest': 'DWxin1xWOeI8OuWQXazh4VjLWAaCLAA954em7DMh0h8=',
    'description': 'Test policy',
}


@tagged('post_install', '-at_install')
class TestXmlSignature(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.certificate = cls.env['certificate.certificate'].create({
            'name': 'Test PKCS12 Certificate',
            'pkcs12_password': 'example',
            'content': cls.file_read('certificate/tests/data/cert.pfx'),
        })
        cls.signing_time = datetime(2026, 11, 19, 15, 0, 0, tzinfo=timezone(timedelta(hours=-6)))

    def _sign(self, **kwargs):
        """Sign DOCUMENT and return the signed document, serialized then parsed again as a receiver does."""
        root = etree.fromstring(DOCUMENT)
        self.certificate._sign_xml_xades(root, signing_time=self.signing_time, signature_id='id-test', **kwargs)
        return etree.fromstring(etree.tostring(root, encoding='UTF-8'))

    def _c14n(self, node, exclusive=False):
        return etree.tostring(node, method='c14n', exclusive=exclusive, with_comments=False)

    def _digest(self, data):
        return base64.b64encode(hashlib.sha256(data).digest()).decode()

    def _get_reference(self, signature, uri):
        return signature.find(f"ds:SignedInfo/ds:Reference[@URI='{uri}']", NSMAP)

    def _assert_signature_valid(self, signed, exclusive=False):
        """Check the signature of `signed` from scratch, without the code that produced it."""
        signature = signed.find('ds:Signature', NSMAP)

        # The document reference is the document as it was before signing
        self.assertEqual(
            self._get_reference(signature, '').findtext('ds:DigestValue', namespaces=NSMAP),
            self._digest(self._c14n(etree.fromstring(DOCUMENT), exclusive)),
        )
        # The certificate and the signed properties, in the context of the signed document
        for uri, xpath in (('#id-test-keyinfo', 'ds:KeyInfo'), ('#id-test-signedprops', 'ds:Object/xades:QualifyingProperties/xades:SignedProperties')):
            self.assertEqual(
                self._get_reference(signature, uri).findtext('ds:DigestValue', namespaces=NSMAP),
                self._digest(self._c14n(signature.find(xpath, NSMAP), exclusive)),
            )
        # The signature value is the RSA-SHA256 signature of the canonical SignedInfo
        cert = x509.load_pem_x509_certificate(self.certificate.pem_certificate.content)
        cert.public_key().verify(
            base64.b64decode(signature.findtext('ds:SignatureValue', namespaces=NSMAP)),
            self._c14n(signature.find('ds:SignedInfo', NSMAP), exclusive),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

    def test_sign_xml_xades_epes_inclusive(self):
        signed = self._sign(policy=POLICY)

        signature = signed[-1]
        self.assertEqual(signature.tag, f"{{{NSMAP['ds']}}}Signature")
        self.assertEqual(signature.get('Id'), 'id-test')
        self.assertEqual(
            signature.find('ds:SignedInfo/ds:CanonicalizationMethod', NSMAP).get('Algorithm'),
            'http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
        )
        signed_signature_properties = signature.find('.//xades:SignedSignatureProperties', NSMAP)
        self.assertEqual(signed_signature_properties.findtext('xades:SigningTime', namespaces=NSMAP), '2026-11-19T15:00:00-06:00')
        self.assertEqual(
            signed_signature_properties.findtext('xades:SigningCertificate/xades:Cert/xades:CertDigest/ds:DigestValue', namespaces=NSMAP),
            self.certificate._get_fingerprint_bytes(formatting='base64').decode(),
        )
        self.assertEqual(
            signed_signature_properties.findtext('.//xades:SigPolicyId/xades:Identifier', namespaces=NSMAP),
            POLICY['identifier'],
        )
        self.assertEqual(
            signed_signature_properties.findtext('.//xades:SigPolicyHash/ds:DigestValue', namespaces=NSMAP),
            POLICY['digest'],
        )
        self._assert_signature_valid(signed)

    def test_sign_xml_xades_bes_exclusive(self):
        signed = self._sign(canonicalization='exclusive')

        signature = signed.find('ds:Signature', NSMAP)
        self.assertIsNone(signature.find('.//xades:SignaturePolicyIdentifier', NSMAP))
        self.assertEqual(
            [transform.get('Algorithm') for transform in self._get_reference(signature, '').iterfind('ds:Transforms/ds:Transform', NSMAP)],
            ['http://www.w3.org/2000/09/xmldsig#enveloped-signature', 'http://www.w3.org/2001/10/xml-exc-c14n#'],
        )
        self._assert_signature_valid(signed, exclusive=True)

    def test_sign_xml_xades_detects_tampering(self):
        signed = self._sign(policy=POLICY)
        signed.find('{urn:test:document}Line').set('amount', '1000.00')

        signature = signed.find('ds:Signature', NSMAP)
        signature.getparent().remove(signature)
        self.assertNotEqual(
            self._get_reference(signature, '').findtext('ds:DigestValue', namespaces=NSMAP),
            self._digest(self._c14n(signed)),
        )

        signed_info = signature.find('ds:SignedInfo', NSMAP)
        self._get_reference(signature, '').find('ds:DigestValue', NSMAP).text = self._digest(self._c14n(signed))
        cert = x509.load_pem_x509_certificate(self.certificate.pem_certificate.content)
        with self.assertRaises(InvalidSignature):
            cert.public_key().verify(
                base64.b64decode(signature.findtext('ds:SignatureValue', namespaces=NSMAP)),
                self._c14n(signed_info),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
