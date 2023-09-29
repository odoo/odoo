import base64
import hashlib
import re
from copy import deepcopy

import lxml
from dateutil.parser import parse

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from lxml import etree

from odoo import _
from odoo.tools import file_open

XMLSIG_NSMAP = {"ds": "http://www.w3.org/2000/09/xmldsig#", "xades": "http://uri.etsi.org/01903/v1.3.2#"}


def _c14n_method_constructor(with_comments=False, exclusive=False):
    def _c14n_method(node):
        return etree.tostring(node, method="c14n", with_comments=with_comments, exclusive=exclusive)
    return _c14n_method


def _rsa_method_constructor(digest_method):
    def _rsa_method(data, signature, key):
        return key.verify(base64.b64decode(signature), data, padding.PKCS1v15(), digest_method())
    return _rsa_method


def _hmac_method_constructor(digest_method):
    def _hmac_method(data, signature, key):
        hmac_instance = hmac.HMAC(key, digest_method(), backend=default_backend())
        hmac_instance.update(data)
        return hmac_instance.verify(base64.b64decode(signature))
    return _hmac_method


def _hash_method_constructor(digest_method):
    def _hash_method(data):
        return digest_method(data).digest()
    return _hash_method


C14N_TRANSFORMS_METHODS = {
    "http://www.w3.org/TR/2001/REC-xml-c14n-20010315": _c14n_method_constructor(),
    "http://www.w3.org/TR/2001/REC-xml-c14n-20010315#WithComments": _c14n_method_constructor(with_comments=True),
    "http://www.w3.org/2001/10/xml-exc-c14n#": _c14n_method_constructor(exclusive=True),
    "http://www.w3.org/2001/10/xml-exc-c14n#WithComments": _c14n_method_constructor(with_comments=True, exclusive=True),
}

HASH_METHODS = {
    "http://www.w3.org/2001/04/xmldsig-more#md5": hashes.MD5,
    "http://www.w3.org/2000/09/xmldsig#sha1": hashes.SHA1,
    "http://www.w3.org/2001/04/xmldsig-more#sha224": hashes.SHA224,
    "http://www.w3.org/2001/04/xmlenc#sha256": hashes.SHA256,
    "http://www.w3.org/2001/04/xmldsig-more#sha384": hashes.SHA384,
    "http://www.w3.org/2001/04/xmlenc#sha512": hashes.SHA512,
}

DIGEST_METHODS = {
    "http://www.w3.org/2001/04/xmldsig-more#md5": _hash_method_constructor(hashlib.md5),
    "http://www.w3.org/2000/09/xmldsig#sha1": _hash_method_constructor(hashlib.sha1),
    "http://www.w3.org/2001/04/xmldsig-more#sha224": _hash_method_constructor(hashlib.sha224),
    "http://www.w3.org/2001/04/xmlenc#sha256": _hash_method_constructor(hashlib.sha256),
    "http://www.w3.org/2001/04/xmldsig-more#sha384": _hash_method_constructor(hashlib.sha384),
    "http://www.w3.org/2001/04/xmlenc#sha512": _hash_method_constructor(hashlib.sha384),
}

SIGNATURE_METHODS = {
    "http://www.w3.org/2001/04/xmldsig-more#rsa-md5": _rsa_method_constructor(hashes.MD5),
    "http://www.w3.org/2000/09/xmldsig#rsa-sha1": _rsa_method_constructor(hashes.SHA1),
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha224": _rsa_method_constructor(hashes.SHA224),
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256": _rsa_method_constructor(hashes.SHA256),
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha384": _rsa_method_constructor(hashes.SHA384),
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha512": _rsa_method_constructor(hashes.SHA512),
    "http://www.w3.org/2000/09/xmldsig#hmac-sha1":_hmac_method_constructor(hashes.SHA1),
    "http://www.w3.org/2001/04/xmldsig-more#hmac-sha224": _hmac_method_constructor(hashes.SHA224),
    "http://www.w3.org/2001/04/xmldsig-more#hmac-sha256": _hmac_method_constructor(hashes.SHA256),
    "http://www.w3.org/2001/04/xmldsig-more#hmac-sha384": _hmac_method_constructor(hashes.SHA384),
    "http://www.w3.org/2001/04/xmldsig-more#hmac-sha512": _hmac_method_constructor(hashes.SHA512),
}


def _transform_enveloped_signature(node):
    signature = node.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
    previous = signature.getprevious()
    if previous is not None and signature.tail:
        previous.tail = "".join([previous.tail or "", signature.tail or ""])
    elif signature.tail:
        signature.getparent().text = "".join([signature.getparent().text or "", signature.tail or ""])
    node.remove(signature)


def _apply_transforms(node, transforms_node):
    canonical = False
    if transforms_node is not None:
        transform_nodes = transforms_node.findall("ds:Transform", namespaces=XMLSIG_NSMAP)
        transform_methods = [transform_node.get("Algorithm") for transform_node in transform_nodes]

        if "http://www.w3.org/2000/09/xmldsig#enveloped-signature" in transform_methods:
            _transform_enveloped_signature(node)

        if "http://www.w3.org/2000/09/xmldsig#base64" in transform_methods:
            node = base64.b64decode(node.text)

        for transform_method in transform_methods:
            if transform_method in C14N_TRANSFORMS_METHODS:
                node = C14N_TRANSFORMS_METHODS[transform_method](node)
                canonical = True

    if not canonical and not isinstance(node, (str, bytes)):
        node = _c14n_method_constructor()(node)

    return node


def _find_uri(node, uri=""):
    if uri == "":
        return deepcopy(node.getroottree().getroot())
    if uri.startswith("#"):
        uri = uri.lstrip("#")
        root_node = deepcopy(node.getroottree())
        for attr in ("ID", "Id", "id", "xml:id"):
            xpath = f"//*[@*[local-name() = '{attr}' ]=$uri]"
            result = root_node.xpath(xpath, uri=uri)
            if len(result) == 1:
                break
        if len(result) != 1:
            raise ValueError(_("Cannot reach specified URI"))
        return result[0]
    raise ValueError(_("Cannot reach specified URI"))


def _validate_reference(reference_node):
    node = _find_uri(reference_node, reference_node.get("URI", ""))
    transforms_node = reference_node.find("ds:Transforms", namespaces=XMLSIG_NSMAP)
    node = _apply_transforms(node, transforms_node)
    digest_value = DIGEST_METHODS[reference_node.find("ds:DigestMethod", namespaces=XMLSIG_NSMAP).get("Algorithm")](node)
    return digest_value == base64.b64decode(reference_node.find("ds:DigestValue", namespaces=XMLSIG_NSMAP).text)


def _check_xmldsig_schema(signature_node):
    with file_open('account/tools/xml_verifier/xmldsig_schema.xsd') as schema_file:
        schema = etree.XMLSchema(file=schema_file)
    schema.assertValid(signature_node)


def validate_xmldsig_signature(signature_node, xmldsig_schema=None):
    """ Validates an XML file signature if that XML is following the xmldsig format.

    :param lxml._Element signature_node: The Signature node representing the XML signature to validate.
    :param lxml.XMLSchema xmldsig_schema: Optional. An XMLSchema object used to validate the XML signature
        against the xmldsig schema. If provided, the function will use this schema for validation.
        If not provided, the function will perform a basic schema validation using the default xmldsig schema.

    :raises ValueError: If the signature method specified in the signature is not supported
        or if the specified URI in a reference could not be reached.
    :raises NotImplementedError: If the signature method in the signature is not x509 or RSA.
    :raises InvalidSignature: If one or more reference digests in the signature are not valid
        or if the XML signature is not valid.
    """
    if xmldsig_schema is not None:
        xmldsig_schema.assertValid(signature_node)
    else:
        _check_xmldsig_schema(signature_node)

    signed_info_node = signature_node.find("ds:SignedInfo", namespaces=XMLSIG_NSMAP)
    for reference_node in signed_info_node.findall("ds:Reference", namespaces=XMLSIG_NSMAP):
        if not _validate_reference(reference_node):
            raise InvalidSignature(_("One or more reference digests were not valid."))

    canonicalization_method = signed_info_node.find("ds:CanonicalizationMethod", namespaces=XMLSIG_NSMAP).get("Algorithm")
    signature_method = signed_info_node.find("ds:SignatureMethod", namespaces=XMLSIG_NSMAP).get("Algorithm")
    if signature_method not in SIGNATURE_METHODS:
        raise ValueError(_("Method %s not accepted", signature_method))
    signed_info_node = C14N_TRANSFORMS_METHODS[canonicalization_method](signed_info_node)
    signature_method = SIGNATURE_METHODS[signature_method]

    rsa_key_node = signature_node.find("ds:KeyInfo/ds:KeyValue/ds:RSAKeyValue", namespaces=XMLSIG_NSMAP)
    certificate_node = signature_node.find("ds:KeyInfo/ds:X509Data/ds:X509Certificate", namespaces=XMLSIG_NSMAP)
    if rsa_key_node is not None:
        modulus = int.from_bytes(base64.b64decode(rsa_key_node.find("ds:Modulus", namespaces=XMLSIG_NSMAP).text), "big")
        exponent = int.from_bytes(base64.b64decode(rsa_key_node.find("ds:Exponent", namespaces=XMLSIG_NSMAP).text), "big")
        public_key = rsa.RSAPublicNumbers(exponent, modulus).public_key(default_backend())
    elif certificate_node is not None:
        certificate = x509.load_der_x509_certificate(base64.b64decode(certificate_node.text), default_backend())
        public_key = certificate.public_key()
    else:
        raise NotImplementedError(_("Only x509 and RSA signatures methods are implemented"))

    try:
        signature_method(signed_info_node, signature_node.find("ds:SignatureValue", namespaces=XMLSIG_NSMAP).text, public_key)
    except InvalidSignature:
        raise InvalidSignature(_("Signature is invalid."))


def _verify_signed_properties(signed_properties, signature_node):
    signature_properties = signed_properties.find("xades:SignedSignatureProperties", namespaces=XMLSIG_NSMAP)

    signing_time = signature_properties.find("xades:SigningTime", namespaces=XMLSIG_NSMAP)
    signing_time_parsed = parse(signing_time.text)

    signing_certificate = signature_properties.find("xades:SigningCertificate", namespaces=XMLSIG_NSMAP)
    if not _validate_xades_certificate(signing_certificate, signature_node, signing_time_parsed):
        raise InvalidSignature(_("X509Certificate could not be validated."))


def _validate_xades_certificate(signing_certificate, signature_node, signing_time):
    certs = signing_certificate.findall("xades:Cert", namespaces=XMLSIG_NSMAP)
    x509_data = signature_node.find("ds:KeyInfo/ds:X509Data", namespaces=XMLSIG_NSMAP)
    x509_certificate = x509_data.find("ds:X509Certificate", namespaces=XMLSIG_NSMAP)
    serial = x509_data.find("ds:X509IssuerSerial", namespaces=XMLSIG_NSMAP)

    if x509_data is None:
        return False

    if serial is not None:
        issuer_name = serial.find("ds:X509IssuerName", namespaces=XMLSIG_NSMAP).text
        serial_number = serial.find("ds:X509SerialNumber", namespaces=XMLSIG_NSMAP).text

        matching_cert = None
        for cert in certs:
            if (cert.find("xades:IssuerSerial/ds:X509IssuerName", namespaces=XMLSIG_NSMAP).text == issuer_name
                    and cert.find("xades:IssuerSerial/ds:X509SerialNumber", namespaces=XMLSIG_NSMAP).text == serial_number):
                matching_cert = cert
                break

        if matching_cert is None:
            return False
    else:
        matching_cert = certs[0]

    parsed_x509 = x509.load_der_x509_certificate(base64.b64decode(x509_certificate.text), default_backend())
    _validate_root_ca(parsed_x509)

    # Check validity period.
    if not parsed_x509.not_valid_before <= signing_time <= parsed_x509.not_valid_after:
        return False

    # Check serial number.
    if str(parsed_x509.serial_number) != matching_cert.find("xades:IssuerSerial/ds:X509SerialNumber", namespaces=XMLSIG_NSMAP).text:
        return False

    # Check issuer.
    rdns_pattern = re.compile(r'(?<=\()([A-Z]{1,2}=.*)(?=\))')
    parsed_issuer = ', '.join(sorted(match.group() for match in (rdns_pattern.search(str(element)) for element in parsed_x509.issuer.rdns) if match))
    if parsed_issuer != matching_cert.find("xades:IssuerSerial/ds:X509IssuerName", namespaces=XMLSIG_NSMAP).text:
        return False

    # Check fingerprint
    digest = matching_cert.find("xades:CertDigest", namespaces=XMLSIG_NSMAP)
    digest_algorithm = HASH_METHODS[digest.find("ds:DigestMethod", namespaces=XMLSIG_NSMAP).get("Algorithm")]()
    if base64.b64encode(parsed_x509.fingerprint(digest_algorithm)).decode() != digest.find("ds:DigestValue", namespaces=XMLSIG_NSMAP).text:
        return False

    return True


def validate_xades_signature(signature_node):
    """ Validate an XAdES signature.

    :param lxml._Element signature_node: The Signature node representing the XML signature to validate.

    :raises ValueError: If the XAdES signature validation fails.
    """
    # XAdES validation starts by validating the XMLDSig first.
    validate_xmldsig_signature(signature_node)

    with file_open('account/tools/xml_verifier/xades_schema.xsd') as schema_file:
        schema = etree.XMLSchema(file=schema_file)

    schema.assertValid(signature_node)

    signed_properties_node = signature_node.find(
        "ds:Object/xades:QualifyingProperties["
        "@Target='#{}']/xades:SignedProperties".format(signature_node.get("Id")),
        namespaces=XMLSIG_NSMAP,
    )

    _verify_signed_properties(signed_properties_node, signature_node)

def _validate_root_ca(x509_data):
    with file_open('account/tools/xml_verifier/root_ca.cer', 'rb') as root_ca_file:
        root_ca_data = root_ca_file.read()
        root_ca = x509.load_der_x509_certificate(root_ca_data, default_backend())

    with file_open("account/tools/xml_verifier/test_sig.xsig", "rt") as f:
        xades_sample = lxml.etree.fromstring(f.read().encode())

    certs = xades_sample.xpath('//ds:X509Certificate', namespaces=XMLSIG_NSMAP)
    certs_len = len(certs)

    valid = True

    # Verify chain of trust.
    for idx, cert in enumerate(certs[:certs_len-1]):
        leaf_cert = x509.load_der_x509_certificate(base64.b64decode(cert.text), default_backend())
        intermediate_cert = x509.load_der_x509_certificate(base64.b64decode(certs[idx+1].text), default_backend())

        try:
            intermediate_cert_peb = intermediate_cert.public_key()
            intermediate_cert_peb.verify(leaf_cert.signature, leaf_cert.tbs_certificate_bytes, padding.PKCS1v15(), leaf_cert.signature_hash_algorithm)
        except Exception as e:
            valid = str(e)

    # Last intermediate cert is to be verified by the root CA.
    try:
        intermediate_cert = x509.load_der_x509_certificate(base64.b64decode(certs[certs_len-1].text), default_backend())
        root_cert_peb = root_ca.public_key()
        root_cert_peb.verify(intermediate_cert.signature, intermediate_cert.tbs_certificate_bytes, padding.PKCS1v15(),intermediate_cert.signature_hash_algorithm)
    except Exception as e:
        valid = str(e)

    return valid
