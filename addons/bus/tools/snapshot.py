import base64
import math


def encode_snapshot(snapshot_str: str) -> str:
    """Encodes a raw PostgreSQL snapshot string of the form "xmin:xmax:xip1,xip2,..."
    into a compact "xmin:xmax:bitmap" string where the xip list is replaced by a
    base64-encoded bitmap (one bit per transaction ID in [xmin, xmax)).
    """
    xmin_str, xmax_str, xips_str = snapshot_str.split(":")
    xmin = int(xmin_str)
    xmax = int(xmax_str)
    xips = [int(x) for x in xips_str.split(",") if x]
    bitmap = bytearray(math.ceil((xmax - xmin) / 8))
    for x in xips:
        offset = x - xmin
        bitmap[offset // 8] |= 1 << (offset % 8)
    return f"{xmin_str}:{xmax_str}:{base64.b64encode(bitmap).decode()}"


def decode_snapshot(encoded: str):
    """Decodes a snapshot produced by encode_snapshot back to (xmin, xmax, xips)."""
    xmin_str, xmax_str, b64_bitmap = encoded.split(":")
    xmin = int(xmin_str)
    xmax = int(xmax_str)
    bitmap = base64.b64decode(b64_bitmap)
    xips = []
    for i in range(xmax - xmin):
        if bitmap[i // 8] & (1 << (i % 8)):
            xips.append(xmin + i)
    return xmin, xmax, xips
