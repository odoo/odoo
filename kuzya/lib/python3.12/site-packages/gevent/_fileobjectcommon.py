"""
gevent internals.
"""
from __future__ import absolute_import, print_function, division

try:
    from errno import EBADF
except ImportError:
    EBADF = 9

import io
import functools
import sys
import os

from gevent.hub import _get_hub_noargs as get_hub
from gevent._compat import integer_types
from gevent._compat import reraise
from gevent._compat import fspath
from gevent.lock import Semaphore, DummySemaphore

class cancel_wait_ex(IOError):

    def __init__(self):
        IOError.__init__(
            self,
            EBADF, 'File descriptor was closed in another greenlet')

class FileObjectClosed(IOError):

    def __init__(self):
        IOError.__init__(
            self,
            EBADF, 'Bad file descriptor (FileObject was closed)')

class UniversalNewlineBytesWrapper(io.TextIOWrapper):
    """
    Uses TextWrapper to decode universal newlines, but returns the
    results as bytes.

    This is for Python 2 where the 'rU' mode did that.
    """
    mode = None
    def __init__(self, fobj, line_buffering):
        # latin-1 has the ability to round-trip arbitrary bytes.
        io.TextIOWrapper.__init__(self, fobj, encoding='latin-1',
                                  newline=None,
                                  line_buffering=line_buffering)

    def read(self, *args, **kwargs):
        result = io.TextIOWrapper.read(self, *args, **kwargs)
        return result.encode('latin-1')

    def readline(self, limit=-1):
        result = io.TextIOWrapper.readline(self, limit)
        return result.encode('latin-1')

    def __iter__(self):
        # readlines() is implemented in terms of __iter__
        # and TextIOWrapper.__iter__ checks that readline returns
        # a unicode object, which we don't, so we override
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    next = __next__


class FlushingBufferedWriter(io.BufferedWriter):

    def write(self, b):
        ret = io.BufferedWriter.write(self, b)
        self.flush()
        return ret


class WriteallMixin(object):

    def writeall(self, value):
        """
        Similar to :meth:`socket.socket.sendall`, ensures that all the contents of
        *value* have been written (though not necessarily flushed) before returning.

        Returns the length of *value*.

        .. versionadded:: 20.12.0
        """
        # Do we need to play the same get_memory games we do with sockets?
        # And what about chunking for large values? See _socketcommon.py
        write = super(WriteallMixin, self).write

        total = len(value)
        while value:
            l = len(value)
            w = write(value)
            if w == l:
                break
            value = value[w:]
        return total


class FileIO(io.FileIO):
    """A subclass that we can dynamically assign __class__ for."""
    __slots__ = ()


class WriteIsWriteallMixin(WriteallMixin):

    def write(self, value):
        return self.writeall(value)


class WriteallFileIO(WriteIsWriteallMixin, io.FileIO):
    pass


class OpenDescriptor(object): # pylint:disable=too-many-instance-attributes
    """
    Interprets the arguments to `open`. Internal use only.

    Originally based on code in the stdlib's _pyio.py (Python implementation of
    the :mod:`io` module), but modified for gevent:

    - Native strings are returned on Python 2 when neither
      'b' nor 't' are in the mode string and no encoding is specified.
    - Universal newlines work in that mode.
    - Allows externally unbuffered text IO.

    :keyword bool atomic_write: If true, then if the opened, wrapped, stream
        is unbuffered (meaning that ``write`` can produce short writes and the return
        value needs to be checked), then the implementation will be adjusted so that
        ``write`` behaves like Python 2 on a built-in file object and writes the
        entire value. Only set this on Python 2; the only intended user is
        :class:`gevent.subprocess.Popen`.
    """

    @staticmethod
    def _collapse_arg(pref_name, preferred_val, old_name, old_val, default):
        # We could play tricks with the callers ``locals()`` to avoid having to specify
        # the name (which we only use for error handling) but ``locals()`` may be slow and
        # inhibit JIT (on PyPy), so we just write it out long hand.
        if preferred_val is not None and old_val is not None:
            raise TypeError("Cannot specify both %s=%s and %s=%s" % (
                pref_name, preferred_val,
                old_name, old_val
            ))
        if preferred_val is None and old_val is None:
            return default
        return preferred_val if preferred_val is not None else old_val

    def __init__(self, fobj, mode='r', bufsize=None, close=None,
                 encoding=None, errors=None, newline=None,
                 buffering=None, closefd=None,
                 atomic_write=False):
        # Based on code in the stdlib's _pyio.py from 3.8.
        # pylint:disable=too-many-locals,too-many-branches,too-many-statements

        closefd = self._collapse_arg('closefd', closefd, 'close', close, True)
        del close
        buffering = self._collapse_arg('buffering', buffering, 'bufsize', bufsize, -1)
        del bufsize

        if not hasattr(fobj, 'fileno'):
            if not isinstance(fobj, integer_types):
                # Not a fd. Support PathLike on Python 2 and Python <= 3.5.
                fobj = fspath(fobj)
            if not isinstance(fobj, (str, bytes) + integer_types): # pragma: no cover
                raise TypeError("invalid file: %r" % fobj)
            if isinstance(fobj, (str, bytes)):
                closefd = True

        if not isinstance(mode, str):
            raise TypeError("invalid mode: %r" % mode)
        if not isinstance(buffering, integer_types):
            raise TypeError("invalid buffering: %r" % buffering)
        if encoding is not None and not isinstance(encoding, str):
            raise TypeError("invalid encoding: %r" % encoding)
        if errors is not None and not isinstance(errors, str):
            raise TypeError("invalid errors: %r" % errors)

        modes = set(mode)
        if modes - set("axrwb+tU") or len(mode) > len(modes):
            raise ValueError("invalid mode: %r" % mode)

        creating = "x" in modes
        reading = "r" in modes
        writing = "w" in modes
        appending = "a" in modes
        updating = "+" in modes
        text = "t" in modes
        binary = "b" in modes
        universal = 'U' in modes

        can_write = creating or writing or appending or updating

        if universal:
            if can_write:
                raise ValueError("mode U cannot be combined with 'x', 'w', 'a', or '+'")
            # Just because the stdlib deprecates this, no need for us to do so as well.
            # Especially not while we still support Python 2.
            # import warnings
            # warnings.warn("'U' mode is deprecated",
            #               DeprecationWarning, 4)
            reading = True
        if text and binary:
            raise ValueError("can't have text and binary mode at once")
        if creating + reading + writing + appending > 1:
            raise ValueError("can't have read/write/append mode at once")
        if not (creating or reading or writing or appending):
            raise ValueError("must have exactly one of read/write/append mode")
        if binary and encoding is not None:
            raise ValueError("binary mode doesn't take an encoding argument")
        if binary and errors is not None:
            raise ValueError("binary mode doesn't take an errors argument")
        if binary and newline is not None:
            raise ValueError("binary mode doesn't take a newline argument")
        if binary and buffering == 1:
            import warnings
            warnings.warn("line buffering (buffering=1) isn't supported in binary "
                          "mode, the default buffer size will be used",
                          RuntimeWarning, 4)

        self._fobj = fobj
        self.fileio_mode = (
            (creating and "x" or "")
            + (reading and "r" or "")
            + (writing and "w" or "")
            + (appending and "a" or "")
            + (updating and "+" or "")
        )
        self.mode = self.fileio_mode + ('t' if text else '') + ('b' if binary else '')

        self.creating = creating
        self.reading = reading
        self.writing = writing
        self.appending = appending
        self.updating = updating
        self.text = text
        self.binary = binary
        self.can_write = can_write
        self.can_read = reading or updating
        self.native = (
            not self.text and not self.binary # Neither t nor b given.
            and not encoding and not errors # And no encoding or error handling either.
        )
        self.universal = universal

        self.buffering = buffering
        self.encoding = encoding
        self.errors = errors
        self.newline = newline
        self.closefd = closefd
        self.atomic_write = atomic_write

    default_buffer_size = io.DEFAULT_BUFFER_SIZE

    _opened = None
    _opened_raw = None

    def is_fd(self):
        return isinstance(self._fobj, integer_types)

    def opened(self):
        """
        Return the :meth:`wrapped` file object.
        """
        if self._opened is None:
            raw = self.opened_raw()
            try:
                self._opened = self.__wrapped(raw)
            except:
                # XXX: This might be a bug? Could we wind up closing
                # something we shouldn't close?
                raw.close()
                raise
        return self._opened

    def _raw_object_is_new(self, raw):
        return self._fobj is not raw

    def opened_raw(self):
        if self._opened_raw is None:
            self._opened_raw = self._do_open_raw()
        return self._opened_raw

    def _do_open_raw(self):
        if hasattr(self._fobj, 'fileno'):
            return self._fobj
        # io.FileIO doesn't allow assigning to its __class__,
        # and we can't know for sure here whether we need the atomic write()
        # method or not (it depends on the layers on top of us),
        # so we use a subclass that *does* allow assigning.
        return FileIO(self._fobj, self.fileio_mode, self.closefd)

    @staticmethod
    def is_buffered(stream):
        return (
            # buffering happens internally in the text codecs
            isinstance(stream, (io.BufferedIOBase, io.TextIOBase))
            or (hasattr(stream, 'buffer') and stream.buffer is not None)
        )

    @classmethod
    def buffer_size_for_stream(cls, stream):
        result = cls.default_buffer_size
        try:
            bs = os.fstat(stream.fileno()).st_blksize
        except (OSError, AttributeError):
            pass
        else:
            if bs > 1:
                result = bs
        return result

    def __buffered(self, stream, buffering):
        if self.updating:
            Buffer = io.BufferedRandom
        elif self.creating or self.writing or self.appending:
            Buffer = io.BufferedWriter
        elif self.reading:
            Buffer = io.BufferedReader
        else: # prgama: no cover
            raise ValueError("unknown mode: %r" % self.mode)

        try:
            result = Buffer(stream, buffering)
        except AttributeError:
            # Python 2 file() objects don't have the readable/writable
            # attributes. But they handle their own buffering.
            result = stream

        return result

    def _make_atomic_write(self, result, raw):
        # The idea was to swizzle the class with one that defines
        # write() to call writeall(). This avoids setting any
        # attribute on the return object, avoids an additional layer
        # of proxying, and avoids any reference cycles (if setting a
        # method on the object).
        #
        # However, this is not possible with the built-in io classes
        # (static types defined in C cannot have __class__ assigned).
        # Fortunately, we need this only for the specific case of
        # opening a file descriptor (subprocess.py) on Python 2, in
        # which we fully control the types involved.
        #
        # So rather than attempt that, we only implement exactly what we need.
        if result is not raw or self._raw_object_is_new(raw):
            if result.__class__ is FileIO:
                result.__class__ = WriteallFileIO
            else: # pragma: no cover
                raise NotImplementedError(
                    "Don't know how to make %s have atomic write. "
                    "Please open a gevent issue with your use-case." % (
                        result
                    )
                )
        return result

    def __wrapped(self, raw):
        """
        Wraps the raw IO object (`RawIOBase` or `io.TextIOBase`) in
        buffers, text decoding, and newline handling.
        """
        if self.binary and isinstance(raw, io.TextIOBase):
            # Can't do it. The TextIO object will have its own buffer, and
            # trying to read from the raw stream or the buffer without going through
            # the TextIO object is likely to lead to problems with the codec.
            raise ValueError("Unable to perform binary IO on top of text IO stream")

        result = raw
        buffering = self.buffering

        line_buffering = False
        if buffering == 1 or buffering < 0 and raw.isatty():
            buffering = -1
            line_buffering = True
        if buffering < 0:
            buffering = self.buffer_size_for_stream(result)

        if buffering < 0: # pragma: no cover
            raise ValueError("invalid buffering size")

        if buffering != 0 and not self.is_buffered(result):
            # Need to wrap our own buffering around it. If it
            # is already buffered, don't do so.
            result = self.__buffered(result, buffering)

        if not self.binary:
            # Either native or text at this point.
            # Python 2 and text mode, or Python 3 and either text or native (both are the same)
            if not isinstance(raw, io.TextIOBase):
                # Avoid double-wrapping a TextIOBase in another TextIOWrapper.
                # That tends not to work. See https://github.com/gevent/gevent/issues/1542
                result = io.TextIOWrapper(result, self.encoding, self.errors, self.newline,
                                          line_buffering)

        if result is not raw or self._raw_object_is_new(raw):
            # Set the mode, if possible, but only if we created a new
            # object.
            try:
                result.mode = self.mode
            except (AttributeError, TypeError):
                # AttributeError: No such attribute
                # TypeError: Readonly attribute (py2)
                pass

        if (
                self.atomic_write
                and not self.is_buffered(result)
                and not isinstance(result, WriteIsWriteallMixin)
        ):
            # Let subclasses have a say in how they make this atomic, and
            # whether or not they do so even if we're actually returning the raw object.
            result = self._make_atomic_write(result, raw)

        return result


class _ClosedIO(object):
    # Used for FileObjectBase._io when FOB.close()
    # is called. Lets us drop references to ``_io``
    # for GC/resource cleanup reasons, but keeps some useful
    # information around.
    __slots__ = ('name',)

    def __init__(self, io_obj):
        try:
            self.name = io_obj.name
        except AttributeError:
            pass

    def __getattr__(self, name):
        if name == 'name':
            # We didn't set it in __init__ because there wasn't one
            raise AttributeError
        raise FileObjectClosed

    def __bool__(self):
        return False
    __nonzero__ = __bool__


class FileObjectBase(object):
    """
    Internal base class to ensure a level of consistency
    between :class:`~.FileObjectPosix`, :class:`~.FileObjectThread`
    and :class:`~.FileObjectBlock`.
    """

    # List of methods we delegate to the wrapping IO object, if they
    # implement them and we do not.
    _delegate_methods = (
        # General methods
        'flush',
        'fileno',
        'writable',
        'readable',
        'seek',
        'seekable',
        'tell',

        # Read
        'read',
        'readline',
        'readlines',
        'read1',
        'readinto',

        # Write.
        # Note that we do not extend WriteallMixin,
        # so writeall will be copied, if it exists, and
        # wrapped.
        'write',
        'writeall',
        'writelines',
        'truncate',
    )


    _io = None

    def __init__(self, descriptor):
        # type: (OpenDescriptor) -> None
        self._io = descriptor.opened()
        # We don't actually use this property ourself, but we save it (and
        # pass it along) for compatibility.
        self._close = descriptor.closefd
        self._do_delegate_methods()


    io = property(lambda s: s._io,
                  # Historically we either hand-wrote all the delegation methods
                  # to use self.io, or we simply used __getattr__ to look them up at
                  # runtime. This meant people could change the io attribute on the fly
                  # and it would mostly work (subprocess.py used to do that). We don't recommend
                  # that, but we still support it.
                  lambda s, nv: setattr(s, '_io', nv) or s._do_delegate_methods())

    def _do_delegate_methods(self):
        for meth_name in self._delegate_methods:
            meth = getattr(self._io, meth_name, None)
            implemented_by_class = hasattr(type(self), meth_name)
            if meth and not implemented_by_class:
                setattr(self, meth_name, self._wrap_method(meth))
            elif hasattr(self, meth_name) and not implemented_by_class:
                delattr(self, meth_name)

    def _wrap_method(self, method):
        """
        Wrap a method we're copying into our dictionary from the underlying
        io object to do something special or different, if necessary.
        """
        return method

    @property
    def closed(self):
        """True if the file is closed"""
        return isinstance(self._io, _ClosedIO)

    def close(self):
        if isinstance(self._io, _ClosedIO):
            return

        fobj = self._io
        self._io = _ClosedIO(self._io)
        try:
            self._do_close(fobj, self._close)
        finally:
            fobj = None
            # Remove delegate methods to drop remaining references to
            # _io.
            d = self.__dict__
            for meth_name in self._delegate_methods:
                d.pop(meth_name, None)

    def _do_close(self, fobj, closefd):
        raise NotImplementedError()

    def __getattr__(self, name):
        return getattr(self._io, name)

    def __repr__(self):
        return '<%s at 0x%x %s_fobj=%r%s>' % (
            self.__class__.__name__,
            id(self),
            'closed' if self.closed else '',
            self.io,
            self._extra_repr()
        )

    def _extra_repr(self):
        return ''

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    next = __next__

    def __bool__(self):
        return True

    __nonzero__ = __bool__


class FileObjectBlock(FileObjectBase):
    """
    FileObjectBlock()

    A simple synchronous wrapper around a file object.

    Adds no concurrency or gevent compatibility.
    """

    def __init__(self, fobj, *args, **kwargs):
        descriptor = OpenDescriptor(fobj, *args, **kwargs)
        FileObjectBase.__init__(self, descriptor)

    def _do_close(self, fobj, closefd):
        fobj.close()


class FileObjectThread(FileObjectBase):
    """
    FileObjectThread()

    A file-like object wrapping another file-like object, performing all blocking
    operations on that object in a background thread.

    .. caution::
        Attempting to change the threadpool or lock of an existing FileObjectThread
        has undefined consequences.

    .. versionchanged:: 1.1b1
       The file object is closed using the threadpool. Note that whether or
       not this action is synchronous or asynchronous is not documented.
    """

    def __init__(self, *args, **kwargs):
        """
        :keyword bool lock: If True (the default) then all operations will
           be performed one-by-one. Note that this does not guarantee that, if using
           this file object from multiple threads/greenlets, operations will be performed
           in any particular order, only that no two operations will be attempted at the
           same time. You can also pass your own :class:`gevent.lock.Semaphore` to synchronize
           file operations with an external resource.
        :keyword bool closefd: If True (the default) then when this object is closed,
           the underlying object is closed as well. If *fobj* is a path, then
           *closefd* must be True.
        """
        lock = kwargs.pop('lock', True)
        threadpool = kwargs.pop('threadpool', None)
        descriptor = OpenDescriptor(*args, **kwargs)

        self.threadpool = threadpool or get_hub().threadpool
        self.lock = lock
        if self.lock is True:
            self.lock = Semaphore()
        elif not self.lock:
            self.lock = DummySemaphore()
        if not hasattr(self.lock, '__enter__'):
            raise TypeError('Expected a Semaphore or boolean, got %r' % type(self.lock))

        self.__io_holder = [descriptor.opened()] # signal for _wrap_method
        FileObjectBase.__init__(self, descriptor)

    def _do_close(self, fobj, closefd):
        self.__io_holder[0] = None # for _wrap_method
        try:
            with self.lock:
                self.threadpool.apply(fobj.flush)
        finally:
            if closefd:
                # Note that we're not taking the lock; older code
                # did fobj.close() without going through the threadpool at all,
                # so acquiring the lock could potentially introduce deadlocks
                # that weren't present before. Avoiding the lock doesn't make
                # the existing race condition any worse.
                # We wrap the close in an exception handler and re-raise directly
                # to avoid the (common, expected) IOError from being logged by the pool
                def close(_fobj=fobj):
                    try:
                        _fobj.close()
                    except: # pylint:disable=bare-except
                        # pylint:disable-next=return-in-finally
                        return sys.exc_info()
                    finally:
                        _fobj = None
                del fobj

                exc_info = self.threadpool.apply(close)
                del close

                if exc_info:
                    reraise(*exc_info)

    def _do_delegate_methods(self):
        FileObjectBase._do_delegate_methods(self)
        self.__io_holder[0] = self._io

    def _extra_repr(self):
        return ' threadpool=%r' % (self.threadpool,)

    def _wrap_method(self, method):
        # NOTE: We are careful to avoid introducing a refcycle
        # within self. Our wrapper cannot refer to self.
        io_holder = self.__io_holder
        lock = self.lock
        threadpool = self.threadpool

        @functools.wraps(method)
        def thread_method(*args, **kwargs):
            if io_holder[0] is None:
                # This is different than FileObjectPosix, etc,
                # because we want to save the expensive trip through
                # the threadpool.
                raise FileObjectClosed
            with lock:
                return threadpool.apply(method, args, kwargs)

        return thread_method
