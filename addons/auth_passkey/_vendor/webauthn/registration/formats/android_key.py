import hashlib
from typing import List

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.x509 import (
    Extension,
    ExtensionNotFound,
    ObjectIdentifier,
    UnrecognizedExtension,
)

from ....webauthn.helpers import (
    decode_credential_public_key,
    decoded_public_key_to_cryptography,
    parse_cbor,
    validate_certificate_chain,
    verify_signature,
)
from ....webauthn.helpers.asn1.android_key import (
    AuthorizationList,
    KeyDescription,
    KeyOrigin,
    KeyPurpose,
)
from ....webauthn.helpers.exceptions import (
    InvalidCertificateChain,
    InvalidRegistrationResponse,
)
from ....webauthn.helpers.known_root_certs import (
    google_hardware_attestation_root_1,
    google_hardware_attestation_root_2,
)
from ....webauthn.helpers.structs import AttestationStatement


def verify_android_key(
    *,
    attestation_statement: AttestationStatement,
    attestation_object: bytes,
    client_data_json: bytes,
    credential_public_key: bytes,
    pem_root_certs_bytes: List[bytes],
) -> bool:
    """Verify an "android-key" attestation statement

    See https://www.w3.org/TR/webauthn-2/#sctn-android-key-attestation

    Also referenced: https://source.android.com/security/keystore/attestation
    """
    if not attestation_statement.sig:
        raise InvalidRegistrationResponse(
            "Attestation statement was missing signature (Android Key)"
        )

    if not attestation_statement.alg:
        raise InvalidRegistrationResponse(
            "Attestation statement was missing algorithm (Android Key)"
        )

    if not attestation_statement.x5c:
        raise InvalidRegistrationResponse("Attestation statement was missing x5c (Android Key)")

    # Validate certificate chain
    try:
        # Include known root certificates for this attestation format
        pem_root_certs_bytes.append(google_hardware_attestation_root_1)
        pem_root_certs_bytes.append(google_hardware_attestation_root_2)

        validate_certificate_chain(
            x5c=attestation_statement.x5c,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    except InvalidCertificateChain as err:
        raise InvalidRegistrationResponse(f"{err} (Android Key)")

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

    # Verify that sig is a valid signature over the concatenation of authenticatorData
    # and clientDataHash using the public key in the first certificate in x5c with the
    # algorithm specified in alg.
    attestation_cert_bytes = attestation_statement.x5c[0]
    attestation_cert = x509.load_der_x509_certificate(attestation_cert_bytes, default_backend())
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
            "Could not verify attestation statement signature (Android Key)"
        )

    # Verify that the public key in the first certificate in x5c matches the
    # credentialPublicKey in the attestedCredentialData in authenticatorData.
    attestation_cert_pub_key_bytes = attestation_cert_pub_key.public_bytes(
        Encoding.DER,
        PublicFormat.SubjectPublicKeyInfo,
    )
    # Convert our raw public key bytes into the same format cryptography generates for
    # the cert subject key
    decoded_pub_key = decode_credential_public_key(credential_public_key)
    pub_key_crypto = decoded_public_key_to_cryptography(decoded_pub_key)
    pub_key_crypto_bytes = pub_key_crypto.public_bytes(
        Encoding.DER,
        PublicFormat.SubjectPublicKeyInfo,
    )

    if attestation_cert_pub_key_bytes != pub_key_crypto_bytes:
        raise InvalidRegistrationResponse(
            "Certificate public key did not match credential public key (Android Key)"
        )

    # Verify that the attestationChallenge field in the attestation certificate
    # extension data is identical to clientDataHash.
    ext_key_description_oid = "1.3.6.1.4.1.11129.2.1.17"
    try:
        cert_extensions = attestation_cert.extensions
        ext_key_description: Extension = cert_extensions.get_extension_for_oid(
            ObjectIdentifier(ext_key_description_oid)
        )
    except ExtensionNotFound:
        raise InvalidRegistrationResponse(
            f"Certificate missing extension {ext_key_description_oid} (Android Key)"
        )

    # Peel apart the Extension into an UnrecognizedExtension, then the bytes we actually
    # want
    ext_value_wrapper: UnrecognizedExtension = ext_key_description.value
    ext_value: bytes = ext_value_wrapper.value
    parsed_ext = KeyDescription.load(ext_value)

    # Verify the following using the appropriate authorization list from the attestation
    # certificate extension data:
    software_enforced: AuthorizationList = parsed_ext["softwareEnforced"]
    tee_enforced: AuthorizationList = parsed_ext["teeEnforced"]

    # The AuthorizationList.allApplications field is not present on either authorization
    # list (softwareEnforced nor teeEnforced), since PublicKeyCredential MUST be scoped
    # to the RP ID.
    if software_enforced["allApplications"].native is not None:
        raise InvalidRegistrationResponse(
            "allApplications field was present in softwareEnforced (Android Key)"
        )

    if tee_enforced["allApplications"].native is not None:
        raise InvalidRegistrationResponse(
            "allApplications field was present in teeEnforced (Android Key)"
        )

    # The value in the AuthorizationList.origin field is equal to KM_ORIGIN_GENERATED.
    origin = tee_enforced["origin"].native
    if origin != KeyOrigin.GENERATED:
        raise InvalidRegistrationResponse(
            f"teeEnforced.origin {origin} was not {KeyOrigin.GENERATED}"
        )

    # The value in the AuthorizationList.purpose field is equal to KM_PURPOSE_SIGN.
    purpose = tee_enforced["purpose"].native
    if purpose != [KeyPurpose.SIGN]:
        raise InvalidRegistrationResponse(
            f"teeEnforced.purpose {purpose} was not [{KeyPurpose.SIGN}]"
        )

    return True
