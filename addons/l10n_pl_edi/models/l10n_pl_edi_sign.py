# -*- coding: utf-8 -*-
import base64
import uuid
from datetime import datetime, timezone

from odoo import _
from odoo.exceptions import UserError


from lxml import etree
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding


class XadesSigner:
    """
    Handles the creation of XAdES-BES signatures for KSeF authentication challenges.
    This utility isolates the complex cryptographic and XML canonicalization logic
    from the Odoo models.
    """
    def __init__(self, cert_content):
        """
        Initializes the signer with the certificate and private key.
        :param cert_content: The PEM-encoded certificate and private key as bytes.
        """
        if not cert_content:
            raise UserError(_("KSeF certificate and private key are not set."))
        try:
            self.private_key = serialization.load_pem_private_key(cert_content, password=None)
            self.cert = x509.load_pem_x509_certificate(cert_content)
        except ValueError:
            raise UserError(_("The provided file is not a valid certificate/private key."))

    def _get_xml_to_sign(self, challenge_code, nip):
        """Generates the initial XML document to be signed."""
        xml_to_sign_str = f"""
        <AuthTokenRequest xmlns="http://ksef.mf.gov.pl/auth/token/2.0">
        <Challenge>{challenge_code}</Challenge>
        <ContextIdentifier>
            <Nip>{nip}</Nip>
        </ContextIdentifier>
        <SubjectIdentifierType>certificateSubject</SubjectIdentifierType>
        </AuthTokenRequest>"""
        parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
        return etree.fromstring(xml_to_sign_str.encode('utf-8'), parser)

    def _calculate_digest(self, node):
        """Canonicalizes and hashes an XML node using SHA256."""
        c14n_node = etree.tostring(node, method="c14n", exclusive=False, with_comments=False, strip_text=True)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(c14n_node)
        return base64.b64encode(digest.finalize()).decode('utf-8')

    def _build_qualifying_properties(self, signature_node, sig_id, props_id):
        """Builds and appends the XAdES <ds:Object> to the signature."""
        NS_DS = "http://www.w3.org/2000/09/xmldsig#"
        NS_XADES = "http://uri.etsi.org/01903/v1.3.2#"

        object_node = etree.SubElement(signature_node, etree.QName(NS_DS, "Object"))
        qualifying_props_node = etree.SubElement(object_node, etree.QName(NS_XADES, "QualifyingProperties"), Target=f"#{sig_id}")
        signed_props_node = etree.SubElement(qualifying_props_node, etree.QName(NS_XADES, "SignedProperties"), Id=props_id)
        signed_sig_props_node = etree.SubElement(signed_props_node, etree.QName(NS_XADES, "SignedSignatureProperties"))

        now = datetime.now(timezone.utc).astimezone()
        etree.SubElement(signed_sig_props_node, etree.QName(NS_XADES, "SigningTime")).text = now.isoformat(timespec='milliseconds')

        signing_cert_node = etree.SubElement(signed_sig_props_node, etree.QName(NS_XADES, "SigningCertificate"))
        cert_node = etree.SubElement(signing_cert_node, etree.QName(NS_XADES, "Cert"))
        cert_digest_node = etree.SubElement(cert_node, etree.QName(NS_XADES, "CertDigest"))
        etree.SubElement(cert_digest_node, etree.QName(NS_DS, "DigestMethod"), Algorithm="http://www.w3.org/2001/04/xmlenc#sha256")

        cert_digest = hashes.Hash(hashes.SHA256())
        cert_digest.update(self.cert.public_bytes(serialization.Encoding.DER))
        etree.SubElement(cert_digest_node, etree.QName(NS_DS, "DigestValue")).text = base64.b64encode(cert_digest.finalize()).decode('utf-8')

        issuer_serial_node = etree.SubElement(cert_node, etree.QName(NS_XADES, "IssuerSerial"))
        etree.SubElement(issuer_serial_node, etree.QName(NS_DS, "X509IssuerName")).text = self.cert.issuer.rfc4514_string()
        etree.SubElement(issuer_serial_node, etree.QName(NS_DS, "X509SerialNumber")).text = str(self.cert.serial_number)
        signed_props_node_digest = self._calculate_digest(signed_props_node)

        return signed_props_node_digest

    def sign_authentication_challenge(self, challenge_code, nip):
        """Main function to generate the complete XAdES signature."""
        root = self._get_xml_to_sign(challenge_code, nip)

        NS_DS = "http://www.w3.org/2000/09/xmldsig#"
        nsmap = {'ds': NS_DS}
        sig_id, props_id = f"signature-{uuid.uuid4()}", f"signedprops-{uuid.uuid4()}"

        signature_node = etree.SubElement(root, etree.QName(NS_DS, "Signature"), Id=sig_id, nsmap={'ds': NS_DS, 'xades': "http://uri.etsi.org/01903/v1.3.2#"})
        signed_info_node = etree.SubElement(signature_node, etree.QName(NS_DS, "SignedInfo"))
        etree.SubElement(signed_info_node, etree.QName(NS_DS, "CanonicalizationMethod"), Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        etree.SubElement(signed_info_node, etree.QName(NS_DS, "SignatureMethod"), Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")

        ref1 = etree.SubElement(signed_info_node, etree.QName(NS_DS, "Reference"), Id=f"reference-{uuid.uuid4()}", URI="")
        etree.SubElement(etree.SubElement(ref1, etree.QName(NS_DS, "Transforms")), etree.QName(NS_DS, "Transform"), Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature")
        etree.SubElement(ref1, etree.QName(NS_DS, "DigestMethod"), Algorithm="http://www.w3.org/2001/04/xmlenc#sha256")
        digest1_node = etree.SubElement(ref1, etree.QName(NS_DS, "DigestValue"))

        ref2 = etree.SubElement(signed_info_node, etree.QName(NS_DS, "Reference"), Type="http://uri.etsi.org/01903#SignedProperties", URI=f"#{props_id}")
        etree.SubElement(etree.SubElement(ref2, etree.QName(NS_DS, "Transforms")), etree.QName(NS_DS, "Transform"), Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        etree.SubElement(ref2, etree.QName(NS_DS, "DigestMethod"), Algorithm="http://www.w3.org/2001/04/xmlenc#sha256")
        digest2_node = etree.SubElement(ref2, etree.QName(NS_DS, "DigestValue"))

        temp_root = etree.fromstring(etree.tostring(root))
        temp_root.xpath("./ds:Signature", namespaces=nsmap)[0].getparent().remove(temp_root.xpath("./ds:Signature", namespaces=nsmap)[0])
        digest1_node.text = self._calculate_digest(temp_root)
        digest2_node.text =  self._build_qualifying_properties(signature_node, sig_id, props_id)

        signature_value = self.private_key.sign(
            etree.tostring(signed_info_node, method="c14n", exclusive=False, with_comments=False, strip_text=True),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        etree.SubElement(signature_node, etree.QName(NS_DS, "SignatureValue")).text = base64.b64encode(signature_value).decode('utf-8')

        key_info_node = etree.SubElement(signature_node, etree.QName(NS_DS, "KeyInfo"))
        x509_data = etree.SubElement(key_info_node, etree.QName(NS_DS, "X509Data"))
        cert_pem = self.cert.public_bytes(serialization.Encoding.PEM)
        etree.SubElement(x509_data, etree.QName(NS_DS, "X509Certificate")).text = "".join(cert_pem.decode('utf-8').splitlines()[1:-1])

        object_node = signature_node.xpath("./ds:Object", namespaces=nsmap)[0]
        signature_node.append(object_node)

        return etree.tostring(root, xml_declaration=True, encoding="utf-8", standalone="no").decode('utf-8')
