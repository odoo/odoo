import hashlib

MASK_INT32 = 0x7FFFFFFF  # For signed Int32, only take 31 bits, as the MSB is the sign bit


def derive_seed_from(base_seed: int, index: int) -> int:
    """
    Deterministically derive a new 32-bit (signed) seed from a base seed and index.

    :param base_seed: Parent seed.
    :param index: Stable offset used to derive a distinct seed.
    :return: Positive signed 32-bit seed.
    """
    source = f'{base_seed}:{index}'.encode('utf-8')  # noqa: UP012
    hash_digest = hashlib.sha256(source).digest()
    # Masking is necessary to not overflow Postgres' int4 type
    new_seed = int.from_bytes(hash_digest[:4], 'big') & MASK_INT32

    return new_seed  # noqa: RET504
