"""Enveloped XML signatures (XML-DSig), with the XAdES-BES and XAdES-EPES qualifying properties.

References:
- XML-DSig: https://www.w3.org/TR/xmldsig-core1/
- XAdES 1.3.2: https://www.etsi.org/deliver/etsi_ts/101900_101999/101903/01.03.02_60/ts_101903v010302p.pdf
"""
import base64
import hashlib

from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

NS_DS = 'http://www.w3.org/2000/09/xmldsig#'
NS_XADES = 'http://uri.etsi.org/01903/v1.3.2#'
NSMAP = {'ds': NS_DS, 'xades': NS_XADES}

C14N_ALGORITHMS = {
    'inclusive': 'http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
    'exclusive': 'http://www.w3.org/2001/10/xml-exc-c14n#',
}
DIGEST_ALGORITHMS = {
    'sha1': 'http://www.w3.org/2000/09/xmldsig#sha1',
    'sha256': 'http://www.w3.org/2001/04/xmlenc#sha256',
}
SIGNATURE_ALGORITHMS = {
    'sha1': 'http://www.w3.org/2000/09/xmldsig#rsa-sha1',
    'sha256': 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256',
}
ENVELOPED_SIGNATURE_TRANSFORM = 'http://www.w3.org/2000/09/xmldsig#enveloped-signature'
SIGNED_PROPERTIES_TYPE = 'http://uri.etsi.org/01903#SignedProperties'


def _ds(tag):
    return etree.QName(NS_DS, tag).text


def _xades(tag):
    return etree.QName(NS_XADES, tag).text


def canonicalize(node, canonicalization='inclusive'):
    """Return the canonical form of `node` (C14N 1.0, without comments) as bytes.

    The node is serialized in the context of its document: with the inclusive form,
    the namespaces declared on its ancestors are part of the result.
    """
    return etree.tostring(node, method='c14n', exclusive=canonicalization == 'exclusive', with_comments=False)


def compute_digest(data, algorithm='sha256'):
    """Return the base64 digest of `data` (bytes), as a string."""
    return base64.b64encode(hashlib.new(algorithm, data).digest()).decode()


def build_xades_signature(signature_id, x509_certificate, signing_time, canonicalization='inclusive', digest_algorithm='sha256', policy=None):
    """Return an unsigned ds:Signature element with its XAdES qualifying properties.

    The digests and the signature value are empty, see `sign_enveloped`.

    :param signature_id: the Id of the ds:Signature; the Ids of its parts derive from it.
    :param x509_certificate: the signing certificate, a `cryptography` x509.Certificate.
    :param signing_time: the signing time (an aware datetime).
    :param canonicalization: 'inclusive' or 'exclusive'.
    :param digest_algorithm: 'sha1' or 'sha256', for the digests and the signature.
    :param policy: None for XAdES-BES; for XAdES-EPES, a dict with the policy
        'identifier' (its URL), 'digest' (the base64 digest of the policy document),
        'digest_algorithm' (default 'sha256') and an optional 'description'.
    """
    c14n_uri = C14N_ALGORITHMS[canonicalization]
    digest_uri = DIGEST_ALGORITHMS[digest_algorithm]
    key_info_id = f'{signature_id}-keyinfo'
    signed_properties_id = f'{signature_id}-signedprops'
    # With the exclusive form, every reference states it; the inclusive one is the default
    c14n_transforms = [c14n_uri] if canonicalization == 'exclusive' else []

    signature = etree.Element(_ds('Signature'), nsmap={'ds': NS_DS}, Id=signature_id)

    signed_info = etree.SubElement(signature, _ds('SignedInfo'))
    etree.SubElement(signed_info, _ds('CanonicalizationMethod'), Algorithm=c14n_uri)
    etree.SubElement(signed_info, _ds('SignatureMethod'), Algorithm=SIGNATURE_ALGORITHMS[digest_algorithm])

    def add_reference(transform_uris, **attributes):
        reference = etree.SubElement(signed_info, _ds('Reference'), **attributes)
        if transform_uris:
            transforms = etree.SubElement(reference, _ds('Transforms'))
            for transform_uri in transform_uris:
                etree.SubElement(transforms, _ds('Transform'), Algorithm=transform_uri)
        etree.SubElement(reference, _ds('DigestMethod'), Algorithm=digest_uri)
        etree.SubElement(reference, _ds('DigestValue'))

    add_reference([ENVELOPED_SIGNATURE_TRANSFORM, *c14n_transforms], Id=f'{signature_id}-ref0', URI='')
    add_reference(c14n_transforms, URI=f'#{key_info_id}')
    add_reference(c14n_transforms, Type=SIGNED_PROPERTIES_TYPE, URI=f'#{signed_properties_id}')

    etree.SubElement(signature, _ds('SignatureValue'), Id=f'{signature_id}-sigvalue')

    key_info = etree.SubElement(signature, _ds('KeyInfo'), Id=key_info_id)
    x509_data = etree.SubElement(key_info, _ds('X509Data'))
    certificate_der = x509_certificate.public_bytes(Encoding.DER)
    etree.SubElement(x509_data, _ds('X509Certificate')).text = base64.b64encode(certificate_der).decode()

    ds_object = etree.SubElement(signature, _ds('Object'))
    qualifying_properties = etree.SubElement(
        ds_object, _xades('QualifyingProperties'), nsmap={'xades': NS_XADES}, Target=f'#{signature_id}',
    )
    signed_properties = etree.SubElement(qualifying_properties, _xades('SignedProperties'), Id=signed_properties_id)
    signed_signature_properties = etree.SubElement(signed_properties, _xades('SignedSignatureProperties'))
    etree.SubElement(signed_signature_properties, _xades('SigningTime')).text = signing_time.isoformat(timespec='seconds')

    cert = etree.SubElement(etree.SubElement(signed_signature_properties, _xades('SigningCertificate')), _xades('Cert'))
    cert_digest = etree.SubElement(cert, _xades('CertDigest'))
    etree.SubElement(cert_digest, _ds('DigestMethod'), Algorithm=digest_uri)
    etree.SubElement(cert_digest, _ds('DigestValue')).text = compute_digest(certificate_der, digest_algorithm)
    issuer_serial = etree.SubElement(cert, _xades('IssuerSerial'))
    etree.SubElement(issuer_serial, _ds('X509IssuerName')).text = x509_certificate.issuer.rfc4514_string()
    etree.SubElement(issuer_serial, _ds('X509SerialNumber')).text = str(x509_certificate.serial_number)

    if policy:
        policy_id = etree.SubElement(
            etree.SubElement(signed_signature_properties, _xades('SignaturePolicyIdentifier')),
            _xades('SignaturePolicyId'),
        )
        sig_policy_id = etree.SubElement(policy_id, _xades('SigPolicyId'))
        etree.SubElement(sig_policy_id, _xades('Identifier')).text = policy['identifier']
        if policy.get('description'):
            etree.SubElement(sig_policy_id, _xades('Description')).text = policy['description']
        policy_hash = etree.SubElement(policy_id, _xades('SigPolicyHash'))
        etree.SubElement(policy_hash, _ds('DigestMethod'), Algorithm=DIGEST_ALGORITHMS[policy.get('digest_algorithm', 'sha256')])
        etree.SubElement(policy_hash, _ds('DigestValue')).text = policy['digest']

    return signature


def sign_enveloped(node, signature, certificate, canonicalization='inclusive', digest_algorithm='sha256'):
    """Append `signature`, built by `build_xades_signature`, to `node` and fill its digests and value.

    :param node: the element receiving the signature; the signature covers its whole document.
    :param signature: the unsigned ds:Signature element.
    :param certificate: the certificate.certificate record whose private key signs.
    """
    # The enveloped reference is the document without the signature: the document before it is appended
    document_digest = compute_digest(canonicalize(node.getroottree().getroot(), canonicalization), digest_algorithm)
    node.append(signature)

    signed_info = signature.find('ds:SignedInfo', NSMAP)
    for reference in signed_info.iterfind('ds:Reference', NSMAP):
        if uri := reference.get('URI'):
            referenced_node = signature.find(f".//*[@Id='{uri[1:]}']")
            digest = compute_digest(canonicalize(referenced_node, canonicalization), digest_algorithm)
        else:
            digest = document_digest
        reference.find('ds:DigestValue', NSMAP).text = digest

    signature.find('ds:SignatureValue', NSMAP).text = certificate._sign(
        canonicalize(signed_info, canonicalization),
        hashing_algorithm=digest_algorithm,
        formatting='base64',
    ).decode()
