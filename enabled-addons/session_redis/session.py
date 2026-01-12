# Copyright 2016-2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import builtins
import json
import logging
from typing import TypeAlias

import odoo.http
from odoo.http import SESSION_LIFETIME
from odoo.tools._vendor.sessions import SessionStore

from . import json_encoding

# this was equal to the duration of the session garbage collector in
# odoo.http.session_gc()
DEFAULT_SESSION_TIMEOUT_ANONYMOUS = 60 * 60 * 3  # 3 hours in seconds

_logger = logging.getLogger(__name__)


# Many parts of the session store API operate not on full session keys, but only
# the first n characters of them (see odoo.http.STORED_SESSION_BYTES). In
# particular used by Devices, but Odoo in general seems to promise that this
# partial sid will be safe to store in the database, and can be used to later
# find sessions, even if those sessions are actually longer.
PartialSid: TypeAlias = str


class RedisSessionStore(SessionStore):
    """SessionStore that saves session to redis"""

    def __init__(
        self,
        redis,
        session_class=None,
        prefix="",
        expiration=None,
        anon_expiration=None,
    ):
        super().__init__(session_class=session_class)
        self.redis = redis
        if expiration is None:
            self.expiration = SESSION_LIFETIME
        else:
            self.expiration = expiration
        if anon_expiration is None:
            self.anon_expiration = DEFAULT_SESSION_TIMEOUT_ANONYMOUS
        else:
            self.anon_expiration = anon_expiration
        self.prefix = "session:"
        if prefix:
            self.prefix = f"{self.prefix}:{prefix}:"

    # Use the key generation method of the FileSystemSessionStore: it seems that
    # the one on the general SessionStore does not generate long enough keys to
    # support the device session rotation logic (SessionStore produces 40
    # character long keys, while the new rotation logic appears to assume a
    # length of at least 84).
    generate_key = odoo.http.FilesystemSessionStore.generate_key
    is_valid_key = odoo.http.FilesystemSessionStore.is_valid_key

    def build_key(self, sid):
        return f"{self.prefix}{sid}"

    def save(self, session):
        key = self.build_key(session.sid)

        # If the session has a deletion_time, it is slated for rotation, and
        # should be removed once the rotation window is over. See
        # odoo.http.SESSION_DELETION_TIMER.
        # Otherwise, allow to set a custom expiration for a session
        # such as a very short one for monitoring requests
        if session.uid:
            expiration = (
                session.get("deletion_time")
                or session.get("expiration")
                or self.expiration
            )
        else:
            expiration = (
                session.get("deletion_time")
                or session.get("expiration")
                or self.anon_expiration
            )
        if _logger.isEnabledFor(logging.DEBUG):
            if session.uid:
                user_msg = f"user '{session.login}' (id: {session.uid})"
            else:
                user_msg = "anonymous user"
            _logger.debug(
                f"saving session with key '{key}' and "
                f"expiration of {expiration} seconds for {user_msg}"
            )

        data = json.dumps(dict(session), cls=json_encoding.SessionEncoder).encode(
            "utf-8"
        )
        if self.redis.set(key, data):
            if not (expiration and isinstance(expiration, int)):
                expiration = DEFAULT_SESSION_TIMEOUT_ANONYMOUS
                expiration = DEFAULT_SESSION_TIMEOUT_ANONYMOUS
            return self.redis.expire(key, expiration)

    def delete(self, session):
        key = self.build_key(session.sid)
        _logger.debug(f"deleting session with key {key}")
        return self.redis.delete(key)

    def get(self, sid):
        if not self.is_valid_key(sid):
            _logger.debug(
                f"session with invalid sid '{sid}' has been asked, returning a new one"
            )
            return self.new()

        key = self.build_key(sid)
        saved = self.redis.get(key)
        if not saved:
            _logger.debug(
                f"session with non-existent key '{key}' has been asked, "
                "returning a new one"
            )
            return self.new()
        try:
            data = json.loads(saved.decode("utf-8"), cls=json_encoding.SessionDecoder)
        except ValueError:
            _logger.debug(
                f"session for key '{key}' has been asked but its json "
                "content could not be read, it has been reset"
            )
            data = {}
        return self.session_class(data, sid, False)

    def list(self):
        keys = self.redis.keys(f"{self.prefix}*")
        _logger.debug("a listing redis keys has been called")
        return [key[len(self.prefix) :] for key in keys]

    # The FilesystemSessionStore's rotate does not do anything file-system
    # specific so it can just be reused here
    rotate = odoo.http.FilesystemSessionStore.rotate

    def vacuum(self, *args, **kwargs):
        """Do not garbage collect the sessions

        Redis keys are automatically cleaned at the end of their
        expiration.
        """
        return None

    def delete_old_sessions(self, session):
        """
        # Deletion of rotated sessions is handled by updating the sessions'
        # expiry based on deletion_time in save(), so this method is redundant
        # when using a redis store.

        # While this method is not part of the generic SessionStore API, it is
        # defined on the file session store, and is used by the Session itself
        # as part of the session rotation (see odoo.http.Session._delete_old_sessions).
        """
        return

    def get_missing_session_identifiers(
        self, identifiers: builtins.list[PartialSid]
    ) -> set[PartialSid]:
        """
        Given a list of partial session ids, return a set of those session ids
        which no longer exist in the keystore.

        While this method is not part of the generic SessionStore API, it is
        defined on the file session store, and is used by Odoo's devices to
        figure out what needs to be revoked
        (see odoo.addons.base.models.res_device.ResDeviceLog.__update_revoked).
        """
        identifiers = set(identifiers)
        not_found = set()
        for partial_sid in identifiers:
            try:
                next(
                    self.redis.scan_iter(
                        match=f"{self.prefix}{partial_sid}*",
                        count=1,
                    )
                )
            except StopIteration:
                # No matches found
                not_found.add(partial_sid)

        return not_found

    def delete_from_identifiers(self, identifiers: builtins.list[PartialSid]):
        """
        Given a list of partial session ids, remove any that are in the session store.

        While this method is not part of the generic SessionStore API, it is
        defined on the file session store, and is used by devices when revoking
        device sessions (see odoo.addons.base.models.res_device.ResDevice._revoke).
        """
        patterns_to_unlink = []
        for identifier in identifiers:
            # Avoid removing a session if it does not match an identifier. See this same
            # comment in odoo.http.FileSessionStore.delete_from_identifiers.
            if not odoo.http._session_identifier_re.match(identifier):
                raise ValueError(
                    "Identifier format incorrect, did you pass in a string instead ",
                    "of a list?",
                )
            patterns_to_unlink.append(f"{self.prefix}{identifier}*")
        keys_to_unlink = []
        for pattern in patterns_to_unlink:
            keys_to_unlink.extend(self.redis.scan_iter(match=pattern))
        if keys_to_unlink:
            self.redis.delete(*keys_to_unlink)
