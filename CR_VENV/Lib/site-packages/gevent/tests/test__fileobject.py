from __future__ import print_function
from __future__ import absolute_import

import functools
import gc
import io
import os
import sys
import tempfile
import unittest

import gevent
from gevent import fileobject
from gevent._fileobjectcommon import OpenDescriptor
try:
    from gevent._fileobjectposix import GreenOpenDescriptor
except ImportError:
    GreenOpenDescriptor = None

from gevent._compat import PY2
from gevent._compat import PY3
from gevent._compat import text_type

import gevent.testing as greentest
from gevent.testing import sysinfo

try:
    ResourceWarning # pylint:disable=used-before-assignment
except NameError:
    class ResourceWarning(Warning):
        "Python 2 fallback"

# pylint:disable=unspecified-encoding

def Writer(fobj, line):
    for character in line:
        fobj.write(character)
        fobj.flush()
    fobj.close()


def close_fd_quietly(fd):
    try:
        os.close(fd)
    except (IOError, OSError):
        pass

def skipUnlessWorksWithRegularFiles(func):
    @functools.wraps(func)
    def f(self):
        if not self.WORKS_WITH_REGULAR_FILES:
            self.skipTest("Doesn't work with regular files")
        func(self)
    return f


class CleanupMixin(object):
    def _mkstemp(self, suffix):
        fileno, path = tempfile.mkstemp(suffix)
        self.addCleanup(os.remove, path)
        self.addCleanup(close_fd_quietly, fileno)
        return fileno, path

    def _pipe(self):
        r, w = os.pipe()
        self.addCleanup(close_fd_quietly, r)
        self.addCleanup(close_fd_quietly, w)
        return r, w


class TestFileObjectBlock(CleanupMixin,
                          greentest.TestCase):
    # serves as a base for the concurrent tests too

    WORKS_WITH_REGULAR_FILES = True

    def _getTargetClass(self):
        return fileobject.FileObjectBlock

    def _makeOne(self, *args, **kwargs):
        return self._getTargetClass()(*args, **kwargs)

    def _test_del(self, **kwargs):
        r, w = self._pipe()
        self._do_test_del((r, w), **kwargs)

    def _do_test_del(self, pipe, **kwargs):
        r, w = pipe
        s = self._makeOne(w, 'wb', **kwargs)
        s.write(b'x')
        try:
            s.flush()
        except IOError:
            # Sometimes seen on Windows/AppVeyor
            print("Failed flushing fileobject", repr(s), file=sys.stderr)
            import traceback
            traceback.print_exc()

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', ResourceWarning)
            # Deliberately getting ResourceWarning with FileObject(Thread) under Py3
            del s
            gc.collect() # PyPy

        if kwargs.get("close", True):
            with self.assertRaises((OSError, IOError)):
                # expected, because FileObject already closed it
                os.close(w)
        else:
            os.close(w)

        with self._makeOne(r, 'rb') as fobj:
            self.assertEqual(fobj.read(), b'x')

    def test_del(self):
        # Close should be true by default
        self._test_del()

    def test_del_close(self):
        self._test_del(close=True)


    @skipUnlessWorksWithRegularFiles
    def test_seek(self):
        fileno, path = self._mkstemp('.gevent.test__fileobject.test_seek')

        s = b'a' * 1024
        os.write(fileno, b'B' * 15)
        os.write(fileno, s)
        os.close(fileno)

        with open(path, 'rb') as f:
            f.seek(15)
            native_data = f.read(1024)

        with open(path, 'rb') as f_raw:
            f = self._makeOne(f_raw, 'rb', close=False)

            if PY3 or hasattr(f, 'seekable'):
                # On Python 3, all objects should have seekable.
                # On Python 2, only our custom objects do.
                self.assertTrue(f.seekable())
            f.seek(15)
            self.assertEqual(15, f.tell())

            # Note that a duplicate close() of the underlying
            # file descriptor can look like an OSError from this line
            # as we exit the with block
            fileobj_data = f.read(1024)

        self.assertEqual(native_data, s)
        self.assertEqual(native_data, fileobj_data)

    def __check_native_matches(self, byte_data, open_mode,
                               meth='read', open_path=True,
                               **open_kwargs):
        fileno, path = self._mkstemp('.gevent_test_' + open_mode)

        os.write(fileno, byte_data)
        os.close(fileno)

        with io.open(path, open_mode, **open_kwargs) as f:
            native_data = getattr(f, meth)()

        if open_path:
            with self._makeOne(path, open_mode, **open_kwargs) as f:
                gevent_data = getattr(f, meth)()
        else:
            # Note that we don't use ``io.open()`` for the raw file,
            # on Python 2. We want 'r' to mean what the usual call to open() means.
            opener = io.open if PY3 else open
            with opener(path, open_mode, **open_kwargs) as raw:
                with self._makeOne(raw) as f:
                    gevent_data = getattr(f, meth)()

        self.assertEqual(native_data, gevent_data)
        return gevent_data

    @skipUnlessWorksWithRegularFiles
    def test_str_default_to_native(self):
        # With no 'b' or 't' given, read and write native str.
        gevent_data = self.__check_native_matches(b'abcdefg', 'r')
        self.assertIsInstance(gevent_data, str)

    @skipUnlessWorksWithRegularFiles
    def test_text_encoding(self):
        gevent_data = self.__check_native_matches(
            u'\N{SNOWMAN}'.encode('utf-8'),
            'r+',
            buffering=5, encoding='utf-8'
        )
        self.assertIsInstance(gevent_data, text_type)

    @skipUnlessWorksWithRegularFiles
    def test_does_not_leak_on_exception(self):
        # If an exception occurs during opening,
        # everything still gets cleaned up.
        pass

    @skipUnlessWorksWithRegularFiles
    def test_rbU_produces_bytes_readline(self):
        if sys.version_info > (3, 11):
            self.skipTest("U file mode was removed in 3.11")
        # Including U in rb still produces bytes.
        # Note that the universal newline behaviour is
        # essentially ignored in explicit bytes mode.
        gevent_data = self.__check_native_matches(
            b'line1\nline2\r\nline3\rlastline\n\n',
            'rbU',
            meth='readlines',
        )
        self.assertIsInstance(gevent_data[0], bytes)
        self.assertEqual(len(gevent_data), 4)

    @skipUnlessWorksWithRegularFiles
    def test_rU_produces_native(self):
        if sys.version_info > (3, 11):
            self.skipTest("U file mode was removed in 3.11")
        gevent_data = self.__check_native_matches(
            b'line1\nline2\r\nline3\rlastline\n\n',
            'rU',
            meth='readlines',
        )
        self.assertIsInstance(gevent_data[0], str)

    @skipUnlessWorksWithRegularFiles
    def test_r_readline_produces_native(self):
        gevent_data = self.__check_native_matches(
            b'line1\n',
            'r',
            meth='readline',
        )
        self.assertIsInstance(gevent_data, str)

    @skipUnlessWorksWithRegularFiles
    def test_r_readline_on_fobject_produces_native(self):
        gevent_data = self.__check_native_matches(
            b'line1\n',
            'r',
            meth='readline',
            open_path=False,
        )
        self.assertIsInstance(gevent_data, str)

    def test_close_pipe(self):
        # Issue #190, 203
        r, w = os.pipe()
        x = self._makeOne(r)
        y = self._makeOne(w, 'w')
        x.close()
        y.close()

    @skipUnlessWorksWithRegularFiles
    @greentest.ignores_leakcheck
    def test_name_after_close(self):
        fileno, path = self._mkstemp('.gevent_test_named_path_after_close')

        # Passing the fileno; the name is the same as the fileno, and
        # doesn't change when closed.
        f = self._makeOne(fileno)
        nf = os.fdopen(fileno)
        # On Python 2, os.fdopen() produces a name of <fdopen>;
        # we follow the Python 3 semantics everywhere.
        nf_name = '<fdopen>' if greentest.PY2 else fileno
        self.assertEqual(f.name, fileno)
        self.assertEqual(nf.name, nf_name)

        # A file-like object that has no name; we'll close the
        # `f` after this because we reuse the fileno, which
        # gets passed to fcntl and so must still be valid
        class Nameless(object):
            def fileno(self):
                return fileno
            close = flush = isatty = closed = writable = lambda self: False
            seekable = readable = lambda self: True

        nameless = self._makeOne(Nameless(), 'rb')
        with self.assertRaises(AttributeError):
            getattr(nameless, 'name')
        nameless.close()
        with self.assertRaises(AttributeError):
            getattr(nameless, 'name')

        f.close()
        try:
            nf.close()
        except (OSError, IOError):
            # OSError: Py3, IOError: Py2
            pass
        self.assertEqual(f.name, fileno)
        self.assertEqual(nf.name, nf_name)

        def check(arg):
            f = self._makeOne(arg)
            self.assertEqual(f.name, path)
            f.close()
            # Doesn't change after closed.
            self.assertEqual(f.name, path)

        # Passing the string
        check(path)

        # Passing an opened native object
        with open(path) as nf:
            check(nf)

        # An io object
        with io.open(path) as nf:
            check(nf)





class ConcurrentFileObjectMixin(object):
    # Additional tests for fileobjects that cooperate
    # and we have full control of the implementation

    def test_read1_binary_present(self):
        # Issue #840
        r, w = self._pipe()
        reader = self._makeOne(r, 'rb')
        self._close_on_teardown(reader)
        writer = self._makeOne(w, 'w')
        self._close_on_teardown(writer)
        self.assertTrue(hasattr(reader, 'read1'), dir(reader))

    def test_read1_text_not_present(self):
        # Only defined for binary.
        r, w = self._pipe()
        reader = self._makeOne(r, 'rt')
        self._close_on_teardown(reader)
        self.addCleanup(os.close, w)
        self.assertFalse(hasattr(reader, 'read1'), dir(reader))

    def test_read1_default(self):
        # If just 'r' is given, whether it has one or not
        # depends on if we're Python 2 or 3.
        r, w = self._pipe()
        self.addCleanup(os.close, w)
        reader = self._makeOne(r)
        self._close_on_teardown(reader)
        self.assertEqual(PY2, hasattr(reader, 'read1'))

    def test_bufsize_0(self):
        # Issue #840
        r, w = self._pipe()
        x = self._makeOne(r, 'rb', bufsize=0)
        y = self._makeOne(w, 'wb', bufsize=0)
        self._close_on_teardown(x)
        self._close_on_teardown(y)
        y.write(b'a')
        b = x.read(1)
        self.assertEqual(b, b'a')

        y.writelines([b'2'])
        b = x.read(1)
        self.assertEqual(b, b'2')

    def test_newlines(self):
        import warnings
        r, w = self._pipe()
        lines = [b'line1\n', b'line2\r', b'line3\r\n', b'line4\r\nline5', b'\nline6']
        g = gevent.spawn(Writer, self._makeOne(w, 'wb'), lines)

        try:
            with warnings.catch_warnings():
                if sys.version_info > (3, 11):
                    # U is removed in Python 3.11
                    mode = 'r'
                    self.skipTest("U file mode was removed in 3.11")
                else:
                    # U is deprecated in Python 3, shows up on FileObjectThread
                    warnings.simplefilter('ignore', DeprecationWarning)
                    mode = 'rU'
                fobj = self._makeOne(r, mode)
            result = fobj.read()
            fobj.close()
            self.assertEqual('line1\nline2\nline3\nline4\nline5\nline6', result)
        finally:
            g.kill()


class TestFileObjectThread(ConcurrentFileObjectMixin, # pylint:disable=too-many-ancestors
                           TestFileObjectBlock):

    def _getTargetClass(self):
        return fileobject.FileObjectThread

    def test_del_noclose(self):
        # In the past, we used os.fdopen() when given a file descriptor,
        # and that has a destructor that can't be bypassed, so
        # close=false wasn't allowed. Now that we do everything with the
        # io module, it is allowed.
        self._test_del(close=False)

    # We don't test this with FileObjectThread. Sometimes the
    # visibility of the 'close' operation, which happens in a
    # background thread, doesn't make it to the foreground
    # thread in a timely fashion, leading to 'os.close(4) must
    # not succeed' in test_del_close. We have the same thing
    # with flushing and closing in test_newlines. Both of
    # these are most commonly (only?) observed on Py27/64-bit.
    # They also appear on 64-bit 3.6 with libuv

    def test_del(self):
        raise unittest.SkipTest("Race conditions")

    def test_del_close(self):
        raise unittest.SkipTest("Race conditions")


@unittest.skipUnless(
    hasattr(fileobject, 'FileObjectPosix'),
    "Needs FileObjectPosix"
)
class TestFileObjectPosix(ConcurrentFileObjectMixin, # pylint:disable=too-many-ancestors
                          TestFileObjectBlock):

    if sysinfo.LIBUV and sysinfo.LINUX:
        # On Linux, initializing the watcher for a regular
        # file results in libuv raising EPERM. But that works
        # fine on other platforms.
        WORKS_WITH_REGULAR_FILES = False

    def _getTargetClass(self):
        return fileobject.FileObjectPosix

    def test_seek_raises_ioerror(self):
        # https://github.com/gevent/gevent/issues/1323

        # Get a non-seekable file descriptor
        r, _w = self._pipe()

        with self.assertRaises(OSError) as ctx:
            os.lseek(r, 0, os.SEEK_SET)
        os_ex = ctx.exception

        with self.assertRaises(IOError) as ctx:
            f = self._makeOne(r, 'r', close=False)
            # Seek directly using the underlying GreenFileDescriptorIO;
            # the buffer may do different things, depending
            # on the version of Python (especially 3.7+)
            f.fileio.seek(0)
        io_ex = ctx.exception

        self.assertEqual(io_ex.errno, os_ex.errno)
        self.assertEqual(io_ex.strerror, os_ex.strerror)
        self.assertEqual(io_ex.args, os_ex.args)
        self.assertEqual(str(io_ex), str(os_ex))

class TestTextMode(CleanupMixin, unittest.TestCase):

    def test_default_mode_writes_linesep(self):
        # See https://github.com/gevent/gevent/issues/1282
        # libuv 1.x interferes with the default line mode on
        # Windows.
        # First, make sure we initialize gevent
        gevent.get_hub()

        fileno, path = self._mkstemp('.gevent.test__fileobject.test_default')
        os.close(fileno)

        with open(path, "w") as f:
            f.write("\n")

        with open(path, "rb") as f:
            data = f.read()

        self.assertEqual(data, os.linesep.encode('ascii'))

class TestOpenDescriptor(CleanupMixin, greentest.TestCase):

    def _getTargetClass(self):
        return OpenDescriptor

    def _makeOne(self, *args, **kwargs):
        return self._getTargetClass()(*args, **kwargs)

    def _check(self, regex, kind, *args, **kwargs):
        with self.assertRaisesRegex(kind, regex):
            self._makeOne(*args, **kwargs)

    case = lambda re, **kwargs: (re, TypeError, kwargs)
    vase = lambda re, **kwargs: (re, ValueError, kwargs)
    CASES = (
        case('mode', mode=42),
        case('buffering', buffering='nope'),
        case('encoding', encoding=42),
        case('errors', errors=42),
        vase('mode', mode='aoeug'),
        vase('mode U cannot be combined', mode='wU'),
        vase('text and binary', mode='rtb'),
        vase('append mode at once', mode='rw'),
        vase('exactly one', mode='+'),
        vase('take an encoding', mode='rb', encoding='ascii'),
        vase('take an errors', mode='rb', errors='strict'),
        vase('take a newline', mode='rb', newline='\n'),
    )

    def test_atomicwrite_fd(self):
        from gevent._fileobjectcommon import WriteallMixin
        # It basically only does something when buffering is otherwise disabled
        fileno, _w = self._pipe()
        desc = self._makeOne(fileno, 'wb',
                             buffering=0,
                             closefd=False,
                             atomic_write=True)
        self.assertTrue(desc.atomic_write)

        fobj = desc.opened()
        self.assertIsInstance(fobj, WriteallMixin)
        os.close(fileno)

def pop():
    for regex, kind, kwargs in TestOpenDescriptor.CASES:
        setattr(
            TestOpenDescriptor, 'test_' + regex.replace(' ', '_'),
            lambda self, _re=regex, _kind=kind, _kw=kwargs: self._check(_re, _kind, 1, **_kw)
        )
pop()

@unittest.skipIf(GreenOpenDescriptor is None, "No support for non-blocking IO")
class TestGreenOpenDescripton(TestOpenDescriptor):
    def _getTargetClass(self):
        return GreenOpenDescriptor




if __name__ == '__main__':
    greentest.main()
