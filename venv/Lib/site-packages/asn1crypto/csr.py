# coding: utf-8

"""
ASN.1 type classes for certificate signing requests (CSR). Exports the
following items:

 - CertificatationRequest()

Other type classes are defined that help compose the types listed above.
"""

from __future__ import unicode_literals, division, absolute_import, print_function

from .algos import SignedDigestAlgorithm
from .core import (
    Any,
    Integer,
    ObjectIdentifier,
    OctetBitString,
    Sequence,
    SetOf,
)
from .keys import PublicKeyInfo
from .x509 import DirectoryString, Extensions, Name


# The structures in this file are taken from https://tools.ietf.org/html/rfc2986
# and https://tools.ietf.org/html/rfc2985


class Version(Integer):
    _map = {
        0: 'v1',
    }


class CSRAttributeType(ObjectIdentifier):
    _map = {
        '1.2.840.113549.1.9.7': 'challenge_password',
        '1.2.840.113549.1.9.9': 'extended_certificate_attributes',
        '1.2.840.113549.1.9.14': 'extension_request',
    }


class SetOfDirectoryString(SetOf):
    _child_spec = DirectoryString


class Attribute(Sequence):
    _fields = [
        ('type', ObjectIdentifier),
        ('values', SetOf, {'spec': Any}),
    ]


class SetOfAttributes(SetOf):
    _child_spec = Attribute


class SetOfExtensions(SetOf):
    _child_spec = Extensions


class CRIAttribute(Sequence):
    _fields = [
        ('type', CSRAttributeType),
        ('values', Any),
    ]

    _oid_pair = ('type', 'values')
    _oid_specs = {
        'challenge_password': SetOfDirectoryString,
        'extended_certificate_attributes': SetOfAttributes,
        'extension_request': SetOfExtensions,
    }


class CRIAttributes(SetOf):
    _child_spec = CRIAttribute


class CertificationRequestInfo(Sequence):
    _fields = [
        ('version', Version),
        ('subject', Name),
        ('subject_pk_info', PublicKeyInfo),
        ('attributes', CRIAttributes, {'implicit': 0, 'optional': True}),
    ]


class CertificationRequest(Sequence):
    _fields = [
        ('certification_request_info', CertificationRequestInfo),
        ('signature_algorithm', SignedDigestAlgorithm),
        ('signature', OctetBitString),
    ]
