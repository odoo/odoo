"""
Cooperative ``subprocess`` module.

.. caution:: On POSIX platforms, this module is not usable from native
   threads other than the main thread; attempting to do so will raise
   a :exc:`TypeError`. This module depends on libev's fork watchers.
   On POSIX systems, fork watchers are implemented using signals, and
   the thread to which process-directed signals are delivered `is not
   defined`_. Because each native thread has its own gevent/libev
   loop, this means that a fork watcher registered with one loop
   (thread) may never see the signal about a child it spawned if the
   signal is sent to a different thread.

.. note:: The interface of this module is intended to match that of
   the standard library :mod:`subprocess` module (with many backwards
   compatible extensions from Python 3 backported to Python 2). There
   are some small differences between the Python 2 and Python 3
   versions of that module (the Python 2 ``TimeoutExpired`` exception,
   notably, extends ``Timeout`` and there is no ``SubprocessError``) and between the
   POSIX and Windows versions. The HTML documentation here can only
   describe one version; for definitive documentation, see the
   standard library or the source code.

.. _is not defined: http://www.linuxprogrammingblog.com/all-about-linux-signals?page=11
"""
from __future__ import absolute_import, print_function
# Can we split this up to make it cleaner? See https://github.com/gevent/gevent/issues/748
# pylint: disable=too-many-lines
# Most of this we inherit from the standard lib
# pylint: disable=bare-except,too-many-locals,too-many-statements,attribute-defined-outside-init
# pylint: disable=too-many-branches,too-many-instance-attributes
# Most of this is cross-platform
# pylint: disable=no-member,expression-not-assigned,unused-argument,unused-variable
import errno
import gc
import os
import signal
import sys
import traceback
# Python 3.9
try:
    from types import GenericAlias
except ImportError:
    GenericAlias = None

try:
    import grp
except ImportError:
    grp = None

try:
    import pwd
except ImportError:
    pwd = None

from gevent.event import AsyncResult
from gevent.hub import _get_hub_noargs as get_hub
from gevent.hub import linkproxy
from gevent.hub import sleep
from gevent.hub import getcurrent
from gevent._compat import integer_types, string_types, xrange
from gevent._compat import PY3
from gevent._compat import PY35
from gevent._compat import PY36
from gevent._compat import PY37
from gevent._compat import PY38
from gevent._compat import PY311
from gevent._compat import PYPY
from gevent._compat import reraise
from gevent._compat import fsdecode
from gevent._compat import fsencode
from gevent._compat import PathLike
from gevent._util import _NONE
from gevent._util import copy_globals

from gevent.greenlet import Greenlet, joinall
spawn = Greenlet.spawn
import subprocess as __subprocess__


# Standard functions and classes that this module re-implements in a gevent-aware way.
__implements__ = [
    'Popen',
    'call',
    'check_call',
    'check_output',
]
if PY3 and not sys.platform.startswith('win32'):
    __implements__.append("_posixsubprocess")
    _posixsubprocess = None


# Some symbols we define that we expect to export;
# useful for static analysis
PIPE = "PIPE should be imported"

# Standard functions and classes that this module re-imports.
__imports__ = [
    'PIPE',
    'STDOUT',
    'CalledProcessError',
    # Windows:
    'CREATE_NEW_CONSOLE',
    'CREATE_NEW_PROCESS_GROUP',
    'STD_INPUT_HANDLE',
    'STD_OUTPUT_HANDLE',
    'STD_ERROR_HANDLE',
    'SW_HIDE',
    'STARTF_USESTDHANDLES',
    'STARTF_USESHOWWINDOW',
]


__extra__ = [
    'MAXFD',
    '_eintr_retry_call',
    'STARTUPINFO',
    'pywintypes',
    'list2cmdline',
    '_subprocess',
    '_winapi',
    # Python 2.5 does not have _subprocess, so we don't use it
    # XXX We don't run on Py 2.5 anymore; can/could/should we use _subprocess?
    # It's only used on mswindows
    'WAIT_OBJECT_0',
    'WaitForSingleObject',
    'GetExitCodeProcess',
    'GetStdHandle',
    'CreatePipe',
    'DuplicateHandle',
    'GetCurrentProcess',
    'DUPLICATE_SAME_ACCESS',
    'GetModuleFileName',
    'GetVersion',
    'CreateProcess',
    'INFINITE',
    'TerminateProcess',
    'STILL_ACTIVE',

    # These were added for 3.5, but we make them available everywhere.
    'run',
    'CompletedProcess',
]

if PY3:
    __imports__ += [
        'DEVNULL',
        'getstatusoutput',
        'getoutput',
        'SubprocessError',
        'TimeoutExpired',
    ]
else:
    __extra__.append("TimeoutExpired")


if PY35:
    __extra__.remove('run')
    __extra__.remove('CompletedProcess')
    __implements__.append('run')
    __implements__.append('CompletedProcess')

    # Removed in Python 3.5; this is the exact code that was removed:
    # https://hg.python.org/cpython/rev/f98b0a5e5ef5
    __extra__.remove('MAXFD')
    try:
        MAXFD = os.sysconf("SC_OPEN_MAX")
    except:
        MAXFD = 256

if PY36:
    # This was added to __all__ for windows in 3.6
    __extra__.remove('STARTUPINFO')
    __imports__.append('STARTUPINFO')

if PY37:
    __imports__.extend([
        'ABOVE_NORMAL_PRIORITY_CLASS', 'BELOW_NORMAL_PRIORITY_CLASS',
        'HIGH_PRIORITY_CLASS', 'IDLE_PRIORITY_CLASS',
        'NORMAL_PRIORITY_CLASS',
        'REALTIME_PRIORITY_CLASS',
        'CREATE_NO_WINDOW', 'DETACHED_PROCESS',
        'CREATE_DEFAULT_ERROR_MODE',
        'CREATE_BREAKAWAY_FROM_JOB'
    ])

if PY38:
    # Using os.posix_spawn() to start subprocesses
    # bypasses our child watchers on certain operating systems,
    # and with certain library versions. Possibly the right
    # fix is to monkey-patch os.posix_spawn like we do os.fork?
    # These have no effect, they're just here to match the stdlib.
    # TODO: When available, given a monkey patch on them, I think
    # we ought to be able to use them if the stdlib has identified them
    # as suitable.
    __implements__.extend([
        '_use_posix_spawn',
    ])

    def _use_posix_spawn():
        return False

    _USE_POSIX_SPAWN = False

    if __subprocess__._USE_POSIX_SPAWN:
        __implements__.extend([
            '_USE_POSIX_SPAWN',
        ])
    else:
        __imports__.extend([
            '_USE_POSIX_SPAWN',
        ])

if PY311:
    # Python 3.11 added some module-level attributes to control the
    # use of vfork. The docs specifically say that you should not try to read
    # them, only set them, so we don't provide them.
    #
    # Python 3.11 also added a test,  test_surrogates_error_message, that behaves
    # differently based on whether or not the pure python implementation of forking
    # is in use, or the one written in C from _posixsubprocess. Obviously we don't call
    # that, so we need to make us look like a pure python version; it checks that this attribute
    # is none for that.
    _fork_exec = None
    __implements__.extend([
        '_fork_exec',
    ] if sys.platform != 'win32' else [
    ])

actually_imported = copy_globals(__subprocess__, globals(),
                                 only_names=__imports__,
                                 ignore_missing_names=True)
# anything we couldn't import from here we may need to find
# elsewhere
__extra__.extend(set(__imports__).difference(set(actually_imported)))
__imports__ = actually_imported
del actually_imported


# In Python 3 on Windows, a lot of the functions previously
# in _subprocess moved to _winapi
_subprocess = getattr(__subprocess__, '_subprocess', _NONE)
_winapi = getattr(__subprocess__, '_winapi', _NONE)

_attr_resolution_order = [__subprocess__, _subprocess, _winapi]

for name in list(__extra__):
    if name in globals():
        continue
    value = _NONE
    for place in _attr_resolution_order:
        value = getattr(place, name, _NONE)
        if value is not _NONE:
            break

    if value is _NONE:
        __extra__.remove(name)
    else:
        globals()[name] = value

del _attr_resolution_order
__all__ = __implements__ + __imports__
# Some other things we want to document
for _x in ('run', 'CompletedProcess', 'TimeoutExpired'):
    if _x not in __all__:
        __all__.append(_x)



mswindows = sys.platform == 'win32'
if mswindows:
    import msvcrt # pylint: disable=import-error
    if PY3:
        class Handle(int):
            closed = False

            def Close(self):
                if not self.closed:
                    self.closed = True
                    _winapi.CloseHandle(self)

            def Detach(self):
                if not self.closed:
                    self.closed = True
                    return int(self)
                raise ValueError("already closed")

            def __repr__(self):
                return "Handle(%d)" % int(self)

            __del__ = Close
            __str__ = __repr__
else:
    import fcntl
    import pickle
    from gevent import monkey
    fork = monkey.get_original('os', 'fork')
    from gevent.os import fork_and_watch

try:
    BrokenPipeError # pylint:disable=used-before-assignment
except NameError: # Python 2
    class BrokenPipeError(Exception):
        "Never raised, never caught."


def call(*popenargs, **kwargs):
    """
    call(args, *, stdin=None, stdout=None, stderr=None, shell=False, timeout=None) -> returncode

    Run command with arguments. Wait for command to complete or
    timeout, then return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example::

        retcode = call(["ls", "-l"])

    .. versionchanged:: 1.2a1
       The ``timeout`` keyword argument is now accepted on all supported
       versions of Python (not just Python 3) and if it expires will raise a
       :exc:`TimeoutExpired` exception (under Python 2 this is a subclass of :exc:`~.Timeout`).
    """
    timeout = kwargs.pop('timeout', None)
    with Popen(*popenargs, **kwargs) as p:
        try:
            return p.wait(timeout=timeout, _raise_exc=True)
        except:
            p.kill()
            p.wait()
            raise

def check_call(*popenargs, **kwargs):
    """
    check_call(args, *, stdin=None, stdout=None, stderr=None, shell=False, timeout=None) -> 0

    Run command with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    :exc:`CalledProcessError`.  The ``CalledProcessError`` object will have the
    return code in the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example::

        retcode = check_call(["ls", "-l"])
    """
    retcode = call(*popenargs, **kwargs)
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise CalledProcessError(retcode, cmd) # pylint:disable=undefined-variable
    return 0

def check_output(*popenargs, **kwargs):
    r"""
    check_output(args, *, input=None, stdin=None, stderr=None, shell=False, universal_newlines=False, timeout=None) -> output

    Run command with arguments and return its output.

    If the exit code was non-zero it raises a :exc:`CalledProcessError`.  The
    ``CalledProcessError`` object will have the return code in the returncode
    attribute and output in the output attribute.


    The arguments are the same as for the Popen constructor.  Example::

        >>> check_output(["ls", "-1", "/dev/null"])
        '/dev/null\n'

    The ``stdout`` argument is not allowed as it is used internally.

    To capture standard error in the result, use ``stderr=STDOUT``::

        >>> print(check_output(["/bin/sh", "-c",
        ...               "ls -l non_existent_file ; exit 0"],
        ...              stderr=STDOUT).decode('ascii').strip())
        ls: non_existent_file: No such file or directory

    There is an additional optional argument, "input", allowing you to
    pass a string to the subprocess's stdin.  If you use this argument
    you may not also use the Popen constructor's "stdin" argument, as
    it too will be used internally.  Example::

        >>> check_output(["sed", "-e", "s/foo/bar/"],
        ...              input=b"when in the course of fooman events\n")
        'when in the course of barman events\n'

    If ``universal_newlines=True`` is passed, the return value will be a
    string rather than bytes.

    .. versionchanged:: 1.2a1
       The ``timeout`` keyword argument is now accepted on all supported
       versions of Python (not just Python 3) and if it expires will raise a
       :exc:`TimeoutExpired` exception (under Python 2 this is a subclass of :exc:`~.Timeout`).
    .. versionchanged:: 1.2a1
       The ``input`` keyword argument is now accepted on all supported
       versions of Python, not just Python 3
    .. versionchanged:: 22.08.0
       Passing the ``check`` keyword argument is forbidden, just as in Python 3.11.
    """
    timeout = kwargs.pop('timeout', None)
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    if 'check' in kwargs:
        raise ValueError('check argument not allowed, it will be overridden.')
    if 'input' in kwargs:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments may not both be used.')
        inputdata = kwargs['input']
        del kwargs['input']
        kwargs['stdin'] = PIPE
    else:
        inputdata = None
    with Popen(*popenargs, stdout=PIPE, **kwargs) as process:
        try:
            output, unused_err = process.communicate(inputdata, timeout=timeout)
        except TimeoutExpired:
            process.kill()
            output, unused_err = process.communicate()
            raise TimeoutExpired(process.args, timeout, output=output)
        except:
            process.kill()
            process.wait()
            raise
        retcode = process.poll()
        if retcode:
            # pylint:disable=undefined-variable
            raise CalledProcessError(retcode, process.args, output=output)
    return output

_PLATFORM_DEFAULT_CLOSE_FDS = object()

if 'TimeoutExpired' not in globals():
    # Python 2

    # Make TimeoutExpired inherit from _Timeout so it can be caught
    # the way we used to throw things (except Timeout), but make sure it doesn't
    # init a timer. Note that we can't have a fake 'SubprocessError' that inherits
    # from exception, because we need TimeoutExpired to just be a BaseException for
    # bwc.
    from gevent.timeout import Timeout as _Timeout

    class TimeoutExpired(_Timeout):
        """
        This exception is raised when the timeout expires while waiting for
        a child process in `communicate`.

        Under Python 2, this is a gevent extension with the same name as the
        Python 3 class for source-code forward compatibility. However, it extends
        :class:`gevent.timeout.Timeout` for backwards compatibility (because
        we used to just raise a plain ``Timeout``); note that ``Timeout`` is a
        ``BaseException``, *not* an ``Exception``.

        .. versionadded:: 1.2a1
        """

        def __init__(self, cmd, timeout, output=None):
            _Timeout.__init__(self, None)
            self.cmd = cmd
            self.seconds = timeout
            self.output = output

        @property
        def timeout(self):
            return self.seconds

        def __str__(self):
            return ("Command '%s' timed out after %s seconds" %
                    (self.cmd, self.timeout))


if hasattr(os, 'set_inheritable'):
    _set_inheritable = os.set_inheritable
else:
    _set_inheritable = lambda i, v: True


def FileObject(*args, **kwargs):
    # Defer importing FileObject until we need it
    # to allow it to be configured more easily.
    from gevent.fileobject import FileObject as _FileObject
    if not PY3:
        # Make write behave like the old Python 2 file
        # write and loop to consume output, even when not
        # buffered.
        __FileObject = _FileObject
        def _FileObject(*args, **kwargs):
            kwargs['atomic_write'] = True
            return __FileObject(*args, **kwargs)
    globals()['FileObject'] = _FileObject
    return _FileObject(*args)


class _CommunicatingGreenlets(object):
    # At most, exactly one of these objects may be created
    # for a given Popen object. This ensures that only one background
    # greenlet at a time will be reading from the file object. This matters because
    # if a timeout exception is raised, the user may call back into communicate() to
    # get the output (usually after killing the process; see run()). We must not
    # lose output in that case (Python 3 specifically documents that raising a timeout
    # doesn't lose output). Also, attempting to read from a pipe while it's already
    # being read from results in `RuntimeError: reentrant call in io.BufferedReader`;
    # the same thing happens if you attempt to close() it while that's in progress.
    __slots__ = (
        'stdin',
        'stdout',
        'stderr',
        '_all_greenlets',
    )

    def __init__(self, popen, input_data):
        self.stdin = self.stdout = self.stderr = None
        if popen.stdin: # Even if no data, we need to close
            self.stdin = spawn(self._write_and_close, popen.stdin, input_data)

        # If the timeout parameter is used, and the caller calls back after
        # getting a TimeoutExpired exception, we can wind up with multiple
        # greenlets trying to run and read from and close stdout/stderr.
        # That's bad because it can lead to 'RuntimeError: reentrant call in io.BufferedReader'.
        # We can't just kill the previous greenlets when a timeout happens,
        # though, because we risk losing the output collected by that greenlet
        # (and Python 3, where timeout is an official parameter, explicitly says
        # that no output should be lost in the event of a timeout.) Instead, we're
        # watching for the exception and ignoring it. It's not elegant,
        # but it works
        if popen.stdout:
            self.stdout = spawn(self._read_and_close, popen.stdout)

        if popen.stderr:
            self.stderr = spawn(self._read_and_close, popen.stderr)

        all_greenlets = []
        for g in self.stdin, self.stdout, self.stderr:
            if g is not None:
                all_greenlets.append(g)
        self._all_greenlets = tuple(all_greenlets)

    def __iter__(self):
        return iter(self._all_greenlets)

    def __bool__(self):
        return bool(self._all_greenlets)

    __nonzero__ = __bool__

    def __len__(self):
        return len(self._all_greenlets)

    @staticmethod
    def _write_and_close(fobj, data):
        try:
            if data:
                fobj.write(data)
                if hasattr(fobj, 'flush'):
                    # 3.6 started expecting flush to be called.
                    fobj.flush()
        except (OSError, IOError, BrokenPipeError) as ex:
            # Test cases from the stdlib can raise BrokenPipeError
            # without setting an errno value. This matters because
            # Python 2 doesn't have a BrokenPipeError.
            if isinstance(ex, BrokenPipeError) and ex.errno is None:
                ex.errno = errno.EPIPE
            if ex.errno not in (errno.EPIPE, errno.EINVAL):
                raise
        finally:
            try:
                fobj.close()
            except EnvironmentError:
                pass

    @staticmethod
    def _read_and_close(fobj):
        try:
            return fobj.read()
        finally:
            try:
                fobj.close()
            except EnvironmentError:
                pass


class Popen(object):
    """
    The underlying process creation and management in this module is
    handled by the Popen class. It offers a lot of flexibility so that
    developers are able to handle the less common cases not covered by
    the convenience functions.

    .. seealso:: :class:`subprocess.Popen`
       This class should have the same interface as the standard library class.

    .. caution::

       The default values of some arguments, notably ``buffering``, differ
       between Python 2 and Python 3. For the most consistent behaviour across
       versions, it's best to explicitly pass the desired values.

    .. caution::

       On Python 2, the ``read`` method of the ``stdout`` and ``stderr`` attributes
       will not be buffered unless buffering is explicitly requested (e.g., `bufsize=-1`).
       This is different than the ``read`` method of the standard library attributes,
       which will buffer internally even if no buffering has been requested. This
       matches the Python 3 behaviour. For portability, please explicitly request
       buffering if you want ``read(n)`` to return all ``n`` bytes, making more than
       one system call if needed. See `issue 1701 <https://github.com/gevent/gevent/issues/1701>`_
       for more context.

    .. versionchanged:: 1.2a1
       Instances can now be used as context managers under Python 2.7. Previously
       this was restricted to Python 3.

    .. versionchanged:: 1.2a1
       Instances now save the ``args`` attribute under Python 2.7. Previously this was
       restricted to Python 3.

    .. versionchanged:: 1.2b1
        Add the ``encoding`` and ``errors`` parameters for Python 3.

    .. versionchanged:: 1.3a1
       Accept "path-like" objects for the *cwd* parameter on all platforms.
       This was added to Python 3.6. Previously with gevent, it only worked
       on POSIX platforms on 3.6.

    .. versionchanged:: 1.3a1
       Add the ``text`` argument as a synonym for ``universal_newlines``,
       as added on Python 3.7.

    .. versionchanged:: 1.3a2
       Allow the same keyword arguments under Python 2 as Python 3:
       ``pass_fds``, ``start_new_session``, ``restore_signals``, ``encoding``
       and ``errors``. Under Python 2, ``encoding`` and ``errors`` are ignored
       because native handling of universal newlines is used.

    .. versionchanged:: 1.3a2
       Under Python 2, ``restore_signals`` defaults to ``False``. Previously it
       defaulted to ``True``, the same as it did in Python 3.

    .. versionchanged:: 20.6.0
       Add the *group*, *extra_groups*, *user*, and *umask* arguments. These
       were added to Python 3.9, but are available in any gevent version, provided
       the underlying platform support is present.

    .. versionchanged:: 20.12.0
       On Python 2 only, if unbuffered binary communication is requested,
       the ``stdin`` attribute of this object will have a ``write`` method that
       actually performs internal buffering and looping, similar to the standard library.
       It guarantees to write all the data given to it in a single call (but internally
       it may make many system calls and/or trips around the event loop to accomplish this).
       See :issue:`1711`.

    .. versionchanged:: 21.12.0
       Added the ``pipesize`` argument for compatibility with Python 3.10.
       This is ignored on all platforms.

    .. versionchanged:: 22.08.0
       Added the ``process_group`` and ``check`` arguments for compatibility with
       Python 3.11.
    """

    if GenericAlias is not None:
        # 3.9, annoying typing is creeping everywhere.
        __class_getitem__ = classmethod(GenericAlias)

    # The value returned from communicate() when there was nothing to read.
    # Changes if we're in text mode or universal newlines mode.
    _communicate_empty_value = b''

    def __init__(self, args,
                 bufsize=-1 if PY3 else 0,
                 executable=None,
                 stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=_PLATFORM_DEFAULT_CLOSE_FDS, shell=False,
                 cwd=None, env=None, universal_newlines=None,
                 startupinfo=None, creationflags=0,
                 restore_signals=PY3, start_new_session=False,
                 pass_fds=(),
                 # Added in 3.6. These are kept as ivars
                 encoding=None, errors=None,
                 # Added in 3.7. Not an ivar directly.
                 text=None,
                 # Added in 3.9
                 group=None, extra_groups=None, user=None,
                 umask=-1,
                 # Added in 3.10, but ignored.
                 pipesize=-1,
                 # Added in 3.11
                 process_group=None,
                 # gevent additions
                 threadpool=None):

        self.encoding = encoding
        self.errors = errors

        hub = get_hub()

        if bufsize is None:
            # Python 2 doesn't allow None at all, but Python 3 treats
            # it the same as the default. We do as well.
            bufsize = -1 if PY3 else 0
        if not isinstance(bufsize, integer_types):
            raise TypeError("bufsize must be an integer")

        if mswindows:
            if preexec_fn is not None:
                raise ValueError("preexec_fn is not supported on Windows "
                                 "platforms")
            if PY37:
                if close_fds is _PLATFORM_DEFAULT_CLOSE_FDS:
                    close_fds = True
            else:
                any_stdio_set = (stdin is not None or stdout is not None or
                                 stderr is not None)
                if close_fds is _PLATFORM_DEFAULT_CLOSE_FDS:
                    if any_stdio_set:
                        close_fds = False
                    else:
                        close_fds = True
                elif close_fds and any_stdio_set:
                    raise ValueError("close_fds is not supported on Windows "
                                     "platforms if you redirect stdin/stdout/stderr")
            if threadpool is None:
                threadpool = hub.threadpool
            self.threadpool = threadpool
            self._waiting = False
        else:
            # POSIX
            if close_fds is _PLATFORM_DEFAULT_CLOSE_FDS:
                # close_fds has different defaults on Py3/Py2
                if PY3: # pylint: disable=simplifiable-if-statement
                    close_fds = True
                else:
                    close_fds = False

            if pass_fds and not close_fds:
                import warnings
                warnings.warn("pass_fds overriding close_fds.", RuntimeWarning)
                close_fds = True
            if startupinfo is not None:
                raise ValueError("startupinfo is only supported on Windows "
                                 "platforms")
            if creationflags != 0:
                raise ValueError("creationflags is only supported on Windows "
                                 "platforms")
            assert threadpool is None
            self._loop = hub.loop

        # Validate the combinations of text and universal_newlines
        if (text is not None and universal_newlines is not None
                and bool(universal_newlines) != bool(text)):
            # pylint:disable=undefined-variable
            raise SubprocessError('Cannot disambiguate when both text '
                                  'and universal_newlines are supplied but '
                                  'different. Pass one or the other.')

        self.args = args # Previously this was Py3 only.
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.pid = None
        self.returncode = None
        self.universal_newlines = universal_newlines
        self.result = AsyncResult()

        # Input and output objects. The general principle is like
        # this:
        #
        # Parent                   Child
        # ------                   -----
        # p2cwrite   ---stdin--->  p2cread
        # c2pread    <--stdout---  c2pwrite
        # errread    <--stderr---  errwrite
        #
        # On POSIX, the child objects are file descriptors.  On
        # Windows, these are Windows file handles.  The parent objects
        # are file descriptors on both platforms.  The parent objects
        # are -1 when not using PIPEs. The child objects are -1
        # when not redirecting.

        (p2cread, p2cwrite,
         c2pread, c2pwrite,
         errread, errwrite) = self._get_handles(stdin, stdout, stderr)

        # We wrap OS handles *before* launching the child, otherwise a
        # quickly terminating child could make our fds unwrappable
        # (see #8458).
        if mswindows:
            if p2cwrite != -1:
                p2cwrite = msvcrt.open_osfhandle(p2cwrite.Detach(), 0)
            if c2pread != -1:
                c2pread = msvcrt.open_osfhandle(c2pread.Detach(), 0)
            if errread != -1:
                errread = msvcrt.open_osfhandle(errread.Detach(), 0)

        text_mode = PY3 and (self.encoding or self.errors or universal_newlines or text)
        if text_mode or universal_newlines:
            # Always a native str in universal_newlines mode, even when that
            # str type is bytes. Additionally, text_mode is only true under
            # Python 3, so it's actually a unicode str
            self._communicate_empty_value = ''

        uid, gid, gids = self.__handle_uids(user, group, extra_groups)

        if p2cwrite != -1:
            if PY3 and text_mode:
                # Under Python 3, if we left on the 'b' we'd get different results
                # depending on whether we used FileObjectPosix or FileObjectThread
                self.stdin = FileObject(p2cwrite, 'w', bufsize,
                                        encoding=self.encoding, errors=self.errors)
            else:
                self.stdin = FileObject(p2cwrite, 'wb', bufsize)

        if c2pread != -1:
            if universal_newlines or text_mode:
                if PY3:
                    self.stdout = FileObject(c2pread, 'r', bufsize,
                                             encoding=self.encoding, errors=self.errors)
                    # NOTE: Universal Newlines are broken on Windows/Py3, at least
                    # in some cases. This is true in the stdlib subprocess module
                    # as well; the following line would fix the test cases in
                    # test__subprocess.py that depend on python_universal_newlines,
                    # but would be inconsistent with the stdlib:
                else:
                    self.stdout = FileObject(c2pread, 'rU', bufsize)
            else:
                self.stdout = FileObject(c2pread, 'rb', bufsize)
        if errread != -1:
            if universal_newlines or text_mode:
                if PY3:
                    self.stderr = FileObject(errread, 'r', bufsize,
                                             encoding=encoding, errors=errors)
                else:
                    self.stderr = FileObject(errread, 'rU', bufsize)
            else:
                self.stderr = FileObject(errread, 'rb', bufsize)

        self._closed_child_pipe_fds = False
        # Convert here for the sake of all platforms. os.chdir accepts
        # path-like objects natively under 3.6, but CreateProcess
        # doesn't.
        cwd = fsdecode(cwd) if cwd is not None else None
        try:
            self._execute_child(args, executable, preexec_fn, close_fds,
                                pass_fds, cwd, env, universal_newlines,
                                startupinfo, creationflags, shell,
                                p2cread, p2cwrite,
                                c2pread, c2pwrite,
                                errread, errwrite,
                                restore_signals,
                                gid, gids, uid, umask,
                                start_new_session, process_group)
        except:
            # Cleanup if the child failed starting.
            # (gevent: New in python3, but reported as gevent bug in #347.
            # Note that under Py2, any error raised below will replace the
            # original error so we have to use reraise)
            if not PY3:
                exc_info = sys.exc_info()
            for f in filter(None, (self.stdin, self.stdout, self.stderr)):
                try:
                    f.close()
                except (OSError, IOError):
                    pass  # Ignore EBADF or other errors.

            if not self._closed_child_pipe_fds:
                to_close = []
                if stdin == PIPE:
                    to_close.append(p2cread)
                if stdout == PIPE:
                    to_close.append(c2pwrite)
                if stderr == PIPE:
                    to_close.append(errwrite)
                if hasattr(self, '_devnull'):
                    to_close.append(self._devnull)
                for fd in to_close:
                    try:
                        os.close(fd)
                    except (OSError, IOError):
                        pass
            if not PY3:
                try:
                    reraise(*exc_info)
                finally:
                    del exc_info
            raise

    def __handle_uids(self, user, group, extra_groups):
        gid = None
        if group is not None:
            if not hasattr(os, 'setregid'):
                raise ValueError("The 'group' parameter is not supported on the "
                                 "current platform")

            if isinstance(group, str):
                if grp is None:
                    raise ValueError("The group parameter cannot be a string "
                                     "on systems without the grp module")

                gid = grp.getgrnam(group).gr_gid
            elif isinstance(group, int):
                gid = group
            else:
                raise TypeError("Group must be a string or an integer, not {}"
                                .format(type(group)))

            if gid < 0:
                raise ValueError("Group ID cannot be negative, got %s" % gid)

        gids = None
        if extra_groups is not None:
            if not hasattr(os, 'setgroups'):
                raise ValueError("The 'extra_groups' parameter is not "
                                 "supported on the current platform")

            if isinstance(extra_groups, str):
                raise ValueError("Groups must be a list, not a string")

            gids = []
            for extra_group in extra_groups:
                if isinstance(extra_group, str):
                    if grp is None:
                        raise ValueError("Items in extra_groups cannot be "
                                         "strings on systems without the "
                                         "grp module")

                    gids.append(grp.getgrnam(extra_group).gr_gid)
                elif isinstance(extra_group, int):
                    if extra_group >= 2**64:
                        # This check is implicit in the C version of _Py_Gid_Converter.
                        #
                        # We actually need access to the C type ``gid_t`` to get
                        # its actual length. This just makes the test that was added
                        # for the bug pass. That's OK though, if we guess too big here,
                        # we should get an OverflowError from the setgroups()
                        # call we make. The only difference is the type of exception.
                        #
                        # See https://bugs.python.org/issue42655
                        raise ValueError("Item in extra_groups is too large")
                    gids.append(extra_group)
                else:
                    raise TypeError("Items in extra_groups must be a string "
                                    "or integer, not {}"
                                    .format(type(extra_group)))

            # make sure that the gids are all positive here so we can do less
            # checking in the C code
            for gid_check in gids:
                if gid_check < 0:
                    raise ValueError("Group ID cannot be negative, got %s" % (gid_check,))

        uid = None
        if user is not None:
            if not hasattr(os, 'setreuid'):
                raise ValueError("The 'user' parameter is not supported on "
                                 "the current platform")

            if isinstance(user, str):
                if pwd is None:
                    raise ValueError("The user parameter cannot be a string "
                                     "on systems without the pwd module")

                uid = pwd.getpwnam(user).pw_uid
            elif isinstance(user, int):
                uid = user
            else:
                raise TypeError("User must be a string or an integer")

            if uid < 0:
                raise ValueError("User ID cannot be negative, got %s" % (uid,))

        return uid, gid, gids

    def __repr__(self):
        return '<%s at 0x%x pid=%r returncode=%r>' % (self.__class__.__name__, id(self), self.pid, self.returncode)

    def _on_child(self, watcher):
        watcher.stop()
        status = watcher.rstatus
        if os.WIFSIGNALED(status):
            self.returncode = -os.WTERMSIG(status)
        else:
            self.returncode = os.WEXITSTATUS(status)
        self.result.set(self.returncode)

    def _get_devnull(self):
        if not hasattr(self, '_devnull'):
            self._devnull = os.open(os.devnull, os.O_RDWR)
        return self._devnull

    _communicating_greenlets = None

    def communicate(self, input=None, timeout=None):
        """
        Interact with process and return its output and error.

        - Send *input* data to stdin.
        - Read data from stdout and stderr, until end-of-file is reached.
        - Wait for process to terminate.

        The optional *input* argument should be a
        string to be sent to the child process, or None, if no data
        should be sent to the child.

        communicate() returns a tuple (stdout, stderr).

        :keyword timeout: Under Python 2, this is a gevent extension; if
           given and it expires, we will raise :exc:`TimeoutExpired`, which
           extends :exc:`gevent.timeout.Timeout` (note that this only extends :exc:`BaseException`,
           *not* :exc:`Exception`)
           Under Python 3, this raises the standard :exc:`TimeoutExpired` exception.

        .. versionchanged:: 1.1a2
           Under Python 2, if the *timeout* elapses, raise the :exc:`gevent.timeout.Timeout`
           exception. Previously, we silently returned.
        .. versionchanged:: 1.1b5
           Honor a *timeout* even if there's no way to communicate with the child
           (stdin, stdout, and stderr are not pipes).
        """
        if self._communicating_greenlets is None:
            self._communicating_greenlets = _CommunicatingGreenlets(self, input)
        greenlets = self._communicating_greenlets

        # If we were given stdin=stdout=stderr=None, we have no way to
        # communicate with the child, and thus no greenlets to wait
        # on. This is a nonsense case, but it comes up in the test
        # case for Python 3.5 (test_subprocess.py
        # RunFuncTestCase.test_timeout). Instead, we go directly to
        # self.wait
        if not greenlets and timeout is not None:
            self.wait(timeout=timeout, _raise_exc=True)

        done = joinall(greenlets, timeout=timeout)
        # Allow finished greenlets, if any, to raise. This takes priority over
        # the timeout exception.
        for greenlet in done:
            greenlet.get()
        if timeout is not None and len(done) != len(self._communicating_greenlets):
            raise TimeoutExpired(self.args, timeout)

        # Close only after we're sure that everything is done
        # (there was no timeout, or there was, but everything finished).
        # There should be no greenlets still running, even from a prior
        # attempt. If there are, then this can raise RuntimeError: 'reentrant call'.
        # So we ensure that previous greenlets are dead.
        for pipe in (self.stdout, self.stderr):
            if pipe:
                try:
                    pipe.close()
                except RuntimeError:
                    pass

        self.wait()

        return (None if greenlets.stdout is None else greenlets.stdout.get(),
                None if greenlets.stderr is None else greenlets.stderr.get())

    def poll(self):
        """Check if child process has terminated. Set and return :attr:`returncode` attribute."""
        return self._internal_poll()

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        try:  # Flushing a BufferedWriter may raise an error
            if self.stdin:
                self.stdin.close()
        finally:
            # Wait for the process to terminate, to avoid zombies.
            # JAM: gevent: If the process never terminates, this
            # blocks forever.
            self.wait()

    def _gevent_result_wait(self, timeout=None, raise_exc=PY3):
        result = self.result.wait(timeout=timeout)
        if raise_exc and timeout is not None and not self.result.ready():
            raise TimeoutExpired(self.args, timeout)
        return result


    if mswindows:
        #
        # Windows methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            # pylint:disable=undefined-variable
            if stdin is None and stdout is None and stderr is None:
                return (-1, -1, -1, -1, -1, -1)

            p2cread, p2cwrite = -1, -1
            c2pread, c2pwrite = -1, -1
            errread, errwrite = -1, -1

            try:
                DEVNULL
            except NameError:
                _devnull = object()
            else:
                _devnull = DEVNULL

            if stdin is None:
                p2cread = GetStdHandle(STD_INPUT_HANDLE)
                if p2cread is None:
                    p2cread, _ = CreatePipe(None, 0)
                    if PY3:
                        p2cread = Handle(p2cread)
                        _winapi.CloseHandle(_)
            elif stdin == PIPE:
                p2cread, p2cwrite = CreatePipe(None, 0)
                if PY3:
                    p2cread, p2cwrite = Handle(p2cread), Handle(p2cwrite)
            elif stdin == _devnull:
                p2cread = msvcrt.get_osfhandle(self._get_devnull())
            elif isinstance(stdin, int):
                p2cread = msvcrt.get_osfhandle(stdin)
            else:
                # Assuming file-like object
                p2cread = msvcrt.get_osfhandle(stdin.fileno())
            p2cread = self._make_inheritable(p2cread)

            if stdout is None:
                c2pwrite = GetStdHandle(STD_OUTPUT_HANDLE)
                if c2pwrite is None:
                    _, c2pwrite = CreatePipe(None, 0)
                    if PY3:
                        c2pwrite = Handle(c2pwrite)
                        _winapi.CloseHandle(_)
            elif stdout == PIPE:
                c2pread, c2pwrite = CreatePipe(None, 0)
                if PY3:
                    c2pread, c2pwrite = Handle(c2pread), Handle(c2pwrite)
            elif stdout == _devnull:
                c2pwrite = msvcrt.get_osfhandle(self._get_devnull())
            elif isinstance(stdout, int):
                c2pwrite = msvcrt.get_osfhandle(stdout)
            else:
                # Assuming file-like object
                c2pwrite = msvcrt.get_osfhandle(stdout.fileno())
            c2pwrite = self._make_inheritable(c2pwrite)

            if stderr is None:
                errwrite = GetStdHandle(STD_ERROR_HANDLE)
                if errwrite is None:
                    _, errwrite = CreatePipe(None, 0)
                    if PY3:
                        errwrite = Handle(errwrite)
                        _winapi.CloseHandle(_)
            elif stderr == PIPE:
                errread, errwrite = CreatePipe(None, 0)
                if PY3:
                    errread, errwrite = Handle(errread), Handle(errwrite)
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif stderr == _devnull:
                errwrite = msvcrt.get_osfhandle(self._get_devnull())
            elif isinstance(stderr, int):
                errwrite = msvcrt.get_osfhandle(stderr)
            else:
                # Assuming file-like object
                errwrite = msvcrt.get_osfhandle(stderr.fileno())
            errwrite = self._make_inheritable(errwrite)

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)

        def _make_inheritable(self, handle):
            """Return a duplicate of handle, which is inheritable"""
            # pylint:disable=undefined-variable
            return DuplicateHandle(GetCurrentProcess(),
                                   handle, GetCurrentProcess(), 0, 1,
                                   DUPLICATE_SAME_ACCESS)

        def _find_w9xpopen(self):
            """Find and return absolute path to w9xpopen.exe"""
            # pylint:disable=undefined-variable
            w9xpopen = os.path.join(os.path.dirname(GetModuleFileName(0)),
                                    "w9xpopen.exe")
            if not os.path.exists(w9xpopen):
                # Eeek - file-not-found - possibly an embedding
                # situation - see if we can locate it in sys.exec_prefix
                w9xpopen = os.path.join(os.path.dirname(sys.exec_prefix),
                                        "w9xpopen.exe")
                if not os.path.exists(w9xpopen):
                    raise RuntimeError("Cannot locate w9xpopen.exe, which is "
                                       "needed for Popen to work with your "
                                       "shell or platform.")
            return w9xpopen


        def _filter_handle_list(self, handle_list):
            """Filter out console handles that can't be used
            in lpAttributeList["handle_list"] and make sure the list
            isn't empty. This also removes duplicate handles."""
            # An handle with it's lowest two bits set might be a special console
            # handle that if passed in lpAttributeList["handle_list"], will
            # cause it to fail.
            # Only works on 3.7+
            return list({handle for handle in handle_list
                         if handle & 0x3 != 0x3
                         or _winapi.GetFileType(handle) !=
                         _winapi.FILE_TYPE_CHAR})


        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           pass_fds, cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite,
                           unused_restore_signals,
                           unused_gid, unused_gids, unused_uid, unused_umask,
                           unused_start_new_session, unused_process_group):
            """Execute program (MS Windows version)"""
            # pylint:disable=undefined-variable
            assert not pass_fds, "pass_fds not supported on Windows."
            if isinstance(args, str):
                pass
            elif isinstance(args, bytes):
                if shell and PY3:
                    raise TypeError('bytes args is not allowed on Windows')
                args = list2cmdline([args])
            elif isinstance(args, PathLike):
                if shell:
                    raise TypeError('path-like args is not allowed when '
                                    'shell is true')
                args = list2cmdline([args])
            else:
                args = list2cmdline(args)

            if executable is not None:
                executable = fsdecode(executable)

            if not isinstance(args, string_types):
                args = list2cmdline(args)

            # Process startup details
            if startupinfo is None:
                startupinfo = STARTUPINFO()
            elif hasattr(startupinfo, 'copy'):
                # bpo-34044: Copy STARTUPINFO since it is modified below,
                # so the caller can reuse it multiple times.
                startupinfo = startupinfo.copy()
            elif hasattr(startupinfo, '_copy'):
                # When the fix was backported to Python 3.7, copy() was
                # made private as _copy.
                startupinfo = startupinfo._copy()

            use_std_handles = -1 not in (p2cread, c2pwrite, errwrite)
            if use_std_handles:
                startupinfo.dwFlags |= STARTF_USESTDHANDLES
                startupinfo.hStdInput = p2cread
                startupinfo.hStdOutput = c2pwrite
                startupinfo.hStdError = errwrite

            if hasattr(startupinfo, 'lpAttributeList'):
                # Support for Python >= 3.7

                attribute_list = startupinfo.lpAttributeList
                have_handle_list = bool(attribute_list and
                                        "handle_list" in attribute_list and
                                        attribute_list["handle_list"])

                # If we were given an handle_list or need to create one
                if have_handle_list or (use_std_handles and close_fds):
                    if attribute_list is None:
                        attribute_list = startupinfo.lpAttributeList = {}
                    handle_list = attribute_list["handle_list"] = \
                        list(attribute_list.get("handle_list", []))

                    if use_std_handles:
                        handle_list += [int(p2cread), int(c2pwrite), int(errwrite)]

                    handle_list[:] = self._filter_handle_list(handle_list)

                    if handle_list:
                        if not close_fds:
                            import warnings
                            warnings.warn("startupinfo.lpAttributeList['handle_list'] "
                                          "overriding close_fds", RuntimeWarning)

                        # When using the handle_list we always request to inherit
                        # handles but the only handles that will be inherited are
                        # the ones in the handle_list
                        close_fds = False

            if shell:
                startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = SW_HIDE
                comspec = os.environ.get("COMSPEC", "cmd.exe")
                args = '{} /c "{}"'.format(comspec, args)
                if GetVersion() >= 0x80000000 or os.path.basename(comspec).lower() == "command.com":
                    # Win9x, or using command.com on NT. We need to
                    # use the w9xpopen intermediate program. For more
                    # information, see KB Q150956
                    # (http://web.archive.org/web/20011105084002/http://support.microsoft.com/support/kb/articles/Q150/9/56.asp)
                    w9xpopen = self._find_w9xpopen()
                    args = '"%s" %s' % (w9xpopen, args)
                    # Not passing CREATE_NEW_CONSOLE has been known to
                    # cause random failures on win9x.  Specifically a
                    # dialog: "Your program accessed mem currently in
                    # use at xxx" and a hopeful warning about the
                    # stability of your system.  Cost is Ctrl+C wont
                    # kill children.
                    creationflags |= CREATE_NEW_CONSOLE

            # PyPy 2.7 7.3.6 is now producing these errors. This
            # happens automatically on Posix platforms, and is built
            # in to the CreateProcess call on CPython 2 & 3. It's not
            # clear why we don't pick it up for free from the
            # CreateProcess call on PyPy. Currently we don't test PyPy3 on Windows,
            # so we don't know for sure if it's built into CreateProcess there.
            if PYPY:
                def _check_nul(s, err_kind=(ValueError if PY3 else TypeError)):
                    if not s:
                        return
                    nul = b'\0' if isinstance(s, bytes) else '\0'
                    if nul in s:
                        # PyPy 2 expects a TypeError; Python 3 raises ValueError always.
                        raise err_kind("argument must be a string without NUL characters")
                def _check_env():
                    if not env:
                        return
                    for k, v in env.items():
                        _check_nul(k)
                        _check_nul(v)
                        if '=' in k:
                            raise ValueError("'=' not allowed in environment keys")

                _check_nul(executable)
                _check_nul(args)
                _check_env()

            # Start the process
            try:
                hp, ht, pid, tid = CreateProcess(executable, args,
                                                 # no special security
                                                 None, None,
                                                 int(not close_fds),
                                                 creationflags,
                                                 env,
                                                 cwd, # fsdecode handled earlier
                                                 startupinfo)
            except IOError as e: # From 2.6 on, pywintypes.error was defined as IOError
                # Translate pywintypes.error to WindowsError, which is
                # a subclass of OSError.  FIXME: We should really
                # translate errno using _sys_errlist (or similar), but
                # how can this be done from Python?
                if PY3:
                    raise # don't remap here
                raise WindowsError(*e.args)
            finally:
                # Child is launched. Close the parent's copy of those pipe
                # handles that only the child should have open.  You need
                # to make sure that no handles to the write end of the
                # output pipe are maintained in this process or else the
                # pipe will not close when the child process exits and the
                # ReadFile will hang.
                def _close(x):
                    if x is not None and x != -1:
                        if hasattr(x, 'Close'):
                            x.Close()
                        else:
                            _winapi.CloseHandle(x)

                _close(p2cread)
                _close(c2pwrite)
                _close(errwrite)
                if hasattr(self, '_devnull'):
                    os.close(self._devnull)

            # Retain the process handle, but close the thread handle
            self._child_created = True
            self._handle = Handle(hp) if not hasattr(hp, 'Close') else hp
            self.pid = pid
            _winapi.CloseHandle(ht) if not hasattr(ht, 'Close') else ht.Close()

        def _internal_poll(self):
            """Check if child process has terminated.  Returns returncode
            attribute.
            """
            # pylint:disable=undefined-variable
            if self.returncode is None:
                if WaitForSingleObject(self._handle, 0) == WAIT_OBJECT_0:
                    self.returncode = GetExitCodeProcess(self._handle)
                    self.result.set(self.returncode)
            return self.returncode

        def rawlink(self, callback):
            if not self.result.ready() and not self._waiting:
                self._waiting = True
                Greenlet.spawn(self._wait)
            self.result.rawlink(linkproxy(callback, self))
            # XXX unlink

        def _blocking_wait(self):
            # pylint:disable=undefined-variable
            WaitForSingleObject(self._handle, INFINITE)
            self.returncode = GetExitCodeProcess(self._handle)
            return self.returncode

        def _wait(self):
            self.threadpool.spawn(self._blocking_wait).rawlink(self.result)

        def wait(self, timeout=None, _raise_exc=PY3):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            if self.returncode is None:
                if not self._waiting:
                    self._waiting = True
                    self._wait()
            return self._gevent_result_wait(timeout, _raise_exc)

        def send_signal(self, sig):
            """Send a signal to the process
            """
            if sig == signal.SIGTERM:
                self.terminate()
            elif sig == signal.CTRL_C_EVENT:
                os.kill(self.pid, signal.CTRL_C_EVENT)
            elif sig == signal.CTRL_BREAK_EVENT:
                os.kill(self.pid, signal.CTRL_BREAK_EVENT)
            else:
                raise ValueError("Unsupported signal: {}".format(sig))

        def terminate(self):
            """Terminates the process
            """
            # pylint:disable=undefined-variable
            # Don't terminate a process that we know has already died.
            if self.returncode is not None:
                return
            try:
                TerminateProcess(self._handle, 1)
            except OSError as e:
                # ERROR_ACCESS_DENIED (winerror 5) is received when the
                # process already died.
                if e.winerror != 5:
                    raise
                rc = GetExitCodeProcess(self._handle)
                if rc == STILL_ACTIVE:
                    raise
                self.returncode = rc
                self.result.set(self.returncode)

        kill = terminate

    else:
        #
        # POSIX methods
        #

        def rawlink(self, callback):
            # Not public documented, part of the link protocol
            self.result.rawlink(linkproxy(callback, self))
        # XXX unlink

        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tuple with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            p2cread, p2cwrite = -1, -1
            c2pread, c2pwrite = -1, -1
            errread, errwrite = -1, -1

            try:
                DEVNULL
            except NameError:
                _devnull = object()
            else:
                _devnull = DEVNULL

            if stdin is None:
                pass
            elif stdin == PIPE:
                p2cread, p2cwrite = self.pipe_cloexec()
            elif stdin == _devnull:
                p2cread = self._get_devnull()
            elif isinstance(stdin, int):
                p2cread = stdin
            else:
                # Assuming file-like object
                p2cread = stdin.fileno()

            if stdout is None:
                pass
            elif stdout == PIPE:
                c2pread, c2pwrite = self.pipe_cloexec()
            elif stdout == _devnull:
                c2pwrite = self._get_devnull()
            elif isinstance(stdout, int):
                c2pwrite = stdout
            else:
                # Assuming file-like object
                c2pwrite = stdout.fileno()

            if stderr is None:
                pass
            elif stderr == PIPE:
                errread, errwrite = self.pipe_cloexec()
            elif stderr == STDOUT: # pylint:disable=undefined-variable
                if c2pwrite != -1:
                    errwrite = c2pwrite
                else: # child's stdout is not set, use parent's stdout
                    errwrite = sys.__stdout__.fileno()
            elif stderr == _devnull:
                errwrite = self._get_devnull()
            elif isinstance(stderr, int):
                errwrite = stderr
            else:
                # Assuming file-like object
                errwrite = stderr.fileno()

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)

        def _set_cloexec_flag(self, fd, cloexec=True):
            try:
                cloexec_flag = fcntl.FD_CLOEXEC
            except AttributeError:
                cloexec_flag = 1

            old = fcntl.fcntl(fd, fcntl.F_GETFD)
            if cloexec:
                fcntl.fcntl(fd, fcntl.F_SETFD, old | cloexec_flag)
            else:
                fcntl.fcntl(fd, fcntl.F_SETFD, old & ~cloexec_flag)

        def _remove_nonblock_flag(self, fd):
            flags = fcntl.fcntl(fd, fcntl.F_GETFL) & (~os.O_NONBLOCK)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)

        def pipe_cloexec(self):
            """Create a pipe with FDs set CLOEXEC."""
            # Pipes' FDs are set CLOEXEC by default because we don't want them
            # to be inherited by other subprocesses: the CLOEXEC flag is removed
            # from the child's FDs by _dup2(), between fork() and exec().
            # This is not atomic: we would need the pipe2() syscall for that.
            r, w = os.pipe()
            self._set_cloexec_flag(r)
            self._set_cloexec_flag(w)
            return r, w

        _POSSIBLE_FD_DIRS = (
            '/proc/self/fd', # Linux
            '/dev/fd', # BSD, including macOS
        )

        @classmethod
        def _close_fds(cls, keep, errpipe_write):
            # From the C code:
            # errpipe_write is part of keep. It must be closed at
            # exec(), but kept open in the child process until exec() is
            # called.
            for path in cls._POSSIBLE_FD_DIRS:
                if os.path.isdir(path):
                    return cls._close_fds_from_path(path, keep, errpipe_write)
            return cls._close_fds_brute_force(keep, errpipe_write)

        @classmethod
        def _close_fds_from_path(cls, path, keep, errpipe_write):
            # path names a directory whose only entries have
            # names that are ascii strings of integers in base10,
            # corresponding to the fds the current process has open
            try:
                fds = [int(fname) for fname in os.listdir(path)]
            except (ValueError, OSError):
                cls._close_fds_brute_force(keep, errpipe_write)
            else:
                for i in keep:
                    if i == errpipe_write:
                        continue
                    _set_inheritable(i, True)

                for fd in fds:
                    if fd in keep or fd < 3:
                        continue
                    try:
                        os.close(fd)
                    except:
                        pass

        @classmethod
        def _close_fds_brute_force(cls, keep, errpipe_write):
            # `keep` is a set of fds, so we
            # use os.closerange from 3 to min(keep)
            # and then from max(keep + 1) to MAXFD and
            # loop through filling in the gaps.

            # Under new python versions, we need to explicitly set
            # passed fds to be inheritable or they will go away on exec

            # XXX: Bug: We implicitly rely on errpipe_write being the largest open
            # FD so that we don't change its cloexec flag.

            assert hasattr(os, 'closerange') # Added in 2.7
            keep = sorted(keep)
            min_keep = min(keep)
            max_keep = max(keep)
            os.closerange(3, min_keep)
            os.closerange(max_keep + 1, MAXFD)

            for i in xrange(min_keep, max_keep):
                if i in keep:
                    _set_inheritable(i, True)
                    continue

                try:
                    os.close(i)
                except:
                    pass

        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           pass_fds, cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite,
                           restore_signals,
                           gid, gids, uid, umask,
                           start_new_session, process_group):
            """Execute program (POSIX version)"""

            if PY3 and isinstance(args, (str, bytes)):
                args = [args]
            elif not PY3 and isinstance(args, string_types):
                args = [args]
            elif isinstance(args, PathLike):
                if shell:
                    raise TypeError('path-like args is not allowed when '
                                    'shell is true')
                args = [fsencode(args)] # os.PathLike -> [str]
            else:
                args = list(args)

            if shell:
                # On Android the default shell is at '/system/bin/sh'.
                unix_shell = (
                    '/system/bin/sh' if hasattr(sys, 'getandroidapilevel') else '/bin/sh'
                )
                args = [unix_shell, "-c"] + args
                if executable:
                    args[0] = executable

            if executable is None:
                executable = args[0]

            self._loop.install_sigchld()

            # For transferring possible exec failure from child to parent
            # The first char specifies the exception type: 0 means
            # OSError, 1 means some other error.
            errpipe_read, errpipe_write = self.pipe_cloexec()
            # errpipe_write must not be in the standard io 0, 1, or 2 fd range.
            low_fds_to_close = []
            while errpipe_write < 3:
                low_fds_to_close.append(errpipe_write)
                errpipe_write = os.dup(errpipe_write)
            for low_fd in low_fds_to_close:
                os.close(low_fd)
            try:
                try:
                    gc_was_enabled = gc.isenabled()
                    # Disable gc to avoid bug where gc -> file_dealloc ->
                    # write to stderr -> hang.  http://bugs.python.org/issue1336
                    gc.disable()
                    try:
                        self.pid = fork_and_watch(self._on_child, self._loop, True, fork)
                    except:
                        if gc_was_enabled:
                            gc.enable()
                        raise
                    if self.pid == 0:
                        # Child

                        # XXX: Technically we're doing a lot of stuff here that
                        # may not be safe to do before a exec(), depending on the OS.
                        # CPython 3 goes to great lengths to precompute a lot
                        # of this info before the fork and pass it all to C functions that
                        # try hard not to call things like malloc(). (Of course,
                        # CPython 2 pretty much did what we're doing.)
                        try:
                            # Close parent's pipe ends
                            if p2cwrite != -1:
                                os.close(p2cwrite)
                            if c2pread != -1:
                                os.close(c2pread)
                            if errread != -1:
                                os.close(errread)
                            os.close(errpipe_read)

                            # When duping fds, if there arises a situation
                            # where one of the fds is either 0, 1 or 2, it
                            # is possible that it is overwritten (#12607).
                            if c2pwrite == 0:
                                c2pwrite = os.dup(c2pwrite)
                                _set_inheritable(c2pwrite, False)
                            while errwrite in (0, 1):
                                errwrite = os.dup(errwrite)
                                _set_inheritable(errwrite, False)

                            # Dup fds for child
                            def _dup2(existing, desired):
                                # dup2() removes the CLOEXEC flag but
                                # we must do it ourselves if dup2()
                                # would be a no-op (issue #10806).
                                if existing == desired:
                                    self._set_cloexec_flag(existing, False)
                                elif existing != -1:
                                    os.dup2(existing, desired)
                                try:
                                    self._remove_nonblock_flag(desired)
                                except OSError:
                                    # Ignore EBADF, it may not actually be
                                    # open yet.
                                    # Tested beginning in 3.7.0b3 test_subprocess.py
                                    pass
                            _dup2(p2cread, 0)
                            _dup2(c2pwrite, 1)
                            _dup2(errwrite, 2)

                            # Close pipe fds.  Make sure we don't close the
                            # same fd more than once, or standard fds.
                            if not PY3:
                                closed = set([None])
                                for fd in [p2cread, c2pwrite, errwrite]:
                                    if fd not in closed and fd > 2:
                                        os.close(fd)
                                        closed.add(fd)

                            # Python 3 (with a working set_inheritable):
                            # We no longer manually close p2cread,
	                        # c2pwrite, and errwrite here as
	                        # _close_open_fds takes care when it is
	                        # not already non-inheritable.

                            if cwd is not None:
                                try:
                                    os.chdir(cwd)
                                except OSError as e:
                                    e._failed_chdir = True
                                    raise

                            # Python 3.9
                            if umask >= 0:
                                os.umask(umask)
                            # XXX: CPython does _Py_RestoreSignals here.
                            # Then setsid() based on ???
                            if gids:
                                os.setgroups(gids)
                            if gid:
                                os.setregid(gid, gid)
                            if uid:
                                os.setreuid(uid, uid)
                            if process_group is not None:
                                os.setpgid(0, process_group)
                            if preexec_fn:
                                preexec_fn()

                            # Close all other fds, if asked for. This must be done
                            # after preexec_fn runs.
                            if close_fds:
                                fds_to_keep = set(pass_fds)
                                fds_to_keep.add(errpipe_write)
                                self._close_fds(fds_to_keep, errpipe_write)

                            if restore_signals:
                                # restore the documented signals back to sig_dfl;
                                # not all will be defined on every platform
                                for sig in 'SIGPIPE', 'SIGXFZ', 'SIGXFSZ':
                                    sig = getattr(signal, sig, None)
                                    if sig is not None:
                                        signal.signal(sig, signal.SIG_DFL)

                            if start_new_session:
                                os.setsid()

                            if env is None:
                                os.execvp(executable, args)
                            else:
                                if PY3:
                                    # Python 3.6 started testing for
                                    # bytes values in the env; it also
                                    # started encoding strs using
                                    # fsencode and using a lower-level
                                    # API that takes a list of keys
                                    # and values. We don't have access
                                    # to that API, so we go the reverse direction.
                                    env = {os.fsdecode(k) if isinstance(k, bytes) else k:
                                           os.fsdecode(v) if isinstance(v, bytes) else v
                                           for k, v in env.items()}
                                os.execvpe(executable, args, env)

                        except:
                            exc_type, exc_value, tb = sys.exc_info()
                            # Save the traceback and attach it to the exception object
                            exc_lines = traceback.format_exception(exc_type,
                                                                   exc_value,
                                                                   tb)
                            exc_value.child_traceback = ''.join(exc_lines)
                            os.write(errpipe_write, pickle.dumps(exc_value))

                        finally:
                            # Make sure that the process exits no matter what.
                            # The return code does not matter much as it won't be
                            # reported to the application
                            os._exit(1)

                    # Parent
                    self._child_created = True
                    if gc_was_enabled:
                        gc.enable()
                finally:
                    # be sure the FD is closed no matter what
                    os.close(errpipe_write)

                # self._devnull is not always defined.
                devnull_fd = getattr(self, '_devnull', None)
                if p2cread != -1 and p2cwrite != -1 and p2cread != devnull_fd:
                    os.close(p2cread)
                if c2pwrite != -1 and c2pread != -1 and c2pwrite != devnull_fd:
                    os.close(c2pwrite)
                if errwrite != -1 and errread != -1 and errwrite != devnull_fd:
                    os.close(errwrite)
                if devnull_fd is not None:
                    os.close(devnull_fd)
                # Prevent a double close of these fds from __init__ on error.
                self._closed_child_pipe_fds = True

                # Wait for exec to fail or succeed; possibly raising exception
                errpipe_read = FileObject(errpipe_read, 'rb')
                data = errpipe_read.read()
            finally:
                try:
                    if hasattr(errpipe_read, 'close'):
                        errpipe_read.close()
                    else:
                        os.close(errpipe_read)
                except OSError:
                    # Especially on PyPy, we sometimes see the above
                    # `os.close(errpipe_read)` raise an OSError.
                    # It's not entirely clear why, but it happens in
                    # InterprocessSignalTests.test_main sometimes, which must mean
                    # we have some sort of race condition.
                    pass
                finally:
                    errpipe_read = -1

            if data != b"":
                self.wait()
                child_exception = pickle.loads(data)
                for fd in (p2cwrite, c2pread, errread):
                    if fd is not None and fd != -1:
                        os.close(fd)
                if isinstance(child_exception, OSError):
                    child_exception.filename = executable
                    if hasattr(child_exception, '_failed_chdir'):
                        child_exception.filename = cwd
                raise child_exception

        def _handle_exitstatus(self, sts, _WIFSIGNALED=os.WIFSIGNALED,
                               _WTERMSIG=os.WTERMSIG, _WIFEXITED=os.WIFEXITED,
                               _WEXITSTATUS=os.WEXITSTATUS, _WIFSTOPPED=os.WIFSTOPPED,
                               _WSTOPSIG=os.WSTOPSIG):
            # This method is called (indirectly) by __del__, so it cannot
            # refer to anything outside of its local scope.
            # (gevent: We don't have a __del__, that's in the CPython implementation.)
            if _WIFSIGNALED(sts):
                self.returncode = -_WTERMSIG(sts)
            elif _WIFEXITED(sts):
                self.returncode = _WEXITSTATUS(sts)
            elif _WIFSTOPPED(sts):
                self.returncode = -_WSTOPSIG(sts)
            else:
                # Should never happen
                raise RuntimeError("Unknown child exit status!")

        def _internal_poll(self):
            """Check if child process has terminated.  Returns returncode
            attribute.
            """
            if self.returncode is None:
                if get_hub() is not getcurrent():
                    sig_pending = getattr(self._loop, 'sig_pending', True)
                    if sig_pending:
                        sleep(0.00001)
            return self.returncode

        def wait(self, timeout=None, _raise_exc=PY3):
            """
            Wait for child process to terminate.  Returns :attr:`returncode`
            attribute.

            :keyword timeout: The floating point number of seconds to
                wait. Under Python 2, this is a gevent extension, and
                we simply return if it expires. Under Python 3, if
                this time elapses without finishing the process,
                :exc:`TimeoutExpired` is raised.
            """
            return self._gevent_result_wait(timeout, _raise_exc)

        def send_signal(self, sig):
            """Send a signal to the process
            """
            # Skip signalling a process that we know has already died.
            if self.returncode is None:
                os.kill(self.pid, sig)

        def terminate(self):
            """Terminate the process with SIGTERM
            """
            self.send_signal(signal.SIGTERM)

        def kill(self):
            """Kill the process with SIGKILL
            """
            self.send_signal(signal.SIGKILL)


def _with_stdout_stderr(exc, stderr):
    # Prior to Python 3.5, most exceptions didn't have stdout
    # and stderr attributes and can't take the stderr attribute in their
    # constructor
    exc.stdout = exc.output
    exc.stderr = stderr
    return exc

class CompletedProcess(object):
    """
    A process that has finished running.

    This is returned by run().

    Attributes:
      - args: The list or str args passed to run().
      - returncode: The exit code of the process, negative for signals.
      - stdout: The standard output (None if not captured).
      - stderr: The standard error (None if not captured).

    .. versionadded:: 1.2a1
       This first appeared in Python 3.5 and is available to all
       Python versions in gevent.
    """
    if GenericAlias is not None:
        # Sigh, 3.9 spreading typing stuff all over everything
        __class_getitem__ = classmethod(GenericAlias)

    def __init__(self, args, returncode, stdout=None, stderr=None):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        args = ['args={!r}'.format(self.args),
                'returncode={!r}'.format(self.returncode)]
        if self.stdout is not None:
            args.append('stdout={!r}'.format(self.stdout))
        if self.stderr is not None:
            args.append('stderr={!r}'.format(self.stderr))
        return "{}({})".format(type(self).__name__, ', '.join(args))

    def check_returncode(self):
        """Raise CalledProcessError if the exit code is non-zero."""
        if self.returncode:
            # pylint:disable=undefined-variable
            raise _with_stdout_stderr(CalledProcessError(self.returncode, self.args, self.stdout), self.stderr)


def run(*popenargs, **kwargs):
    """
    run(args, *, stdin=None, input=None, stdout=None, stderr=None, shell=False, timeout=None, check=False) -> CompletedProcess

    Run command with arguments and return a CompletedProcess instance.

    The returned instance will have attributes args, returncode, stdout and
    stderr. By default, stdout and stderr are not captured, and those attributes
    will be None. Pass stdout=PIPE and/or stderr=PIPE in order to capture them.
    If check is True and the exit code was non-zero, it raises a
    CalledProcessError. The CalledProcessError object will have the return code
    in the returncode attribute, and output & stderr attributes if those streams
    were captured.

    If timeout is given, and the process takes too long, a TimeoutExpired
    exception will be raised.

    There is an optional argument "input", allowing you to
    pass a string to the subprocess's stdin.  If you use this argument
    you may not also use the Popen constructor's "stdin" argument, as
    it will be used internally.
    The other arguments are the same as for the Popen constructor.
    If universal_newlines=True is passed, the "input" argument must be a
    string and stdout/stderr in the returned object will be strings rather than
    bytes.

    .. versionadded:: 1.2a1
       This function first appeared in Python 3.5. It is available on all Python
       versions gevent supports.

    .. versionchanged:: 1.3a2
       Add the ``capture_output`` argument from Python 3.7. It automatically sets
       ``stdout`` and ``stderr`` to ``PIPE``. It is an error to pass either
       of those arguments along with ``capture_output``.
    """
    input = kwargs.pop('input', None)
    timeout = kwargs.pop('timeout', None)
    check = kwargs.pop('check', False)
    capture_output = kwargs.pop('capture_output', False)

    if input is not None:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = PIPE

    if capture_output:
        if ('stdout' in kwargs) or ('stderr' in kwargs):
            raise ValueError('stdout and stderr arguments may not be used '
                             'with capture_output.')
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE

    with Popen(*popenargs, **kwargs) as process:
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise _with_stdout_stderr(TimeoutExpired(process.args, timeout, output=stdout), stderr)
        except:
            process.kill()
            process.wait()
            raise
        retcode = process.poll()
        if check and retcode:
            # pylint:disable=undefined-variable
            raise _with_stdout_stderr(CalledProcessError(retcode, process.args, stdout), stderr)

    return CompletedProcess(process.args, retcode, stdout, stderr)

def _gevent_did_monkey_patch(target_module, *_args, **_kwargs):
    # Beginning on 3.8 on Mac, the 'spawn' method became the default
    # start method. That doesn't fire fork watchers and we can't
    # easily patch to make it do so: multiprocessing uses the private
    # c accelerated _subprocess module to implement this. Instead we revert
    # back to using fork.
    from gevent._compat import MAC

    if MAC:
        import multiprocessing
        if hasattr(multiprocessing, 'set_start_method'):
            multiprocessing.set_start_method('fork', force=True)
