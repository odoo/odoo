# coding: utf-8

"""
ASN.1 type classes for PKCS#12 files. Exports the following items:

 - CertBag()
 - CrlBag()
 - Pfx()
 - SafeBag()
 - SecretBag()

Other type classes are defined that help compose the types listed above.
"""

from __future__ import unicode_literals, division, absolute_import, print_function

from .algos import DigestInfo
from .cms import ContentInfo, SignedData
from .core import (
    Any,
    BMPString,
    Integer,
    ObjectIdentifier,
    OctetString,
    ParsableOctetString,
    Sequence,
    SequenceOf,
    SetOf,
)
from .keys import PrivateKeyInfo, EncryptedPrivateKeyInfo
from .x509 import Certificate, KeyPurposeId


# The structures in this file are taken from https://tools.ietf.org/html/rfc7292

class MacData(Sequence):
    _fields = [
        ('mac', DigestInfo),
        ('mac_salt', OctetString),
        ('iterations', Integer, {'default': 1}),
    ]


class Version(Integer):
    _map = {
        3: 'v3'
    }


class AttributeType(ObjectIdentifier):
    _map = {
        # https://tools.ietf.org/html/rfc2985#page-18
        '1.2.840.113549.1.9.20': 'friendly_name',
        '1.2.840.113549.1.9.21': 'local_key_id',
        # https://support.microsoft.com/en-us/kb/287547
        '1.3.6.1.4.1.311.17.1': 'microsoft_local_machine_keyset',
        # https://github.com/frohoff/jdk8u-dev-jdk/blob/master/src/share/classes/sun/security/pkcs12/PKCS12KeyStore.java
        # this is a set of OIDs, representing key usage, the usual value is a SET of one element OID 2.5.29.37.0
        '2.16.840.1.113894.746875.1.1': 'trusted_key_usage',
    }


class SetOfAny(SetOf):
    _child_spec = Any


class SetOfBMPString(SetOf):
    _child_spec = BMPString


class SetOfOctetString(SetOf):
    _child_spec = OctetString


class SetOfKeyPurposeId(SetOf):
    _child_spec = KeyPurposeId


class Attribute(Sequence):
    _fields = [
        ('type', AttributeType),
        ('values', None),
    ]

    _oid_specs = {
        'friendly_name': SetOfBMPString,
        'local_key_id': SetOfOctetString,
        'microsoft_csp_name': SetOfBMPString,
        'trusted_key_usage': SetOfKeyPurposeId,
    }

    def _values_spec(self):
        return self._oid_specs.get(self['type'].native, SetOfAny)

    _spec_callbacks = {
        'values': _values_spec
    }


class Attributes(SetOf):
    _child_spec = Attribute


class Pfx(Sequence):
    _fields = [
        ('version', Version),
        ('auth_safe', ContentInfo),
        ('mac_data', MacData, {'optional': True})
    ]

    _authenticated_safe = None

    @property
    def authenticated_safe(self):
        if self._authenticated_safe is None:
            content = self['auth_safe']['content']
            if isinstance(content, SignedData):
                content = content['content_info']['content']
            self._authenticated_safe = AuthenticatedSafe.load(content.native)
        return self._authenticated_safe


class AuthenticatedSafe(SequenceOf):
    _child_spec = ContentInfo


class BagId(ObjectIdentifier):
    _map = {
        '1.2.840.113549.1.12.10.1.1': 'key_bag',
        '1.2.840.113549.1.12.10.1.2': 'pkcs8_shrouded_key_bag',
        '1.2.840.113549.1.12.10.1.3': 'cert_bag',
        '1.2.840.113549.1.12.10.1.4': 'crl_bag',
        '1.2.840.113549.1.12.10.1.5': 'secret_bag',
        '1.2.840.113549.1.12.10.1.6': 'safe_contents',
    }


class CertId(ObjectIdentifier):
    _map = {
        '1.2.840.113549.1.9.22.1': 'x509',
        '1.2.840.113549.1.9.22.2': 'sdsi',
    }


class CertBag(Sequence):
    _fields = [
        ('cert_id', CertId),
        ('cert_value', ParsableOctetString, {'explicit': 0}),
    ]

    _oid_pair = ('cert_id', 'cert_value')
    _oid_specs = {
        'x509': Certificate,
    }


class CrlBag(Sequence):
    _fields = [
        ('crl_id', ObjectIdentifier),
        ('crl_value', OctetString, {'explicit': 0}),
    ]


class SecretBag(Sequence):
    _fields = [
        ('secret_type_id', ObjectIdentifier),
        ('secret_value', OctetString, {'explicit': 0}),
    ]


class SafeContents(SequenceOf):
    pass


class SafeBag(Sequence):
    _fields = [
        ('bag_id', BagId),
        ('bag_value', Any, {'explicit': 0}),
        ('bag_attributes', Attributes, {'optional': True}),
    ]

    _oid_pair = ('bag_id', 'bag_value')
    _oid_specs = {
        'key_bag': PrivateKeyInfo,
        'pkcs8_shrouded_key_bag': EncryptedPrivateKeyInfo,
        'cert_bag': CertBag,
        'crl_bag': CrlBag,
        'secret_bag': SecretBag,
        'safe_contents': SafeContents
    }


SafeContents._child_spec = SafeBag
