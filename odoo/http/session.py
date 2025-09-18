"""Session storage and management."""

import base64
import collections.abc
import contextlib
import os
import re
import time
from hashlib import sha512
from pathlib import Path

from odoo.libs._vendor import sessions
from odoo.libs.json import dumps_bytes as _fast_dumps_bytes
from odoo.libs.json import loads as _fast_loads
from odoo.service import security
from odoo.tools import get_lang

from .constants import (
    DEFAULT_LANG,
    SESSION_DELETION_TIMER,
    SESSION_LIFETIME,
    STORED_SESSION_BYTES,
    get_default_session,
)

_base64_urlsafe_re = re.compile(r"^[A-Za-z0-9_-]{84}$")
_session_identifier_re = re.compile(r"^[A-Za-z0-9_-]{%s}$" % STORED_SESSION_BYTES)


class FilesystemSessionStore(sessions.FilesystemSessionStore):
    """Place where to load and save session objects."""

    def get_session_filename(self, sid):
        # scatter sessions across 4096 (64^2) directories
        if not self.is_valid_key(sid):
            raise ValueError(f"Invalid session id {sid!r}")
        return str(Path(self.path, sid[:2], sid))

    def save(self, session):
        dirname = Path(self.get_session_filename(session.sid)).parent
        if not dirname.is_dir():
            with contextlib.suppress(OSError):
                dirname.mkdir(mode=0o0755)
        super().save(session)

    def delete_old_sessions(self, session):
        if "gc_previous_sessions" in session:
            if session["create_time"] + SESSION_DELETION_TIMER < time.time():
                self.delete_from_identifiers([session.sid[:STORED_SESSION_BYTES]])
                del session["gc_previous_sessions"]
                self.save(session)

    def get(self, sid):
        # retro compatibility
        old_path = Path(super().get_session_filename(sid))
        session_path = Path(self.get_session_filename(sid))
        if old_path.is_file() and not session_path.is_file():
            dirname = session_path.parent
            if not dirname.is_dir():
                with contextlib.suppress(OSError):
                    dirname.mkdir(mode=0o0755)
            with contextlib.suppress(OSError):
                old_path.rename(session_path)
        return super().get(sid)

    def rotate(self, session, env, soft=False):
        # With a soft rotation, things like the CSRF token will still work. It's used for rotating
        # the session in a way that half the bytes remain to identify the user and the other half
        # to authenticate the user. Meanwhile with a hard rotation the entire session id is changed,
        # which is useful in cases such as logging the user out.
        if soft:
            # Multiple network requests can occur at the same time, all using the old session.
            # We don't want to create a new session for each request, it's better to reference the one already made.
            static = session.sid[:STORED_SESSION_BYTES]
            recent_session = self.get(session.sid)
            if "next_sid" in recent_session:
                # A new session has already been saved on disk by a concurrent request,
                # the _save_session is going to simply use session.sid to set a new cookie.
                session.sid = recent_session["next_sid"]
                return
            next_sid = static + self.generate_key()[STORED_SESSION_BYTES:]
            session["next_sid"] = next_sid
            session["deletion_time"] = time.time() + SESSION_DELETION_TIMER
            self.save(session)
            # Now prepare the new session
            session["gc_previous_sessions"] = True
            session.sid = next_sid
            del session["deletion_time"]
            del session["next_sid"]
        else:
            self.delete(session)
            session.sid = self.generate_key()
        if session.uid:
            assert env, "saving this session requires an environment"
            session.session_token = security.compute_session_token(session, env)
        session.should_rotate = False
        session["create_time"] = time.time()
        self.save(session)

    def vacuum(self, max_lifetime=SESSION_LIFETIME):
        from .application import root  # lazy import

        threshold = time.time() - max_lifetime
        base_path = Path(root.session_store.path)
        for path in base_path.glob("*/*"):
            with contextlib.suppress(OSError):
                if path.stat().st_mtime < threshold:
                    path.unlink()

    def generate_key(self, salt=None):
        # The generated key is case sensitive (base64) and the length is 84 chars.
        # In the worst-case scenario, i.e. in an insensitive filesystem (NTFS for example)
        # taking into account the proportion of characters in the pool and a length
        # of 42 (stored part in the database), the entropy for the base64 generated key
        # is 217.875 bits which is better than the 160 bits entropy of a hexadecimal key
        # with a length of 40 (method ``generate_key`` of ``SessionStore``).
        # The risk of collision is negligible in practice.
        # Formulas:
        #   - L: length of generated word
        #   - p_char: probability of obtaining the character in the pool
        #   - n: size of the pool
        #   - k: number of generated word
        #   Entropy = - L * sum(p_char * log2(p_char))
        #   Collision ~= (1 - exp((-k * (k - 1)) / (2 * (n**L))))
        key = str(time.time()).encode() + os.urandom(64)
        hash_key = sha512(key).digest()[:-1]  # prevent base64 padding
        return base64.urlsafe_b64encode(hash_key).decode("utf-8")

    def is_valid_key(self, key):
        return _base64_urlsafe_re.match(key) is not None

    def get_missing_session_identifiers(self, identifiers):
        """
        :param identifiers: session identifiers whose file existence must be checked
                            identifiers are a part session sid (first 42 chars)
        :type identifiers: iterable
        :return: the identifiers which are not present on the filesystem
        :rtype: set
        """
        # There are a lot of session files.
        # Use the param ``identifiers`` to select the necessary directories.
        # In the worst case, we have 4096 directories (64^2).
        identifiers = set(identifiers)
        base = Path(self.path)
        directories = {
            str(base / identifier[:2]) for identifier in identifiers
        }
        # Remove the identifiers for which a file is present on the filesystem.
        for directory in directories:
            with (
                contextlib.suppress(OSError),
                os.scandir(directory) as session_files,
            ):
                identifiers.difference_update(sf.name[:42] for sf in session_files)
        return identifiers

    def delete_from_identifiers(self, identifiers: list):
        """Delete session files matching the given identifiers."""
        files_to_unlink: list[Path] = []
        base_path = Path(self.path)
        for identifier in identifiers:
            # Avoid to remove a session if it does not match an identifier.
            # This prevent malicious user to delete sessions from a different
            # database by specifying a custom ``res.device.log``.
            if not _session_identifier_re.match(identifier):
                raise ValueError(
                    "Identifier format incorrect, did you pass in a string instead of a list?"
                )
            parent_dir = base_path / identifier[:2]
            if parent_dir.is_relative_to(base_path):
                files_to_unlink.extend(parent_dir.glob(identifier + "*"))
        for fn in files_to_unlink:
            with contextlib.suppress(OSError):
                fn.unlink()


class Session(collections.abc.MutableMapping):
    """Structure containing data persisted across requests."""

    __slots__ = (
        "_Session__data",
        "can_save",
        "is_dirty",
        "is_new",
        "should_rotate",
        "sid",
    )

    def __init__(self, data, sid, new=False):
        self.can_save = True
        self.__data = {}
        self.update(data)
        self.is_dirty = False
        self.is_new = new
        self.should_rotate = False
        self.sid = sid

    def __getitem__(self, item):
        return self.__data[item]

    def __setitem__(self, item, value):
        if not isinstance(value, (str, int, float, bool, type(None))):
            value = _fast_loads(_fast_dumps_bytes(value))
        if item not in self.__data or self.__data[item] != value:
            self.is_dirty = True
        self.__data[item] = value

    def __delitem__(self, item):
        del self.__data[item]
        self.is_dirty = True

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)

    def clear(self):
        self.__data.clear()
        self.is_dirty = True

    #
    # Session properties
    #
    @property
    def uid(self):
        return self.get("uid")

    @uid.setter
    def uid(self, uid):
        self["uid"] = uid

    @property
    def db(self):
        return self.get("db")

    @db.setter
    def db(self, db):
        self["db"] = db

    @property
    def login(self):
        return self.get("login")

    @login.setter
    def login(self, login):
        self["login"] = login

    @property
    def context(self):
        return self.get("context")

    @context.setter
    def context(self, context):
        self["context"] = context

    @property
    def debug(self):
        return self.get("debug")

    @debug.setter
    def debug(self, debug):
        self["debug"] = debug

    @property
    def session_token(self):
        return self.get("session_token")

    @session_token.setter
    def session_token(self, session_token):
        self["session_token"] = session_token

    #
    # Session methods
    #
    def authenticate(self, env, credential):
        """
        Authenticate the current user with the given db, login and
        credential. If successful, store the authentication parameters in
        the current session, unless multi-factor-auth (MFA) is
        activated. In that case, that last part will be done by
        :ref:`finalize`.

        .. versionchanged:: saas-15.3
           The current request is no longer updated using the user and
           context of the session when the authentication is done using
           a database different than request.db. It is up to the caller
           to open a new cursor/registry/env on the given database.
        """
        from . import request  # lazy import

        wsgienv = {
            "interactive": True,
            "base_location": request.httprequest.url_root.rstrip("/"),
            "HTTP_HOST": request.httprequest.environ["HTTP_HOST"],
            "REMOTE_ADDR": request.httprequest.environ["REMOTE_ADDR"],
        }
        env = env(user=None, su=False)
        auth_info = env["res.users"].authenticate(credential, wsgienv)
        pre_uid = auth_info["uid"]

        self.uid = None
        self["pre_login"] = credential["login"]
        self["pre_uid"] = pre_uid

        # if 2FA is disabled we finalize immediately
        user = env["res.users"].browse(pre_uid)
        if auth_info.get("mfa") == "skip" or not user._mfa_url():
            self.finalize(env)

        if request and request.session is self and request.db == env.registry.db_name:
            request.env = env(user=self.uid, context=self.context)
            request.update_context(lang=get_lang(request.env(user=pre_uid)).code)

        return auth_info

    def finalize(self, env):
        """
        Finalizes a partial session, should be called on MFA validation
        to convert a partial / pre-session into a logged-in one.
        """
        login = self.pop("pre_login")
        uid = self.pop("pre_uid")

        env = env(user=uid)
        user_context = dict(env["res.users"].context_get())

        self.should_rotate = True
        self.update(
            {
                "db": env.registry.db_name,
                "login": login,
                "uid": uid,
                "context": user_context,
                "session_token": env.user._compute_session_token(self.sid),
            }
        )

    def logout(self, keep_db=False):
        from . import request  # lazy import

        db = self.db if keep_db else get_default_session()["db"]  # None
        debug = self.debug
        self.clear()
        self.update(get_default_session(), db=db, debug=debug)
        self.context["lang"] = request.default_lang() if request else DEFAULT_LANG
        self.should_rotate = True

        if request and request.env:
            request.env["ir.http"]._post_logout()

    def touch(self):
        self.is_dirty = True

    def update_trace(self, request):
        """
        :return: dict if a device log has to be inserted, ``None`` otherwise
        """
        if self.get("_trace_disable"):
            # To avoid generating useless logs, e.g. for automated technical sessions,
            # a session can be flagged with `_trace_disable`. This should never be done
            # without a proper assessment of the consequences for auditability.
            # Non-admin users have no direct or indirect way to set this flag, so it can't
            # be abused by unprivileged users. Such sessions will of course still be
            # subject to all other auditing mechanisms (server logs, web proxy logs,
            # metadata tracking on modified records, etc.)
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
                # If the device logs are not up to date (i.e. not updated for one hour or more)
                if now - trace["last_activity"] >= 3600:
                    trace["last_activity"] = now
                    self.is_dirty = True
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
        self.is_dirty = True
        return new_trace

    def _delete_old_sessions(self):
        from .application import root  # lazy import

        root.session_store.delete_old_sessions(self)
