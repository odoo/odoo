from builtins import range

from .data import ERROR_CORRECTION_FACTORS


def compute_error_correction_code_words(data_words, level):
    assert 0 <= level <= 8

    # Correction factors for the given level
    factors = ERROR_CORRECTION_FACTORS[level]

    # Number of EC words
    count = 2 ** (level + 1)

    # Correction code words list, prepopulated with zeros
    ec_words = [0] * count

    # Do the math
    for data_word in data_words:
        temp = (data_word + ec_words[-1]) % 929

        for x in range(count - 1, -1, -1):
            word = ec_words[x - 1] if x > 0 else 0
            ec_words[x] = (word + 929 - (temp * factors[x]) % 929) % 929

    return [929 - x if x > 0 else x for x in reversed(ec_words)]
