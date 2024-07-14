import base64
import binascii
import hashlib
import hmac
from copy import deepcopy

from lxml import etree
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from odoo.tools import consteq

XMLSIG_NSMAP = {"ds": "http://www.w3.org/2000/09/xmldsig#"}


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
        return consteq(hmac.HMAC(key, data, digest_method()), base64.b64decode(signature))
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


def _apply_transform(node, transform_node):
    transform_method = transform_node.get("Algorithm")
    if transform_method in C14N_TRANSFORMS_METHODS:
        return C14N_TRANSFORMS_METHODS[transform_method](node)

    if transform_method == "http://www.w3.org/2000/09/xmldsig#enveloped-signature":
        root_node = etree.fromstring(node).getroottree().getroot()
        signature = root_node.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
        previous = signature.getprevious()
        if previous is not None and signature.tail:  # lxml future requirements, avoids a FutureWarning
            previous.tail = "".join([previous.tail or "", signature.tail or ""])
        elif signature.tail:
            signature.getparent().text = "".join([signature.getparent().text or "", signature.tail or ""])
        root_node.remove(signature)
        return C14N_TRANSFORMS_METHODS["http://www.w3.org/TR/2001/REC-xml-c14n-20010315"](root_node)

    if transform_method == "http://www.w3.org/2000/09/xmldsig#base64":
        try:
            root_node = etree.fromstring(node)
            return base64.b64decode(root_node.text)
        except binascii.Error:
            return base64.b64decode(node)
    raise ValueError("Method not found or not allowed")


def _find_uri(node, uri=""):
    uri_node = deepcopy(node.getroottree())
    if uri == "":
        return etree.tostring(uri_node.getroot(), method="c14n", with_comments=False, exclusive=False)
    if uri.startswith("#"):
        uri = uri.lstrip("#")
        xpath = "//*[@*[local-name() = '{}' ]=$uri]"
        for attr in ("ID", "Id", "id"):
            result = uri_node.xpath(xpath.format(attr), uri=uri)
            if len(result) == 1:
                break
        if len(result) != 1:
            raise ValueError("Cannot reach specified URI")
        return etree.tostring(result[0], method="c14n", with_comments=False, exclusive=False)
    raise ValueError("Cannot reach specified URI")


def _validate_reference(reference_node):
    node = _find_uri(reference_node, reference_node.get("URI", ""))
    transforms_node = reference_node.find("ds:Transforms", namespaces=XMLSIG_NSMAP)
    digest_value = False
    if transforms_node is not None:  # lxml future requirements, avoids a FutureWarning
        for transform_node in transforms_node.findall("ds:Transform", namespaces=XMLSIG_NSMAP):
            node = _apply_transform(node, transform_node)
        digest_value = DIGEST_METHODS[reference_node.find("ds:DigestMethod", namespaces=XMLSIG_NSMAP).get("Algorithm")](node)
    try:
        decoded_file_digest = base64.b64decode(reference_node.find("ds:DigestValue", namespaces=XMLSIG_NSMAP).text, validate=True)
    except binascii.Error:
        raise ValueError("DigestValue is not a valid base64 string")
    return consteq(digest_value, decoded_file_digest)


def validate_xmldsig_signature(signature_node, xmldsig_schema):
    """ Validates a xml file signature if that xml is following the xmldsig format

    :param lxml._Element signature_node: Signature node
    :param  lxml.XMLSchema xmldsig_schema: xmldsig schema
    :return: Whether the signature is valid
    :rtype: bool
    """
    def octet_stream_to_integer_primitive(array):
        return sum((array[i] * (256 ** len(array) - i - 1) for i, val in enumerate(array)))
    xmldsig_schema.assertValid(signature_node)
    signed_info_node = signature_node.find("ds:SignedInfo", namespaces=XMLSIG_NSMAP)
    for reference_node in signed_info_node.findall("ds:Reference", namespaces=XMLSIG_NSMAP):
        if not _validate_reference(reference_node):
            return False

    canonicalization_method = signed_info_node.find("ds:CanonicalizationMethod", namespaces=XMLSIG_NSMAP).get("Algorithm")
    signature_method = signed_info_node.find("ds:SignatureMethod", namespaces=XMLSIG_NSMAP).get("Algorithm")
    if signature_method not in SIGNATURE_METHODS:
        raise ValueError(f"Method {signature_method} not accepted")
    signed_info_node = C14N_TRANSFORMS_METHODS[canonicalization_method](etree.fromstring(etree.tostring(signed_info_node)))
    # The weird fromstring(tostring) deals with lxml using XPATH 1.0 when "empty" default prefixes are only possible with XPATH 2.0
    # E.G. Here the <SIE> tag has no prefix but corresponds to <{http://www.sie.se/sie5}SIE> in the original file
    # which is not valid in XPATH 1.0 and thus lxml fails during the signature validation
    signature_method = SIGNATURE_METHODS[signature_method]

    rsa_key_node = signature_node.find("ds:KeyInfo/ds:KeyValue/ds:RSAKeyValue", namespaces=XMLSIG_NSMAP)
    certificate_node = signature_node.find("ds:KeyInfo/ds:X509Data/ds:X509Certificate", namespaces=XMLSIG_NSMAP)
    if rsa_key_node is not None:  # lxml future requirements, avoids a FutureWarning
        n = octet_stream_to_integer_primitive(base64.b64decode(rsa_key_node.find("ds:Modulus", namespaces=XMLSIG_NSMAP).text))
        e = octet_stream_to_integer_primitive(base64.b64decode(rsa_key_node.find("ds:Exponent", namespaces=XMLSIG_NSMAP).text))
        public_key = rsa.RSAPublicNumbers(e, n).public_key(default_backend())
    elif certificate_node is not None:  # lxml future requirements, avoids a FutureWarning
        certificate = x509.load_der_x509_certificate(base64.b64decode(certificate_node.text), default_backend())
        public_key = certificate.public_key()
    else:
        raise NotImplementedError("Only x509 and RSA signatures methods are implemented")

    try:
        signature_method(signed_info_node, signature_node.find("ds:SignatureValue", namespaces=XMLSIG_NSMAP).text, public_key)
        return True
    except InvalidSignature:
        return False
