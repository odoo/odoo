import base64
import contextlib
import mimetypes
from datetime import datetime
from io import BytesIO
from pathlib import Path
from stat import S_ISDIR, S_ISREG
from typing import Any, ClassVar
from urllib.parse import urlsplit
from zlib import adler32

from werkzeug.exceptions import NotFound
from werkzeug.utils import send_file as _send_file

from odoo.libs.debug_log import DebugLog
from odoo.tools import file_path

from .constants import STATIC_CACHE, STATIC_CACHE_LONG
from .core import request
from .settings import current as current_settings
from .wrappers import Response, _Response, sanitize_download_name

_debug = DebugLog(__name__)

_REDIRECT_SCHEMES = frozenset({"", "http", "https"})


class Stream:
    _ALLOWED_KWARGS: ClassVar[frozenset[str]]

    type: str = ""
    data: bytes | None = None
    path: str | None = None
    url: str | None = None

    mimetype: str | None = None
    as_attachment: bool = False
    download_name: str | None = None
    conditional: bool = True
    etag: bool | str = True
    last_modified: float | datetime | None = None
    max_age: int | None = None
    immutable: bool = False
    size: int | None = None
    public: bool = False

    def __init__(self, **kwargs: Any) -> None:
        unknown = kwargs.keys() - self._ALLOWED_KWARGS
        if unknown:
            msg = f"Stream got unexpected keyword arguments: {sorted(unknown)}"
            raise TypeError(msg)
        self.__dict__.update(kwargs)

    @classmethod
    def from_path(
        cls, path: str, filter_ext: tuple[str, ...] = ("",), public: bool = False
    ) -> Stream:
        path = file_path(path, filter_ext)
        _debug.logic(
            "http.stream.path_checked", path=path, filters=",".join(filter_ext) or None
        )
        return cls._from_trusted_path(path, public=public)

    @classmethod
    def _from_trusted_path(cls, path: str, public: bool = False) -> Stream:
        p = Path(path)
        st = p.stat()
        if not S_ISREG(st.st_mode):
            msg = f"Path {path!r} is not a regular file"
            _debug.logic("http.stream.not_regular", is_dir=S_ISDIR(st.st_mode))
            if S_ISDIR(st.st_mode):
                raise IsADirectoryError(msg)
            raise OSError(msg)
        check = adler32(path.encode())
        mimetype = mimetypes.guess_type(path)[0]
        _debug.lifecycle(
            "http.stream.from_path",
            name=p.name,
            size=st.st_size,
            mimetype=mimetype,
            public=public,
        )
        return cls(
            type="path",
            path=path,
            mimetype=mimetype,
            download_name=p.name,
            etag=f"{st.st_mtime_ns}-{st.st_size}-{check}",
            last_modified=st.st_mtime,
            size=st.st_size,
            public=public,
        )

    @classmethod
    def from_binary_field(cls, record: Any, field_name: str) -> Stream:
        # Under bin_size a binary field answers its human size ("12.50 Kb"),
        # which the raw-bytes fallback below would serve as the file.
        record = record.with_context(
            bin_size=False, **{f"bin_size_{field_name}": False}
        )
        data = record[field_name] or b""
        if isinstance(data, str):
            data = data.encode()

        decoded = False  # debuglog
        with contextlib.suppress(ValueError):
            data = base64.b64decode(
                data.replace(b"\r", b"").replace(b"\n", b""),
                validate=True,
            )
            decoded = True  # debuglog
        _debug.lifecycle(
            "http.stream.from_field",
            model=getattr(record, "_name", None),
            field=field_name,
            size=len(data),
            base64=decoded,
        )
        return cls(
            type="data",
            data=data,
            etag=record.env["ir.attachment"]._get_content_checksum(data),
            last_modified=record.write_date if record._log_access else None,
            size=len(data),
            public=record.env.user._is_public(),
        )

    def _get_required_attribute(self, attr: str) -> Any:
        value = getattr(self, attr)
        if value is None:
            e = f"There is nothing to stream, missing {attr!r} attribute."
            raise ValueError(e)
        return value

    def _check_type(self) -> None:
        if self.type not in ("url", "data", "path"):
            e = f"Invalid type: {self.type!r}, should be 'url', 'data' or 'path'."
            raise ValueError(e)

    def read(self) -> bytes:
        if self.type == "url":
            msg = "Cannot read an URL"
            raise ValueError(msg)

        self._check_type()
        _debug.perf.count("http.stream.read", type=self.type, size=self.size)

        if self.type == "data":
            return self._get_required_attribute("data")

        return Path(self._get_required_attribute("path")).read_bytes()

    def _prepare_url_redirect(self) -> Any:
        url = self._get_required_attribute("url")
        scheme = urlsplit(url).scheme.lower()
        if scheme not in _REDIRECT_SCHEMES:
            _debug.logic("http.stream.url_redirect_refused", scheme=scheme)
            raise NotFound
        # Not a 301: browsers keep a permanent redirect forever, and an
        # attachment's url can be edited; a cached 302 expires.
        max_age = STATIC_CACHE if self.max_age is None else self.max_age
        _debug.logic("http.stream.url_redirect", max_age=max_age, scheme=scheme)
        res = request.redirect(url, code=302, local=False)
        res.headers["Cache-Control"] = f"max-age={max_age}"
        return res

    def _prepare_path_response(self, send_file_kwargs: dict[str, Any]) -> Any:
        path = self._get_required_attribute("path")
        send_file_kwargs["use_x_sendfile"] = False
        x_accel_redirect: str | None = None
        settings = current_settings()
        if settings.x_sendfile:
            with contextlib.suppress(ValueError):
                fspath = Path(path).relative_to(settings.filestore_root)
                x_accel_redirect = f"/web/filestore/{fspath}"
                send_file_kwargs["use_x_sendfile"] = True

        res = _send_file(path, **send_file_kwargs)
        _debug.logic(
            "http.stream.sendfile",
            x_sendfile=settings.x_sendfile,
            in_filestore=x_accel_redirect is not None,
            accel="X-Sendfile" in res.headers and x_accel_redirect is not None,
            size=self.size,
        )
        if "X-Sendfile" in res.headers and x_accel_redirect is not None:
            res.headers["X-Accel-Redirect"] = x_accel_redirect
            res.headers.pop("X-Sendfile", None)
            res.headers["Content-Length"] = "0"
        return res

    def prepare_response(
        self,
        as_attachment: bool | None = None,
        immutable: bool | None = None,
        content_security_policy: str | None = "default-src 'none'",
        environ: dict[str, Any] | None = None,
        **send_file_kwargs: Any,
    ) -> Any:
        self._check_type()

        if self.type == "url":
            return self._prepare_url_redirect()

        if as_attachment is None:
            as_attachment = self.as_attachment
        if immutable is None:
            immutable = self.immutable

        send_file_kwargs = {
            "mimetype": self.mimetype,
            "as_attachment": as_attachment,
            "download_name": None
            if self.download_name is None
            else sanitize_download_name(self.download_name),
            "conditional": self.conditional,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "max_age": STATIC_CACHE_LONG if immutable else self.max_age,
            "environ": request.httprequest.raw_environ if environ is None else environ,
            "response_class": _Response,
            **send_file_kwargs,
        }

        if self.type == "data":
            res = _send_file(
                BytesIO(self._get_required_attribute("data")), **send_file_kwargs
            )
        else:
            res = self._prepare_path_response(send_file_kwargs)

        _debug.pipeline(
            "http.stream.response",
            type=self.type,
            mimetype=self.mimetype,
            size=self.size,
            status=res.status_code,
            public=self.public,
            immutable=immutable,
            attachment=as_attachment,
        )
        headers = res.headers
        headers["X-Content-Type-Options"] = "nosniff"

        if content_security_policy:
            headers["Content-Security-Policy"] = content_security_policy

        cache_control = res.cache_control
        if self.public:
            if (cache_control.max_age or 0) > 0:
                cache_control.public = True
        else:
            cache_control.pop("public", "")
            cache_control.private = True
        if immutable:
            cache_control["immutable"] = None

        return Response(res)


Stream._ALLOWED_KWARGS = frozenset(
    name for name in Stream.__annotations__ if not name.startswith("_")
)
