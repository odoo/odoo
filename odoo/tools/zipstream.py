# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Utilities to work with partial zip files.

The zipfile library found in the python standard library only work with
full zipfile, i.e. the entire zipfile must be created/loaded in memory.

There are situations where we don't want to load the entire thing in
memory, e.g. to craft a zipfile out of many large file and to send it
over the network.
"""

# https://users.cs.jmu.edu/buchhofp/forensics/formats/pkzip.html
# https://pkwaredownloads.blob.core.windows.net/pkware-general/Documentation/APPNOTE-6.3.9.TXT
# https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-dosdatetimetofiletime
#
# The structure of a zip file is as follow:
#
#   Local File Header 1
#   File data 1
#   (Optional) Data Descriptor 1
#   Local File Header 2
#   File data 2
#   (Optional) Data Descriptor 2
#   ...
#   Local File Header n
#   File data n
#   (Optional) Data Descriptor n
#
#   Central Directory file 1
#   Central Directory file 2
#   ...
#   Central Directory file n
#
#   (if zip64) End Of Central Directory Zip64
#   (if zip64) End Of Central Directory Locator
#   EndOfCentralDirectory
#
# Each Local File Header contains the metadata for the file that
# follows (e.g. the filename). It is possible that the crc32 or
# compressed file size or uncompressed file size are not yet known when
# producing the local file header and will only be known once the file
# data loaded. In those cases the DATA_DESCRIPTOR flag can be set and
# the actual three values will be written after the data.
#
# Each File data can be compressed using an algorithm whoose identifier
# was written in the local file header. They can also be encrypted but
# this library does not support encryption.
#
# The central directory is found at the end of the archive, after all
# files. It contains a copy of every Local File Header enhanced with the
# data descriptor values and an additional pointer (numeric offset from
# the beginning of the archive) where to find the local file header.
#
# After the central directory comes three structures that let contain
# pointers (numeric offset from the beginning of the archive) where to
# find the start of the Central Directory, and the start of the Zip64
# Central Directory.


import dataclasses
import datetime as dt
import enum
import io
import struct
import typing
import zlib
from collections.abc import Iterable, Iterator, MutableMapping
from functools import partial

try:
    import bz2
except ImportError:
    bz2 = None

try:
    import lzma
except ImportError:
    lzma = None

MAX_INT32 = 0xFF_FF_FF_FF  # 4GiB - 1


# attachments.read(ZipAttachment.__required_keys__)
class ZipAttachment(typing.TypedDict):
    id: typing.NotRequired[int]
    """
    The ID of the attachment, not used by this library, present for
    compatiblity with :meth:`~odoo.models.BaseModel.read`.
    """

    file_size: int
    """ The size (in bytes) of the file. """

    mimetype: str
    """
    The mimetype of the file.

    Only text/ mimetypes are compressed, other mimetypes (e.g. image/,
    video/, application/) are expected to be compressed already and are
    stored as-is in the generated zipfile.
    """

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

    store_fname: str
    """
    The path to file on the filesystem. It must be a path relative to
    the :func:`generate_zip`'s ``filestore`` parameter.
    """

    write_date: dt.datetime
    """
    The last modification datetime of the file.

    When the datetime is naive, it is assumed to be UTC.
    """


def generate_zip(
    attachments: Iterable[dict | ZipAttachment],
    filestore: str,
    user_timezone: dt.timezone = dt.UTC,
) -> Iterator[bytes]:
    """
    Generate a zipfile out of many attachments piece by piece so that it
    is possible to save it on disk or send it over the network using
    very little memory.

    :param attachments: The attachments as a list of dict with entries
        ``'file_size'``, ``'mimetype'``, ``'name'``, ``'store_fname'``
        and ``'write_date'`` to include in the zipfile. It typically is
        ``attachments.read(ZipAttachment.__required_keys__)``, but it
        can also be crafted by hand.
    :param filestore: The directory path where to look for attachments'
        ``store_fname``. The directory acts as a jail, relative paths
        cannot go back beyond that directory. It typically should be
        ``odoo.tools.config.filestore(env.cr.dbname)``.
    :param user_timezone: ZIP datetimes are naive, they don't have a
        timezone and most ZIP softwares assume the datetime is localized
        in the user's current timezone. Use this parameter so that a
        file modified at 8AM New-York time appears as "8AM" when opened
        by a user at New-York.
    """
    from werkzeug.security import safe_join  # noqa: PLC0415, solves an import cycle

    directory: list[_LocalFile] = []
    offset = 0

    def send(chunk):
        nonlocal offset
        offset += len(chunk)
        return chunk

    for attach in attachments:
        local_file = _LocalFile()
        local_file.offset = offset
        directory.append(local_file)

        filename = attach['name'].strip('/').encode()
        filepath = safe_join(filestore, attach['store_fname'])
        if not filepath:
            raise FileNotFoundError((filestore, attach['store_fname']))

        need_zip64 = attach['file_size'] > MAX_INT32
        flags = Flags.DATA_DESCRIPTOR
        try:
            filename.decode('ascii')
        except UnicodeDecodeError:
            flags |= Flags.UNICODE_FILENAME
        version_needed = (
                 Version.UNICODE_FILENAME if flags & Flags.UNICODE_FILENAME
            else Version.ZIP64 if need_zip64
            else Version.DEFAULT
        )
        compression = (
            # assume non-text mimetypes are compressed already
            CompressionMethod.DEFLATED
            if attach['mimetype'].startswith('text/') else
            CompressionMethod.NO_COMPRESSION  # 0, falsy
        )

        # Relocalize the date in the user's timezone. Best we can do as
        # zipfiles have no timezone information.
        modification = attach['write_date']
        if modification.tzinfo != user_timezone:
            if not modification.tzinfo:
                modification = modification.replace(tzinfo=dt.UTC)
            modification = modification.astimezone(user_timezone)
        modification = modification.replace(tzinfo=None)

        extra_fields = {}
        if need_zip64:
            extra_fields[ExtraFieldId.ZIP64] = Zip64(
                original_size=0,  # found in data descriptor
                compressed_size=0,  # found in data descriptor
                offset=local_file.offset,
                disk_no=0,
            )

        local_file.header = LocalFileHeader(
            version=version_needed,
            flags=flags,
            compression=compression,
            modification=attach['write_date'],
            crc32=0,  # found in data descriptor
            compressed_size=0,  # found in data descriptor
            uncompressed_size=0,  # found in data descriptor
            filename=filename,
            extra_fields=extra_fields,
        )
        yield send(local_file.header.pack())

        # crc32 and compressed_size updated while reading the file
        dd = local_file.data_descriptor = DataDescriptor(
            crc32=0,
            compressed_size=0 if compression else attach['file_size'],
            uncompressed_size=attach['file_size'],
        )
        if compression:
            compressor = compression.compressor()
        with open(filepath, 'rb') as file:
            while chunk := file.read(io.DEFAULT_BUFFER_SIZE):  # 8kiB
                dd.crc32 = zlib.crc32(chunk, dd.crc32)
                if compression:
                    chunk = compressor.compress(chunk)
                    dd.compressed_size += len(chunk)
                yield send(chunk)
        if compression:
            chunk = compressor.flush()
            if chunk:
                dd.compressed_size += len(chunk)
                yield send(chunk)
            del compressor
        yield send(dd.pack(zip64=need_zip64))

    central_directory_offset = offset
    for local_file in directory:
        zip64 = local_file.header.extra_fields.get(ExtraFieldId.ZIP64)
        if zip64:
            zip64.original_size = local_file.uncompressed_size
            zip64.compressed_size = local_file.compressed_size

        yield send(CentralDirectoryFileHeader(
            version_os=OS.UNIX,
            version_zip=Version.UNICODE_FILENAME,
            version_needed=local_file.header.version,
            flags=local_file.header.flags,
            compression=local_file.header.compression,
            modification=local_file.header.modification,
            crc32=(local_file.data_descriptor or local_file.header).crc32,
            compressed_size=MAX_INT32 if zip64 else ((
                local_file.data_descriptor or local_file.header).compressed_size),
            uncompressed_size=MAX_INT32 if zip64 else ((
                local_file.data_descriptor or local_file.header).uncompressed_size),
            disk_no=0xFF_FF if zip64 else 0,
            internal_attribute=(
                InternalAttribute.TEXT if local_file.header.compression else 0
            ),
            external_attribute=0,
            local_header_offset=MAX_INT32 if need_zip64 else local_file.offset,
            filename=local_file.header.filename,
            extra_fields=local_file.header.extra_fields,
            comment=b'',
        ).pack())

    central_directory_size = offset - central_directory_offset
    if any(ExtraFieldId.ZIP64 in cf.header.extra_fields for cf in directory):
        central_directory64_offset = offset
        yield send(EndOfCentralDirectory64(
            version_os=OS.UNIX,
            version_zip=Version.UNICODE_FILENAME,
            version_needed=Version.UNICODE_FILENAME,
            disk_no=0,
            central_directory_disk_no=0,
            central_directory_disk_entries_count=len(directory),
            central_directory_total_entries_count=len(directory),
            central_directory_size=central_directory_size,
            central_directory_offset=central_directory_offset,
            comment=b'',
        ).pack())
        yield send(EndOfCentralDirectoryLocator(
            central_directory64_disk_no=0,
            central_directory64_offset=central_directory64_offset,
            total_disk_count=1,
        ))

    yield send(EndOfCentralDirectory(
        disk_no=0,
        central_directory_disk_no=0,
        central_directory_disk_entries_count=len(directory),
        central_directory_total_entries_count=len(directory),
        central_directory_size=min(central_directory_size, MAX_INT32),
        central_directory_offset=min(central_directory_offset, MAX_INT32),
        comment=b'',
    ).pack())


class _LocalFile:
    __slots__ = ('data_descriptor', 'header', 'offset')


def serialize_time_date(dt: dt.datetime) -> tuple[int, int]:
    """
    Serialize a python datetime into the MS-DOS format used by ZIP.

    The ZIP datetimes are naive, there is no timezone associated with
    the value. This function uses the datetime as-is, be it naive or
    aware, UTC or not.

    The MS-DOS format works for dates between 1980 and 2107 (included)
    and has a precision down to 2 seconds (odd seconds don't exist).
    This function rejects dates before the range. This function
    serializes dates after the range, even if the date will not fit in
    a 16-bits unsigned integer.

    :param dt: A python datetime to be serialized.
    :returns: A 2 value tuple (time, date), to be ``struct.pack('<HH')``.
    :raises ValueError: When the given datetime is before 1980.
    """
    # https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-dosdatetimetofiletime
    if dt.year < 1980:
        raise ValueError(
            f"cannot serialize a date before 1970: {dt}")
    ziptime = (dt.hour << 11) + (dt.minute << 5) + dt.second // 2
    zipdate = ((dt.year - 1980) << 9) + (dt.month << 5) + dt.day
    return (ziptime, zipdate)


def deserialize_time_date(ziptime: int, zipdate: int) -> dt.datetime:
    """
    Deserialize a time and date pair in the MS-DOS format used by ZIP
    into a python datetime.

    The ZIP datetimes are naive, there is no timezone associated with
    the value. This function likewise makes no attempt to localize the
    datetime and just return the deserialized naive python datetime. The
    actual timezone depends on the software that created the ZIP file.

    The MS-DOS format works for dates between 1980 and 2107 (included)
    and has a precision down to 2 seconds. This function makes no
    attempt to support dates outside that range.

    :param ziptime: A MS-DOS time as a 16-bits unsigned integer.
    :param ziptime: A MS-DOS date as a 16-bits unsigned integer.
    :returns: A naive python datetime, between 1/1/1980-00:00:00 and
        31/12/2107-23:59:58 (included).
    """
    # ruff: noqa: E221
    # https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-dosdatetimetofiletime
    second = (ziptime & 0b0000000000011111)
    minute = (ziptime & 0b0000011111100000) >> 5
    hour   = (ziptime & 0b1111100000000000) >> 11
    day    = (zipdate & 0b0000000000011111)
    month  = (zipdate & 0b0000000111100000) >> 5
    year   = (zipdate & 0b1111111000000000) >> 9
    try:
        return dt.datetime(1980 + year, month, day, hour, minute, second * 2)
    except ValueError as exc:
        exc.add_note(str((1980 + year, month, day, hour, minute, second * 2)))
        raise


class OS(enum.IntEnum):
    """ The operating system where a zipfile was created. """
    MSDOS = 0
    AMIGA = 1
    OPOENVMS = 2
    UNIX = 3
    VM_CMS = 4
    ATARI_ST = 5
    OS_2_HPFS = 6
    MACINTOSH = 7
    Z_SYSTEM = 8
    CP_M = 9
    NTFS = 10
    MVS = 11
    VSE = 12
    ACORN_RISC = 13
    VFAT = 14
    ALTERNATE_MVS = 15
    BEOS = 16
    TANDEM = 17
    OS_400 = 18
    DARWIN = 19


class Version(enum.IntEnum):
    """ The version of zip needed to work with a specific file. """
    DEFAULT = 20  # 2.0
    ZIP64 = 45  # 4.5
    UNICODE_FILENAME = 63  # 6.3


class InternalAttribute(enum.IntFlag, boundary=enum.FlagBoundary.KEEP):
    """ Some flags found in the central directory. """
    TEXT = 1 << 0
    CONTROL_FIELD_RECORDS_PRECEDE_LOGICAL_RECORDS = 1 << 2


class CompressionMethod(enum.IntEnum):
    """
    The compression algorithm used to compress a file.

    All algorithms are listed in this enumeration but only deflated,
    bzip2 and lzma are supported.
    """
    NO_COMPRESSION = 0
    SHRUNK = 1
    REDUCED_WITH_COMPRESSION_FACTOR_1 = 2
    REDUCED_WITH_COMPRESSION_FACTOR_2 = 3
    REDUCED_WITH_COMPRESSION_FACTOR_3 = 4
    REDUCED_WITH_COMPRESSION_FACTOR_4 = 5
    IMPLODED = 6
    DEFLATED = 8
    ENHANCED_DEFLATED = 9
    PK_WARE_DCL_IMPLODED = 10
    BZIP2 = 12
    LZMA = 14
    IBM_TERSE = 18
    IBM_LZ77_Z = 19
    PPMD = 98


CompressionMethod.DEFLATED.compressor = partial(zlib.compressobj, wbits=-15)
CompressionMethod.DEFLATED.decompressor = partial(zlib.decompressobj, wbits=-15)
if bz2:
    CompressionMethod.BZIP2.compressor = bz2.BZ2Compressor
    CompressionMethod.BZIP2.decompressor = bz2.BZ2Decompressor
if lzma:
    CompressionMethod.LZMA.compressor = lzma.LZMACompressor
    CompressionMethod.LZMA.decompressor = lzma.LZMADecompressor


class Flags(enum.IntFlag, boundary=enum.FlagBoundary.KEEP):
    """
    Some flags found in the Local File Header.

    All specified flags are listed in this enumeration but only
    data descriptor and language encoding are supported.
    """
    ENCRYPTED_FILE = 1 << 0
    COMPRESSION_OPTION1 = 1 << 1
    COMPRESSION_OPTION2 = 1 << 2
    DATA_DESCRIPTOR = 1 << 3
    ENHANCED_DEFLATION = 1 << 4
    COMPRESSED_PATCHED_DATA = 1 << 5
    STRONG_ENCRYPTION = 1 << 6
    LANGUAGE_ENCODING = 1 << 11  # filename and comment use UTF-8
    MASK_HEADER_VALUES = 1 << 13


class ExtraFieldId(enum.IntEnum):
    """ The numeric identifier of every extra field. """
    ZIP64 = 0x0001


class _ExtraField:
    """
    Abstract class and registry for concrete extra fields.

    All subclasses must implement ``extra_field_id``, ``_struct`` and
    ``__init__``. All subclasses are registered in the ``_registry``
    using ``extra_field_id`` as entry key.

    Two functions: :meth:`unpack` and :meth:`pack` are provided to
    serialize and parse an extra field using ``_struct``.

    The generic :meth:`pack` works by introspecting the dataclass fields
    of the concrete ExtraField class. It only works when ``_struct``
    maps 1-1 to the dataclass fields. In other cases, please override
    :meth:`pack`.
    """

    _registry: 'MutableMapping[ExtraFieldId, _ExtraField]' = {}
    """ A registry of extra fields. Populated by :meth:`__init_subclass__`. """

    extra_field_id: ExtraFieldId
    """ The unique numeric identifier of this extra field. """

    _struct: bytes
    """
    The structure (without the ``<HH`` prefix) used to parse and
    serialize the extra field.
    """

    @classmethod
    def unpack(cls, data):
        # Don't override this method. Implement your logic inside __init__.

        # support unpacking with and without header
        if len(data) == struct.calcsize(cls._struct) + 4:
            # header present, unpack it
            extra_field_id, extra_field_size = struct.unpack('<HH', data[:4])
            if extra_field_id != cls.extra_field_id:
                raise ValueError(
                    f"invalid header, expected {cls.extra_field_id!r}, got {extra_field_id}")
            if extra_field_size != len(data):
                raise ValueError(
                    f"invalid header, {extra_field_size=} but {len(data)=}")
            data = data[4:]
        return cls(*struct.unpack(cls._struct, data))

    def pack(self):
        # It is ok to override this method.

        # always pack the extra field with its header
        return struct.pack('<HH' + self._struct.removeprefix('<'),
            self.extra_field_id,
            struct.calcsize(self._struct),
            *(
                getattr(self, field.name)
                for field in dataclasses.fields(self)
            ),
        )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        other_cls = cls._registry.setdefault(cls.extra_field_id, cls)
        assert other_cls is cls, \
            f"conflicting classes for {cls.extra_field_id!r}: {other_cls} vs {cls}"


def _parse_extra_fields(data: bytes) -> dict[ExtraFieldId | int, _ExtraField | bytes]:
    # A field is a header with type (2 bytes), length (2 bytes) and the
    # actual data ({length} bytes). Parsing the extra field is delegated
    # to the concrete _ExtraField class for {type} (or left as bytes if
    # no concrete class exists).
    buffer = io.BytesIO(data)
    extra_fields = {}
    while buffer.tell() < len(data):
        id_, size = struct.unpack('<HH', buffer.read(4))
        if buffer.tell() + size > len(data):
            raise ValueError(
                f"invalid header, expected {size} bytes, but only {len(data) - size} bytes remaining")
        extra_field = buffer.read(size)
        try:
            id_ = ExtraFieldId(id_)
            ExtraField = _ExtraField._registry[id_]
        except (KeyError, ValueError):
            extra_fields[id_] = extra_field
        else:
            extra_fields[id_] = ExtraField.unpack(extra_field)
    return extra_fields


def _serialize_extra_fields(
    dico: dict[ExtraFieldId | int, _ExtraField | bytes],
) -> bytes:
    out = []
    for id_, item in dico.items():
        match item:
            case _ExtraField():
                data = item.pack()
            case bytes():
                data = item
            case e:
                raise TypeError(e)
        out.append(struct.pack('<HH', id_, len(data)))
        out.append(data)
    return b''.join(out)


@dataclasses.dataclass
class Zip64(_ExtraField):
    extra_field_id = ExtraFieldId.ZIP64  # noqa: RUF045
    _struct = '<QQQI'

    original_size: int
    compressed_size: int
    offset: int
    disk_no: int


@dataclasses.dataclass
class DataDescriptor:
    _struct = '<4sIII'
    _struct_64 = '<4sIQQ'

    signature = b'PK\7\x08'  # noqa: RUF045
    crc32: int
    compressed_size: int
    uncompressed_size: int

    def pack(self, zip64=None):
        if zip64 is None:
            zip64 = self.uncompressed_size > 0xFF_FF_FF_FF
        return struct.pack(self._struct_64 if zip64 else self._struct,
            self.signature,
            self.crc32,
            self.compressed_size,
            self.uncompressed_size,
        )

    @classmethod
    def unpack(cls, data, zip64=False):
        dd_struct = cls._struct_64 if zip64 else cls._struct
        if len(data) == struct.calcsize(dd_struct) - 4:
            data = cls.signature + data
        sign, crc32, csize, usize = struct.unpack(dd_struct, data)
        if sign != cls.signature:
            raise ValueError(
                f"invalid data descriptor, exptected {cls.signature!r}, got {sign}")
        return cls(crc32, csize, usize)


@dataclasses.dataclass
class LocalFileHeader:
    _struct = '<4sHHHHHIIIHH'
    _length = struct.calcsize(_struct)

    signature = b'PK\3\4'  # noqa: RUF045
    version: int
    flags: Flags
    compression: CompressionMethod
    modification: dt.datetime
    crc32: int
    compressed_size: int
    uncompressed_size: int
    filename: str
    extra_fields: dict[ExtraFieldId | int, _ExtraField | bytes]

    def pack(self, *, encoding='ascii'):
        filename = self.filename.encode(
            'utf-8' if self.flags & Flags.UNICODE_FILENAME else encoding)
        extra_fields = _serialize_extra_fields(self.extra_fields)
        return struct.pack(self._struct,
            self.signature,
            self.version,
            self.flags,
            self.compression,
            *serialize_time_date(self.modification),
            self.crc32,
            self.compressed_size,
            self.uncompressed_size,
            len(filename),
            len(extra_fields),
        ) + filename + extra_fields

    @classmethod
    def unpack(cls, file_header, *, encoding='ascii'):
        buffer = io.BytesIO(file_header)
        (
            signature,
            version,
            flags,
            compression,
            modtime,
            moddate,
            crc32,
            compressed_size,
            uncompressed_size,
            filename_len,
            extra_fields_len,
        ) = struct.unpack(cls._struct, buffer.read(cls._length))

        if signature != cls.signature:
            raise ValueError(
                f"invalid header, expected {cls.signature}, got {signature}")
        if len(file_header) != (cls._length + filename_len + extra_fields_len):
            raise ValueError(
                f"invalid header, expected {cls._length+filename_len+extra_fields_len=} bytes where cls._length=struct.calcsize({cls._struct})={cls._length} {filename_len=} {extra_fields_len=}, got {len(file_header)=} bytes")  # noqa: E226

        flags = Flags(flags)
        return cls(
            version=version,
            flags=flags,
            compression=CompressionMethod(compression),
            modification=deserialize_time_date(modtime, moddate),
            crc32=crc32,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            filename=buffer.read(filename_len).decode(
                'utf-8' if flags & Flags.UNICODE_FILENAME else encoding),
            extra_fields=_parse_extra_fields(buffer.read(extra_fields_len)),
        )


@dataclasses.dataclass
class CentralDirectoryFileHeader:
    _struct = '<4sBBHHHHHIIIHHHHHII'
    _length = struct.calcsize(_struct)

    signature = b'PK\1\2'  # noqa: RUF045
    version_os: OS
    version_zip: Version
    version_needed: Version
    flags: Flags
    compression: CompressionMethod
    modification: dt.datetime
    crc32: int
    compressed_size: int
    uncompressed_size: int
    disk_no: int
    internal_attribute: int
    external_attribute: int
    local_header_offset: int
    filename: str
    extra_fields: dict[ExtraFieldId | int, _ExtraField | bytes]
    comment: str

    def pack(self, *, encoding='ascii'):
        filename = self.filename.encode(
            'utf-8' if self.flags & Flags.UNICODE_FILENAME else encoding)
        comment = self.comment.encode(
            'utf-8' if self.flags & Flags.UNICODE_FILENAME else encoding)
        extra_fields = _serialize_extra_fields(self.extra_fields)
        return struct.pack(self._struct,
            self.signature,
            self.version_os,
            self.version_zip,
            self.version_needed,
            self.flags,
            self.compression,
            *serialize_time_date(self.modification),
            self.crc32,
            self.compressed_size,
            self.uncompressed_size,
            len(filename),
            len(extra_fields),
            len(comment),
            self.disk_no,
            self.internal_attribute,
            self.external_attribute,
            self.local_header_offset,
        ) + filename + extra_fields + comment

    @classmethod
    def unpack(cls, cd_file_header, *, encoding='ascii'):
        buffer = io.BytesIO(cd_file_header)
        (
            signature,
            version_os,
            version_zip,
            version_needed,
            flags,
            compression,
            modtime,
            moddate,
            crc32,
            compressed_size,
            uncompressed_size,
            filename_len,
            extra_fields_len,
            comment_len,
            disk_no,
            internal_attribute,
            external_attribute,
            local_header_offset,
        ) = struct.unpack(cls._struct, buffer.read(cls._length))

        if signature != cls.signature:
            raise ValueError(
                f"invalid header, expected {cls.signature}, got {signature}")
        if len(cd_file_header) != (cls._length + filename_len + extra_fields_len + comment_len):
            raise ValueError(
                f"invalid header, expected {cls._length+filename_len+extra_fields_len+comment_len=} bytes where cls._length=struct.calcsize({cls._struct})={cls._length} {filename_len=} {extra_fields_len=} {comment_len=}, got {len(cd_file_header)=} bytes")  # noqa: E226

        flags = Flags(flags)
        return cls(
            version_os=OS(version_os),
            version_zip=Version(version_zip),
            version_needed=Version(version_needed),
            flags=flags,
            compression=CompressionMethod(compression),
            modification=deserialize_time_date(modtime, moddate),
            crc32=crc32,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            disk_no=disk_no,
            internal_attribute=internal_attribute,
            external_attribute=external_attribute,
            local_header_offset=local_header_offset,
            filename=buffer.read(filename_len).decode(
                'utf-8' if flags & Flags.UNICODE_FILENAME else encoding),
            extra_fields=_parse_extra_fields(buffer.read(extra_fields_len)),
            comment=buffer.read(comment_len).decode(
                'utf-8' if flags & Flags.UNICODE_FILENAME else encoding),
        )


@dataclasses.dataclass
class EndOfCentralDirectory64:
    _struct = '<4sQBBHIIQQQQ'
    _length = struct.calcsize(_struct)
    _length_header = struct.calcsize('<4sQ')

    signature = b'PK\6\6'  # noqa: RUF045
    version_os: OS
    version_zip: Version
    version_needed: Version
    disk_no: int
    central_directory_disk_no: int
    central_directory_disk_entries_count: int
    central_directory_total_entries_count: int
    central_directory_size: int
    central_directory_offset: int
    comment: str

    @classmethod
    def unpack(cls, eocd, encoding='utf-8'):
        signature, size, *fields = struct.unpack(cls._struct, eocd[:cls._length])
        if signature != cls.signature:
            raise ValueError(
                f"invalid header, expected {cls.signature}, got {signature}")
        if len(eocd) != size + cls._length_header:
            raise ValueError(
                f"invalid header, expected {size} bytes, got {len(eocd)=} bytes")
        comment = eocd[cls._length:].decode(encoding)
        return cls(*fields, comment)

    def pack(self, encoding='utf-8'):
        return struct.pack(self._struct,
            self.signature,
            self._length + len(self.comment) - self._length_header,
            self.version_os,
            self.version_needed,
            self.disk_no,
            self.central_directory_disk_no,
            self.central_directory_disk_entries_count,
            self.central_directory_total_entries_count,
            self.central_directory_size,
            self.central_directory_offset,
        ) + self.comment.encode(encoding)


@dataclasses.dataclass
class EndOfCentralDirectoryLocator:
    _struct = '<4sIQI'
    _length = struct.calcsize(_struct)

    signature = b'PK\6\7'  # noqa: RUF045
    central_directory64_disk_no: int
    central_directory64_offset: int
    total_disk_count: int

    @classmethod
    def unpack(cls, eocdl):
        signature, *fields = struct.unpack(cls._struct, eocdl)
        if signature != cls.signature:
            pass
        return cls(*fields)

    def pack(self):
        return struct.pack(self.struct,
            self.signature,
            self.central_directory64_disk_no,
            self.central_directory64_offset,
            self.total_disk_count,
        )


@dataclasses.dataclass
class EndOfCentralDirectory:
    _struct = '<4sHHHHIIH'
    _length = struct.calcsize(_struct)

    signature = b'PK\5\6'  # noqa: RUF045
    disk_no: int
    central_directory_disk_no: int
    central_directory_disk_entries_count: int
    central_directory_total_entries_count: int
    central_directory_size: int
    central_directory_offset: int
    comment: bytes

    @classmethod
    def unpack(cls, eocd):
        signature, *fields, comment_len = struct.unpack(cls._struct, eocd[:cls._length])
        if signature != cls.signature:
            raise ValueError(
                f"invalid header, expected {cls.signature}, got {signature}")
        if len(eocd) != (cls._length + comment_len):
            raise ValueError(
                f"invalid header, expected {cls._length+comment_len=} bytes where cls._length=struct.calcsize({cls._struct})={cls._length} {comment_len=}, got {len(eocd)=} bytes")  # noqa: E226
        return cls(*fields, eocd[cls._length:])

    def pack(self):
        return struct.pack(self._struct,
            self.signature,
            self.disk_no,
            self.central_directory_disk_no,
            self.central_directory_disk_entries_count,
            self.central_directory_total_entries_count,
            self.central_directory_size,
            self.central_directory_offset,
            len(self.comment),
        ) + self.comment
