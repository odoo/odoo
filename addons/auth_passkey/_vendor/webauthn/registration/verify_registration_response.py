import hashlib
from dataclasses import dataclass, asdict
from typing import List, Mapping, Optional, Union

from ...webauthn.helpers import (
    aaguid_to_string,
    bytes_to_base64url,
    byteslike_to_bytes,
    decode_credential_public_key,
    parse_attestation_object,
    parse_client_data_json,
    parse_backup_flags,
    parse_registration_credential_json,
)
from ...webauthn.helpers.cose import COSEAlgorithmIdentifier
from ...webauthn.helpers.exceptions import InvalidRegistrationResponse
from ...webauthn.helpers.structs import (
    AttestationFormat,
    ClientDataType,
    CredentialDeviceType,
    PublicKeyCredentialType,
    RegistrationCredential,
    TokenBindingStatus,
)
from .formats.android_key import verify_android_key
from .formats.android_safetynet import verify_android_safetynet
from .formats.apple import verify_apple
from .formats.fido_u2f import verify_fido_u2f
from .formats.packed import verify_packed
from .formats.tpm import verify_tpm
from .generate_registration_options import default_supported_pub_key_algs


@dataclass
class VerifiedRegistration:
    """Information about a verified attestation of which an RP can make use.

    Attributes:
        `credential_id`: The generated credential's ID
        `credential_public_key`: The generated credential's public key
        `sign_count`: How many times the authenticator says the credential was used
        `aaguid`: A 128-bit identifier indicating the type and vendor of the authenticator
        `fmt`: The attestation format
        `credential_type`: The literal string "public-key"
        `user_verified`: Whether the user was verified by the authenticator
        `attestation_object`: The raw attestation object for later scrutiny
    """

    credential_id: bytes
    credential_public_key: bytes
    sign_count: int
    aaguid: str
    fmt: AttestationFormat
    credential_type: PublicKeyCredentialType
    user_verified: bool
    attestation_object: bytes
    credential_device_type: CredentialDeviceType
    credential_backed_up: bool


expected_token_binding_statuses = [
    TokenBindingStatus.SUPPORTED,
    TokenBindingStatus.PRESENT,
]


def verify_registration_response(
    *,
    credential: Union[str, dict, RegistrationCredential],
    expected_challenge: bytes,
    expected_rp_id: str,
    expected_origin: Union[str, List[str]],
    require_user_verification: bool = False,
    supported_pub_key_algs: List[COSEAlgorithmIdentifier] = default_supported_pub_key_algs,
    pem_root_certs_bytes_by_fmt: Optional[Mapping[AttestationFormat, List[bytes]]] = None,
) -> VerifiedRegistration:
    """Verify an authenticator's response to navigator.credentials.create()

    Args:
        - `credential`: The value returned from `navigator.credentials.create()`. Can be either a
          stringified JSON object, a plain dict, or an instance of RegistrationCredential
        - `expected_challenge`: The challenge passed to the authenticator within the preceding
          registration options.
        - `expected_rp_id`: The Relying Party's unique identifier as specified in the precending
          registration options.
        - `expected_origin`: The domain, with HTTP protocol (e.g. "https://domain.here"), on which
          the registration should have occurred. Can also be a list of expected origins.
        - (optional) `require_user_verification`: Whether or not to require that the authenticator
          verified the user.
        - (optional) `supported_pub_key_algs`: A list of public key algorithm IDs the RP chooses to
          restrict support to. Defaults to all supported algorithm IDs.
        - (optional) `pem_root_certs_bytes_by_fmt`: A list of root certificates, in PEM format, to
          be used to validate the certificate chains for specific attestation statement formats.

    Returns:
        Information about the authenticator and registration

    Raises:
        `helpers.exceptions.InvalidRegistrationResponse` if the response cannot be verified
    """
    if isinstance(credential, str) or isinstance(credential, dict):
        credential = parse_registration_credential_json(credential)

    verified = False

    # FIDO-specific check
    if bytes_to_base64url(credential.raw_id) != credential.id:
        raise InvalidRegistrationResponse("id and raw_id were not equivalent")

    # FIDO-specific check
    if credential.type != PublicKeyCredentialType.PUBLIC_KEY:
        raise InvalidRegistrationResponse(
            f'Unexpected credential type "{credential.type}", expected "public-key"'
        )

    response = credential.response

    client_data_bytes = byteslike_to_bytes(response.client_data_json)
    attestation_object_bytes = byteslike_to_bytes(response.attestation_object)

    client_data = parse_client_data_json(client_data_bytes)

    if client_data.type != ClientDataType.WEBAUTHN_CREATE:
        raise InvalidRegistrationResponse(
            f'Unexpected client data type "{client_data.type}", expected "{ClientDataType.WEBAUTHN_CREATE}"'
        )

    if expected_challenge != client_data.challenge:
        raise InvalidRegistrationResponse("Client data challenge was not expected challenge")

    if isinstance(expected_origin, str):
        if expected_origin != client_data.origin:
            raise InvalidRegistrationResponse(
                f'Unexpected client data origin "{client_data.origin}", expected "{expected_origin}"'
            )
    else:
        try:
            expected_origin.index(client_data.origin)
        except ValueError:
            raise InvalidRegistrationResponse(
                f'Unexpected client data origin "{client_data.origin}", expected one of {expected_origin}'
            )

    if client_data.token_binding:
        status = client_data.token_binding.status
        if status not in expected_token_binding_statuses:
            raise InvalidRegistrationResponse(
                f'Unexpected token_binding status of "{status}", expected one of "{",".join(expected_token_binding_statuses)}"'
            )

    attestation_object = parse_attestation_object(attestation_object_bytes)

    auth_data = attestation_object.auth_data

    # Generate a hash of the expected RP ID for comparison
    expected_rp_id_hash = hashlib.sha256()
    expected_rp_id_hash.update(expected_rp_id.encode("utf-8"))
    expected_rp_id_hash_bytes = expected_rp_id_hash.digest()

    if auth_data.rp_id_hash != expected_rp_id_hash_bytes:
        raise InvalidRegistrationResponse("Unexpected RP ID hash")

    if not auth_data.flags.up:
        raise InvalidRegistrationResponse("User was not present during attestation")

    if require_user_verification and not auth_data.flags.uv:
        raise InvalidRegistrationResponse(
            "User verification is required but user was not verified during attestation"
        )

    if not auth_data.attested_credential_data:
        raise InvalidRegistrationResponse("Authenticator did not provide attested credential data")

    attested_credential_data = auth_data.attested_credential_data

    if not attested_credential_data.credential_id:
        raise InvalidRegistrationResponse("Authenticator did not provide a credential ID")

    if not attested_credential_data.credential_public_key:
        raise InvalidRegistrationResponse("Authenticator did not provide a credential public key")

    if not attested_credential_data.aaguid:
        raise InvalidRegistrationResponse("Authenticator did not provide an AAGUID")

    decoded_credential_public_key = decode_credential_public_key(
        attested_credential_data.credential_public_key
    )

    if decoded_credential_public_key.alg not in supported_pub_key_algs:
        raise InvalidRegistrationResponse(
            f'Unsupported credential public key alg "{decoded_credential_public_key.alg}", expected one of: {supported_pub_key_algs}'
        )

    # Prepare a list of possible root certificates for certificate chain validation
    pem_root_certs_bytes: List[bytes] = []
    if pem_root_certs_bytes_by_fmt:
        custom_certs = pem_root_certs_bytes_by_fmt.get(attestation_object.fmt)
        if custom_certs:
            # Load any provided custom root certs
            pem_root_certs_bytes.extend(custom_certs)

    if attestation_object.fmt == AttestationFormat.NONE:
        # A "none" attestation should not contain _anything_ in its attestation statement
        any_att_stmt_fields_set = any(
            [field is not None for field in asdict(attestation_object.att_stmt).values()]
        )

        if any_att_stmt_fields_set:
            raise InvalidRegistrationResponse(
                "None attestation had unexpected attestation statement"
            )

        # There's nothing else to verify, so mark the verification successful
        verified = True
    elif attestation_object.fmt == AttestationFormat.FIDO_U2F:
        verified = verify_fido_u2f(
            attestation_statement=attestation_object.att_stmt,
            client_data_json=client_data_bytes,
            rp_id_hash=auth_data.rp_id_hash,
            credential_id=attested_credential_data.credential_id,
            credential_public_key=attested_credential_data.credential_public_key,
            aaguid=attested_credential_data.aaguid,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    elif attestation_object.fmt == AttestationFormat.PACKED:
        verified = verify_packed(
            attestation_statement=attestation_object.att_stmt,
            attestation_object=attestation_object_bytes,
            client_data_json=client_data_bytes,
            credential_public_key=attested_credential_data.credential_public_key,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    elif attestation_object.fmt == AttestationFormat.TPM:
        verified = verify_tpm(
            attestation_statement=attestation_object.att_stmt,
            attestation_object=attestation_object_bytes,
            client_data_json=client_data_bytes,
            credential_public_key=attested_credential_data.credential_public_key,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    elif attestation_object.fmt == AttestationFormat.APPLE:
        verified = verify_apple(
            attestation_statement=attestation_object.att_stmt,
            attestation_object=attestation_object_bytes,
            client_data_json=client_data_bytes,
            credential_public_key=attested_credential_data.credential_public_key,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    elif attestation_object.fmt == AttestationFormat.ANDROID_SAFETYNET:
        verified = verify_android_safetynet(
            attestation_statement=attestation_object.att_stmt,
            attestation_object=attestation_object_bytes,
            client_data_json=client_data_bytes,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    elif attestation_object.fmt == AttestationFormat.ANDROID_KEY:
        verified = verify_android_key(
            attestation_statement=attestation_object.att_stmt,
            attestation_object=attestation_object_bytes,
            client_data_json=client_data_bytes,
            credential_public_key=attested_credential_data.credential_public_key,
            pem_root_certs_bytes=pem_root_certs_bytes,
        )
    else:
        # Raise exception on an attestation format we're not prepared to verify
        raise InvalidRegistrationResponse(
            f'Unsupported attestation type "{attestation_object.fmt}"'
        )

    # If we got this far and still couldn't verify things then raise an error instead
    # of simply returning False
    if not verified:
        raise InvalidRegistrationResponse("Attestation statement could not be verified")

    parsed_backup_flags = parse_backup_flags(auth_data.flags)

    return VerifiedRegistration(
        credential_id=attested_credential_data.credential_id,
        credential_public_key=attested_credential_data.credential_public_key,
        sign_count=auth_data.sign_count,
        aaguid=aaguid_to_string(attested_credential_data.aaguid),
        fmt=attestation_object.fmt,
        credential_type=credential.type,
        user_verified=auth_data.flags.uv,
        attestation_object=attestation_object_bytes,
        credential_device_type=parsed_backup_flags.credential_device_type,
        credential_backed_up=parsed_backup_flags.credential_backed_up,
    )
