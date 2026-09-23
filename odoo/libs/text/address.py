__all__ = ["street_split"]

import re

_ADDRESS_REGEX = re.compile(r"^(.*?)(\s[0-9][0-9\S]*)?(?: - (.+))?$", flags=re.DOTALL)


def street_split(street: str | None) -> dict[str, str]:
    match = _ADDRESS_REGEX.match(street or "")
    results = match.groups("") if match else ("", "", "")
    return {
        "street_name": results[0].strip(),
        "street_number": results[1].strip(),
        "street_number2": results[2].strip(),
    }
