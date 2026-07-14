from .parse_attestation_statement import parse_attestation_statement
from .parse_authenticator_data import parse_authenticator_data
from .structs import AttestationObject
from .parse_cbor import parse_cbor


def parse_attestation_object(val: bytes) -> AttestationObject:
    """
    Decode and peel apart the CBOR-encoded blob `response.attestationObject` into
    structured data.
    """
    attestation_dict = parse_cbor(val)

    decoded_attestation_object = AttestationObject(
        fmt=attestation_dict["fmt"],
        auth_data=parse_authenticator_data(attestation_dict["authData"]),
    )

    if "attStmt" in attestation_dict:
        decoded_attestation_object.att_stmt = parse_attestation_statement(
            attestation_dict["attStmt"]
        )

    return decoded_attestation_object
