# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from http import HTTPStatus

MAX_BUFFER_SIZE = 2**10


class HttpMessage:

    def __init__(self):
        self.headers = {}

    def _readHeaderLines(self, reader: io.BufferedReader) -> list[str]:
        lines = []

        while True:
            request_line = reader.readline().decode('utf-8')

            if len(request_line) == 0:
                raise EOFError("Input stream has ended")

            if request_line == "\r\n":
                break

            lines.append(request_line)

        return lines

    def _addToHeader(self, header_line: str) -> None:
        key, value = header_line.split(':')
        self.headers[key.strip()] = value.strip()

    def readHeader(self, reader: io.TextIOWrapper) -> None:
        raise NotImplementedError()

    def _readSingleChunk(self, reader: io.TextIOWrapper) -> bytes:
        def read_chunk_content(rem_size):
            chunk = b""
            while rem_size > 0:
                bs = min(MAX_BUFFER_SIZE, rem_size)
                byte = reader.read(bs)

                if not byte:
                    raise EOFError("Unexpected end of file while reading chunk content.")

                chunk += byte.encode() if isinstance(byte, str) else byte
                rem_size -= len(byte)

            return chunk

        # Read and parse the chunk size line, strip removes trailing '\r\n'
        size_line = reader.readline()
        if not size_line:
            raise EOFError("Unexpected end of file while reading chunk size.")
        size = int(size_line.strip(), 16)

        chunk = read_chunk_content(size)

        # Consume the trailing '\r\n' after the chunk
        crlf = reader.read(2)
        if crlf != '\r\n':
            raise ValueError(f"Expected '\\r\\n' after chunk, got {crlf!r}")

        return chunk

    def readChunkedBody(self, reader: io.TextIOWrapper) -> bytes:
        encoded_body = b""
        while True:
            chunk = self._readSingleChunk(reader)

            if len(chunk) == 0:
                break

            encoded_body += chunk

        return encoded_body


class HttpRequest(HttpMessage):

    def __init__(self, method=None, path=None, version=None):
        super().__init__()
        self.method = method
        self.path = path
        self.version = version

    def readHeader(self, reader: io.TextIOWrapper) -> None:
        header_lines = self._readHeaderLines(reader)
        self.method, self.path, self.version = header_lines[0].split(' ')

        for line in header_lines[1:]:
            self._addToHeader(line)


class HttpResponse(HttpMessage):

    def __init__(self, code: int, version="1.1"):
        super().__init__()
        self.version = version
        self.code = code
        self.body = None

    def addHeader(self, key: str, value: str) -> None:
        self.headers[key] = value

    def addBody(self, body: bytes) -> None:
        if not isinstance(body, bytes):
            raise TypeError("Body must be in bytes")
        self.body = body
        self.addHeader("Content-Length", len(body))

    def __bytes__(self) -> bytes:
        def firstLine():
            return f"HTTP/{self.version} {self.code} {HTTPStatus(self.code).phrase}".encode()

        def headers():
            return (f"{key}: {value}".encode() for key, value in self.headers.items())

        return b"\r\n".join([firstLine(), *headers(), b"", self.body])
