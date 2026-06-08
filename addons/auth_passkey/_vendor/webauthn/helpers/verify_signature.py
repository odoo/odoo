from typing import Union

from cryptography.hazmat.primitives.asymmetric.dsa import DSAPublicKey
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.asymmetric.ed448 import Ed448PublicKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x448 import X448PublicKey
from cryptography.hazmat.primitives.asymmetric.padding import MGF1, PSS, PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from .algorithms import (
    get_ec2_sig_alg,
    get_rsa_pkcs1_sig_alg,
    get_rsa_pss_sig_alg,
    is_rsa_pkcs,
    is_rsa_pss,
)
from .cose import COSEAlgorithmIdentifier
from .exceptions import UnsupportedAlgorithm, UnsupportedPublicKey


def verify_signature(
    *,
    public_key: Union[
        EllipticCurvePublicKey,
        RSAPublicKey,
        Ed25519PublicKey,
        DSAPublicKey,
        Ed448PublicKey,
        X25519PublicKey,
        X448PublicKey,
    ],
    signature_alg: COSEAlgorithmIdentifier,
    signature: bytes,
    data: bytes,
) -> None:
    """Verify a signature was signed with the private key corresponding to the provided
    public key.

    Args:
        `public_key`: A public key loaded via cryptography's `load_der_public_key`, `load_der_x509_certificate`, etc...
        `signature_alg`: Algorithm ID used to sign the signature
        `signature`: Signature to verify
        `data`: Data signed by private key

    Raises:
        `webauth.helpers.exceptions.UnsupportedAlgorithm` when the algorithm is not a recognized COSE algorithm ID
        `webauth.helpers.exceptions.UnsupportedPublicKey` when the public key is not a valid EC2, RSA, or OKP certificate
        `cryptography.exceptions.InvalidSignature` when the signature cannot be verified
    """
    if isinstance(public_key, EllipticCurvePublicKey):
        public_key.verify(signature, data, get_ec2_sig_alg(signature_alg))
    elif isinstance(public_key, RSAPublicKey):
        if is_rsa_pkcs(signature_alg):
            public_key.verify(signature, data, PKCS1v15(), get_rsa_pkcs1_sig_alg(signature_alg))
        elif is_rsa_pss(signature_alg):
            rsa_alg = get_rsa_pss_sig_alg(signature_alg)
            public_key.verify(
                signature,
                data,
                PSS(mgf=MGF1(rsa_alg), salt_length=PSS.MAX_LENGTH),
                rsa_alg,
            )
        else:
            raise UnsupportedAlgorithm(f"Unrecognized RSA signature alg {signature_alg}")
    elif isinstance(public_key, Ed25519PublicKey):
        public_key.verify(signature, data)
    else:
        raise UnsupportedPublicKey(
            f"Unsupported public key for signature verification: {public_key}"
        )
