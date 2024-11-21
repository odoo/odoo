import json
from json.decoder import JSONDecodeError
from typing import Union

from .base64url_to_bytes import base64url_to_bytes
from .byteslike_to_bytes import byteslike_to_bytes
from .exceptions import InvalidJSONStructure
from .structs import CollectedClientData, TokenBinding


def parse_client_data_json(val: bytes) -> CollectedClientData:
    """
    Break apart `response.clientDataJSON` buffer into structured data
    """
    val = byteslike_to_bytes(val)

    try:
        json_dict = json.loads(val)
    except JSONDecodeError:
        raise InvalidJSONStructure("Unable to decode client_data_json bytes as JSON")

    # Ensure required values are present in client data
    if "type" not in json_dict:
        raise InvalidJSONStructure('client_data_json missing required property "type"')
    if "challenge" not in json_dict:
        raise InvalidJSONStructure('client_data_json missing required property "challenge"')
    if "origin" not in json_dict:
        raise InvalidJSONStructure('client_data_json missing required property "origin"')

    client_data = CollectedClientData(
        type=json_dict["type"],
        challenge=base64url_to_bytes(json_dict["challenge"]),
        origin=json_dict["origin"],
    )

    # Populate optional values if set
    if "crossOrigin" in json_dict:
        cross_origin = bool(json_dict["crossOrigin"])
        client_data.cross_origin = cross_origin

    if "tokenBinding" in json_dict:
        token_binding_dict = json_dict["tokenBinding"]

        # Some U2F devices set a string to `token_binding`, in which case ignore it
        if type(token_binding_dict) is dict:
            if "status" not in token_binding_dict:
                raise InvalidJSONStructure('token_binding missing required property "status"')

            status = token_binding_dict["status"]
            try:
                # This will raise ValidationError on an unexpected status
                token_binding = TokenBinding(status=status)

                # Handle optional values
                if "id" in token_binding_dict:
                    id = token_binding_dict["id"]
                    token_binding.id = f"{id}"

                client_data.token_binding = token_binding
            except Exception:
                # If we encounter a status we don't expect then ignore token_binding
                # completely
                pass

    return client_data
