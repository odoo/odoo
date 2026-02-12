import base64
import uuid
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from lxml import etree


class XadesSigner:
    """
    Handles the creation of XAdES-BES signatures for KSeF authentication challenges.
    """
    def __init__(self, key_pem, cert_pem, private_key_password=None):
        self.private_key = serialization.load_pem_private_key(key_pem, password=private_key_password)
        self.cert = x509.load_pem_x509_certificate(cert_pem)

    @staticmethod
    def _calculate_digest(node):
        c14n_node = etree.tostring(node, method="c14n", exclusive=True, with_comments=False, strip_text=False)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(c14n_node)
        return base64.b64encode(digest.finalize()).decode('utf-8')

    def _der_to_raw_ecdsa(self, signature):
        r, s = decode_dss_signature(signature)
        key_size = (self.private_key.curve.key_size + 7) // 8
        return r.to_bytes(key_size, 'big') + s.to_bytes(key_size, 'big')

    def _build_qualifying_properties(self, signature_node, sig_id, props_id):
        NS_DS = "http://www.w3.org/2000/09/xmldsig#"
        NS_XADES = "http://uri.etsi.org/01903/v1.3.2#"

        object_node = etree.SubElement(signature_node, etree.QName(NS_DS, "Object"))
        qualifying_props_node = etree.SubElement(object_node, etree.QName(NS_XADES, "QualifyingProperties"), Target=f"#{sig_id}")
        signed_props_node = etree.SubElement(qualifying_props_node, etree.QName(NS_XADES, "SignedProperties"), Id=props_id)
        signed_sig_props_node = etree.SubElement(signed_props_node, etree.QName(NS_XADES, "SignedSignatureProperties"))

        now = datetime.now(timezone.utc)
        etree.SubElement(signed_sig_props_node, etree.QName(NS_XADES, "SigningTime")).text = now.strftime('%Y-%m-%dT%H:%M:%SZ')

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

        return self._calculate_digest(signed_props_node)

    def sign_authentication_challenge(self, challenge_code, nip):
        xml_to_sign_str = f'<AuthTokenRequest xmlns="http://ksef.mf.gov.pl/auth/token/2.0"><Challenge>{challenge_code}</Challenge><ContextIdentifier><Nip>{nip}</Nip></ContextIdentifier><SubjectIdentifierType>certificateSubject</SubjectIdentifierType></AuthTokenRequest>'
        root = etree.fromstring(xml_to_sign_str)

        is_rsa = isinstance(self.private_key, rsa.RSAPrivateKey)
        sig_alg_uri = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256" if is_rsa else "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"

        NS_DS = "http://www.w3.org/2000/09/xmldsig#"
        nsmap = {'ds': NS_DS}
        sig_id, props_id = f"signature-{uuid.uuid4()}", f"signedprops-{uuid.uuid4()}"

        signature_node = etree.SubElement(root, etree.QName(NS_DS, "Signature"), Id=sig_id, nsmap={'ds': NS_DS, 'xades': "http://uri.etsi.org/01903/v1.3.2#"})
        signed_info_node = etree.SubElement(signature_node, etree.QName(NS_DS, "SignedInfo"))
        etree.SubElement(signed_info_node, etree.QName(NS_DS, "CanonicalizationMethod"), Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")
        etree.SubElement(signed_info_node, etree.QName(NS_DS, "SignatureMethod"), Algorithm=sig_alg_uri)

        ref1 = etree.SubElement(signed_info_node, etree.QName(NS_DS, "Reference"), Id=f"reference-{uuid.uuid4()}", URI="")
        etree.SubElement(etree.SubElement(ref1, etree.QName(NS_DS, "Transforms")), etree.QName(NS_DS, "Transform"), Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature")
        etree.SubElement(ref1, etree.QName(NS_DS, "DigestMethod"), Algorithm="http://www.w3.org/2001/04/xmlenc#sha256")
        digest1_node = etree.SubElement(ref1, etree.QName(NS_DS, "DigestValue"))

        ref2 = etree.SubElement(signed_info_node, etree.QName(NS_DS, "Reference"), Type="http://uri.etsi.org/01903#SignedProperties", URI=f"#{props_id}")
        etree.SubElement(etree.SubElement(ref2, etree.QName(NS_DS, "Transforms")), etree.QName(NS_DS, "Transform"), Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")
        etree.SubElement(ref2, etree.QName(NS_DS, "DigestMethod"), Algorithm="http://www.w3.org/2001/04/xmlenc#sha256")
        digest2_node = etree.SubElement(ref2, etree.QName(NS_DS, "DigestValue"))

        temp_root = etree.fromstring(etree.tostring(root))
        temp_root.xpath("./ds:Signature", namespaces=nsmap)[0].getparent().remove(temp_root.xpath("./ds:Signature", namespaces=nsmap)[0])
        digest1_node.text = self._calculate_digest(temp_root)
        digest2_node.text = self._build_qualifying_properties(signature_node, sig_id, props_id)

        signed_info_c14n = etree.tostring(signed_info_node, method="c14n", exclusive=True, with_comments=False)

        if is_rsa:
            signature_val = self.private_key.sign(signed_info_c14n, padding.PKCS1v15(), hashes.SHA256())
        else:
            der_sig = self.private_key.sign(signed_info_c14n, ec.ECDSA(hashes.SHA256()))
            signature_val = self._der_to_raw_ecdsa(der_sig)

        etree.SubElement(signature_node, etree.QName(NS_DS, "SignatureValue")).text = base64.b64encode(signature_val).decode('utf-8')

        key_info_node = etree.SubElement(signature_node, etree.QName(NS_DS, "KeyInfo"))
        x509_data = etree.SubElement(key_info_node, etree.QName(NS_DS, "X509Data"))
        cert_pem = self.cert.public_bytes(serialization.Encoding.PEM)
        etree.SubElement(x509_data, etree.QName(NS_DS, "X509Certificate")).text = "".join(cert_pem.decode('utf-8').splitlines()[1:-1])

        object_node = signature_node.xpath("./ds:Object", namespaces=nsmap)[0]
        signature_node.append(object_node)

        return etree.tostring(root, xml_declaration=True, encoding="utf-8", standalone="no").decode('utf-8')
