import base64
from copy import deepcopy
from cryptography.exceptions import InvalidSignature

import lxml

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.account.tools.xml_verifier.xml_verifier import validate_xmldsig_signature, validate_xades_signature, _verify_signed_properties

from odoo.tools import file_open


@tagged('standard', 'at_install')
class XMLVerifierTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.XMLSIG_NSMAP = {"ds": "http://www.w3.org/2000/09/xmldsig#", "xades": "http://uri.etsi.org/01903/v1.3.2#"}

        with file_open("account/tools/xml_verifier/xades_signed.xml", "rt") as f:
            cls.xades_sample = lxml.etree.fromstring(f.read().encode())

        cls.signature_node = cls.xades_sample.find('ds:Signature', namespaces=cls.XMLSIG_NSMAP)
        return res

    def test_xmldsig_verification(self):
        validate_xmldsig_signature(self.signature_node)

        # Invalid reference digest value.
        signature_with_wrong_digest = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_with_wrong_digest.find(".//ds:DigestValue", namespaces=self.XMLSIG_NSMAP).text = base64.b64encode(str.encode("Wrong Digest"))
        with self.assertRaises(InvalidSignature, msg="Should throw a InvalidSignature when the references are not valid"):
            validate_xmldsig_signature(signature_with_wrong_digest)

        # Signature method not found.
        signature_with_invalid_method = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_with_invalid_method.find(".//ds:SignatureMethod", namespaces=self.XMLSIG_NSMAP).set("Algorithm", "New signature")
        with self.assertRaises(ValueError, msg="Should throw a ValueError when the signature method is not found"):
            validate_xmldsig_signature(signature_with_invalid_method)

        # Reference URI not found.
        signature_with_invalid_uri = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_with_invalid_uri.findall(".//ds:Reference", namespaces=self.XMLSIG_NSMAP)[1].set("URI", "#Invalid-URI")
        with self.assertRaises(ValueError, msg="Should throw a ValueError when reference URI is not found"):
            validate_xmldsig_signature(signature_with_invalid_uri)

        # Invalid signature.
        signature_invalid = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_invalid.find("ds:SignatureValue", namespaces=self.XMLSIG_NSMAP).text = base64.b64encode(str.encode("Wrong Signature"))
        with self.assertRaises(InvalidSignature, msg="Should throw an InvalidSignature when signature is invalid"):
            validate_xmldsig_signature(signature_invalid)

    def test_xades_verification(self):
        validate_xades_signature(self.signature_node)

        # Invalid signature time.
        signature_with_invalid_time = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_with_invalid_time.find(".//xades:SigningTime", namespaces=self.XMLSIG_NSMAP).text = "1980-08-25T10:34:05.454232"
        signed_properties_node = signature_with_invalid_time.find(
            "ds:Object/xades:QualifyingProperties["
            "@Target='#{}']/xades:SignedProperties".format(signature_with_invalid_time.get("Id")),
            namespaces=self.XMLSIG_NSMAP,
        )
        with self.assertRaises(InvalidSignature, msg="Should throw a InvalidSignature when signature time is invalid"):
            _verify_signed_properties(signed_properties_node, signature_with_invalid_time)

        # Invalid x509 serial number.
        signature_with_invalid_serial_number = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_with_invalid_serial_number.find(".//ds:X509SerialNumber", namespaces=self.XMLSIG_NSMAP).text = "00000"
        signed_properties_node = signature_with_invalid_serial_number.find(
            "ds:Object/xades:QualifyingProperties["
            "@Target='#{}']/xades:SignedProperties".format(signature_with_invalid_serial_number.get("Id")),
            namespaces=self.XMLSIG_NSMAP,
        )
        with self.assertRaises(InvalidSignature, msg="Should throw a InvalidSignature when serial number is invalid"):
            _verify_signed_properties(signed_properties_node, signature_with_invalid_serial_number)

        # Invalid x509 issuer name.
        signature_with_invalid_issuer_name = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_with_invalid_issuer_name.find(".//ds:X509IssuerName", namespaces=self.XMLSIG_NSMAP).text = "Invalid-Issuer"
        signed_properties_node = signature_with_invalid_issuer_name.find(
            "ds:Object/xades:QualifyingProperties["
            "@Target='#{}']/xades:SignedProperties".format(signature_with_invalid_issuer_name.get("Id")),
            namespaces=self.XMLSIG_NSMAP,
        )
        with self.assertRaises(InvalidSignature, msg="Should throw a InvalidSignature when issuer name is invalid"):
            _verify_signed_properties(signed_properties_node, signature_with_invalid_issuer_name)

        # Invalid digest.
        signature_with_invalid_digest = deepcopy(self.xades_sample).find('ds:Signature', namespaces=self.XMLSIG_NSMAP)
        signature_with_invalid_digest.find(".//xades:CertDigest/ds:DigestValue", namespaces=self.XMLSIG_NSMAP).text = base64.b64encode(str.encode("Wrong Digest"))
        signed_properties_node = signature_with_invalid_digest.find(
            "ds:Object/xades:QualifyingProperties["
            "@Target='#{}']/xades:SignedProperties".format(signature_with_invalid_digest.get("Id")),
            namespaces=self.XMLSIG_NSMAP,
        )
        with self.assertRaises(InvalidSignature, msg="Should throw a InvalidSignature when digest invalid"):
            _verify_signed_properties(signed_properties_node, signature_with_invalid_digest)
