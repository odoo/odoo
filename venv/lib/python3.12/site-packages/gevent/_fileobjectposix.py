from __future__ import absolute_import
from __future__ import print_function
import os
import sys


from io import BytesIO
from io import DEFAULT_BUFFER_SIZE
from io import FileIO
from io import RawIOBase
from io import UnsupportedOperation

from gevent._compat import reraise
from gevent._fileobjectcommon import cancel_wait_ex
from gevent._fileobjectcommon import FileObjectBase
from gevent._fileobjectcommon import OpenDescriptor
from gevent._fileobjectcommon import WriteIsWriteallMixin
from gevent._hub_primitives import wait_on_watcher
from gevent.hub import get_hub
from gevent.os import _read
from gevent.os import _write
from gevent.os import ignored_errors
from gevent.os import make_nonblocking


class GreenFileDescriptorIO(RawIOBase):
    # Internal, undocumented, class. All that's documented is that this
    # is a IOBase object. Constructor is private.

    # Note that RawIOBase has a __del__ method that calls
    # self.close(). (In C implementations like CPython, this is
    # the type's tp_dealloc slot; prior to Python 3, the object doesn't
    # appear to have a __del__ method, even though it functionally does)

    _read_watcher = None
    _write_watcher = None
    _closed = False
    _seekable = None
    _keep_alive = None # An object that needs to live as long as we do.

    def __init__(self, fileno, open_descriptor, closefd=True):
        RawIOBase.__init__(self)

        self._closefd = closefd
        self._fileno = fileno
        self.name = fileno
        self.mode = open_descriptor.fileio_mode
        make_nonblocking(fileno)
        readable = open_descriptor.can_read
        writable = open_descriptor.can_write

        self.hub = get_hub()
        io_watcher = self.hub.loop.io
        try:
            if readable:
                self._read_watcher = io_watcher(fileno, 1)

            if writable:
                self._write_watcher = io_watcher(fileno, 2)
        except:
            # If anything goes wrong, it's important to go ahead and
            # close these watchers *now*, especially under libuv, so
            # that they don't get eventually reclaimed by the garbage
            # collector at some random time, thanks to the C level
            # slot (even though we don't seem to have any actual references
            # at the Python level). Previously, if we didn't close now,
            # that random close in the future would cause issues if we had duplicated
            # the fileno (if a wrapping with statement had closed an open fileobject,
            # for example)

            # test__fileobject can show a failure if this doesn't happen
            # TRAVIS=true GEVENT_LOOP=libuv python -m gevent.tests.test__fileobject \
            #    TestFileObjectPosix.test_seek TestFileObjectThread.test_bufsize_0
            self.close()
            raise

    def isatty(self):
        # TODO: Couldn't we just subclass FileIO?
        f = FileIO(self._fileno, 'r', False)
        try:
            return f.isatty()
        finally:
            f.close()

    def readable(self):
        return self._read_watcher is not None

    def writable(self):
        return self._write_watcher is not None

    def seekable(self):
        if self._seekable is None:
            try:
                os.lseek(self._fileno, 0, os.SEEK_CUR)
            except OSError:
                self._seekable = False
            else:
                self._seekable = True
        return self._seekable

    def fileno(self):
        return self._fileno

    @property
    def closed(self):
        return self._closed

    def __destroy_events(self):
        read_event = self._read_watcher
        write_event = self._write_watcher
        hub = self.hub
        self.hub = self._read_watcher = self._write_watcher = None

        hub.cancel_waits_close_and_then(
            (read_event, write_event),
            cancel_wait_ex,
            self.__finish_close,
            self._closefd,
            self._fileno,
            self._keep_alive
        )

    def close(self):
        if self._closed:
            return
        self.flush()
        # TODO: Can we use 'read_event is not None and write_event is
        # not None' to mean _closed?
        self._closed = True
        try:
            self.__destroy_events()
        finally:
            self._fileno = self._keep_alive = None

    @staticmethod
    def __finish_close(closefd, fileno, keep_alive):
        try:
            if closefd:
                os.close(fileno)
        finally:
            if hasattr(keep_alive, 'close'):
                keep_alive.close()

    # RawIOBase provides a 'read' method that will call readall() if
    # the `size` was missing or -1 and otherwise call readinto(). We
    # want to take advantage of this to avoid single byte reads when
    # possible. This is highlighted by a bug in BufferedIOReader that
    # calls read() in a loop when its readall() method is invoked;
    # this was fixed in Python 3.3, but we still need our workaround for 2.7. See
    # https://github.com/gevent/gevent/issues/675)
    def __read(self, n):
        if self._read_watcher is None:
            raise UnsupportedOperation('read')
        while 1:
            try:
                return _read(self._fileno, n)
            except OSError as ex:
                if ex.args[0] not in ignored_errors:
                    raise
            wait_on_watcher(self._read_watcher, None, None, self.hub)

    def readall(self):
        ret = BytesIO()
        while True:
            try:
                data = self.__read(DEFAULT_BUFFER_SIZE)
            except cancel_wait_ex:
                # We were closed while reading. A buffered reader
                # just returns what it has handy at that point,
                # so we do to.
                data = None
            if not data:
                break
            ret.write(data)
        return ret.getvalue()

    def readinto(self, b):
        data = self.__read(len(b))
        n = len(data)
        try:
            b[:n] = data
        except TypeError as err:
            import array
            if not isinstance(b, array.array):
                raise err
            b[:n] = array.array(b'b', data)
        return n

    def write(self, b):
        if self._write_watcher is None:
            raise UnsupportedOperation('write')
        while True:
            try:
                return _write(self._fileno, b)
            except OSError as ex:
                if ex.args[0] not in ignored_errors:
                    raise
            wait_on_watcher(self._write_watcher, None, None, self.hub)

    def seek(self, offset, whence=0):
        try:
            return os.lseek(self._fileno, offset, whence)
        except IOError: # pylint:disable=try-except-raise
            raise
        except OSError as ex: # pylint:disable=duplicate-except
            # Python 2.x
            # make sure on Python 2.x we raise an IOError
            # as documented for RawIOBase.
            # See https://github.com/gevent/gevent/issues/1323
            reraise(IOError, IOError(*ex.args), sys.exc_info()[2])

    def __repr__(self):
        return "<%s at 0x%x fileno=%s mode=%r>" % (
            type(self).__name__, id(self), self._fileno, self.mode
        )


class GreenFileDescriptorIOWriteall(WriteIsWriteallMixin,
                                    GreenFileDescriptorIO):
    pass


class GreenOpenDescriptor(OpenDescriptor):

    def _do_open_raw(self):
        if self.is_fd():
            fileio = GreenFileDescriptorIO(self._fobj, self, closefd=self.closefd)
        else:
            # Either an existing file object or a path string (which
            # we open to get a file object). In either case, the other object
            # owns the descriptor and we must not close it.
            closefd = False

            raw = OpenDescriptor._do_open_raw(self)

            fileno = raw.fileno()
            fileio = GreenFileDescriptorIO(fileno, self, closefd=closefd)
            fileio._keep_alive = raw
            # We can usually do better for a name, though.
            try:
                fileio.name = raw.name
            except AttributeError:
                del fileio.name
        return fileio

    def _make_atomic_write(self, result, raw):
        # Our return value from _do_open_raw is always a new
        # object that we own, so we're always free to change
        # the class.
        assert result is not raw or self._raw_object_is_new(raw)
        if result.__class__ is GreenFileDescriptorIO:
            result.__class__ = GreenFileDescriptorIOWriteall
        else:
            result = OpenDescriptor._make_atomic_write(self, result, raw)
        return result


class FileObjectPosix(FileObjectBase):
    """
    FileObjectPosix()

    A file-like object that operates on non-blocking files but
    provides a synchronous, cooperative interface.

    .. caution::
         This object is only effective wrapping files that can be used meaningfully
         with :func:`select.select` such as sockets and pipes.

         In general, on most platforms, operations on regular files
         (e.g., ``open('a_file.txt')``) are considered non-blocking
         already, even though they can take some time to complete as
         data is copied to the kernel and flushed to disk: this time
         is relatively bounded compared to sockets or pipes, though.
         A :func:`~os.read` or :func:`~os.write` call on such a file
         will still effectively block for some small period of time.
         Therefore, wrapping this class around a regular file is
         unlikely to make IO gevent-friendly: reading or writing large
         amounts of data could still block the event loop.

         If you'll be working with regular files and doing IO in large
         chunks, you may consider using
         :class:`~gevent.fileobject.FileObjectThread` or
         :func:`~gevent.os.tp_read` and :func:`~gevent.os.tp_write` to bypass this
         concern.

    .. tip::
         Although this object provides a :meth:`fileno` method and so
         can itself be passed to :func:`fcntl.fcntl`, setting the
         :data:`os.O_NONBLOCK` flag will have no effect (reads will
         still block the greenlet, although other greenlets can run).
         However, removing that flag *will cause this object to no
         longer be cooperative* (other greenlets will no longer run).

         You can use the internal ``fileio`` attribute of this object
         (a :class:`io.RawIOBase`) to perform non-blocking byte reads.
         Note, however, that once you begin directly using this
         attribute, the results from using methods of *this* object
         are undefined, especially in text mode. (See :issue:`222`.)

    .. versionchanged:: 1.1
       Now uses the :mod:`io` package internally. Under Python 2, previously
       used the undocumented class :class:`socket._fileobject`. This provides
       better file-like semantics (and portability to Python 3).
    .. versionchanged:: 1.2a1
       Document the ``fileio`` attribute for non-blocking reads.
    .. versionchanged:: 1.2a1

        A bufsize of 0 in write mode is no longer forced to be 1.
        Instead, the underlying buffer is flushed after every write
        operation to simulate a bufsize of 0. In gevent 1.0, a
        bufsize of 0 was flushed when a newline was written, while
        in gevent 1.1 it was flushed when more than one byte was
        written. Note that this may have performance impacts.
    .. versionchanged:: 1.3a1
        On Python 2, enabling universal newlines no longer forces unicode
        IO.
    .. versionchanged:: 1.5
       The default value for *mode* was changed from ``rb`` to ``r``. This is consistent
       with :func:`open`, :func:`io.open`, and :class:`~.FileObjectThread`, which is the
       default ``FileObject`` on some platforms.
    .. versionchanged:: 1.5
       Stop forcing buffering. Previously, given a ``buffering=0`` argument,
       *buffering* would be set to 1, and ``buffering=1`` would be forced to
       the default buffer size. This was a workaround for a long-standing concurrency
       issue. Now the *buffering* argument is interpreted as intended.
    """

    default_bufsize = DEFAULT_BUFFER_SIZE

    def __init__(self, *args, **kwargs):
        descriptor = GreenOpenDescriptor(*args, **kwargs)
        FileObjectBase.__init__(self, descriptor)
        # This attribute is documented as available for non-blocking reads.
        self.fileio = descriptor.opened_raw()

    def _do_close(self, fobj, closefd):
        try:
            fobj.close()
            # self.fileio already knows whether or not to close the
            # file descriptor
            self.fileio.close()
        finally:
            self.fileio = None
