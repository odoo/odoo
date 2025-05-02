# Copyright (c) 2009-2012 Denis Bilenko. See LICENSE for details.
# pylint: disable=redefined-outer-name,too-many-lines
"""
Make the standard library cooperative.

The primary purpose of this module is to carefully patch, in place,
portions of the standard library with gevent-friendly functions that
behave in the same way as the original (at least as closely as possible).

The primary interface to this is the :func:`patch_all` function, which
performs all the available patches. It accepts arguments to limit the
patching to certain modules, but most programs **should** use the
default values as they receive the most wide-spread testing, and some monkey
patches have dependencies on others.

Patching **should be done as early as possible** in the lifecycle of the
program. For example, the main module (the one that tests against
``__main__`` or is otherwise the first imported) should begin with
this code, ideally before any other imports::

    from gevent import monkey
    monkey.patch_all()

A corollary of the above is that patching **should be done on the main
thread** and **should be done while the program is single-threaded**.

.. tip::

    Some frameworks, such as gunicorn, handle monkey-patching for you.
    Check their documentation to be sure.

.. warning::

    Patching too late can lead to unreliable behaviour (for example, some
    modules may still use blocking sockets) or even errors.

.. tip::

    Be sure to read the documentation for each patch function to check for
    known incompatibilities.

Querying
========

Sometimes it is helpful to know if objects have been monkey-patched, and in
advanced cases even to have access to the original standard library functions. This
module provides functions for that purpose.

- :func:`is_module_patched`
- :func:`is_object_patched`
- :func:`get_original`

.. _plugins:

Plugins and Events
==================

Beginning in gevent 1.3, events are emitted during the monkey patching process.
These events are delivered first to :mod:`gevent.events` subscribers, and then
to `setuptools entry points`_.

The following events are defined. They are listed in (roughly) the order
that a call to :func:`patch_all` will emit them.

- :class:`gevent.events.GeventWillPatchAllEvent`
- :class:`gevent.events.GeventWillPatchModuleEvent`
- :class:`gevent.events.GeventDidPatchModuleEvent`
- :class:`gevent.events.GeventDidPatchBuiltinModulesEvent`
- :class:`gevent.events.GeventDidPatchAllEvent`

Each event class documents the corresponding setuptools entry point name. The
entry points will be called with a single argument, the same instance of
the class that was sent to the subscribers.

You can subscribe to the events to monitor the monkey-patching process and
to manipulate it, for example by raising :exc:`gevent.events.DoNotPatch`.

You can also subscribe to the events to provide additional patching beyond what
gevent distributes, either for additional standard library modules, or
for third-party packages. The suggested time to do this patching is in
the subscriber for :class:`gevent.events.GeventDidPatchBuiltinModulesEvent`.
For example, to automatically patch `psycopg2`_ using `psycogreen`_
when the call to :func:`patch_all` is made, you could write code like this::

    # mypackage.py
    def patch_psycopg(event):
        from psycogreen.gevent import patch_psycopg
        patch_psycopg()

In your ``setup.py`` you would register it like this::

    from setuptools import setup
    setup(
        ...
        entry_points={
            'gevent.plugins.monkey.did_patch_builtins': [
                'psycopg2 = mypackage:patch_psycopg',
            ],
        },
        ...
    )

For more complex patching, gevent provides a helper method
that you can call to replace attributes of modules with attributes of your
own modules. This function also takes care of emitting the appropriate events.

- :func:`patch_module`

.. _setuptools entry points: http://setuptools.readthedocs.io/en/latest/setuptools.html#dynamic-discovery-of-services-and-plugins
.. _psycopg2: https://pypi.python.org/pypi/psycopg2
.. _psycogreen: https://pypi.python.org/pypi/psycogreen

Use as a module
===============

Sometimes it is useful to run existing python scripts or modules that
were not built to be gevent aware under gevent. To do so, this module
can be run as the main module, passing the script and its arguments.
For details, see the :func:`main` function.

.. versionchanged:: 1.3b1
   Added support for plugins and began emitting will/did patch events.
"""
from __future__ import absolute_import
from __future__ import print_function
import sys

__all__ = [
    'patch_all',
    'patch_builtins',
    'patch_dns',
    'patch_os',
    'patch_queue',
    'patch_select',
    'patch_signal',
    'patch_socket',
    'patch_ssl',
    'patch_subprocess',
    'patch_sys',
    'patch_thread',
    'patch_time',
    # query functions
    'get_original',
    'is_module_patched',
    'is_object_patched',
    # plugin API
    'patch_module',
    # module functions
    'main',
]

WIN = sys.platform.startswith("win")

class _BadImplements(AttributeError):
    """
    Raised when ``__implements__`` is incorrect.
    """

    def __init__(self, module):
        AttributeError.__init__(
            self,
            "Module %r has a bad or missing value for __implements__" % (module,)
        )

class MonkeyPatchWarning(RuntimeWarning):
    """
    The type of warnings we issue.

    .. versionadded:: 1.3a2
    """

def _notify_patch(event, _warnings=None):
    # Raises DoNotPatch if we're not supposed to patch
    from gevent.events import notify_and_call_entry_points

    event._warnings = _warnings
    notify_and_call_entry_points(event)

def _ignores_DoNotPatch(func):

    from functools import wraps

    @wraps(func)
    def ignores(*args, **kwargs):
        from gevent.events import DoNotPatch
        try:
            return func(*args, **kwargs)
        except DoNotPatch:
            return False

    return ignores


# maps module name -> {attribute name: original item}
# e.g. "time" -> {"sleep": built-in function sleep}
# NOT A PUBLIC API. However, third-party monkey-patchers may be using
# it? TODO: Provide better API for them.
saved = {}


def is_module_patched(mod_name):
    """
    Check if a module has been replaced with a cooperative version.

    :param str mod_name: The name of the standard library module,
        e.g., ``'socket'``.

    """
    return mod_name in saved


def is_object_patched(mod_name, item_name):
    """
    Check if an object in a module has been replaced with a
    cooperative version.

    :param str mod_name: The name of the standard library module,
        e.g., ``'socket'``.
    :param str item_name: The name of the attribute in the module,
        e.g., ``'create_connection'``.

    """
    return is_module_patched(mod_name) and item_name in saved[mod_name]


def is_anything_patched():
    # Check if this module has done any patching in the current process.
    # This is currently only used in gevent tests.
    #
    # Not currently a documented, public API, because I'm not convinced
    # it is 100% reliable in the event of third-party patch functions that
    # don't use ``saved``.
    #
    # .. versionadded:: 21.1.0
    return bool(saved)


def _get_original(name, items):
    d = saved.get(name, {})
    values = []
    module = None
    for item in items:
        if item in d:
            values.append(d[item])
        else:
            if module is None:
                module = __import__(name)
            values.append(getattr(module, item))
    return values


def get_original(mod_name, item_name):
    """
    Retrieve the original object from a module.

    If the object has not been patched, then that object will still be
    retrieved.

    :param str mod_name: The name of the standard library module,
        e.g., ``'socket'``. Can also be a sequence of standard library
        modules giving alternate names to try, e.g., ``('thread', '_thread')``;
        the first importable module will supply all *item_name* items.
    :param item_name: A string or sequence of strings naming the
        attribute(s) on the module ``mod_name`` to return.

    :return: The original value if a string was given for
             ``item_name`` or a sequence of original values if a
             sequence was passed.
    """
    mod_names = [mod_name] if isinstance(mod_name, str) else mod_name
    if isinstance(item_name, str):
        item_names = [item_name]
        unpack = True
    else:
        item_names = item_name
        unpack = False

    for mod in mod_names:
        try:
            result = _get_original(mod, item_names)
        except ImportError:
            if mod is mod_names[-1]:
                raise
        else:
            return result[0] if unpack else result

_NONE = object()


def patch_item(module, attr, newitem):
    olditem = getattr(module, attr, _NONE)
    if olditem is not _NONE:
        saved.setdefault(module.__name__, {}).setdefault(attr, olditem)
    setattr(module, attr, newitem)


def remove_item(module, attr):
    olditem = getattr(module, attr, _NONE)
    if olditem is _NONE:
        return
    saved.setdefault(module.__name__, {}).setdefault(attr, olditem)
    delattr(module, attr)


def __call_module_hook(gevent_module, name, module, items, _warnings):
    # This function can raise DoNotPatch on 'will'

    def warn(message):
        _queue_warning(message, _warnings)

    func_name = '_gevent_' + name + '_monkey_patch'
    try:
        func = getattr(gevent_module, func_name)
    except AttributeError:
        func = lambda *args: None


    func(module, items, warn)


class _GeventDoPatchRequest(object):

    get_original = staticmethod(get_original)

    def __init__(self,
                 target_module,
                 source_module,
                 items,
                 patch_kwargs):
        self.target_module = target_module
        self.source_module = source_module
        self.items = items
        self.patch_kwargs = patch_kwargs or {}

    def default_patch_items(self):
        for attr in self.items:
            patch_item(self.target_module, attr, getattr(self.source_module, attr))

    def remove_item(self, target_module, *items):
        if isinstance(target_module, str):
            items = (target_module,) + items
            target_module = self.target_module

        for item in items:
            remove_item(target_module, item)


def patch_module(target_module, source_module, items=None,
                 _warnings=None,
                 _patch_kwargs=None,
                 _notify_will_subscribers=True,
                 _notify_did_subscribers=True,
                 _call_hooks=True):
    """
    patch_module(target_module, source_module, items=None)

    Replace attributes in *target_module* with the attributes of the
    same name in *source_module*.

    The *source_module* can provide some attributes to customize the process:

    * ``__implements__`` is a list of attribute names to copy; if not present,
      the *items* keyword argument is mandatory. ``__implements__`` must only have
      names from the standard library module in it.
    * ``_gevent_will_monkey_patch(target_module, items, warn, **kwargs)``
    * ``_gevent_did_monkey_patch(target_module, items, warn, **kwargs)``
      These two functions in the *source_module* are called *if* they exist,
      before and after copying attributes, respectively. The "will" function
      may modify *items*. The value of *warn* is a function that should be called
      with a single string argument to issue a warning to the user. If the "will"
      function raises :exc:`gevent.events.DoNotPatch`, no patching will be done. These functions
      are called before any event subscribers or plugins.

    :keyword list items: A list of attribute names to replace. If
       not given, this will be taken from the *source_module* ``__implements__``
       attribute.
    :return: A true value if patching was done, a false value if patching was canceled.

    .. versionadded:: 1.3b1
    """
    from gevent import events

    if items is None:
        items = getattr(source_module, '__implements__', None)
        if items is None:
            raise _BadImplements(source_module)

    try:
        if _call_hooks:
            __call_module_hook(source_module, 'will', target_module, items, _warnings)
        if _notify_will_subscribers:
            _notify_patch(
                events.GeventWillPatchModuleEvent(target_module.__name__, source_module,
                                                  target_module, items),
                _warnings)
    except events.DoNotPatch:
        return False

    # Undocumented, internal use: If the module defines
    # `_gevent_do_monkey_patch(patch_request: _GeventDoPatchRequest)` call that;
    # the module is responsible for its own patching.
    do_patch = getattr(
        source_module,
        '_gevent_do_monkey_patch',
        _GeventDoPatchRequest.default_patch_items
    )
    request = _GeventDoPatchRequest(target_module, source_module, items, _patch_kwargs)
    do_patch(request)

    if _call_hooks:
        __call_module_hook(source_module, 'did', target_module, items, _warnings)

    if _notify_did_subscribers:
        # We allow turning off the broadcast of the 'did' event for the benefit
        # of our internal functions which need to do additional work (besides copying
        # attributes) before their patch can be considered complete.
        _notify_patch(
            events.GeventDidPatchModuleEvent(target_module.__name__, source_module,
                                             target_module)
        )

    return True

def _check_availability(name):
    """
    Test that the source and target modules for *name* are
    available and return them.

    :raise ImportError: If the source or target cannot be imported.
    :return: The tuple ``(gevent_module, target_module, target_module_name)``
    """
    # Always import the gevent module first. This helps us be sure we can
    # use regular imports in gevent files (when we can't use gevent.monkey.get_original())
    gevent_module = getattr(__import__('gevent.' + name), name)
    target_module_name = getattr(gevent_module, '__target__', name)
    target_module = __import__(target_module_name)

    return gevent_module, target_module, target_module_name

def _patch_module(name,
                  items=None,
                  _warnings=None,
                  _patch_kwargs=None,
                  _notify_will_subscribers=True,
                  _notify_did_subscribers=True,
                  _call_hooks=True):

    gevent_module, target_module, target_module_name = _check_availability(name)

    patch_module(target_module, gevent_module, items=items,
                 _warnings=_warnings, _patch_kwargs=_patch_kwargs,
                 _notify_will_subscribers=_notify_will_subscribers,
                 _notify_did_subscribers=_notify_did_subscribers,
                 _call_hooks=_call_hooks)

    # On Python 2, the `futures` package will install
    # a bunch of modules with the same name as those from Python 3,
    # such as `_thread`; primarily these just do `from thread import *`,
    # meaning we have alternate references. If that's already been imported,
    # we need to attempt to patch that too.

    # Be sure to keep the original states matching also.

    alternate_names = getattr(gevent_module, '__alternate_targets__', ())
    for alternate_name in alternate_names:
        alternate_module = sys.modules.get(alternate_name)
        if alternate_module is not None and alternate_module is not target_module:
            saved.pop(alternate_name, None)
            patch_module(alternate_module, gevent_module, items=items,
                         _warnings=_warnings,
                         _notify_will_subscribers=False,
                         _notify_did_subscribers=False,
                         _call_hooks=False)
            saved[alternate_name] = saved[target_module_name]

    return gevent_module, target_module


def _queue_warning(message, _warnings):
    # Queues a warning to show after the monkey-patching process is all done.
    # Done this way to avoid extra imports during the process itself, just
    # in case. If we're calling a function one-off (unusual) go ahead and do it
    if _warnings is None:
        _process_warnings([message])
    else:
        _warnings.append(message)


def _process_warnings(_warnings):
    import warnings
    for warning in _warnings:
        warnings.warn(warning, MonkeyPatchWarning, stacklevel=3)


def _patch_sys_std(name):
    from gevent.fileobject import FileObjectThread
    orig = getattr(sys, name)
    if not isinstance(orig, FileObjectThread):
        patch_item(sys, name, FileObjectThread(orig))

@_ignores_DoNotPatch
def patch_sys(stdin=True, stdout=True, stderr=True): # pylint:disable=unused-argument
    """
    Patch sys.std[in,out,err] to use a cooperative IO via a
    threadpool.

    This is relatively dangerous and can have unintended consequences
    such as hanging the process or `misinterpreting control keys`_
    when :func:`input` and :func:`raw_input` are used. :func:`patch_all`
    does *not* call this function by default.

    This method does nothing on Python 3. The Python 3 interpreter
    wants to flush the TextIOWrapper objects that make up
    stderr/stdout at shutdown time, but using a threadpool at that
    time leads to a hang.

    .. _`misinterpreting control keys`: https://github.com/gevent/gevent/issues/274

    .. deprecated:: 23.7.0
       Does nothing on any supported version.
    """
    return

@_ignores_DoNotPatch
def patch_os():
    """
    Replace :func:`os.fork` with :func:`gevent.fork`, and, on POSIX,
    :func:`os.waitpid` with :func:`gevent.os.waitpid` (if the
    environment variable ``GEVENT_NOWAITPID`` is not defined). Does
    nothing if fork is not available.

    .. caution:: This method must be used with :func:`patch_signal` to have proper `SIGCHLD`
         handling and thus correct results from ``waitpid``.
         :func:`patch_all` calls both by default.

    .. caution:: For `SIGCHLD` handling to work correctly, the event loop must run.
         The easiest way to help ensure this is to use :func:`patch_all`.
    """
    _patch_module('os')


@_ignores_DoNotPatch
def patch_queue():
    """
    On Python 3.7 and above, replace :class:`queue.SimpleQueue` (implemented
    in C) with its Python counterpart.

    .. versionadded:: 1.3.5
    """

    import gevent.queue
    if 'SimpleQueue' in gevent.queue.__all__:
        _patch_module('queue', items=['SimpleQueue'])


@_ignores_DoNotPatch
def patch_time():
    """
    Replace :func:`time.sleep` with :func:`gevent.sleep`.
    """
    _patch_module('time')

@_ignores_DoNotPatch
def patch_contextvars():
    """
    Replaces the implementations of :mod:`contextvars` with
    :mod:`gevent.contextvars`.

    On Python 3.7 and above, this is a standard library module. On
    earlier versions, a backport that uses the same distribution name
    and import name is available on PyPI (though this is not
    recommended). If that is installed, it will be patched.

    .. versionchanged:: 20.04.0
       Clarify that the backport is also patched.

    .. versionchanged:: 20.9.0
       This now does nothing on Python 3.7 and above.
       gevent now depends on greenlet 0.4.17, which
       natively handles switching context vars when greenlets are switched.
       Older versions of Python that have the backport installed will
       still be patched.

    .. deprecated:: 23.7.0
       Does nothing on any supported version.
    """
    return


def _patch_existing_locks(threading):
    if len(list(threading.enumerate())) != 1:
        return
    # This is used to protect internal data structures for enumerate.
    # It's acquired when threads are started and when they're stopped.
    # Stopping a thread checks a Condition, which on Python 2 wants to test
    # _is_owned of its (patched) Lock. Since our LockType doesn't have
    # _is_owned, it tries to acquire the lock non-blocking; that triggers a
    # switch. If the next thing in the callback list was a thread that needed
    # to start or end, we wouldn't be able to acquire this native lock
    # because it was being held already; we couldn't switch either, so we'd
    # block permanently.
    threading._active_limbo_lock = threading._allocate_lock()
    try:
        tid = threading.get_ident()
    except AttributeError:
        tid = threading._get_ident()
    rlock_type = type(threading.RLock())
    try:
        import importlib._bootstrap
    except ImportError:
        class _ModuleLock(object):
            pass
    else:
        _ModuleLock = importlib._bootstrap._ModuleLock # python 2 pylint: disable=no-member
    # It might be possible to walk up all the existing stack frames to find
    # locked objects...at least if they use `with`. To be sure, we look at every object
    # Since we're supposed to be done very early in the process, there shouldn't be
    # too many.

    # Note that the C implementation of locks, at least on some
    # versions of CPython, cannot be found and cannot be fixed (they simply
    # don't show up to GC; see https://github.com/gevent/gevent/issues/1354)

    # By definition there's only one thread running, so the various
    # owner attributes were the old (native) thread id. Make it our
    # current greenlet id so that when it wants to unlock and compare
    # self.__owner with _get_ident(), they match.
    gc = __import__('gc')
    for o in gc.get_objects():
        if isinstance(o, rlock_type):
            for owner_name in (
                    '_owner', # Python 3 or backported PyPy2
                    '_RLock__owner', # Python 2
            ):
                if hasattr(o, owner_name):
                    if getattr(o, owner_name) is not None:
                        setattr(o, owner_name, tid)
                    break
            else: # pragma: no cover
                raise AssertionError(
                    "Unsupported Python implementation; "
                    "Found unknown lock implementation.",
                    vars(o)
                )
        elif isinstance(o, _ModuleLock):
            if o.owner is not None:
                o.owner = tid

@_ignores_DoNotPatch
def patch_thread(threading=True, _threading_local=True, Event=True, logging=True,
                 existing_locks=True,
                 _warnings=None):
    """
    patch_thread(threading=True, _threading_local=True, Event=True, logging=True, existing_locks=True) -> None

    Replace the standard :mod:`thread` module to make it greenlet-based.

    :keyword bool threading: When True (the default),
        also patch :mod:`threading`.
    :keyword bool _threading_local: When True (the default),
        also patch :class:`_threading_local.local`.
    :keyword bool logging: When True (the default), also patch locks
        taken if the logging module has been configured.

    :keyword bool existing_locks: When True (the default), and the
        process is still single threaded, make sure that any
        :class:`threading.RLock` (and, under Python 3, :class:`importlib._bootstrap._ModuleLock`)
        instances that are currently locked can be properly unlocked. **Important**: This is a
        best-effort attempt and, on certain implementations, may not detect all
        locks. It is important to monkey-patch extremely early in the startup process.
        Setting this to False is not recommended, especially on Python 2.

    .. caution::
        Monkey-patching :mod:`thread` and using
        :class:`multiprocessing.Queue` or
        :class:`concurrent.futures.ProcessPoolExecutor` (which uses a
        ``Queue``) will hang the process.

        Monkey-patching with this function and using
        sub-interpreters (and advanced C-level API) and threads may be
        unstable on certain platforms.

    .. versionchanged:: 1.1b1
        Add *logging* and *existing_locks* params.
    .. versionchanged:: 1.3a2
        ``Event`` defaults to True.
    """
    # XXX: Simplify
    # pylint:disable=too-many-branches,too-many-locals,too-many-statements

    # Description of the hang:
    # There is an incompatibility with patching 'thread' and the 'multiprocessing' module:
    # The problem is that multiprocessing.queues.Queue uses a half-duplex multiprocessing.Pipe,
    # which is implemented with os.pipe() and _multiprocessing.Connection. os.pipe isn't patched
    # by gevent, as it returns just a fileno. _multiprocessing.Connection is an internal implementation
    # class implemented in C, which exposes a 'poll(timeout)' method; under the covers, this issues a
    # (blocking) select() call: hence the need for a real thread. Except for that method, we could
    # almost replace Connection with gevent.fileobject.SocketAdapter, plus a trivial
    # patch to os.pipe (below). Sigh, so close. (With a little work, we could replicate that method)

    # import os
    # import fcntl
    # os_pipe = os.pipe
    # def _pipe():
    #   r, w = os_pipe()
    #   fcntl.fcntl(r, fcntl.F_SETFL, os.O_NONBLOCK)
    #   fcntl.fcntl(w, fcntl.F_SETFL, os.O_NONBLOCK)
    #   return r, w
    # os.pipe = _pipe

    # The 'threading' module copies some attributes from the
    # thread module the first time it is imported. If we patch 'thread'
    # before that happens, then we store the wrong values in 'saved',
    # So if we're going to patch threading, we either need to import it
    # before we patch thread, or manually clean up the attributes that
    # are in trouble. The latter is tricky because of the different names
    # on different versions.
    if threading:
        threading_mod = __import__('threading')
        # Capture the *real* current thread object before
        # we start returning DummyThread objects, for comparison
        # to the main thread.
        orig_current_thread = threading_mod.current_thread()
    else:
        threading_mod = None
        gevent_threading_mod = None
        orig_current_thread = None

    gevent_thread_mod, thread_mod = _patch_module('thread',
                                                  _warnings=_warnings,
                                                  _notify_did_subscribers=False)


    if threading:
        gevent_threading_mod, _ = _patch_module('threading',
                                                _warnings=_warnings,
                                                _notify_did_subscribers=False)

        if Event:
            from gevent.event import Event
            patch_item(threading_mod, 'Event', Event)
            # Python 2 had `Event` as a function returning
            # the private class `_Event`. Some code may be relying
            # on that.
            if hasattr(threading_mod, '_Event'):
                patch_item(threading_mod, '_Event', Event)

        if existing_locks:
            _patch_existing_locks(threading_mod)

        if logging and 'logging' in sys.modules:
            logging = __import__('logging')
            patch_item(logging, '_lock', threading_mod.RLock())
            for wr in logging._handlerList:
                # In py26, these are actual handlers, not weakrefs
                handler = wr() if callable(wr) else wr
                if handler is None:
                    continue
                if not hasattr(handler, 'lock'):
                    raise TypeError("Unknown/unsupported handler %r" % handler)
                handler.lock = threading_mod.RLock()

    if _threading_local:
        _threading_local = __import__('_threading_local')
        from gevent.local import local
        patch_item(_threading_local, 'local', local)

    def make_join_func(thread, thread_greenlet):
        from gevent.hub import sleep
        from time import time

        def join(timeout=None):
            end = None
            if threading_mod.current_thread() is thread:
                raise RuntimeError("Cannot join current thread")
            if thread_greenlet is not None and thread_greenlet.dead:
                return
            # You may ask: Why not call thread_greenlet.join()?
            # Well, in the one case we actually have a greenlet, it's the
            # low-level greenlet.greenlet object for the main thread, which
            # doesn't have a join method.
            #
            # You may ask: Why not become the main greenlet's *parent*
            # so you can get notified when it finishes? Because you can't
            # create a greenlet cycle (the current greenlet is a descendent
            # of the parent), and nor can you set a greenlet's parent to None,
            # so there can only ever be one greenlet with a parent of None: the main
            # greenlet, the one we need to watch.
            #
            # You may ask: why not swizzle out the problematic lock on the main thread
            # into a gevent friendly lock? Well, the interpreter actually depends on that
            # for the main thread in threading._shutdown; see below.

            if not thread.is_alive():
                return

            if timeout:
                end = time() + timeout

            while thread.is_alive():
                if end is not None and time() > end:
                    return
                sleep(0.01)
        return join

    if threading:
        from gevent.threading import main_native_thread

        for thread in threading_mod._active.values():
            if thread == main_native_thread():
                continue
            thread.join = make_join_func(thread, None)

    # Issue 18808 changes the nature of Thread.join() to use
    # locks. This means that a greenlet spawned in the main thread
    # (which is already running) cannot wait for the main thread---it
    # hangs forever. We patch around this if possible. See also
    # gevent.threading.
    greenlet = __import__('greenlet')
    already_patched = is_object_patched('threading', '_shutdown')
    orig_shutdown = threading_mod._shutdown

    if orig_current_thread == threading_mod.main_thread() and not already_patched:
        main_thread = threading_mod.main_thread()
        _greenlet = main_thread._greenlet = greenlet.getcurrent()
        main_thread.__real_tstate_lock = main_thread._tstate_lock
        assert main_thread.__real_tstate_lock is not None
        # The interpreter will call threading._shutdown
        # when the main thread exits and is about to
        # go away. It is called *in* the main thread. This
        # is a perfect place to notify other greenlets that
        # the main thread is done. We do this by overriding the
        # lock of the main thread during operation, and only restoring
        # it to the native blocking version at shutdown time
        # (the interpreter also has a reference to this lock in a
        # C data structure).
        main_thread._tstate_lock = threading_mod.Lock()
        main_thread._tstate_lock.acquire()

        def _shutdown():
            # Release anyone trying to join() me,
            # and let us switch to them.
            if not main_thread._tstate_lock:
                return

            main_thread._tstate_lock.release()
            from gevent import sleep
            try:
                sleep()
            except: # pylint:disable=bare-except
                # A greenlet could have .kill() us
                # or .throw() to us. I'm the main greenlet,
                # there's no where else for this to go.
                from gevent  import get_hub
                get_hub().print_exception(_greenlet, *sys.exc_info())

            # Now, this may have resulted in us getting stopped
            # if some other greenlet actually just ran there.
            # That's not good, we're not supposed to be stopped
            # when we enter _shutdown.
            main_thread._is_stopped = False
            main_thread._tstate_lock = main_thread.__real_tstate_lock
            main_thread.__real_tstate_lock = None
            # The only truly blocking native shutdown lock to
            # acquire should be our own (hopefully), and the call to
            # _stop that orig_shutdown makes will discard it.

            orig_shutdown()
            patch_item(threading_mod, '_shutdown', orig_shutdown)

        patch_item(threading_mod, '_shutdown', _shutdown)

        # We create a bit of a reference cycle here,
        # so main_thread doesn't get to be collected in a timely way.
        # Not good. Take it out of dangling so we don't get
        # warned about it.
        threading_mod._dangling.remove(main_thread)

        # Patch up the ident of the main thread to match. This
        # matters if threading was imported before monkey-patching
        # thread
        oldid = main_thread.ident
        main_thread._ident = threading_mod.get_ident()
        if oldid in threading_mod._active:
            threading_mod._active[main_thread.ident] = threading_mod._active[oldid]
        if oldid != main_thread.ident:
            del threading_mod._active[oldid]
    elif not already_patched:
        _queue_warning("Monkey-patching not on the main thread; "
                       "threading.main_thread().join() will hang from a greenlet",
                       _warnings)

        main_thread = threading_mod.main_thread()
        def _shutdown():
            # We've patched get_ident but *did not* patch the
            # main_thread.ident value. Beginning in Python 3.9.8
            # and then later releases (3.10.1, probably), the
            # _main_thread object is only _stop() if the ident of
            # the current thread (the *real* main thread) matches
            # the ident of the _main_thread object. But without doing that,
            # the main thread's shutdown lock (threading._shutdown_locks) is never
            # removed *or released*, thus hanging the interpreter.
            # XXX: There's probably a better way to do this. Probably need to take a
            # step back and look at the whole picture.
            main_thread._ident = threading_mod.get_ident()
            orig_shutdown()
            patch_item(threading_mod, '_shutdown', orig_shutdown)
        patch_item(threading_mod, '_shutdown', _shutdown)

    from gevent import events
    _notify_patch(events.GeventDidPatchModuleEvent('thread', gevent_thread_mod, thread_mod))
    _notify_patch(events.GeventDidPatchModuleEvent('threading', gevent_threading_mod, threading_mod))

@_ignores_DoNotPatch
def patch_socket(dns=True, aggressive=True):
    """
    Replace the standard socket object with gevent's cooperative
    sockets.

    :keyword bool dns: When true (the default), also patch address
        resolution functions in :mod:`socket`. See :doc:`/dns` for details.
    """
    from gevent import socket
    # Note: although it seems like it's not strictly necessary to monkey patch 'create_connection',
    # it's better to do it. If 'create_connection' was not monkey patched, but the rest of socket module
    # was, create_connection would still use "green" getaddrinfo and "green" socket.
    # However, because gevent.socket.socket.connect is a Python function, the exception raised by it causes
    # _socket object to be referenced by the frame, thus causing the next invocation of bind(source_address) to fail.
    if dns:
        items = socket.__implements__ # pylint:disable=no-member
    else:
        items = set(socket.__implements__) - set(socket.__dns__) # pylint:disable=no-member
    _patch_module('socket', items=items)
    if aggressive:
        if 'ssl' not in socket.__implements__: # pylint:disable=no-member
            remove_item(socket, 'ssl')

@_ignores_DoNotPatch
def patch_dns():
    """
    Replace :doc:`DNS functions </dns>` in :mod:`socket` with
    cooperative versions.

    This is only useful if :func:`patch_socket` has been called and is
    done automatically by that method if requested.
    """
    from gevent import socket
    _patch_module('socket', items=socket.__dns__) # pylint:disable=no-member


def _find_module_refs(to, excluding_names=()):
    # Looks specifically for module-level references,
    # i.e., 'from foo import Bar'. We define a module reference
    # as a dict (subclass) that also has a __name__ attribute.
    # This does not handle subclasses, but it does find them.
    # Returns two sets. The first is modules (name, file) that were
    # found. The second is subclasses that were found.
    gc = __import__('gc')
    direct_ref_modules = set()
    subclass_modules = set()

    def report(mod):
        return mod['__name__'], mod.get('__file__', '<unknown>')

    for r in gc.get_referrers(to):
        if isinstance(r, dict) and '__name__' in r:
            if r['__name__'] in excluding_names:
                continue

            for v in r.values():
                if v is to:
                    direct_ref_modules.add(report(r))
        elif isinstance(r, type) and to in r.__bases__ and 'gevent.' not in r.__module__:
            subclass_modules.add(r)

    return direct_ref_modules, subclass_modules

@_ignores_DoNotPatch
def patch_ssl(_warnings=None, _first_time=True):
    """
    patch_ssl() -> None

    Replace :class:`ssl.SSLSocket` object and socket wrapping functions in
    :mod:`ssl` with cooperative versions.

    This is only useful if :func:`patch_socket` has been called.
    """
    may_need_warning = (
        _first_time
        and 'ssl' in sys.modules
        and hasattr(sys.modules['ssl'], 'SSLContext'))
    # Previously, we didn't warn on Python 2 if pkg_resources has been imported
    # because that imports ssl and it's commonly used for namespace packages,
    # which typically means we're still in some early part of the import cycle.
    # However, with our new more discriminating check, that no longer seems to be a problem.
    # Prior to 3.6, we don't have the RecursionError problem, and prior to 3.7 we don't have the
    # SSLContext.sslsocket_class/SSLContext.sslobject_class problem.

    gevent_mod, _ = _patch_module('ssl', _warnings=_warnings)
    if may_need_warning:
        direct_ref_modules, subclass_modules = _find_module_refs(
            gevent_mod.orig_SSLContext,
            excluding_names=('ssl', 'gevent.ssl', 'gevent._ssl3', 'gevent._sslgte279'))
        if direct_ref_modules or subclass_modules:
            # Normally you don't want to have dynamic warning strings, because
            # the cache in the warning module is based on the string. But we
            # specifically only do this the first time we patch ourself, so it's
            # ok.
            direct_ref_mod_str = subclass_str = ''
            if direct_ref_modules:
                direct_ref_mod_str = 'Modules that had direct imports (NOT patched): %s. ' % ([
                    "%s (%s)" % (name, fname)
                    for name, fname in direct_ref_modules
                ])
            if subclass_modules:
                subclass_str = 'Subclasses (NOT patched): %s. ' % ([
                    str(t) for t in subclass_modules
                ])
            _queue_warning(
                'Monkey-patching ssl after ssl has already been imported '
                'may lead to errors, including RecursionError on Python 3.6. '
                'It may also silently lead to incorrect behaviour on Python 3.7. '
                'Please monkey-patch earlier. '
                'See https://github.com/gevent/gevent/issues/1016. '
                + direct_ref_mod_str + subclass_str,
                _warnings)


@_ignores_DoNotPatch
def patch_select(aggressive=True):
    """
    Replace :func:`select.select` with :func:`gevent.select.select`
    and :func:`select.poll` with :class:`gevent.select.poll` (where available).

    If ``aggressive`` is true (the default), also remove other
    blocking functions from :mod:`select` .

    - :func:`select.epoll`
    - :func:`select.kqueue`
    - :func:`select.kevent`
    - :func:`select.devpoll` (Python 3.5+)
    """
    _patch_module('select',
                  _patch_kwargs={'aggressive': aggressive})

@_ignores_DoNotPatch
def patch_selectors(aggressive=True):
    """
    Replace :class:`selectors.DefaultSelector` with
    :class:`gevent.selectors.GeventSelector`.

    If ``aggressive`` is true (the default), also remove other
    blocking classes :mod:`selectors`:

    - :class:`selectors.EpollSelector`
    - :class:`selectors.KqueueSelector`
    - :class:`selectors.DevpollSelector` (Python 3.5+)

    On Python 2, the :mod:`selectors2` module is used instead
    of :mod:`selectors` if it is available. If this module cannot
    be imported, no patching is done and :mod:`gevent.selectors` is
    not available.

    In :func:`patch_all`, the *select* argument controls both this function
    and :func:`patch_select`.

    .. versionadded:: 20.6.0
    """
    try:
        _check_availability('selectors')
    except ImportError: # pragma: no cover
        return

    _patch_module('selectors',
                  _patch_kwargs={'aggressive': aggressive})


@_ignores_DoNotPatch
def patch_subprocess():
    """
    Replace :func:`subprocess.call`, :func:`subprocess.check_call`,
    :func:`subprocess.check_output` and :class:`subprocess.Popen` with
    :mod:`cooperative versions <gevent.subprocess>`.

    .. note::
       On Windows under Python 3, the API support may not completely match
       the standard library.

    """
    _patch_module('subprocess')

@_ignores_DoNotPatch
def patch_builtins():
    """
    Make the builtin :func:`__import__` function `greenlet safe`_ under Python 2.

    .. note::
       This does nothing under Python 3 as it is not necessary. Python 3 features
       improved import locks that are per-module, not global.

    .. _greenlet safe: https://github.com/gevent/gevent/issues/108

    .. deprecated:: 23.7.0
       Does nothing on any supported platform.
    """


@_ignores_DoNotPatch
def patch_signal():
    """
    Make the :func:`signal.signal` function work with a :func:`monkey-patched os <patch_os>`.

    .. caution:: This method must be used with :func:`patch_os` to have proper ``SIGCHLD``
         handling. :func:`patch_all` calls both by default.

    .. caution:: For proper ``SIGCHLD`` handling, you must yield to the event loop.
         Using :func:`patch_all` is the easiest way to ensure this.

    .. seealso:: :mod:`gevent.signal`
    """
    _patch_module("signal")


def _check_repatching(**module_settings):
    _warnings = []
    key = '_gevent_saved_patch_all_module_settings'

    del module_settings['kwargs']
    currently_patched = saved.setdefault(key, {})
    first_time = not currently_patched
    if not first_time and currently_patched != module_settings:
        _queue_warning("Patching more than once will result in the union of all True"
                       " parameters being patched",
                       _warnings)

    to_patch = {}
    for k, v in module_settings.items():
        # If we haven't seen the setting at all, record it and echo it.
        # If we have seen the setting, but it became true, record it and echo it.
        if k not in currently_patched:
            to_patch[k] = currently_patched[k] = v
        elif v and not currently_patched[k]:
            to_patch[k] = currently_patched[k] = True

    return _warnings, first_time, to_patch


def _subscribe_signal_os(will_patch_all):
    if will_patch_all.will_patch_module('signal') and not will_patch_all.will_patch_module('os'):
        warnings = will_patch_all._warnings # Internal
        _queue_warning('Patching signal but not os will result in SIGCHLD handlers'
                       ' installed after this not being called and os.waitpid may not'
                       ' function correctly if gevent.subprocess is used. This may raise an'
                       ' error in the future.',
                       warnings)

def patch_all(socket=True, dns=True, time=True, select=True, thread=True, os=True, ssl=True,
              subprocess=True, sys=False, aggressive=True, Event=True,
              builtins=True, signal=True,
              queue=True, contextvars=True,
              **kwargs):
    """
    Do all of the default monkey patching (calls every other applicable
    function in this module).

    :return: A true value if patching all modules wasn't cancelled, a false
      value if it was.

    .. versionchanged:: 1.1
       Issue a :mod:`warning <warnings>` if this function is called multiple times
       with different arguments. The second and subsequent calls will only add more
       patches, they can never remove existing patches by setting an argument to ``False``.
    .. versionchanged:: 1.1
       Issue a :mod:`warning <warnings>` if this function is called with ``os=False``
       and ``signal=True``. This will cause SIGCHLD handlers to not be called. This may
       be an error in the future.
    .. versionchanged:: 1.3a2
       ``Event`` defaults to True.
    .. versionchanged:: 1.3b1
       Defined the return values.
    .. versionchanged:: 1.3b1
       Add ``**kwargs`` for the benefit of event subscribers. CAUTION: gevent may add
       and interpret additional arguments in the future, so it is suggested to use prefixes
       for kwarg values to be interpreted by plugins, for example, `patch_all(mylib_futures=True)`.
    .. versionchanged:: 1.3.5
       Add *queue*, defaulting to True, for Python 3.7.
    .. versionchanged:: 1.5
       Remove the ``httplib`` argument. Previously, setting it raised a ``ValueError``.
    .. versionchanged:: 1.5a3
       Add the ``contextvars`` argument.
    .. versionchanged:: 1.5
       Better handling of patching more than once.
    """
    # pylint:disable=too-many-locals,too-many-branches

    # Check to see if they're changing the patched list
    _warnings, first_time, modules_to_patch = _check_repatching(**locals())

    if not modules_to_patch:
        # Nothing to do. Either the arguments were identical to what
        # we previously did, or they specified false values
        # for things we had previously patched.
        _process_warnings(_warnings)
        return

    for k, v in modules_to_patch.items():
        locals()[k] = v

    from gevent import events
    try:
        _notify_patch(events.GeventWillPatchAllEvent(modules_to_patch, kwargs), _warnings)
    except events.DoNotPatch:
        return False

    # order is important
    if os:
        patch_os()
    if thread:
        patch_thread(Event=Event, _warnings=_warnings)
    if time:
        # time must be patched after thread, some modules used by thread
        # need access to the real time.sleep function.
        patch_time()

    # sys must be patched after thread. in other cases threading._shutdown will be
    # initiated to _MainThread with real thread ident
    if sys:
        patch_sys()
    if socket:
        patch_socket(dns=dns, aggressive=aggressive)
    if select:
        patch_select(aggressive=aggressive)
        patch_selectors(aggressive=aggressive)
    if ssl:
        patch_ssl(_warnings=_warnings, _first_time=first_time)
    if subprocess:
        patch_subprocess()
    if builtins:
        patch_builtins()
    if signal:
        patch_signal()
    if queue:
        patch_queue()
    if contextvars:
        patch_contextvars()

    _notify_patch(events.GeventDidPatchBuiltinModulesEvent(modules_to_patch, kwargs), _warnings)
    _notify_patch(events.GeventDidPatchAllEvent(modules_to_patch, kwargs), _warnings)

    _process_warnings(_warnings)
    return True


def main():
    args = {}
    argv = sys.argv[1:]
    verbose = False
    run_fn = "run_path"
    script_help, patch_all_args, modules = _get_script_help()
    while argv and argv[0].startswith('--'):
        option = argv[0][2:]
        if option == 'verbose':
            verbose += 1
        elif option == 'module':
            run_fn = "run_module"
        elif option.startswith('no-') and option.replace('no-', '') in patch_all_args:
            args[option[3:]] = False
        elif option in patch_all_args:
            args[option] = True
            if option in modules:
                for module in modules:
                    args.setdefault(module, False)
        else:
            sys.exit(script_help + '\n\n' + 'Cannot patch %r' % option)
        del argv[0]
        # TODO: break on --
    if verbose:
        import pprint
        import os
        print('gevent.monkey.patch_all(%s)' % ', '.join('%s=%s' % item for item in args.items()))
        print('sys.version=%s' % (sys.version.strip().replace('\n', ' '), ))
        print('sys.path=%s' % pprint.pformat(sys.path))
        print('sys.modules=%s' % pprint.pformat(sorted(sys.modules.keys())))
        print('cwd=%s' % os.getcwd())

    if not argv:
        print(script_help)
        return

    sys.argv[:] = argv
    # Make sure that we don't get imported again under a different
    # name (usually it's ``__main__`` here) because that could lead to
    # double-patching, and making monkey.get_original() not work.
    try:
        mod_name = __spec__.name
    except NameError:
        # Py2: __spec__ is not defined as standard
        mod_name = 'gevent.monkey'
    sys.modules[mod_name] = sys.modules[__name__]
    # On Python 2, we have to set the gevent.monkey attribute
    # manually; putting gevent.monkey into sys.modules stops the
    # import machinery from making that connection, and ``from gevent
    # import monkey`` is broken. On Python 3 (.8 at least) that's not
    # necessary.
    if 'gevent' in sys.modules:
        sys.modules['gevent'].monkey = sys.modules[mod_name]
    # Running ``patch_all()`` will load pkg_resources entry point plugins
    # which may attempt to import ``gevent.monkey``, so it is critical that
    # we have established the correct saved module name first.
    patch_all(**args)

    import runpy
    # Use runpy.run_path to closely (exactly) match what the
    # interpreter does given 'python <path>'. This includes allowing
    # passing .pyc/.pyo files and packages with a __main__ and
    # potentially even zip files. Previously we used exec, which only
    # worked if we directly read a python source file.
    run_meth = getattr(runpy, run_fn)
    return run_meth(sys.argv[0], run_name='__main__')


def _get_script_help():
    # pylint:disable=deprecated-method
    import inspect
    try:
        getter = inspect.getfullargspec # deprecated in 3.5, un-deprecated in 3.6
    except AttributeError:
        getter = inspect.getargspec
    patch_all_args = getter(patch_all)[0]
    modules = [x for x in patch_all_args if 'patch_' + x in globals()]
    script_help = """gevent.monkey - monkey patch the standard modules to use gevent.

USAGE: ``python -m gevent.monkey [MONKEY OPTIONS] [--module] (script|module) [SCRIPT OPTIONS]``

If no MONKEY OPTIONS are present, monkey patches all the modules as if by calling ``patch_all()``.
You can exclude a module with --no-<module>, e.g. --no-thread. You can
specify a module to patch with --<module>, e.g. --socket. In the latter
case only the modules specified on the command line will be patched.

The default behavior is to execute the script passed as argument. If you wish
to run a module instead, pass the `--module` argument before the module name.

.. versionchanged:: 1.3b1
    The *script* argument can now be any argument that can be passed to `runpy.run_path`,
    just like the interpreter itself does, for example a package directory containing ``__main__.py``.
    Previously it had to be the path to
    a .py source file.

.. versionchanged:: 1.5
    The `--module` option has been added.

MONKEY OPTIONS: ``--verbose %s``""" % ', '.join('--[no-]%s' % m for m in modules)
    return script_help, patch_all_args, modules

main.__doc__ = _get_script_help()[0]

if __name__ == '__main__':
    main()
