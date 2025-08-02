# -*- coding: utf-8 -*-
r"""
    Vendored copy of https://github.com/pallets/werkzeug/blob/2b2c4c3dd3cf7389e9f4aa06371b7332257c6289/src/werkzeug/contrib/sessions.py

    werkzeug.contrib was removed from werkzeug 1.0. sessions (and secure
    cookies) were moved to the secure-cookies package. Problem is distros
    are starting to update werkzeug to 1.0 without having secure-cookies
    (e.g. Arch has done so, Debian has updated python-werkzeug in
    "experimental"), which will be problematic once that starts trickling
    down onto more stable distros and people start deploying that.

    Edited some to fix imports and remove some compatibility things
    (mostly PY2) and the unnecessary (to us) SessionMiddleware

    :copyright: 2007 Pallets
    :license: BSD-3-Clause
"""
import logging
import os
import re
import tempfile
from hashlib import sha1
from os import path, replace as rename
from odoo.tools.misc import pickle
from time import time

from werkzeug.datastructures import CallbackDict

_logger = logging.getLogger(__name__)
_sha1_re = re.compile(r"^[a-f0-9]{40}$")


def generate_key(salt=None):
    if salt is None:
        salt = repr(salt).encode("ascii")
    return sha1(b"".join([salt, str(time()).encode("ascii"), os.urandom(30)])).hexdigest()


class ModificationTrackingDict(CallbackDict):
    __slots__ = ("modified", "on_update")

    def __init__(self, *args, **kwargs):
        def on_update(self):
            self.modified = True

        self.modified = False
        CallbackDict.__init__(self, on_update=on_update)
        dict.update(self, *args, **kwargs)

    def copy(self):
        """Create a flat copy of the dict."""
        missing = object()
        result = object.__new__(self.__class__)
        for name in self.__slots__:
            val = getattr(self, name, missing)
            if val is not missing:
                setattr(result, name, val)
        return result

    def __copy__(self):
        return self.copy()


class Session(ModificationTrackingDict):
    """Subclass of a dict that keeps track of direct object changes.  Changes
    in mutable structures are not tracked, for those you have to set
    `modified` to `True` by hand.
    """

    __slots__ = ModificationTrackingDict.__slots__ + ("sid", "new")

    def __init__(self, data, sid, new=False):
        ModificationTrackingDict.__init__(self, data)
        self.sid = sid
        self.new = new

    def __repr__(self):
        return "<%s %s%s>" % (
            self.__class__.__name__,
            dict.__repr__(self),
            "*" if self.should_save else "",
        )

    @property
    def should_save(self):
        """True if the session should be saved.

        .. versionchanged:: 0.6
           By default the session is now only saved if the session is
           modified, not if it is new like it was before.
        """
        return self.modified


class SessionStore(object):
    """Baseclass for all session stores.  The Werkzeug contrib module does not
    implement any useful stores besides the filesystem store, application
    developers are encouraged to create their own stores.

    :param session_class: The session class to use.  Defaults to
                          :class:`Session`.
    """

    def __init__(self, session_class=None):
        if session_class is None:
            session_class = Session
        self.session_class = session_class

    def is_valid_key(self, key):
        """Check if a key has the correct format."""
        return _sha1_re.match(key) is not None

    def generate_key(self, salt=None):
        """Simple function that generates a new session key."""
        return generate_key(salt)

    def new(self):
        """Generate a new session."""
        return self.session_class({}, self.generate_key(), True)

    def save(self, session):
        """Save a session."""

    def save_if_modified(self, session):
        """Save if a session class wants an update."""
        if session.should_save:
            self.save(session)

    def delete(self, session):
        """Delete a session."""

    def get(self, sid):
        """Get a session for this sid or a new session object.  This method
        has to check if the session key is valid and create a new session if
        that wasn't the case.
        """
        return self.session_class({}, sid, True)


#: used for temporary files by the filesystem session store
_fs_transaction_suffix = ".__wz_sess"


class FilesystemSessionStore(SessionStore):
    """Simple example session store that saves sessions on the filesystem.
    This store works best on POSIX systems and Windows Vista / Windows
    Server 2008 and newer.

    .. versionchanged:: 0.6
       `renew_missing` was added.  Previously this was considered `True`,
       now the default changed to `False` and it can be explicitly
       deactivated.

    :param path: the path to the folder used for storing the sessions.
                 If not provided the default temporary directory is used.
    :param filename_template: a string template used to give the session
                              a filename.  ``%s`` is replaced with the
                              session id.
    :param session_class: The session class to use.  Defaults to
                          :class:`Session`.
    :param renew_missing: set to `True` if you want the store to
                          give the user a new sid if the session was
                          not yet saved.
    """

    def __init__(
        self,
        path=None,
        filename_template="werkzeug_%s.sess",
        session_class=None,
        renew_missing=False,
        mode=0o644,
    ):
        SessionStore.__init__(self, session_class)
        if path is None:
            path = tempfile.gettempdir()
        self.path = path
        assert not filename_template.endswith(_fs_transaction_suffix), (
            "filename templates may not end with %s" % _fs_transaction_suffix
        )
        self.filename_template = filename_template
        self.renew_missing = renew_missing
        self.mode = mode

    def get_session_filename(self, sid):
        # out of the box, this should be a strict ASCII subset but
        # you might reconfigure the session object to have a more
        # arbitrary string.
        return path.join(self.path, self.filename_template % sid)

    def save(self, session):
        fn = self.get_session_filename(session.sid)
        fd, tmp = tempfile.mkstemp(suffix=_fs_transaction_suffix, dir=self.path)
        f = os.fdopen(fd, "wb")
        try:
            pickle.dump(dict(session), f, pickle.HIGHEST_PROTOCOL)
        finally:
            f.close()
        try:
            rename(tmp, fn)
            os.chmod(fn, self.mode)
        except (IOError, OSError):
            pass

    def delete(self, session):
        fn = self.get_session_filename(session.sid)
        try:
            os.unlink(fn)
        except OSError:
            pass

    def get(self, sid):
        if not self.is_valid_key(sid):
            return self.new()
        try:
            f = open(self.get_session_filename(sid), "rb")
        except IOError:
            _logger.debug('Could not load session from disk. Use empty session.', exc_info=True)
            if self.renew_missing:
                return self.new()
            data = {}
        else:
            try:
                try:
                    data = pickle.load(f, errors={})
                except Exception:
                    _logger.debug('Could not load session data. Use empty session.', exc_info=True)
                    data = {}
            finally:
                f.close()
        return self.session_class(data, sid, False)

    def list(self):
        """Lists all sessions in the store.

        .. versionadded:: 0.6
        """
        before, after = self.filename_template.split("%s", 1)
        filename_re = re.compile(
            r"%s(.{5,})%s$" % (re.escape(before), re.escape(after))
        )
        result = []
        for filename in os.listdir(self.path):
            #: this is a session that is still being saved.
            if filename.endswith(_fs_transaction_suffix):
                continue
            match = filename_re.match(filename)
            if match is not None:
                result.append(match.group(1))
        return result
