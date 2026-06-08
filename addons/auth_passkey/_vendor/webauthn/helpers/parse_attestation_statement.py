from .structs import AttestationStatement


def parse_attestation_statement(val: dict) -> AttestationStatement:
    """
    Turn `response.attestationObject.attStmt` into structured data
    """
    attestation_statement = AttestationStatement()

    # Populate optional fields that may exist in the attestation statement
    if "sig" in val:
        attestation_statement.sig = val["sig"]
    if "x5c" in val:
        attestation_statement.x5c = val["x5c"]
    if "response" in val:
        attestation_statement.response = val["response"]
    if "alg" in val:
        attestation_statement.alg = val["alg"]
    if "ver" in val:
        attestation_statement.ver = val["ver"]
    if "certInfo" in val:
        attestation_statement.cert_info = val["certInfo"]
    if "pubArea" in val:
        attestation_statement.pub_area = val["pubArea"]

    return attestation_statement
