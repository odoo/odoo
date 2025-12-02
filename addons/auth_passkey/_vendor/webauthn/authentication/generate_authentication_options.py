from typing import List, Optional

from ..helpers import generate_challenge
from ..helpers.structs import (
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    UserVerificationRequirement,
)


def generate_authentication_options(
    *,
    rp_id: str,
    challenge: Optional[bytes] = None,
    timeout: int = 60000,
    allow_credentials: Optional[List[PublicKeyCredentialDescriptor]] = None,
    user_verification: UserVerificationRequirement = UserVerificationRequirement.PREFERRED,
) -> PublicKeyCredentialRequestOptions:
    """Generate options for retrieving a credential via navigator.credentials.get()

    Args:
        `rp_id`: The Relying Party's unique identifier as specified in attestations.
        (optional) `challenge`: A byte sequence for the authenticator to return back in its response. Defaults to 64 random bytes.
        (optional) `timeout`: How long in milliseconds the browser should give the user to choose an authenticator. This value is a *hint* and may be ignored by the browser.
        (optional) `allow_credentials`: A list of credentials registered to the user.
        (optional) `user_verification`: The RP's preference for the authenticator's enforcement of the "user verified" flag.

    Returns:
        Authentication options ready for the browser. Consider using `helpers.options_to_json()` in this library to quickly convert the options to JSON.
    """

    if not rp_id:
        raise ValueError("rp_id cannot be an empty string")

    ########
    # Set defaults for required values
    ########

    if not challenge:
        challenge = generate_challenge()

    if not allow_credentials:
        allow_credentials = []

    return PublicKeyCredentialRequestOptions(
        rp_id=rp_id,
        challenge=challenge,
        timeout=timeout,
        allow_credentials=allow_credentials,
        user_verification=user_verification,
    )
