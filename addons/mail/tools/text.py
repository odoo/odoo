# Part of Odoo. See LICENSE file for full copyright and licensing details.

from difflib import SequenceMatcher


def text_diff_summary(text1, text2, kept_chars=25):
    """ Returns the differences between two text, keeping some context
    characters around the differences.

    :param str text1: first text to compare
    :param str text2: second text to compare
    :param int kept_chars: number of characters to include in result on each
        side of each difference

    :return: tuple (first text difference summary, second text difference summary)
    """
    if text1 == text2:
        return '...', '...'
    matcher = SequenceMatcher(None, text1, text2)
    result1, result2 = [], []
    first = True
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            chunk = text1[i1:i2]
            if first:
                if len(chunk) > kept_chars:
                    chunk = f'...{chunk[-kept_chars:]}'
            elif i2 == len(text1) and j2 == len(text2):  # end
                if len(chunk) > kept_chars:
                    chunk = f'{chunk[:kept_chars]}...'
            elif len(chunk) > kept_chars * 2:
                chunk = f'{chunk[:kept_chars]}...{chunk[-kept_chars:]}'
            result1.append(chunk)
            result2.append(chunk)
        elif tag == 'replace':
            result1.append(text1[i1:i2])
            result2.append(text2[j1:j2])
        elif tag == 'delete':
            result1.append(text1[i1:i2])
        elif tag == 'insert':
            result2.append(text2[j1:j2])
        first = False
    diff1, diff2 = ''.join(result1), ''.join(result2)
    return diff1, diff2
