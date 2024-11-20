# coding: utf-8

"""
ASN.1 type classes for the online certificate status protocol (OCSP). Exports
the following items:

 - OCSPRequest()
 - OCSPResponse()

Other type classes are defined that help compose the types listed above.
"""

from __future__ import unicode_literals, division, absolute_import, print_function

from ._errors import unwrap
from .algos import DigestAlgorithm, SignedDigestAlgorithm
from .core import (
    Boolean,
    Choice,
    Enumerated,
    GeneralizedTime,
    IA5String,
    Integer,
    Null,
    ObjectIdentifier,
    OctetBitString,
    OctetString,
    ParsableOctetString,
    Sequence,
    SequenceOf,
)
from .crl import AuthorityInfoAccessSyntax, CRLReason
from .keys import PublicKeyAlgorithm
from .x509 import Certificate, GeneralName, GeneralNames, Name


# The structures in this file are taken from https://tools.ietf.org/html/rfc6960


class Version(Integer):
    _map = {
        0: 'v1'
    }


class CertId(Sequence):
    _fields = [
        ('hash_algorithm', DigestAlgorithm),
        ('issuer_name_hash', OctetString),
        ('issuer_key_hash', OctetString),
        ('serial_number', Integer),
    ]


class ServiceLocator(Sequence):
    _fields = [
        ('issuer', Name),
        ('locator', AuthorityInfoAccessSyntax),
    ]


class RequestExtensionId(ObjectIdentifier):
    _map = {
        '1.3.6.1.5.5.7.48.1.7': 'service_locator',
    }


class RequestExtension(Sequence):
    _fields = [
        ('extn_id', RequestExtensionId),
        ('critical', Boolean, {'default': False}),
        ('extn_value', ParsableOctetString),
    ]

    _oid_pair = ('extn_id', 'extn_value')
    _oid_specs = {
        'service_locator': ServiceLocator,
    }


class RequestExtensions(SequenceOf):
    _child_spec = RequestExtension


class Request(Sequence):
    _fields = [
        ('req_cert', CertId),
        ('single_request_extensions', RequestExtensions, {'explicit': 0, 'optional': True}),
    ]

    _processed_extensions = False
    _critical_extensions = None
    _service_locator_value = None

    def _set_extensions(self):
        """
        Sets common named extensions to private attributes and creates a list
        of critical extensions
        """

        self._critical_extensions = set()

        for extension in self['single_request_extensions']:
            name = extension['extn_id'].native
            attribute_name = '_%s_value' % name
            if hasattr(self, attribute_name):
                setattr(self, attribute_name, extension['extn_value'].parsed)
            if extension['critical'].native:
                self._critical_extensions.add(name)

        self._processed_extensions = True

    @property
    def critical_extensions(self):
        """
        Returns a set of the names (or OID if not a known extension) of the
        extensions marked as critical

        :return:
            A set of unicode strings
        """

        if not self._processed_extensions:
            self._set_extensions()
        return self._critical_extensions

    @property
    def service_locator_value(self):
        """
        This extension is used when communicating with an OCSP responder that
        acts as a proxy for OCSP requests

        :return:
            None or a ServiceLocator object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._service_locator_value


class Requests(SequenceOf):
    _child_spec = Request


class ResponseType(ObjectIdentifier):
    _map = {
        '1.3.6.1.5.5.7.48.1.1': 'basic_ocsp_response',
    }


class AcceptableResponses(SequenceOf):
    _child_spec = ResponseType


class PreferredSignatureAlgorithm(Sequence):
    _fields = [
        ('sig_identifier', SignedDigestAlgorithm),
        ('cert_identifier', PublicKeyAlgorithm, {'optional': True}),
    ]


class PreferredSignatureAlgorithms(SequenceOf):
    _child_spec = PreferredSignatureAlgorithm


class TBSRequestExtensionId(ObjectIdentifier):
    _map = {
        '1.3.6.1.5.5.7.48.1.2': 'nonce',
        '1.3.6.1.5.5.7.48.1.4': 'acceptable_responses',
        '1.3.6.1.5.5.7.48.1.8': 'preferred_signature_algorithms',
    }


class TBSRequestExtension(Sequence):
    _fields = [
        ('extn_id', TBSRequestExtensionId),
        ('critical', Boolean, {'default': False}),
        ('extn_value', ParsableOctetString),
    ]

    _oid_pair = ('extn_id', 'extn_value')
    _oid_specs = {
        'nonce': OctetString,
        'acceptable_responses': AcceptableResponses,
        'preferred_signature_algorithms': PreferredSignatureAlgorithms,
    }


class TBSRequestExtensions(SequenceOf):
    _child_spec = TBSRequestExtension


class TBSRequest(Sequence):
    _fields = [
        ('version', Version, {'explicit': 0, 'default': 'v1'}),
        ('requestor_name', GeneralName, {'explicit': 1, 'optional': True}),
        ('request_list', Requests),
        ('request_extensions', TBSRequestExtensions, {'explicit': 2, 'optional': True}),
    ]


class Certificates(SequenceOf):
    _child_spec = Certificate


class Signature(Sequence):
    _fields = [
        ('signature_algorithm', SignedDigestAlgorithm),
        ('signature', OctetBitString),
        ('certs', Certificates, {'explicit': 0, 'optional': True}),
    ]


class OCSPRequest(Sequence):
    _fields = [
        ('tbs_request', TBSRequest),
        ('optional_signature', Signature, {'explicit': 0, 'optional': True}),
    ]

    _processed_extensions = False
    _critical_extensions = None
    _nonce_value = None
    _acceptable_responses_value = None
    _preferred_signature_algorithms_value = None

    def _set_extensions(self):
        """
        Sets common named extensions to private attributes and creates a list
        of critical extensions
        """

        self._critical_extensions = set()

        for extension in self['tbs_request']['request_extensions']:
            name = extension['extn_id'].native
            attribute_name = '_%s_value' % name
            if hasattr(self, attribute_name):
                setattr(self, attribute_name, extension['extn_value'].parsed)
            if extension['critical'].native:
                self._critical_extensions.add(name)

        self._processed_extensions = True

    @property
    def critical_extensions(self):
        """
        Returns a set of the names (or OID if not a known extension) of the
        extensions marked as critical

        :return:
            A set of unicode strings
        """

        if not self._processed_extensions:
            self._set_extensions()
        return self._critical_extensions

    @property
    def nonce_value(self):
        """
        This extension is used to prevent replay attacks by including a unique,
        random value with each request/response pair

        :return:
            None or an OctetString object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._nonce_value

    @property
    def acceptable_responses_value(self):
        """
        This extension is used to allow the client and server to communicate
        with alternative response formats other than just basic_ocsp_response,
        although no other formats are defined in the standard.

        :return:
            None or an AcceptableResponses object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._acceptable_responses_value

    @property
    def preferred_signature_algorithms_value(self):
        """
        This extension is used by the client to define what signature algorithms
        are preferred, including both the hash algorithm and the public key
        algorithm, with a level of detail down to even the public key algorithm
        parameters, such as curve name.

        :return:
            None or a PreferredSignatureAlgorithms object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._preferred_signature_algorithms_value


class OCSPResponseStatus(Enumerated):
    _map = {
        0: 'successful',
        1: 'malformed_request',
        2: 'internal_error',
        3: 'try_later',
        5: 'sign_required',
        6: 'unauthorized',
    }


class ResponderId(Choice):
    _alternatives = [
        ('by_name', Name, {'explicit': 1}),
        ('by_key', OctetString, {'explicit': 2}),
    ]


# Custom class to return a meaningful .native attribute from CertStatus()
class StatusGood(Null):
    def set(self, value):
        """
        Sets the value of the object

        :param value:
            None or 'good'
        """

        if value is not None and value != 'good' and not isinstance(value, Null):
            raise ValueError(unwrap(
                '''
                value must be one of None, "good", not %s
                ''',
                repr(value)
            ))

        self.contents = b''

    @property
    def native(self):
        return 'good'


# Custom class to return a meaningful .native attribute from CertStatus()
class StatusUnknown(Null):
    def set(self, value):
        """
        Sets the value of the object

        :param value:
            None or 'unknown'
        """

        if value is not None and value != 'unknown' and not isinstance(value, Null):
            raise ValueError(unwrap(
                '''
                value must be one of None, "unknown", not %s
                ''',
                repr(value)
            ))

        self.contents = b''

    @property
    def native(self):
        return 'unknown'


class RevokedInfo(Sequence):
    _fields = [
        ('revocation_time', GeneralizedTime),
        ('revocation_reason', CRLReason, {'explicit': 0, 'optional': True}),
    ]


class CertStatus(Choice):
    _alternatives = [
        ('good', StatusGood, {'implicit': 0}),
        ('revoked', RevokedInfo, {'implicit': 1}),
        ('unknown', StatusUnknown, {'implicit': 2}),
    ]


class CrlId(Sequence):
    _fields = [
        ('crl_url', IA5String, {'explicit': 0, 'optional': True}),
        ('crl_num', Integer, {'explicit': 1, 'optional': True}),
        ('crl_time', GeneralizedTime, {'explicit': 2, 'optional': True}),
    ]


class SingleResponseExtensionId(ObjectIdentifier):
    _map = {
        '1.3.6.1.5.5.7.48.1.3': 'crl',
        '1.3.6.1.5.5.7.48.1.6': 'archive_cutoff',
        # These are CRLEntryExtension values from
        # https://tools.ietf.org/html/rfc5280
        '2.5.29.21': 'crl_reason',
        '2.5.29.24': 'invalidity_date',
        '2.5.29.29': 'certificate_issuer',
        # https://tools.ietf.org/html/rfc6962.html#page-13
        '1.3.6.1.4.1.11129.2.4.5': 'signed_certificate_timestamp_list',
    }


class SingleResponseExtension(Sequence):
    _fields = [
        ('extn_id', SingleResponseExtensionId),
        ('critical', Boolean, {'default': False}),
        ('extn_value', ParsableOctetString),
    ]

    _oid_pair = ('extn_id', 'extn_value')
    _oid_specs = {
        'crl': CrlId,
        'archive_cutoff': GeneralizedTime,
        'crl_reason': CRLReason,
        'invalidity_date': GeneralizedTime,
        'certificate_issuer': GeneralNames,
        'signed_certificate_timestamp_list': OctetString,
    }


class SingleResponseExtensions(SequenceOf):
    _child_spec = SingleResponseExtension


class SingleResponse(Sequence):
    _fields = [
        ('cert_id', CertId),
        ('cert_status', CertStatus),
        ('this_update', GeneralizedTime),
        ('next_update', GeneralizedTime, {'explicit': 0, 'optional': True}),
        ('single_extensions', SingleResponseExtensions, {'explicit': 1, 'optional': True}),
    ]

    _processed_extensions = False
    _critical_extensions = None
    _crl_value = None
    _archive_cutoff_value = None
    _crl_reason_value = None
    _invalidity_date_value = None
    _certificate_issuer_value = None

    def _set_extensions(self):
        """
        Sets common named extensions to private attributes and creates a list
        of critical extensions
        """

        self._critical_extensions = set()

        for extension in self['single_extensions']:
            name = extension['extn_id'].native
            attribute_name = '_%s_value' % name
            if hasattr(self, attribute_name):
                setattr(self, attribute_name, extension['extn_value'].parsed)
            if extension['critical'].native:
                self._critical_extensions.add(name)

        self._processed_extensions = True

    @property
    def critical_extensions(self):
        """
        Returns a set of the names (or OID if not a known extension) of the
        extensions marked as critical

        :return:
            A set of unicode strings
        """

        if not self._processed_extensions:
            self._set_extensions()
        return self._critical_extensions

    @property
    def crl_value(self):
        """
        This extension is used to locate the CRL that a certificate's revocation
        is contained within.

        :return:
            None or a CrlId object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._crl_value

    @property
    def archive_cutoff_value(self):
        """
        This extension is used to indicate the date at which an archived
        (historical) certificate status entry will no longer be available.

        :return:
            None or a GeneralizedTime object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._archive_cutoff_value

    @property
    def crl_reason_value(self):
        """
        This extension indicates the reason that a certificate was revoked.

        :return:
            None or a CRLReason object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._crl_reason_value

    @property
    def invalidity_date_value(self):
        """
        This extension indicates the suspected date/time the private key was
        compromised or the certificate became invalid. This would usually be
        before the revocation date, which is when the CA processed the
        revocation.

        :return:
            None or a GeneralizedTime object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._invalidity_date_value

    @property
    def certificate_issuer_value(self):
        """
        This extension indicates the issuer of the certificate in question.

        :return:
            None or an x509.GeneralNames object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._certificate_issuer_value


class Responses(SequenceOf):
    _child_spec = SingleResponse


class ResponseDataExtensionId(ObjectIdentifier):
    _map = {
        '1.3.6.1.5.5.7.48.1.2': 'nonce',
        '1.3.6.1.5.5.7.48.1.9': 'extended_revoke',
    }


class ResponseDataExtension(Sequence):
    _fields = [
        ('extn_id', ResponseDataExtensionId),
        ('critical', Boolean, {'default': False}),
        ('extn_value', ParsableOctetString),
    ]

    _oid_pair = ('extn_id', 'extn_value')
    _oid_specs = {
        'nonce': OctetString,
        'extended_revoke': Null,
    }


class ResponseDataExtensions(SequenceOf):
    _child_spec = ResponseDataExtension


class ResponseData(Sequence):
    _fields = [
        ('version', Version, {'explicit': 0, 'default': 'v1'}),
        ('responder_id', ResponderId),
        ('produced_at', GeneralizedTime),
        ('responses', Responses),
        ('response_extensions', ResponseDataExtensions, {'explicit': 1, 'optional': True}),
    ]


class BasicOCSPResponse(Sequence):
    _fields = [
        ('tbs_response_data', ResponseData),
        ('signature_algorithm', SignedDigestAlgorithm),
        ('signature', OctetBitString),
        ('certs', Certificates, {'explicit': 0, 'optional': True}),
    ]


class ResponseBytes(Sequence):
    _fields = [
        ('response_type', ResponseType),
        ('response', ParsableOctetString),
    ]

    _oid_pair = ('response_type', 'response')
    _oid_specs = {
        'basic_ocsp_response': BasicOCSPResponse,
    }


class OCSPResponse(Sequence):
    _fields = [
        ('response_status', OCSPResponseStatus),
        ('response_bytes', ResponseBytes, {'explicit': 0, 'optional': True}),
    ]

    _processed_extensions = False
    _critical_extensions = None
    _nonce_value = None
    _extended_revoke_value = None

    def _set_extensions(self):
        """
        Sets common named extensions to private attributes and creates a list
        of critical extensions
        """

        self._critical_extensions = set()

        for extension in self['response_bytes']['response'].parsed['tbs_response_data']['response_extensions']:
            name = extension['extn_id'].native
            attribute_name = '_%s_value' % name
            if hasattr(self, attribute_name):
                setattr(self, attribute_name, extension['extn_value'].parsed)
            if extension['critical'].native:
                self._critical_extensions.add(name)

        self._processed_extensions = True

    @property
    def critical_extensions(self):
        """
        Returns a set of the names (or OID if not a known extension) of the
        extensions marked as critical

        :return:
            A set of unicode strings
        """

        if not self._processed_extensions:
            self._set_extensions()
        return self._critical_extensions

    @property
    def nonce_value(self):
        """
        This extension is used to prevent replay attacks on the request/response
        exchange

        :return:
            None or an OctetString object
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._nonce_value

    @property
    def extended_revoke_value(self):
        """
        This extension is used to signal that the responder will return a
        "revoked" status for non-issued certificates.

        :return:
            None or a Null object (if present)
        """

        if self._processed_extensions is False:
            self._set_extensions()
        return self._extended_revoke_value

    @property
    def basic_ocsp_response(self):
        """
        A shortcut into the BasicOCSPResponse sequence

        :return:
            None or an asn1crypto.ocsp.BasicOCSPResponse object
        """

        return self['response_bytes']['response'].parsed

    @property
    def response_data(self):
        """
        A shortcut into the parsed, ResponseData sequence

        :return:
            None or an asn1crypto.ocsp.ResponseData object
        """

        return self['response_bytes']['response'].parsed['tbs_response_data']
