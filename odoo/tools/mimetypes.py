# -*- coding: utf-8 -*-
"""
Mimetypes-related utilities

# TODO: reexport stdlib mimetypes?
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
_logger_guess_mimetype = _logger.getChild('guess_mimetype')

# We define our own guess_mimetype implementation and if magic is available we
# use it instead.

# discriminants for zip-based file formats
_ooxml_dirs = {
    'word/': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pt/': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'xl/': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

_Signature = collections.namedtuple('_Signature', ['magic_number', 'offset'])


def _match_magic_number(bin_data, *, all=(), any=()):
    for signature in all:
        if bin_data[signature.offset:signature.offset + len(signature.magic_number)] != signature.magic_number:
            return False

    if not any:
        return True

    for signature in any:
        if bin_data[signature.offset:signature.offset + len(signature.magic_number)] == signature.magic_number:
            return True

    return False


def _match_office_open_xml(bin_data, *, dirname):
    if not _is_zip(bin_data):
        return False

    with io.BytesIO(bin_data) as file, zipfile.ZipFile(file) as zip:
        filenames = zip.namelist()

        if '[Content_Types].xml' not in filenames:
            return False

        return any(entry.startswith(dirname) for entry in filenames)


def _match_open_document(bin_data, *, dirname):
    if not _is_zip(bin_data):
        return False

    mime_validator = re.compile(
        r"""
        [\w-]+ # type-name
        / # subtype separator
        [\w-]+ # registration facet or subtype
        (?:\.[\w-]+)* # optional faceted name
        (?:\+[\w-]+)? # optional structured syntax specifier
    """, re.VERBOSE)

    with io.BytesIO(bin_data) as file, zipfile.ZipFile(file) as zip:
        filenames = zip.namelist()

        if 'mimetype' not in filenames:
            return False

        marcel = zip.read('mimetype').decode('ascii')

        return len(marcel) < 256 and mime_validator.match(marcel) and dirname in marcel


def _is_cfb(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('D0 CF 11 E0 A1 B1 1A E1'), 0)])


def _is_empty(bin_data):
    return not bin_data


def _is_jpg(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('FF D8 FF'), 0)])


def _is_png(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('89 50 4E 47'), 0)])


def _is_gif(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'GIF', 0)])


def _is_bmp(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'BM', 0)])


def _is_ico(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('00 00 01 00'), 0)])


def _is_webp(bin_data):
    return _match_magic_number(bin_data, all=[
        _Signature(b'RIFF', 0),
        _Signature(b'WEBP', 8),
    ])


def _is_zip(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('50 4B 03 04'), 0)])


def _is_docx(bin_data):
    return _match_office_open_xml(bin_data, dirname='word/')


def _is_pptx(bin_data):
    return _match_office_open_xml(bin_data, dirname='ppt/')


def _is_xlsx(bin_data):
    return _match_office_open_xml(bin_data, dirname='xl/')


def _is_odt(bin_data):
    return _match_open_document(bin_data, dirname='text')


def _is_ods(bin_data):
    return _match_open_document(bin_data, dirname='spreadsheet')


def _is_ppt(bin_data):
    if not _is_cfb(bin_data):
        return False

    any_signatures_1 = [
        _Signature(bytes.fromhex('00 6E 1E F0'), 512),
        _Signature(bytes.fromhex('0F 00 E8 03'), 512),
        _Signature(bytes.fromhex('A0 46 1D F0'), 512),
    ]

    all_signatures_2 = [
        _Signature(bytes.fromhex('FD FF FF FF'), 512),
        _Signature(bytes.fromhex('00 00'), 522),
    ]

    all_signatures_3 = [
        _Signature(b'\x00\xB9\x29\xE8\x11\x00\x00\x00MS PowerPoint 97', 2072),
    ]

    return any([
        _match_magic_number(bin_data, any=any_signatures_1),
        _match_magic_number(bin_data, all=all_signatures_2),
        _match_magic_number(bin_data, all=all_signatures_3),
    ])


def _is_pdf(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'%PDF-', 0)])


def _is_doc(bin_data):
    if _is_cfb(bin_data):
        return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('EC A5 C1 00'), 512)])  # Word

    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('0D 44 4F 43'), 0)])  # Deskmate


def _is_xml(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'<', 0)])


def _is_xls(bin_data):
    if not _is_cfb(bin_data):
        return False

    any_signatures_1 = [
        _Signature(bytes.fromhex('09 08 10 00 00 06 05 00'), 512),
    ]
    all_signatures_2 = [
        _Signature(bytes.fromhex('FD FF FF FF'), 512),
    ]
    any_signatures_2 = [
        _Signature(bytes.fromhex('00'), 518),
        _Signature(bytes.fromhex('02'), 518),
    ]

    return any([
        _match_magic_number(bin_data, any=any_signatures_1),
        _match_magic_number(bin_data, all=all_signatures_2, any=any_signatures_2),
        b'\xE2\x00\x00\x00\x5C\x00\x70\x00\x04\x00\x00Calc' in bin_data[1568:2095],
    ])


def _is_svg(bin_data):
    return b'<svg' in bin_data and b'/svg' in bin_data


def _is_txt(bin_data):
    return all(c >= ' ' or c in '\t\n\r' for c in bin_data[:1024].decode())

_Mimetype = collections.namedtuple('_Mimetype', ['mimetype', 'extension', 'match'])  # noqa: PYI024
SUPPORTED_MIMETYPES = {
    'empty': _Mimetype('application/x-empty', None, _is_empty),
    'pdf': _Mimetype('application/pdf', 'pdf', _is_pdf),
    'jpg': _Mimetype('image/jpeg', 'jpg', _is_jpg),
    'png': _Mimetype('image/png', 'png', _is_png),
    'gif': _Mimetype('image/gif', 'gif', _is_gif),
    'bmp': _Mimetype('image/bmp', 'bmp', _is_bmp),
    'svg': _Mimetype('image/svg+xml', 'svg', _is_svg),
    'xml': _Mimetype('text/xml', 'xml', _is_xml),
    'ico': _Mimetype('image/vnd.microsoft.icon', 'ico', _is_ico),
    'webp': _Mimetype('image/webp', 'webp', _is_webp),
    'doc': _Mimetype('application/msword', 'doc', _is_doc),
    'xls': _Mimetype('application/vnd.ms-excel', 'xls', _is_xls),
    'ppt': _Mimetype('application/vnd.ms-powerpoint', 'ppt', _is_ppt),
    'docx': _Mimetype('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'docx', _is_docx),
    'xlsx': _Mimetype('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx', _is_xlsx),
    'pptx': _Mimetype('application/vnd.openxmlformats-officedocument.presentationml.presentation', 'pptx', _is_pptx),
    'odt': _Mimetype('application/vnd.oasis.opendocument.text', 'odt', _is_odt),
    'ods': _Mimetype('application/vnd.oasis.opendocument.spreadsheet', 'ods', _is_ods),
    'zip': _Mimetype('application/zip', 'zip', _is_zip),
    'txt': _Mimetype('text/plain', 'txt', _is_txt),
}

# SUPPORTED_ZIP_MIMETYPES = {
#     'docx': _Mimetype('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'docx', _is_docx),
#     'xlsx': _Mimetype('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx', _is_xlsx),
#     'pptx': _Mimetype('application/vnd.openxmlformats-officedocument.presentationml.presentation', 'pptx', _is_pptx),
#     'odt': _Mimetype('application/vnd.oasis.opendocument.text', 'odt', _is_ods),
#     'ods': _Mimetype('application/vnd.oasis.opendocument.spreadsheet', 'ods', _is_ods),
# }


def _odoo_guess_file_mimetype():
    pass


def _odoo_guess_binary_mimetype():
    pass


def _odoo_guess_mimetype(bin_data, default='application/octet-stream'):
    for supported_mimetype in SUPPORTED_MIMETYPES.values():
        if supported_mimetype.match(bin_data):
            return supported_mimetype.mimetype

    return default



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

_ppt_pattern = re.compile(rb'''
    \x00\x6E\x1E\xF0  # PowerPoint presentation subheader_1
  | \x0F\x00\xE8\x03  # PowerPoint presentation subheader_2
  | \xA0\x46\x1D\xF0  # PowerPoint presentation subheader_3
  | \xFD\xFF\xFF\xFF\x0E\x00\x00\x00  # PowerPoint presentation subheader_4
  | \xFD\xFF\xFF\xFF\x1C\x00\x00\x00  # PowerPoint presentation subheader_5
  | \xFD\xFF\xFF\xFF\x43\x00\x00\x00  # PowerPoint presentation subheader_6
''', re.VERBOSE)

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
    if b'Microsoft Excel' in data:
        return 'application/vnd.ms-excel'
    if _ppt_pattern.search(data):
        return 'application/vnd.ms-powerpoint'
    return False


try:
    import magic
    def guess_mimetype(bin_data, default=None):
        if isinstance(bin_data, bytearray):
            bin_data = bytes(bin_data[:1024])
        elif not isinstance(bin_data, bytes):
            raise TypeError('`bin_data` must be bytes or bytearray')
        mimetype = magic.from_buffer(bin_data[:1024], mime=True)
        if mimetype in ('application/CDFV2', 'application/x-ole-storage'):
            # Those are the generic file format that Microsoft Office
            # was using before 2006, use our own check to further
            # discriminate the mimetype.
            try:
                if msoffice_mimetype := _check_olecf(bin_data):
                    return msoffice_mimetype
            except Exception:  # noqa: BLE001
                _logger_guess_mimetype.warning(
                    "Sub-checker '_check_olecf' of type '%s' failed",
                    mimetype,
                    exc_info=True,
                )
        if mimetype == 'application/zip':
            # magic doesn't properly detect some Microsoft Office
            # documents created after 2025, use our own check to further
            # discriminate the mimetype.
            # /!\ Only work when bin_data holds the whole zipfile. /!\
            try:
                if msoffice_mimetype := _check_ooxml(bin_data):
                    return msoffice_mimetype
            except zipfile.BadZipFile:
                pass
            except Exception:  # noqa: BLE001
                _logger_guess_mimetype.warning(
                    "Sub-checker '_check_ooxml' of type '%s' failed",
                    mimetype,
                    exc_info=True,
                )
        return mimetype

except ImportError:
    guess_mimetype = _odoo_guess_mimetype

_extension_pattern = re.compile(r'\w+')


def get_extension(filename):
    # A file has no extension if it has no dot (ignoring the leading one
    # of hidden files) or that what follow the last dot is not a single
    # word, e.g. "Mr. Doe"
    _stem, dot, ext = filename.lstrip('.').rpartition('.')
    if not dot or not _extension_pattern.fullmatch(ext):
        return ''

    # Assume all 4-chars extensions to be valid extensions even if it is
    # not known from the mimetypes database. In /etc/mime.types, only 7%
    # known extensions are longer.
    if len(ext) <= 4:
        return f'.{ext}'.lower()

    # Use the mimetype database to determine the extension of the file.
    guessed_mimetype, guessed_ext = mimetypes.guess_type(filename)
    if guessed_ext:
        return guessed_ext
    if guessed_mimetype:
        return f'.{ext}'.lower()

    # Unknown extension.
    return ''


_old_ms_office_mimetypes = {'.doc', '.xls', '.ppt'}
_new_ms_office_mimetypes = {'.docx', '.xlsx', '.pptx'}
_olecf_mimetypes = {'application/x-ole-storage', 'application/CDFV2'}


def fix_filename_extension(filename, mimetype):
    """
    Make sure the filename ends with an extension of the mimetype.

    :param str filename: the filename with an unsafe extension
    :param str mimetype: the mimetype detected reading the file's content
    :returns: the same filename if its extension matches the detected
        mimetype, otherwise the same filename with the mimetype's
        extension added at the end.
    """
    extension_mimetype = mimetypes.guess_type(filename)[0]
    if extension_mimetype == mimetype:
        return filename

    extension = get_extension(filename)
    if mimetype in _olecf_mimetypes and extension in _old_ms_office_mimetypes:
        return filename

    if mimetype == 'application/zip' and extension in _new_ms_office_mimetypes:
        return filename

    if extension := mimetypes.guess_extension(mimetype):
        _logger.warning("File %r has an invalid extension for mimetype %r, adding %r", filename, mimetype, extension)
        return filename + extension

    _logger.warning("File %r has an unknown extension for mimetype %r", filename, mimetype)
    return filename
