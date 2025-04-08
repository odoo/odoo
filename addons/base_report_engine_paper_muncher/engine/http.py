# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from http import HttpStatus

MAX_BUFFER_SIZE = 2**10


class HttpMessage():

    def __init__(self):
        self.headers = {}

    def _readHeaderLines(self, reader: io.TextIOWrapper) -> list[str]:
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
                chunk += byte

                rem_size -= bs
            return chunk

        size = int(reader.readline()[:-2])
        chunk = read_chunk_content(size)

        reader.read(2)

        return chunk

    def readChunkedBody(self, reader: io.TextIOWrapper) -> bytes:
        encoded_body = b""
        while True:
            chunk = self._readSingleChunk(reader)

            if chunk is None:
                return None

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
            raise ValueError("Body must be in bytes")
        self.body = body
        self.addHeader("Content-Length", len(body))

    def __bytes__(self) -> bytes:
        def firstLine():
            return f"HTTP/{self.version} {self.code} {HttpStatus(self.code).phrase}".encode()

        def headers():
            return (f"{key}: {value}".encode() for key, value in self.headers.items())

        return b"\r\n".join([firstLine(), *headers(), b"", self.body])
