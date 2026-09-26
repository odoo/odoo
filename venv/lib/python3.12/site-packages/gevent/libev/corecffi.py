# pylint: disable=too-many-lines, protected-access, redefined-outer-name, not-callable
# pylint: disable=no-member
from __future__ import absolute_import, print_function
import sys

# pylint: disable=undefined-all-variable
__all__ = [
    'get_version',
    'get_header_version',
    'supported_backends',
    'recommended_backends',
    'embeddable_backends',
    'time',
    'loop',
]

from zope.interface import implementer

from gevent._interfaces import ILoop

from gevent.libev import _corecffi # pylint:disable=no-name-in-module,import-error

ffi = _corecffi.ffi # pylint:disable=no-member
libev = _corecffi.lib # pylint:disable=no-member

if hasattr(libev, 'vfd_open'):
    # Must be on windows
    # pylint:disable=c-extension-no-member
    assert sys.platform.startswith("win"), "vfd functions only needed on windows"
    vfd_open = libev.vfd_open
    vfd_free = libev.vfd_free
    vfd_get = libev.vfd_get
else:
    vfd_open = vfd_free = vfd_get = lambda fd: fd

libev.gevent_set_ev_alloc()

#####
## NOTE on Windows:
# The C implementation does several things specially for Windows;
# a possibly incomplete list is:
#
# - the loop runs a periodic signal checker;
# - the io watcher constructor is different and it has a destructor;
# - the child watcher is not defined
#
# The CFFI implementation does none of these things, and so
# is possibly NOT FUNCTIONALLY CORRECT on Win32
#####


from gevent._ffi.loop import AbstractCallbacks
from gevent._ffi.loop import assign_standard_callbacks

class _Callbacks(AbstractCallbacks):
    # pylint:disable=arguments-differ,arguments-renamed

    def python_check_callback(self, *args):
        # There's a pylint bug (pylint 2.9.3, astroid 2.6.2) that causes pylint to crash
        # with an AttributeError on certain types of arguments-differ errors
        # But code in _ffi/loop depends on being able to find the watcher_ptr
        # argument is the local frame. BUT it gets invoked before the function body runs.
        # Hence the override of _find_watcher_ptr_in_traceback.
        # pylint:disable=unused-variable
        _loop, watcher_ptr, _events = args
        AbstractCallbacks.python_check_callback(self, watcher_ptr)

    def _find_watcher_ptr_in_traceback(self, tb):
        if tb is not None:
            l = tb.tb_frame.f_locals
            if 'watcher_ptr' in l:
                return l['watcher_ptr']
            if 'args' in l and len(l['args']) == 3:
                return l['args'][1]
        return AbstractCallbacks._find_watcher_ptr_in_traceback(self, tb)

    def python_prepare_callback(self, _loop_ptr, watcher_ptr, _events):
        AbstractCallbacks.python_prepare_callback(self, watcher_ptr)

    def _find_loop_from_c_watcher(self, watcher_ptr):
        loop_handle = ffi.cast('struct ev_watcher*', watcher_ptr).data
        return self.from_handle(loop_handle)

_callbacks = assign_standard_callbacks(ffi, libev, _Callbacks)


UNDEF = libev.EV_UNDEF
NONE = libev.EV_NONE
READ = libev.EV_READ
WRITE = libev.EV_WRITE
TIMER = libev.EV_TIMER
PERIODIC = libev.EV_PERIODIC
SIGNAL = libev.EV_SIGNAL
CHILD = libev.EV_CHILD
STAT = libev.EV_STAT
IDLE = libev.EV_IDLE
PREPARE = libev.EV_PREPARE
CHECK = libev.EV_CHECK
EMBED = libev.EV_EMBED
FORK = libev.EV_FORK
CLEANUP = libev.EV_CLEANUP
ASYNC = libev.EV_ASYNC
CUSTOM = libev.EV_CUSTOM
ERROR = libev.EV_ERROR

READWRITE = libev.EV_READ | libev.EV_WRITE

MINPRI = libev.EV_MINPRI
MAXPRI = libev.EV_MAXPRI

BACKEND_PORT = libev.EVBACKEND_PORT
BACKEND_KQUEUE = libev.EVBACKEND_KQUEUE
BACKEND_EPOLL = libev.EVBACKEND_EPOLL
BACKEND_POLL = libev.EVBACKEND_POLL
BACKEND_SELECT = libev.EVBACKEND_SELECT
FORKCHECK = libev.EVFLAG_FORKCHECK
NOINOTIFY = libev.EVFLAG_NOINOTIFY
SIGNALFD = libev.EVFLAG_SIGNALFD
NOSIGMASK = libev.EVFLAG_NOSIGMASK


from gevent._ffi.loop import EVENTS
GEVENT_CORE_EVENTS = EVENTS


def get_version():
    return 'libev-%d.%02d' % (libev.ev_version_major(), libev.ev_version_minor())


def get_header_version():
    return 'libev-%d.%02d' % (libev.EV_VERSION_MAJOR, libev.EV_VERSION_MINOR)

# This list backends in the order they are actually tried by libev,
# as defined in loop_init. The names must be lower case.
_flags = [
    # IOCP --- not supported/used.
    (libev.EVBACKEND_PORT, 'port'),
    (libev.EVBACKEND_KQUEUE, 'kqueue'),
    (libev.EVBACKEND_IOURING, 'linux_iouring'),
    (libev.EVBACKEND_LINUXAIO, "linux_aio"),
    (libev.EVBACKEND_EPOLL, 'epoll'),
    (libev.EVBACKEND_POLL, 'poll'),
    (libev.EVBACKEND_SELECT, 'select'),

    (libev.EVFLAG_NOENV, 'noenv'),
    (libev.EVFLAG_FORKCHECK, 'forkcheck'),
    (libev.EVFLAG_SIGNALFD, 'signalfd'),
    (libev.EVFLAG_NOSIGMASK, 'nosigmask')
]

_flags_str2int = dict((string, flag) for (flag, string) in _flags)



def _flags_to_list(flags):
    result = []
    for code, value in _flags:
        if flags & code:
            result.append(value)
        flags &= ~code
        if not flags:
            break
    if flags:
        result.append(flags)
    return result

if sys.version_info[0] >= 3:
    basestring = (bytes, str)
    integer_types = (int,)
else:
    import __builtin__ # pylint:disable=import-error
    basestring = (__builtin__.basestring,)
    integer_types = (int, __builtin__.long)


def _flags_to_int(flags):
    # Note, that order does not matter, libev has its own predefined order
    if not flags:
        return 0
    if isinstance(flags, integer_types):
        return flags
    result = 0
    try:
        if isinstance(flags, basestring):
            flags = flags.split(',')
        for value in flags:
            value = value.strip().lower()
            if value:
                result |= _flags_str2int[value]
    except KeyError as ex:
        raise ValueError('Invalid backend or flag: %s\nPossible values: %s' % (ex, ', '.join(sorted(_flags_str2int.keys()))))
    return result


def _str_hex(flag):
    if isinstance(flag, integer_types):
        return hex(flag)
    return str(flag)


def _check_flags(flags):
    as_list = []
    flags &= libev.EVBACKEND_MASK
    if not flags:
        return
    if not flags & libev.EVBACKEND_ALL:
        raise ValueError('Invalid value for backend: 0x%x' % flags)
    if not flags & libev.ev_supported_backends():
        as_list = [_str_hex(x) for x in _flags_to_list(flags)]
        raise ValueError('Unsupported backend: %s' % '|'.join(as_list))


def supported_backends():
    return _flags_to_list(libev.ev_supported_backends())


def recommended_backends():
    return _flags_to_list(libev.ev_recommended_backends())


def embeddable_backends():
    return _flags_to_list(libev.ev_embeddable_backends())


def time():
    return libev.ev_time()

from gevent._ffi.loop import AbstractLoop


from gevent.libev import watcher as _watchers
_events_to_str = _watchers._events_to_str # exported


@implementer(ILoop)
class loop(AbstractLoop):
    # pylint:disable=too-many-public-methods

    # libuv parameters simply won't accept anything lower than 1ms
    # (0.001s), but libev takes fractional seconds. In practice, on
    # one machine, libev can sleep for very small periods of time:
    #
    # sleep(0.00001) -> 0.000024
    # sleep(0.0001)  -> 0.000156
    # sleep(0.001)   -> 0.00136 (which is comparable to libuv)

    approx_timer_resolution = 0.00001

    error_handler = None

    _CHECK_POINTER = 'struct ev_check *'

    _PREPARE_POINTER = 'struct ev_prepare *'

    _TIMER_POINTER = 'struct ev_timer *'

    def __init__(self, flags=None, default=None):
        AbstractLoop.__init__(self, ffi, libev, _watchers, flags, default)
        self._default = bool(libev.ev_is_default_loop(self._ptr))

    def _init_loop(self, flags, default):
        c_flags = _flags_to_int(flags)
        _check_flags(c_flags)
        c_flags |= libev.EVFLAG_NOENV
        c_flags |= libev.EVFLAG_FORKCHECK
        if default is None:
            default = True
        if default:
            ptr = libev.gevent_ev_default_loop(c_flags)
            if not ptr:
                raise SystemError("ev_default_loop(%s) failed" % (c_flags, ))
        else:
            ptr = libev.ev_loop_new(c_flags)
            if not ptr:
                raise SystemError("ev_loop_new(%s) failed" % (c_flags, ))
        if default or SYSERR_CALLBACK is None:
            set_syserr_cb(self._handle_syserr)

        # Mark this loop as being used.
        libev.ev_set_userdata(ptr, ptr)
        return ptr

    def _init_and_start_check(self):
        libev.ev_check_init(self._check, libev.python_check_callback)
        self._check.data = self._handle_to_self
        libev.ev_check_start(self._ptr, self._check)
        self.unref()

    def _init_and_start_prepare(self):
        libev.ev_prepare_init(self._prepare, libev.python_prepare_callback)
        libev.ev_prepare_start(self._ptr, self._prepare)
        self.unref()

    def _init_callback_timer(self):
        libev.ev_timer_init(self._timer0, libev.gevent_noop, 0.0, 0.0)

    def _stop_callback_timer(self):
        libev.ev_timer_stop(self._ptr, self._timer0)

    def _start_callback_timer(self):
        libev.ev_timer_start(self._ptr, self._timer0)

    def _stop_aux_watchers(self):
        super(loop, self)._stop_aux_watchers()
        if libev.ev_is_active(self._prepare):
            self.ref()
            libev.ev_prepare_stop(self._ptr, self._prepare)
        if libev.ev_is_active(self._check):
            self.ref()
            libev.ev_check_stop(self._ptr, self._check)
        if libev.ev_is_active(self._timer0):
            libev.ev_timer_stop(self._timer0)

    def _setup_for_run_callback(self):
        # XXX: libuv needs to start the callback timer to be sure
        # that the loop wakes up and calls this. Our C version doesn't
        # do this.
        # self._start_callback_timer()
        self.ref() # we should go through the loop now

    def destroy(self):
        if self._ptr:
            super(loop, self).destroy()
            # pylint:disable=comparison-with-callable
            if globals()["SYSERR_CALLBACK"] == self._handle_syserr:
                set_syserr_cb(None)


    def _can_destroy_loop(self, ptr):
        # Is it marked as destroyed?
        return libev.ev_userdata(ptr)

    def _destroy_loop(self, ptr):
        # Mark as destroyed.
        libev.ev_set_userdata(ptr, ffi.NULL)
        libev.ev_loop_destroy(ptr)

        libev.gevent_zero_prepare(self._prepare)
        libev.gevent_zero_check(self._check)
        libev.gevent_zero_timer(self._timer0)

        del self._prepare
        del self._check
        del self._timer0


    @property
    def MAXPRI(self):
        return libev.EV_MAXPRI

    @property
    def MINPRI(self):
        return libev.EV_MINPRI

    def _default_handle_error(self, context, type, value, tb): # pylint:disable=unused-argument
        super(loop, self)._default_handle_error(context, type, value, tb)
        libev.ev_break(self._ptr, libev.EVBREAK_ONE)

    def run(self, nowait=False, once=False):
        flags = 0
        if nowait:
            flags |= libev.EVRUN_NOWAIT
        if once:
            flags |= libev.EVRUN_ONCE

        libev.ev_run(self._ptr, flags)

    def reinit(self):
        libev.ev_loop_fork(self._ptr)

    def ref(self):
        libev.ev_ref(self._ptr)

    def unref(self):
        libev.ev_unref(self._ptr)

    def break_(self, how=libev.EVBREAK_ONE):
        libev.ev_break(self._ptr, how)

    def verify(self):
        libev.ev_verify(self._ptr)

    def now(self):
        return libev.ev_now(self._ptr)

    def update_now(self):
        libev.ev_now_update(self._ptr)

    def __repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), self._format())

    @property
    def iteration(self):
        return libev.ev_iteration(self._ptr)

    @property
    def depth(self):
        return libev.ev_depth(self._ptr)

    @property
    def backend_int(self):
        return libev.ev_backend(self._ptr)

    @property
    def backend(self):
        backend = libev.ev_backend(self._ptr)
        for key, value in _flags:
            if key == backend:
                return value
        return backend

    @property
    def pendingcnt(self):
        return libev.ev_pending_count(self._ptr)

    def closing_fd(self, fd):
        pending_before = libev.ev_pending_count(self._ptr)
        libev.ev_feed_fd_event(self._ptr, fd, 0xFFFF)
        pending_after = libev.ev_pending_count(self._ptr)
        return pending_after > pending_before

    if sys.platform != "win32":

        def install_sigchld(self):
            libev.gevent_install_sigchld_handler()

        def reset_sigchld(self):
            libev.gevent_reset_sigchld_handler()

    def fileno(self):
        if self._ptr and LIBEV_EMBED:
            # If we don't embed, we can't access these fields,
            # the type is opaque
            fd = self._ptr.backend_fd
            if fd >= 0:
                return fd

    @property
    def activecnt(self):
        if not self._ptr:
            raise ValueError('operation on destroyed loop')
        if LIBEV_EMBED:
            return self._ptr.activecnt
        return -1


@ffi.def_extern()
def _syserr_cb(msg):
    try:
        msg = ffi.string(msg)
        SYSERR_CALLBACK(msg, ffi.errno)
    except:
        set_syserr_cb(None)
        raise  # let cffi print the traceback


def set_syserr_cb(callback):
    global SYSERR_CALLBACK
    if callback is None:
        libev.ev_set_syserr_cb(ffi.NULL)
        SYSERR_CALLBACK = None
    elif callable(callback):
        libev.ev_set_syserr_cb(libev._syserr_cb)
        SYSERR_CALLBACK = callback
    else:
        raise TypeError('Expected callable or None, got %r' % (callback, ))

SYSERR_CALLBACK = None

LIBEV_EMBED = libev.LIBEV_EMBED
