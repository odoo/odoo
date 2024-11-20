# coding: utf-8

"""
ASN.1 type classes for PDF signature structures. Adds extra oid mapping and
value parsing to asn1crypto.x509.Extension() and asn1crypto.xms.CMSAttribute().
"""

from __future__ import unicode_literals, division, absolute_import, print_function

from .cms import CMSAttributeType, CMSAttribute
from .core import (
    Boolean,
    Integer,
    Null,
    ObjectIdentifier,
    OctetString,
    Sequence,
    SequenceOf,
    SetOf,
)
from .crl import CertificateList
from .ocsp import OCSPResponse
from .x509 import (
    Extension,
    ExtensionId,
    GeneralName,
    KeyPurposeId,
)


class AdobeArchiveRevInfo(Sequence):
    _fields = [
        ('version', Integer)
    ]


class AdobeTimestamp(Sequence):
    _fields = [
        ('version', Integer),
        ('location', GeneralName),
        ('requires_auth', Boolean, {'optional': True, 'default': False}),
    ]


class OtherRevInfo(Sequence):
    _fields = [
        ('type', ObjectIdentifier),
        ('value', OctetString),
    ]


class SequenceOfCertificateList(SequenceOf):
    _child_spec = CertificateList


class SequenceOfOCSPResponse(SequenceOf):
    _child_spec = OCSPResponse


class SequenceOfOtherRevInfo(SequenceOf):
    _child_spec = OtherRevInfo


class RevocationInfoArchival(Sequence):
    _fields = [
        ('crl', SequenceOfCertificateList, {'explicit': 0, 'optional': True}),
        ('ocsp', SequenceOfOCSPResponse, {'explicit': 1, 'optional': True}),
        ('other_rev_info', SequenceOfOtherRevInfo, {'explicit': 2, 'optional': True}),
    ]


class SetOfRevocationInfoArchival(SetOf):
    _child_spec = RevocationInfoArchival


ExtensionId._map['1.2.840.113583.1.1.9.2'] = 'adobe_archive_rev_info'
ExtensionId._map['1.2.840.113583.1.1.9.1'] = 'adobe_timestamp'
ExtensionId._map['1.2.840.113583.1.1.10'] = 'adobe_ppklite_credential'
Extension._oid_specs['adobe_archive_rev_info'] = AdobeArchiveRevInfo
Extension._oid_specs['adobe_timestamp'] = AdobeTimestamp
Extension._oid_specs['adobe_ppklite_credential'] = Null
KeyPurposeId._map['1.2.840.113583.1.1.5'] = 'pdf_signing'
CMSAttributeType._map['1.2.840.113583.1.1.8'] = 'adobe_revocation_info_archival'
CMSAttribute._oid_specs['adobe_revocation_info_archival'] = SetOfRevocationInfoArchival
