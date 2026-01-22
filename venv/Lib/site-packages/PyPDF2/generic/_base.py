# Copyright (c) 2006, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import codecs
import decimal
import hashlib
import re
from binascii import unhexlify
from typing import Any, Callable, Optional, Union

from .._codecs import _pdfdoc_encoding_rev
from .._utils import (
    StreamType,
    b_,
    deprecate_with_replacement,
    hex_str,
    hexencode,
    logger_warning,
    read_non_whitespace,
    read_until_regex,
    str_,
)
from ..errors import STREAM_TRUNCATED_PREMATURELY, PdfReadError, PdfStreamError

__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"


class PdfObject:
    # function for calculating a hash value
    hash_func: Callable[..., "hashlib._Hash"] = hashlib.sha1

    def hash_value_data(self) -> bytes:
        return ("%s" % self).encode()

    def hash_value(self) -> bytes:
        return (
            "%s:%s"
            % (
                self.__class__.__name__,
                self.hash_func(self.hash_value_data()).hexdigest(),
            )
        ).encode()

    def get_object(self) -> Optional["PdfObject"]:
        """Resolve indirect references."""
        return self

    def getObject(self) -> Optional["PdfObject"]:  # pragma: no cover
        deprecate_with_replacement("getObject", "get_object")
        return self.get_object()

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        raise NotImplementedError


class NullObject(PdfObject):
    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        stream.write(b"null")

    @staticmethod
    def read_from_stream(stream: StreamType) -> "NullObject":
        nulltxt = stream.read(4)
        if nulltxt != b"null":
            raise PdfReadError("Could not read Null object")
        return NullObject()

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)

    def __repr__(self) -> str:
        return "NullObject"

    @staticmethod
    def readFromStream(stream: StreamType) -> "NullObject":  # pragma: no cover
        deprecate_with_replacement("readFromStream", "read_from_stream")
        return NullObject.read_from_stream(stream)


class BooleanObject(PdfObject):
    def __init__(self, value: Any) -> None:
        self.value = value

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, BooleanObject):
            return self.value == __o.value
        elif isinstance(__o, bool):
            return self.value == __o
        else:
            return False

    def __repr__(self) -> str:
        return "True" if self.value else "False"

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        if self.value:
            stream.write(b"true")
        else:
            stream.write(b"false")

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)

    @staticmethod
    def read_from_stream(stream: StreamType) -> "BooleanObject":
        word = stream.read(4)
        if word == b"true":
            return BooleanObject(True)
        elif word == b"fals":
            stream.read(1)
            return BooleanObject(False)
        else:
            raise PdfReadError("Could not read Boolean object")

    @staticmethod
    def readFromStream(stream: StreamType) -> "BooleanObject":  # pragma: no cover
        deprecate_with_replacement("readFromStream", "read_from_stream")
        return BooleanObject.read_from_stream(stream)


class IndirectObject(PdfObject):
    def __init__(self, idnum: int, generation: int, pdf: Any) -> None:  # PdfReader
        self.idnum = idnum
        self.generation = generation
        self.pdf = pdf

    def get_object(self) -> Optional[PdfObject]:
        obj = self.pdf.get_object(self)
        if obj is None:
            return None
        return obj.get_object()

    def __repr__(self) -> str:
        return f"IndirectObject({self.idnum!r}, {self.generation!r}, {id(self.pdf)})"

    def __eq__(self, other: Any) -> bool:
        return (
            other is not None
            and isinstance(other, IndirectObject)
            and self.idnum == other.idnum
            and self.generation == other.generation
            and self.pdf is other.pdf
        )

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        stream.write(b_(f"{self.idnum} {self.generation} R"))

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)

    @staticmethod
    def read_from_stream(stream: StreamType, pdf: Any) -> "IndirectObject":  # PdfReader
        idnum = b""
        while True:
            tok = stream.read(1)
            if not tok:
                raise PdfStreamError(STREAM_TRUNCATED_PREMATURELY)
            if tok.isspace():
                break
            idnum += tok
        generation = b""
        while True:
            tok = stream.read(1)
            if not tok:
                raise PdfStreamError(STREAM_TRUNCATED_PREMATURELY)
            if tok.isspace():
                if not generation:
                    continue
                break
            generation += tok
        r = read_non_whitespace(stream)
        if r != b"R":
            raise PdfReadError(
                f"Error reading indirect object reference at byte {hex_str(stream.tell())}"
            )
        return IndirectObject(int(idnum), int(generation), pdf)

    @staticmethod
    def readFromStream(
        stream: StreamType, pdf: Any  # PdfReader
    ) -> "IndirectObject":  # pragma: no cover
        deprecate_with_replacement("readFromStream", "read_from_stream")
        return IndirectObject.read_from_stream(stream, pdf)


class FloatObject(decimal.Decimal, PdfObject):
    def __new__(
        cls, value: Union[str, Any] = "0", context: Optional[Any] = None
    ) -> "FloatObject":
        try:
            return decimal.Decimal.__new__(cls, str_(value), context)
        except Exception:
            # If this isn't a valid decimal (happens in malformed PDFs)
            # fallback to 0
            logger_warning(f"FloatObject ({value}) invalid; use 0.0 instead", __name__)
            return decimal.Decimal.__new__(cls, "0.0")

    def __repr__(self) -> str:
        if self == self.to_integral():
            # If this is an integer, format it with no decimal place.
            return str(self.quantize(decimal.Decimal(1)))
        else:
            # Otherwise, format it with a decimal place, taking care to
            # remove any extraneous trailing zeros.
            return f"{self:f}".rstrip("0")

    def as_numeric(self) -> float:
        return float(repr(self).encode("utf8"))

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        stream.write(repr(self).encode("utf8"))

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)


class NumberObject(int, PdfObject):
    NumberPattern = re.compile(b"[^+-.0-9]")

    def __new__(cls, value: Any) -> "NumberObject":
        try:
            return int.__new__(cls, int(value))
        except ValueError:
            logger_warning(f"NumberObject({value}) invalid; use 0 instead", __name__)
            return int.__new__(cls, 0)

    def as_numeric(self) -> int:
        return int(repr(self).encode("utf8"))

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        stream.write(repr(self).encode("utf8"))

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)

    @staticmethod
    def read_from_stream(stream: StreamType) -> Union["NumberObject", FloatObject]:
        num = read_until_regex(stream, NumberObject.NumberPattern)
        if num.find(b".") != -1:
            return FloatObject(num)
        return NumberObject(num)

    @staticmethod
    def readFromStream(
        stream: StreamType,
    ) -> Union["NumberObject", FloatObject]:  # pragma: no cover
        deprecate_with_replacement("readFromStream", "read_from_stream")
        return NumberObject.read_from_stream(stream)


class ByteStringObject(bytes, PdfObject):
    """
    Represents a string object where the text encoding could not be determined.
    This occurs quite often, as the PDF spec doesn't provide an alternate way to
    represent strings -- for example, the encryption data stored in files (like
    /O) is clearly not text, but is still stored in a "String" object.
    """

    @property
    def original_bytes(self) -> bytes:
        """For compatibility with TextStringObject.original_bytes."""
        return self

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        bytearr = self
        if encryption_key:
            from .._security import RC4_encrypt

            bytearr = RC4_encrypt(encryption_key, bytearr)  # type: ignore
        stream.write(b"<")
        stream.write(hexencode(bytearr))
        stream.write(b">")

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)


class TextStringObject(str, PdfObject):
    """
    Represents a string object that has been decoded into a real unicode string.
    If read from a PDF document, this string appeared to match the
    PDFDocEncoding, or contained a UTF-16BE BOM mark to cause UTF-16 decoding to
    occur.
    """

    autodetect_pdfdocencoding = False
    autodetect_utf16 = False

    @property
    def original_bytes(self) -> bytes:
        """
        It is occasionally possible that a text string object gets created where
        a byte string object was expected due to the autodetection mechanism --
        if that occurs, this "original_bytes" property can be used to
        back-calculate what the original encoded bytes were.
        """
        return self.get_original_bytes()

    def get_original_bytes(self) -> bytes:
        # We're a text string object, but the library is trying to get our raw
        # bytes.  This can happen if we auto-detected this string as text, but
        # we were wrong.  It's pretty common.  Return the original bytes that
        # would have been used to create this object, based upon the autodetect
        # method.
        if self.autodetect_utf16:
            return codecs.BOM_UTF16_BE + self.encode("utf-16be")
        elif self.autodetect_pdfdocencoding:
            return encode_pdfdocencoding(self)
        else:
            raise Exception("no information about original bytes")

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        # Try to write the string out as a PDFDocEncoding encoded string.  It's
        # nicer to look at in the PDF file.  Sadly, we take a performance hit
        # here for trying...
        try:
            bytearr = encode_pdfdocencoding(self)
        except UnicodeEncodeError:
            bytearr = codecs.BOM_UTF16_BE + self.encode("utf-16be")
        if encryption_key:
            from .._security import RC4_encrypt

            bytearr = RC4_encrypt(encryption_key, bytearr)
            obj = ByteStringObject(bytearr)
            obj.write_to_stream(stream, None)
        else:
            stream.write(b"(")
            for c in bytearr:
                if not chr(c).isalnum() and c != b" ":
                    # This:
                    #   stream.write(b_(rf"\{c:0>3o}"))
                    # gives
                    #   https://github.com/davidhalter/parso/issues/207
                    stream.write(b_("\\%03o" % c))
                else:
                    stream.write(b_(chr(c)))
            stream.write(b")")

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)


class NameObject(str, PdfObject):
    delimiter_pattern = re.compile(rb"\s+|[\(\)<>\[\]{}/%]")
    surfix = b"/"
    renumber_table = {
        "#": b"#23",
        "(": b"#28",
        ")": b"#29",
        "/": b"#2F",
        **{chr(i): f"#{i:02X}".encode() for i in range(33)},
    }

    def write_to_stream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:
        stream.write(self.renumber())  # b_(renumber(self)))

    def writeToStream(
        self, stream: StreamType, encryption_key: Union[None, str, bytes]
    ) -> None:  # pragma: no cover
        deprecate_with_replacement("writeToStream", "write_to_stream")
        self.write_to_stream(stream, encryption_key)

    def renumber(self) -> bytes:
        out = self[0].encode("utf-8")
        if out != b"/":
            logger_warning(f"Incorrect first char in NameObject:({self})", __name__)
        for c in self[1:]:
            if c > "~":
                for x in c.encode("utf-8"):
                    out += f"#{x:02X}".encode()
            else:
                try:
                    out += self.renumber_table[c]
                except KeyError:
                    out += c.encode("utf-8")
        return out

    @staticmethod
    def unnumber(sin: bytes) -> bytes:
        i = sin.find(b"#", 0)
        while i >= 0:
            try:
                sin = sin[:i] + unhexlify(sin[i + 1 : i + 3]) + sin[i + 3 :]
                i = sin.find(b"#", i + 1)
            except ValueError:
                # if the 2 characters after # can not be converted to hexa
                # we change nothing and carry on
                i = i + 1
        return sin

    @staticmethod
    def read_from_stream(stream: StreamType, pdf: Any) -> "NameObject":  # PdfReader
        name = stream.read(1)
        if name != NameObject.surfix:
            raise PdfReadError("name read error")
        name += read_until_regex(stream, NameObject.delimiter_pattern, ignore_eof=True)
        try:
            # Name objects should represent irregular characters
            # with a '#' followed by the symbol's hex number
            name = NameObject.unnumber(name)
            for enc in ("utf-8", "gbk"):
                try:
                    ret = name.decode(enc)
                    return NameObject(ret)
                except Exception:
                    pass
            raise UnicodeDecodeError("", name, 0, 0, "Code Not Found")
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            if not pdf.strict:
                logger_warning(
                    f"Illegal character in Name Object ({repr(name)})", __name__
                )
                return NameObject(name.decode("charmap"))
            else:
                raise PdfReadError(
                    f"Illegal character in Name Object ({repr(name)})"
                ) from e

    @staticmethod
    def readFromStream(
        stream: StreamType, pdf: Any  # PdfReader
    ) -> "NameObject":  # pragma: no cover
        deprecate_with_replacement("readFromStream", "read_from_stream")
        return NameObject.read_from_stream(stream, pdf)


def encode_pdfdocencoding(unicode_string: str) -> bytes:
    retval = b""
    for c in unicode_string:
        try:
            retval += b_(chr(_pdfdoc_encoding_rev[c]))
        except KeyError:
            raise UnicodeEncodeError(
                "pdfdocencoding", c, -1, -1, "does not exist in translation table"
            )
    return retval
