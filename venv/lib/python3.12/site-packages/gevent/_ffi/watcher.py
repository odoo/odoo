"""
Useful base classes for watchers. The available
watchers will depend on the specific event loop.
"""
# pylint:disable=not-callable
from __future__ import absolute_import, print_function

import signal as signalmodule
import functools
import warnings

from gevent._config import config
from gevent._util import LazyOnClass

try:
    from tracemalloc import get_object_traceback

    def tracemalloc(init):
        # PYTHONTRACEMALLOC env var controls this on Python 3.
        return init
except ImportError: # Python < 3.4

    if config.trace_malloc:
        # Use the same env var to turn this on for Python 2
        import traceback

        class _TB(object):
            __slots__ = ('lines',)

            def __init__(self, lines):
                # These end in newlines, which we don't want for consistency
                self.lines = [x.rstrip() for x in lines]

            def format(self):
                return self.lines

        def tracemalloc(init):
            @functools.wraps(init)
            def traces(self, *args, **kwargs):
                init(self, *args, **kwargs)
                self._captured_malloc = _TB(traceback.format_stack())
            return traces

        def get_object_traceback(obj):
            return obj._captured_malloc

    else:
        def get_object_traceback(_obj):
            return None

        def tracemalloc(init):
            return init

from gevent._compat import fsencode

from gevent._ffi import _dbg # pylint:disable=unused-import
from gevent._ffi import GEVENT_DEBUG_LEVEL
from gevent._ffi import DEBUG
from gevent._ffi.loop import GEVENT_CORE_EVENTS
from gevent._ffi.loop import _NOARGS

ALLOW_WATCHER_DEL = GEVENT_DEBUG_LEVEL >= DEBUG

__all__ = [

]

try:
    ResourceWarning # pylint:disable=used-before-assignment
except NameError:
    class ResourceWarning(Warning):
        "Python 2 fallback"

class _NoWatcherResult(int):

    def __repr__(self):
        return "<NoWatcher>"

_NoWatcherResult = _NoWatcherResult(0)

def events_to_str(event_field, all_events):
    result = []
    for (flag, string) in all_events:
        c_flag = flag
        if event_field & c_flag:
            result.append(string)
            event_field &=  (~c_flag)
        if not event_field:
            break
    if event_field:
        result.append(hex(event_field))
    return '|'.join(result)


def not_while_active(func):
    @functools.wraps(func)
    def nw(self, *args, **kwargs):
        if self.active:
            raise ValueError("not while active")
        func(self, *args, **kwargs)
    return nw

def only_if_watcher(func):
    @functools.wraps(func)
    def if_w(self):
        if self._watcher:
            return func(self)
        return _NoWatcherResult
    return if_w


class AbstractWatcherType(type):
    """
    Base metaclass for watchers.

    To use, you will:

    - subclass the watcher class defined from this type.
    - optionally subclass this type
    """
    # pylint:disable=bad-mcs-classmethod-argument

    _FFI = None
    _LIB = None

    def __new__(cls, name, bases, cls_dict):
        if name != 'watcher' and not cls_dict.get('_watcher_skip_ffi'):
            cls._fill_watcher(name, bases, cls_dict)
        if '__del__' in cls_dict and not ALLOW_WATCHER_DEL: # pragma: no cover
            raise TypeError("CFFI watchers are not allowed to have __del__")
        return type.__new__(cls, name, bases, cls_dict)

    @classmethod
    def _fill_watcher(cls, name, bases, cls_dict):
        # TODO: refactor smaller
        # pylint:disable=too-many-locals
        if name.endswith('_'):
            # Strip trailing _ added to avoid keyword duplications
            # e.g., async_
            name = name[:-1]

        def _mro_get(attr, bases, error=True):
            for b in bases:
                try:
                    return getattr(b, attr)
                except AttributeError:
                    continue
            if error: # pragma: no cover
                raise AttributeError(attr)
        _watcher_prefix = cls_dict.get('_watcher_prefix') or _mro_get('_watcher_prefix', bases)

        if '_watcher_type' not in cls_dict:
            watcher_type = _watcher_prefix + '_' + name
            cls_dict['_watcher_type'] = watcher_type
        elif not cls_dict['_watcher_type'].startswith(_watcher_prefix):
            watcher_type = _watcher_prefix + '_' + cls_dict['_watcher_type']
            cls_dict['_watcher_type'] = watcher_type

        active_name = _watcher_prefix + '_is_active'

        def _watcher_is_active(self):
            return getattr(self._LIB, active_name)

        LazyOnClass.lazy(cls_dict, _watcher_is_active)

        watcher_struct_name = cls_dict.get('_watcher_struct_name')
        if not watcher_struct_name:
            watcher_struct_pattern = (cls_dict.get('_watcher_struct_pattern')
                                      or _mro_get('_watcher_struct_pattern', bases, False)
                                      or 'struct %s')
            watcher_struct_name = watcher_struct_pattern % (watcher_type,)

        def _watcher_struct_pointer_type(self):
            return self._FFI.typeof(watcher_struct_name + ' *')

        LazyOnClass.lazy(cls_dict, _watcher_struct_pointer_type)

        callback_name = (cls_dict.get('_watcher_callback_name')
                         or _mro_get('_watcher_callback_name', bases, False)
                         or '_gevent_generic_callback')

        def _watcher_callback(self):
            return self._FFI.addressof(self._LIB, callback_name)

        LazyOnClass.lazy(cls_dict, _watcher_callback)

        def _make_meth(name, watcher_name):
            def meth(self):
                lib_name = self._watcher_type + '_' + name
                return getattr(self._LIB, lib_name)
            meth.__name__ = watcher_name
            return meth

        for meth_name in 'start', 'stop', 'init':
            watcher_name = '_watcher' + '_' + meth_name
            if watcher_name not in cls_dict:
                LazyOnClass.lazy(cls_dict, _make_meth(meth_name, watcher_name))

    def new_handle(cls, obj):
        return cls._FFI.new_handle(obj)

    def new(cls, kind):
        return cls._FFI.new(kind)

class watcher(object):

    _callback = None
    _args = None
    _watcher = None
    # self._handle has a reference to self, keeping it alive.
    # We must keep self._handle alive for ffi.from_handle() to be
    # able to work. We only fill this in when we are started,
    # and when we are stopped we destroy it.
    # NOTE: This is a GC cycle, so we keep it around for as short
    # as possible.
    _handle = None

    @tracemalloc
    def __init__(self, _loop, ref=True, priority=None, args=_NOARGS):
        self.loop = _loop
        self.__init_priority = priority
        self.__init_args = args
        self.__init_ref = ref
        self._watcher_full_init()


    def _watcher_full_init(self):
        priority = self.__init_priority
        ref = self.__init_ref
        args = self.__init_args

        self._watcher_create(ref)

        if priority is not None:
            self._watcher_ffi_set_priority(priority)

        try:
            self._watcher_ffi_init(args)
        except:
            # Let these be GC'd immediately.
            # If we keep them around to when *we* are gc'd,
            # they're probably invalid, meaning any native calls
            # we do then to close() them are likely to fail
            self._watcher = None
            raise
        self._watcher_ffi_set_init_ref(ref)

    @classmethod
    def _watcher_ffi_close(cls, ffi_watcher):
        pass

    def _watcher_create(self, ref): # pylint:disable=unused-argument
        self._watcher = self._watcher_new()

    def _watcher_new(self):
        return type(self).new(self._watcher_struct_pointer_type) # pylint:disable=no-member

    def _watcher_ffi_set_init_ref(self, ref):
        pass

    def _watcher_ffi_set_priority(self, priority):
        pass

    def _watcher_ffi_init(self, args):
        raise NotImplementedError()

    def _watcher_ffi_start(self):
        raise NotImplementedError()

    def _watcher_ffi_stop(self):
        self._watcher_stop(self.loop.ptr, self._watcher)

    def _watcher_ffi_ref(self):
        raise NotImplementedError()

    def _watcher_ffi_unref(self):
        raise NotImplementedError()

    def _watcher_ffi_start_unref(self):
        # While a watcher is active, we don't keep it
        # referenced. This allows a timer, for example, to be started,
        # and still allow the loop to end if there is nothing
        # else to do. see test__order.TestSleep0 for one example.
        self._watcher_ffi_unref()

    def _watcher_ffi_stop_ref(self):
        self._watcher_ffi_ref()

    # A string identifying the type of libev object we watch, e.g., 'ev_io'
    # This should be a class attribute.
    _watcher_type = None
    # A class attribute that is the callback on the libev object that init's the C struct,
    # e.g., libev.ev_io_init. If None, will be set by _init_subclasses.
    _watcher_init = None
    # A class attribute that is the callback on the libev object that starts the C watcher,
    # e.g., libev.ev_io_start. If None, will be set by _init_subclasses.
    _watcher_start = None
    # A class attribute that is the callback on the libev object that stops the C watcher,
    # e.g., libev.ev_io_stop. If None, will be set by _init_subclasses.
    _watcher_stop = None
    # A cffi ctype object identifying the struct pointer we create.
    # This is a class attribute set based on the _watcher_type
    _watcher_struct_pointer_type = None
    # The attribute of the libev object identifying the custom
    # callback function for this type of watcher. This is a class
    # attribute set based on the _watcher_type in _init_subclasses.
    _watcher_callback = None
    _watcher_is_active = None

    def close(self):
        if self._watcher is None:
            return

        self.stop()
        _watcher = self._watcher
        self._watcher = None
        self._watcher_set_data(_watcher, self._FFI.NULL) # pylint: disable=no-member
        self._watcher_ffi_close(_watcher)
        self.loop = None

    def _watcher_set_data(self, the_watcher, data):
        # This abstraction exists for the sole benefit of
        # libuv.watcher.stat, which "subclasses" uv_handle_t.
        # Can we do something to avoid this extra function call?
        the_watcher.data = data
        return data

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        self.close()

    if ALLOW_WATCHER_DEL:
        def __del__(self):
            if self._watcher:
                tb = get_object_traceback(self)
                tb_msg = ''
                if tb is not None:
                    tb_msg = '\n'.join(tb.format())
                    tb_msg = '\nTraceback:\n' + tb_msg
                warnings.warn("Failed to close watcher %r%s" % (self, tb_msg),
                              ResourceWarning)

                # may fail if __init__ did; will be harmlessly printed
                self.close()

    __in_repr = False

    def __repr__(self):
        basic = "<%s at 0x%x" % (self.__class__.__name__, id(self))
        if self.__in_repr:
            return basic + '>'
        # Running child watchers have been seen to have a
        # recursive repr in ``self.args``, thanks to ``gevent.os.fork_and_watch``
        # passing the watcher as an argument to its callback.
        self.__in_repr = True
        try:
            result = '%s%s' % (basic, self._format())
            if self.pending:
                result += " pending"
            if self.callback is not None:
                fself = getattr(self.callback, '__self__', None)
                if fself is self:
                    result += " callback=<bound method %s of self>" % (self.callback.__name__)
                else:
                    result += " callback=%r" % (self.callback, )
            if self.args is not None:
                result += " args=%r" % (self.args, )
            if self.callback is None and self.args is None:
                result += " stopped"
            result += " watcher=%s" % (self._watcher)
            result += " handle=%s" % (self._watcher_handle)
            result += " ref=%s" % (self.ref)
            return result + ">"
        finally:
            self.__in_repr = False

    @property
    def _watcher_handle(self):
        if self._watcher:
            return self._watcher.data

    def _format(self):
        return ''

    @property
    def ref(self):
        raise NotImplementedError()

    def _get_callback(self):
        return self._callback if '_callback' in self.__dict__ else None

    def _set_callback(self, cb):
        if not callable(cb) and cb is not None:
            raise TypeError("Expected callable, not %r" % (cb, ))
        if cb is None:
            if '_callback' in self.__dict__:
                del self._callback
        else:
            self._callback = cb
    callback = property(_get_callback, _set_callback)

    def _get_args(self):
        return self._args

    def _set_args(self, args):
        if not isinstance(args, tuple) and args is not None:
            raise TypeError("args must be a tuple or None")
        if args is None:
            if '_args' in self.__dict__:
                del self._args
        else:
            self._args = args

    args = property(_get_args, _set_args)

    def start(self, callback, *args):
        if callback is None:
            raise TypeError('callback must be callable, not None')
        self.callback = callback
        self.args = args or _NOARGS
        self.loop._keepaliveset.add(self)
        self._handle = self._watcher_set_data(self._watcher, type(self).new_handle(self)) # pylint:disable=no-member
        self._watcher_ffi_start()
        self._watcher_ffi_start_unref()

    def stop(self):
        if self.callback is None:
            assert self.loop is None or self not in self.loop._keepaliveset
            return
        self.callback = None
        # Only after setting the signal to make this idempotent do
        # we move ahead.
        self._watcher_ffi_stop_ref()
        self._watcher_ffi_stop()
        self.loop._keepaliveset.discard(self)
        self._handle = None
        self._watcher_set_data(self._watcher, self._FFI.NULL) # pylint:disable=no-member

        self.args = None

    def _get_priority(self):
        return None

    @not_while_active
    def _set_priority(self, priority):
        pass

    priority = property(_get_priority, _set_priority)


    @property
    def active(self):
        if self._watcher is not None and self._watcher_is_active(self._watcher):
            return True
        return False

    @property
    def pending(self):
        return False

watcher = AbstractWatcherType('watcher', (object,), dict(watcher.__dict__))

class IoMixin(object):

    EVENT_MASK = 0

    def __init__(self, loop, fd, events, ref=True, priority=None, _args=None):
        # Win32 only works with sockets, and only when we use libuv, because
        # we don't use _open_osfhandle. See libuv/watchers.py:io for a description.
        if fd < 0:
            raise ValueError('fd must be non-negative: %r' % fd)
        if events & ~self.EVENT_MASK:
            raise ValueError('illegal event mask: %r' % events)
        self._fd = fd
        super(IoMixin, self).__init__(loop, ref=ref, priority=priority,
                                      args=_args or (fd, events))

    def start(self, callback, *args, **kwargs):
        args = args or _NOARGS
        if kwargs.get('pass_events'):
            args = (GEVENT_CORE_EVENTS, ) + args
        super(IoMixin, self).start(callback, *args)

    def _format(self):
        return ' fd=%d' % self._fd

class TimerMixin(object):
    _watcher_type = 'timer'

    def __init__(self, loop, after=0.0, repeat=0.0, ref=True, priority=None):
        if repeat < 0.0:
            raise ValueError("repeat must be positive or zero: %r" % repeat)
        self._after = after
        self._repeat = repeat
        super(TimerMixin, self).__init__(loop, ref=ref, priority=priority, args=(after, repeat))

    def start(self, callback, *args, **kw):
        update = kw.get("update", self.loop.starting_timer_may_update_loop_time)
        if update:
            # Quoth the libev doc: "This is a costly operation and is
            # usually done automatically within ev_run(). This
            # function is rarely useful, but when some event callback
            # runs for a very long time without entering the event
            # loop, updating libev's idea of the current time is a
            # good idea."

            # 1.3 changed the default for this to False *unless* the loop is
            # running a callback; see libuv for details. Note that
            # starting Timeout objects still sets this to true.

            self.loop.update_now()
        super(TimerMixin, self).start(callback, *args)

    def again(self, callback, *args, **kw):
        raise NotImplementedError()


class SignalMixin(object):
    _watcher_type = 'signal'

    def __init__(self, loop, signalnum, ref=True, priority=None):
        if signalnum < 1 or signalnum >= signalmodule.NSIG:
            raise ValueError('illegal signal number: %r' % signalnum)
        # still possible to crash on one of libev's asserts:
        # 1) "libev: ev_signal_start called with illegal signal number"
        #    EV_NSIG might be different from signal.NSIG on some platforms
        # 2) "libev: a signal must not be attached to two different loops"
        #    we probably could check that in LIBEV_EMBED mode, but not in general
        self._signalnum = signalnum
        super(SignalMixin, self).__init__(loop, ref=ref, priority=priority, args=(signalnum, ))


class IdleMixin(object):
    _watcher_type = 'idle'


class PrepareMixin(object):
    _watcher_type = 'prepare'


class CheckMixin(object):
    _watcher_type = 'check'


class ForkMixin(object):
    _watcher_type = 'fork'


class AsyncMixin(object):
    _watcher_type = 'async'

    def send(self):
        raise NotImplementedError()

    def send_ignoring_arg(self, _ignored):
        """
        Calling compatibility with ``greenlet.switch(arg)``
        as used by waiters that have ``rawlink``.

        This is an advanced method, not usually needed.
        """
        return self.send()

    @property
    def pending(self):
        raise NotImplementedError()


class ChildMixin(object):

    # hack for libuv which doesn't extend watcher
    _CALL_SUPER_INIT = True

    def __init__(self, loop, pid, trace=0, ref=True):
        if not loop.default:
            raise TypeError('child watchers are only available on the default loop')
        loop.install_sigchld()
        self._pid = pid
        if self._CALL_SUPER_INIT:
            super(ChildMixin, self).__init__(loop, ref=ref, args=(pid, trace))

    def _format(self):
        return ' pid=%r rstatus=%r' % (self.pid, self.rstatus)

    @property
    def pid(self):
        return self._pid

    @property
    def rpid(self):
        # The received pid, the result of the waitpid() call.
        return self._rpid

    _rpid = None
    _rstatus = 0

    @property
    def rstatus(self):
        return self._rstatus

class StatMixin(object):

    @staticmethod
    def _encode_path(path):
        return fsencode(path)

    def __init__(self, _loop, path, interval=0.0, ref=True, priority=None):
        # Store the encoded path in the same attribute that corecext does
        self._paths = self._encode_path(path)

        # Keep the original path to avoid re-encoding, especially on Python 3
        self._path = path

        # Although CFFI would automatically convert a bytes object into a char* when
        # calling ev_stat_init(..., char*, ...), on PyPy the char* pointer is not
        # guaranteed to live past the function call. On CPython, only with a constant/interned
        # bytes object is the pointer guaranteed to last path the function call. (And since
        # Python 3 is pretty much guaranteed to produce a newly-encoded bytes object above, thats
        # rarely the case). Therefore, we must keep a reference to the produced cdata object
        # so that the struct ev_stat_watcher's `path` pointer doesn't become invalid/deallocated
        self._cpath = self._FFI.new('char[]', self._paths)

        self._interval = interval
        super(StatMixin, self).__init__(_loop, ref=ref, priority=priority,
                                        args=(self._cpath,
                                              interval))

    @property
    def path(self):
        return self._path

    @property
    def attr(self):
        raise NotImplementedError

    @property
    def prev(self):
        raise NotImplementedError

    @property
    def interval(self):
        return self._interval
