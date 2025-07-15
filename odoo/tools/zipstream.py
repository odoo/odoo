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


FILE_HEADER_STRUCT = '<4sHHHHHIIIHH'
FILE_HEADER_LENGTH = struct.calcsize(FILE_HEADER_STRUCT)

DATA_DESCRIPTOR_STRUCT = '<4sIII'
DATA_DESCRIPTOR_LENGTH = struct.calcsize(DATA_DESCRIPTOR_STRUCT)


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
    encrypted_file: bool
    compression_option1: bool
    compression_option2: bool
    data_descriptor: bool
    enhanced_deflation: bool
    compressed_patched_data: bool
    strong_encryption: bool
    _1: bool = dataclasses.field(repr=False)  # reserved flag
    _2: bool = dataclasses.field(repr=False)  # reserved flag
    _3: bool = dataclasses.field(repr=False)  # reserved flag
    language_encoding: bool
    _4: bool = dataclasses.field(repr=False)  # reserved flag
    mask_header_values: bool
    _5: bool = dataclasses.field(repr=False)  # reserved flag
    _6: bool = dataclasses.field(repr=False)  # reserved flag

    @classmethod
    def unpack(cls, encoded_flags: int):
        bits = bin(encoded_flags).removeprefix('0b').zfill(15)
        return cls(*[bit == '1' for bit in bits])

    def pack(self):
        bits = [
            '1' if getattr(self, field_name) else '0'
            for field_name in dataclasses.fields(self)
        ]
        return int(bits, 2)


@dataclasses.dataclass
class ZipFileHeader:
    signature: bytes
    version: int
    flags: ZipFlags
    compression: CompressionMethod
    modification: datetime.datetime
    crc32: int
    compressed_size: int
    uncompressed_size: int
    filename: bytes
    extra_fields: bytes

    def pack(self):
        raise NotImplementedError

    @classmethod
    def unpack(cls, file_header):
        signature, *headers, filename_len, extra_field_len = list(struct.unpack(
            FILE_HEADER_STRUCT, file_header[:FILE_HEADER_LENGTH]))
        if signature != b'PK\3\4':
            e = "invalid signature"
            raise ValueError(e)
        if len(file_header) != (FILE_HEADER_LENGTH + filename_len + extra_field_len):
            e = "invalid length"
            raise ValueError(e)
        headers[1] = ZipFlags.unpack(headers[1])
        headers[2] = CompressionMethod(headers[2])
        headers[3:5] = [cls.parse_time_date(headers[3], headers[4])]
        filename = file_header[FILE_HEADER_LENGTH:FILE_HEADER_LENGTH + filename_len]
        extra_fields = file_header[FILE_HEADER_LENGTH + filename_len:]
        return cls(signature, *headers, filename, extra_fields)

    @staticmethod
    def parse_time_date(ziptime, zipdate):
        second = (ziptime & 0b11111)
        minute = (ziptime & 0b11111100000) >> 5
        hour = (ziptime & 0b1111100000000000) >> 11
        day = (zipdate & 0b11111)
        month = (zipdate & 0b111100000) >> 5
        year = (zipdate & 0b1111111000000000) >> 9
        return datetime.datetime(1980 + year, month, day, hour, minute, second * 2)

    @property
    def uses_data_descriptor(self):
        return (
            self.flags.data_descriptor
            and not self.crc32
            and not self.uncompressed_size
            and not self.compressed_size
        )


def _find_data_descriptor(data, content_start):
    search_from = content_start
    while True:
        index = data.find(b'PK\x07\x08', search_from)
        if index == -1:
            e = "coun't not find data descriptor"
            raise ValueError(e)
        _, crc32, csize, usize = struct.unpack(
            DATA_DESCRIPTOR_STRUCT,
            data[index:index + DATA_DESCRIPTOR_LENGTH],
        )
        if index - content_start == csize:
            # if proved unreliable, then test the crc32 and verify that
            # b'PK\1\3' or b'PK\3\4' follows too.
            return crc32, csize, usize
        search_from = index + 4


def get_first_file(partial_zip: bytes) -> tuple[ZipFileHeader, bytes]:
    """
    Attempt to locate and read the first file of a partial zip.

    :param partial_zip: Enough bytes from the zip to read the first
        compressed file.
    :returns: a 2-item tuple with the header (filename, size, ...) and
        the compressed content of the first file of the zip.
    :raises ValueError: When it is not a zip, or that there isn't enough
        data available to read the first file in its entirety.
    """
    if not partial_zip.startswith(b'PK\3\4'):
        e = "not a zipfile, or no file in zip"
        raise ValueError(e)
    if len(partial_zip) < FILE_HEADER_LENGTH:
        e = "not enought data to read zipfile header"
        raise ValueError(e)
    *_, filename_len, extra_field_len = struct.unpack(
        FILE_HEADER_STRUCT, partial_zip[:FILE_HEADER_LENGTH])
    if len(partial_zip) < FILE_HEADER_LENGTH + filename_len + extra_field_len:
        e = "not enought data to read zipfile filename and extra fields"
        raise ValueError(e)

    header_len = FILE_HEADER_LENGTH + filename_len + extra_field_len
    header = ZipFileHeader.unpack(partial_zip[:header_len])
    if header.uses_data_descriptor:
        header.crc32, header.compressed_size, header.uncompressed_size = (
            _find_data_descriptor(partial_zip, header_len)
        )

    if header.compressed_size > len(partial_zip) - header_len:
        e = "not enought data"
        raise ValueError(e)
    compressed_content = partial_zip[header_len:header_len + header.compressed_size]

    return (header, compressed_content)


def decompress_file(header: ZipFileHeader, compressed_content: bytes) -> bytes:
    match header.compression:
        case CompressionMethod.NO_COMPRESSION:
            return compressed_content
        case CompressionMethod.DEFLATED if zlib:
            return zlib.decompress(compressed_content, wbits=-15)
        case CompressionMethod.BZIP2 if bz2:
            return bz2.decompress(compressed_content)
        case CompressionMethod.LZMA if lzma:
            return lzma.decompress(compressed_content)
        case compression:
            e = f"can't decompress {compression}"
            raise ValueError(e)
