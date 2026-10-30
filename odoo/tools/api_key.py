import secrets

__all__ = [
    'is_api_key',
    'is_readonly_api_key',
    'is_readwrite_api_key',
    'new_api_key',
]


TOKEN_LENGTH = 20  # in bytes
SUFFIX = '_oak'  # Odoo Api Key, cute
READONLY_PREFIX = 'ro_'


def new_api_key(*, readonly: bool) -> str:
    """ Generate a new random API key. """
    key = secrets.token_hex(TOKEN_LENGTH) + SUFFIX
    if readonly:
        key = READONLY_PREFIX + key
    return key


def is_api_key(key: str) -> bool:
    """ Determine if the given string is an Odoo API key. """
    # Keys generated before commit baa1add2dd (20.1) have neither the
    # prefix nor the suffix: strip them for comparison.
    token_hex = key.removeprefix(READONLY_PREFIX).removesuffix(SUFFIX)
    return (
        len(token_hex) == TOKEN_LENGTH * 2
        and all(hexdigit in "0123456789abcdef" for hexdigit in token_hex)
    )


def is_readonly_api_key(key: str) -> bool:
    """ Determine if the given string is a read-only Odoo API key. """
    return is_api_key(key) and key.startswith(READONLY_PREFIX)


def is_readwrite_api_key(key: str) -> bool:
    """ Determine if the given string is a read/write Odoo API key. """
    return is_api_key(key) and not key.startswith(READONLY_PREFIX)
