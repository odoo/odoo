# -*- coding: utf-8 -*-
"""
Mimetypes-related utilities

# TODO: reexport stdlib mimetypes?
"""
import collections
import io
import logging
import re
import zipfile

__all__ = ['guess_mimetype']

_logger = logging.getLogger(__name__)

# We define our own guess_mimetype implementation and if magic is available we
# use it instead.

# discriminants for zip-based file formats
_ooxml_dirs = {
    'word/': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pt/': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'xl/': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
def _check_ooxml(data):
    with io.BytesIO(data) as f, zipfile.ZipFile(f) as z:
        filenames = z.namelist()
        # OOXML documents should have a [Content_Types].xml file for early
        # check that we're interested in this thing at all
        if '[Content_Types].xml' not in filenames:
            return False

        # then there is a directory whose name denotes the type of the file:
        # word, pt (powerpoint) or xl (excel)
        for dirname, mime in _ooxml_dirs.items():
            if any(entry.startswith(dirname) for entry in filenames):
                return mime

        return False


# checks that a string looks kinda sorta like a mimetype
_mime_validator = re.compile(r"""
    [\w-]+ # type-name
    / # subtype separator
    [\w-]+ # registration facet or subtype
    (?:\.[\w-]+)* # optional faceted name
    (?:\+[\w-]+)? # optional structured syntax specifier
""", re.VERBOSE)
def _check_open_container_format(data):
    # Open Document Format for Office Applications (OpenDocument) Version 1.2
    #
    # Part 3: Packages
    # 3 Packages
    # 3.3 MIME Media Type
    with io.BytesIO(data) as f, zipfile.ZipFile(f) as z:
        # If a MIME media type for a document exists, then an OpenDocument
        # package should contain a file with name "mimetype".
        if 'mimetype' not in z.namelist():
            return False

        # The content of this file shall be the ASCII encoded MIME media type
        # associated with the document.
        marcel = z.read('mimetype').decode('ascii')
        # check that it's not too long (RFC6838 § 4.2 restricts type and
        # subtype to 127 characters each + separator, strongly recommends
        # limiting them to 64 but does not require it) and that it looks a lot
        # like a valid mime type
        if len(marcel) < 256 and _mime_validator.match(marcel):
            return marcel

        return False

_xls_pattern = re.compile(b"""
    \x09\x08\x10\x00\x00\x06\x05\x00
  | \xFD\xFF\xFF\xFF(\x10|\x1F|\x20|"|\\#|\\(|\\))
""", re.VERBOSE)
_ppt_pattern = re.compile(b"""
    \x00\x6E\x1E\xF0
  | \x0F\x00\xE8\x03
  | \xA0\x46\x1D\xF0
  | \xFD\xFF\xFF\xFF(\x0E|\x1C|\x43)\x00\x00\x00
""", re.VERBOSE)
def _check_olecf(data):
    """ Pre-OOXML Office formats are OLE Compound Files which all use the same
    file signature ("magic bytes") and should have a subheader at offset 512
    (0x200).

    Subheaders taken from http://www.garykessler.net/library/file_sigs.html
    according to which Mac office files *may* have different subheaders. We'll
    ignore that.
    """
    offset = 0x200
    if data.startswith(b'\xEC\xA5\xC1\x00', offset):
        return 'application/msword'
    # the _xls_pattern stuff doesn't seem to work correctly (the test file
    # only has a bunch of \xf* at offset 0x200), that apparently works
    elif b'Microsoft Excel' in data:
        return 'application/vnd.ms-excel'
    elif _ppt_pattern.match(data, offset):
        return 'application/vnd.ms-powerpoint'
    return False

# for "master" formats with many subformats, discriminants is a list of
# functions, tried in order and the first non-falsy value returned is the
# selected mime type. If all functions return falsy values, the master
# mimetype is returned.
_Entry = collections.namedtuple('_Entry', ['mimetype', 'signatures', 'discriminants'])
_mime_mappings = (
    # pdf
    _Entry('application/pdf', [b'%PDF'], []),
    # jpg, jpeg, png, gif, bmp
    _Entry('image/jpeg', [b'\xFF\xD8\xFF\xE0', b'\xFF\xD8\xFF\xE2', b'\xFF\xD8\xFF\xE3', b'\xFF\xD8\xFF\xE1'], []),
    _Entry('image/png', [b'\x89PNG\r\n\x1A\n'], []),
    _Entry('image/gif', [b'GIF87a', b'GIF89a'], []),
    _Entry('image/bmp', [b'BM'], []),
    # OLECF files in general (Word, Excel, PPT, default to word because why not?)
    _Entry('application/msword', [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1', b'\x0D\x44\x4F\x43'], [
        _check_olecf
    ]),
    # zip, but will include jar, odt, ods, odp, docx, xlsx, pptx, apk
    _Entry('application/zip', [b'PK\x03\x04'], [_check_ooxml, _check_open_container_format]),
)
def guess_mimetype(bin_data, default='application/octet-stream'):
    """ Attempts to guess the mime type of the provided binary data, similar
    to but significantly more limited than libmagic

    :param str bin_data: binary data to try and guess a mime type for
    :returns: matched mimetype or ``application/octet-stream`` if none matched
    """
    # by default, guess the type using the magic number of file hex signature (like magic, but more limited)
    # see http://www.filesignatures.net/ for file signatures
    for entry in _mime_mappings:
        for signature in entry.signatures:
            if bin_data.startswith(signature):
                for discriminant in entry.discriminants:
                    try:
                        guess = discriminant(bin_data)
                        if guess: return guess
                    except Exception:
                        # log-and-next
                        _logger.getChild('guess_mimetype').warn(
                            "Sub-checker '%s' of type '%s' failed",
                            discriminant.__name__, entry.mimetype,
                            exc_info=True
                        )
                # if no discriminant or no discriminant matches, return
                # primary mime type
                return entry.mimetype
    return default


try:
    import magic
except ImportError:
    magic = None
else:
    # There are 2 python libs named 'magic' with incompatible api.

    # magic from pypi https://pypi.python.org/pypi/python-magic/
    if hasattr(magic,'from_buffer'):
        guess_mimetype = lambda bin_data, default=None: magic.from_buffer(bin_data, mime=True)
    # magic from file(1) https://packages.debian.org/squeeze/python-magic
    elif hasattr(magic,'open'):
        ms = magic.open(magic.MAGIC_MIME_TYPE)
        ms.load()
        guess_mimetype = lambda bin_data, default=None: ms.buffer(bin_data)
