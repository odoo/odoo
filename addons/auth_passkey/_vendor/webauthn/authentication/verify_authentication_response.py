from dataclasses import dataclass
import hashlib
from typing import List, Union

from cryptography.exceptions import InvalidSignature

from ...webauthn.helpers import (
    bytes_to_base64url,
    byteslike_to_bytes,
    decode_credential_public_key,
    decoded_public_key_to_cryptography,
    parse_authenticator_data,
    parse_backup_flags,
    parse_client_data_json,
    parse_authentication_credential_json,
    verify_signature,
)
from ...webauthn.helpers.exceptions import InvalidAuthenticationResponse
from ...webauthn.helpers.structs import (
    AuthenticationCredential,
    ClientDataType,
    CredentialDeviceType,
    PublicKeyCredentialType,
    TokenBindingStatus,
)


@dataclass
class VerifiedAuthentication:
    """
    Information about a verified authentication of which an RP can make use
    """

    credential_id: bytes
    new_sign_count: int
    credential_device_type: CredentialDeviceType
    credential_backed_up: bool


expected_token_binding_statuses = [
    TokenBindingStatus.SUPPORTED,
    TokenBindingStatus.PRESENT,
]


def verify_authentication_response(
    *,
    credential: Union[str, dict, AuthenticationCredential],
    expected_challenge: bytes,
    expected_rp_id: str,
    expected_origin: Union[str, List[str]],
    credential_public_key: bytes,
    credential_current_sign_count: int,
    require_user_verification: bool = False,
) -> VerifiedAuthentication:
    """Verify a response from navigator.credentials.get()

    Args:
        - `credential`: The value returned from `navigator.credentials.get()`. Can be either a
          stringified JSON object, a plain dict, or an instance of RegistrationCredential
        - `expected_challenge`: The challenge passed to the authenticator within the preceding
          authentication options.
        - `expected_rp_id`: The Relying Party's unique identifier as specified in the preceding
          authentication options.
        - `expected_origin`: The domain, with HTTP protocol (e.g. "https://domain.here"), on which
          the authentication ceremony should have occurred.
        - `credential_public_key`: The public key for the credential's ID as provided in a
          preceding authenticator registration ceremony.
        - `credential_current_sign_count`: The current known number of times the authenticator was
          used.
        - (optional) `require_user_verification`: Whether or not to require that the authenticator
          verified the user.

    Returns:
        Information about the authenticator

    Raises:
        `helpers.exceptions.InvalidAuthenticationResponse` if the response cannot be verified
    """
    if isinstance(credential, str) or isinstance(credential, dict):
        credential = parse_authentication_credential_json(credential)

    # FIDO-specific check
    if bytes_to_base64url(credential.raw_id) != credential.id:
        raise InvalidAuthenticationResponse("id and raw_id were not equivalent")

    # FIDO-specific check
    if credential.type != PublicKeyCredentialType.PUBLIC_KEY:
        raise InvalidAuthenticationResponse(
            f'Unexpected credential type "{credential.type}", expected "public-key"'
        )

    response = credential.response

    client_data_bytes = byteslike_to_bytes(response.client_data_json)
    authenticator_data_bytes = byteslike_to_bytes(response.authenticator_data)
    signature_bytes = byteslike_to_bytes(response.signature)

    client_data = parse_client_data_json(client_data_bytes)

    if client_data.type != ClientDataType.WEBAUTHN_GET:
        raise InvalidAuthenticationResponse(
            f'Unexpected client data type "{client_data.type}", expected "{ClientDataType.WEBAUTHN_GET}"'
        )

    if expected_challenge != client_data.challenge:
        raise InvalidAuthenticationResponse("Client data challenge was not expected challenge")

    if isinstance(expected_origin, str):
        if expected_origin != client_data.origin:
            raise InvalidAuthenticationResponse(
                f'Unexpected client data origin "{client_data.origin}", expected "{expected_origin}"'
            )
    else:
        try:
            expected_origin.index(client_data.origin)
        except ValueError:
            raise InvalidAuthenticationResponse(
                f'Unexpected client data origin "{client_data.origin}", expected one of {expected_origin}'
            )

    if client_data.token_binding:
        status = client_data.token_binding.status
        if status not in expected_token_binding_statuses:
            raise InvalidAuthenticationResponse(
                f'Unexpected token_binding status of "{status}", expected one of "{",".join(expected_token_binding_statuses)}"'
            )

    auth_data = parse_authenticator_data(authenticator_data_bytes)

    # Generate a hash of the expected RP ID for comparison
    expected_rp_id_hash = hashlib.sha256()
    expected_rp_id_hash.update(expected_rp_id.encode("utf-8"))
    expected_rp_id_hash_bytes = expected_rp_id_hash.digest()

    if auth_data.rp_id_hash != expected_rp_id_hash_bytes:
        raise InvalidAuthenticationResponse("Unexpected RP ID hash")

    if not auth_data.flags.up:
        raise InvalidAuthenticationResponse("User was not present during authentication")

    if require_user_verification and not auth_data.flags.uv:
        raise InvalidAuthenticationResponse(
            "User verification is required but user was not verified during authentication"
        )

    if (
        auth_data.sign_count > 0 or credential_current_sign_count > 0
    ) and auth_data.sign_count <= credential_current_sign_count:
        # Require the sign count to have been incremented over what was reported by the
        # authenticator the last time this credential was used, otherwise this might be
        # a replay attack
        raise InvalidAuthenticationResponse(
            f"Response sign count of {auth_data.sign_count} was not greater than current count of {credential_current_sign_count}"
        )

    client_data_hash = hashlib.sha256()
    client_data_hash.update(client_data_bytes)
    client_data_hash_bytes = client_data_hash.digest()

    signature_base = authenticator_data_bytes + client_data_hash_bytes

    try:
        decoded_public_key = decode_credential_public_key(credential_public_key)
        crypto_public_key = decoded_public_key_to_cryptography(decoded_public_key)

        verify_signature(
            public_key=crypto_public_key,
            signature_alg=decoded_public_key.alg,
            signature=signature_bytes,
            data=signature_base,
        )
    except InvalidSignature:
        raise InvalidAuthenticationResponse("Could not verify authentication signature")

    parsed_backup_flags = parse_backup_flags(auth_data.flags)

    return VerifiedAuthentication(
        credential_id=credential.raw_id,
        new_sign_count=auth_data.sign_count,
        credential_device_type=parsed_backup_flags.credential_device_type,
        credential_backed_up=parsed_backup_flags.credential_backed_up,
    )
