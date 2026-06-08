import codecs


def aaguid_to_string(val: bytes) -> str:
    """
    Take aaguid bytes and convert them to a GUID string
    """
    if len(val) != 16:
        raise ValueError(f"AAGUID was {len(val)} bytes, expected 16 bytes")

    # Convert to a hexadecimal string representation
    to_hex = codecs.encode(val, encoding="hex").decode("utf-8")

    # Split up the hex string into segments
    # 8 chars
    seg_1 = to_hex[0:8]
    # 4 chars
    seg_2 = to_hex[8:12]
    # 4 chars
    seg_3 = to_hex[12:16]
    # 4 chars
    seg_4 = to_hex[16:20]
    # 12 chars
    seg_5 = to_hex[20:32]

    # "00000000-0000-0000-0000-000000000000"
    return f"{seg_1}-{seg_2}-{seg_3}-{seg_4}-{seg_5}"
