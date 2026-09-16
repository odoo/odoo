# coding: utf-8

"""
ASN.1 type classes for certificate signing requests (CSR). Exports the
following items:

 - CertificationRequest()

Other type classes are defined that help compose the types listed above.
"""

from __future__ import unicode_literals, division, absolute_import, print_function

from .algos import SignedDigestAlgorithm
from .core import (
    Any,
    BitString,
    BMPString,
    Integer,
    ObjectIdentifier,
    OctetBitString,
    Sequence,
    SetOf,
    UTF8String
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
        # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-wcce/a5eaae36-e9f3-4dc5-a687-bfa7115954f1
        '1.3.6.1.4.1.311.13.2.2': 'microsoft_enrollment_csp_provider',
        # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-wcce/7c677cba-030d-48be-ba2b-01e407705f34
        '1.3.6.1.4.1.311.13.2.3': 'microsoft_os_version',
        # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-wcce/64e5ff6d-c6dd-4578-92f7-b3d895f9b9c7
        '1.3.6.1.4.1.311.21.20': 'microsoft_request_client_info',
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


class MicrosoftEnrollmentCSProvider(Sequence):
    _fields = [
        ('keyspec', Integer),
        ('cspname', BMPString),  # cryptographic service provider name
        ('signature', BitString),
    ]


class SetOfMicrosoftEnrollmentCSProvider(SetOf):
    _child_spec = MicrosoftEnrollmentCSProvider


class MicrosoftRequestClientInfo(Sequence):
    _fields = [
        ('clientid', Integer),
        ('machinename', UTF8String),
        ('username', UTF8String),
        ('processname', UTF8String),
    ]


class SetOfMicrosoftRequestClientInfo(SetOf):
    _child_spec = MicrosoftRequestClientInfo


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
        'microsoft_enrollment_csp_provider': SetOfMicrosoftEnrollmentCSProvider,
        'microsoft_os_version': SetOfDirectoryString,
        'microsoft_request_client_info': SetOfMicrosoftRequestClientInfo,
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
