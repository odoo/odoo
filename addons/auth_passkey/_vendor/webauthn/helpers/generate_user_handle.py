import secrets


def generate_user_handle() -> bytes:
    """
    Convenience method RP's can use to generate a privacy-preserving random sequence of
    bytes as per best practices defined in the WebAuthn spec. This value is intended to
    be used as the value of `user_id` when calling `generate_registration_options()`,
    and can then be used during authentication verification to match the credential to
    a user.

    See https://www.w3.org/TR/webauthn-2/#sctn-user-handle-privacy:

    "It is RECOMMENDED to let the user handle be 64 random bytes, and store this value
    in the user's account."
    """
    return secrets.token_bytes(64)
