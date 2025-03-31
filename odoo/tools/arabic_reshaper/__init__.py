# The following code was copied from the original author's repository
# at https://github.com/mpcabd/python-arabic-reshaper/tree/v3.0.0/arabic_reshaper
# Version: 3.0.0
# This work is licensed under the MIT License.
# To view a copy of this license, visit https://opensource.org/licenses/MIT
# Written by Abdullah Diab (mpcabd)
# Email: mpcabd@gmail.com
# Website: http://mpcabd.xyz
#
# This code was simplified by removing configuration (keeping only the default
# configuration) then constant-folding all the configuration items by hand.

import re

from itertools import repeat

from .letters import (UNSHAPED, ISOLATED, TATWEEL, ZWJ, LETTERS_ARABIC, FINAL,
                      INITIAL, MEDIAL, connects_with_letters_before_and_after,
                      connects_with_letter_before, connects_with_letter_after)

__all__ = ['reshape']

HARAKAT_RE = re.compile(
    '['
    '\u0610-\u061a'
    '\u064b-\u065f'
    '\u0670'
    '\u06d6-\u06dc'
    '\u06df-\u06e8'
    '\u06ea-\u06ed'
    '\u08d4-\u08e1'
    '\u08d4-\u08ed'
    '\u08e3-\u08ff'
    ']',

    re.UNICODE | re.VERBOSE
)


LIGATURES_RE = re.compile("""
    \u0627\u0644\u0644\u0647 # ARABIC LIGATURE ALLAH
  | \u0644\u0627 # ARABIC LIGATURE LAM WITH ALEF
  | \u0644\u0623 # ARABIC LIGATURE LAM WITH ALEF WITH HAMZA ABOVE
  | \u0644\u0625 # ARABIC LIGATURE LAM WITH ALEF WITH HAMZA BELOW
  | \u0644\u0622 # ARABIC LIGATURE LAM WITH ALEF WITH MADDA ABOVE
""", re.UNICODE | re.VERBOSE)

GROUP_INDEX_TO_LIGATURE_FORMs = [
    ('\N{ARABIC LIGATURE ALLAH ISOLATED FORM}', '', '', ''),
    ('\N{ARABIC LIGATURE LAM WITH ALEF ISOLATED FORM}', '', '', '\N{ARABIC LIGATURE LAM WITH ALEF FINAL FORM}'),
    ('\N{ARABIC LIGATURE LAM WITH ALEF WITH HAMZA ABOVE ISOLATED FORM}', '', '', '\N{ARABIC LIGATURE LAM WITH ALEF WITH HAMZA ABOVE FINAL FORM}'),
    ('\N{ARABIC LIGATURE LAM WITH ALEF WITH HAMZA BELOW ISOLATED FORM}', '', '', '\N{ARABIC LIGATURE LAM WITH ALEF WITH HAMZA BELOW FINAL FORM}'),
    ('\N{ARABIC LIGATURE LAM WITH ALEF WITH MADDA ABOVE ISOLATED FORM}', '', '', '\N{ARABIC LIGATURE LAM WITH ALEF WITH MADDA ABOVE FINAL FORM}'),
]


def reshape(text):
    if not text:
        return ''

    output = []

    LETTER = 0
    FORM = 1
    NOT_SUPPORTED = -1

    for letter in text:
        if HARAKAT_RE.match(letter):
            pass
        elif letter not in LETTERS_ARABIC:
            output.append((letter, NOT_SUPPORTED))
        elif not output:  # first letter
            output.append((letter, ISOLATED))
        else:
            previous_letter = output[-1]
            if (
                previous_letter[FORM] == NOT_SUPPORTED or
                not connects_with_letter_before(letter, LETTERS_ARABIC) or
                not connects_with_letter_after(previous_letter[LETTER], LETTERS_ARABIC) or
                (previous_letter[FORM] == FINAL and not connects_with_letters_before_and_after(previous_letter[LETTER], LETTERS_ARABIC))
            ):
                output.append((letter, ISOLATED))
            elif previous_letter[FORM] == ISOLATED:
                output[-1] = (previous_letter[LETTER], INITIAL)
                output.append((letter, FINAL))
            # Otherwise, we will change the previous letter to connect
            # to the current letter
            else:
                output[-1] = (previous_letter[LETTER], MEDIAL)
                output.append((letter, FINAL))

        # Remove ZWJ if it's the second to last item as it won't be useful
        if len(output) > 1 and output[-2][LETTER] == ZWJ:
            output.pop(len(output) - 2)

    if output and output[-1][LETTER] == ZWJ:
        output.pop()

    # Clean text from Harakat to be able to find ligatures
    text = HARAKAT_RE.sub('', text)

    for match in LIGATURES_RE.finditer(text):
        group_index = next((
            i for i, group in enumerate(match.groups()) if group
        ), -1)
        forms = GROUP_INDEX_TO_LIGATURE_FORMs[group_index]
        a, b = match.span()
        a_form = output[a][FORM]
        b_form = output[b - 1][FORM]

        # +-----------+----------+---------+---------+----------+
        # | a   \   b | ISOLATED | INITIAL | MEDIAL  | FINAL    |
        # +-----------+----------+---------+---------+----------+
        # | ISOLATED  | ISOLATED | INITIAL | INITIAL | ISOLATED |
        # | INITIAL   | ISOLATED | INITIAL | INITIAL | ISOLATED |
        # | MEDIAL    | FINAL    | MEDIAL  | MEDIAL  | FINAL    |
        # | FINAL     | FINAL    | MEDIAL  | MEDIAL  | FINAL    |
        # +-----------+----------+---------+---------+----------+

        if a_form in (ISOLATED, INITIAL):
            if b_form in (ISOLATED, FINAL):
                ligature_form = ISOLATED
            else:
                ligature_form = INITIAL
        else:
            if b_form in (ISOLATED, FINAL):
                ligature_form = FINAL
            else:
                ligature_form = MEDIAL
        if not forms[ligature_form]:
            continue
        output[a] = (forms[ligature_form], NOT_SUPPORTED)
        output[a + 1:b] = repeat(('', NOT_SUPPORTED), b - 1 - a)

    result = []
    for o in output:
        if o[LETTER]:
            if o[FORM] == NOT_SUPPORTED or o[FORM] == UNSHAPED:
                result.append(o[LETTER])
            else:
                result.append(LETTERS_ARABIC[o[LETTER]][o[FORM]])

    return ''.join(result)
