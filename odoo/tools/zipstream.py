# Part of Odoo. See LICENSE file for full copyright and licensing details.
""" Craft zipfiles using little memory. """

import datetime as dt
import io
import typing
import zipfile
from collections.abc import Iterable, Iterator, Sequence

from .binary import BinaryValue

try:
    import bz2
except ImportError:
    bz2 = None

try:
    import lzma
except ImportError:
    lzma = None

if typing.TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment


MAX_INT32 = 0xFF_FF_FF_FF  # 4GiB - 1


class ZipAttachment(typing.TypedDict):
    name: str
    """
    The hierarchized name of the file.

    Folders inside zipfiles are implicits, all files whose names start
    with a same "<folder>/" prefix appears together inside the same
    folder in the zipfile.

    .. example::

        To replicate the following structure:

        .. code::

            reports
            ├── 2025
            │   ├── november.pdf
            │   └── december.pdf
            └── 2026
                └── january.pdf

        Create three zip-attachments with names:

        * reports/2026/january.pdf
        * reports/2025/november.pdf
        * reports/2025/december.pdf

    .. tip::

        Many ZIP softwares have an "extract here" button that extracts
        the zipfile in the user's working directory. That button works
        best when all the files are enclosed in a top-level folder.
    """

    raw: BinaryValue
    """ The file to include in the zipfile. """

    write_date: dt.datetime
    """
    The last modification datetime of the file.

    When the datetime is naive, it is assumed to be UTC.
    """


def guess_zip_size(attachments: Iterable['IrAttachment | ZipAttachment']) -> int:
    """
    Get the approximative size the zipfile will have with all the
    attachments stored inside.

    This function assumes no file compression, utf-8 filenames, and
    standard + z64 zip headers. It is likely that the final file will
    store compressed files, hence be lighter than this function pretends.
    """
    count_z32 = [att for att in attachments if att['raw'].size <= MAX_INT32]
    count_z64 = len(attachments) - count_z32

    headers_size = (
        len(attachments) * zipfile.sizeFileHeader
      + count_z32 * 16  # struct.calcsize('<4sIII')  # DataDescriptor 32
      + count_z64 * 24  # struct.calcsize('<4sIQQ')  # DataDescriptor 64
      + len(attachments) * zipfile.sizeCentralDir
      + zipfile.sizeEndCentDir
    )

    if count_z64:
        headers_size += zipfile.sizeEndCentDir64
        headers_size += zipfile.sizeEndCentDir64Locator
        # ExtraField Zip64, twice: FileHeader, CentralDirectory
        headers_size += count_z64 * 64  # 2 * struct.calcsize('<HHQQQI')

    # assume no file gets compressed
    content_size = sum(attach['raw'].size for attach in attachments)
    filenames_size = sum(len(attach.name.encode() for attach in attachments))

    return headers_size + filenames_size + content_size


class _ChunkSink(io.RawIOBase):
    def __init__(self):
        self._chunks = []

    def writable(self):
        return True

    def write(self, b):
        if b:
            self._chunks.append(bytes(b))
        return len(b)

    def get_chunks(self) -> Sequence[bytes]:
        if not self._chunks:
            return ()
        chunks, self._chunks = self._chunks, []
        return chunks


def stream_zip(
    attachments: Iterable['IrAttachment | ZipAttachment'],
    user_timezone: dt.timezone = dt.UTC,
) -> Iterator[bytes]:
    """
    Generate a zipfile out of many attachments piece by piece so that it
    is possible to save it on disk or send it over the network using
    very little memory.

    :param attachments: The attachments, either as a recordset or as a
        list of :class:`ZipAttachment`.
    :param user_timezone: ZIP datetimes are naive, they don't have a
        timezone and most ZIP softwares assume the datetime is localized
        in the user's current timezone. Use this parameter so that a
        file modified at 8AM New-York time appears as "8AM" when opened
        by a user at New-York.
    :returns: An iterator (something you can iter on, but only once)
        that yields the pieces of the zipfile as it is being generated.

    .. example::

        .. code-block::

            attachments = env['ir.attachment'].search(...)
            attachments.fetch(ZipAttachment.__required_fields__)
            stream = generate_zip(attachments)
            with open('filename.zip', 'wb') as file:
                for chunk in stream:
                    file.write(chunk)
    """
    sink = _ChunkSink()
    with zipfile.ZipFile(sink, 'wb') as zip_file:
        for attach in attachments:
            write_date = attach['write_date']
            write_date = write_date.replace(tzinfo=write_date.tzinfo or dt.UTC)
            info = zipfile.ZipInfo(
                attach['name'].lstrip('/'),
                write_date.astimezone(user_timezone).timetuple()[:6],
            )
            info.file_size = attach['raw'].size
            if info.is_dir():
                info.external_attr = (0o40775 << 16) | 0x10
            elif attach['raw'].mimetype.startswith('text/'):
                # other mimetypes are assumed to be compressed already
                info.compress_type = zipfile.ZIP_DEFLATED

            with attach['raw'].open() as file, zip_file.open(info, 'w') as zip_entry:
                while chunk := file.read(io.DEFAULT_BUFFER_SIZE):
                    zip_entry.write(chunk)
                    if chunks := sink.get_chunks():
                        yield from chunks
            yield from sink.get_chunks()
    yield from sink.get_chunks()
