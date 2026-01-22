# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.


import typing

from cryptography import utils
from cryptography.hazmat._der import (
    DERReader,
    INTEGER,
    SEQUENCE,
    encode_der,
    encode_der_integer,
)
from cryptography.hazmat.primitives import hashes


def decode_dss_signature(signature: bytes) -> typing.Tuple[int, int]:
    with DERReader(signature).read_single_element(SEQUENCE) as seq:
        r = seq.read_element(INTEGER).as_integer()
        s = seq.read_element(INTEGER).as_integer()
        return r, s


def encode_dss_signature(r: int, s: int) -> bytes:
    return encode_der(
        SEQUENCE,
        encode_der(INTEGER, encode_der_integer(r)),
        encode_der(INTEGER, encode_der_integer(s)),
    )


class Prehashed(object):
    def __init__(self, algorithm: hashes.HashAlgorithm):
        if not isinstance(algorithm, hashes.HashAlgorithm):
            raise TypeError("Expected instance of HashAlgorithm.")

        self._algorithm = algorithm
        self._digest_size = algorithm.digest_size

    digest_size = utils.read_only_property("_digest_size")
