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

from werkzeug.datastructures import CallbackDict

_logger = logging.getLogger(__name__)


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
