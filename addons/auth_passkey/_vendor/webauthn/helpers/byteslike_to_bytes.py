from typing import Union


def byteslike_to_bytes(val: Union[bytes, memoryview]) -> bytes:
    """
    Massage bytes subclasses into bytes for ease of concatenation, comparison, etc...
    """
    if isinstance(val, memoryview):
        val = val.tobytes()

    return bytes(val)
