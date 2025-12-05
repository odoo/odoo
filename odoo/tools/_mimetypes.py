# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import re
import typing
import zipfile

MIMETYPE_HEAD_SIZE = 2048


def guess_mimetype(bin_data: bytes, default: str):
    for supported_mimetype in _database.values():
        if supported_mimetype.match(bin_data):
            return supported_mimetype.mimetype

    return default


_database = {}


class _Mimetype(typing.NamedTuple):
    mimetype: str
    extension: str
    match: callable[[bytes], bool]


def register(mimetype):
    def _register_inner(magic_function):
        pre, is_, extension = magic_function.__name__.partition('is_')
        assert not pre and is_ and extension, \
            f"function name is not like _is_{{extension}}: {magic_function.__name__}"
        assert (exist := _database.get(extension)) is None, \
            f"cannot override {extension!r}: {exist}"
        _database[extension] = _Mimetype(mimetype, extension, magic_function)
        magic_function.mimetype = mimetype
        magic_function.extension = extension
        return magic_function
    return _register_inner


class _Signature(typing.NamedTuple):
    magic_number: bytes
    offset: int = 0


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


# text/

@register('image/svg+xml')
def is_svg(bin_data):
    return b'<svg' in bin_data and b'/svg' in bin_data and is_txt(bin_data)


@register('text/plain')
def is_txt(bin_data):
    try:
        head = bin_data[:MIMETYPE_HEAD_SIZE].decode()
    except UnicodeDecodeError:
        return False
    return all(c >= ' ' or c in '\t\n\r' for c in head)


@register('text/xml')
def is_xml(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'<')]) and is_txt(bin_data)


# application/

def is_cfb(bin_data):
    return _match_magic_number(bin_data, all=[
        _Signature(bytes.fromhex('D0 CF 11 E0 A1 B1 1A E1')),
    ])


@register('application/pdf')
def is_pdf(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'%PDF-')])


@register('application/zip')
def is_zip(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('50 4B 03 04'))])


# Images

@register('image/bmp')
def is_bmp(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'BM')])


@register('image/gif')
def is_gif(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'GIF')])


@register('image/vnd.microsoft.icon')
def is_ico(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('00 00 01 00'))])


@register('image/jpeg')
def is_jpg(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(bytes.fromhex('FF D8 FF'))])


@register('image/png')
def is_png(bin_data):
    return _match_magic_number(bin_data, all=[_Signature(b'\x89PNG')])


@register('image/webp')
def is_webp(bin_data):
    return _match_magic_number(bin_data, all=[
        _Signature(b'RIFF'),
        _Signature(b'WEBP', offset=8),
    ])


# Microsoft Office

def _match_office_open_xml(bin_data, *, dirname):
    if not is_zip(bin_data):
        return False

    with io.BytesIO(bin_data) as file, zipfile.ZipFile(file) as zip:
        filenames = zip.namelist()

        if '[Content_Types].xml' not in filenames:
            return False

        return any(entry.startswith(dirname) for entry in filenames)


@register('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
def is_docx(bin_data):
    return _match_office_open_xml(bin_data, dirname='word/')


@register('application/vnd.openxmlformats-officedocument.presentationml.presentation')
def is_pptx(bin_data):
    return _match_office_open_xml(bin_data, dirname='ppt/')


@register('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
def is_xlsx(bin_data):
    return _match_office_open_xml(bin_data, dirname='xl/')


@register('application/msword')
def is_doc(bin_data):
    if is_cfb(bin_data):
        return _match_magic_number(bin_data, all=[
            _Signature(bytes.fromhex('EC A5 C1 00'), offset=512),
        ])  # Word

    return _match_magic_number(bin_data, all=[
        _Signature(bytes.fromhex('0D 44 4F 43')),
    ])  # Deskmate


@register('application/vnd.ms-powerpoint')
def is_ppt(bin_data):
    if not is_cfb(bin_data):
        return False

    any_signatures_1 = [
        _Signature(bytes.fromhex('00 6E 1E F0'), offset=512),
        _Signature(bytes.fromhex('0F 00 E8 03'), offset=512),
        _Signature(bytes.fromhex('A0 46 1D F0'), offset=512),
    ]

    all_signatures_2 = [
        _Signature(bytes.fromhex('FD FF FF FF'), offset=512),
        _Signature(bytes.fromhex('00 00'), offset=522),
    ]

    all_signatures_3 = [
        _Signature(b'\0\xB9\x29\xE8\x11\0\0\0MS PowerPoint 97', offset=2072),
    ]

    return (_match_magic_number(bin_data, any=any_signatures_1)
         or _match_magic_number(bin_data, all=all_signatures_2)
         or _match_magic_number(bin_data, all=all_signatures_3)
    )


@register('application/vnd.ms-excel')
def is_xls(bin_data):
    if not is_cfb(bin_data):
        return False

    any_signatures_1 = [
        _Signature(bytes.fromhex('09 08 10 00 00 06 05 00'), offset=512),
    ]
    all_signatures_2 = [
        _Signature(bytes.fromhex('FD FF FF FF'), offset=512),
    ]
    any_signatures_2 = [
        _Signature(b'\0', offset=518),
        _Signature(b'\2', offset=518),
    ]

    return (_match_magic_number(bin_data, any=any_signatures_1)
         or _match_magic_number(bin_data, all=all_signatures_2, any=any_signatures_2)
         or b'\xE2\0\0\0\x5C\0\x70\0\x04\0\0Calc' in bin_data[1568:2095]
    )


# Open Document

def _match_open_document(bin_data, *, dirname):
    if not is_zip(bin_data):
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


@register('application/vnd.oasis.opendocument.text')
def is_odt(bin_data):
    return _match_open_document(bin_data, dirname='text')


@register('application/vnd.oasis.opendocument.spreadsheet')
def is_ods(bin_data):
    return _match_open_document(bin_data, dirname='spreadsheet')
