import secrets


def generate_challenge() -> bytes:
    """
    Create a random value for the authenticator to sign, going above and beyond the recommended
    number of random bytes as per https://www.w3.org/TR/webauthn-2/#sctn-cryptographic-challenges:

    "In order to prevent replay attacks, the challenges MUST contain enough entropy to make
    guessing them infeasible. Challenges SHOULD therefore be at least 16 bytes long."
    """
    return secrets.token_bytes(64)
