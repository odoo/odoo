from itertools import chain, groupby
from pdf417gen.compaction.numeric import compact_numbers
from pdf417gen.compaction.text import compact_text
from pdf417gen.util import iterate_prev_next


def replace_short_numeric_chunks(chunks):
    """
    The Numeric Compaction mode can pack almost 3 digits (2.93) into a symbol
    character. Though Numeric Compaction mode can be invoked at any digit
    length, it is recommended to use Numeric Compaction mode when there are
    more than 13 consecutive digits. Otherwise, use Text Compaction mode.
    """
    from pdf417gen.compaction import Chunk

    for prev, chunk, next in iterate_prev_next(chunks):
        is_short_numeric_chunk = (
            chunk.compact_fn == compact_numbers
            and len(chunk.data) < 13
        )

        borders_text_chunk = (
            (prev and prev.compact_fn == compact_text) or
            (next and next.compact_fn == compact_text)
        )

        if is_short_numeric_chunk and borders_text_chunk:
            yield Chunk(chunk.data, compact_text)
        else:
            yield chunk


def merge_chunks_with_same_compact_fn(chunks):
    from pdf417gen.compaction import Chunk

    for compact_fn, group in groupby(chunks, key=lambda x: x[1]):
        data = chain.from_iterable(chunk.data for chunk in group)
        yield Chunk(list(data), compact_fn)
