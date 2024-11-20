# coding: utf-8

"""
ASN.1 type classes for cryptographic message syntax (CMS). Structures are also
compatible with PKCS#7. Exports the following items:

 - AuthenticatedData()
 - AuthEnvelopedData()
 - CompressedData()
 - ContentInfo()
 - DigestedData()
 - EncryptedData()
 - EnvelopedData()
 - SignedAndEnvelopedData()
 - SignedData()

Other type classes are defined that help compose the types listed above.

Most CMS structures in the wild are formatted as ContentInfo encapsulating one of the other types.
"""

from __future__ import unicode_literals, division, absolute_import, print_function

try:
    import zlib
except (ImportError):
    zlib = None

from .algos import (
    _ForceNullParameters,
    DigestAlgorithm,
    EncryptionAlgorithm,
    HmacAlgorithm,
    KdfAlgorithm,
    RSAESOAEPParams,
    SignedDigestAlgorithm,
)
from .core import (
    Any,
    BitString,
    Choice,
    Enumerated,
    GeneralizedTime,
    Integer,
    ObjectIdentifier,
    OctetBitString,
    OctetString,
    ParsableOctetString,
    Sequence,
    SequenceOf,
    SetOf,
    UTCTime,
    UTF8String,
)
from .crl import CertificateList
from .keys import PublicKeyInfo
from .ocsp import OCSPResponse
from .x509 import Attributes, Certificate, Extensions, GeneralName, GeneralNames, Name


# These structures are taken from
# ftp://ftp.rsasecurity.com/pub/pkcs/ascii/pkcs-6.asc

class ExtendedCertificateInfo(Sequence):
    _fields = [
        ('version', Integer),
        ('certificate', Certificate),
        ('attributes', Attributes),
    ]


class ExtendedCertificate(Sequence):
    _fields = [
        ('extended_certificate_info', ExtendedCertificateInfo),
        ('signature_algorithm', SignedDigestAlgorithm),
        ('signature', OctetBitString),
    ]


# These structures are taken from https://tools.ietf.org/html/rfc5652,
# https://tools.ietf.org/html/rfc5083, http://tools.ietf.org/html/rfc2315,
# https://tools.ietf.org/html/rfc5940, https://tools.ietf.org/html/rfc3274,
# https://tools.ietf.org/html/rfc3281


class CMSVersion(Integer):
    _map = {
        0: 'v0',
        1: 'v1',
        2: 'v2',
        3: 'v3',
        4: 'v4',
        5: 'v5',
    }


class CMSAttributeType(ObjectIdentifier):
    _map = {
        '1.2.840.113549.1.9.3': 'content_type',
        '1.2.840.113549.1.9.4': 'message_digest',
        '1.2.840.113549.1.9.5': 'signing_time',
        '1.2.840.113549.1.9.6': 'counter_signature',
        # https://tools.ietf.org/html/rfc2633#page-26
        '1.2.840.113549.1.9.16.2.11': 'encrypt_key_pref',
        # https://tools.ietf.org/html/rfc3161#page-20
        '1.2.840.113549.1.9.16.2.14': 'signature_time_stamp_token',
        # https://tools.ietf.org/html/rfc6211#page-5
        '1.2.840.113549.1.9.52': 'cms_algorithm_protection',
        # https://docs.microsoft.com/en-us/previous-versions/hh968145(v%3Dvs.85)
        '1.3.6.1.4.1.311.2.4.1': 'microsoft_nested_signature',
        # Some places refer to this as SPC_RFC3161_OBJID, others szOID_RFC3161_counterSign.
        # https://docs.microsoft.com/en-us/windows/win32/api/wincrypt/ns-wincrypt-crypt_algorithm_identifier
        # refers to szOID_RFC3161_counterSign as "1.2.840.113549.1.9.16.1.4",
        # but that OID is also called szOID_TIMESTAMP_TOKEN. Because of there being
        # no canonical source for this OID, we give it our own name
        '1.3.6.1.4.1.311.3.3.1': 'microsoft_time_stamp_token',
    }


class Time(Choice):
    _alternatives = [
        ('utc_time', UTCTime),
        ('generalized_time', GeneralizedTime),
    ]


class ContentType(ObjectIdentifier):
    _map = {
        '1.2.840.113549.1.7.1': 'data',
        '1.2.840.113549.1.7.2': 'signed_data',
        '1.2.840.113549.1.7.3': 'enveloped_data',
        '1.2.840.113549.1.7.4': 'signed_and_enveloped_data',
        '1.2.840.113549.1.7.5': 'digested_data',
        '1.2.840.113549.1.7.6': 'encrypted_data',
        '1.2.840.113549.1.9.16.1.2': 'authenticated_data',
        '1.2.840.113549.1.9.16.1.9': 'compressed_data',
        '1.2.840.113549.1.9.16.1.23': 'authenticated_enveloped_data',
    }


class CMSAlgorithmProtection(Sequence):
    _fields = [
        ('digest_algorithm', DigestAlgorithm),
        ('signature_algorithm', SignedDigestAlgorithm, {'implicit': 1, 'optional': True}),
        ('mac_algorithm', HmacAlgorithm, {'implicit': 2, 'optional': True}),
    ]


class SetOfContentType(SetOf):
    _child_spec = ContentType


class SetOfOctetString(SetOf):
    _child_spec = OctetString


class SetOfTime(SetOf):
    _child_spec = Time


class SetOfAny(SetOf):
    _child_spec = Any


class SetOfCMSAlgorithmProtection(SetOf):
    _child_spec = CMSAlgorithmProtection


class CMSAttribute(Sequence):
    _fields = [
        ('type', CMSAttributeType),
        ('values', None),
    ]

    _oid_specs = {}

    def _values_spec(self):
        return self._oid_specs.get(self['type'].native, SetOfAny)

    _spec_callbacks = {
        'values': _values_spec
    }


class CMSAttributes(SetOf):
    _child_spec = CMSAttribute


class IssuerSerial(Sequence):
    _fields = [
        ('issuer', GeneralNames),
        ('serial', Integer),
        ('issuer_uid', OctetBitString, {'optional': True}),
    ]


class AttCertVersion(Integer):
    _map = {
        0: 'v1',
        1: 'v2',
    }


class AttCertSubject(Choice):
    _alternatives = [
        ('base_certificate_id', IssuerSerial, {'explicit': 0}),
        ('subject_name', GeneralNames, {'explicit': 1}),
    ]


class AttCertValidityPeriod(Sequence):
    _fields = [
        ('not_before_time', GeneralizedTime),
        ('not_after_time', GeneralizedTime),
    ]


class AttributeCertificateInfoV1(Sequence):
    _fields = [
        ('version', AttCertVersion, {'default': 'v1'}),
        ('subject', AttCertSubject),
        ('issuer', GeneralNames),
        ('signature', SignedDigestAlgorithm),
        ('serial_number', Integer),
        ('att_cert_validity_period', AttCertValidityPeriod),
        ('attributes', Attributes),
        ('issuer_unique_id', OctetBitString, {'optional': True}),
        ('extensions', Extensions, {'optional': True}),
    ]


class AttributeCertificateV1(Sequence):
    _fields = [
        ('ac_info', AttributeCertificateInfoV1),
        ('signature_algorithm', SignedDigestAlgorithm),
        ('signature', OctetBitString),
    ]


class DigestedObjectType(Enumerated):
    _map = {
        0: 'public_key',
        1: 'public_key_cert',
        2: 'other_objy_types',
    }


class ObjectDigestInfo(Sequence):
    _fields = [
        ('digested_object_type', DigestedObjectType),
        ('other_object_type_id', ObjectIdentifier, {'optional': True}),
        ('digest_algorithm', DigestAlgorithm),
        ('object_digest', OctetBitString),
    ]


class Holder(Sequence):
    _fields = [
        ('base_certificate_id', IssuerSerial, {'implicit': 0, 'optional': True}),
        ('entity_name', GeneralNames, {'implicit': 1, 'optional': True}),
        ('object_digest_info', ObjectDigestInfo, {'implicit': 2, 'optional': True}),
    ]


class V2Form(Sequence):
    _fields = [
        ('issuer_name', GeneralNames, {'optional': True}),
        ('base_certificate_id', IssuerSerial, {'explicit': 0, 'optional': True}),
        ('object_digest_info', ObjectDigestInfo, {'explicit': 1, 'optional': True}),
    ]


class AttCertIssuer(Choice):
    _alternatives = [
        ('v1_form', GeneralNames),
        ('v2_form', V2Form, {'explicit': 0}),
    ]


class IetfAttrValue(Choice):
    _alternatives = [
        ('octets', OctetString),
        ('oid', ObjectIdentifier),
        ('string', UTF8String),
    ]


class IetfAttrValues(SequenceOf):
    _child_spec = IetfAttrValue


class IetfAttrSyntax(Sequence):
    _fields = [
        ('policy_authority', GeneralNames, {'implicit': 0, 'optional': True}),
        ('values', IetfAttrValues),
    ]


class SetOfIetfAttrSyntax(SetOf):
    _child_spec = IetfAttrSyntax


class SvceAuthInfo(Sequence):
    _fields = [
        ('service', GeneralName),
        ('ident', GeneralName),
        ('auth_info', OctetString, {'optional': True}),
    ]


class SetOfSvceAuthInfo(SetOf):
    _child_spec = SvceAuthInfo


class RoleSyntax(Sequence):
    _fields = [
        ('role_authority', GeneralNames, {'implicit': 0, 'optional': True}),
        ('role_name', GeneralName, {'implicit': 1}),
    ]


class SetOfRoleSyntax(SetOf):
    _child_spec = RoleSyntax


class ClassList(BitString):
    _map = {
        0: 'unmarked',
        1: 'unclassified',
        2: 'restricted',
        3: 'confidential',
        4: 'secret',
        5: 'top_secret',
    }


class SecurityCategory(Sequence):
    _fields = [
        ('type', ObjectIdentifier, {'implicit': 0}),
        ('value', Any, {'implicit': 1}),
    ]


class SetOfSecurityCategory(SetOf):
    _child_spec = SecurityCategory


class Clearance(Sequence):
    _fields = [
        ('policy_id', ObjectIdentifier, {'implicit': 0}),
        ('class_list', ClassList, {'implicit': 1, 'default': 'unclassified'}),
        ('security_categories', SetOfSecurityCategory, {'implicit': 2, 'optional': True}),
    ]


class SetOfClearance(SetOf):
    _child_spec = Clearance


class BigTime(Sequence):
    _fields = [
        ('major', Integer),
        ('fractional_seconds', Integer),
        ('sign', Integer, {'optional': True}),
    ]


class LeapData(Sequence):
    _fields = [
        ('leap_time', BigTime),
        ('action', Integer),
    ]


class SetOfLeapData(SetOf):
    _child_spec = LeapData


class TimingMetrics(Sequence):
    _fields = [
        ('ntp_time', BigTime),
        ('offset', BigTime),
        ('delay', BigTime),
        ('expiration', BigTime),
        ('leap_event', SetOfLeapData, {'optional': True}),
    ]


class SetOfTimingMetrics(SetOf):
    _child_spec = TimingMetrics


class TimingPolicy(Sequence):
    _fields = [
        ('policy_id', SequenceOf, {'spec': ObjectIdentifier}),
        ('max_offset', BigTime, {'explicit': 0, 'optional': True}),
        ('max_delay', BigTime, {'explicit': 1, 'optional': True}),
    ]


class SetOfTimingPolicy(SetOf):
    _child_spec = TimingPolicy


class AttCertAttributeType(ObjectIdentifier):
    _map = {
        '1.3.6.1.5.5.7.10.1': 'authentication_info',
        '1.3.6.1.5.5.7.10.2': 'access_identity',
        '1.3.6.1.5.5.7.10.3': 'charging_identity',
        '1.3.6.1.5.5.7.10.4': 'group',
        '2.5.4.72': 'role',
        '2.5.4.55': 'clearance',
        '1.3.6.1.4.1.601.10.4.1': 'timing_metrics',
        '1.3.6.1.4.1.601.10.4.2': 'timing_policy',
    }


class AttCertAttribute(Sequence):
    _fields = [
        ('type', AttCertAttributeType),
        ('values', None),
    ]

    _oid_specs = {
        'authentication_info': SetOfSvceAuthInfo,
        'access_identity': SetOfSvceAuthInfo,
        'charging_identity': SetOfIetfAttrSyntax,
        'group': SetOfIetfAttrSyntax,
        'role': SetOfRoleSyntax,
        'clearance': SetOfClearance,
        'timing_metrics': SetOfTimingMetrics,
        'timing_policy': SetOfTimingPolicy,
    }

    def _values_spec(self):
        return self._oid_specs.get(self['type'].native, SetOfAny)

    _spec_callbacks = {
        'values': _values_spec
    }


class AttCertAttributes(SequenceOf):
    _child_spec = AttCertAttribute


class AttributeCertificateInfoV2(Sequence):
    _fields = [
        ('version', AttCertVersion),
        ('holder', Holder),
        ('issuer', AttCertIssuer),
        ('signature', SignedDigestAlgorithm),
        ('serial_number', Integer),
        ('att_cert_validity_period', AttCertValidityPeriod),
        ('attributes', AttCertAttributes),
        ('issuer_unique_id', OctetBitString, {'optional': True}),
        ('extensions', Extensions, {'optional': True}),
    ]


class AttributeCertificateV2(Sequence):
    # Handle the situation where a V2 cert is encoded as V1
    _bad_tag = 1

    _fields = [
        ('ac_info', AttributeCertificateInfoV2),
        ('signature_algorithm', SignedDigestAlgorithm),
        ('signature', OctetBitString),
    ]


class OtherCertificateFormat(Sequence):
    _fields = [
        ('other_cert_format', ObjectIdentifier),
        ('other_cert', Any),
    ]


class CertificateChoices(Choice):
    _alternatives = [
        ('certificate', Certificate),
        ('extended_certificate', ExtendedCertificate, {'implicit': 0}),
        ('v1_attr_cert', AttributeCertificateV1, {'implicit': 1}),
        ('v2_attr_cert', AttributeCertificateV2, {'implicit': 2}),
        ('other', OtherCertificateFormat, {'implicit': 3}),
    ]

    def validate(self, class_, tag, contents):
        """
        Ensures that the class and tag specified exist as an alternative. This
        custom version fixes parsing broken encodings there a V2 attribute
        # certificate is encoded as a V1

        :param class_:
            The integer class_ from the encoded value header

        :param tag:
            The integer tag from the encoded value header

        :param contents:
            A byte string of the contents of the value - used when the object
            is explicitly tagged

        :raises:
            ValueError - when value is not a valid alternative
        """

        super(CertificateChoices, self).validate(class_, tag, contents)
        if self._choice == 2:
            if AttCertVersion.load(Sequence.load(contents)[0].dump()).native == 'v2':
                self._choice = 3


class CertificateSet(SetOf):
    _child_spec = CertificateChoices


class ContentInfo(Sequence):
    _fields = [
        ('content_type', ContentType),
        ('content', Any, {'explicit': 0, 'optional': True}),
    ]

    _oid_pair = ('content_type', 'content')
    _oid_specs = {}


class SetOfContentInfo(SetOf):
    _child_spec = ContentInfo


class EncapsulatedContentInfo(Sequence):
    _fields = [
        ('content_type', ContentType),
        ('content', ParsableOctetString, {'explicit': 0, 'optional': True}),
    ]

    _oid_pair = ('content_type', 'content')
    _oid_specs = {}


class IssuerAndSerialNumber(Sequence):
    _fields = [
        ('issuer', Name),
        ('serial_number', Integer),
    ]


class SignerIdentifier(Choice):
    _alternatives = [
        ('issuer_and_serial_number', IssuerAndSerialNumber),
        ('subject_key_identifier', OctetString, {'implicit': 0}),
    ]


class DigestAlgorithms(SetOf):
    _child_spec = DigestAlgorithm


class CertificateRevocationLists(SetOf):
    _child_spec = CertificateList


class SCVPReqRes(Sequence):
    _fields = [
        ('request', ContentInfo, {'explicit': 0, 'optional': True}),
        ('response', ContentInfo),
    ]


class OtherRevInfoFormatId(ObjectIdentifier):
    _map = {
        '1.3.6.1.5.5.7.16.2': 'ocsp_response',
        '1.3.6.1.5.5.7.16.4': 'scvp',
    }


class OtherRevocationInfoFormat(Sequence):
    _fields = [
        ('other_rev_info_format', OtherRevInfoFormatId),
        ('other_rev_info', Any),
    ]

    _oid_pair = ('other_rev_info_format', 'other_rev_info')
    _oid_specs = {
        'ocsp_response': OCSPResponse,
        'scvp': SCVPReqRes,
    }


class RevocationInfoChoice(Choice):
    _alternatives = [
        ('crl', CertificateList),
        ('other', OtherRevocationInfoFormat, {'implicit': 1}),
    ]


class RevocationInfoChoices(SetOf):
    _child_spec = RevocationInfoChoice


class SignerInfo(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('sid', SignerIdentifier),
        ('digest_algorithm', DigestAlgorithm),
        ('signed_attrs', CMSAttributes, {'implicit': 0, 'optional': True}),
        ('signature_algorithm', SignedDigestAlgorithm),
        ('signature', OctetString),
        ('unsigned_attrs', CMSAttributes, {'implicit': 1, 'optional': True}),
    ]


class SignerInfos(SetOf):
    _child_spec = SignerInfo


class SignedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('digest_algorithms', DigestAlgorithms),
        ('encap_content_info', None),
        ('certificates', CertificateSet, {'implicit': 0, 'optional': True}),
        ('crls', RevocationInfoChoices, {'implicit': 1, 'optional': True}),
        ('signer_infos', SignerInfos),
    ]

    def _encap_content_info_spec(self):
        # If the encap_content_info is version v1, then this could be a PKCS#7
        # structure, or a CMS structure. CMS wraps the encoded value in an
        # Octet String tag.

        # If the version is greater than 1, it is definite CMS
        if self['version'].native != 'v1':
            return EncapsulatedContentInfo

        # Otherwise, the ContentInfo spec from PKCS#7 will be compatible with
        # CMS v1 (which only allows Data, an Octet String) and PKCS#7, which
        # allows Any
        return ContentInfo

    _spec_callbacks = {
        'encap_content_info': _encap_content_info_spec
    }


class OriginatorInfo(Sequence):
    _fields = [
        ('certs', CertificateSet, {'implicit': 0, 'optional': True}),
        ('crls', RevocationInfoChoices, {'implicit': 1, 'optional': True}),
    ]


class RecipientIdentifier(Choice):
    _alternatives = [
        ('issuer_and_serial_number', IssuerAndSerialNumber),
        ('subject_key_identifier', OctetString, {'implicit': 0}),
    ]


class KeyEncryptionAlgorithmId(ObjectIdentifier):
    _map = {
        '1.2.840.113549.1.1.1': 'rsaes_pkcs1v15',
        '1.2.840.113549.1.1.7': 'rsaes_oaep',
        '2.16.840.1.101.3.4.1.5': 'aes128_wrap',
        '2.16.840.1.101.3.4.1.8': 'aes128_wrap_pad',
        '2.16.840.1.101.3.4.1.25': 'aes192_wrap',
        '2.16.840.1.101.3.4.1.28': 'aes192_wrap_pad',
        '2.16.840.1.101.3.4.1.45': 'aes256_wrap',
        '2.16.840.1.101.3.4.1.48': 'aes256_wrap_pad',
    }

    _reverse_map = {
        'rsa': '1.2.840.113549.1.1.1',
        'rsaes_pkcs1v15': '1.2.840.113549.1.1.1',
        'rsaes_oaep': '1.2.840.113549.1.1.7',
        'aes128_wrap': '2.16.840.1.101.3.4.1.5',
        'aes128_wrap_pad': '2.16.840.1.101.3.4.1.8',
        'aes192_wrap': '2.16.840.1.101.3.4.1.25',
        'aes192_wrap_pad': '2.16.840.1.101.3.4.1.28',
        'aes256_wrap': '2.16.840.1.101.3.4.1.45',
        'aes256_wrap_pad': '2.16.840.1.101.3.4.1.48',
    }


class KeyEncryptionAlgorithm(_ForceNullParameters, Sequence):
    _fields = [
        ('algorithm', KeyEncryptionAlgorithmId),
        ('parameters', Any, {'optional': True}),
    ]

    _oid_pair = ('algorithm', 'parameters')
    _oid_specs = {
        'rsaes_oaep': RSAESOAEPParams,
    }


class KeyTransRecipientInfo(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('rid', RecipientIdentifier),
        ('key_encryption_algorithm', KeyEncryptionAlgorithm),
        ('encrypted_key', OctetString),
    ]


class OriginatorIdentifierOrKey(Choice):
    _alternatives = [
        ('issuer_and_serial_number', IssuerAndSerialNumber),
        ('subject_key_identifier', OctetString, {'implicit': 0}),
        ('originator_key', PublicKeyInfo, {'implicit': 1}),
    ]


class OtherKeyAttribute(Sequence):
    _fields = [
        ('key_attr_id', ObjectIdentifier),
        ('key_attr', Any),
    ]


class RecipientKeyIdentifier(Sequence):
    _fields = [
        ('subject_key_identifier', OctetString),
        ('date', GeneralizedTime, {'optional': True}),
        ('other', OtherKeyAttribute, {'optional': True}),
    ]


class KeyAgreementRecipientIdentifier(Choice):
    _alternatives = [
        ('issuer_and_serial_number', IssuerAndSerialNumber),
        ('r_key_id', RecipientKeyIdentifier, {'implicit': 0}),
    ]


class RecipientEncryptedKey(Sequence):
    _fields = [
        ('rid', KeyAgreementRecipientIdentifier),
        ('encrypted_key', OctetString),
    ]


class RecipientEncryptedKeys(SequenceOf):
    _child_spec = RecipientEncryptedKey


class KeyAgreeRecipientInfo(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('originator', OriginatorIdentifierOrKey, {'explicit': 0}),
        ('ukm', OctetString, {'explicit': 1, 'optional': True}),
        ('key_encryption_algorithm', KeyEncryptionAlgorithm),
        ('recipient_encrypted_keys', RecipientEncryptedKeys),
    ]


class KEKIdentifier(Sequence):
    _fields = [
        ('key_identifier', OctetString),
        ('date', GeneralizedTime, {'optional': True}),
        ('other', OtherKeyAttribute, {'optional': True}),
    ]


class KEKRecipientInfo(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('kekid', KEKIdentifier),
        ('key_encryption_algorithm', KeyEncryptionAlgorithm),
        ('encrypted_key', OctetString),
    ]


class PasswordRecipientInfo(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('key_derivation_algorithm', KdfAlgorithm, {'implicit': 0, 'optional': True}),
        ('key_encryption_algorithm', KeyEncryptionAlgorithm),
        ('encrypted_key', OctetString),
    ]


class OtherRecipientInfo(Sequence):
    _fields = [
        ('ori_type', ObjectIdentifier),
        ('ori_value', Any),
    ]


class RecipientInfo(Choice):
    _alternatives = [
        ('ktri', KeyTransRecipientInfo),
        ('kari', KeyAgreeRecipientInfo, {'implicit': 1}),
        ('kekri', KEKRecipientInfo, {'implicit': 2}),
        ('pwri', PasswordRecipientInfo, {'implicit': 3}),
        ('ori', OtherRecipientInfo, {'implicit': 4}),
    ]


class RecipientInfos(SetOf):
    _child_spec = RecipientInfo


class EncryptedContentInfo(Sequence):
    _fields = [
        ('content_type', ContentType),
        ('content_encryption_algorithm', EncryptionAlgorithm),
        ('encrypted_content', OctetString, {'implicit': 0, 'optional': True}),
    ]


class EnvelopedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('originator_info', OriginatorInfo, {'implicit': 0, 'optional': True}),
        ('recipient_infos', RecipientInfos),
        ('encrypted_content_info', EncryptedContentInfo),
        ('unprotected_attrs', CMSAttributes, {'implicit': 1, 'optional': True}),
    ]


class SignedAndEnvelopedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('recipient_infos', RecipientInfos),
        ('digest_algorithms', DigestAlgorithms),
        ('encrypted_content_info', EncryptedContentInfo),
        ('certificates', CertificateSet, {'implicit': 0, 'optional': True}),
        ('crls', CertificateRevocationLists, {'implicit': 1, 'optional': True}),
        ('signer_infos', SignerInfos),
    ]


class DigestedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('digest_algorithm', DigestAlgorithm),
        ('encap_content_info', None),
        ('digest', OctetString),
    ]

    def _encap_content_info_spec(self):
        # If the encap_content_info is version v1, then this could be a PKCS#7
        # structure, or a CMS structure. CMS wraps the encoded value in an
        # Octet String tag.

        # If the version is greater than 1, it is definite CMS
        if self['version'].native != 'v1':
            return EncapsulatedContentInfo

        # Otherwise, the ContentInfo spec from PKCS#7 will be compatible with
        # CMS v1 (which only allows Data, an Octet String) and PKCS#7, which
        # allows Any
        return ContentInfo

    _spec_callbacks = {
        'encap_content_info': _encap_content_info_spec
    }


class EncryptedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('encrypted_content_info', EncryptedContentInfo),
        ('unprotected_attrs', CMSAttributes, {'implicit': 1, 'optional': True}),
    ]


class AuthenticatedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('originator_info', OriginatorInfo, {'implicit': 0, 'optional': True}),
        ('recipient_infos', RecipientInfos),
        ('mac_algorithm', HmacAlgorithm),
        ('digest_algorithm', DigestAlgorithm, {'implicit': 1, 'optional': True}),
        # This does not require the _spec_callbacks approach of SignedData and
        # DigestedData since AuthenticatedData was not part of PKCS#7
        ('encap_content_info', EncapsulatedContentInfo),
        ('auth_attrs', CMSAttributes, {'implicit': 2, 'optional': True}),
        ('mac', OctetString),
        ('unauth_attrs', CMSAttributes, {'implicit': 3, 'optional': True}),
    ]


class AuthEnvelopedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('originator_info', OriginatorInfo, {'implicit': 0, 'optional': True}),
        ('recipient_infos', RecipientInfos),
        ('auth_encrypted_content_info', EncryptedContentInfo),
        ('auth_attrs', CMSAttributes, {'implicit': 1, 'optional': True}),
        ('mac', OctetString),
        ('unauth_attrs', CMSAttributes, {'implicit': 2, 'optional': True}),
    ]


class CompressionAlgorithmId(ObjectIdentifier):
    _map = {
        '1.2.840.113549.1.9.16.3.8': 'zlib',
    }


class CompressionAlgorithm(Sequence):
    _fields = [
        ('algorithm', CompressionAlgorithmId),
        ('parameters', Any, {'optional': True}),
    ]


class CompressedData(Sequence):
    _fields = [
        ('version', CMSVersion),
        ('compression_algorithm', CompressionAlgorithm),
        ('encap_content_info', EncapsulatedContentInfo),
    ]

    _decompressed = None

    @property
    def decompressed(self):
        if self._decompressed is None:
            if zlib is None:
                raise SystemError('The zlib module is not available')
            self._decompressed = zlib.decompress(self['encap_content_info']['content'].native)
        return self._decompressed


class RecipientKeyIdentifier(Sequence):
    _fields = [
        ('subjectKeyIdentifier', OctetString),
        ('date', GeneralizedTime, {'optional': True}),
        ('other', OtherKeyAttribute, {'optional': True}),
    ]


class SMIMEEncryptionKeyPreference(Choice):
    _alternatives = [
        ('issuer_and_serial_number', IssuerAndSerialNumber, {'implicit': 0}),
        ('recipientKeyId', RecipientKeyIdentifier, {'implicit': 1}),
        ('subjectAltKeyIdentifier', PublicKeyInfo, {'implicit': 2}),
    ]


class SMIMEEncryptionKeyPreferences(SetOf):
    _child_spec = SMIMEEncryptionKeyPreference


ContentInfo._oid_specs = {
    'data': OctetString,
    'signed_data': SignedData,
    'enveloped_data': EnvelopedData,
    'signed_and_enveloped_data': SignedAndEnvelopedData,
    'digested_data': DigestedData,
    'encrypted_data': EncryptedData,
    'authenticated_data': AuthenticatedData,
    'compressed_data': CompressedData,
    'authenticated_enveloped_data': AuthEnvelopedData,
}


EncapsulatedContentInfo._oid_specs = {
    'signed_data': SignedData,
    'enveloped_data': EnvelopedData,
    'signed_and_enveloped_data': SignedAndEnvelopedData,
    'digested_data': DigestedData,
    'encrypted_data': EncryptedData,
    'authenticated_data': AuthenticatedData,
    'compressed_data': CompressedData,
    'authenticated_enveloped_data': AuthEnvelopedData,
}


CMSAttribute._oid_specs = {
    'content_type': SetOfContentType,
    'message_digest': SetOfOctetString,
    'signing_time': SetOfTime,
    'counter_signature': SignerInfos,
    'signature_time_stamp_token': SetOfContentInfo,
    'cms_algorithm_protection': SetOfCMSAlgorithmProtection,
    'microsoft_nested_signature': SetOfContentInfo,
    'microsoft_time_stamp_token': SetOfContentInfo,
    'encrypt_key_pref': SMIMEEncryptionKeyPreferences,
}
