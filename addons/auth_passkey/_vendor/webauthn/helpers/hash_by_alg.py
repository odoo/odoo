import hashlib
from typing import Optional

from .cose import COSEAlgorithmIdentifier

SHA_256 = [
    COSEAlgorithmIdentifier.ECDSA_SHA_256,
    COSEAlgorithmIdentifier.RSASSA_PSS_SHA_256,
    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
]
SHA_384 = [
    COSEAlgorithmIdentifier.RSASSA_PSS_SHA_384,
    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_384,
]
SHA_512 = [
    COSEAlgorithmIdentifier.ECDSA_SHA_512,
    COSEAlgorithmIdentifier.RSASSA_PSS_SHA_512,
    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_512,
]
SHA_1 = [
    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_1,
]


def hash_by_alg(to_hash: bytes, alg: Optional[COSEAlgorithmIdentifier] = None) -> bytes:
    """
    Generate a hash of `to_hash` by the specified COSE algorithm ID. Defaults to hashing
    with SHA256
    """
    # Default to SHA256 for hashing
    hash = hashlib.sha256()

    if alg in SHA_384:
        hash = hashlib.sha384()
    elif alg in SHA_512:
        hash = hashlib.sha512()
    elif alg in SHA_1:
        hash = hashlib.sha1()

    hash.update(to_hash)
    return hash.digest()
