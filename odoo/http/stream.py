from __future__ import annotations

import contextlib
import mimetypes
import os
import typing
from io import BytesIO
from os.path import join as opj
from pathlib import Path
from zlib import adler32

from werkzeug.urls import url_quote
from werkzeug.utils import send_file as _send_file

from odoo.tools import config, file_path

if typing.TYPE_CHECKING:
    from datetime import datetime
    from typing import Self

    from odoo.models import BaseModel

    from .response import Response

STATIC_CACHE = 60 * 60 * 24 * 7  # 1 week
""" The cache duration for static content from the filesystem. """

STATIC_CACHE_LONG = 60 * 60 * 24 * 365  # 1 year
"""
The cache duration for content where the url uniquely identifies the
content (usually using a hash)
"""


def content_disposition(filename: str, disposition_type: typing.Literal['attachment', 'inline'] = 'attachment') -> str:
    """
    Craft a ``Content-Disposition`` header, see :rfc:`6266`.

    :param filename: The name of the file, should that file be saved on
        disk by the browser.
    :param disposition_type: Tell the browser what to do with the file,
        either ``"attachment"`` to save the file on disk,
        either ``"inline"`` to display the file.
    """
    if disposition_type not in ('attachment', 'inline'):
        e = f"Invalid disposition_type: {disposition_type!r}"
        raise ValueError(e)
    return "{}; filename*=UTF-8''{}".format(
        disposition_type,
        url_quote(filename, safe='', unsafe='()<>@,;:"/[]?={}\\*\'%'),  # RFC6266
    )


class Stream:
    """
    Send the content of a file, an attachment or a binary field via HTTP

    This utility is safe, cache-aware and uses the best available
    streaming strategy. Works best with the --x-sendfile cli option.

    Create a Stream via one of the constructors: :meth:`~from_path`:, or
    :meth:`~from_binary_field`:, generate the corresponding HTTP response
    object via :meth:`~get_response`:.

    Instantiating a Stream object manually without using one of the
    dedicated constructors is discouraged.
    """

    type: typing.Literal['data', 'path', 'url']
    data: bytes | None = None
    path: str | None = None
    url = None

    mimetype: str | None = None
    as_attachment: bool = False
    download_name: str | None = None
    conditional = True
    etag: str | typing.Literal[True] = True
    last_modified: datetime | float | None = None
    max_age = None
    immutable: bool = False
    size: int | None = None
    public: bool = False

    def __init__(self, **kwargs):
        # Remove class methods from the instances
        self.from_path = self.from_attachment = self.from_binary_field = None
        self.__dict__.update(kwargs)
        assert self.type in ('data', 'path', 'url'), f"Invalid type {self.type!r} in Stream"
        assert getattr(self, self.type, None) is not None, f"Missing attribute {self.type!r} to Stream"

    @classmethod
    def from_path(cls, path: str, filter_ext: tuple[str, ...] = (), public: bool = False) -> Self:
        """
        Create a :class:`~Stream`: from an addon resource.

        :param path: See :func:`~odoo.tools.file_path`
        :param filter_ext: See :func:`~odoo.tools.file_path`
        :param bool public: Advertise the resource as being cachable by
            intermediate proxies, otherwise only let the browser caches
            it.
        """
        path = file_path(path, filter_ext)
        check = adler32(path.encode())
        stat = os.stat(path)
        return cls(
            type='path',
            path=path,
            mimetype=mimetypes.guess_type(path)[0],
            download_name=os.path.basename(path),
            etag=f'{int(stat.st_mtime)}-{stat.st_size}-{check}',
            last_modified=stat.st_mtime,
            size=stat.st_size,
            public=public,
        )

    @classmethod
    def from_binary_field(cls, record: BaseModel, field_name: str) -> Self:
        """ Create a :class:`~Stream`: from a binary field. """
        data = record[field_name].content
        return cls(
            type='data',
            data=data,
            etag=request.env['ir.attachment']._compute_checksum(data),
            last_modified=record.write_date if record._log_access else None,
            size=len(data),
            public=record.env.user._is_public()  # good enough
        )

    def read(self) -> bytes:
        """ Get the stream content as bytes. """
        if self.type == 'url':
            e = "Cannot read an URL"
            raise ValueError(e)

        if self.type == 'data':
            assert self.data is not None
            return self.data

        assert self.path is not None, "Missing path to read Stream"
        with open(self.path, 'rb') as file:
            return file.read()

    def get_response(
        self,
        as_attachment: bool | None = None,
        immutable: bool | None = None,
        content_security_policy: str | None = "default-src 'none'",
        **send_file_kwargs,
    ) -> Response:
        """
        Create the corresponding :class:`~Response` for the current stream.

        :param as_attachment: Indicate to the browser that it
            should offer to save the file instead of displaying it.
        :param immutable: Add the ``immutable`` directive to
            the ``Cache-Control`` response header, allowing intermediary
            proxies to aggressively cache the response. This option also
            set the ``max-age`` directive to 1 year.
        :param content_security_policy: Optional value for the
            ``Content-Security-Policy`` (CSP) header. This header is
            used by browsers to allow/restrict the downloaded resource
            to itself perform new http requests. By default CSP is set
            to ``"default-scr 'none'"`` which restrict all requests.
        :param send_file_kwargs: Other keyword arguments to send to
            :func:`odoo.tools._vendor.send_file.send_file` instead of
            the stream sensitive values. Discouraged.
        """
        if self.type == 'url':
            if self.max_age is not None:
                res = request.redirect(self.url, code=302, local=False)
                res.headers['Cache-Control'] = f'max-age={self.max_age}'
                return res
            return request.redirect(self.url, code=301, local=False)

        if as_attachment is None:
            as_attachment = self.as_attachment
        if immutable is None:
            immutable = self.immutable

        send_file_kwargs = {
            'mimetype': self.mimetype,
            'as_attachment': as_attachment,
            'download_name': self.download_name,
            'conditional': self.conditional,
            'etag': self.etag,
            'last_modified': self.last_modified,
            'max_age': STATIC_CACHE_LONG if immutable else self.max_age,
            'environ': request.httprequest.environ,
            'response_class': Response,
            **send_file_kwargs,
        }

        if self.type == 'data':
            res = _send_file(BytesIO(self.data), **send_file_kwargs)
        else:  # self.type == 'path'
            send_file_kwargs['use_x_sendfile'] = False
            if config['x_sendfile']:
                with contextlib.suppress(ValueError):  # outside of the filestore
                    fspath = Path(self.path).relative_to(opj(config['data_dir'], 'filestore'))
                    x_accel_redirect = f'/web/filestore/{fspath}'
                    send_file_kwargs['use_x_sendfile'] = True

            res = _send_file(self.path, **send_file_kwargs)
            if 'X-Sendfile' in res.headers:
                res.headers['X-Accel-Redirect'] = x_accel_redirect

                # In case of X-Sendfile/X-Accel-Redirect, the body is empty,
                # yet werkzeug gives the length of the file. This makes
                # NGINX wait for content that'll never arrive.
                res.headers['Content-Length'] = '0'

        res.headers['X-Content-Type-Options'] = 'nosniff'

        if content_security_policy:  # see also Application.set_csp()
            res.headers['Content-Security-Policy'] = content_security_policy

        if self.public:
            if (res.cache_control.max_age or 0) > 0:
                res.cache_control.public = True
        else:
            res.cache_control.pop('public', '')
            res.cache_control.private = True
        if immutable:
            res.cache_control['immutable'] = None  # None sets the directive

        return res


# ruff: noqa: E402
from .requestlib import request
from .response import Response
