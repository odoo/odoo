from __future__ import annotations

import re
import struct
import sys
from codecs import getincrementaldecoder
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import IO, TYPE_CHECKING, Any, TypeVar, cast, overload

from ._types import (
    CBORDecodeEOF,
    CBORDecodeValueError,
    CBORSimpleValue,
    CBORTag,
    FrozenDict,
    break_marker,
    undefined,
)

if TYPE_CHECKING:
    from decimal import Decimal
    from email.message import Message
    from fractions import Fraction
    from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
    from typing import Literal
    from uuid import UUID

T = TypeVar("T")

timestamp_re = re.compile(
    r"^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)" r"(?:\.(\d{1,6})\d*)?(?:Z|([+-])(\d\d):(\d\d))$"
)
incremental_utf8_decoder = getincrementaldecoder("utf-8")


class CBORDecoder:
    """
    The CBORDecoder class implements a fully featured `CBOR`_ decoder with
    several extensions for handling shared references, big integers, rational
    numbers and so on. Typically the class is not used directly, but the
    :func:`load` and :func:`loads` functions are called to indirectly construct
    and use the class.

    When the class is constructed manually, the main entry points are
    :meth:`decode` and :meth:`decode_from_bytes`.

    .. _CBOR: https://cbor.io/
    """

    __slots__ = (
        "_tag_hook",
        "_object_hook",
        "_share_index",
        "_shareables",
        "_fp",
        "_fp_read",
        "_immutable",
        "_str_errors",
        "_stringref_namespace",
    )

    _fp: IO[bytes]
    _fp_read: Callable[[int], bytes]

    def __init__(
        self,
        fp: IO[bytes],
        tag_hook: Callable[[CBORDecoder, CBORTag], Any] | None = None,
        object_hook: Callable[[CBORDecoder, dict[Any, Any]], Any] | None = None,
        str_errors: Literal["strict", "error", "replace"] = "strict",
    ):
        """
        :param fp:
            the file to read from (any file-like object opened for reading in binary
            mode)
        :param tag_hook:
            callable that takes 2 arguments: the decoder instance, and the
            :class:`.CBORTag` to be decoded. This callback is invoked for any tags
            for which there is no built-in decoder. The return value is substituted
            for the :class:`.CBORTag` object in the deserialized output
        :param object_hook:
            callable that takes 2 arguments: the decoder instance, and a
            dictionary. This callback is invoked for each deserialized
            :class:`dict` object. The return value is substituted for the dict in
            the deserialized output.
        :param str_errors:
            determines how to handle unicode decoding errors (see the `Error Handlers`_
            section in the standard library documentation for details)

        .. _Error Handlers: https://docs.python.org/3/library/codecs.html#error-handlers

        """
        self.fp = fp
        self.tag_hook = tag_hook
        self.object_hook = object_hook
        self.str_errors = str_errors
        self._share_index: int | None = None
        self._shareables: list[object] = []
        self._stringref_namespace: list[str | bytes] | None = None
        self._immutable = False

    @property
    def immutable(self) -> bool:
        """
        Used by decoders to check if the calling context requires an immutable
        type.  Object_hook or tag_hook should raise an exception if this flag
        is set unless the result can be safely used as a dict key.
        """
        return self._immutable

    @property
    def fp(self) -> IO[bytes]:
        return self._fp

    @fp.setter
    def fp(self, value: IO[bytes]) -> None:
        try:
            if not callable(value.read):
                raise ValueError("fp.read is not callable")
        except AttributeError:
            raise ValueError("fp object has no read method")
        else:
            self._fp = value
            self._fp_read = value.read

    @property
    def tag_hook(self) -> Callable[[CBORDecoder, CBORTag], Any] | None:
        return self._tag_hook

    @tag_hook.setter
    def tag_hook(self, value: Callable[[CBORDecoder, CBORTag], Any] | None) -> None:
        if value is None or callable(value):
            self._tag_hook = value
        else:
            raise ValueError("tag_hook must be None or a callable")

    @property
    def object_hook(self) -> Callable[[CBORDecoder, dict[Any, Any]], Any] | None:
        return self._object_hook

    @object_hook.setter
    def object_hook(self, value: Callable[[CBORDecoder, Mapping[Any, Any]], Any] | None) -> None:
        if value is None or callable(value):
            self._object_hook = value
        else:
            raise ValueError("object_hook must be None or a callable")

    @property
    def str_errors(self) -> Literal["strict", "error", "replace"]:
        return self._str_errors

    @str_errors.setter
    def str_errors(self, value: Literal["strict", "error", "replace"]) -> None:
        if value in ("strict", "error", "replace"):
            self._str_errors = value
        else:
            raise ValueError(
                f"invalid str_errors value {value!r} (must be one of 'strict', "
                "'error', or 'replace')"
            )

    def set_shareable(self, value: T) -> T:
        """
        Set the shareable value for the last encountered shared value marker,
        if any. If the current shared index is ``None``, nothing is done.

        :param value: the shared value
        :returns: the shared value to permit chaining
        """
        if self._share_index is not None:
            self._shareables[self._share_index] = value

        return value

    def _stringref_namespace_add(self, string: str | bytes, length: int) -> None:
        if self._stringref_namespace is not None:
            next_index = len(self._stringref_namespace)
            if next_index < 24:
                is_referenced = length >= 3
            elif next_index < 256:
                is_referenced = length >= 4
            elif next_index < 65536:
                is_referenced = length >= 5
            elif next_index < 4294967296:
                is_referenced = length >= 7
            else:
                is_referenced = length >= 11

            if is_referenced:
                self._stringref_namespace.append(string)

    def read(self, amount: int) -> bytes:
        """
        Read bytes from the data stream.

        :param int amount: the number of bytes to read
        """
        data = self._fp_read(amount)
        if len(data) < amount:
            raise CBORDecodeEOF(
                f"premature end of stream (expected to read {amount} bytes, got {len(data)} "
                "instead)"
            )

        return data

    def _decode(self, immutable: bool = False, unshared: bool = False) -> Any:
        if immutable:
            old_immutable = self._immutable
            self._immutable = True
        if unshared:
            old_index = self._share_index
            self._share_index = None
        try:
            initial_byte = self.read(1)[0]
            major_type = initial_byte >> 5
            subtype = initial_byte & 31
            decoder = major_decoders[major_type]
            return decoder(self, subtype)
        finally:
            if immutable:
                self._immutable = old_immutable
            if unshared:
                self._share_index = old_index

    def decode(self) -> object:
        """
        Decode the next value from the stream.

        :raises CBORDecodeError: if there is any problem decoding the stream
        """
        return self._decode()

    def decode_from_bytes(self, buf: bytes) -> object:
        """
        Wrap the given bytestring as a file and call :meth:`decode` with it as
        the argument.

        This method was intended to be used from the ``tag_hook`` hook when an
        object needs to be decoded separately from the rest but while still
        taking advantage of the shared value registry.
        """
        with BytesIO(buf) as fp:
            old_fp = self.fp
            self.fp = fp
            retval = self._decode()
            self.fp = old_fp
            return retval

    @overload
    def _decode_length(self, subtype: int) -> int:
        ...

    @overload
    def _decode_length(self, subtype: int, allow_indefinite: Literal[True]) -> int | None:
        ...

    def _decode_length(self, subtype: int, allow_indefinite: bool = False) -> int | None:
        if subtype < 24:
            return subtype
        elif subtype == 24:
            return self.read(1)[0]
        elif subtype == 25:
            return cast(int, struct.unpack(">H", self.read(2))[0])
        elif subtype == 26:
            return cast(int, struct.unpack(">L", self.read(4))[0])
        elif subtype == 27:
            return cast(int, struct.unpack(">Q", self.read(8))[0])
        elif subtype == 31 and allow_indefinite:
            return None
        else:
            raise CBORDecodeValueError("unknown unsigned integer subtype 0x%x" % subtype)

    def decode_uint(self, subtype: int) -> int:
        # Major tag 0
        return self.set_shareable(self._decode_length(subtype))

    def decode_negint(self, subtype: int) -> int:
        # Major tag 1
        return self.set_shareable(-self._decode_length(subtype) - 1)

    def decode_bytestring(self, subtype: int) -> bytes:
        # Major tag 2
        length = self._decode_length(subtype, allow_indefinite=True)
        if length is None:
            # Indefinite length
            buf: list[bytes] = []
            while True:
                initial_byte = self.read(1)[0]
                if initial_byte == 0xFF:
                    result = b"".join(buf)
                    break
                elif initial_byte >> 5 == 2:
                    length = self._decode_length(initial_byte & 0x1F)
                    if length is None or length > sys.maxsize:
                        raise CBORDecodeValueError(
                            "invalid length for indefinite bytestring chunk 0x%x" % length
                        )
                    value = self.read(length)
                    buf.append(value)
                else:
                    raise CBORDecodeValueError(
                        "non-bytestring found in indefinite length bytestring"
                    )
        else:
            if length > sys.maxsize:
                raise CBORDecodeValueError("invalid length for bytestring 0x%x" % length)
            elif length <= 65536:
                result = self.read(length)
            else:
                # Read large bytestrings 65536 (2 ** 16) bytes at a time
                left = length
                buffer = bytearray()
                while left:
                    chunk_size = min(left, 65536)
                    buffer.extend(self.read(chunk_size))
                    left -= chunk_size

                result = bytes(buffer)

            self._stringref_namespace_add(result, length)

        return self.set_shareable(result)

    def decode_string(self, subtype: int) -> str:
        # Major tag 3
        length = self._decode_length(subtype, allow_indefinite=True)
        if length is None:
            # Indefinite length
            # NOTE: It may seem redundant to repeat this code to handle UTF-8
            # strings but there is a reason to do this separately to
            # byte-strings. Specifically, the CBOR spec states (in sec. 2.2):
            #
            #     Text strings with indefinite lengths act the same as byte
            #     strings with indefinite lengths, except that all their chunks
            #     MUST be definite-length text strings.  Note that this implies
            #     that the bytes of a single UTF-8 character cannot be spread
            #     between chunks: a new chunk can only be started at a
            #     character boundary.
            #
            # This precludes using the indefinite bytestring decoder above as
            # that would happily ignore UTF-8 characters split across chunks.
            buf: list[str] = []
            while True:
                initial_byte = self.read(1)[0]
                if initial_byte == 0xFF:
                    result = "".join(buf)
                    break
                elif initial_byte >> 5 == 3:
                    length = self._decode_length(initial_byte & 0x1F)
                    if length is None or length > sys.maxsize:
                        raise CBORDecodeValueError(
                            "invalid length for indefinite string chunk 0x%x" % length
                        )

                    try:
                        value = self.read(length).decode("utf-8", self._str_errors)
                    except UnicodeDecodeError as exc:
                        raise CBORDecodeValueError("error decoding unicode string") from exc

                    buf.append(value)
                else:
                    raise CBORDecodeValueError("non-string found in indefinite length string")
        else:
            if length > sys.maxsize:
                raise CBORDecodeValueError("invalid length for string 0x%x" % length)

            if length <= 65536:
                try:
                    result = self.read(length).decode("utf-8", self._str_errors)
                except UnicodeDecodeError as exc:
                    raise CBORDecodeValueError("error decoding unicode string") from exc
            else:
                # Read and decode large text strings 65536 (2 ** 16) bytes at a time
                codec = incremental_utf8_decoder(self._str_errors)
                left = length
                result = ""
                while left:
                    chunk_size = min(left, 65536)
                    final = left <= chunk_size
                    try:
                        result += codec.decode(self.read(chunk_size), final)
                    except UnicodeDecodeError as exc:
                        raise CBORDecodeValueError("error decoding unicode string") from exc

                    left -= chunk_size

            self._stringref_namespace_add(result, length)

        return self.set_shareable(result)

    def decode_array(self, subtype: int) -> Sequence[Any]:
        # Major tag 4
        length = self._decode_length(subtype, allow_indefinite=True)
        if length is None:
            # Indefinite length
            items: list[Any] = []
            if not self._immutable:
                self.set_shareable(items)
            while True:
                value = self._decode()
                if value is break_marker:
                    break
                else:
                    items.append(value)
        else:
            if length > sys.maxsize:
                raise CBORDecodeValueError("invalid length for array 0x%x" % length)

            items = []
            if not self._immutable:
                self.set_shareable(items)

            for index in range(length):
                items.append(self._decode())

        if self._immutable:
            items_tuple = tuple(items)
            self.set_shareable(items_tuple)
            return items_tuple

        return items

    def decode_map(self, subtype: int) -> Mapping[Any, Any]:
        # Major tag 5
        length = self._decode_length(subtype, allow_indefinite=True)
        if length is None:
            # Indefinite length
            dictionary: dict[Any, Any] = {}
            self.set_shareable(dictionary)
            while True:
                key = self._decode(immutable=True, unshared=True)
                if key is break_marker:
                    break
                else:
                    dictionary[key] = self._decode(unshared=True)
        else:
            dictionary = {}
            self.set_shareable(dictionary)
            for _ in range(length):
                key = self._decode(immutable=True, unshared=True)
                dictionary[key] = self._decode(unshared=True)

        if self._object_hook:
            dictionary = self._object_hook(self, dictionary)
            self.set_shareable(dictionary)
        elif self._immutable:
            frozen_dict = FrozenDict(dictionary)
            self.set_shareable(dictionary)
            return frozen_dict

        return dictionary

    def decode_semantic(self, subtype: int) -> Any:
        # Major tag 6
        tagnum = self._decode_length(subtype)
        if semantic_decoder := semantic_decoders.get(tagnum):
            return semantic_decoder(self)

        tag = CBORTag(tagnum, None)
        self.set_shareable(tag)
        tag.value = self._decode(unshared=True)
        if self._tag_hook:
            tag = self._tag_hook(self, tag)

        return self.set_shareable(tag)

    def decode_special(self, subtype: int) -> Any:
        # Simple value
        if subtype < 20:
            # XXX Set shareable?
            return CBORSimpleValue(subtype)

        # Major tag 7
        try:
            return special_decoders[subtype](self)
        except KeyError as e:
            raise CBORDecodeValueError(
                "Undefined Reserved major type 7 subtype 0x%x" % subtype
            ) from e

    #
    # Semantic decoders (major tag 6)
    #
    def decode_epoch_date(self) -> date:
        # Semantic tag 100
        value = self._decode()
        return self.set_shareable(date.fromordinal(value + 719163))

    def decode_date_string(self) -> date:
        # Semantic tag 1004
        value = self._decode()
        return self.set_shareable(date.fromisoformat(value))

    def decode_datetime_string(self) -> datetime:
        # Semantic tag 0
        value = self._decode()
        match = timestamp_re.match(value)
        if match:
            (
                year,
                month,
                day,
                hour,
                minute,
                second,
                secfrac,
                offset_sign,
                offset_h,
                offset_m,
            ) = match.groups()
            if secfrac is None:
                microsecond = 0
            else:
                microsecond = int(f"{secfrac:<06}")

            if offset_h:
                if offset_sign == "-":
                    sign = -1
                else:
                    sign = 1
                hours = int(offset_h) * sign
                minutes = int(offset_m) * sign
                tz = timezone(timedelta(hours=hours, minutes=minutes))
            else:
                tz = timezone.utc

            return self.set_shareable(
                datetime(
                    int(year),
                    int(month),
                    int(day),
                    int(hour),
                    int(minute),
                    int(second),
                    microsecond,
                    tz,
                )
            )
        else:
            raise CBORDecodeValueError(f"invalid datetime string: {value!r}")

    def decode_epoch_datetime(self) -> datetime:
        # Semantic tag 1
        value = self._decode()

        try:
            tmp = datetime.fromtimestamp(value, timezone.utc)
        except (OverflowError, OSError, ValueError) as exc:
            raise CBORDecodeValueError("error decoding datetime from epoch") from exc

        return self.set_shareable(tmp)

    def decode_positive_bignum(self) -> int:
        # Semantic tag 2
        from binascii import hexlify

        value = self._decode()
        if not isinstance(value, bytes):
            raise CBORDecodeValueError("invalid bignum value " + str(value))

        return self.set_shareable(int(hexlify(value), 16))

    def decode_negative_bignum(self) -> int:
        # Semantic tag 3
        return self.set_shareable(-self.decode_positive_bignum() - 1)

    def decode_fraction(self) -> Decimal:
        # Semantic tag 4
        from decimal import Decimal

        try:
            exp, sig = self._decode()
        except (TypeError, ValueError) as e:
            raise CBORDecodeValueError("Incorrect tag 4 payload") from e
        tmp = Decimal(sig).as_tuple()
        return self.set_shareable(Decimal((tmp.sign, tmp.digits, exp)))

    def decode_bigfloat(self) -> Decimal:
        # Semantic tag 5
        from decimal import Decimal

        try:
            exp, sig = self._decode()
        except (TypeError, ValueError) as e:
            raise CBORDecodeValueError("Incorrect tag 5 payload") from e

        return self.set_shareable(Decimal(sig) * (2 ** Decimal(exp)))

    def decode_stringref(self) -> str | bytes:
        # Semantic tag 25
        if self._stringref_namespace is None:
            raise CBORDecodeValueError("string reference outside of namespace")

        index: int = self._decode()
        try:
            value = self._stringref_namespace[index]
        except IndexError:
            raise CBORDecodeValueError("string reference %d not found" % index)

        return value

    def decode_shareable(self) -> object:
        # Semantic tag 28
        old_index = self._share_index
        self._share_index = len(self._shareables)
        self._shareables.append(None)
        try:
            return self._decode()
        finally:
            self._share_index = old_index

    def decode_sharedref(self) -> Any:
        # Semantic tag 29
        value = self._decode(unshared=True)
        try:
            shared = self._shareables[value]
        except IndexError:
            raise CBORDecodeValueError("shared reference %d not found" % value)

        if shared is None:
            raise CBORDecodeValueError("shared value %d has not been initialized" % value)
        else:
            return shared

    def decode_rational(self) -> Fraction:
        # Semantic tag 30
        from fractions import Fraction

        inputval = self._decode(immutable=True, unshared=True)
        try:
            value = Fraction(*inputval)
        except (TypeError, ZeroDivisionError) as exc:
            if not isinstance(inputval, tuple):
                raise CBORDecodeValueError(
                    "error decoding rational: input value was not a tuple"
                ) from None

            raise CBORDecodeValueError("error decoding rational") from exc

        return self.set_shareable(value)

    def decode_regexp(self) -> re.Pattern[str]:
        # Semantic tag 35
        try:
            value = re.compile(self._decode())
        except re.error as exc:
            raise CBORDecodeValueError("error decoding regular expression") from exc

        return self.set_shareable(value)

    def decode_mime(self) -> Message:
        # Semantic tag 36
        from email.parser import Parser

        try:
            value = Parser().parsestr(self._decode())
        except TypeError as exc:
            raise CBORDecodeValueError("error decoding MIME message") from exc

        return self.set_shareable(value)

    def decode_uuid(self) -> UUID:
        # Semantic tag 37
        from uuid import UUID

        try:
            value = UUID(bytes=self._decode())
        except (TypeError, ValueError) as exc:
            raise CBORDecodeValueError("error decoding UUID value") from exc

        return self.set_shareable(value)

    def decode_stringref_namespace(self) -> Any:
        # Semantic tag 256
        old_namespace = self._stringref_namespace
        self._stringref_namespace = []
        value = self._decode()
        self._stringref_namespace = old_namespace
        return value

    def decode_set(self) -> set[Any] | frozenset[Any]:
        # Semantic tag 258
        if self._immutable:
            return self.set_shareable(frozenset(self._decode(immutable=True)))
        else:
            return self.set_shareable(set(self._decode(immutable=True)))

    def decode_ipaddress(self) -> IPv4Address | IPv6Address | CBORTag:
        # Semantic tag 260
        from ipaddress import ip_address

        buf = self.decode()
        if not isinstance(buf, bytes) or len(buf) not in (4, 6, 16):
            raise CBORDecodeValueError(f"invalid ipaddress value {buf!r}")
        elif len(buf) in (4, 16):
            return self.set_shareable(ip_address(buf))
        elif len(buf) == 6:
            # MAC address
            return self.set_shareable(CBORTag(260, buf))

        raise CBORDecodeValueError(f"invalid ipaddress value {buf!r}")

    def decode_ipnetwork(self) -> IPv4Network | IPv6Network:
        # Semantic tag 261
        from ipaddress import ip_network

        net_map = self.decode()
        if isinstance(net_map, Mapping) and len(net_map) == 1:
            for net in net_map.items():
                try:
                    return self.set_shareable(ip_network(net, strict=False))
                except (TypeError, ValueError):
                    break

        raise CBORDecodeValueError(f"invalid ipnetwork value {net_map!r}")

    def decode_self_describe_cbor(self) -> Any:
        # Semantic tag 55799
        return self._decode()

    #
    # Special decoders (major tag 7)
    #

    def decode_simple_value(self) -> CBORSimpleValue:
        # XXX Set shareable?
        return CBORSimpleValue(self.read(1)[0])

    def decode_float16(self) -> float:
        return self.set_shareable(cast(float, struct.unpack(">e", self.read(2))[0]))

    def decode_float32(self) -> float:
        return self.set_shareable(cast(float, struct.unpack(">f", self.read(4))[0]))

    def decode_float64(self) -> float:
        return self.set_shareable(cast(float, struct.unpack(">d", self.read(8))[0]))


major_decoders: dict[int, Callable[[CBORDecoder, int], Any]] = {
    0: CBORDecoder.decode_uint,
    1: CBORDecoder.decode_negint,
    2: CBORDecoder.decode_bytestring,
    3: CBORDecoder.decode_string,
    4: CBORDecoder.decode_array,
    5: CBORDecoder.decode_map,
    6: CBORDecoder.decode_semantic,
    7: CBORDecoder.decode_special,
}

special_decoders: dict[int, Callable[[CBORDecoder], Any]] = {
    20: lambda self: False,
    21: lambda self: True,
    22: lambda self: None,
    23: lambda self: undefined,
    24: CBORDecoder.decode_simple_value,
    25: CBORDecoder.decode_float16,
    26: CBORDecoder.decode_float32,
    27: CBORDecoder.decode_float64,
    31: lambda self: break_marker,
}

semantic_decoders: dict[int, Callable[[CBORDecoder], Any]] = {
    0: CBORDecoder.decode_datetime_string,
    1: CBORDecoder.decode_epoch_datetime,
    2: CBORDecoder.decode_positive_bignum,
    3: CBORDecoder.decode_negative_bignum,
    4: CBORDecoder.decode_fraction,
    5: CBORDecoder.decode_bigfloat,
    25: CBORDecoder.decode_stringref,
    28: CBORDecoder.decode_shareable,
    29: CBORDecoder.decode_sharedref,
    30: CBORDecoder.decode_rational,
    35: CBORDecoder.decode_regexp,
    36: CBORDecoder.decode_mime,
    37: CBORDecoder.decode_uuid,
    100: CBORDecoder.decode_epoch_date,
    256: CBORDecoder.decode_stringref_namespace,
    258: CBORDecoder.decode_set,
    260: CBORDecoder.decode_ipaddress,
    261: CBORDecoder.decode_ipnetwork,
    1004: CBORDecoder.decode_date_string,
    55799: CBORDecoder.decode_self_describe_cbor,
}


def loads(
    s: bytes | bytearray | memoryview,
    tag_hook: Callable[[CBORDecoder, CBORTag], Any] | None = None,
    object_hook: Callable[[CBORDecoder, dict[Any, Any]], Any] | None = None,
    str_errors: Literal["strict", "error", "replace"] = "strict",
) -> Any:
    """
    Deserialize an object from a bytestring.

    :param bytes s:
        the bytestring to deserialize
    :param tag_hook:
        callable that takes 2 arguments: the decoder instance, and the :class:`.CBORTag`
        to be decoded. This callback is invoked for any tags for which there is no
        built-in decoder. The return value is substituted for the :class:`.CBORTag`
        object in the deserialized output
    :param object_hook:
        callable that takes 2 arguments: the decoder instance, and a dictionary. This
        callback is invoked for each deserialized :class:`dict` object. The return value
        is substituted for the dict in the deserialized output.
    :param str_errors:
        determines how to handle unicode decoding errors (see the `Error Handlers`_
        section in the standard library documentation for details)
    :return:
        the deserialized object

    .. _Error Handlers: https://docs.python.org/3/library/codecs.html#error-handlers

    """
    with BytesIO(s) as fp:
        return CBORDecoder(
            fp, tag_hook=tag_hook, object_hook=object_hook, str_errors=str_errors
        ).decode()


def load(
    fp: IO[bytes],
    tag_hook: Callable[[CBORDecoder, CBORTag], Any] | None = None,
    object_hook: Callable[[CBORDecoder, dict[Any, Any]], Any] | None = None,
    str_errors: Literal["strict", "error", "replace"] = "strict",
) -> Any:
    """
    Deserialize an object from an open file.

    :param fp:
        the file to read from (any file-like object opened for reading in binary mode)
    :param tag_hook:
        callable that takes 2 arguments: the decoder instance, and the :class:`.CBORTag`
        to be decoded. This callback is invoked for any tags for which there is no
        built-in decoder. The return value is substituted for the :class:`.CBORTag`
        object in the deserialized output
    :param object_hook:
        callable that takes 2 arguments: the decoder instance, and a dictionary. This
        callback is invoked for each deserialized :class:`dict` object. The return value
        is substituted for the dict in the deserialized output.
    :param str_errors:
        determines how to handle unicode decoding errors (see the `Error Handlers`_
        section in the standard library documentation for details)
    :return:
        the deserialized object

    .. _Error Handlers: https://docs.python.org/3/library/codecs.html#error-handlers

    """
    return CBORDecoder(
        fp, tag_hook=tag_hook, object_hook=object_hook, str_errors=str_errors
    ).decode()
