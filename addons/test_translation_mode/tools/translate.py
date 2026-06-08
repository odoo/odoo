from __future__ import annotations

import json
import re

import odoo.tools.translate as translate


"""
Parameters used to encode and decode contextualized translations (short: 'CT').

Translation metadata:

Each translation is preceded by its context, or "metadata", which is a 'list' containing:
- :int: whether the term is translated (0 or 1);
- :string: the (encoded) addon from which the translation originates;
- :string: the (encoded) source term
- :string: (optional the (encoded) translation, attached only if:
    > it exists for the given source (if not, source == translation)
    > the translated term differs from its source

Encoding:

This metadata is "encoded" and attached to each translated string. It is encoded
using the following system:
1. the metadata (list) is stringified;
2. stringified metadata is converted to bytes array;
3. each byte is then converted to a tuple of its base-16 integer components;
4. each integer is then swapped with its corresponding zero-width character.

Hiding:

The metadata is encoded in zero-width characters to allow 2 things:
- being properly picked up by the client code with an arrangement of non-conventional characters;
- being invisible in the UI, should the service not work or fail to pick up a translation.

Decoding happens on the client side; see: <addons/test_translation_mode/static/src/translation.patch.js>
"""
CT_MAP = tuple('\u200B\u200C\u200D\u200E\u200F\u2060\u2061\u2062\u2063\u2064\uFE00\uFE01\uFE02\uFE03\uFE04\uFE05')
RE_CONTEXTUALIZED_TRANSLATION = re.compile(
    f"[{CT_MAP[0]}{CT_MAP[1]}][{''.join(CT_MAP)}]+"
)


original_CSVFileReader__iter__ = translate.CSVFileReader.__iter__
original_PoFileReader__iter__ = translate.PoFileReader.__iter__
original_XMLDataFileReader__iter__ = translate.XMLDataFileReader.__iter__


def contextualize_entry(entry: str):
    translation = entry.get('value', "")
    if translation and RE_CONTEXTUALIZED_TRANSLATION.match(translation):
        return entry

    source = entry.get('src', "")
    final_translation = translation or source
    metadata = [entry.get('module', "base"), source]
    if source != final_translation:
        metadata.append(translation)

    # Encoding
    str_metadata = json.dumps(metadata)
    bytes_metadata = str_metadata.encode('utf-8')
    byte_count = encode_word(len(bytes_metadata))  # supports lengths up to 2^16
    encoded_metadata = ''.join(encode_byte(byte) for byte in bytes_metadata)
    is_translated_bit = CT_MAP[1 if translation else 0]

    entry['value'] = is_translated_bit + byte_count + encoded_metadata + final_translation
    return entry


def encode_byte(byte: int):
    return CT_MAP[(byte >> 4) & 0xF] + CT_MAP[byte & 0xF]


def encode_word(word: int):
    return CT_MAP[(word >> 12) & 0xF] + CT_MAP[(word >> 8) & 0xF] + CT_MAP[(word >> 4) & 0xF] + CT_MAP[word & 0xF]


def CSVFileReader__iter__(self):
    for entry in original_CSVFileReader__iter__(self):
        yield contextualize_entry(entry)


def PoFileReader__iter__(self):
    for entry in original_PoFileReader__iter__(self):
        yield contextualize_entry(entry)


def XMLDataFileReader__iter__(self):
    for entry in original_XMLDataFileReader__iter__(self):
        yield contextualize_entry(entry)


translate.CSVFileReader.__iter__ = CSVFileReader__iter__
translate.PoFileReader.__iter__ = PoFileReader__iter__
translate.XMLDataFileReader.__iter__ = XMLDataFileReader__iter__

# Reset cached translations
translate.code_translations.python_translations.clear()
translate.code_translations.web_translations.clear()
