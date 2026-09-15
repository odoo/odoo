import base64
import contextlib
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

from .constants import SESSION_DELETION_TIMER, SESSION_LIFETIME, STORED_SESSION_BYTES
from .exceptions import SessionExpiredException
from .session import Session

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
