from enum import Enum


class COSEAlgorithmIdentifier(int, Enum):
    """Various registered values indicating cryptographic algorithms that may be used in credential responses

    Members:
        `ECDSA_SHA_256`
        `EDDSA`
        `ECDSA_SHA_512`
        `RSASSA_PSS_SHA_256`
        `RSASSA_PSS_SHA_384`
        `RSASSA_PSS_SHA_512`
        `RSASSA_PKCS1_v1_5_SHA_256`
        `RSASSA_PKCS1_v1_5_SHA_384`
        `RSASSA_PKCS1_v1_5_SHA_512`
        `RSASSA_PKCS1_v1_5_SHA_1`

    https://www.w3.org/TR/webauthn-2/#sctn-alg-identifier
    https://www.iana.org/assignments/cose/cose.xhtml#algorithms
    """

    ECDSA_SHA_256 = -7
    EDDSA = -8
    ECDSA_SHA_512 = -36
    RSASSA_PSS_SHA_256 = -37
    RSASSA_PSS_SHA_384 = -38
    RSASSA_PSS_SHA_512 = -39
    RSASSA_PKCS1_v1_5_SHA_256 = -257
    RSASSA_PKCS1_v1_5_SHA_384 = -258
    RSASSA_PKCS1_v1_5_SHA_512 = -259
    RSASSA_PKCS1_v1_5_SHA_1 = -65535  # Deprecated; here for legacy support


class COSEKTY(int, Enum):
    """
    Possible values for COSEKey.KTY representing a public key's key type

    https://tools.ietf.org/html/rfc8152#section-13
    https://www.iana.org/assignments/cose/cose.xhtml#table-key-type
    """

    OKP = 1
    EC2 = 2
    RSA = 3


class COSECRV(int, Enum):
    """Possible values for COSEKey.CRV representing an EC2 public key's curve

    https://tools.ietf.org/html/rfc8152#section-13.1
    https://www.iana.org/assignments/cose/cose.xhtml#table-elliptic-curves
    """

    P256 = 1  # EC2, NIST P-256 also known as secp256r1
    P384 = 2  # EC2, NIST P-384 also known as secp384r1
    P521 = 3  # EC2, NIST P-521 also known as secp521r1
    ED25519 = 6  # OKP, Ed25519 for use w/ EdDSA only


class COSEKey(int, Enum):
    """
    COSE keys for public keys

    https://tools.ietf.org/html/rfc8152
    https://www.iana.org/assignments/cose/cose.xhtml#table-key-common-parameters
    https://www.iana.org/assignments/cose/cose.xhtml#table-key-type-parameters
    """

    KTY = 1
    ALG = 3
    # EC2, OKP
    CRV = -1
    X = -2
    # EC2
    Y = -3
    # RSA
    N = -1
    E = -2
