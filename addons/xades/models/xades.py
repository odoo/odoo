# -*- coding: utf-8 -*-

import base64
import logging
import xmlsig
import pytz
import uuid

from io import BytesIO
from base64 import b64decode, b64encode
from cryptography.hazmat.primitives import hashes
from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker
from OpenSSL import crypto
from xmlsig import constants
from odoo.exceptions import Warning as UserError
from xmlsig.utils import create_node, get_rdns_name


EtsiNS = 'http://uri.etsi.org/01903/v1.3.2#'
ID_ATTR = 'Id'
NS_MAP = constants.NS_MAP
NS_MAP['etsi'] = EtsiNS

ETSI = ElementMaker(namespace=EtsiNS)
DS = ElementMaker(namespace=constants.DSigNs)

MAP_HASHLIB = {
    constants.TransformMd5: hashes.MD5,
    constants.TransformSha1: hashes.SHA1,
    constants.TransformSha224: hashes.SHA224,
    constants.TransformSha256: hashes.SHA256,
    constants.TransformSha384: hashes.SHA384,
    constants.TransformSha512: hashes.SHA512,
    }


class XadesContext(xmlsig.SignatureContext):

    hash_method = constants.TransformSha1

    def __init__(self, certificates=False):
        self.certificates = certificates
        super(XadesContext, self).__init__()

    def sign(self, node):
        signed_properties = \
            node.find("ds:Object/etsi:QualifyingProperties[@Target='#{}']/etsi:SignedProperties".format(node.get('Id'
                      )), namespaces=NS_MAP)
        self.calculate_signed_properties(signed_properties, node, True)
        unsigned_properties = \
            node.find("ds:Object/etsi:QualifyingProperties[@Target='#{}']/etsi:UnsignedProperties".format(node.get('Id'
                      )), namespaces=NS_MAP)
        if unsigned_properties is not None:
            self.calculate_unsigned_properties(unsigned_properties,
                    node, True)
        res = super(XadesContext, self).sign(node)
        return res

    def calculate_signed_properties(
        self,
        signed_properties,
        node,
        sign=False,
        ):
        signature_properties = \
            signed_properties.find('etsi:SignedSignatureProperties',
                                   namespaces=NS_MAP)
        assert signature_properties is not None
        self.calculate_signature_properties(signature_properties, node,
                sign)
        data_object_properties = \
            signed_properties.find('etsi:SignedDataObjectProperties',
                                   namespaces=NS_MAP)
        if data_object_properties is not None:
            self.calculate_data_object_properties(data_object_properties,
                    node, sign)
        return

    def calculate_signature_properties(
        self,
        signature_properties,
        node,
        sign=False,
        ):
        signing_time = signature_properties.find('etsi:SigningTime',
                namespaces=NS_MAP)
        certificate_list = \
            signature_properties.find('etsi:SigningCertificate',
                namespaces=NS_MAP)
        assert signing_time is not None
        if sign and signing_time.text is None:
            now = datetime.now().replace(microsecond=0)
            signing_time.text = now.isoformat()
        if sign:
            self.calculate_certificates(certificate_list,
                    self.certificates or [self.x509])

    def calculate_certificates(self, node, keys_x509):
        for key_x509 in keys_x509:
            self.calculate_certificate(node, key_x509)

    def calculate_certificate(self, node, key_x509):
        fingerprint = \
            key_x509.fingerprint(MAP_HASHLIB[self.hash_method]())
        _ETSI_Cert = \
            ETSI.Cert(ETSI.CertDigest(DS.DigestMethod(Algorithm=self.hash_method),
                      DS.DigestValue(b64encode(fingerprint).decode())),
                      ETSI.IssuerSerial(DS.X509IssuerName(get_rdns_name(key_x509.issuer.rdns)),
                      DS.X509SerialNumber(str(key_x509.serial_number))))

        node.append(_ETSI_Cert)


def create_qualifying_properties(node, name=None, etsi='etsi'):
    obj_node = create_node('Object', node, constants.DSigNs)
    qualifying = etree.SubElement(obj_node, etree.QName(EtsiNS,
                                  'QualifyingProperties'),
                                  nsmap={etsi: EtsiNS})
    qualifying.set('Target', '#' + node.get(ID_ATTR))
    if name is not None:
        qualifying.set(ID_ATTR, name)
    return qualifying


def create_signed_properties(node, name=None, datetime=None):
    properties = create_node('SignedProperties', node, EtsiNS)
    if name is not None:
        properties.set(ID_ATTR, name)
    signature_properties = create_node('SignedSignatureProperties',
            properties, EtsiNS)
    signing_time = create_node('SigningTime', signature_properties,
                               EtsiNS)
    if datetime is not None:
        signing_time.text = datetime.isoformat()
    create_node('SigningCertificate', signature_properties, EtsiNS)
    return properties


def add_data_object_format(
    node,
    reference,
    description=None,
    identifier=None,
    mime_type=None,
    encoding=None,
    ):

    sign_data = create_node('SignedDataObjectProperties', node, EtsiNS)
    data_object_node = create_node('DataObjectFormat', ns=EtsiNS)
    sign_data.insert(len(node.findall('etsi:DataObjectFormat',
                     namespaces=NS_MAP)), data_object_node)
    data_object_node.set('ObjectReference', reference)
    if description is not None:
        create_node('Description', data_object_node, EtsiNS).text = \
            description
    if identifier is not None:
        identifier.to_xml(create_node('ObjectIdentifier',
                          data_object_node, EtsiNS))
    if mime_type is not None:
        create_node('MimeType', data_object_node, EtsiNS).text = \
            mime_type
    if encoding is not None:
        create_node('Encoding', data_object_node, EtsiNS).text = \
            encoding
    return data_object_node




def sign(xmldata, keydata, passphrase, target):
    key = base64.b64decode(keydata)
    
    root = parse_xml(xmldata)
    signature_id = get_unique_id()

    signature = \
        xmlsig.template.create(xmlsig.constants.TransformInclC14N,
                            xmlsig.constants.TransformRsaSha1,
                            'Signature')
    xmlsig.template.add_reference(signature,
                                xmlsig.constants.TransformSha1,
                                uri='#' + signature_id, uri_type="http://uri.etsi.org/01903#SignedProperties")
    xmlsig.template.add_reference(signature,
                                xmlsig.constants.TransformSha1,
                                uri='#KI')
    ref = xmlsig.template.add_reference(signature,
            xmlsig.constants.TransformSha1, uri=target, name='REF')
    xmlsig.template.add_transform(ref,
                                xmlsig.constants.TransformEnveloped)
    ki = xmlsig.template.ensure_key_info(signature, name='KI')
    data = xmlsig.template.add_x509_data(ki)
    xmlsig.template.x509_data_add_certificate(data)
    serial = xmlsig.template.x509_data_add_issuer_serial(data)
    xmlsig.template.x509_issuer_serial_add_issuer_name(serial)
    xmlsig.template.x509_issuer_serial_add_serial_number(serial)
    xmlsig.template.add_key_value(ki)
    qualifying = create_qualifying_properties(signature,
            name=get_unique_id())
    props = create_signed_properties(qualifying, name=signature_id)
    obj_data = add_data_object_format(qualifying, get_unique_id(),
            'contenido comprobante', None, 'text/xml')

    root.append(signature)

    certificate = crypto.load_pkcs12(key, passphrase=passphrase)
    ctx = XadesContext()

    ctx.load_pkcs12(certificate)
    ctx.sign(signature)

    return etree.tostring(root, xml_declaration=True,  encoding="UTF-8")

def parse_xml(xmldata):
    return etree.parse(BytesIO(xmldata)).getroot()

def get_unique_id():
    return "id-{}".format(uuid.uuid4())