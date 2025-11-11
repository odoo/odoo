import base64
import io
from collections.abc import Buffer

__all__ = ['BinaryBytes', 'BinaryValue']


class BinaryValue(Buffer):
    """ Value of a binary field in cache and on records. It is a proxy object to
    the value's content as bytes, enabling getting the content in a lazy way
    (for performance). Abstract class.
    """
    __slots__ = ()

    def open(self) -> io.IOBase:
        """Open the value's content as an IO stream."""
        return io.BytesIO(self.content)

    @property
    def content(self) -> bytes:
        """The ``bytes``."""
        raise NotImplementedError

    @property
    def mimetype(self) -> str:
        """Guessed mimetype."""
        from .mimetypes import guess_mimetype  # noqa: PLC0415
        return guess_mimetype(self.content, '')

    @property
    def size(self) -> int:
        """Length of the binary."""
        return len(self.content)

    def __bytes__(self):
        # shortcut for `bytes(...)`
        return self.content

    def __buffer__(self, flags: int) -> memoryview:
        # https://peps.python.org/pep-0688/
        return memoryview(self.content)

    def __copy__(self):
        # BinaryValue is immutable from the point of view of the API.
        return self

    def __deepcopy__(self, memo):
        return self.__copy__()

    def to_base64(self) -> str:
        """Return the content encoded as a base64 string."""
        return base64.b64encode(self).decode()

    def decode(self, encoding="utf-8", errors="strict") -> str:
        """Decode the raw contents to a string."""
        return self.content.decode(encoding, errors)


class BinaryBytes(BinaryValue):
    """Static binary value."""
    __slots__ = ('__data',)

    def __init__(self, data: Buffer):
        # force bytes
        self.__data = bytes(data)

    @property
    def content(self):
        return self.__data

    def __bool__(self):
        return bool(self.__data)

    def __repr__(self):
        data = self.__data
        if len(data) > 27:
            data = data[:27] + b'...'
        return f"Binary:{data!r}"


EMPTY_BINARY = BinaryBytes(b'')
