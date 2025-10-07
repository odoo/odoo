# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.x509.ocsp import (
    OCSPRequest,
    OCSPRequestBuilder,
    OCSPResponse,
    OCSPResponseBuilder,
    OCSPResponseStatus,
)

def load_der_ocsp_request(data: bytes) -> OCSPRequest: ...
def load_der_ocsp_response(data: bytes) -> OCSPResponse: ...
def create_ocsp_request(builder: OCSPRequestBuilder) -> OCSPRequest: ...
def create_ocsp_response(
    status: OCSPResponseStatus,
    builder: OCSPResponseBuilder | None,
    private_key: PrivateKeyTypes | None,
    hash_algorithm: hashes.HashAlgorithm | None,
) -> OCSPResponse: ...
