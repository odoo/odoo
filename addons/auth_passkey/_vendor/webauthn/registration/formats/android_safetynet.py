import base64
from dataclasses import dataclass
import hashlib
import json
from typing import List

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID

from ....webauthn.helpers.cose import COSEAlgorithmIdentifier
from ....webauthn.helpers import (
    base64url_to_bytes,
    parse_cbor,
    validate_certificate_chain,
    verify_safetynet_timestamp,
    verify_signature,
)
from ....webauthn.helpers.exceptions import (
    InvalidCertificateChain,
    InvalidRegistrationResponse,
)
from ....webauthn.helpers.known_root_certs import globalsign_r2, globalsign_root_ca
from ....webauthn.helpers.structs import AttestationStatement


@dataclass
class SafetyNetJWSHeader:
    """Properties in the Header of a SafetyNet JWS"""

    alg: str
    x5c: List[str]


@dataclass
class SafetyNetJWSPayload:
    """Properties in the Payload of a SafetyNet JWS

    Values below correspond to camelCased properties in the JWS itself. This class
    handles converting the properties to Pythonic snake_case.
    """

    nonce: str
    timestamp_ms: int
    apk_package_name: str
    apk_digest_sha256: str
    cts_profile_match: bool
    apk_certificate_digest_sha256: List[str]
    basic_integrity: bool


def verify_android_safetynet(
    *,
    attestation_statement: AttestationStatement,
    attestation_object: bytes,
    client_data_json: bytes,
    pem_root_certs_bytes: List[bytes],
    verify_timestamp_ms: bool = True,
) -> bool:
    """Verify an "android-safetynet" attestation statement

    See https://www.w3.org/TR/webauthn-2/#sctn-android-safetynet-attestation

    Notes:
        - `verify_timestamp_ms` is a kind of escape hatch specifically for enabling
          testing of this method. Without this we can't use static responses in unit
          tests because they'll always evaluate as expired. This flag can be removed
          from this method if we ever figure out how to dynamically create
          safetynet-formatted responses that can be immediately tested.
    """

    if not attestation_statement.ver:
        # As of this writing, there is only one format of the SafetyNet response and
        # ver is reserved for future use (so for now just make sure it's present)
        raise InvalidRegistrationResponse("Attestation statement was missing version (SafetyNet)")

    if not attestation_statement.response:
        raise InvalidRegistrationResponse("Attestation statement was missing response (SafetyNet)")

    # Begin peeling apart the JWS in the attestation statement response
    jws = attestation_statement.response.decode("ascii")
    jws_parts = jws.split(".")

    if len(jws_parts) != 3:
        raise InvalidRegistrationResponse("Response JWS did not have three parts (SafetyNet)")

    header_json = json.loads(base64url_to_bytes(jws_parts[0]))
    payload_json = json.loads(base64url_to_bytes(jws_parts[1]))

    header = SafetyNetJWSHeader(
        alg=header_json.get("alg", ""),
        x5c=header_json.get("x5c", []),
    )
    payload = SafetyNetJWSPayload(
        nonce=payload_json.get("nonce", ""),
        timestamp_ms=payload_json.get("timestampMs", 0),
        apk_package_name=payload_json.get("apkPackageName", ""),
        apk_digest_sha256=payload_json.get("apkDigestSha256", ""),
        cts_profile_match=payload_json.get("ctsProfileMatch", False),
        apk_certificate_digest_sha256=payload_json.get("apkCertificateDigestSha256", []),
        basic_integrity=payload_json.get("basicIntegrity", False),
    )

    signature_bytes_str: str = jws_parts[2]

    # Verify that the nonce attribute in the payload of response is identical to the
    # Base64 encoding of the SHA-256 hash of the concatenation of authenticatorData and
    # clientDataHash.

    # Extract attStmt bytes from attestation_object
    attestation_dict = parse_cbor(attestation_object)
    authenticator_data_bytes = attestation_dict["authData"]

    # Generate a hash of client_data_json
    client_data_hash = hashlib.sha256()
    client_data_hash.update(client_data_json)
    client_data_hash_bytes = client_data_hash.digest()

    nonce_data = b"".join(
        [
            authenticator_data_bytes,
            client_data_hash_bytes,
        ]
    )
    # Start with a sha256 hash
    nonce_data_hash = hashlib.sha256()
    nonce_data_hash.update(nonce_data)
    nonce_data_hash_bytes = nonce_data_hash.digest()
    # Encode to base64
    nonce_data_hash_bytes = base64.b64encode(nonce_data_hash_bytes)
    # Finish by decoding to string
    nonce_data_str = nonce_data_hash_bytes.decode("utf-8")

    if payload.nonce != nonce_data_str:
        raise InvalidRegistrationResponse("Payload nonce was not expected value (SafetyNet)")

    # Verify that the SafetyNet response actually came from the SafetyNet service
    # by following the steps in the SafetyNet online documentation.
    x5c = [base64url_to_bytes(cert) for cert in header.x5c]

    if not payload.cts_profile_match:
        raise InvalidRegistrationResponse("Could not verify device integrity (SafetyNet)")

    if verify_timestamp_ms:
        try:
            verify_safetynet_timestamp(payload.timestamp_ms)
        except ValueError as err:
            raise InvalidRegistrationResponse(f"{err} (SafetyNet)")

    # Verify that the leaf certificate was issued to the hostname attest.android.com
    attestation_cert = x509.load_der_x509_certificate(x5c[0], default_backend())
    cert_common_name = attestation_cert.subject.get_attributes_for_oid(
        NameOID.COMMON_NAME,
    )[0]

    if cert_common_name.value != "attest.android.com":
        raise InvalidRegistrationResponse(
            'Certificate common name was not "attest.android.com" (SafetyNet)'
        )

    # Validate certificate chain
    try:
        # Include known root certificates for this attestation format with whatever
        # other certs were provided
        pem_root_certs_bytes.append(globalsign_r2)
        pem_root_certs_bytes.append(globalsign_root_ca)

        validate_certificate_chain(
            x5c=x5c,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    except InvalidCertificateChain as err:
        raise InvalidRegistrationResponse(f"{err} (SafetyNet)")

    # Verify signature
    verification_data = f"{jws_parts[0]}.{jws_parts[1]}".encode("utf-8")
    signature_bytes = base64url_to_bytes(signature_bytes_str)

    if header.alg != "RS256":
        raise InvalidRegistrationResponse(f"JWS header alg was not RS256: {header.alg} (SafetyNet")

    # Get cert public key bytes
    attestation_cert_pub_key = attestation_cert.public_key()

    try:
        verify_signature(
            public_key=attestation_cert_pub_key,
            signature_alg=COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
            signature=signature_bytes,
            data=verification_data,
        )
    except InvalidSignature:
        raise InvalidRegistrationResponse(
            "Could not verify attestation statement signature (Packed)"
        )

    return True
