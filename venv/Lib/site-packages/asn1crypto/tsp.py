# coding: utf-8

"""
ASN.1 type classes for the time stamp protocol (TSP). Exports the following
items:

 - TimeStampReq()
 - TimeStampResp()

Also adds TimeStampedData() support to asn1crypto.cms.ContentInfo(),
TimeStampedData() and TSTInfo() support to
asn1crypto.cms.EncapsulatedContentInfo() and some oids and value parsers to
asn1crypto.cms.CMSAttribute().

Other type classes are defined that help compose the types listed above.
"""

from __future__ import unicode_literals, division, absolute_import, print_function

from .algos import DigestAlgorithm
from .cms import (
    CMSAttribute,
    CMSAttributeType,
    ContentInfo,
    ContentType,
    EncapsulatedContentInfo,
)
from .core import (
    Any,
    BitString,
    Boolean,
    Choice,
    GeneralizedTime,
    IA5String,
    Integer,
    ObjectIdentifier,
    OctetString,
    Sequence,
    SequenceOf,
    SetOf,
    UTF8String,
)
from .crl import CertificateList
from .x509 import (
    Attributes,
    CertificatePolicies,
    GeneralName,
    GeneralNames,
)


# The structures in this file are based on https://tools.ietf.org/html/rfc3161,
# https://tools.ietf.org/html/rfc4998, https://tools.ietf.org/html/rfc5544,
# https://tools.ietf.org/html/rfc5035, https://tools.ietf.org/html/rfc2634

class Version(Integer):
    _map = {
        0: 'v0',
        1: 'v1',
        2: 'v2',
        3: 'v3',
        4: 'v4',
        5: 'v5',
    }


class MessageImprint(Sequence):
    _fields = [
        ('hash_algorithm', DigestAlgorithm),
        ('hashed_message', OctetString),
    ]


class Accuracy(Sequence):
    _fields = [
        ('seconds', Integer, {'optional': True}),
        ('millis', Integer, {'implicit': 0, 'optional': True}),
        ('micros', Integer, {'implicit': 1, 'optional': True}),
    ]


class Extension(Sequence):
    _fields = [
        ('extn_id', ObjectIdentifier),
        ('critical', Boolean, {'default': False}),
        ('extn_value', OctetString),
    ]


class Extensions(SequenceOf):
    _child_spec = Extension


class TSTInfo(Sequence):
    _fields = [
        ('version', Version),
        ('policy', ObjectIdentifier),
        ('message_imprint', MessageImprint),
        ('serial_number', Integer),
        ('gen_time', GeneralizedTime),
        ('accuracy', Accuracy, {'optional': True}),
        ('ordering', Boolean, {'default': False}),
        ('nonce', Integer, {'optional': True}),
        ('tsa', GeneralName, {'explicit': 0, 'optional': True}),
        ('extensions', Extensions, {'implicit': 1, 'optional': True}),
    ]


class TimeStampReq(Sequence):
    _fields = [
        ('version', Version),
        ('message_imprint', MessageImprint),
        ('req_policy', ObjectIdentifier, {'optional': True}),
        ('nonce', Integer, {'optional': True}),
        ('cert_req', Boolean, {'default': False}),
        ('extensions', Extensions, {'implicit': 0, 'optional': True}),
    ]


class PKIStatus(Integer):
    _map = {
        0: 'granted',
        1: 'granted_with_mods',
        2: 'rejection',
        3: 'waiting',
        4: 'revocation_warning',
        5: 'revocation_notification',
    }


class PKIFreeText(SequenceOf):
    _child_spec = UTF8String


class PKIFailureInfo(BitString):
    _map = {
        0: 'bad_alg',
        2: 'bad_request',
        5: 'bad_data_format',
        14: 'time_not_available',
        15: 'unaccepted_policy',
        16: 'unaccepted_extensions',
        17: 'add_info_not_available',
        25: 'system_failure',
    }


class PKIStatusInfo(Sequence):
    _fields = [
        ('status', PKIStatus),
        ('status_string', PKIFreeText, {'optional': True}),
        ('fail_info', PKIFailureInfo, {'optional': True}),
    ]


class TimeStampResp(Sequence):
    _fields = [
        ('status', PKIStatusInfo),
        ('time_stamp_token', ContentInfo),
    ]


class MetaData(Sequence):
    _fields = [
        ('hash_protected', Boolean),
        ('file_name', UTF8String, {'optional': True}),
        ('media_type', IA5String, {'optional': True}),
        ('other_meta_data', Attributes, {'optional': True}),
    ]


class TimeStampAndCRL(SequenceOf):
    _fields = [
        ('time_stamp', EncapsulatedContentInfo),
        ('crl', CertificateList, {'optional': True}),
    ]


class TimeStampTokenEvidence(SequenceOf):
    _child_spec = TimeStampAndCRL


class DigestAlgorithms(SequenceOf):
    _child_spec = DigestAlgorithm


class EncryptionInfo(Sequence):
    _fields = [
        ('encryption_info_type', ObjectIdentifier),
        ('encryption_info_value', Any),
    ]


class PartialHashtree(SequenceOf):
    _child_spec = OctetString


class PartialHashtrees(SequenceOf):
    _child_spec = PartialHashtree


class ArchiveTimeStamp(Sequence):
    _fields = [
        ('digest_algorithm', DigestAlgorithm, {'implicit': 0, 'optional': True}),
        ('attributes', Attributes, {'implicit': 1, 'optional': True}),
        ('reduced_hashtree', PartialHashtrees, {'implicit': 2, 'optional': True}),
        ('time_stamp', ContentInfo),
    ]


class ArchiveTimeStampSequence(SequenceOf):
    _child_spec = ArchiveTimeStamp


class EvidenceRecord(Sequence):
    _fields = [
        ('version', Version),
        ('digest_algorithms', DigestAlgorithms),
        ('crypto_infos', Attributes, {'implicit': 0, 'optional': True}),
        ('encryption_info', EncryptionInfo, {'implicit': 1, 'optional': True}),
        ('archive_time_stamp_sequence', ArchiveTimeStampSequence),
    ]


class OtherEvidence(Sequence):
    _fields = [
        ('oe_type', ObjectIdentifier),
        ('oe_value', Any),
    ]


class Evidence(Choice):
    _alternatives = [
        ('tst_evidence', TimeStampTokenEvidence, {'implicit': 0}),
        ('ers_evidence', EvidenceRecord, {'implicit': 1}),
        ('other_evidence', OtherEvidence, {'implicit': 2}),
    ]


class TimeStampedData(Sequence):
    _fields = [
        ('version', Version),
        ('data_uri', IA5String, {'optional': True}),
        ('meta_data', MetaData, {'optional': True}),
        ('content', OctetString, {'optional': True}),
        ('temporal_evidence', Evidence),
    ]


class IssuerSerial(Sequence):
    _fields = [
        ('issuer', GeneralNames),
        ('serial_number', Integer),
    ]


class ESSCertID(Sequence):
    _fields = [
        ('cert_hash', OctetString),
        ('issuer_serial', IssuerSerial, {'optional': True}),
    ]


class ESSCertIDs(SequenceOf):
    _child_spec = ESSCertID


class SigningCertificate(Sequence):
    _fields = [
        ('certs', ESSCertIDs),
        ('policies', CertificatePolicies, {'optional': True}),
    ]


class SetOfSigningCertificates(SetOf):
    _child_spec = SigningCertificate


class ESSCertIDv2(Sequence):
    _fields = [
        ('hash_algorithm', DigestAlgorithm, {'default': {'algorithm': 'sha256'}}),
        ('cert_hash', OctetString),
        ('issuer_serial', IssuerSerial, {'optional': True}),
    ]


class ESSCertIDv2s(SequenceOf):
    _child_spec = ESSCertIDv2


class SigningCertificateV2(Sequence):
    _fields = [
        ('certs', ESSCertIDv2s),
        ('policies', CertificatePolicies, {'optional': True}),
    ]


class SetOfSigningCertificatesV2(SetOf):
    _child_spec = SigningCertificateV2


EncapsulatedContentInfo._oid_specs['tst_info'] = TSTInfo
EncapsulatedContentInfo._oid_specs['timestamped_data'] = TimeStampedData
ContentInfo._oid_specs['timestamped_data'] = TimeStampedData
ContentType._map['1.2.840.113549.1.9.16.1.4'] = 'tst_info'
ContentType._map['1.2.840.113549.1.9.16.1.31'] = 'timestamped_data'
CMSAttributeType._map['1.2.840.113549.1.9.16.2.12'] = 'signing_certificate'
CMSAttribute._oid_specs['signing_certificate'] = SetOfSigningCertificates
CMSAttributeType._map['1.2.840.113549.1.9.16.2.47'] = 'signing_certificate_v2'
CMSAttribute._oid_specs['signing_certificate_v2'] = SetOfSigningCertificatesV2
