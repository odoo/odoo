import contextlib
import logging
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psycopg.errors

from odoo.exceptions import MissingError
from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from odoo.api import Environment
    from odoo.http import Stream

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

STORAGE_BACKENDS: dict[str, type[AttachmentStorage]] = {}

_UNKNOWN_SCHEMES_WARNED: set[tuple[str, str]] = set()


def register_storage(cls: type[AttachmentStorage]) -> type[AttachmentStorage]:
    if not cls.location:
        msg = f"{cls.__name__} must define a location name to be registered"
        raise ValueError(msg)
    if (current := STORAGE_BACKENDS.get(cls.location)) not in (None, cls):
        _debug.logic(
            "backend_registration_refused",
            location=cls.location,
            holder=current.__name__,
            claimant=cls.__name__,
        )
        msg = (
            f"storage location {cls.location!r} is already registered by "
            f"{current.__name__}; {cls.__name__} cannot claim it too"
        )
        raise ValueError(msg)
    STORAGE_BACKENDS[cls.location] = cls
    _debug.lifecycle("backend_registered", location=cls.location, backend=cls.__name__)
    return cls


def backend_for_key(env: Environment, key: str) -> AttachmentStorage:
    if "://" in key:
        for backend_cls in STORAGE_BACKENDS.values():
            if backend_cls.owns_key(key):
                _debug.logic(
                    "backend_for_key",
                    scheme=backend_cls.key_scheme,
                    backend=backend_cls.__name__,
                )
                return backend_cls(env)
        scheme = key.split("://", 1)[0]
        _debug.logic("backend_for_key", scheme=scheme, backend="UnknownSchemeStorage")
        if (seen_key := (env.cr.dbname, scheme)) not in _UNKNOWN_SCHEMES_WARNED:
            _UNKNOWN_SCHEMES_WARNED.add(seen_key)
            _logger.warning(
                "No storage backend registered for scheme %r (key %r); "
                "falling back to the local filestore. Subsequent read "
                "failures for such keys are caused by the missing backend "
                "module, not the filestore. (warned once per scheme)",
                scheme,
                key,
            )
        return UnknownSchemeStorage(env)
    return FileStorage(env)


class AttachmentStorage:
    location: str = ""
    key_scheme: str = ""

    def __init__(self, env: Environment) -> None:
        self.env = env

    @classmethod
    def owns_key(cls, key: str) -> bool:
        return bool(cls.key_scheme) and key.startswith(cls.key_scheme + "://")

    @staticmethod
    def _inline_datas_values(data: bytes) -> dict[str, Any]:
        return {"store_fname": False, "db_datas": data}

    def write(self, data: bytes, checksum: str) -> dict[str, Any]:
        raise NotImplementedError

    def write_stream(self, fileobj: Any) -> dict[str, Any]:
        model = self.env["ir.attachment"]
        data = fileobj.read()
        if isinstance(data, str):
            data = data.encode()
        checksum = model._get_content_checksum(data)
        _debug.perf.count(
            "stream_buffered", backend=type(self).__name__, size=len(data)
        )
        return {
            "checksum": checksum,
            "file_size": len(data),
            **self.write(data, checksum),
        }

    def read(self, key: str, size: int | None = None) -> bytes:
        raise NotImplementedError

    def remove(self, key: str) -> None:
        raise NotImplementedError

    def to_stream(self, attachment: Any, stream: Stream) -> Stream:
        raise NotImplementedError

    def autovacuum(self) -> tuple[int, bool] | bool | None:
        pass


class UnknownSchemeStorage(AttachmentStorage):
    location = "unknown"

    def write(self, data: bytes, checksum: str) -> dict[str, Any]:
        raise NotImplementedError

    def read(self, key: str, size: int | None = None) -> bytes:
        _logger.warning("No storage backend can read %r; serving no content", key)
        _debug.logic("unknown_scheme", op="read", key=key)
        return b""

    def remove(self, key: str) -> None:
        _logger.warning("No storage backend can delete %r; leaving it in place", key)
        _debug.logic("unknown_scheme", op="delete", key=key)

    def to_stream(self, attachment: Any, stream: Stream) -> Stream:
        _debug.logic("unknown_scheme", op="stream", attachment=attachment.id)
        raise MissingError(
            attachment.env._(
                "The content of attachment %(id)s is held by a storage backend "
                "that is not installed (%(key)s).",
                id=attachment.id,
                key=attachment.store_fname,
            )
        )


@register_storage
class DbStorage(AttachmentStorage):
    location = "db"

    def write(self, data: bytes, checksum: str) -> dict[str, Any]:
        _debug.lifecycle("db_write", size=len(data))
        return self._inline_datas_values(data)


@register_storage
class FileStorage(AttachmentStorage):
    location = "file"

    def _model(self):
        return self.env["ir.attachment"]

    def write(self, data: bytes, checksum: str) -> dict[str, Any]:
        if not data:
            _debug.logic("file_write_inlined", reason="empty")
            return self._inline_datas_values(data)
        with _debug.perf("file_write", size=len(data)):
            fname = self._model()._write_file(data, checksum)
        return {"store_fname": fname, "db_datas": False}

    def write_stream(self, fileobj: Any) -> dict[str, Any]:
        fname, size, checksum = self._model()._write_file_stream(fileobj)
        _debug.lifecycle("file_stream_written", size=size, inlined=not size)
        if not size:
            return {
                "checksum": checksum,
                "file_size": 0,
                **self._inline_datas_values(b""),
            }
        return {
            "checksum": checksum,
            "file_size": size,
            "store_fname": fname,
            "db_datas": False,
        }

    def read(self, key: str, size: int | None = None) -> bytes:
        data = self._model()._read_file(key, size=size)
        _debug.perf.count("file_read", key=key, requested=size, bytes=len(data))
        return data

    def remove(self, key: str) -> None:
        _debug.lifecycle("file_marked_for_gc", key=key)
        self._model()._mark_for_gc(key)

    def autovacuum(self) -> tuple[int, bool] | bool:
        model = self._model()
        cr = self.env.cr
        cr.commit()

        checklist = model._get_gc_checklist(limit=model._GC_MAX_ENTRIES)
        capped = len(checklist) >= model._GC_MAX_ENTRIES
        _debug.pipeline("filestore_gc_checklist", entries=len(checklist), capped=capped)
        if capped:
            _logger.info(
                "filestore gc: checklist cap reached (%d entries); the "
                "remainder will be swept by the next run",
                len(checklist),
            )

        removed = 0
        batches = 0
        for names in batched(checklist, cr.BATCH_SIZE, strict=False):
            batches += 1
            cr.execute("SET LOCAL lock_timeout TO '10s'")
            try:
                cr.execute("LOCK ir_attachment IN SHARE MODE")
            except psycopg.errors.LockNotAvailable:
                cr.rollback()
                _debug.logic("filestore_gc_lock_lost", removed=removed)
                if not removed:
                    return False
                _logger.warning(
                    "filestore gc: lost the lock after %d removal(s); the "
                    "rest of the checklist waits for the next run",
                    removed,
                )
                return removed, True
            removed += model._gc_file_store_unsafe(
                {name: checklist[name] for name in names}
            )
            cr.commit()
        _logger.info("filestore gc %d checked, %d removed", len(checklist), removed)
        _debug.lifecycle(
            "filestore_gc_done",
            checked=len(checklist),
            removed=removed,
            batches=batches,
            capped=capped,
        )
        return removed, capped

    def to_stream(self, attachment: Any, stream: Stream) -> Stream:
        stream.type = "path"
        try:
            stream.path = attachment._get_full_path(attachment.store_fname)
        except ValueError:
            _debug.logic(
                "stream_key_refused",
                attachment=attachment.id,
                reason="escapes_filestore",
            )
            stream.path = None
        stat = None
        if stream.path:
            with contextlib.suppress(FileNotFoundError):
                stat = Path(stream.path).stat()
        if stat is None:
            _debug.logic("stream_file_missing", attachment=attachment.id)
            _logger.warning(
                "Filestore file missing or invalid for attachment %s: %s",
                attachment.id,
                stream.path or attachment.store_fname,
            )
            stream.type = "data"
            stream.data = b""
            stream.size = 0
            stream.etag = False
            stream.last_modified = None
            stream.conditional = False
            stream.public = False
            return stream
        stream.last_modified = stat.st_mtime
        stream.size = stat.st_size
        _debug.pipeline("stream_from_file", attachment=attachment.id, size=stat.st_size)
        return stream
