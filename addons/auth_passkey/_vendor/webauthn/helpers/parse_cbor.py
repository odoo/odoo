from typing import Any

import cbor2

from .exceptions import InvalidCBORData


def parse_cbor(data: bytes) -> Any:
    """
    Attempt to decode CBOR-encoded data.

    Raises:
        `helpers.exceptions.InvalidCBORData` if data cannot be decoded
    """
    try:
        to_return = cbor2.loads(data)
    except Exception as exc:
        raise InvalidCBORData("Could not decode CBOR data") from exc

    return to_return
