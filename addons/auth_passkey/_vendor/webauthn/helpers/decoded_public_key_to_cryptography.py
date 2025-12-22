import codecs
from typing import Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePublicKey,
    EllipticCurvePublicNumbers,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPublicNumbers

from .algorithms import get_ec2_curve
from .cose import COSECRV, COSEAlgorithmIdentifier
from .decode_credential_public_key import (
    DecodedEC2PublicKey,
    DecodedOKPPublicKey,
    DecodedRSAPublicKey,
)
from .exceptions import UnsupportedPublicKey


def decoded_public_key_to_cryptography(
    public_key: Union[DecodedOKPPublicKey, DecodedEC2PublicKey, DecodedRSAPublicKey]
) -> Union[Ed25519PublicKey, EllipticCurvePublicKey, RSAPublicKey]:
    """Convert raw decoded public key parameters (crv, x, y, n, e, etc...) into
    public keys using primitives from the cryptography.io library
    """
    if isinstance(public_key, DecodedEC2PublicKey):
        """
        alg is -7 (ES256), where kty is 2 (with uncompressed points) and
        crv is 1 (P-256).
        https://www.w3.org/TR/webauthn-2/#sctn-public-key-easy
        """
        x = int(codecs.encode(public_key.x, "hex"), 16)
        y = int(codecs.encode(public_key.y, "hex"), 16)
        curve = get_ec2_curve(public_key.crv)

        ecc_pub_key = EllipticCurvePublicNumbers(x, y, curve).public_key(default_backend())

        return ecc_pub_key
    elif isinstance(public_key, DecodedRSAPublicKey):
        """
        alg is -257 (RS256)
        https://www.w3.org/TR/webauthn-2/#sctn-public-key-easy
        """
        e = int(codecs.encode(public_key.e, "hex"), 16)
        n = int(codecs.encode(public_key.n, "hex"), 16)

        rsa_pub_key = RSAPublicNumbers(e, n).public_key(default_backend())

        return rsa_pub_key
    elif isinstance(public_key, DecodedOKPPublicKey):
        """
        -8 (EdDSA), where crv is 6 (Ed25519).
        https://www.w3.org/TR/webauthn-2/#sctn-public-key-easy
        """
        if public_key.alg != COSEAlgorithmIdentifier.EDDSA or public_key.crv != COSECRV.ED25519:
            raise UnsupportedPublicKey(
                f"OKP public key with alg {public_key.alg} and crv {public_key.crv} is not supported"
            )

        okp_pub_key = Ed25519PublicKey.from_public_bytes(public_key.x)

        return okp_pub_key
    else:
        raise UnsupportedPublicKey(f"Unrecognized decoded public key: {public_key}")
