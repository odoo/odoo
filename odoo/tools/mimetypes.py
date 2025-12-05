# Part of Odoo. See LICENSE file for full copyright and licensing details.
""" Mimetypes related utilities. """

import collections
import io
import logging
import mimetypes
import re
from os import PathLike

from . import _mimetypes

try:
    import magic
except ImportError:
    magic = None

__all__ = (
    'MIMETYPE_HEAD_SIZE',
    'fix_filename_extension',
    'get_extension',
    'guess_mimetype',
)


_logger = logging.getLogger(__name__)
_logger_guess_mimetype = _logger.getChild('guess_mimetype')

MIMETYPE_HEAD_SIZE = _mimetypes.MIMETYPE_HEAD_SIZE
_extension_re = re.compile(r'[\w-]+')
_old_ms_office_mimetypes = {'.doc', '.xls', '.ppt'}
_new_ms_office_mimetypes = {'.docx', '.xlsx', '.pptx'}
_olecf_mimetypes = {'application/x-ole-storage', 'application/CDFV2'}


def guess_mimetype(
    bin_data: collections.abc.Buffer,  # bytes, bytearray, memoryview
    default: str = 'application/octet-stream',
) -> str:
    """
    Get a glance at the first ``MIMETYPE_HEAD_SIZE`` (2kiB) bytes of the
    given binary data and try to determine the content mimetype.

    It uses :manpage:`magic(5)` when both the C library and the python
    wrapper are installed. Otherwise it uses Odoo's own limited
    implemementation.

    .. warning::

       This function is best-effort, do not blindly trust its output!
       It takes a glance at some positions inside the data to try to
       match some known patterns. A rogue user can easily trick this
       function by forging a file with the expected patterns at the
       correct positions.

    >>> guess_mimetype(b"<?xml version="1.0" ?><odoo></odoo>")
    "text/xml"
    """
    if isinstance(bin_data, bytes):
        pass
    elif isinstance(bin_data, collections.abc.Buffer):
        bin_data = bytes(bin_data[:MIMETYPE_HEAD_SIZE])
    else:
        e = ...
        raise TypeError(e)

    if magic:
        return _magic_guess_mimetype(bin_data, default)
    return _mimetypes.guess_mimetype(bin_data, default)


def guess_file_mimetype(
    path: PathLike,
    default: str = 'application/octet-stream',
) -> str:
    if magic:
        return magic.from_file(path, mime=True)
    return _mimetypes.guess_file_mimetype(path)


def get_extension(filename: str) -> str:
    """
    Return the extension (with the dot and lowercased) of the file.

    This function is a bit safer than :func:`os.path.splitext` and
    :meth:`pathlib.Path.suffix` from the python standard library: it
    makes sure that extensions longer than 4 characters exist in the
    ``/etc/mime.types`` database before returning them.

    >>> # same as the standard library
    >>> get_extension('file.txt')
    '.txt'
    >>> get_extension('file.tar.gz')
    '.gz'
    >>> get_extension('.htaccess')
    ''
    >>> # different from the standard library
    >>> get_extension('file.idontexist')
    ''
    """

    # A file has no extension if it has no dot (ignoring the leading one
    # of hidden files) or that what follow the last dot is not a single
    # word, e.g. "Mr. Doe"
    _stem, dot, ext = filename.lstrip('.').rpartition('.')
    if not dot or not _extension_re.fullmatch(ext):
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
    Make sure the filename ends with an extension of the given mimetype.

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


def is_mimetype_textual(mimetype):
    maintype, subtype = mimetype.split('/')
    return (
        maintype == 'text'
        or (maintype == 'application' and subtype in {'documents-email', 'json', 'xml'})
    )


def _magic_guess_mimetype(bin_data: bytes):
    mimetype = magic.from_buffer(bin_data[:MIMETYPE_HEAD_SIZE], mime=True)
    if mimetype in ('application/CDFV2', 'application/x-ole-storage'):
        # Those are the generic file format that Microsoft Office
        # was using before 2006, use our own check to further
        # discriminate the mimetype.
        if _mimetypes.is_doc(bin_data):
            return 'application/msword'
        if _mimetypes.is_xls(bin_data):
            return 'application/vnd.ms-excel'
        if _mimetypes.is_ppt(bin_data):
            return 'application/vnd.ms-powerpoint'
    elif mimetype == 'application/zip':
        # magic doesn't properly detect some Microsoft Office
        # documents created after 2025, use our own check to further
        # discriminate the mimetype.
        with io.BytesIO(bin_data) as file:
            if mimetype_ := _mimetypes.guess_office_open_xml(file):
                return mimetype_
    return mimetype
