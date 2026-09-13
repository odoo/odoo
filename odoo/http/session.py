import base64
import collections.abc
import contextlib
import copy
import errno
import fcntl
import logging
import os
import re
import tempfile
import threading
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from stat import S_ISREG
from typing import Any

from odoo.libs._vendor import sessions
from odoo.libs.debug_log import DebugLog
from odoo.libs.json import dumps_bytes as _dumps_bytes
from odoo.libs.json import loads as _loads
from odoo.tools import get_lang

from ._protocols import get_ir_http
from .constants import (
    DEFAULT_LANG,
    SESSION_DELETION_TIMER,
    SESSION_LIFETIME,
    STORED_SESSION_BYTES,
    prepare_default_session,
)
from .core import request
from .exceptions import SessionExpiredException

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_SESSION_KEY_LENGTH = 84
assert STORED_SESSION_BYTES < _SESSION_KEY_LENGTH, (
    f"STORED_SESSION_BYTES ({STORED_SESSION_BYTES}) must be < "
    f"_SESSION_KEY_LENGTH ({_SESSION_KEY_LENGTH}) for soft rotation to work"
)
_base64_urlsafe_re = re.compile(rf"^[A-Za-z0-9_-]{{{_SESSION_KEY_LENGTH}}}$")
_session_identifier_re = re.compile(rf"^[A-Za-z0-9_-]{{{STORED_SESSION_BYTES}}}$")
_session_stripe_re = re.compile(r"^[A-Za-z0-9_-]{2}$")

_TRACE_MAX_ENTRIES = 50


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def prepare_session_dir(path: str) -> str:
    try:
        Path(path).mkdir(0o700, parents=True)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
        if not os.access(path, os.W_OK):
            raise OSError(f"{path}: session directory is not writable") from exc
    return path


class FilesystemSessionStore(sessions.FilesystemSessionStore):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._held_locks = threading.local()
        self._durability = threading.local()
        self._lock_directory_ready = False

    @contextlib.contextmanager
    def _locked_sid(self, sid: str) -> Iterator[None]:
        self.get_session_filename(sid)
        # Fixed stripes bound lock-file growth. Never unlink them: replacing a
        # locked inode would let two workers enter the same critical section.
        stripe = sid[:2]
        held = getattr(self._held_locks, "stripes", None)
        if held is None:
            held = self._held_locks.stripes = set()
        if stripe in held:
            _debug.lifecycle("http.session.lock_reentered", stripe=stripe)
            yield
            return
        # A fresh descriptor per acquisition, not a cached one: flock belongs to
        # the open file description, so a shared descriptor would let two
        # threads of this process, or a forked child, into the same section.
        lock_fd = self._open_lock_file(stripe)
        try:
            with _debug.perf("http.session.lock_wait", stripe=stripe):
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
            held.add(stripe)
            _debug.lifecycle("http.session.lock_acquired", stripe=stripe)
            try:
                yield
            finally:
                held.remove(stripe)
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)

    def _open_lock_file(self, stripe: str) -> int:
        directory = Path(self.path, ".locks")
        if not self._lock_directory_ready:
            directory.mkdir(mode=0o700, exist_ok=True)
            self._lock_directory_ready = True
        flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC
        try:
            return os.open(directory / stripe, flags, 0o600)
        except FileNotFoundError:
            directory.mkdir(mode=0o700, exist_ok=True)
            return os.open(directory / stripe, flags, 0o600)

    @contextlib.contextmanager
    def _durably(self) -> Iterator[None]:
        previous = getattr(self._durability, "enabled", False)
        self._durability.enabled = True
        try:
            yield
        finally:
            self._durability.enabled = previous

    def _write(self, session: Session) -> None:
        filename = Path(self.get_session_filename(session.sid))
        durable = getattr(self._durability, "enabled", False)
        fd, tmp = tempfile.mkstemp(
            suffix=sessions._fs_transaction_suffix, dir=self.path
        )
        try:
            os.fchmod(fd, self.mode)
            with os.fdopen(fd, "wb") as handle:
                handle.write(_dumps_bytes(dict(session)))
                if durable:
                    handle.flush()
                    os.fsync(handle.fileno())
            Path(tmp).replace(filename)
            if durable:
                _fsync_directory(filename.parent)
        except OSError:
            _logger.warning(
                "Failed to persist session %r to %r",
                session.sid,
                str(filename),
                exc_info=True,
            )
            _debug.logic(
                "http.session.write_failed", sid=session.sid[:8], durable=durable
            )
            with contextlib.suppress(OSError):
                Path(tmp).unlink()
            raise

    def get_session_filename(self, sid: str) -> str:
        if not self.is_valid_key(sid):
            raise ValueError(f"Invalid session id {sid!r}")
        return str(Path(self.path, sid[:2], sid))

    def save(self, session: Session) -> None:
        origin = session.rotation[0].sid if session.rotation else session.sid
        with self._locked_sid(origin):
            if not session.is_new:
                current = self.get(session.sid)
                if current.is_new:
                    _debug.logic("http.session.save_refused", reason="revoked")
                    raise SessionExpiredException("Session was revoked")
                if "next_sid" in current:
                    _debug.logic("http.session.save", strategy="adopt_rotation")
                    self._adopt_live_successor(session, current)
                    return
                session.merge_changes(current)
            _debug.logic(
                "http.session.save",
                strategy="new" if session.is_new else "merge",
                rotating=session.rotation is not None,
            )
            self._save_unlocked(session)

    def _get_live_session(self, session: Session) -> Session:
        family = session.sid[:STORED_SESSION_BYTES]
        seen = {session.sid}
        while "next_sid" in session:
            sid = session["next_sid"]
            if (
                not isinstance(sid, str)
                or not self.is_valid_key(sid)
                or sid in seen
                or sid[:STORED_SESSION_BYTES] != family
            ):
                _debug.logic("http.session.rotation_chain_invalid", hops=len(seen))
                raise SessionExpiredException("Invalid session rotation chain")
            seen.add(sid)
            session = self.get(sid)
            if session.is_new:
                _debug.logic("http.session.rotation_chain_revoked", hops=len(seen))
                raise SessionExpiredException("Rotated session was revoked")
        _debug.logic("http.session.rotation_chain", hops=len(seen) - 1)
        return session

    def _save_unlocked(self, session: Session) -> None:
        dirname = Path(self.get_session_filename(session.sid)).parent
        if not dirname.is_dir():
            with contextlib.suppress(OSError):
                dirname.mkdir(mode=0o0700)
        with _debug.perf(
            "http.session.write",
            sid=session.sid[:8],
            was_new=session.is_new,
            durable=getattr(self._durability, "enabled", False),
        ):
            self._write(session)
        session.is_new = False
        session.mtime = time.time()
        session.mark_clean()

    def new(self) -> Session:
        session = super().new()
        session.store = self
        _debug.lifecycle("http.session.new", sid=session.sid[:8])
        return session

    def get(self, sid: str) -> Session:
        if not self.is_valid_key(sid):
            _debug.logic("http.session.get", sid=sid[:8], found=False, invalid_key=True)
            return self.new()
        with self._locked_sid(sid):
            with _debug.perf("http.session.read", sid=sid[:8]) as span:
                session = super().get(sid)
                span.set(found=not session.is_new)
        session.store = self
        session.mark_clean()
        if not session.is_new:
            with contextlib.suppress(OSError):
                session.mtime = (
                    Path(self.get_session_filename(session.sid)).stat().st_mtime
                )
        _debug.logic(
            "http.session.get", sid=sid[:8], found=not session.is_new, uid=session.uid
        )
        return session

    def _remove_sid(self, sid: str) -> None:
        path = Path(self.get_session_filename(sid))
        with self._locked_sid(sid), contextlib.suppress(FileNotFoundError):
            path.unlink()
            # A revocation that a crash can undo is not a revocation.
            _fsync_directory(path.parent)
        _debug.lifecycle("http.session.removed", sid=sid[:8])

    def delete(self, session: Session) -> None:
        self._remove_sid(session.sid)

    def keep_alive(self, session: Session) -> None:
        with self._locked_sid(session.sid):
            try:
                os.utime(self.get_session_filename(session.sid))
                session.mtime = time.time()
                _debug.lifecycle("http.session.kept_alive", sid=session.sid[:8])
            except FileNotFoundError:
                if not session.is_new:
                    _debug.logic("http.session.keep_alive_revoked", sid=session.sid[:8])
                    raise SessionExpiredException("Session was revoked") from None
                self.save(session)

    def remove_old_sessions(self, session: Session) -> None:
        if "gc_previous_sessions" in session:
            if session["create_time"] + SESSION_DELETION_TIMER < time.time():
                self.remove_sessions_for_identifiers(
                    [session.sid[:STORED_SESSION_BYTES]],
                    exclude_sid=session.sid,
                )
                del session["gc_previous_sessions"]
                _debug.lifecycle("http.session.family_collected", sid=session.sid[:8])
                self.save(session)

    def stage_rotation(self, session: Session, env: Any, soft: bool = False) -> None:
        _debug.lifecycle(
            "http.session.rotation_staged",
            soft=soft,
            uid=session.uid,
            already_staged=session.rotation is not None,
        )
        if session.rotation is not None:
            return
        original = session.snapshot()
        next_sid = self.generate_key()
        if soft:
            next_sid = (
                session.sid[:STORED_SESSION_BYTES] + next_sid[STORED_SESSION_BYTES:]
            )
        new_token = None
        if session.uid:
            if env is None:
                msg = "Saving an authenticated session requires an environment"
                raise ValueError(msg)
            new_token = (
                env["res.users"].browse(session.uid)._get_session_token(next_sid)
            )

        session.rotation = (original, soft)
        session.sid = next_sid
        session.is_new = True
        if new_token:
            session.session_token = new_token
        session.should_rotate = True
        session["create_time"] = time.time()
        if soft:
            session["gc_previous_sessions"] = True
        session.pop("next_sid", None)
        session.pop("deletion_time", None)
        _debug.lifecycle(
            "http.session.rotation_prepared",
            soft=soft,
            sid=next_sid[:8],
            token=new_token is not None,
            uid=session.uid,
        )

    def rotate(self, session: Session, env: Any, soft: bool = False) -> None:
        if soft and session.rotation is None:
            with self._locked_sid(session.sid):
                recent = self.get(session.sid)
                if "next_sid" in recent:
                    _debug.logic("http.session.rotate", strategy="adopt_before_stage")
                    self._adopt_live_successor(session, recent)
                    return
        self.stage_rotation(session, env, soft)
        assert session.rotation is not None
        original, soft = session.rotation
        try:
            with self._locked_sid(original.sid):
                current = self.get(original.sid)
                if not original.is_new and current.is_new:
                    _debug.logic("http.session.rotation_refused", reason="revoked")
                    raise SessionExpiredException("Session was revoked")
                if soft and "next_sid" in current:
                    _debug.logic("http.session.rotate", strategy="adopt_in_lock")
                    self._adopt_live_successor(session, current)
                    return
                _debug.logic(
                    "http.session.rotate",
                    strategy="soft" if soft else "hard",
                    original_new=original.is_new,
                )
                # Write the successor first: an interrupted write must not
                # leave the old cookie pointing at a nonexistent session.
                if soft and not original.is_new:
                    uid = session.uid
                    session.merge_changes(current)
                    if session.db != original.db:
                        _debug.logic(
                            "http.session.rotation_refused", reason="db_changed"
                        )
                        raise SessionExpiredException("Session database changed")
                    if session.uid != uid:
                        session.session_token = (
                            env["res.users"]
                            .browse(session.uid)
                            ._get_session_token(session.sid)
                            if session.uid
                            else None
                        )
                        _debug.lifecycle(
                            "http.session.token_regenerated",
                            merged_uid=session.uid,
                            staged_uid=uid,
                        )
                self.save(session)
                if soft:
                    current["next_sid"] = session.sid
                    current["deletion_time"] = time.time() + SESSION_DELETION_TIMER
                    with self._durably():
                        self._save_unlocked(current)
                elif not original.is_new:
                    # A previous soft rotation keeps predecessor cookies valid
                    # briefly. A hard rotation must revoke that entire family.
                    self.remove_sessions_for_identifiers(
                        [original.sid[:STORED_SESSION_BYTES]],
                        exclude_sid=session.sid,
                    )
                session.rotation = None
                session.should_rotate = False
                _debug.lifecycle(
                    "http.session.rotated",
                    soft=soft,
                    uid=session.uid,
                    family_revoked=not soft and not original.is_new,
                )
        except Exception:
            _debug.logic("http.session.rotation_failed", soft=soft, uid=session.uid)
            session.restore(original)
            raise

    def _adopt_live_successor(self, session: Session, current: Session) -> None:
        peer = self._get_live_session(current)
        original = session.snapshot()
        try:
            self._adopt_rotation(session, peer)
            self._save_unlocked(session)
        except Exception:
            session.restore(original)
            raise

    def _adopt_rotation(self, session: Session, peer: Session) -> None:
        if (session.db, session.uid) != (peer.db, peer.uid):
            _debug.logic("http.session.save_refused", reason="identity_changed")
            raise SessionExpiredException("Session identity changed")
        session.merge_changes(peer)
        session.sid = peer.sid
        session.is_new = False
        session.mtime = peer.mtime
        for key in ("session_token", "create_time", "gc_previous_sessions"):
            if key in peer:
                session[key] = peer[key]
        session.pop("next_sid", None)
        session.pop("deletion_time", None)
        session.rotation = None
        session.should_rotate = False
        _debug.lifecycle("http.session.rotation_adopted", sid=peer.sid[:8])

    def vacuum(self, max_lifetime: int = SESSION_LIFETIME) -> None:
        threshold = time.time() - max_lifetime
        base_path = Path(self.path)
        removed = 0  # debuglog
        with _debug.perf("http.session.vacuum", max_lifetime=max_lifetime) as span:
            for stripe_dir in base_path.iterdir():
                stripe = stripe_dir.name
                if not _session_stripe_re.fullmatch(stripe) or not stripe_dir.is_dir():
                    continue
                with self._locked_sid(stripe.ljust(_SESSION_KEY_LENGTH, "_")):
                    for path in stripe_dir.iterdir():
                        if not self.is_valid_key(path.name):
                            continue
                        with contextlib.suppress(OSError):
                            st = path.stat()
                            if S_ISREG(st.st_mode) and st.st_mtime < threshold:
                                path.unlink()
                                removed += 1  # debuglog
            for path in base_path.glob(f"*{sessions._fs_transaction_suffix}"):
                with contextlib.suppress(OSError):
                    st = path.stat()
                    if S_ISREG(st.st_mode) and st.st_mtime < threshold:
                        path.unlink()
                        removed += 1  # debuglog
            span.set(removed=removed)

    def generate_key(self, salt: bytes | None = None) -> str:
        return base64.urlsafe_b64encode(os.urandom(63)).decode("ascii")

    def is_valid_key(self, key: str) -> bool:
        return _base64_urlsafe_re.fullmatch(key) is not None

    def get_missing_session_identifiers(self, identifiers: Iterable[str]) -> set[str]:
        identifiers = set(identifiers)
        asked = len(identifiers)  # debuglog
        base = Path(self.path)
        directories = {str(base / identifier[:2]) for identifier in identifiers}
        for directory in directories:
            with (
                contextlib.suppress(OSError),
                os.scandir(directory) as session_files,
            ):
                identifiers.difference_update(
                    sf.name[:STORED_SESSION_BYTES] for sf in session_files
                )
        _debug.pipeline(
            "http.session.missing_identifiers",
            asked=asked,
            missing=len(identifiers),
            directories=len(directories),
        )
        return identifiers

    def remove_sessions_for_identifiers(
        self,
        identifiers: list[str],
        exclude_sid: str | None = None,
    ) -> None:
        base_path = Path(self.path)
        _debug.pipeline(
            "http.session.remove_family",
            identifiers=len(identifiers),
            excluding=exclude_sid is not None,
        )
        for identifier in identifiers:
            if not _session_identifier_re.fullmatch(identifier):
                msg = "Identifier format incorrect, did you pass in a string instead of a list?"
                raise ValueError(msg)
            with self._locked_sid(identifier.ljust(_SESSION_KEY_LENGTH, "_")):
                for fn in (base_path / identifier[:2]).glob(identifier + "*"):
                    if exclude_sid is not None and fn.name == exclude_sid:
                        continue
                    self._remove_sid(fn.name)


_SESSION_JSON_PRIMITIVES = (str, int, float, bool, type(None))


def _merge_session_data(baseline: dict, local: dict, current: dict) -> dict:
    merged = dict(current)
    for key in baseline.keys() - local.keys():
        merged.pop(key, None)
    for key, value in local.items():
        if key in baseline and value == baseline[key]:
            continue
        before, latest = baseline.get(key), current.get(key)
        if (
            isinstance(before, dict)
            and isinstance(value, dict)
            and isinstance(latest, dict)
        ):
            merged[key] = _merge_session_data(before, value, latest)
        else:
            merged[key] = value
    return merged


def _coerce_session_value(value: Any) -> Any:
    if isinstance(value, _SESSION_JSON_PRIMITIVES):
        return value
    if isinstance(value, dict):
        coerced = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError(
                    f"Session dict keys must be str, got {type(k).__name__}: {k!r}"
                )
            coerced[k] = _coerce_session_value(v)
        return coerced
    if isinstance(value, (list, tuple)):
        return [_coerce_session_value(v) for v in value]
    raise TypeError(
        f"Session values must be JSON-serializable "
        f"(str/int/float/bool/None/list/dict/tuple), "
        f"got {type(value).__name__}: {value!r}"
    )


class Session(collections.abc.MutableMapping):
    __slots__ = (
        "_Session__baseline",
        "_Session__data",
        "can_save",
        "is_dirty",
        "is_new",
        "mtime",
        "rotation",
        "should_rotate",
        "sid",
        "store",
    )

    def __init__(self, data: dict[str, Any], sid: str, new: bool = False) -> None:
        self.can_save: bool = True
        self.__data: dict[str, Any] = dict(data)
        self.is_dirty: bool = False
        self.__baseline: bytes | None = None
        self.is_new: bool = new
        self.mtime: float | None = None
        self.should_rotate: bool = False
        self.rotation: tuple[Session, bool] | None = None
        self.sid: str = sid
        self.store: Any = None

    def snapshot(self) -> Session:
        snapshot = Session(copy.deepcopy(self.__data), self.sid, self.is_new)
        snapshot.__baseline = self.__baseline
        snapshot.can_save = self.can_save
        snapshot.is_dirty = self.is_dirty
        snapshot.mtime = self.mtime
        snapshot.should_rotate = self.should_rotate
        snapshot.store = self.store
        return snapshot

    def restore(self, snapshot: Session) -> None:
        self.__data = copy.deepcopy(snapshot.__data)
        self.__baseline = snapshot.__baseline
        self.sid = snapshot.sid
        self.is_new = snapshot.is_new
        self.is_dirty = snapshot.is_dirty
        self.mtime = snapshot.mtime
        self.can_save = snapshot.can_save
        self.should_rotate = snapshot.should_rotate
        self.rotation = None
        _debug.lifecycle(
            "http.session.restored", sid=self.sid[:8], uid=self.uid, is_new=self.is_new
        )

    def merge_changes(self, current: Session) -> None:
        _debug.logic(
            "http.session.merge",
            has_baseline=self.__baseline is not None,
            dirty=self.is_dirty,
        )
        if self.__baseline is None:
            return
        before = len(self.__data)  # debuglog
        self.__data = _merge_session_data(
            _loads(self.__baseline), self.__data, dict(current)
        )
        _debug.lifecycle(
            "http.session.merged", keys_before=before, keys_after=len(self.__data)
        )

    def __getitem__(self, item: str) -> Any:
        return self.__data[item]

    def __setitem__(self, item: str, value: Any) -> None:
        value = _coerce_session_value(value)
        if item not in self.__data or self.__data[item] != value:
            self.is_dirty = True
        self.__data[item] = value

    def __delitem__(self, item: str) -> None:
        del self.__data[item]
        self.is_dirty = True

    def __len__(self) -> int:
        return len(self.__data)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__data)

    def clear(self) -> None:
        self.__data.clear()
        self.is_dirty = True

    @property
    def uid(self) -> int | None:
        return self.get("uid")

    @uid.setter
    def uid(self, uid: int | None) -> None:
        self["uid"] = uid

    @property
    def db(self) -> str | None:
        return self.get("db")

    @db.setter
    def db(self, db: str | None) -> None:
        self["db"] = db

    @property
    def login(self) -> str | None:
        return self.get("login")

    @login.setter
    def login(self, login: str | None) -> None:
        self["login"] = login

    @property
    def context(self) -> dict[str, Any] | None:
        return self.get("context")

    @context.setter
    def context(self, context: dict[str, Any] | None) -> None:
        self["context"] = context

    @property
    def debug(self) -> str:
        return self.get("debug") or ""

    @debug.setter
    def debug(self, debug: str | None) -> None:
        self["debug"] = debug

    @property
    def session_token(self) -> str | None:
        return self.get("session_token")

    @session_token.setter
    def session_token(self, session_token: str | None) -> None:
        self["session_token"] = session_token

    def authenticate(self, env: Any, credential: dict[str, Any]) -> dict[str, Any]:
        wsgienv = {
            "interactive": True,
            "base_location": request.httprequest.url_root.rstrip("/"),
            "HTTP_HOST": request.httprequest.environ.get("HTTP_HOST", ""),
            "REMOTE_ADDR": request.httprequest.environ.get("REMOTE_ADDR", ""),
        }
        env = env(user=None, su=False)
        with _debug.perf(
            "http.session.authenticate",
            cr=getattr(env, "cr", None),
            auth_type=credential.get("type"),
        ) as span:
            auth_info = env["res.users"].authenticate(credential, wsgienv)
            span.set(uid=auth_info["uid"])
        pre_uid = auth_info["uid"]

        self.uid = None
        self["pre_login"] = credential["login"]
        self["pre_uid"] = pre_uid

        user = env["res.users"].browse(pre_uid)
        mfa_required = auth_info.get("mfa") != "skip" and bool(user._get_mfa_url())
        _debug.logic(
            "http.session.authenticated",
            db=env.registry.db_name,
            uid=pre_uid,
            mfa_required=mfa_required,
            auth_type=credential.get("type"),
        )
        if not mfa_required:
            self.finalize_login(env)

        if request and request.session is self and request.db == env.registry.db_name:
            request.env = env(user=self.uid, context=self.context)
            request.update_context(lang=get_lang(request.env(user=pre_uid)).code)
            _debug.lifecycle("http.session.request_env_rebound", uid=self.uid)

        return auth_info

    def finalize_login(self, env: Any) -> None:
        login = self.pop("pre_login")
        uid = self.pop("pre_uid")

        env = env(user=uid)
        with _debug.perf(
            "http.session.finalize_login", cr=getattr(env, "cr", None), uid=uid
        ):
            user_context = dict(env["res.users"].context_get())

            self._require_hard_rotation()
            self.update(
                {
                    "db": env.registry.db_name,
                    "login": login,
                    "uid": uid,
                    "context": user_context,
                    "session_token": env.user._get_session_token(self.sid),
                }
            )
        _debug.lifecycle(
            "http.session.login_finalized",
            db=env.registry.db_name,
            uid=uid,
            context_keys=len(user_context),
        )

    def logout(self, keep_db: bool = False) -> None:
        _debug.lifecycle("http.session.logout", uid=self.uid, keep_db=keep_db)
        db = self.db if keep_db else None
        debug = self.debug
        self.clear()
        self.update(prepare_default_session(), db=db, debug=debug)
        context = self.context
        assert context is not None
        context["lang"] = request.get_default_lang() if request else DEFAULT_LANG
        self._require_hard_rotation()

        if request and request.env is not None:
            _debug.lifecycle("http.session.post_logout_hook", db=request.db)
            get_ir_http(request.env)._post_logout()

    def _require_hard_rotation(self) -> None:
        self.should_rotate = True
        _debug.logic(
            "http.session.hard_rotation_required",
            staged=self.rotation is not None,
            staged_soft=self.rotation is not None and self.rotation[1],
        )
        if self.rotation is not None:
            original, soft = self.rotation
            if soft:
                # Leave the old family as well as its cookie. A stale request's
                # family cleanup must not be able to delete the logged-in or
                # logged-out successor of this authentication transition.
                self.sid = self.store.generate_key()
                self.pop("gc_previous_sessions", None)
            self.rotation = (original, False)

    def mark_dirty(self) -> None:
        self.is_dirty = True

    def mark_clean(self) -> None:
        self.is_dirty = False
        self.__baseline = _dumps_bytes(self.__data)

    def has_content_changed(self) -> bool:
        if self.__baseline is None:
            return self.is_dirty
        return _dumps_bytes(self.__data) != self.__baseline

    def is_modified(self) -> bool:
        return self.is_dirty or self.has_content_changed()

    def update_trace(self, request: Any) -> dict[str, Any] | None:
        if self.get("_trace_disable"):
            return None

        user_agent = request.httprequest.user_agent
        platform = user_agent.platform
        browser = user_agent.browser
        ip_address = request.httprequest.remote_addr
        now = int(time.time())
        for trace in self["_trace"]:
            if (
                trace["platform"] == platform
                and trace["browser"] == browser
                and trace["ip_address"] == ip_address
            ):
                if now - trace["last_activity"] >= 3600:
                    trace["last_activity"] = now
                    self.is_dirty = True
                    _debug.lifecycle("http.session.trace_refreshed", browser=browser)
                    return trace
                return None
        new_trace = {
            "platform": platform,
            "browser": browser,
            "ip_address": ip_address,
            "first_activity": now,
            "last_activity": now,
        }
        self["_trace"].append(new_trace)
        if len(self["_trace"]) > _TRACE_MAX_ENTRIES:
            oldest_idx = min(
                range(len(self["_trace"])),
                key=lambda i: self["_trace"][i]["last_activity"],
            )
            del self["_trace"][oldest_idx]
            _debug.lifecycle("http.session.trace_evicted", traces=len(self["_trace"]))
        self.is_dirty = True
        _debug.lifecycle(
            "http.session.trace_added", browser=browser, traces=len(self["_trace"])
        )
        return new_trace

    def _remove_old_sessions(self) -> None:
        if self.store is None:
            return
        self.store.remove_old_sessions(self)
