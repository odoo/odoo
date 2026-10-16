# -*- coding: utf-8 -*-

import re


# BR-FR-05 subject codes are three uppercase letters (#REG#, #ABL#, #PMT#, ...).
_CODED_NOTE_RE = re.compile(r'#([A-Z]{3})#')


def coded_note_codes(text):
    if not text:
        return []
    return _CODED_NOTE_RE.findall(str(text))
