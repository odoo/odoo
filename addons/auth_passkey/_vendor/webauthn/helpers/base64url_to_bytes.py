from base64 import urlsafe_b64decode


def base64url_to_bytes(val: str) -> bytes:
    """
    Convert a Base64URL-encoded string to bytes.
    """
    # Padding is optional in Base64URL. Unfortunately, Python's decoder requires the
    # padding. Given the fact that urlsafe_b64decode will ignore too _much_ padding,
    # we can tack on a constant amount of padding to ensure encoded values can always be
    # decoded.
    return urlsafe_b64decode(f"{val}===")
