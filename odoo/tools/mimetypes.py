# -*- coding: utf-8 -*-
"""
Mimetypes-related utilities

# TODO: re-export stdlib mimetypes?
"""

import collections
import functools
import io
import logging
import mimetypes
import re
import zipfile

__all__ = ['guess_mimetype']

_logger = logging.getLogger(__name__)

# We define our own guess_mimetype implementation and if magic is available we
# use it instead.

# Discriminants for zip-based file formats
_ooxml_dirs = {
    'word/': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'ppt/': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'xl/': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

def _check_ooxml(data):
    with io.BytesIO(data) as f, zipfile.ZipFile(f) as z:
        filenames = z.namelist()
        # OOXML documents should have a [Content_Types].xml file for early
        # check that we're interested in this thing at all
        if '[Content_Types].xml' not in filenames:
            return False

        # There is a directory whose name denotes the type of the file:
        # word, ppt (powerpoint) or xl (excel)
        for dirname, mime in _ooxml_dirs.items():
            if any(entry.startswith(dirname) for entry in filenames):
                return mime

        return False


# Checks that a string looks like a mimetype
_mime_validator = re.compile(r"""
    [\w-]+ # type-name
    / # subtype separator
    [\w-]+ # registration facet or subtype
    (?:\.[\w-]+)* # optional faceted name
    (?:\+[\w-]+)? # optional structured syntax specifier
""", re.VERBOSE)

def _check_open_container_format(data):
    with io.BytesIO(data) as f, zipfile.ZipFile(f) as z:
        # OpenDocument package should contain a file named "mimetype"
        if 'mimetype' not in z.namelist():
            return False

        # The content of this file should be the ASCII encoded MIME media type
        marcel = z.read('mimetype').decode('ascii')
        # Check that it looks like a valid mime type
        if len(marcel) < 256 and _mime_validator.match(marcel):
            return marcel

        return False

_xls_pattern = re.compile(b"""
    \x09\x08\x10\x00\x00\x06\x05\x00
  | \xFD\xFF\xFF\xFF(\x10|\x1F|\x20|"|#|\(|\))
""", re.VERBOSE)

_ppt_pattern = re.compile(b"""
    \x00\x6E\x1E\xF0
  | \x0F\x00\xE8\x03
  | \xA0\x46\x1D\xF0
  | \xFD\xFF\xFF\xFF(\x0E|\x1C|\x43)\x00\x00\x00
""", re.VERBOSE)

def _check_olecf(data):
    """ Pre-OOXML Office formats are OLE Compound Files with the same
    file signature ("magic bytes") and a subheader at offset 512 (0x200).
    """
    offset = 0x200
    if data.startswith(b'\xEC\xA5\xC1\x00', offset):
        return 'application/msword'
    elif b'Microsoft Excel' in data:
        return 'application/vnd.ms-excel'
    elif _ppt_pattern.match(data, offset):
        return 'application/vnd.ms-powerpoint'
    return False


def _check_svg(data):
    """Checks the existence of the opening and closing SVG tags"""
    if b'<svg' in data and b'</svg>' in data:
        return 'image/svg+xml'
    return False

def _check_webp(data):
    """Checks the presence of the WEBP and VP8 in the RIFF"""
    if data[8:15] == b'WEBPVP8':
        return 'image/webp'
    return False

# For "master" formats with many subformats, discriminants is a list of
# functions, tried in order. The first non-falsy value returned is the
# selected mime type. If all functions return falsy values, the master
# mimetype is returned.
_Entry = collections.namedtuple('_Entry', ['mimetype', 'signatures', 'discriminants'])

_mime_mappings = (
    _Entry('application/pdf', [b'%PDF'], []),
    _Entry('image/jpeg', [b'\xFF\xD8\xFF\xE0', b'\xFF\xD8\xFF\xE2', b'\xFF\xD8\xFF\xE3', b'\xFF\xD8\xFF\xE1', b'\xFF\xD8\xFF\xDB'], []),
    _Entry('image/png', [b'\x89PNG\r\n\x1A\n'], []),
    _Entry('image/gif', [b'GIF87a', b'GIF89a'], []),
    _Entry('image/bmp', [b'BM'], []),
    _Entry('application/xml', [b'<'], [_check_svg]),
    _Entry('image/x-icon', [b'\x00\x00\x01\x00'], []),
    _Entry('image/webp', [b'RIFF'], [_check_webp]),
    _Entry('application/msword', [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1', b'\x0D\x44\x4F\x43'], [_check_olecf]),
    _Entry('application/zip', [b'PK\x03\x04'], [_check_ooxml, _check_open_container_format]),
)

def _odoo_guess_mimetype(bin_data, default='application/octet-stream'):
    """ Attempts to guess the mime type of the provided binary data.

    :param bytes bin_data: binary data to try and guess a mime type for
    :returns: matched mimetype or ``application/octet-stream`` if none matched
    """
    for entry in _mime_mappings:
        for signature in entry.signatures:
            if bin_data.startswith(signature):
                for discriminant in entry.discriminants:
                    try:
                        guess = discriminant(bin_data)
                        if guess:
                            return guess
                    except Exception:
                        _logger.getChild('guess_mimetype').warn(
                            "Sub-checker '%s' of type '%s' failed",
                            discriminant.__name__, entry.mimetype,
                            exc_info=True
                        )
                return entry.mimetype
    return default

try:
    import magic
except ImportError:
    magic = None

if magic:
    # There are 2 python libs named 'magic' with incompatible APIs.
    if hasattr(magic, 'from_buffer'):
        _guesser = functools.partial(magic.from_buffer, mime=True)
    elif hasattr(magic, 'open'):
        ms = magic.open(magic.MAGIC_MIME_TYPE)
        ms.load()
        _guesser = ms.buffer

    def guess_mimetype(bin_data, default=None):
        mimetype = _guesser(bin_data[:1024])
        if mimetype == 'image/svg':
            return 'image/svg+xml'
        return mimetype
else:
    guess_mimetype = _odoo_guess_mimetype

def neuter_mimetype(mimetype, user):
    if 'ht' in mimetype or 'xml' in mimetype or 'svg' in mimetype:
        if not user._is_system():
            return 'text/plain'
    return mimetype

def get_extension(filename):
    stem, dot, ext = filename.lstrip('.').rpartition('.')
    if not dot or not ext.isalnum():
        return ''

    if len(ext) <= 4:
        return f'.{ext}'.lower()

    guessed_mimetype, guessed_ext = mimetypes.guess_type(filename)
    if guessed_ext:
        return guessed_ext
    if guessed_mimetype:
        return f'.{ext}'.lower()

    return ''
