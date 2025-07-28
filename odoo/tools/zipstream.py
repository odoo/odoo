# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Utilities to work with partial zip files.

The zipfile library found in the python standard library only work with
full zipfile, i.e. the entire zipfile must be created/loaded in memory.

There are situations where we don't want to load the entire thing in
memory, e.g. to craft a zipfile out of many large file and to send it
over the network.
"""

import dataclasses
import datetime
import enum
import io
import struct

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


DEFAULT_VERSION = 20
ZIP64_VERSION = 45


@dataclasses.dataclass
class ZipDataDescriptor:
    _signature = b'PK\7\x08'
    _struct = '<4sIII'
    _struct_64 = '<4sIQQ'

    crc32: int
    compressed_size: int
    uncompressed_size: int

    def pack(self, zip64=None):
        if zip64 is None:
            zip64 = self.uncompressed_size > 0xFF_FF_FF_FF
        return struct.pack(
            self._struct_64 if zip64 else self._struct,
            self._signature,
            self.crc32,
            self.compressed_size,
            self.uncompressed_size,
        )

    @classmethod
    def unpack(cls, data, zip64=False):
        dd_struct = cls._struct_64 if zip64 else cls._struct
        if len(data) == struct.calcsize(dd_struct) - 4:
            data = cls._signature + data
        sign, crc32, csize, usize = struct.unpack(dd_struct, data)
        if sign != cls._signature:
            raise ValueError
        return cls(crc32, csize, usize)


@dataclasses.dataclass
class ZipLocalFileHeader:
    _signature = b'PK\3\4'
    _struct = '<4sHHHHHIIIHH'
    _length = struct.calcsize(_struct)

    signature: bytes
    version: int
    flags: 'ZipFlags'
    compression: 'CompressionMethod'
    modification: datetime.datetime
    crc32: int
    compressed_size: int
    uncompressed_size: int
    filename: bytes
    extra_fields: dict['ExtraFieldId', '_ExtraField | bytes']

    def pack(self):
        extra_fields = b''.join([ef.pack() for ef in self.extra_fields])
        return struct.pack(
            self._struct,
            self._signature,
            self.version,
            self.flags.pack(),
            self.compression,
            *self.format_time_date(self.modification),
            self.crc32,
            self.compressed_size,
            self.uncompressed_size,
            len(self.filename),
            len(extra_fields),
        ) + self.filename + extra_fields

    @classmethod
    def unpack(cls, file_header):
        signature, *headers, filename_len, extra_fields_len = list(struct.unpack(
            cls._struct, file_header[:cls._length]))
        if signature != cls._signature:
            e = "invalid signature"
            raise ValueError(e)
        if len(file_header) != (cls._length + filename_len + extra_fields_len):
            e = "invalid length"
            raise ValueError(e)
        headers[1] = ZipFlags.unpack(headers[1])
        headers[2] = CompressionMethod(headers[2])
        headers[3:5] = [cls.parse_time_date(headers[3], headers[4])]
        filename = file_header[cls._length:cls._length + filename_len]
        extra_fields_data = file_header[cls._length + filename_len:]

        i = 0
        extra_fields = {}
        while i < extra_fields_len:
            id_, size = struct.unpack('HH', extra_fields_data[i:i + 4])
            extra_field = extra_fields[i:i + size]
            extra_fields[id_] = (
                extra_field_cls.unpack(extra_field)
                if (extra_field_cls := _ExtraField._registry.get(id_)) else
                extra_field
            )
            i += 4 + size

        return cls(signature, *headers, filename, extra_fields)

    @staticmethod
    def parse_time_date(ziptime: int, zipdate: int) -> datetime.datetime:
        second = (ziptime & 0b11111)
        minute = (ziptime & 0b11111100000) >> 5
        hour = (ziptime & 0b1111100000000000) >> 11
        day = (zipdate & 0b11111)
        month = (zipdate & 0b111100000) >> 5
        year = (zipdate & 0b1111111000000000) >> 9
        return datetime.datetime(1980 + year, month, day, hour, minute, second * 2)

    @staticmethod
    def format_time_date(dt: datetime.datetime) -> tuple[int, int]:
        ziptime = dt.second // 2 + (dt.minute << 5) + (dt.hour << 11)
        zipdate = dt.day + (dt.month << 5) + (dt.year << 9)
        return (ziptime, zipdate)


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


@dataclasses.dataclass
class ZipFlags:
    encrypted_file: bool = False
    compression_option1: bool = False
    compression_option2: bool = False
    data_descriptor: bool = False
    enhanced_deflation: bool = False
    compressed_patched_data: bool = False
    strong_encryption: bool = False
    _1: bool = dataclasses.field(default=False, repr=False)  # reserved flag
    _2: bool = dataclasses.field(default=False, repr=False)  # reserved flag
    _3: bool = dataclasses.field(default=False, repr=False)  # reserved flag
    language_encoding: bool = False
    _4: bool = dataclasses.field(default=False, repr=False)  # reserved flag
    mask_header_values: bool = False
    _5: bool = dataclasses.field(default=False, repr=False)  # reserved flag
    _6: bool = dataclasses.field(default=False, repr=False)  # reserved flag

    @classmethod
    def unpack(cls, encoded_flags: int):
        bits = bin(encoded_flags).removeprefix('0b').zfill(15)
        return cls(*[bit == '1' for bit in bits])

    def pack(self):
        bits = [
            '1' if getattr(self, field.name) else '0'
            for field in dataclasses.fields(self)
        ]
        return int(''.join(bits), 2)


class ExtraFieldId(enum.IntEnum):
    ZIP64 = 0x0001


class _ExtraField:
    _registry = {}
    id: ExtraFieldId

    @classmethod
    def unpack(cls, data):
        id_, _size, *args = struct.unpack(cls._struct, data)
        assert id_ == cls.id
        return cls(*args)

    def pack(self):
        return struct.pack(
            self._struct,
            self.id,
            self._struct_size - 4,
            *(
                getattr(self, field.name)
                for field in dataclasses.fields(self)
            ),
        )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if _ExtraField in cls.__bases__:
            cls._registry[cls.id] = cls


@dataclasses.dataclass
class _Zip64(_ExtraField):
    id = ExtraFieldId.ZIP64
    _struct = 'HHQQQI'
    _struct_size = struct.calcsize(_struct)

    original_size: int
    compressed_size: int
    relative_header_offset: int
    disk_start: int


def write(attachments):
    pos = 0

    def send(chunk):
        nonlocal pos
        pos += len(chunk)
        return chunk

    for att in attachments:
        need_zip64 = att.file_size > 0xFF_FF_FF_FF

        # assume non-text mimetypes are compressed already
        compression = (
            CompressionMethod.DEFLATED
            if (att.mimetype or '').startswith('text/') else
            CompressionMethod.NO_COMPRESSION
        )

        extra_fields = {}
        if need_zip64:
            extra_fields[ExtraFieldId.ZIP64] = _Zip64(
                original_size=0,
                compressed_size=0,
                relative_header_offset=0,
                disk_start=0,
            )

        local_file_header = ZipLocalFileHeader(
            ZipLocalFileHeader._signature,
            version=45 if need_zip64 else 20,
            flags=ZipFlags(
                data_descriptor=True,
            ),
            compression=compression,
            modification=att.write_date,
            crc32=0,
            compressed_size=0,
            uncompressed_size=0,
            filename=att.name,
            extra_fields=extra_fields,
        )
        yield send(local_file_header.pack())

        crc32 = 0
        if compression:
            compress = zlib.compressobj(wbits=-15)
            compressed_size = 0

        path = werkzeug.security.safe_join(
            os.path.abspath(config.filestore(att.env.cr.dbname)),
            att.store_fname)
        with open(path, 'rb') as file:
            while chunk := file.read(io.DEFAULT_BUFFER_SIZE):
                crc32 = zlib.crc32(chunk, crc32)
                if compression:
                    chunk = compress.compress(chunk)
                    compressed_size += len(chunk)
                yield send(chunk)

        yield send(struct.pack(
            '<4sIQQ' if need_zip64 else '<4sIII',
            b'PK\7\x08',
            crc32,
            compressed_size if compression else att.file_size,
            att.file_size,
        ))

    # TODO: central directory
    ...
