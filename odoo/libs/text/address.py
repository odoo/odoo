"""Address parsing utilities.

Pure Python text helpers with no Odoo dependencies.
"""

__all__ = ["ADDRESS_REGEX", "street_split"]

import re

# Regex pattern for splitting street addresses into components
# Matches: street_name [street_number] [- street_number2]
ADDRESS_REGEX = re.compile(r"^(.*?)(\s[0-9][0-9\S]*)?(?: - (.+))?$", flags=re.DOTALL)


def street_split(street: str | None) -> dict[str, str]:
    """Split a street address into its component parts.

    Parses an address string into street name, number, and optional secondary number.

    :param street: Full street address string (e.g., "Main Street 123 - Apt B")
    :returns: Dictionary with keys 'street_name', 'street_number', 'street_number2'

    Example::

        >>> street_split("Main Street 123 - Apt B")
        {'street_name': 'Main Street', 'street_number': '123', 'street_number2': 'Apt B'}
        >>> street_split("Oak Avenue")
        {'street_name': 'Oak Avenue', 'street_number': '', 'street_number2': ''}
    """
    match = ADDRESS_REGEX.match(street or "")
    results = match.groups("") if match else ("", "", "")
    return {
        "street_name": results[0].strip(),
        "street_number": results[1].strip(),
        "street_number2": results[2],
    }
