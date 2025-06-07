from typing import Union
from dataclasses import dataclass

import cbor2

from .cose import COSECRV, COSEKTY, COSEAlgorithmIdentifier, COSEKey
from .exceptions import InvalidPublicKeyStructure, UnsupportedPublicKeyType
from .parse_cbor import parse_cbor


@dataclass
class DecodedOKPPublicKey:
    kty: COSEKTY
    alg: COSEAlgorithmIdentifier
    crv: COSECRV
    x: bytes


@dataclass
class DecodedEC2PublicKey:
    kty: COSEKTY
    alg: COSEAlgorithmIdentifier
    crv: COSECRV
    x: bytes
    y: bytes


@dataclass
class DecodedRSAPublicKey:
    kty: COSEKTY
    alg: COSEAlgorithmIdentifier
    n: bytes
    e: bytes


def decode_credential_public_key(
    key: bytes,
) -> Union[DecodedOKPPublicKey, DecodedEC2PublicKey, DecodedRSAPublicKey]:
    """
    Decode a CBOR-encoded public key and turn it into a data structure.

    Supports OKP, EC2, and RSA public keys
    """
    # Occassionally we might be given a public key in an "uncompressed" format,
    # typically from older U2F security keys. As per the FIDO spec this is indicated by
    # a leading 0x04 "uncompressed point compression method" format byte. In that case
    # we need to fill in some blanks to turn it into a full EC2 key for signature
    # verification
    #
    # See https://fidoalliance.org/specs/fido-v2.0-id-20180227/fido-registry-v2.0-id-20180227.html#public-key-representation-formats
    if key[0] == 0x04:
        return DecodedEC2PublicKey(
            kty=COSEKTY.EC2,
            alg=COSEAlgorithmIdentifier.ECDSA_SHA_256,
            crv=COSECRV.P256,
            x=key[1:33],
            y=key[33:65],
        )

    decoded_key: dict = parse_cbor(key)

    kty = decoded_key[COSEKey.KTY]
    alg = decoded_key[COSEKey.ALG]

    if not kty:
        raise InvalidPublicKeyStructure("Credential public key missing kty")
    if not alg:
        raise InvalidPublicKeyStructure("Credential public key missing alg")

    if kty == COSEKTY.OKP:
        crv = decoded_key[COSEKey.CRV]
        x = decoded_key[COSEKey.X]

        if not crv:
            raise InvalidPublicKeyStructure("OKP credential public key missing crv")
        if not x:
            raise InvalidPublicKeyStructure("OKP credential public key missing x")

        return DecodedOKPPublicKey(
            kty=kty,
            alg=alg,
            crv=crv,
            x=x,
        )
    elif kty == COSEKTY.EC2:
        crv = decoded_key[COSEKey.CRV]
        x = decoded_key[COSEKey.X]
        y = decoded_key[COSEKey.Y]

        if not crv:
            raise InvalidPublicKeyStructure("EC2 credential public key missing crv")
        if not x:
            raise InvalidPublicKeyStructure("EC2 credential public key missing x")
        if not y:
            raise InvalidPublicKeyStructure("EC2 credential public key missing y")

        return DecodedEC2PublicKey(
            kty=kty,
            alg=alg,
            crv=crv,
            x=x,
            y=y,
        )
    elif kty == COSEKTY.RSA:
        n = decoded_key[COSEKey.N]
        e = decoded_key[COSEKey.E]

        if not n:
            raise InvalidPublicKeyStructure("RSA credential public key missing n")
        if not e:
            raise InvalidPublicKeyStructure("RSA credential public key missing e")

        return DecodedRSAPublicKey(
            kty=kty,
            alg=alg,
            n=n,
            e=e,
        )

    raise UnsupportedPublicKeyType(f'Unsupported credential public key type "{kty}"')
