# coding: utf-8

"""
ASN.1 type classes for public and private keys. Exports the following items:

 - DSAPrivateKey()
 - ECPrivateKey()
 - EncryptedPrivateKeyInfo()
 - PrivateKeyInfo()
 - PublicKeyInfo()
 - RSAPrivateKey()
 - RSAPublicKey()

Other type classes are defined that help compose the types listed above.
"""

from __future__ import unicode_literals, division, absolute_import, print_function

import hashlib
import math

from ._errors import unwrap, APIException
from ._types import type_name, byte_cls
from .algos import _ForceNullParameters, DigestAlgorithm, EncryptionAlgorithm, RSAESOAEPParams, RSASSAPSSParams
from .core import (
    Any,
    Asn1Value,
    BitString,
    Choice,
    Integer,
    IntegerOctetString,
    Null,
    ObjectIdentifier,
    OctetBitString,
    OctetString,
    ParsableOctetString,
    ParsableOctetBitString,
    Sequence,
    SequenceOf,
    SetOf,
)
from .util import int_from_bytes, int_to_bytes


class OtherPrimeInfo(Sequence):
    """
    Source: https://tools.ietf.org/html/rfc3447#page-46
    """

    _fields = [
        ('prime', Integer),
        ('exponent', Integer),
        ('coefficient', Integer),
    ]


class OtherPrimeInfos(SequenceOf):
    """
    Source: https://tools.ietf.org/html/rfc3447#page-46
    """

    _child_spec = OtherPrimeInfo


class RSAPrivateKeyVersion(Integer):
    """
    Original Name: Version
    Source: https://tools.ietf.org/html/rfc3447#page-45
    """

    _map = {
        0: 'two-prime',
        1: 'multi',
    }


class RSAPrivateKey(Sequence):
    """
    Source: https://tools.ietf.org/html/rfc3447#page-45
    """

    _fields = [
        ('version', RSAPrivateKeyVersion),
        ('modulus', Integer),
        ('public_exponent', Integer),
        ('private_exponent', Integer),
        ('prime1', Integer),
        ('prime2', Integer),
        ('exponent1', Integer),
        ('exponent2', Integer),
        ('coefficient', Integer),
        ('other_prime_infos', OtherPrimeInfos, {'optional': True})
    ]


class RSAPublicKey(Sequence):
    """
    Source: https://tools.ietf.org/html/rfc3447#page-44
    """

    _fields = [
        ('modulus', Integer),
        ('public_exponent', Integer)
    ]


class DSAPrivateKey(Sequence):
    """
    The ASN.1 structure that OpenSSL uses to store a DSA private key that is
    not part of a PKCS#8 structure. Reversed engineered from english-language
    description on linked OpenSSL documentation page.

    Original Name: None
    Source: https://www.openssl.org/docs/apps/dsa.html
    """

    _fields = [
        ('version', Integer),
        ('p', Integer),
        ('q', Integer),
        ('g', Integer),
        ('public_key', Integer),
        ('private_key', Integer),
    ]


class _ECPoint():
    """
    In both PublicKeyInfo and PrivateKeyInfo, the EC public key is a byte
    string that is encoded as a bit string. This class adds convenience
    methods for converting to and from the byte string to a pair of integers
    that are the X and Y coordinates.
    """

    @classmethod
    def from_coords(cls, x, y):
        """
        Creates an ECPoint object from the X and Y integer coordinates of the
        point

        :param x:
            The X coordinate, as an integer

        :param y:
            The Y coordinate, as an integer

        :return:
            An ECPoint object
        """

        x_bytes = int(math.ceil(math.log(x, 2) / 8.0))
        y_bytes = int(math.ceil(math.log(y, 2) / 8.0))

        num_bytes = max(x_bytes, y_bytes)

        byte_string = b'\x04'
        byte_string += int_to_bytes(x, width=num_bytes)
        byte_string += int_to_bytes(y, width=num_bytes)

        return cls(byte_string)

    def to_coords(self):
        """
        Returns the X and Y coordinates for this EC point, as native Python
        integers

        :return:
            A 2-element tuple containing integers (X, Y)
        """

        data = self.native
        first_byte = data[0:1]

        # Uncompressed
        if first_byte == b'\x04':
            remaining = data[1:]
            field_len = len(remaining) // 2
            x = int_from_bytes(remaining[0:field_len])
            y = int_from_bytes(remaining[field_len:])
            return (x, y)

        if first_byte not in set([b'\x02', b'\x03']):
            raise ValueError(unwrap(
                '''
                Invalid EC public key - first byte is incorrect
                '''
            ))

        raise ValueError(unwrap(
            '''
            Compressed representations of EC public keys are not supported due
            to patent US6252960
            '''
        ))


class ECPoint(OctetString, _ECPoint):

    pass


class ECPointBitString(OctetBitString, _ECPoint):

    pass


class SpecifiedECDomainVersion(Integer):
    """
    Source: http://www.secg.org/sec1-v2.pdf page 104
    """
    _map = {
        1: 'ecdpVer1',
        2: 'ecdpVer2',
        3: 'ecdpVer3',
    }


class FieldType(ObjectIdentifier):
    """
    Original Name: None
    Source: http://www.secg.org/sec1-v2.pdf page 101
    """

    _map = {
        '1.2.840.10045.1.1': 'prime_field',
        '1.2.840.10045.1.2': 'characteristic_two_field',
    }


class CharacteristicTwoBasis(ObjectIdentifier):
    """
    Original Name: None
    Source: http://www.secg.org/sec1-v2.pdf page 102
    """

    _map = {
        '1.2.840.10045.1.2.1.1': 'gn_basis',
        '1.2.840.10045.1.2.1.2': 'tp_basis',
        '1.2.840.10045.1.2.1.3': 'pp_basis',
    }


class Pentanomial(Sequence):
    """
    Source: http://www.secg.org/sec1-v2.pdf page 102
    """

    _fields = [
        ('k1', Integer),
        ('k2', Integer),
        ('k3', Integer),
    ]


class CharacteristicTwo(Sequence):
    """
    Original Name: Characteristic-two
    Source: http://www.secg.org/sec1-v2.pdf page 101
    """

    _fields = [
        ('m', Integer),
        ('basis', CharacteristicTwoBasis),
        ('parameters', Any),
    ]

    _oid_pair = ('basis', 'parameters')
    _oid_specs = {
        'gn_basis': Null,
        'tp_basis': Integer,
        'pp_basis': Pentanomial,
    }


class FieldID(Sequence):
    """
    Source: http://www.secg.org/sec1-v2.pdf page 100
    """

    _fields = [
        ('field_type', FieldType),
        ('parameters', Any),
    ]

    _oid_pair = ('field_type', 'parameters')
    _oid_specs = {
        'prime_field': Integer,
        'characteristic_two_field': CharacteristicTwo,
    }


class Curve(Sequence):
    """
    Source: http://www.secg.org/sec1-v2.pdf page 104
    """

    _fields = [
        ('a', OctetString),
        ('b', OctetString),
        ('seed', OctetBitString, {'optional': True}),
    ]


class SpecifiedECDomain(Sequence):
    """
    Source: http://www.secg.org/sec1-v2.pdf page 103
    """

    _fields = [
        ('version', SpecifiedECDomainVersion),
        ('field_id', FieldID),
        ('curve', Curve),
        ('base', ECPoint),
        ('order', Integer),
        ('cofactor', Integer, {'optional': True}),
        ('hash', DigestAlgorithm, {'optional': True}),
    ]


class NamedCurve(ObjectIdentifier):
    """
    Various named curves

    Original Name: None
    Source: https://tools.ietf.org/html/rfc3279#page-23,
            https://tools.ietf.org/html/rfc5480#page-5
    """

    _map = {
        # https://tools.ietf.org/html/rfc3279#page-23
        '1.2.840.10045.3.0.1': 'c2pnb163v1',
        '1.2.840.10045.3.0.2': 'c2pnb163v2',
        '1.2.840.10045.3.0.3': 'c2pnb163v3',
        '1.2.840.10045.3.0.4': 'c2pnb176w1',
        '1.2.840.10045.3.0.5': 'c2tnb191v1',
        '1.2.840.10045.3.0.6': 'c2tnb191v2',
        '1.2.840.10045.3.0.7': 'c2tnb191v3',
        '1.2.840.10045.3.0.8': 'c2onb191v4',
        '1.2.840.10045.3.0.9': 'c2onb191v5',
        '1.2.840.10045.3.0.10': 'c2pnb208w1',
        '1.2.840.10045.3.0.11': 'c2tnb239v1',
        '1.2.840.10045.3.0.12': 'c2tnb239v2',
        '1.2.840.10045.3.0.13': 'c2tnb239v3',
        '1.2.840.10045.3.0.14': 'c2onb239v4',
        '1.2.840.10045.3.0.15': 'c2onb239v5',
        '1.2.840.10045.3.0.16': 'c2pnb272w1',
        '1.2.840.10045.3.0.17': 'c2pnb304w1',
        '1.2.840.10045.3.0.18': 'c2tnb359v1',
        '1.2.840.10045.3.0.19': 'c2pnb368w1',
        '1.2.840.10045.3.0.20': 'c2tnb431r1',
        '1.2.840.10045.3.1.2': 'prime192v2',
        '1.2.840.10045.3.1.3': 'prime192v3',
        '1.2.840.10045.3.1.4': 'prime239v1',
        '1.2.840.10045.3.1.5': 'prime239v2',
        '1.2.840.10045.3.1.6': 'prime239v3',
        # https://tools.ietf.org/html/rfc5480#page-5
        # http://www.secg.org/SEC2-Ver-1.0.pdf
        '1.2.840.10045.3.1.1': 'secp192r1',
        '1.2.840.10045.3.1.7': 'secp256r1',
        '1.3.132.0.1': 'sect163k1',
        '1.3.132.0.2': 'sect163r1',
        '1.3.132.0.3': 'sect239k1',
        '1.3.132.0.4': 'sect113r1',
        '1.3.132.0.5': 'sect113r2',
        '1.3.132.0.6': 'secp112r1',
        '1.3.132.0.7': 'secp112r2',
        '1.3.132.0.8': 'secp160r1',
        '1.3.132.0.9': 'secp160k1',
        '1.3.132.0.10': 'secp256k1',
        '1.3.132.0.15': 'sect163r2',
        '1.3.132.0.16': 'sect283k1',
        '1.3.132.0.17': 'sect283r1',
        '1.3.132.0.22': 'sect131r1',
        '1.3.132.0.23': 'sect131r2',
        '1.3.132.0.24': 'sect193r1',
        '1.3.132.0.25': 'sect193r2',
        '1.3.132.0.26': 'sect233k1',
        '1.3.132.0.27': 'sect233r1',
        '1.3.132.0.28': 'secp128r1',
        '1.3.132.0.29': 'secp128r2',
        '1.3.132.0.30': 'secp160r2',
        '1.3.132.0.31': 'secp192k1',
        '1.3.132.0.32': 'secp224k1',
        '1.3.132.0.33': 'secp224r1',
        '1.3.132.0.34': 'secp384r1',
        '1.3.132.0.35': 'secp521r1',
        '1.3.132.0.36': 'sect409k1',
        '1.3.132.0.37': 'sect409r1',
        '1.3.132.0.38': 'sect571k1',
        '1.3.132.0.39': 'sect571r1',
        # https://tools.ietf.org/html/rfc5639#section-4.1
        '1.3.36.3.3.2.8.1.1.1': 'brainpoolp160r1',
        '1.3.36.3.3.2.8.1.1.2': 'brainpoolp160t1',
        '1.3.36.3.3.2.8.1.1.3': 'brainpoolp192r1',
        '1.3.36.3.3.2.8.1.1.4': 'brainpoolp192t1',
        '1.3.36.3.3.2.8.1.1.5': 'brainpoolp224r1',
        '1.3.36.3.3.2.8.1.1.6': 'brainpoolp224t1',
        '1.3.36.3.3.2.8.1.1.7': 'brainpoolp256r1',
        '1.3.36.3.3.2.8.1.1.8': 'brainpoolp256t1',
        '1.3.36.3.3.2.8.1.1.9': 'brainpoolp320r1',
        '1.3.36.3.3.2.8.1.1.10': 'brainpoolp320t1',
        '1.3.36.3.3.2.8.1.1.11': 'brainpoolp384r1',
        '1.3.36.3.3.2.8.1.1.12': 'brainpoolp384t1',
        '1.3.36.3.3.2.8.1.1.13': 'brainpoolp512r1',
        '1.3.36.3.3.2.8.1.1.14': 'brainpoolp512t1',
    }

    _key_sizes = {
        # Order values used to compute these sourced from
        # http://cr.openjdk.java.net/~vinnie/7194075/webrev-3/src/share/classes/sun/security/ec/CurveDB.java.html
        '1.2.840.10045.3.0.1': 21,
        '1.2.840.10045.3.0.2': 21,
        '1.2.840.10045.3.0.3': 21,
        '1.2.840.10045.3.0.4': 21,
        '1.2.840.10045.3.0.5': 24,
        '1.2.840.10045.3.0.6': 24,
        '1.2.840.10045.3.0.7': 24,
        '1.2.840.10045.3.0.8': 24,
        '1.2.840.10045.3.0.9': 24,
        '1.2.840.10045.3.0.10': 25,
        '1.2.840.10045.3.0.11': 30,
        '1.2.840.10045.3.0.12': 30,
        '1.2.840.10045.3.0.13': 30,
        '1.2.840.10045.3.0.14': 30,
        '1.2.840.10045.3.0.15': 30,
        '1.2.840.10045.3.0.16': 33,
        '1.2.840.10045.3.0.17': 37,
        '1.2.840.10045.3.0.18': 45,
        '1.2.840.10045.3.0.19': 45,
        '1.2.840.10045.3.0.20': 53,
        '1.2.840.10045.3.1.2': 24,
        '1.2.840.10045.3.1.3': 24,
        '1.2.840.10045.3.1.4': 30,
        '1.2.840.10045.3.1.5': 30,
        '1.2.840.10045.3.1.6': 30,
        # Order values used to compute these sourced from
        # http://www.secg.org/SEC2-Ver-1.0.pdf
        # ceil(n.bit_length() / 8)
        '1.2.840.10045.3.1.1': 24,
        '1.2.840.10045.3.1.7': 32,
        '1.3.132.0.1': 21,
        '1.3.132.0.2': 21,
        '1.3.132.0.3': 30,
        '1.3.132.0.4': 15,
        '1.3.132.0.5': 15,
        '1.3.132.0.6': 14,
        '1.3.132.0.7': 14,
        '1.3.132.0.8': 21,
        '1.3.132.0.9': 21,
        '1.3.132.0.10': 32,
        '1.3.132.0.15': 21,
        '1.3.132.0.16': 36,
        '1.3.132.0.17': 36,
        '1.3.132.0.22': 17,
        '1.3.132.0.23': 17,
        '1.3.132.0.24': 25,
        '1.3.132.0.25': 25,
        '1.3.132.0.26': 29,
        '1.3.132.0.27': 30,
        '1.3.132.0.28': 16,
        '1.3.132.0.29': 16,
        '1.3.132.0.30': 21,
        '1.3.132.0.31': 24,
        '1.3.132.0.32': 29,
        '1.3.132.0.33': 28,
        '1.3.132.0.34': 48,
        '1.3.132.0.35': 66,
        '1.3.132.0.36': 51,
        '1.3.132.0.37': 52,
        '1.3.132.0.38': 72,
        '1.3.132.0.39': 72,
        # Order values used to compute these sourced from
        # https://tools.ietf.org/html/rfc5639#section-3
        # ceil(q.bit_length() / 8)
        '1.3.36.3.3.2.8.1.1.1': 20,
        '1.3.36.3.3.2.8.1.1.2': 20,
        '1.3.36.3.3.2.8.1.1.3': 24,
        '1.3.36.3.3.2.8.1.1.4': 24,
        '1.3.36.3.3.2.8.1.1.5': 28,
        '1.3.36.3.3.2.8.1.1.6': 28,
        '1.3.36.3.3.2.8.1.1.7': 32,
        '1.3.36.3.3.2.8.1.1.8': 32,
        '1.3.36.3.3.2.8.1.1.9': 40,
        '1.3.36.3.3.2.8.1.1.10': 40,
        '1.3.36.3.3.2.8.1.1.11': 48,
        '1.3.36.3.3.2.8.1.1.12': 48,
        '1.3.36.3.3.2.8.1.1.13': 64,
        '1.3.36.3.3.2.8.1.1.14': 64,
    }

    @classmethod
    def register(cls, name, oid, key_size):
        """
        Registers a new named elliptic curve that is not included in the
        default list of named curves

        :param name:
            A unicode string of the curve name

        :param oid:
            A unicode string of the dotted format OID

        :param key_size:
            An integer of the number of bytes the private key should be
            encoded to
        """

        cls._map[oid] = name
        if cls._reverse_map is not None:
            cls._reverse_map[name] = oid
        cls._key_sizes[oid] = key_size


class ECDomainParameters(Choice):
    """
    Source: http://www.secg.org/sec1-v2.pdf page 102
    """

    _alternatives = [
        ('specified', SpecifiedECDomain),
        ('named', NamedCurve),
        ('implicit_ca', Null),
    ]

    @property
    def key_size(self):
        if self.name == 'implicit_ca':
            raise ValueError(unwrap(
                '''
                Unable to calculate key_size from ECDomainParameters
                that are implicitly defined by the CA key
                '''
            ))

        if self.name == 'specified':
            order = self.chosen['order'].native
            return math.ceil(math.log(order, 2.0) / 8.0)

        oid = self.chosen.dotted
        if oid not in NamedCurve._key_sizes:
            raise ValueError(unwrap(
                '''
                The asn1crypto.keys.NamedCurve %s does not have a registered key length,
                please call asn1crypto.keys.NamedCurve.register()
                ''',
                repr(oid)
            ))
        return NamedCurve._key_sizes[oid]


class ECPrivateKeyVersion(Integer):
    """
    Original Name: None
    Source: http://www.secg.org/sec1-v2.pdf page 108
    """

    _map = {
        1: 'ecPrivkeyVer1',
    }


class ECPrivateKey(Sequence):
    """
    Source: http://www.secg.org/sec1-v2.pdf page 108
    """

    _fields = [
        ('version', ECPrivateKeyVersion),
        ('private_key', IntegerOctetString),
        ('parameters', ECDomainParameters, {'explicit': 0, 'optional': True}),
        ('public_key', ECPointBitString, {'explicit': 1, 'optional': True}),
    ]

    # Ensures the key is set to the correct length when encoding
    _key_size = None

    # This is necessary to ensure the private_key IntegerOctetString is encoded properly
    def __setitem__(self, key, value):
        res = super(ECPrivateKey, self).__setitem__(key, value)

        if key == 'private_key':
            if self._key_size is None:
                # Infer the key_size from the existing private key if possible
                pkey_contents = self['private_key'].contents
                if isinstance(pkey_contents, byte_cls) and len(pkey_contents) > 1:
                    self.set_key_size(len(self['private_key'].contents))

            elif self._key_size is not None:
                self._update_key_size()

        elif key == 'parameters' and isinstance(self['parameters'], ECDomainParameters) and \
                self['parameters'].name != 'implicit_ca':
            self.set_key_size(self['parameters'].key_size)

        return res

    def set_key_size(self, key_size):
        """
        Sets the key_size to ensure the private key is encoded to the proper length

        :param key_size:
            An integer byte length to encode the private_key to
        """

        self._key_size = key_size
        self._update_key_size()

    def _update_key_size(self):
        """
        Ensure the private_key explicit encoding width is set
        """

        if self._key_size is not None and isinstance(self['private_key'], IntegerOctetString):
            self['private_key'].set_encoded_width(self._key_size)


class DSAParams(Sequence):
    """
    Parameters for a DSA public or private key

    Original Name: Dss-Parms
    Source: https://tools.ietf.org/html/rfc3279#page-9
    """

    _fields = [
        ('p', Integer),
        ('q', Integer),
        ('g', Integer),
    ]


class Attribute(Sequence):
    """
    Source: https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-X.501-198811-S!!PDF-E&type=items page 8
    """

    _fields = [
        ('type', ObjectIdentifier),
        ('values', SetOf, {'spec': Any}),
    ]


class Attributes(SetOf):
    """
    Source: https://tools.ietf.org/html/rfc5208#page-3
    """

    _child_spec = Attribute


class PrivateKeyAlgorithmId(ObjectIdentifier):
    """
    These OIDs for various public keys are reused when storing private keys
    inside of a PKCS#8 structure

    Original Name: None
    Source: https://tools.ietf.org/html/rfc3279
    """

    _map = {
        # https://tools.ietf.org/html/rfc3279#page-19
        '1.2.840.113549.1.1.1': 'rsa',
        # https://tools.ietf.org/html/rfc4055#page-8
        '1.2.840.113549.1.1.10': 'rsassa_pss',
        # https://tools.ietf.org/html/rfc3279#page-18
        '1.2.840.10040.4.1': 'dsa',
        # https://tools.ietf.org/html/rfc3279#page-13
        '1.2.840.10045.2.1': 'ec',
    }


class PrivateKeyAlgorithm(_ForceNullParameters, Sequence):
    """
    Original Name: PrivateKeyAlgorithmIdentifier
    Source: https://tools.ietf.org/html/rfc5208#page-3
    """

    _fields = [
        ('algorithm', PrivateKeyAlgorithmId),
        ('parameters', Any, {'optional': True}),
    ]

    _oid_pair = ('algorithm', 'parameters')
    _oid_specs = {
        'dsa': DSAParams,
        'ec': ECDomainParameters,
        'rsassa_pss': RSASSAPSSParams,
    }


class PrivateKeyInfo(Sequence):
    """
    Source: https://tools.ietf.org/html/rfc5208#page-3
    """

    _fields = [
        ('version', Integer),
        ('private_key_algorithm', PrivateKeyAlgorithm),
        ('private_key', ParsableOctetString),
        ('attributes', Attributes, {'implicit': 0, 'optional': True}),
    ]

    def _private_key_spec(self):
        algorithm = self['private_key_algorithm']['algorithm'].native
        return {
            'rsa': RSAPrivateKey,
            'rsassa_pss': RSAPrivateKey,
            'dsa': Integer,
            'ec': ECPrivateKey,
        }[algorithm]

    _spec_callbacks = {
        'private_key': _private_key_spec
    }

    _algorithm = None
    _bit_size = None
    _public_key = None
    _fingerprint = None

    @classmethod
    def wrap(cls, private_key, algorithm):
        """
        Wraps a private key in a PrivateKeyInfo structure

        :param private_key:
            A byte string or Asn1Value object of the private key

        :param algorithm:
            A unicode string of "rsa", "dsa" or "ec"

        :return:
            A PrivateKeyInfo object
        """

        if not isinstance(private_key, byte_cls) and not isinstance(private_key, Asn1Value):
            raise TypeError(unwrap(
                '''
                private_key must be a byte string or Asn1Value, not %s
                ''',
                type_name(private_key)
            ))

        if algorithm == 'rsa':
            if not isinstance(private_key, RSAPrivateKey):
                private_key = RSAPrivateKey.load(private_key)
            params = Null()
        elif algorithm == 'dsa':
            if not isinstance(private_key, DSAPrivateKey):
                private_key = DSAPrivateKey.load(private_key)
            params = DSAParams()
            params['p'] = private_key['p']
            params['q'] = private_key['q']
            params['g'] = private_key['g']
            public_key = private_key['public_key']
            private_key = private_key['private_key']
        elif algorithm == 'ec':
            if not isinstance(private_key, ECPrivateKey):
                private_key = ECPrivateKey.load(private_key)
            else:
                private_key = private_key.copy()
            params = private_key['parameters']
            del private_key['parameters']
        else:
            raise ValueError(unwrap(
                '''
                algorithm must be one of "rsa", "dsa", "ec", not %s
                ''',
                repr(algorithm)
            ))

        private_key_algo = PrivateKeyAlgorithm()
        private_key_algo['algorithm'] = PrivateKeyAlgorithmId(algorithm)
        private_key_algo['parameters'] = params

        container = cls()
        container._algorithm = algorithm
        container['version'] = Integer(0)
        container['private_key_algorithm'] = private_key_algo
        container['private_key'] = private_key

        # Here we save the DSA public key if possible since it is not contained
        # within the PKCS#8 structure for a DSA key
        if algorithm == 'dsa':
            container._public_key = public_key

        return container

    # This is necessary to ensure any contained ECPrivateKey is the
    # correct size
    def __setitem__(self, key, value):
        res = super(PrivateKeyInfo, self).__setitem__(key, value)

        algorithm = self['private_key_algorithm']

        # When possible, use the parameter info to make sure the private key encoding
        # retains any necessary leading bytes, instead of them being dropped
        if (key == 'private_key_algorithm' or key == 'private_key') and \
                algorithm['algorithm'].native == 'ec' and \
                isinstance(algorithm['parameters'], ECDomainParameters) and \
                algorithm['parameters'].name != 'implicit_ca' and \
                isinstance(self['private_key'], ParsableOctetString) and \
                isinstance(self['private_key'].parsed, ECPrivateKey):
            self['private_key'].parsed.set_key_size(algorithm['parameters'].key_size)

        return res

    def unwrap(self):
        """
        Unwraps the private key into an RSAPrivateKey, DSAPrivateKey or
        ECPrivateKey object

        :return:
            An RSAPrivateKey, DSAPrivateKey or ECPrivateKey object
        """

        raise APIException(
            'asn1crypto.keys.PrivateKeyInfo().unwrap() has been removed, '
            'please use oscrypto.asymmetric.PrivateKey().unwrap() instead')

    @property
    def curve(self):
        """
        Returns information about the curve used for an EC key

        :raises:
            ValueError - when the key is not an EC key

        :return:
            A two-element tuple, with the first element being a unicode string
            of "implicit_ca", "specified" or "named". If the first element is
            "implicit_ca", the second is None. If "specified", the second is
            an OrderedDict that is the native version of SpecifiedECDomain. If
            "named", the second is a unicode string of the curve name.
        """

        if self.algorithm != 'ec':
            raise ValueError(unwrap(
                '''
                Only EC keys have a curve, this key is %s
                ''',
                self.algorithm.upper()
            ))

        params = self['private_key_algorithm']['parameters']
        chosen = params.chosen

        if params.name == 'implicit_ca':
            value = None
        else:
            value = chosen.native

        return (params.name, value)

    @property
    def hash_algo(self):
        """
        Returns the name of the family of hash algorithms used to generate a
        DSA key

        :raises:
            ValueError - when the key is not a DSA key

        :return:
            A unicode string of "sha1" or "sha2"
        """

        if self.algorithm != 'dsa':
            raise ValueError(unwrap(
                '''
                Only DSA keys are generated using a hash algorithm, this key is
                %s
                ''',
                self.algorithm.upper()
            ))

        byte_len = math.log(self['private_key_algorithm']['parameters']['q'].native, 2) / 8

        return 'sha1' if byte_len <= 20 else 'sha2'

    @property
    def algorithm(self):
        """
        :return:
            A unicode string of "rsa", "dsa" or "ec"
        """

        if self._algorithm is None:
            self._algorithm = self['private_key_algorithm']['algorithm'].native
        return self._algorithm

    @property
    def bit_size(self):
        """
        :return:
            The bit size of the private key, as an integer
        """

        if self._bit_size is None:
            if self.algorithm == 'rsa':
                prime = self['private_key'].parsed['modulus'].native
            elif self.algorithm == 'dsa':
                prime = self['private_key_algorithm']['parameters']['p'].native
            elif self.algorithm == 'ec':
                prime = self['private_key'].parsed['private_key'].native
            self._bit_size = int(math.ceil(math.log(prime, 2)))
            modulus = self._bit_size % 8
            if modulus != 0:
                self._bit_size += 8 - modulus
        return self._bit_size

    @property
    def byte_size(self):
        """
        :return:
            The byte size of the private key, as an integer
        """

        return int(math.ceil(self.bit_size / 8))

    @property
    def public_key(self):
        """
        :return:
            If an RSA key, an RSAPublicKey object. If a DSA key, an Integer
            object. If an EC key, an ECPointBitString object.
        """

        raise APIException(
            'asn1crypto.keys.PrivateKeyInfo().public_key has been removed, '
            'please use oscrypto.asymmetric.PrivateKey().public_key.unwrap() instead')

    @property
    def public_key_info(self):
        """
        :return:
            A PublicKeyInfo object derived from this private key.
        """

        raise APIException(
            'asn1crypto.keys.PrivateKeyInfo().public_key_info has been removed, '
            'please use oscrypto.asymmetric.PrivateKey().public_key.asn1 instead')

    @property
    def fingerprint(self):
        """
        Creates a fingerprint that can be compared with a public key to see if
        the two form a pair.

        This fingerprint is not compatible with fingerprints generated by any
        other software.

        :return:
            A byte string that is a sha256 hash of selected components (based
            on the key type)
        """

        raise APIException(
            'asn1crypto.keys.PrivateKeyInfo().fingerprint has been removed, '
            'please use oscrypto.asymmetric.PrivateKey().fingerprint instead')


class EncryptedPrivateKeyInfo(Sequence):
    """
    Source: https://tools.ietf.org/html/rfc5208#page-4
    """

    _fields = [
        ('encryption_algorithm', EncryptionAlgorithm),
        ('encrypted_data', OctetString),
    ]


# These structures are from https://tools.ietf.org/html/rfc3279

class ValidationParms(Sequence):
    """
    Source: https://tools.ietf.org/html/rfc3279#page-10
    """

    _fields = [
        ('seed', BitString),
        ('pgen_counter', Integer),
    ]


class DomainParameters(Sequence):
    """
    Source: https://tools.ietf.org/html/rfc3279#page-10
    """

    _fields = [
        ('p', Integer),
        ('g', Integer),
        ('q', Integer),
        ('j', Integer, {'optional': True}),
        ('validation_params', ValidationParms, {'optional': True}),
    ]


class PublicKeyAlgorithmId(ObjectIdentifier):
    """
    Original Name: None
    Source: https://tools.ietf.org/html/rfc3279
    """

    _map = {
        # https://tools.ietf.org/html/rfc3279#page-19
        '1.2.840.113549.1.1.1': 'rsa',
        # https://tools.ietf.org/html/rfc3447#page-47
        '1.2.840.113549.1.1.7': 'rsaes_oaep',
        # https://tools.ietf.org/html/rfc4055#page-8
        '1.2.840.113549.1.1.10': 'rsassa_pss',
        # https://tools.ietf.org/html/rfc3279#page-18
        '1.2.840.10040.4.1': 'dsa',
        # https://tools.ietf.org/html/rfc3279#page-13
        '1.2.840.10045.2.1': 'ec',
        # https://tools.ietf.org/html/rfc3279#page-10
        '1.2.840.10046.2.1': 'dh',
    }


class PublicKeyAlgorithm(_ForceNullParameters, Sequence):
    """
    Original Name: AlgorithmIdentifier
    Source: https://tools.ietf.org/html/rfc5280#page-18
    """

    _fields = [
        ('algorithm', PublicKeyAlgorithmId),
        ('parameters', Any, {'optional': True}),
    ]

    _oid_pair = ('algorithm', 'parameters')
    _oid_specs = {
        'dsa': DSAParams,
        'ec': ECDomainParameters,
        'dh': DomainParameters,
        'rsaes_oaep': RSAESOAEPParams,
        'rsassa_pss': RSASSAPSSParams,
    }


class PublicKeyInfo(Sequence):
    """
    Original Name: SubjectPublicKeyInfo
    Source: https://tools.ietf.org/html/rfc5280#page-17
    """

    _fields = [
        ('algorithm', PublicKeyAlgorithm),
        ('public_key', ParsableOctetBitString),
    ]

    def _public_key_spec(self):
        algorithm = self['algorithm']['algorithm'].native
        return {
            'rsa': RSAPublicKey,
            'rsaes_oaep': RSAPublicKey,
            'rsassa_pss': RSAPublicKey,
            'dsa': Integer,
            # We override the field spec with ECPoint so that users can easily
            # decompose the byte string into the constituent X and Y coords
            'ec': (ECPointBitString, None),
            'dh': Integer,
        }[algorithm]

    _spec_callbacks = {
        'public_key': _public_key_spec
    }

    _algorithm = None
    _bit_size = None
    _fingerprint = None
    _sha1 = None
    _sha256 = None

    @classmethod
    def wrap(cls, public_key, algorithm):
        """
        Wraps a public key in a PublicKeyInfo structure

        :param public_key:
            A byte string or Asn1Value object of the public key

        :param algorithm:
            A unicode string of "rsa"

        :return:
            A PublicKeyInfo object
        """

        if not isinstance(public_key, byte_cls) and not isinstance(public_key, Asn1Value):
            raise TypeError(unwrap(
                '''
                public_key must be a byte string or Asn1Value, not %s
                ''',
                type_name(public_key)
            ))

        if algorithm != 'rsa':
            raise ValueError(unwrap(
                '''
                algorithm must "rsa", not %s
                ''',
                repr(algorithm)
            ))

        algo = PublicKeyAlgorithm()
        algo['algorithm'] = PublicKeyAlgorithmId(algorithm)
        algo['parameters'] = Null()

        container = cls()
        container['algorithm'] = algo
        if isinstance(public_key, Asn1Value):
            public_key = public_key.untag().dump()
        container['public_key'] = ParsableOctetBitString(public_key)

        return container

    def unwrap(self):
        """
        Unwraps an RSA public key into an RSAPublicKey object. Does not support
        DSA or EC public keys since they do not have an unwrapped form.

        :return:
            An RSAPublicKey object
        """

        raise APIException(
            'asn1crypto.keys.PublicKeyInfo().unwrap() has been removed, '
            'please use oscrypto.asymmetric.PublicKey().unwrap() instead')

    @property
    def curve(self):
        """
        Returns information about the curve used for an EC key

        :raises:
            ValueError - when the key is not an EC key

        :return:
            A two-element tuple, with the first element being a unicode string
            of "implicit_ca", "specified" or "named". If the first element is
            "implicit_ca", the second is None. If "specified", the second is
            an OrderedDict that is the native version of SpecifiedECDomain. If
            "named", the second is a unicode string of the curve name.
        """

        if self.algorithm != 'ec':
            raise ValueError(unwrap(
                '''
                Only EC keys have a curve, this key is %s
                ''',
                self.algorithm.upper()
            ))

        params = self['algorithm']['parameters']
        chosen = params.chosen

        if params.name == 'implicit_ca':
            value = None
        else:
            value = chosen.native

        return (params.name, value)

    @property
    def hash_algo(self):
        """
        Returns the name of the family of hash algorithms used to generate a
        DSA key

        :raises:
            ValueError - when the key is not a DSA key

        :return:
            A unicode string of "sha1" or "sha2" or None if no parameters are
            present
        """

        if self.algorithm != 'dsa':
            raise ValueError(unwrap(
                '''
                Only DSA keys are generated using a hash algorithm, this key is
                %s
                ''',
                self.algorithm.upper()
            ))

        parameters = self['algorithm']['parameters']
        if parameters.native is None:
            return None

        byte_len = math.log(parameters['q'].native, 2) / 8

        return 'sha1' if byte_len <= 20 else 'sha2'

    @property
    def algorithm(self):
        """
        :return:
            A unicode string of "rsa", "dsa" or "ec"
        """

        if self._algorithm is None:
            self._algorithm = self['algorithm']['algorithm'].native
        return self._algorithm

    @property
    def bit_size(self):
        """
        :return:
            The bit size of the public key, as an integer
        """

        if self._bit_size is None:
            if self.algorithm == 'ec':
                self._bit_size = int(((len(self['public_key'].native) - 1) / 2) * 8)
            else:
                if self.algorithm == 'rsa':
                    prime = self['public_key'].parsed['modulus'].native
                elif self.algorithm == 'dsa':
                    prime = self['algorithm']['parameters']['p'].native
                self._bit_size = int(math.ceil(math.log(prime, 2)))
                modulus = self._bit_size % 8
                if modulus != 0:
                    self._bit_size += 8 - modulus

        return self._bit_size

    @property
    def byte_size(self):
        """
        :return:
            The byte size of the public key, as an integer
        """

        return int(math.ceil(self.bit_size / 8))

    @property
    def sha1(self):
        """
        :return:
            The SHA1 hash of the DER-encoded bytes of this public key info
        """

        if self._sha1 is None:
            self._sha1 = hashlib.sha1(byte_cls(self['public_key'])).digest()
        return self._sha1

    @property
    def sha256(self):
        """
        :return:
            The SHA-256 hash of the DER-encoded bytes of this public key info
        """

        if self._sha256 is None:
            self._sha256 = hashlib.sha256(byte_cls(self['public_key'])).digest()
        return self._sha256

    @property
    def fingerprint(self):
        """
        Creates a fingerprint that can be compared with a private key to see if
        the two form a pair.

        This fingerprint is not compatible with fingerprints generated by any
        other software.

        :return:
            A byte string that is a sha256 hash of selected components (based
            on the key type)
        """

        raise APIException(
            'asn1crypto.keys.PublicKeyInfo().fingerprint has been removed, '
            'please use oscrypto.asymmetric.PublicKey().fingerprint instead')
