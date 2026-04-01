import json
from typing import Union, Dict, Any

from .structs import (
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialRequestOptions,
)
from .bytes_to_base64url import bytes_to_base64url


def options_to_json(
    options: Union[
        PublicKeyCredentialCreationOptions,
        PublicKeyCredentialRequestOptions,
    ]
) -> str:
    """
    Prepare options for transmission to the front end as JSON
    """
    if isinstance(options, PublicKeyCredentialCreationOptions):
        _rp = {"name": options.rp.name}
        if options.rp.id:
            _rp["id"] = options.rp.id

        _user: Dict[str, Any] = {
            "id": bytes_to_base64url(options.user.id),
            "name": options.user.name,
            "displayName": options.user.display_name,
        }

        reg_to_return: Dict[str, Any] = {
            "rp": _rp,
            "user": _user,
            "challenge": bytes_to_base64url(options.challenge),
            "pubKeyCredParams": [
                {"type": param.type, "alg": param.alg} for param in options.pub_key_cred_params
            ],
        }

        # Begin handling optional values

        if options.timeout is not None:
            reg_to_return["timeout"] = options.timeout

        if options.exclude_credentials is not None:
            _excluded = options.exclude_credentials
            json_excluded = []

            for cred in _excluded:
                json_excluded_cred: Dict[str, Any] = {
                    "id": bytes_to_base64url(cred.id),
                    "type": cred.type.value,
                }

                if cred.transports:
                    json_excluded_cred["transports"] = [
                        transport.value for transport in cred.transports
                    ]

                json_excluded.append(json_excluded_cred)

            reg_to_return["excludeCredentials"] = json_excluded

        if options.authenticator_selection is not None:
            _selection = options.authenticator_selection
            json_selection: Dict[str, Any] = {}

            if _selection.authenticator_attachment is not None:
                json_selection[
                    "authenticatorAttachment"
                ] = _selection.authenticator_attachment.value

            if _selection.resident_key is not None:
                json_selection["residentKey"] = _selection.resident_key.value

            if _selection.require_resident_key is not None:
                json_selection["requireResidentKey"] = _selection.require_resident_key

            if _selection.user_verification is not None:
                json_selection["userVerification"] = _selection.user_verification.value

            reg_to_return["authenticatorSelection"] = json_selection

        if options.attestation is not None:
            reg_to_return["attestation"] = options.attestation.value

        return json.dumps(reg_to_return)

    if isinstance(options, PublicKeyCredentialRequestOptions):
        auth_to_return: Dict[str, Any] = {"challenge": bytes_to_base64url(options.challenge)}

        if options.timeout is not None:
            auth_to_return["timeout"] = options.timeout

        if options.rp_id is not None:
            auth_to_return["rpId"] = options.rp_id

        if options.allow_credentials is not None:
            _allowed = options.allow_credentials
            json_allowed = []

            for cred in _allowed:
                json_allowed_cred: Dict[str, Any] = {
                    "id": bytes_to_base64url(cred.id),
                    "type": cred.type.value,
                }

                if cred.transports:
                    json_allowed_cred["transports"] = [
                        transport.value for transport in cred.transports
                    ]

                json_allowed.append(json_allowed_cred)

            auth_to_return["allowCredentials"] = json_allowed

        if options.user_verification:
            auth_to_return["userVerification"] = options.user_verification.value

        return json.dumps(auth_to_return)

    raise TypeError(
        "Options was not instance of PublicKeyCredentialCreationOptions or PublicKeyCredentialRequestOptions"
    )
