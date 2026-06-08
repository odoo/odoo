from typing import Union

from .byteslike_to_bytes import byteslike_to_bytes
from .exceptions import InvalidAuthenticatorDataStructure
from .structs import AttestedCredentialData, AuthenticatorData, AuthenticatorDataFlags
from .parse_cbor import parse_cbor
from .encode_cbor import encode_cbor


def parse_authenticator_data(val: bytes) -> AuthenticatorData:
    """
    Turn `response.attestationObject.authData` into structured data
    """
    val = byteslike_to_bytes(val)

    # Don't bother parsing if there aren't enough bytes for at least:
    # - rpIdHash (32 bytes)
    # - flags (1 byte)
    # - signCount (4 bytes)
    if len(val) < 37:
        raise InvalidAuthenticatorDataStructure(
            f"Authenticator data was {len(val)} bytes, expected at least 37 bytes"
        )

    pointer = 0

    rp_id_hash = val[pointer:32]
    pointer += 32

    # Cast byte to ordinal so we can use bitwise operators on it
    flags_bytes = ord(val[pointer : pointer + 1])
    pointer += 1

    sign_count = val[pointer : pointer + 4]
    pointer += 4

    # Parse flags
    flags = AuthenticatorDataFlags(
        up=flags_bytes & (1 << 0) != 0,
        uv=flags_bytes & (1 << 2) != 0,
        be=flags_bytes & (1 << 3) != 0,
        bs=flags_bytes & (1 << 4) != 0,
        at=flags_bytes & (1 << 6) != 0,
        ed=flags_bytes & (1 << 7) != 0,
    )

    # The value to return
    authenticator_data = AuthenticatorData(
        rp_id_hash=rp_id_hash,
        flags=flags,
        sign_count=int.from_bytes(sign_count, "big"),
    )

    # Parse AttestedCredentialData if present
    if flags.at is True:
        aaguid = val[pointer : pointer + 16]
        pointer += 16

        credential_id_len = int.from_bytes(val[pointer : pointer + 2], "big")
        pointer += 2

        credential_id = val[pointer : pointer + credential_id_len]
        pointer += credential_id_len

        """
        Some authenticators incorrectly compose authData when using EdDSA for their public keys.
        A CBOR "Map of 3 items" (0xA3) should be "Map of 4 items" (0xA4), and if we manually adjust
        the single byte there's a good chance the authData can be correctly parsed. Let's try to
        detect when this happens and gracefully handle it.
        """
        # Decodes to `{1: "OKP", 3: -8, -1: "Ed25519"}` (it's missing key -2 a.k.a. COSEKey.X)
        bad_eddsa_cbor = bytearray.fromhex("a301634f4b500327206745643235353139")
        # If we find the bytes here then let's fix the bad data
        if val[pointer : pointer + len(bad_eddsa_cbor)] == bad_eddsa_cbor:
            # Make a mutable copy of the bytes...
            _val = bytearray(val)
            # ...Fix the bad byte...
            _val[pointer] = 0xA4
            # ...Then replace `val` with the fixed bytes
            val = bytes(_val)

        # Load the next CBOR-encoded value
        credential_public_key = parse_cbor(val[pointer:])
        credential_public_key_bytes = encode_cbor(credential_public_key)
        pointer += len(credential_public_key_bytes)

        attested_cred_data = AttestedCredentialData(
            aaguid=aaguid,
            credential_id=credential_id,
            credential_public_key=credential_public_key_bytes,
        )
        authenticator_data.attested_credential_data = attested_cred_data

    if flags.ed is True:
        extension_object = parse_cbor(val[pointer:])
        extension_bytes = encode_cbor(extension_object)
        pointer += len(extension_bytes)
        authenticator_data.extensions = extension_bytes

    # We should have parsed all authenticator data by this point
    if len(val) > pointer:
        raise InvalidAuthenticatorDataStructure(
            "Leftover bytes detected while parsing authenticator data"
        )

    return authenticator_data
