"""
Name and identifier validation for the ORM.

Provides validation functions used across the ORM for model names,
PostgreSQL identifiers, and method names. Absorbs the regex patterns
that were previously in core/constants.py.
"""

import re

from odoo.exceptions import AccessError, ValidationError

# =============================================================================
# Validation Patterns
# =============================================================================

regex_alphanumeric = re.compile(r"^[a-z0-9_]+$")
regex_object_name = re.compile(r"^[a-z0-9_.]+$")
regex_pg_name = re.compile(r"^[a-z_][a-z0-9_$]*$", re.IGNORECASE)

# Match private methods, to prevent their remote invocation
regex_private = re.compile(r"^(_.*|init)$")


# =============================================================================
# Validation Functions
# =============================================================================


def check_object_name(name: str) -> bool:
    """Check if the given name is a valid model name.

    Model names must be lowercase alphanumeric with underscores and dots
    (e.g. ``res.partner``, ``account.move``).  Uppercase is disallowed
    because PostgreSQL folds unquoted identifiers to lowercase, and Odoo
    does not consistently quote table/column names.

    Returns ``True`` if *name* is valid, ``False`` otherwise.
    Prefer :func:`raise_on_invalid_object_name` for validation with exceptions.
    """
    return regex_object_name.match(name) is not None


def check_pg_name(name: str) -> None:
    """Check whether the given name is a valid PostgreSQL identifier name.

    Raises:
        ValidationError: If name contains invalid characters or exceeds 63 chars.
    """
    if not regex_pg_name.match(name):
        raise ValidationError(f"Invalid characters in table name {name!r}")
    if len(name) > 63:
        raise ValidationError(f"Table name {name!r} is too long")


def check_method_name(name: str) -> None:
    """Check whether the given method name is safe for remote invocation.

    Private methods (prefixed with ``_``) and ``init`` cannot be called
    via RPC.  This centralises the regex that was previously inlined in
    ``odoo.service.model``.

    Raises:
        AccessError: If the method name matches the private-method pattern.
    """
    if regex_private.match(name):
        raise AccessError(
            f"Private methods (such as {name!r}) cannot be called remotely."
        )


def raise_on_invalid_object_name(name: str) -> None:
    """Raise ValueError if the given model name is not valid.

    Raises:
        ValueError: If the name doesn't match the valid model name pattern.
    """
    if not check_object_name(name):
        msg = f"The _name attribute {name!r} is not valid."
        raise ValueError(msg)
