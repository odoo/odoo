# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Utilities to work with partial zip files.

The zipfile library found in the python standard library only work with
full zipfile, i.e. the entire zipfile must be created/loaded in memory.

There are situations where we don't want to load the entire thing in
memory, e.g. to craft a zipfile out of many large file and to send it
over the network.
"""
# https://pkwaredownloads.blob.core.windows.net/pkware-general/Documentation/APPNOTE-6.3.9.TXT

import dataclasses
import datetime
import enum
import io
import itertools
import struct
from collections.abc import Generator, Iterable, Mapping
from functools import partial
from pathlib import Path

try:
    from .mimetypes import is_mimetype_textual
except ImportError:
    def is_mimetype_textual(mimetype):
        maintype, subtype = mimetype.split('/')
        return (
            maintype == 'text'
            or (maintype == 'application' and subtype in {'documents-email', 'json', 'xml'})
        )

try:
    import zlib
except ImportError:
    zlib = None

try:
    import bz2
except ImportError:
    bz2 = None

try:
    import lzma
except ImportError:
    lzma = None

MAX_INT32 = 0xFF_FF_FF_FF  # 4GiB - 1


def serialize_time_date(dt: datetime.datetime) -> tuple[int, int]:
    ziptime = dt.second // 2 + (dt.minute << 5) + (dt.hour << 11)
    zipdate = (dt.day - 1) + ((dt.month - 1) << 5) + ((dt.year - 1980) << 9)
    return (ziptime, zipdate)


def deserialize_time_date(ziptime: int, zipdate: int) -> datetime.datetime:
    second = (ziptime & 0b11111)
    minute = (ziptime & 0b11111100000) >> 5
    hour = (ziptime & 0b1111100000000000) >> 11
    day = (zipdate & 0b11111)
    month = (zipdate & 0b111100000) >> 5
    year = (zipdate & 0b1111111000000000) >> 9
    try:
        return datetime.datetime(1980 + year, month + 1, day + 1, hour, minute, second * 2)
    except ValueError as exc:
        exc.add_note(str((1980 + year, month + 1, day + 1, hour, minute, second * 2)))
        raise


class OS(enum.IntEnum):
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
    DEFAULT = 20
    ZIP64 = 45
    UNICODE_FILENAME = 63


class InternalAttribute(enum.IntFlag, boundary=enum.FlagBoundary.KEEP):
    TEXT = 1 << 0
    CONTROL_FIELD_RECORDS_PRECEDE_LOGICAL_RECORDS = 1 << 2


class CompressionMethod(enum.IntEnum):
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


if zlib:
    CompressionMethod.DEFLATED.compressor = partial(zlib.compressobj, wbits=-15)
    CompressionMethod.DEFLATED.decompressor = partial(zlib.decompressobj, wbits=-15)
if bz2:
    CompressionMethod.BZIP2.compressor = bz2.BZ2Compressor
    CompressionMethod.BZIP2.decompressor = bz2.BZ2Decompressor
if lzma:
    CompressionMethod.LZMA.compressor = lzma.LZMACompressor
    CompressionMethod.LZMA.decompressor = lzma.LZMADecompressor


class Flags(enum.IntFlag, boundary=enum.FlagBoundary.KEEP):
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
    ZIP64 = 0x0001


class _ExtraField:
    _registry = {}

    _struct: bytes
    _length: int
    extra_field_id: ExtraFieldId

    @classmethod
    def unpack(cls, data):
        # support unpacking with and without header
        if len(data) == cls._length + 4:
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
class _Zip64(_ExtraField):
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
    modification: datetime.datetime
    crc32: int
    compressed_size: int
    uncompressed_size: int
    filename: bytes
    extra_fields: dict[ExtraFieldId | int, _ExtraField | bytes]

    def pack(self):
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
            len(self.filename),
            len(extra_fields),
        ) + self.filename + extra_fields

    @classmethod
    def unpack(cls, file_header):
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

        return cls(
            version=version,
            flags=Flags(flags),
            compression=CompressionMethod(compression),
            modification=deserialize_time_date(moddate, modtime),
            crc32=crc32,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            filename=buffer.read(filename_len),
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
    modification: datetime.datetime
    crc32: int
    compressed_size: int
    uncompressed_size: int
    disk_no: int
    internal_attribute: int
    external_attribute: int
    local_header_offset: int
    filename: bytes
    extra_fields: dict['ExtraFieldId | int', '_ExtraField | bytes']
    comment: bytes

    def pack(self):
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
            len(self.filename),
            len(extra_fields),
            len(self.comment),
            self.disk_no,
            self.internal_attribute,
            self.external_attribute,
            self.local_header_offset,
        ) + self.filename + extra_fields + self.comment

    @classmethod
    def unpack(cls, cd_file_header):
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

        return cls(
            version_os=OS(version_os),
            version_zip=Version(version_zip),
            version_needed=Version(version_needed),
            flags=Flags(flags),
            compression=CompressionMethod(compression),
            modification=deserialize_time_date(modtime, moddate),
            crc32=crc32,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            disk_no=disk_no,
            internal_attribute=internal_attribute,
            external_attribute=external_attribute,
            local_header_offset=local_header_offset,
            filename=buffer.read(filename_len),
            extra_fields=_parse_extra_fields(buffer.read(extra_fields_len)),
            comment=buffer.read(comment_len),
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
    comment: bytes

    @classmethod
    def unpack(cls, eocd):
        signature, size, *fields = struct.unpack(cls._struct, eocd[:cls._length])
        if signature != cls.signature:
            raise ValueError(
                f"invalid header, expected {cls.signature}, got {signature}")
        if len(eocd) != size + cls._length_header:
            raise ValueError(
                f"invalid header, expected {size} bytes, got {len(eocd)=} bytes")
        comment = eocd[cls._length:]
        return cls(*fields, comment)

    def pack(self):
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
        ) + self.comment


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


class _DirectoryItem:
    def __init__(self, attachment, offset):
        self.attachment = attachment
        self.offset = offset
        self.local_file_header = None
        self.data_descriptor = None

    def __iter__(self):
        return iter((
            self.attachment,
            self.offset,
            self.local_file_header,
            self.data_descriptor,
        ))


class _Flat(Mapping):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return ''

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError


def write(
    filestore: str,
    attachments: Iterable,
    folders: Mapping[int, str] = _Flat(),
) -> Generator[bytes]:
    directory: list[_DirectoryItem] = []
    offset = 0

    def send(chunk):
        nonlocal offset
        offset += len(chunk)
        return chunk

    for attach in attachments:
        directory.append(_DirectoryItem(attach, offset))
        att_path = Path(filestore).joinpath(attach.store_fname)
        filename = (folders[attach.id].rstrip('/') + '/' + attach.name.strip('/')).encode()

        flags = Flags.DATA_DESCRIPTOR
        need_zip64 = attach.file_size > MAX_INT32
        try:
            filename.decode('ascii')
        except UnicodeDecodeError:
            version_needed = Version.UNICODE_FILENAME
            flags |= Flags.UNICODE_FILENAME
        else:
            version_needed = Version.ZIP64 if need_zip64 else Version.DEFAULT

        # assume non-text mimetypes are compressed already
        compression = (
            CompressionMethod.DEFLATED
            if is_mimetype_textual(attach.mimetype) else
            CompressionMethod.NO_COMPRESSION  # 0, falsy
        )
        extra_fields = {}

        if need_zip64:
            extra_fields[ExtraFieldId.ZIP64] = _Zip64(
                original_size=0,  # found in data descriptor
                compressed_size=0,  # found in data descriptor
                offset=directory[-1].offset,
                disk_no=0,
            )

        directory[-1].local_file_header = LocalFileHeader(
            version=version_needed,
            flags=flags,
            compression=compression,
            modification=attach.write_date,
            crc32=0,  # found in data descriptor
            compressed_size=0,  # found in data descriptor
            uncompressed_size=0,  # found in data descriptor
            filename=attach.name.encode(),
            extra_fields=extra_fields,
        )
        yield send(directory[-1].local_file_header.pack())

        crc32 = 0
        if compression:
            compressor = compression.compressor()
            compressed_size = 0

        with att_path.open('rb') as file:
            while chunk := file.read(io.DEFAULT_BUFFER_SIZE):
                crc32 = zlib.crc32(chunk, crc32)
                if compression:
                    chunk = compressor.compress(chunk)
                    compressed_size += len(chunk)
                yield send(chunk)
            if compression:
                chunk = compressor.flush()
                compressed_size += chunk
                yield send(chunk)

        directory[-1].data_descriptor = DataDescriptor(
            crc32,
            compressed_size if compression else attach.file_size,
            attach.file_size,
        )
        yield send(directory[-1].data_descriptor.pack(zip64=need_zip64))

    # Central directory
    pos_central_directory = offset
    for attachment, local_header_offset, local_file_header, data_descriptor in directory:
        crc32 = (data_descriptor or local_file_header).crc32
        compressed_size = (data_descriptor or local_file_header).compressed_size
        uncompressed_size = (data_descriptor or local_file_header).uncompressed_size
        zip64 = local_file_header.extra_fields.get(ExtraFieldId.ZIP64)
        if zip64:
            zip64.original_size = uncompressed_size
            zip64.compressed_size = compressed_size

        yield send(CentralDirectoryFileHeader(
            version_os=OS.UNIX,
            version_zip=Version.UNICODE_FILENAME,
            version_needed=local_file_header.version,
            flags=local_file_header.flags,
            compression=local_file_header.compression,
            modification=local_file_header.modification,
            crc32=(data_descriptor or local_file_header).crc32,
            compressed_size=MAX_INT32 if zip64 else compressed_size,
            uncompressed_size=MAX_INT32 if zip64 else uncompressed_size,
            disk_no=0xFF_FF if zip64 else 0,
            internal_attribute=(
                InternalAttribute.TEXT if local_file_header.compression else 0
            ),
            external_attribute=0,
            local_header_offset=MAX_INT32 if need_zip64 else local_header_offset,
            filename=local_file_header.filename,
            extra_fields=local_file_header.extra_fields,
            comment=b'',
        ).pack())

    central_directory_length = offset - pos_central_directory
    if any(
        ExtraFieldId.ZIP64 in item.local_file_header.extra_fields
        for item in directory
    ):
        yield send(EndOfCentralDirectory64(
            version_os=OS.UNIX,
            version_zip=Version.UNICODE_FILENAME,
            version_needed=Version.UNICODE_FILENAME,
            disk_no=0,
            central_directory_disk_no=0,
            central_directory_disk_entries_count=len(directory),
            central_directory_total_entries_count=len(directory),
            central_directory_size=central_directory_length,
            central_directory_offset=pos_central_directory,
            comment=b'',
        ).pack())
        yield send(EndOfCentralDirectoryLocator(
            central_directory64_disk_no=0,
            central_directory64_offset=offset,
            total_disk_count=1,
        ))

    yield send(EndOfCentralDirectory(
        disk_no=0,
        central_directory_disk_no=0,
        central_directory_disk_entries_count=len(directory),
        central_directory_total_entries_count=len(directory),
        central_directory_size=central_directory_length,
        central_directory_offset=pos_central_directory,
        comment=b'',
    ).pack())


def _read_file(local_file_header, _read_buffer):
    zip64 = local_file_header.extra_fields.get(ExtraFieldId.ZIP64)
    csize = (zip64 or local_file_header).compressed_size
    expected_usize = (zip64 or local_file_header).uncompressed_size
    if local_file_header.compression:
        decompressor = local_file_header.compression.decompressor()

    crc32 = 0
    usize = 0
    d, m = divmod(csize, io.DEFAULT_BUFFER_SIZE)
    for i in range(d + bool(m)):
        chunk_size = m if i == d else io.DEFAULT_BUFFER_SIZE
        csize += chunk_size
        chunk = _read_buffer(chunk_size)
        if len(chunk) != chunk_size:
            raise ValueError(  # noqa: TRY301
                "unexpected end of file")  # noqa: EM101
        if local_file_header.compression:
            chunk = decompressor.decompress(chunk)
        crc32 = zlib.crc32(chunk, crc32)
        usize += len(chunk)
        yield chunk
    if local_file_header.compression:
        # flush the decompressor
        chunk = decompressor.decompress(b'')
        if hasattr(decompressor, 'flush'):
            chunk += decompressor.flush()
        if not decompressor.eof:
            raise ValueError(  # noqa: TRY301
                f"expected end of file, but found {len(decompressor.unused_data)} remaining bytes: {decompressor.unused_data}")
        if chunk:
            crc32 = zlib.crc32(chunk, crc32)
            usize += len(chunk)
            yield chunk

    if usize != expected_usize:
        raise ValueError(  # noqa: TRY301
            f"invalid uncompressed size: {usize=} != {expected_usize=}")
    if crc32 != local_file_header.crc32:
        raise ValueError(  # noqa: TRY301
            f"invalid crc32: {crc32=} != {local_file_header.crc32=}")

    yield b''  # empty byte to signal end of file


def _read_until_next_file(local_file_header, _read_buffer, _read_into):  # noqa: RET503
    if local_file_header.filename == b'docProps/core.xml':
        pass
    zip64 = ExtraFieldId.ZIP64 in local_file_header.extra_fields
    dd_sign = DataDescriptor.signature
    dd_struct = '<IQQ' if zip64 else '<III'
    dd_length = struct.calcsize(dd_struct)

    crc32 = csize = usize = 0
    if local_file_header.compression:
        dsor = local_file_header.compression.decompressor()

    buffer = bytearray(_read_buffer(io.DEFAULT_BUFFER_SIZE))

    def flush(length):
        nonlocal buffer, crc32, csize, usize

        if dsor:
            with memoryview(buffer)[:length] as mv:
                udata = dsor.decompress(mv)
        else:
            udata = buffer[:length]
        if length:
            buffer[:-length] = buffer[length:]
        csize += length
        usize += len(udata)
        crc32 = zlib.crc32(udata, crc32)
        if udata:
            yield udata

        bytes_read = 0
        while bytes_read < length % len(buffer):
            with memoryview(buffer)[-length + bytes_read:] as mv:
                bytes_read_ = _read_into(mv)
            if not bytes_read_:
                buffer = buffer[:-length + bytes_read]
                break
            bytes_read += bytes_read_

    while True:
        foundpk = buffer.find(b'PK')
        if foundpk == -1:
            assert len(buffer) > dd_length + len(dd_sign)
            yield from flush(len(buffer) - dd_length - len(dd_sign))
            continue
        for signature in (
            LocalFileHeader.signature,
            CentralDirectoryFileHeader.signature,
        ):
            found = buffer.find(signature, foundpk)
            if found != -1:
                break
        else:
            assert len(buffer) > dd_length + len(dd_sign)
            yield from flush(len(buffer) - dd_length - len(dd_sign))
            continue

        expected_crc32, expected_csize, expected_usize = (
            struct.unpack(dd_struct, buffer[found - dd_length:found]))

        if (length := found - dd_length) == expected_csize - csize:
            # dd signature absent
            yield from flush(length)
            if usize != expected_usize or crc32 != expected_crc32:
                yield from flush(dd_length + 4)  # len(b'PK\3\4')
                continue
            buffer = memoryview(buffer)[dd_length:]
        elif (
            (length := found - len(dd_sign) - dd_length) == expected_csize - csize
            and buffer.startswith(dd_sign, length)
        ):
            # dd signature absent
            yield from flush(length)
            if usize != expected_usize or crc32 != expected_crc32:
                yield from flush(len(dd_sign) + dd_length + 4)  # len(b'PK\3\4')
                continue
            buffer = memoryview(buffer)[len(dd_sign) + dd_length:]
        else:
            yield from flush(found + 4)  # len(b'PK\3\4')
            continue

        if dsor:
            yield from flush(0)

        local_file_header.crc32 = crc32
        local_file_header.compressed_size = csize
        local_file_header.uncompressed_size = usize
        yield b''  # signal end of file

        return buffer  # leftover to reinject


def extract(zipfile: io.FileIO) -> Generator[LocalFileHeader | bytes]:
    buffer = None
    fileno = 0
    header = bytearray(LocalFileHeader._length)

    def _read_buffer(n):
        nonlocal buffer
        if buffer is None:
            return zipfile.read(n)
        chunk = buffer.read(n)
        if len(chunk) < n:
            buffer = None
            chunk += zipfile.read(n - len(chunk))
        return chunk

    def _read_into(buff):
        nonlocal buffer
        if buffer is None:
            return zipfile.readinto(buff)
        bytes_read = buffer.readinto(buff)
        if bytes_read < len(buff):
            buffer = None
            bytes_read += zipfile.readinto(memoryview(buff)[bytes_read:])
        return bytes_read

    def reinject(data):
        nonlocal buffer
        if buffer is None:
            buffer = io.BytesIO(leftover)
        else:
            buffer = io.BytesIO(buffer.read() + leftover)

    try:
        while True:
            fileno += 1
            local_file_header = None

            if (_read_into(header) != LocalFileHeader._length
             or not header.startswith(LocalFileHeader.signature)):
                break
            *_, filename_len, extra_fields_len = struct.unpack(LocalFileHeader._struct, header)
            local_file_header = LocalFileHeader.unpack(
                header + _read_buffer(filename_len + extra_fields_len))
            yield local_file_header

            if local_file_header.flags & Flags.DATA_DESCRIPTOR:
                leftover = yield from _read_until_next_file(local_file_header, _read_buffer, _read_into)
                reinject(leftover)
            else:
                yield from _read_file(local_file_header, _read_buffer)

    except Exception as exc:
        e = f"while reading file #{fileno} close to offset {zipfile.tell()}, "
        if local_file_header:
            e += f"file header was: {local_file_header}"
        else:
            e += "couldn't read file header"
        exc.add_note(e)
        raise


def helper(zstream):
    while True:
        try:
            local_file = next(zstream)
            if local_file == b'':
                print("there's a b'' too much!")
                continue
        except StopIteration:
            break
        data = b''.join(itertools.takewhile(b''.__ne__, zstream))
        yield local_file, data


def main():
    # ruff: noqa: PLC0415, T201
    import sys
    import time

    if len(sys.argv) != 3 or '-h' in sys.argv or '--help' in sys.argv:
        sys.exit(f"usage: {sys.argv[0]} <Compress|eXtract> <file>")

    _, mode, filename = sys.argv
    if mode.casefold() in ('c', 'compress'):
        sys.exit("not supported")
    elif mode.casefold() in ('x', 'extract'):
        with open(filename, 'rb') as file:
            zstream = extract(file)
            while True:
                start = time.time()
                try:
                    file = next(zstream)
                except StopIteration:
                    break
                datalen = sum(len(chunk) for chunk in itertools.takewhile(b''.__ne__, zstream))
                stop = time.time()
                print(file)
                print(datalen, "bytes", round(stop - start, 6), "seconds")
    else:
        sys.exit(f"usage: {sys.argv[0]} <Compress|eXtract> <file>")


if __name__ == '__main__':
    # ruff: noqa: PLC0415, T201
    import linecache
    import tracemalloc

    def display_top(snapshot, key_type='lineno', limit=10):
        snapshot = snapshot.filter_traces((
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        ))
        top_stats = snapshot.statistics(key_type, cumulative=True)

        print("\nMemory Summary -- Top %s lines" % limit)
        for index, stat in enumerate(top_stats[:limit], 1):
            frame = stat.traceback[0]
            print("#%s: %s:%s: %.1f KiB"
                  % (index, frame.filename, frame.lineno, stat.size / 1024))
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                print('    %s' % line)

        other = top_stats[limit:]
        if other:
            size = sum(stat.size for stat in other)
            print("%s other: %.1f KiB" % (len(other), size / 1024))
        total = sum(stat.size for stat in top_stats)
        print("Total allocated size: %.1f KiB" % (total / 1024))

    tracemalloc.start()
    main()
    snapshot = tracemalloc.take_snapshot()
    tracemalloc.stop()
    display_top(snapshot)
