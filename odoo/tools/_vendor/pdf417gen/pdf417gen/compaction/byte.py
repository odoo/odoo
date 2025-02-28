"""
Byte Compaction Mode (BC)

Can encode: ASCII 0 to 255
Rate compaction: 1.2 byte per code word
"""

from itertools import chain
from pdf417gen.util import switch_base, chunks


def compact_bytes(data):
    """Encodes data into code words using the Byte compaction mode."""
    compacted_chunks = (_compact_chunk(chunk) for chunk in chunks(data, size=6))
    return chain(*compacted_chunks)


def _compact_chunk(chunk):
    """
    Chunks of exactly 6 bytes are encoded into 5 codewords by using a base 256
    to base 900 transformation. Smaller chunks are left unchanged.
    """
    digits = [i for i in chunk]

    if len(chunk) == 6:
        base900 = switch_base(digits, 256, 900)
        return [0] * (5 - len(base900)) + base900


    return digits
