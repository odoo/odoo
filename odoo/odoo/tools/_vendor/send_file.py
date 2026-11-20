"""
Vendored copy of the werkzeug.utils.send_file function defined in
werkzeug2 which is packaged in Debian 12 "Bookworm" and Ubuntu 22.04
"Jammy". Odoo is compatible with werkzeug2 since saas-15.4.

This vendored copy is deprecated, only present to ensure backward
compatibility with older operating systems.

:copyright: 2007 Pallets
:license: BSD-3-Clause
"""

import io
import logging
import mimetypes
import os
import typing as t
import unicodedata
from datetime import datetime
from time import time
from zlib import adler32

from werkzeug.datastructures import Headers
from werkzeug.exceptions import RequestedRangeNotSatisfiable
from werkzeug.urls import url_quote
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

_logger = logging.getLogger(__name__)


def send_file(
    path_or_file: t.Union[os.PathLike, str, t.IO[bytes]],
    environ: "WSGIEnvironment",
    mimetype: t.Optional[str] = None,
    as_attachment: bool = False,
    download_name: t.Optional[str] = None,
    conditional: bool = True,
    etag: t.Union[bool, str] = True,
    last_modified: t.Optional[t.Union[datetime, int, float]] = None,
    max_age: t.Optional[
        t.Union[int, t.Callable[[t.Optional[str]], t.Optional[int]]]
    ] = None,
    use_x_sendfile: bool = False,
    response_class: t.Optional[t.Type["Response"]] = None,
    _root_path: t.Optional[t.Union[os.PathLike, str]] = None,
) -> "Response":
    """Send the contents of a file to the client.

    The first argument can be a file path or a file-like object. Paths
    are preferred in most cases because Werkzeug can manage the file and
    get extra information from the path. Passing a file-like object
    requires that the file is opened in binary mode, and is mostly
    useful when building a file in memory with :class:`io.BytesIO`.

    Never pass file paths provided by a user. The path is assumed to be
    trusted, so a user could craft a path to access a file you didn't
    intend.

    If the WSGI server sets a ``file_wrapper`` in ``environ``, it is
    used, otherwise Werkzeug's built-in wrapper is used. Alternatively,
    if the HTTP server supports ``X-Sendfile``, ``use_x_sendfile=True``
    will tell the server to send the given path, which is much more
    efficient than reading it in Python.

    :param path_or_file: The path to the file to send, relative to the
        current working directory if a relative path is given.
        Alternatively, a file-like object opened in binary mode. Make
        sure the file pointer is seeked to the start of the data.
    :param environ: The WSGI environ for the current request.
    :param mimetype: The MIME type to send for the file. If not
        provided, it will try to detect it from the file name.
    :param as_attachment: Indicate to a browser that it should offer to
        save the file instead of displaying it.
    :param download_name: The default name browsers will use when saving
        the file. Defaults to the passed file name.
    :param conditional: Enable conditional and range responses based on
        request headers. Requires passing a file path and ``environ``.
    :param etag: Calculate an ETag for the file, which requires passing
        a file path. Can also be a string to use instead.
    :param last_modified: The last modified time to send for the file,
        in seconds. If not provided, it will try to detect it from the
        file path.
    :param max_age: How long the client should cache the file, in
        seconds. If set, ``Cache-Control`` will be ``public``, otherwise
        it will be ``no-cache`` to prefer conditional caching.
    :param use_x_sendfile: Set the ``X-Sendfile`` header to let the
        server to efficiently send the file. Requires support from the
        HTTP server. Requires passing a file path.
    :param response_class: Build the response using this class. Defaults
        to :class:`~werkzeug.wrappers.Response`.
    :param _root_path: Do not use. For internal use only. Use
        :func:`send_from_directory` to safely send files under a path.
    """
    if response_class is None:
        response_class = Response

    path = None
    file = None
    size = None
    mtime = None
    headers = Headers()

    if isinstance(path_or_file, (os.PathLike, str)) or hasattr(
        path_or_file, "__fspath__"
    ):

        # Flask will pass app.root_path, allowing its send_file wrapper
        # to not have to deal with paths.
        if _root_path is not None:
            path = os.path.join(_root_path, path_or_file)
        else:
            path = os.path.abspath(path_or_file)

        stat = os.stat(path)
        size = stat.st_size
        mtime = stat.st_mtime
    else:
        file = path_or_file

    if download_name is None and path is not None:
        download_name = os.path.basename(path)

    if mimetype is None:
        if download_name is None:
            raise TypeError(
                "Unable to detect the MIME type because a file name is"
                " not available. Either set 'download_name', pass a"
                " path instead of a file, or set 'mimetype'."
            )

        mimetype, encoding = mimetypes.guess_type(download_name)

        if mimetype is None:
            mimetype = "application/octet-stream"

        # Don't send encoding for attachments, it causes browsers to
        # save decompress tar.gz files.
        if encoding is not None and not as_attachment:
            headers.set("Content-Encoding", encoding)
            if use_x_sendfile and path is not None:
                headers["X-Accel-Charset"] = encoding

    if download_name is not None:
        try:
            download_name.encode("ascii")
        except UnicodeEncodeError:
            simple = unicodedata.normalize("NFKD", download_name)
            simple = simple.encode("ascii", "ignore").decode("ascii")
            quoted = url_quote(download_name, safe="")
            names = {"filename": simple, "filename*": f"UTF-8''{quoted}"}
        else:
            names = {"filename": download_name}

        value = "attachment" if as_attachment else "inline"
        headers.set("Content-Disposition", value, **names)
    elif as_attachment:
        raise TypeError(
            "No name provided for attachment. Either set"
            " 'download_name' or pass a path instead of a file."
        )

    if use_x_sendfile and path is not None:
        headers["X-Sendfile"] = path
        data = None
    else:
        if file is None:
            file = open(path, "rb")  # type: ignore
        elif isinstance(file, io.BytesIO):
            size = file.getbuffer().nbytes
        elif isinstance(file, io.TextIOBase):
            raise ValueError("Files must be opened in binary mode or use BytesIO.")

        data = wrap_file(environ, file)

    rv = response_class(
        data, mimetype=mimetype, headers=headers, direct_passthrough=True
    )

    if size is not None:
        rv.content_length = size

    if last_modified is not None:
        rv.last_modified = last_modified  # type: ignore
    elif mtime is not None:
        rv.last_modified = mtime  # type: ignore

    rv.cache_control.no_cache = True

    # Flask will pass app.get_send_file_max_age, allowing its send_file
    # wrapper to not have to deal with paths.
    if callable(max_age):
        max_age = max_age(path)

    if max_age is not None:
        if max_age > 0:
            rv.cache_control.no_cache = None
            rv.cache_control.public = True

        rv.cache_control.max_age = max_age
        rv.expires = int(time() + max_age)  # type: ignore

    if isinstance(etag, str):
        rv.set_etag(etag)
    elif etag and path is not None:
        check = adler32(path.encode("utf-8")) & 0xFFFFFFFF
        rv.set_etag(f"{mtime}-{size}-{check}")

    if conditional:
        try:
            rv = rv.make_conditional(environ, accept_ranges=True, complete_length=size)
        except RequestedRangeNotSatisfiable:
            if file is not None:
                file.close()

            raise

        # Some x-sendfile implementations incorrectly ignore the 304
        # status code and send the file anyway.
        if rv.status_code == 304:
            rv.headers.pop("x-sendfile", None)

    return rv
