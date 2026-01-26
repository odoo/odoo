# Copyright (c) 2020 gevent contributors.
"""
This module provides :class:`GeventSelector`, a high-level IO
multiplexing mechanism. This is aliased to :class:`DefaultSelector`.

This module provides the same API as the selectors defined in :mod:`selectors`.

On Python 2, this module is only available if the `selectors2
<https://pypi.org/project/selectors2/>`_ backport is installed.

.. versionadded:: 20.6.0
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from collections import defaultdict

try:
    import selectors as __selectors__
except ImportError:
    # Probably on Python 2. Do we have the backport?
    import selectors2 as __selectors__
    __target__ = 'selectors2'

from gevent.hub import _get_hub_noargs as get_hub
from gevent import sleep
from gevent._compat import iteritems
from gevent._compat import itervalues
from gevent._util import copy_globals
from gevent._util import Lazy

from gevent.event import Event
from gevent.select import _EV_READ
from gevent.select import _EV_WRITE

__implements__ = [
    'DefaultSelector',
]
__extra__ = [
    'GeventSelector',
]
__all__ = __implements__ + __extra__

__imports__ = copy_globals(
    __selectors__, globals(),
    names_to_ignore=__all__,
    # Copy __all__; __all__ is defined by selectors2 but not Python 3.
    dunder_names_to_keep=('__all__',)
)

_POLL_ALL = _EV_READ | _EV_WRITE

EVENT_READ = __selectors__.EVENT_READ
EVENT_WRITE = __selectors__.EVENT_WRITE
_ALL_EVENTS = EVENT_READ | EVENT_WRITE
SelectorKey = __selectors__.SelectorKey

# In 3.4 and selectors2, BaseSelector is a concrete
# class that can be called. In 3.5 and later, it's an
# ABC, with the real implementation being
# passed to _BaseSelectorImpl.
_BaseSelectorImpl = getattr(
    __selectors__,
    '_BaseSelectorImpl',
    __selectors__.BaseSelector
)

class GeventSelector(_BaseSelectorImpl):
    """
    A selector implementation using gevent primitives.

    This is a type of :class:`selectors.BaseSelector`, so the documentation
    for that class applies here.

    .. caution::
       As the base class indicates, it is critically important to
       unregister file objects before closing them. (Or close the selector
       they are registered with before closing them.) Failure to do so
       may crash the process or have other unintended results.
    """

    # Notes on the approach:
    #
    # It's easy to wrap a selector implementation around
    # ``gevent.select.poll``; in fact that's what happens by default
    # when monkey-patching in Python 3. But the problem with that is
    # each call to ``selector.select()`` will result in creating and
    # then destroying new kernel-level polling resources, as nothing
    # in ``gevent.select`` can keep watchers around (because the underlying
    # file could be closed at any time). This ends up producing a large
    # number of syscalls that are unnecessary.
    #
    # So here, we take advantage of the fact that it is documented and
    # required that files not be closed while they are registered.
    # This lets us persist watchers. Indeed, it lets us continually
    # accrue events in the background before a call to ``select()`` is even
    # made. We can take advantage of this to return results immediately, without
    # a syscall, if we have them.
    #
    # We create watchers in ``register()`` and destroy them in
    # ``unregister()``. They do not get started until the first call
    # to ``select()``, though. Once they are started, they don't get
    # stopped until they deliver an event.
    # Lifecycle:
    # register() -> inactive_watchers
    # select() -> inactive_watchers -> active_watchers;
    #             active_watchers   -> inactive_watchers

    def __init__(self, hub=None):
        if hub is not None:
            self.hub = hub
        # {fd: watcher}
        self._active_watchers = {}
        self._inactive_watchers = {}
        # {fd: EVENT_READ|EVENT_WRITE}
        self._accumulated_events = defaultdict(int)
        self._ready = Event()
        super(GeventSelector, self).__init__()

    def __callback(self, events, fd):
        if events > 0:
            cur_event_for_fd = self._accumulated_events[fd]
            if events & _EV_READ:
                cur_event_for_fd |= EVENT_READ
            if events & _EV_WRITE:
                cur_event_for_fd |= EVENT_WRITE
            self._accumulated_events[fd] = cur_event_for_fd

        self._ready.set()

    @Lazy
    def hub(self): # pylint:disable=method-hidden
        return get_hub()

    def register(self, fileobj, events, data=None):
        key = _BaseSelectorImpl.register(self, fileobj, events, data)

        if events == _ALL_EVENTS:
            flags = _POLL_ALL
        elif events == EVENT_READ:
            flags = _EV_READ
        else:
            flags = _EV_WRITE


        loop = self.hub.loop
        io = loop.io
        MAXPRI = loop.MAXPRI

        self._inactive_watchers[key.fd] = watcher = io(key.fd, flags)
        watcher.priority = MAXPRI
        return key

    def unregister(self, fileobj):
        key = _BaseSelectorImpl.unregister(self, fileobj)
        if key.fd in self._active_watchers:
            watcher = self._active_watchers.pop(key.fd)
        else:
            watcher = self._inactive_watchers.pop(key.fd)
        watcher.stop()
        watcher.close()
        self._accumulated_events.pop(key.fd, None)
        return key

    # XXX: Can we implement ``modify`` more efficiently than
    # ``unregister()``+``register()``? We could detect the no-change
    # case and do nothing; recent versions of the standard library
    # do that.

    def select(self, timeout=None):
        """
        Poll for I/O.

        Note that, like the built-in selectors, this will block
        indefinitely if no timeout is given and no files have been
        registered.
        """
        # timeout > 0 : block seconds
        # timeout <= 0 : No blocking.
        # timeout = None: Block forever

        # Event.wait doesn't deal with negative values
        if timeout is not None and timeout < 0:
            timeout = 0

        # Start any watchers that need started. Note that they may
        # not actually get a chance to do anything yet if we already had
        # events set.
        for fd, watcher in iteritems(self._inactive_watchers):
            watcher.start(self.__callback, fd, pass_events=True)
        self._active_watchers.update(self._inactive_watchers)
        self._inactive_watchers.clear()

        # The _ready event is either already set (in which case
        # there are some results waiting in _accumulated_events) or
        # not set, in which case we have to block. But to make the two cases
        # behave the same, we will always yield to the event loop.
        if self._ready.is_set():
            sleep()
        self._ready.wait(timeout)
        self._ready.clear()
        # TODO: If we have nothing ready, but they ask us not to block,
        # should we make an effort to actually spin the event loop and let
        # it check for events?

        result = []
        for fd, event in iteritems(self._accumulated_events):
            key = self._key_from_fd(fd)
            watcher = self._active_watchers.pop(fd)

            ## The below is taken without comment from
            ## https://github.com/gevent/gevent/pull/1523/files and
            ## hasn't been checked:
            #
            # Since we are emulating an epoll object within another epoll object,
            # once a watcher has fired, we must deactivate it until poll is called
            # next. If we did not, someone else could call, e.g., gevent.time.sleep
            # and any unconsumed bytes on our watched fd would prevent the process
            # from sleeping correctly.
            watcher.stop()
            if key:
                result.append((key, event & key.events))
                self._inactive_watchers[fd] = watcher
            else: # pragma: no cover
                # If the key was gone, then somehow we've been unregistered.
                # Don't put it back in inactive, close it.
                watcher.close()

        self._accumulated_events.clear()
        return result

    def close(self):
        for d in self._active_watchers, self._inactive_watchers:
            if d is None:
                continue # already closed
            for watcher in itervalues(d):
                watcher.stop()
                watcher.close()
        self._active_watchers = self._inactive_watchers = None
        self._accumulated_events = None
        self.hub = None
        _BaseSelectorImpl.close(self)


DefaultSelector = GeventSelector

def _gevent_do_monkey_patch(patch_request):
    aggressive = patch_request.patch_kwargs['aggressive']
    target_mod = patch_request.target_module

    patch_request.default_patch_items()

    import sys
    if 'selectors' not in sys.modules:
        # Py2: Make 'import selectors' work
        sys.modules['selectors'] = sys.modules[__name__]

    # Python 3 wants to use `select.select` as a member function,
    # leading to this error in selectors.py (because
    # gevent.select.select is not a builtin and doesn't get the
    # magic auto-static that they do):
    #
    #    r, w, _ = self._select(self._readers, self._writers, [], timeout)
    #    TypeError: select() takes from 3 to 4 positional arguments but 5 were given
    #
    # Note that this obviously only happens if selectors was
    # imported after we had patched select; but there is a code
    # path that leads to it being imported first (but now we've
    # patched select---so we can't compare them identically). It also doesn't
    # happen on Windows, because they define a normal method for _select, to work around
    # some weirdness in the handling of the third argument.
    #
    # The backport doesn't have that.
    orig_select_select = patch_request.get_original('select', 'select')
    assert target_mod.select is not orig_select_select
    selectors = __selectors__
    SelectSelector = selectors.SelectSelector
    if hasattr(SelectSelector, '_select') and SelectSelector._select in (
            target_mod.select, orig_select_select
    ):
        from gevent.select import select
        def _select(self, *args, **kwargs): # pylint:disable=unused-argument
            return select(*args, **kwargs)
        selectors.SelectSelector._select = _select
        _select._gevent_monkey = True # prove for test cases

    if aggressive:
        # If `selectors` had already been imported before we removed
        # select.epoll|kqueue|devpoll, these may have been defined in terms
        # of those functions. They'll fail at runtime.
        patch_request.remove_item(
            selectors,
            'EpollSelector',
            'KqueueSelector',
            'DevpollSelector',
        )
        selectors.DefaultSelector = DefaultSelector

    # Python 3.7 refactors the poll-like selectors to use a common
    # base class and capture a reference to select.poll, etc, at
    # import time. selectors tends to get imported early
    # (importing 'platform' does it: platform -> subprocess -> selectors),
    # so we need to clean that up.
    if hasattr(selectors, 'PollSelector') and hasattr(selectors.PollSelector, '_selector_cls'):
        from gevent.select import poll
        selectors.PollSelector._selector_cls = poll
