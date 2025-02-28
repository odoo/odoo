from collections import namedtuple
from itertools import chain, groupby

from pdf417gen.compaction import optimizations
from pdf417gen.compaction.byte import compact_bytes
from pdf417gen.compaction.numeric import compact_numbers
from pdf417gen.compaction.text import compact_text
from pdf417gen.data import CHARACTERS_LOOKUP


# Codes for switching between compacting modes
TEXT_LATCH = 900
BYTE_LATCH = 901
BYTE_LATCH_ALT = 924
BYTE_SWITCH = 913
NUMERIC_LATCH = 902


# A chunk of barcode data with accompanying compaction function
Chunk = namedtuple("Chunk", ["data", "compact_fn"])


def compact(data):
    """Encodes given data into an array of PDF417 code words."""
    chunks = _split_to_chunks(data)
    chunks = optimizations.replace_short_numeric_chunks(chunks)
    chunks = optimizations.merge_chunks_with_same_compact_fn(chunks)
    return _compact_chunks(chunks)


def _compact_chunks(chunks):
    compacted_chunks = (
        _compact_chunk(ordinal, chunk) for ordinal, chunk in enumerate(chunks))

    return chain(*compacted_chunks)


def _compact_chunk(ordinal, chunk):
    code_words = []

    # Add the switch code if required
    add_switch_code = ordinal > 0 or chunk.compact_fn != compact_text
    if add_switch_code:
        code_words.append(get_switch_code(chunk))

    code_words.extend(chunk.compact_fn(chunk.data))

    return code_words


def _split_to_chunks(data):
    """
    Splits a string into chunks which can be compacted with the same compacting
    function.
    """
    for fn, chunk in groupby(data, key=get_optimal_compactor_fn):
        yield Chunk(list(chunk), fn)


def get_optimal_compactor_fn(char):
    if 48 <= char <= 57:
        return compact_numbers

    if char in CHARACTERS_LOOKUP:
        return compact_text

    return compact_bytes


def get_switch_code(chunk):
    if chunk.compact_fn == compact_text:
        return TEXT_LATCH

    if chunk.compact_fn == compact_bytes:
        return BYTE_LATCH_ALT if len(chunk.data) % 6 == 0 else BYTE_LATCH

    if chunk.compact_fn == compact_numbers:
        return NUMERIC_LATCH

    assert False, "Nonexistant compaction function"
