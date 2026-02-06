from __future__ import annotations

import glob
import json
import logging
import os
import re
import secrets
import tempfile
import time
import typing
from collections.abc import MutableMapping
from contextlib import suppress
from datetime import datetime
from http import HTTPStatus
from zlib import adler32

from odoo.api import Environment
from odoo.tools import consteq, get_lang

if typing.TYPE_CHECKING:
    from collections.abc import Iterable
    from .requestlib import Request


_logger = logging.getLogger('odoo.http')


DEFAULT_LANG = 'en_US'
""" The default lang to use when the browser doesn't specify it. """

SESSION_LIFETIME = 60 * 60 * 24 * 7  # 1 week
"""
The default duration of a user session cookie. Inactive sessions are
reaped server-side as well with a threshold that can be set via an
optional config parameter `sessions.max_inactivity_seconds`.
"""

SESSION_ROTATION_INTERVAL = 60 * 60 * 3  # 3 hours
"""
The default duration before a session is rotated, changing the session
id (also on the cookie) but keeping the same content.
"""

SESSION_DELETION_TIMER = 120
"""
After a session is rotated, the session should be kept for a couple of
seconds to account for network delay between multiple requests which are
made at the same time and all use the same old cookie.
"""

STORED_SESSION_BYTES = 42
"""
The amount of bytes of the session that will remain static and can be
used for calculating the csrf token and be stored inside the database.
"""

DEVICE_ACTIVITY_UPDATE_FREQUENCY = 3600  # 1 hour
""" The frequency with which a device's activity is updated. """

# TODO: remove `84` length when v18.4 is deprecated
# This will invalidate sessions generated with the old sid generator
_base64_urlsafe_re = re.compile(r'^[A-Za-z0-9_-]{84,86}$')
_session_identifier_re = re.compile(r'^[A-Za-z0-9_-]{42}$')


class SessionExpiredException(Exception):
    http_status = HTTPStatus.FORBIDDEN


class CheckIdentityException(SessionExpiredException):
    """ Exception raised when a user is requested to re-authenticate. """
    loglevel = logging.DEBUG


class Session(MutableMapping):
    """ Structure containing data persisted across requests. """
    __slots__ = (
        '_Session__data',
        'can_save',
        'is_dirty',
        'is_new',
        'should_rotate',
        'sid',
    )

    def __init__(self, data, sid, /, new: bool = False):
        self.can_save: bool = True
        self.__data = {}
        self.update(data)
        self.is_dirty: bool = False
        self.is_new = new
        self.should_rotate: bool = False
        self.sid = sid

    def __getitem__(self, item):
        return self.__data[item]

    def __setitem__(self, item, value):
        value = json.loads(json.dumps(value))
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
        return self.get('uid')

    @uid.setter
    def uid(self, uid):
        self['uid'] = uid

    @property
    def db(self):
        return self.get('db')

    @db.setter
    def db(self, db):
        self['db'] = db

    @property
    def login(self):
        return self.get('login')

    @login.setter
    def login(self, login):
        self['login'] = login

    @property
    def context(self):
        return self.get('context')

    @context.setter
    def context(self, context):
        self['context'] = context

    @property
    def debug(self):
        return self.get('debug')

    @debug.setter
    def debug(self, debug):
        self['debug'] = debug

    @property
    def session_token(self):
        return self.get('session_token')

    @session_token.setter
    def session_token(self, session_token):
        self['session_token'] = session_token


def get_default_session() -> dict:
    """ The dictionary to initialise a new session with. """
    return {
        'context': {},  # 'lang': request.default_lang()  # must be set at runtime
        'create_time': time.time(),
        'db': None,
        'debug': '',
        'login': None,
        'uid': None,
        'session_token': None,
        '_devices': {},
    }


def get_session_max_inactivity(env: Environment | None) -> int:
    if not env or env.cr.closed:
        return SESSION_LIFETIME

    ICP = env['ir.config_parameter'].sudo()
    return ICP.get_int('sessions.max_inactivity_seconds') or SESSION_LIFETIME


def authenticate(session: Session, env: Environment, credential: dict) -> dict:
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
    wsgienv = {
        'interactive': True,
        'base_location': request.httprequest.url_root.rstrip('/'),
        'HTTP_HOST': request.httprequest.environ['HTTP_HOST'],
        'REMOTE_ADDR': request.httprequest.environ['REMOTE_ADDR'],
    }
    env = env(user=None, su=False)
    auth_info = env['res.users'].authenticate(credential, wsgienv)
    pre_uid = auth_info['uid']

    session.uid = None
    session['pre_login'] = credential['login']
    session['pre_uid'] = pre_uid

    env = env(user=pre_uid)

    # if 2FA is disabled we finalize immediately
    user = env['res.users'].browse(pre_uid)
    if auth_info.get('mfa') == 'skip' or not user._mfa_url():
        finalize(session, env)

    if request and request.session is session and request.db == env.registry.db_name:
        request.env = env(user=session.uid, context=session.context)
        request.update_context(lang=get_lang(request.env(user=pre_uid)).code)

    return auth_info


def finalize(session: Session, env: Environment) -> None:
    """
    Finalizes a partial session, should be called on MFA validation
    to convert a partial / pre-session into a logged-in one.
    """
    login = session.pop('pre_login')
    uid = session.pop('pre_uid')

    env = env(user=uid)
    user_context = dict(env['res.users'].context_get())

    session.should_rotate = True
    session.update({
        'db': env.registry.db_name,
        'login': login,
        'uid': uid,
        'context': user_context,
        'session_token': env.user._compute_session_token(session.sid),
    })


def logout(session: Session, *, keep_db: bool = False) -> None:
    db = session.db if keep_db else get_default_session()['db']  # None
    debug = session.debug
    session.clear()
    session.update(get_default_session(), db=db, debug=debug)
    session.context['lang'] = request.default_lang() if request else DEFAULT_LANG
    session.should_rotate = True

    if request and request.env:
        request.env['ir.http']._post_logout()


def touch(session: Session):
    session.is_dirty = True


def get_device(session: Session, request: Request) -> dict:
    """
    :return: dict that corresponds to the current device
    """
    # TODO (v20): remove backward compatibility
    if '_devices' not in session:
        session['_devices'] = {}
        session.is_dirty = True

    ip_address = request.httprequest.remote_addr
    user_agent = request.httprequest.user_agent.string
    # No collision with different IP addresses
    device_key = f'{ip_address.encode().hex()}{adler32(user_agent.encode()):x}'

    with suppress(KeyError):
        return session['_devices'][device_key]

    geoip = GeoIP(ip_address)

    session['_devices'][device_key] = new_device = {
        'ip_address': ip_address,
        'user_agent': user_agent,
        'first_activity': int(datetime.now().timestamp()),
        'last_activity': None,
        'country': geoip.country.name,
        'city': geoip.city.name,
    }
    session.is_dirty = True
    return new_device


def update_device(session: Session, request: Request) -> dict | None:
    """
    :return: dict if the current device has been updated, ``None`` otherwise
    """
    if session.get('_trace_disable'):
        # To avoid generating useless logs, e.g. for automated technical sessions,
        # a session can be flagged with `_trace_disable`. This should never be done
        # without a proper assessment of the consequences for auditability.
        # Non-admin users have no direct or indirect way to set this flag, so it can't
        # be abused by unprivileged users. Such sessions will of course still be
        # subject to all other auditing mechanisms (server logs, web proxy logs,
        # metadata tracking on modified records, etc.)
        return None

    device = get_device(session, request)

    now = int(datetime.now().timestamp())
    if device['last_activity'] \
        and (now - device['last_activity']) < DEVICE_ACTIVITY_UPDATE_FREQUENCY:
        return None

    device['last_activity'] = now
    session.is_dirty = True
    return device


def delete_old_sessions(session: Session) -> None:
    root.session_store.delete_old_sessions(session)


def update_session_token(session: Session, env: Environment) -> None:
    """
    Compute the session token of the current user (determined using
    ``session['uid']``) and save it in the session.

    :param env: An environment to access ``res.users``.
    """
    user = env['res.users'].browse(session['uid'])
    session['session_token'] = user._compute_session_token(session.sid)


def check(session: Session, request_or_env: Request | Environment) -> None:
    """
    Verify that the session is not expired, and that the token saved
    in the session matches the session token computed for the user.

    The session token changes when some sensitive informations about
    the user changed: active, login, password, ...

    On success, it logs the request in the ``res.device.log`` and
    returns.

    On failure, it logs the session out (but keep the database) and
    raises a :class:`SessionExpiredException` with an appropriate
    message. See also :meth:`logout`.

    :raises SessionExpiredException: when the session is expired.
    """
    if isinstance(request_or_env, Environment):
        request, env = None, request_or_env
    else:
        request, env = request_or_env, request_or_env.env
    del request_or_env
    delete_old_sessions(session)
    # Make sure we don't use a deleted session that can be saved again
    if session.get('deletion_time', float('+inf')) <= time.time():
        logout(session, keep_db=True)
        e = "session is too old"
        raise SessionExpiredException(e)
    user = env['res.users'].browse(session['uid'])
    expected = user._compute_session_token(session.sid)
    if expected:
        # TODO: use secrets.compare_digest
        if consteq(expected, session['session_token']):
            if request:
                env['res.device.log']._update_device(request)
            return
        # If the session token is not valid, we check if the legacy
        # version works and convert the session token to the new one
        legacy_expected = user._legacy_session_token_hash_compute(session.sid)
        if legacy_expected and consteq(legacy_expected, session['session_token']):
            session['session_token'] = expected
            if request:
                env['res.device.log']._update_device(request)
            return
    logout(session, keep_db=True)
    e = "session token mismatch; likely because the user credentials changed"
    raise SessionExpiredException(e)


class SessionStore:
    """ Odoo implementation of the filesystem session store. """

    def __init__(self, /, path: str | None = None, session_cls: type[Session] = Session):
        """
        :param path: the path to the folder used for storing the sessions.
            If not provided the default temporary directory is used.
        :param session_cls: The session class to use.
            Defaults to :class:`Session`.
        """
        if path is None:
            path = os.path.join(tempfile.gettempdir(), 'odoo_session_store')
            os.makedirs(path, exist_ok=True)
        self.path: str = path
        self.session_cls: type[Session] = session_cls

    def generate_key(self) -> str:
        """ Generate a 86-chars long token with 64 bytes of entropy. """
        # To be secure, random token must have at least 256 bits (32 bytes) of entropy.
        # Here we decide the use a token of 512 bits (2x32 bytes). The session (and
        # cookie) will use the full 64-bytes long token. We will also store the first 32
        # bytes in the `res.device.log` model. In case the `res.device.log` model gets
        # compromised (e.g. data breach), pirates will not be able to exploit the
        # session token because they will lack the remaining 32 bytes.
        return secrets.token_urlsafe(64)

    def is_valid_session_id(self, sid: str) -> bool:
        """ Check if a session identifier has the correct format. """
        return _base64_urlsafe_re.fullmatch(sid) is not None

    def new(self) -> Session:
        """ Generate a new session. """
        return self.session_cls({}, self.generate_key(), new=True)

    def get_session_path(self, sid: str) -> str:
        """Get complete session path."""
        # scatter sessions across 4096 (64^2) directories
        if not self.is_valid_session_id(sid):
            raise ValueError(f'Invalid session id {sid!r}')
        return os.path.join(self.path, sid[:2], sid)

    def save(self, session: Session) -> None:
        """ Save a session. """
        # Perform an atomic save
        session_path = self.get_session_path(session.sid)
        # Create session in a transaction file in the
        # root directory of file session store
        fd, tmp = tempfile.mkstemp(suffix='.__tx_sess__', dir=self.path)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(dict(session), f)
        # Move the transaction file to the correct sub directory
        with suppress(OSError):
            try:
                os.replace(tmp, session_path)
            except FileNotFoundError:
                # Ensure directory then retry
                session_dir = os.path.dirname(session_path)
                os.mkdir(session_dir, mode=0o755)
                os.replace(tmp, session_path)
            os.chmod(session_path, 0o644)

    def delete(self, session: Session) -> None:
        """ Delete a session. """
        session_path = self.get_session_path(session.sid)
        with suppress(OSError):
            os.unlink(session_path)

    def get(self, sid: str, *, keep_sid: bool = False) -> Session:
        """
        Get a session for the sid.

        It returns a new session (with a new sid, not matter `keep_sid`)
        in case the input sid is invalid.

        It returns a new session (with a same or new sid depending on
        `keep_sid`) in case the sid is valid but that the session wasn't
        found on disk.
        """
        if not self.is_valid_session_id(sid):
            return self.new()

        try:

            with open(self.get_session_path(sid), encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    return self.session_cls(data, sid, new=False)
                except ValueError:
                    _logger.debug("Could not load session data. Use empty session.", exc_info=True)
                    # The session file exists on the filesystem (the sid must be retained)
                    return self.session_cls({}, sid, new=False)

        except OSError:
            if keep_sid:
                _logger.debug("Could not load session from disk. Use empty session.", exc_info=True)
                return self.session_cls({}, sid, new=False)
            _logger.debug("Could not load session from disk. Use new session.", exc_info=True)
            return self.new()

    def rotate(self, session: Session, env: Environment, *, soft: bool = False) -> None:
        """
        Rotate the session sid.

        With a soft rotation, things like the CSRF token will still work. It's
        used for rotating the session in a way that half the bytes remain to
        identify the user and the other half to authenticate the user.

        Meanwhile with a hard rotation the entire session id is changed, which
        is useful in cases such as logging the user out.
        """
        if soft:
            # Multiple network requests can occur at the same time, all using the old session.
            # We don't want to create a new session for each request, it's better to reference the one already made.
            static = session.sid[:STORED_SESSION_BYTES]
            recent_session = self.get(session.sid)
            if 'next_sid' in recent_session:
                # A new session has already been saved on disk by a concurrent request,
                # the _save_session is going to simply use session.sid to set a new cookie.
                session.sid = recent_session['next_sid']
                return
            next_sid = static + self.generate_key()[STORED_SESSION_BYTES:]
            session['next_sid'] = next_sid
            session['deletion_time'] = time.time() + SESSION_DELETION_TIMER
            self.save(session)
            # Now prepare the new session
            session['gc_previous_sessions'] = True
            session.sid = next_sid
            del session['deletion_time']
            del session['next_sid']
        else:
            self.delete(session)
            session.sid = self.generate_key()
        if session.uid:
            assert env, "saving this session requires an environment"
            update_session_token(session, env)
        session.should_rotate = False
        session['create_time'] = time.time()
        self.save(session)

    def vacuum(self, max_lifetime=SESSION_LIFETIME):
        """ Remove expired session files older than the given lifetime. """
        threshold = time.time() - max_lifetime
        for fname in glob.iglob(os.path.join(self.path, '*', '*')):
            path = os.path.join(self.path, fname)
            with suppress(OSError):
                if os.path.getmtime(path) < threshold:
                    os.unlink(path)

    def get_missing_session_identifiers(self, identifiers: Iterable[str]) -> set[str]:
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
        directories = {
            os.path.normpath(os.path.join(self.path, identifier[:2]))
            for identifier in identifiers
        }
        # Remove the identifiers for which a file is present on the filesystem.
        for directory in directories:
            with suppress(OSError), os.scandir(directory) as session_files:
                identifiers.difference_update(sf.name[:42] for sf in session_files)
        return identifiers

    def delete_from_identifiers(self, identifiers: Iterable[str]) -> None:
        """ Delete session files matching identifiers within the session store. """
        files_to_unlink = []
        for identifier in identifiers:
            # Avoid to remove a session if it does not match an identifier.
            # This prevent malicious user to delete sessions from a different
            # database by specifying a custom ``res.device.log``.
            if not _session_identifier_re.match(identifier):
                continue
            normalized_path = os.path.normpath(os.path.join(self.path, identifier[:2], identifier + '*'))
            if normalized_path.startswith(self.path):
                files_to_unlink.extend(glob.glob(normalized_path))
        for fn in files_to_unlink:
            with suppress(OSError):
                os.unlink(fn)

    def delete_old_sessions(self, session: Session) -> None:
        """ Delete old sessions based on expiration and cleanup flag value. """
        if 'gc_previous_sessions' in session:
            if session['create_time'] + SESSION_DELETION_TIMER < time.time():
                self.delete_from_identifiers([session.sid[:STORED_SESSION_BYTES]])
                del session['gc_previous_sessions']
                self.save(session)


# ruff: noqa: E402
from .geoip import GeoIP
from .requestlib import request
from .router import root
