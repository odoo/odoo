"""
Text Compaction Mode (TC)

Can encode: ASCII 9, 10, 13 and 32-126
Rate compaction: 2 bytes per code word
"""

from pdf417gen.data import CHARACTERS_LOOKUP, SWITCH_CODES, Submode
from pdf417gen.util import chunks


def _exists_in_submode(char, submode):
    return char in CHARACTERS_LOOKUP and submode in CHARACTERS_LOOKUP[char]


def _get_submode(char):
    if char not in CHARACTERS_LOOKUP:
        raise ValueError("Cannot encode char: {}".format(char))

    submodes = CHARACTERS_LOOKUP[char].keys()

    preference = [Submode.LOWER, Submode.UPPER, Submode.MIXED, Submode.PUNCT]

    for submode in preference:
        if submode in submodes:
            return submode

    raise ValueError("Cannot encode char: {}".format(char))


def compact_text_interim(data):
    """Encodes text data to interim code words."""

    def _interim_text_generator(chars):
        # By default, encoding starts in uppercase submode
        submode = Submode.UPPER

        for char in chars:
            # Switch submode if needed
            if not _exists_in_submode(char, submode):
                prev_submode = submode
                submode = _get_submode(char)
                for code in SWITCH_CODES[prev_submode][submode]:
                    yield code

            yield CHARACTERS_LOOKUP[char][submode]

    return _interim_text_generator(data)


# Since each code word consists of 2 characters, a padding value is
# needed when encoding a single character. 29 is used as padding because
# it's a switch in all 4 submodes, and doesn't add any data.
PADDING_INTERIM_CODE = 29


def _compact_chunk(chunk):
    if len(chunk) == 1:
        chunk = (chunk[0], PADDING_INTERIM_CODE)

    return 30 * chunk[0] + chunk[1]


def compact_text(data):
    """Encodes data into code words using the Text compaction mode."""
    interim_codes = compact_text_interim(data)
    return (_compact_chunk(chunk) for chunk in chunks(interim_codes, 2))
