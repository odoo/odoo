import hashlib
from typing import List

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend

from ....webauthn.helpers import (
    decode_credential_public_key,
    decoded_public_key_to_cryptography,
    parse_cbor,
    validate_certificate_chain,
    verify_signature,
)
from ....webauthn.helpers.exceptions import (
    InvalidCertificateChain,
    InvalidRegistrationResponse,
)
from ....webauthn.helpers.structs import AttestationStatement


def verify_packed(
    *,
    attestation_statement: AttestationStatement,
    attestation_object: bytes,
    client_data_json: bytes,
    credential_public_key: bytes,
    pem_root_certs_bytes: List[bytes],
) -> bool:
    """Verify a "packed" attestation statement

    See https://www.w3.org/TR/webauthn-2/#sctn-packed-attestation
    """
    if not attestation_statement.sig:
        raise InvalidRegistrationResponse("Attestation statement was missing signature (Packed)")

    if not attestation_statement.alg:
        raise InvalidRegistrationResponse("Attestation statement was missing algorithm (Packed)")

    # Extract attStmt bytes from attestation_object
    attestation_dict = parse_cbor(attestation_object)
    authenticator_data_bytes = attestation_dict["authData"]

    # Generate a hash of client_data_json
    client_data_hash = hashlib.sha256()
    client_data_hash.update(client_data_json)
    client_data_hash_bytes = client_data_hash.digest()

    verification_data = b"".join(
        [
            authenticator_data_bytes,
            client_data_hash_bytes,
        ]
    )

    if attestation_statement.x5c:
        # Validate the certificate chain
        try:
            validate_certificate_chain(
                x5c=attestation_statement.x5c,
                pem_root_certs_bytes=pem_root_certs_bytes,
            )
        except InvalidCertificateChain as err:
            raise InvalidRegistrationResponse(f"{err} (Packed)")

        attestation_cert_bytes = attestation_statement.x5c[0]
        attestation_cert = x509.load_der_x509_certificate(
            attestation_cert_bytes, default_backend()
        )
        attestation_cert_pub_key = attestation_cert.public_key()

        try:
            verify_signature(
                public_key=attestation_cert_pub_key,
                signature_alg=attestation_statement.alg,
                signature=attestation_statement.sig,
                data=verification_data,
            )
        except InvalidSignature:
            raise InvalidRegistrationResponse(
                "Could not verify attestation statement signature (Packed)"
            )
    else:
        # Self Attestation
        decoded_pub_key = decode_credential_public_key(credential_public_key)

        if decoded_pub_key.alg != attestation_statement.alg:
            raise InvalidRegistrationResponse(
                f"Credential public key alg {decoded_pub_key.alg} did not equal attestation statement alg {attestation_statement.alg}"
            )

        public_key = decoded_public_key_to_cryptography(decoded_pub_key)

        try:
            verify_signature(
                public_key=public_key,
                signature_alg=attestation_statement.alg,
                signature=attestation_statement.sig,
                data=verification_data,
            )
        except InvalidSignature:
            raise InvalidRegistrationResponse(
                "Could not verify attestation statement signature (Packed|Self)"
            )

    return True
