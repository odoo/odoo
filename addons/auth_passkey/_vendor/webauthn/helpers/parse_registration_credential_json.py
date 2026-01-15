import json
from json.decoder import JSONDecodeError
from typing import Union, Optional, List

from .base64url_to_bytes import base64url_to_bytes
from .exceptions import InvalidRegistrationResponse, InvalidJSONStructure
from .structs import (
    AuthenticatorAttachment,
    AuthenticatorAttestationResponse,
    AuthenticatorTransport,
    PublicKeyCredentialType,
    RegistrationCredential,
)


def parse_registration_credential_json(json_val: Union[str, dict]) -> RegistrationCredential:
    """
    Parse a JSON form of a registration credential, as either a stringified JSON object or a
    plain dict, into an instance of RegistrationCredential
    """
    if isinstance(json_val, str):
        try:
            json_val = json.loads(json_val)
        except JSONDecodeError:
            raise InvalidJSONStructure("Unable to decode credential as JSON")

    if not isinstance(json_val, dict):
        raise InvalidJSONStructure("Credential was not a JSON object")

    cred_id = json_val.get("id")
    if not isinstance(cred_id, str):
        raise InvalidJSONStructure("Credential missing required id")

    cred_raw_id = json_val.get("rawId")
    if not isinstance(cred_raw_id, str):
        raise InvalidJSONStructure("Credential missing required rawId")

    cred_response = json_val.get("response")
    if not isinstance(cred_response, dict):
        raise InvalidJSONStructure("Credential missing required response")

    response_client_data_json = cred_response.get("clientDataJSON")
    if not isinstance(response_client_data_json, str):
        raise InvalidJSONStructure("Credential response missing required clientDataJSON")

    response_attestation_object = cred_response.get("attestationObject")
    if not isinstance(response_attestation_object, str):
        raise InvalidJSONStructure("Credential response missing required attestationObject")

    cred_type = json_val.get("type")
    try:
        # Simply try to get the single matching Enum. We'll set the literal value below assuming
        # the code can get past here (this is basically a mypy optimization)
        PublicKeyCredentialType(cred_type)
    except ValueError as cred_type_exc:
        raise InvalidJSONStructure("Credential had unexpected type") from cred_type_exc

    transports: Optional[List[AuthenticatorTransport]] = None
    response_transports = cred_response.get("transports")
    if isinstance(response_transports, list):
        transports = []
        for val in response_transports:
            try:
                transport_enum = AuthenticatorTransport(val)
                transports.append(transport_enum)
            except ValueError:
                pass

    cred_authenticator_attachment = json_val.get("authenticatorAttachment")
    if isinstance(cred_authenticator_attachment, str):
        try:
            cred_authenticator_attachment = AuthenticatorAttachment(cred_authenticator_attachment)
        except ValueError as cred_attachment_exc:
            raise InvalidJSONStructure(
                "Credential had unexpected authenticatorAttachment"
            ) from cred_attachment_exc
    else:
        cred_authenticator_attachment = None

    try:
        registration_credential = RegistrationCredential(
            id=cred_id,
            raw_id=base64url_to_bytes(cred_raw_id),
            response=AuthenticatorAttestationResponse(
                client_data_json=base64url_to_bytes(response_client_data_json),
                attestation_object=base64url_to_bytes(response_attestation_object),
                transports=transports,
            ),
            authenticator_attachment=cred_authenticator_attachment,
            type=PublicKeyCredentialType.PUBLIC_KEY,
        )
    except Exception as exc:
        raise InvalidRegistrationResponse(
            "Could not parse registration credential from JSON data"
        ) from exc

    return registration_credential
