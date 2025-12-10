import io
import logging
import mimetypes
import re
import typing
import zipfile

try:
    import magic
except ImportError:
    magic = None

__all__ = [
    'get_extension',
    'guess_file_mimetype',
    'guess_mimetype',
]

_logger = logging.getLogger(__name__)
_logger_guess_mimetype = _logger.getChild('guess_mimetype')
_olecf_mimetypes = {'application/x-ole-storage', 'application/CDFV2'}


class _Mimetype(typing.NamedTuple):
    mimetype: str
    extension: str
    match: typing.Callable[[bytes], bool]


class _Signature(typing.NamedTuple):
    magic_number: bytes
    offset: int = 0


def _odoo_guess_mimetype(bin_data, default='application/octet-stream'):
    for supported_mimetype in SUPPORTED_MIMETYPES:
        if supported_mimetype.match(bin_data):
            return supported_mimetype.mimetype

    return default


def _magic_guess_mimetype(bin_data):
    mimetype = magic.from_buffer(bin_data, mime=True)

    # magic.from_buffer() doesn't properly detect DOC, XLS, and PPT documents.
    if mimetype in _olecf_mimetypes:
        if is_doc(bin_data):
            return 'application/msword'

        if is_xls(bin_data):
            return 'application/vnd.ms-excel'

        if is_ppt(bin_data):
            return 'application/vnd.ms-powerpoint'

    # magic.from_buffer() doesn't properly detect DOCX, XLSX, and PPTX documents.
    if mimetype in ('application/octet-stream', 'application/zip'):
        if is_docx(bin_data):
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

        if is_xlsx(bin_data):
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        if is_pptx(bin_data):
            return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

    return mimetype


def guess_mimetype(bin_data, default='application/octet-stream'):
    if magic:
        return _magic_guess_mimetype(bin_data)

    return _odoo_guess_mimetype(bin_data, default)


def _odoo_guess_file_mimetype(path, default='application/octet-stream'):
    with open(path, 'rb') as file:
        data = file.read(4096)  # Smallest power of 2 that works for all detection functions (except for zip).

        if len(data) == 4096 and is_zip(data):  # We need the whole file.
            file.seek(0)
            data = file.read()

        mimetype = _odoo_guess_mimetype(data)

    return mimetype or default


def guess_file_mimetype(path, default='application/octet-stream'):
    if magic:
        return magic.from_file(path, mime=True)

    return _odoo_guess_file_mimetype(path, default)


def _match_magic_number(bin_data, *, match_all=(), match_any=()):
    for signature in match_all:
        if not bin_data.startswith(signature.magic_number, signature.offset):
            return False

    if not match_any:
        return True

    for signature in match_any:
        if bin_data.startswith(signature.magic_number, signature.offset):
            return True

    return False


def _match_office_open_xml(bin_data, *, dirname):
    if not is_zip(bin_data):
        return False

    with io.BytesIO(bin_data) as file:
        try:
            zip = zipfile.ZipFile(file)
        except zipfile.BadZipFile:
            return False

        filenames = zip.namelist()

        if '[Content_Types].xml' not in filenames:
            return False

        return any(entry.startswith(dirname) for entry in filenames)


mime_validator = re.compile(
    r"""
    [\w-]+ # type-name
    / # subtype separator
    [\w-]+ # registration facet or subtype
    (?:\.[\w-]+)* # optional faceted name
    (?:\+[\w-]+)? # optional structured syntax specifier
""", re.VERBOSE)


def _match_open_document(bin_data, *, dirname):
    if not is_zip(bin_data):
        return False

    with io.BytesIO(bin_data) as file:
        try:
            zip = zipfile.ZipFile(file)
        except zipfile.BadZipFile:
            return False

        filenames = zip.namelist()

        if 'mimetype' not in filenames:
            return False

        try:
            marcel = zip.read('mimetype').decode('ascii')
        except UnicodeDecodeError:
            return False

        return len(marcel) < 256 and mime_validator.match(marcel) and dirname in marcel


# -------------------------------------------------------------------------------------------------
# Match magic numbers
# -------------------------------------------------------------------------------------------------
# Images
def is_bmp(bin_data):
    return _match_magic_number(bin_data, match_all=[_Signature(b'BM')])


def is_gif(bin_data):
    return _match_magic_number(bin_data, match_all=[_Signature(b'GIF')])


def is_ico(bin_data):
    return _match_magic_number(bin_data, match_all=[_Signature(bytes.fromhex('00 00 01 00'))])


def is_jpg(bin_data):
    return _match_magic_number(bin_data, match_all=[_Signature(bytes.fromhex('FF D8 FF'))])


def is_png(bin_data):
    return _match_magic_number(bin_data, match_all=[_Signature(bytes.fromhex('89 50 4E 47'))])


def is_webp(bin_data):
    return _match_magic_number(bin_data, match_all=[
        _Signature(b'RIFF'),
        _Signature(b'WEBP', 8),
    ])


# Applications
def is_pdf(bin_data):
    return _match_magic_number(bin_data, match_all=[_Signature(b'%PDF-')])


def is_xml(bin_data):
    return _match_magic_number(bin_data, match_all=[_Signature(b'<')])


# Compound file binary format
def is_cfbf(bin_data):
    return _match_magic_number(bin_data, match_all=[
        _Signature(bytes.fromhex('D0 CF 11 E0 A1 B1 1A E1')),
    ])


def is_doc(bin_data):
    if is_cfbf(bin_data):
        return _match_magic_number(bin_data, match_all=[_Signature(bytes.fromhex('EC A5 C1 00'), 512)])  # Word

    return _match_magic_number(bin_data, match_all=[_Signature(bytes.fromhex('0D 44 4F 43'))])  # Deskmate


def is_ppt(bin_data):
    if not is_cfbf(bin_data):
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
        _match_magic_number(bin_data, match_any=any_signatures_1),
        _match_magic_number(bin_data, match_all=all_signatures_2),
        _match_magic_number(bin_data, match_all=all_signatures_3),
    ])


def is_xls(bin_data):
    if not is_cfbf(bin_data):
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
        _match_magic_number(bin_data, match_any=any_signatures_1),
        _match_magic_number(bin_data, match_all=all_signatures_2, match_any=any_signatures_2),
        b'\xE2\x00\x00\x00\x5C\x00\x70\x00\x04\x00\x00Calc' in bin_data[1568:2095],
    ])


# -------------------------------------------------------------------------------------------------
# Match content
# -------------------------------------------------------------------------------------------------
def is_svg(bin_data):
    return b'<svg' in bin_data and b'/svg' in bin_data


def is_empty(bin_data):
    return not bin_data


def is_txt(bin_data):
    try:
        data = bin_data.decode()
    except UnicodeDecodeError:
        return False

    return all(c >= ' ' or c in '\t\n\r' for c in data)


# -------------------------------------------------------------------------------------------------
# Zip
# -------------------------------------------------------------------------------------------------
def is_zip(bin_data):
    return _match_magic_number(bin_data, match_any=[
        _Signature(b'PK\3\4', 0),  # non-empty zip
        _Signature(b'PK\5\6', 0),  # empty zip
        _Signature(b'PK\6\6', 0),  # empty zip64
    ])


# OpenOffice xml
def is_docx(bin_data):
    return _match_office_open_xml(bin_data, dirname='word/')


def is_pptx(bin_data):
    return _match_office_open_xml(bin_data, dirname='ppt/')


def is_xlsx(bin_data):
    return _match_office_open_xml(bin_data, dirname='xl/')


# Open document
def is_odt(bin_data):
    return _match_open_document(bin_data, dirname='text')


def is_ods(bin_data):
    return _match_open_document(bin_data, dirname='spreadsheet')


SUPPORTED_MIMETYPES = [
    _Mimetype('application/x-empty', '', is_empty),
    _Mimetype('image/svg+xml', 'svg', is_svg),
    _Mimetype('text/xml', 'xml', is_xml),
    _Mimetype('image/jpeg', 'jpg', is_jpg),
    _Mimetype('image/png', 'png', is_png),
    _Mimetype('image/gif', 'gif', is_gif),
    _Mimetype('image/bmp', 'bmp', is_bmp),
    _Mimetype('image/vnd.microsoft.icon', 'ico', is_ico),
    _Mimetype('image/webp', 'webp', is_webp),
    _Mimetype('application/pdf', 'pdf', is_pdf),
    _Mimetype('application/msword', 'doc', is_doc),
    _Mimetype('application/vnd.ms-excel', 'xls', is_xls),
    _Mimetype('application/vnd.ms-powerpoint', 'ppt', is_ppt),
    _Mimetype('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'docx', is_docx),
    _Mimetype('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx', is_xlsx),
    _Mimetype('application/vnd.openxmlformats-officedocument.presentationml.presentation', 'pptx', is_pptx),
    _Mimetype('application/vnd.oasis.opendocument.text', 'odt', is_odt),
    _Mimetype('application/vnd.oasis.opendocument.spreadsheet', 'ods', is_ods),
    _Mimetype('application/zip', 'zip', is_zip),
    _Mimetype('text/plain', 'txt', is_txt),
]


_extension_pattern = re.compile(r'[\w-]+')


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
    if mimetype in _olecf_mimetypes and extension in {'.doc', '.xls', '.ppt'}:
        return filename

    if mimetype == 'application/zip' and extension in {'.docx', '.xlsx', '.pptx'}:
        return filename

    if extension := mimetypes.guess_extension(mimetype):
        _logger.warning("File %r has an invalid extension for mimetype %r, adding %r", filename, mimetype, extension)
        return filename + extension

    _logger.warning("File %r has an unknown extension for mimetype %r", filename, mimetype)
    return filename
