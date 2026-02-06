# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""XMLDSig / XAdES-BES signer for DIAN Colombian electronic invoicing.

Implements the enveloped XML digital signature per:
- W3C XML Signature Syntax and Processing (XMLDSig)
- ETSI TS 101 903 (XAdES) v1.3.2
- DIAN Technical Annex v1.9 requirements

The signature is placed as a second ext:UBLExtension within the UBL document.
"""

import base64
import hashlib
import logging
import uuid
from datetime import datetime
from lxml import etree

_logger = logging.getLogger(__name__)

# Namespace constants
NS_DS = 'http://www.w3.org/2000/09/xmldsig#'
NS_XADES = 'http://uri.etsi.org/01903/v1.3.2#'
NS_XADES141 = 'http://uri.etsi.org/01903/v1.4.1#'
NS_EXT = 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'

NSMAP_DS = {'ds': NS_DS}
NSMAP_XADES = {'xades': NS_XADES}

C14N_ALG = 'http://www.w3.org/2001/10/xml-exc-c14n#'
SIGNATURE_ALG_RSA = 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256'
SIGNATURE_ALG_ECDSA = 'http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256'
DIGEST_ALG = 'http://www.w3.org/2001/04/xmlenc#sha256'
ENVELOPED_SIGNATURE_TRANSFORM = 'http://www.w3.org/2000/09/xmldsig#enveloped-signature'


def _tag(ns, local):
    """Create a Clark notation tag."""
    return '{%s}%s' % (ns, local)


def _calculate_digest(node):
    """Compute SHA-256 digest of an XML node after exclusive C14N."""
    c14n_bytes = etree.tostring(node, method='c14n', exclusive=True, with_comments=False)
    digest = hashlib.sha256(c14n_bytes).digest()
    return base64.b64encode(digest).decode('utf-8')


def _calculate_document_digest(tree, signature_node):
    """Compute SHA-256 digest of the document excluding the signature.

    Per XMLDSig enveloped-signature transform, the Signature element
    is removed from the document before computing the digest.
    """
    # Work on a copy to avoid modifying the original
    root = tree.getroottree().getroot()
    root_copy = etree.fromstring(etree.tostring(root))

    # Find and remove the signature node from the copy
    for sig in root_copy.iter(_tag(NS_DS, 'Signature')):
        sig.getparent().remove(sig)
        break

    c14n_bytes = etree.tostring(root_copy, method='c14n', exclusive=True, with_comments=False)
    digest = hashlib.sha256(c14n_bytes).digest()
    return base64.b64encode(digest).decode('utf-8')


class DianXmlSigner:
    """Signs UBL 2.1 XML documents with XMLDSig/XAdES-BES for DIAN compliance.

    Usage:
        signer = DianXmlSigner(p12_data, password)
        signed_xml = signer.sign(unsigned_xml)
    """

    def __init__(self, p12_data, password):
        """Load the PKCS#12 (.p12/.pfx) certificate.

        :param p12_data: bytes — raw PKCS#12 file content
        :param password: str or bytes — certificate password
        """
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
        except ImportError:
            raise ImportError('The cryptography library is required for XML signing.')

        if isinstance(password, str):
            password = password.encode('utf-8')

        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            p12_data, password
        )
        if private_key is None or certificate is None:
            raise ValueError('Could not extract private key and certificate from PKCS#12 file.')

        self.private_key = private_key
        self.certificate = certificate
        self.additional_certs = additional_certs or []

    def sign(self, xml_content):
        """Sign a UBL XML document and return the signed XML bytes.

        Adds an enveloped XMLDSig/XAdES-BES signature as the second
        ext:UBLExtension within ext:UBLExtensions.

        :param xml_content: bytes — unsigned UBL XML
        :return: bytes — signed UBL XML
        """
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, ec, rsa

        tree = etree.fromstring(xml_content)

        # Generate unique IDs
        sig_id = 'xmldsig-' + uuid.uuid4().hex[:8]
        props_id = sig_id + '-signedprops'
        ref_id = sig_id + '-ref0'
        keyinfo_id = sig_id + '-keyinfo'

        is_rsa = isinstance(self.private_key, rsa.RSAPrivateKey)
        sig_alg = SIGNATURE_ALG_RSA if is_rsa else SIGNATURE_ALG_ECDSA

        # 1. Create the Signature structure
        signature_node = etree.SubElement(
            self._get_or_create_signature_extension(tree),
            _tag(NS_DS, 'Signature'),
            attrib={'Id': sig_id},
            nsmap=NSMAP_DS,
        )

        # 2. Build SignedInfo
        signed_info = etree.SubElement(signature_node, _tag(NS_DS, 'SignedInfo'))
        etree.SubElement(signed_info, _tag(NS_DS, 'CanonicalizationMethod'), Algorithm=C14N_ALG)
        etree.SubElement(signed_info, _tag(NS_DS, 'SignatureMethod'), Algorithm=sig_alg)

        # Reference 1: Document (enveloped-signature transform)
        ref1 = etree.SubElement(signed_info, _tag(NS_DS, 'Reference'), attrib={'Id': ref_id, 'URI': ''})
        transforms1 = etree.SubElement(ref1, _tag(NS_DS, 'Transforms'))
        etree.SubElement(transforms1, _tag(NS_DS, 'Transform'), Algorithm=ENVELOPED_SIGNATURE_TRANSFORM)
        etree.SubElement(transforms1, _tag(NS_DS, 'Transform'), Algorithm=C14N_ALG)
        etree.SubElement(ref1, _tag(NS_DS, 'DigestMethod'), Algorithm=DIGEST_ALG)
        digest1_node = etree.SubElement(ref1, _tag(NS_DS, 'DigestValue'))

        # Reference 2: KeyInfo
        ref2 = etree.SubElement(signed_info, _tag(NS_DS, 'Reference'), URI='#' + keyinfo_id)
        transforms2 = etree.SubElement(ref2, _tag(NS_DS, 'Transforms'))
        etree.SubElement(transforms2, _tag(NS_DS, 'Transform'), Algorithm=C14N_ALG)
        etree.SubElement(ref2, _tag(NS_DS, 'DigestMethod'), Algorithm=DIGEST_ALG)
        digest2_node = etree.SubElement(ref2, _tag(NS_DS, 'DigestValue'))

        # Reference 3: SignedProperties
        ref3 = etree.SubElement(
            signed_info, _tag(NS_DS, 'Reference'),
            attrib={
                'Type': 'http://uri.etsi.org/01903#SignedProperties',
                'URI': '#' + props_id,
            },
        )
        transforms3 = etree.SubElement(ref3, _tag(NS_DS, 'Transforms'))
        etree.SubElement(transforms3, _tag(NS_DS, 'Transform'), Algorithm=C14N_ALG)
        etree.SubElement(ref3, _tag(NS_DS, 'DigestMethod'), Algorithm=DIGEST_ALG)
        digest3_node = etree.SubElement(ref3, _tag(NS_DS, 'DigestValue'))

        # 3. Placeholder for SignatureValue
        sig_value_node = etree.SubElement(signature_node, _tag(NS_DS, 'SignatureValue'))

        # 4. KeyInfo with X509 certificate
        key_info = etree.SubElement(signature_node, _tag(NS_DS, 'KeyInfo'), attrib={'Id': keyinfo_id})
        x509_data = etree.SubElement(key_info, _tag(NS_DS, 'X509Data'))
        x509_cert = etree.SubElement(x509_data, _tag(NS_DS, 'X509Certificate'))

        # Encode certificate as base64 DER
        cert_der = self.certificate.public_bytes(serialization.Encoding.DER)
        x509_cert.text = base64.b64encode(cert_der).decode('utf-8')

        # 5. XAdES Object with QualifyingProperties
        object_node = etree.SubElement(signature_node, _tag(NS_DS, 'Object'))
        qualifying_props = etree.SubElement(
            object_node,
            _tag(NS_XADES, 'QualifyingProperties'),
            attrib={'Target': '#' + sig_id},
            nsmap=NSMAP_XADES,
        )
        signed_props = etree.SubElement(
            qualifying_props,
            _tag(NS_XADES, 'SignedProperties'),
            attrib={'Id': props_id},
        )
        signed_sig_props = etree.SubElement(signed_props, _tag(NS_XADES, 'SignedSignatureProperties'))

        # SigningTime
        signing_time = etree.SubElement(signed_sig_props, _tag(NS_XADES, 'SigningTime'))
        signing_time.text = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        # SigningCertificate
        signing_cert = etree.SubElement(signed_sig_props, _tag(NS_XADES, 'SigningCertificate'))
        cert_elem = etree.SubElement(signing_cert, _tag(NS_XADES, 'Cert'))
        cert_digest_elem = etree.SubElement(cert_elem, _tag(NS_XADES, 'CertDigest'))
        etree.SubElement(cert_digest_elem, _tag(NS_DS, 'DigestMethod'), Algorithm=DIGEST_ALG)
        cert_digest_value = etree.SubElement(cert_digest_elem, _tag(NS_DS, 'DigestValue'))
        cert_digest_value.text = base64.b64encode(hashlib.sha256(cert_der).digest()).decode('utf-8')

        issuer_serial = etree.SubElement(cert_elem, _tag(NS_XADES, 'IssuerSerial'))
        issuer_name = etree.SubElement(issuer_serial, _tag(NS_DS, 'X509IssuerName'))
        issuer_name.text = self.certificate.issuer.rfc4514_string()
        serial_number = etree.SubElement(issuer_serial, _tag(NS_DS, 'X509SerialNumber'))
        serial_number.text = str(self.certificate.serial_number)

        # SignaturePolicyIdentifier
        sig_policy = etree.SubElement(signed_sig_props, _tag(NS_XADES, 'SignaturePolicyIdentifier'))
        sig_policy_id_elem = etree.SubElement(sig_policy, _tag(NS_XADES, 'SignaturePolicyId'))
        sp_id = etree.SubElement(sig_policy_id_elem, _tag(NS_XADES, 'SigPolicyId'))
        sp_identifier = etree.SubElement(sp_id, _tag(NS_XADES, 'Identifier'))
        sp_identifier.text = 'https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf'
        sp_hash = etree.SubElement(sig_policy_id_elem, _tag(NS_XADES, 'SigPolicyHash'))
        etree.SubElement(sp_hash, _tag(NS_DS, 'DigestMethod'), Algorithm=DIGEST_ALG)
        sp_hash_value = etree.SubElement(sp_hash, _tag(NS_DS, 'DigestValue'))
        # DIAN policy document hash (fixed value per DIAN spec)
        sp_hash_value.text = 'dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y='

        # SignerRole
        signer_role = etree.SubElement(signed_sig_props, _tag(NS_XADES, 'SignerRole'))
        claimed_roles = etree.SubElement(signer_role, _tag(NS_XADES, 'ClaimedRoles'))
        claimed_role = etree.SubElement(claimed_roles, _tag(NS_XADES, 'ClaimedRole'))
        claimed_role.text = 'supplier'

        # 6. Compute digests
        # Document digest (with enveloped-signature transform)
        digest1_node.text = _calculate_document_digest(tree, signature_node)

        # KeyInfo digest
        digest2_node.text = _calculate_digest(key_info)

        # SignedProperties digest
        digest3_node.text = _calculate_digest(signed_props)

        # 7. Sign the SignedInfo
        signed_info_c14n = etree.tostring(signed_info, method='c14n', exclusive=True, with_comments=False)

        if is_rsa:
            signature_bytes = self.private_key.sign(
                signed_info_c14n,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        else:
            signature_bytes = self.private_key.sign(
                signed_info_c14n,
                ec.ECDSA(hashes.SHA256()),
            )

        sig_value_node.text = base64.b64encode(signature_bytes).decode('utf-8')

        # 8. Return signed XML
        return etree.tostring(tree, xml_declaration=True, encoding='UTF-8')

    def _get_or_create_signature_extension(self, root):
        """Find or create the second ext:UBLExtension for the signature.

        DIAN expects the signature in the second UBLExtension's ExtensionContent.
        """
        ext_ns = NS_EXT
        ubl_extensions = root.find(_tag(ext_ns, 'UBLExtensions'))
        if ubl_extensions is None:
            ubl_extensions = etree.SubElement(root, _tag(ext_ns, 'UBLExtensions'))

        # Find existing UBLExtension elements
        extensions = ubl_extensions.findall(_tag(ext_ns, 'UBLExtension'))

        # Create a second UBLExtension for the signature
        sig_extension = etree.SubElement(ubl_extensions, _tag(ext_ns, 'UBLExtension'))
        sig_content = etree.SubElement(sig_extension, _tag(ext_ns, 'ExtensionContent'))
        return sig_content

    def get_certificate_expiry(self):
        """Return the certificate's expiry date."""
        return self.certificate.not_valid_after_utc
