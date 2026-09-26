# pylint:disable=missing-docstring,invalid-name,too-many-lines
from __future__ import print_function, absolute_import, division

import collections
import contextlib
import functools
import sys
import os
# At least on 3.6+, importing platform
# imports subprocess, which imports selectors. That
# can expose issues with monkey patching. We don't need it
# though.
# import platform
import re

from .sysinfo import RUNNING_ON_APPVEYOR as APPVEYOR
from .sysinfo import RUNNING_ON_TRAVIS as TRAVIS
from .sysinfo import RESOLVER_NOT_SYSTEM as ARES
from .sysinfo import RESOLVER_ARES
from .sysinfo import RESOLVER_DNSPYTHON
from .sysinfo import RUNNING_ON_CI
from .sysinfo import RUNNING_ON_MUSLLINUX
from .sysinfo import RUN_COVERAGE


from .sysinfo import PYPY
from .sysinfo import PYPY3

from .sysinfo import PY38
from .sysinfo import PY39
from .sysinfo import PY310
from .sysinfo import PY311
from .sysinfo import PY312

from .sysinfo import WIN
from .sysinfo import OSX
from .sysinfo import LINUX

from .sysinfo import LIBUV
from .sysinfo import CFFI_BACKEND

from . import flaky

CPYTHON = not PYPY

# By default, test cases are expected to switch and emit warnings if there was none
# If a test is found in this list, it's expected not to switch.
no_switch_tests = '''test_patched_select.SelectTestCase.test_error_conditions
test_patched_ftplib.*.test_all_errors
test_patched_ftplib.*.test_getwelcome
test_patched_ftplib.*.test_sanitize
test_patched_ftplib.*.test_set_pasv
#test_patched_ftplib.TestIPv6Environment.test_af
test_patched_socket.TestExceptions.testExceptionTree
test_patched_socket.Urllib2FileobjectTest.testClose
test_patched_socket.TestLinuxAbstractNamespace.testLinuxAbstractNamespace
test_patched_socket.TestLinuxAbstractNamespace.testMaxName
test_patched_socket.TestLinuxAbstractNamespace.testNameOverflow
test_patched_socket.FileObjectInterruptedTestCase.*
test_patched_urllib.*
test_patched_asyncore.HelperFunctionTests.*
test_patched_httplib.BasicTest.*
test_patched_httplib.HTTPSTimeoutTest.test_attributes
test_patched_httplib.HeaderTests.*
test_patched_httplib.OfflineTest.*
test_patched_httplib.HTTPSTimeoutTest.test_host_port
test_patched_httplib.SourceAddressTest.testHTTPSConnectionSourceAddress
test_patched_select.SelectTestCase.test_error_conditions
test_patched_smtplib.NonConnectingTests.*
test_patched_urllib2net.OtherNetworkTests.*
test_patched_wsgiref.*
test_patched_subprocess.HelperFunctionTests.*
'''

ignore_switch_tests = '''
test_patched_socket.GeneralModuleTests.*
test_patched_httpservers.BaseHTTPRequestHandlerTestCase.*
test_patched_queue.*
test_patched_signal.SiginterruptTest.*
test_patched_urllib2.*
test_patched_ssl.*
test_patched_signal.BasicSignalTests.*
test_patched_threading_local.*
test_patched_threading.*
'''


def make_re(tests):
    tests = [x.strip().replace(r'\.', r'\\.').replace('*', '.*?')
             for x in tests.split('\n') if x.strip()]
    return re.compile('^%s$' % '|'.join(tests))


no_switch_tests = make_re(no_switch_tests)
ignore_switch_tests = make_re(ignore_switch_tests)


def get_switch_expected(fullname):
    """
    >>> get_switch_expected('test_patched_select.SelectTestCase.test_error_conditions')
    False
    >>> get_switch_expected('test_patched_socket.GeneralModuleTests.testCrucialConstants')
    False
    >>> get_switch_expected('test_patched_socket.SomeOtherTest.testHello')
    True
    >>> get_switch_expected("test_patched_httplib.BasicTest.test_bad_status_repr")
    False
    """
    # certain pylint versions mistype the globals as
    # str, not re.
    # pylint:disable=no-member
    if ignore_switch_tests.match(fullname) is not None:
        return None
    if no_switch_tests.match(fullname) is not None:
        return False
    return True


disabled_tests = [
    # Want's __module__ to be 'signal', which  of course it isn't once
    # monkey-patched.
    'test_signal.GenericTests.test_functions_module_attr',
    # XXX: While we debug latest updates. This is leaking
    'test_threading.ThreadTests.test_no_refcycle_through_target',

    # The server side takes awhile to shut down
    'test_httplib.HTTPSTest.test_local_bad_hostname',
    # These were previously 3.5+ issues (same as above)
    # but have been backported.
    'test_httplib.HTTPSTest.test_local_good_hostname',
    'test_httplib.HTTPSTest.test_local_unknown_cert',


    'test_threading.ThreadTests.test_PyThreadState_SetAsyncExc',
    # uses some internal C API of threads not available when threads are emulated with greenlets

    'test_threading.ThreadTests.test_join_nondaemon_on_shutdown',
    # asserts that repr(sleep) is '<built-in function sleep>'

    'test_urllib2net.TimeoutTest.test_ftp_no_timeout',
    'test_urllib2net.TimeoutTest.test_ftp_timeout',
    'test_urllib2net.TimeoutTest.test_http_no_timeout',
    'test_urllib2net.TimeoutTest.test_http_timeout',
    # accesses _sock.gettimeout() which is always in non-blocking mode

    'test_urllib2net.OtherNetworkTests.test_ftp',
    # too slow

    'test_urllib2net.OtherNetworkTests.test_urlwithfrag',
    # fails dues to some changes on python.org

    'test_urllib2net.OtherNetworkTests.test_sites_no_connection_close',
    # flaky

    'test_socket.UDPTimeoutTest.testUDPTimeout',
    # has a bug which makes it fail with error: (107, 'Transport endpoint is not connected')
    # (it creates a TCP socket, not UDP)

    'test_socket.GeneralModuleTests.testRefCountGetNameInfo',
    # fails with "socket.getnameinfo loses a reference" while the reference is only "lost"
    # because it is referenced by the traceback - any Python function would lose a reference like that.
    # the original getnameinfo does not "lose" it because it's in C.

    'test_socket.NetworkConnectionNoServer.test_create_connection_timeout',
    # replaces socket.socket with MockSocket and then calls create_connection.
    # this unfortunately does not work with monkey patching, because gevent.socket.create_connection
    # is bound to gevent.socket.socket and updating socket.socket does not affect it.
    # this issues also manifests itself when not monkey patching DNS: http://code.google.com/p/gevent/issues/detail?id=54
    # create_connection still uses gevent.socket.getaddrinfo while it should be using socket.getaddrinfo

    'test_asyncore.BaseTestAPI.test_handle_expt',
    # sends some OOB data and expect it to be detected as such; gevent.select.select does not support that

    # This one likes to check its own filename, but we rewrite
    # the file to a temp location during patching.
    'test_asyncore.HelperFunctionTests.test_compact_traceback',

    # expects time.sleep() to return prematurely in case of a signal;
    # gevent.sleep() is better than that and does not get interrupted
    # (unless signal handler raises an error)
    'test_signal.WakeupSignalTests.test_wakeup_fd_early',

    # expects select.select() to raise select.error(EINTR'interrupted
    # system call') gevent.select.select() does not get interrupted
    # (unless signal handler raises an error) maybe it should?
    'test_signal.WakeupSignalTests.test_wakeup_fd_during',

    # these rely on os.read raising EINTR which never happens with gevent.os.read
    'test_signal.SiginterruptTest.test_without_siginterrupt',
    'test_signal.SiginterruptTest.test_siginterrupt_on',
    'test_signal.SiginterruptTest.test_siginterrupt_off',
    # This one takes forever and relies on threading details
    'test_signal.StressTest.test_stress_modifying_handlers',
    # This uses an external file, and launches it. This means that it's not
    # actually testing gevent because there's no monkey-patch.
    'test_signal.PosixTests.test_interprocess_signal',

    'test_subprocess.ProcessTestCase.test_leak_fast_process_del_killed',
    'test_subprocess.ProcessTestCase.test_zombie_fast_process_del',
    # relies on subprocess._active which we don't use

    # Very slow, tries to open lots and lots of subprocess and files,
    # tends to timeout on CI.
    'test_subprocess.ProcessTestCase.test_no_leaking',

    # This test is also very slow, and has been timing out on Travis
    # since November of 2016 on Python 3, but now also seen on Python 2/Pypy.
    'test_subprocess.ProcessTestCase.test_leaking_fds_on_error',

    # Added between 3.6.0 and 3.6.3, uses _testcapi and internals
    # of the subprocess module. Backported to Python 2.7.16.
    'test_subprocess.POSIXProcessTestCase.test_stopped',

    'test_ssl.ThreadedTests.test_default_ciphers',
    'test_ssl.ThreadedTests.test_empty_cert',
    'test_ssl.ThreadedTests.test_malformed_cert',
    'test_ssl.ThreadedTests.test_malformed_key',
    'test_ssl.NetworkedTests.test_non_blocking_connect_ex',
    # XXX needs investigating

    'test_ssl.NetworkedTests.test_algorithms',
    # The host this wants to use, sha256.tbs-internet.com, is not resolvable
    # right now (2015-10-10), and we need to get Windows wheels

    # This started timing out randomly on Travis in oct/nov 2018. It appears
    # to be something with random number generation taking too long.
    'test_ssl.BasicSocketTests.test_random_fork',

    # Relies on the repr of objects (Py3)
    'test_ssl.BasicSocketTests.test_dealloc_warn',

    # Takes forever
    'test_ssl.BasicSocketTests.test_connect_ex_error',

    'test_urllib2.HandlerTests.test_cookie_redirect',
    # this uses cookielib which we don't care about

    'test_thread.ThreadRunningTests.test__count',
    'test_thread.TestForkInThread.test_forkinthread',
    # XXX needs investigating

    'test_subprocess.POSIXProcessTestCase.test_preexec_errpipe_does_not_double_close_pipes',
    # Does not exist in the test suite until 2.7.4+. Subclasses Popen, and overrides
    # _execute_child. But our version has a different parameter list than the
    # version that comes with PyPy/CPython, so fails with a TypeError.

    # This one crashes the interpreter if it has a bug parsing the
    # invalid data.
    'test_ssl.BasicSocketTests.test_parse_cert_CVE_2019_5010',
    # We had to copy in a newer version of the test file for SSL fixes
    # and this doesn't work reliably on all versions.
    'test_httplib.HeaderTests.test_headers_debuglevel',

    # On Appveyor with Python 3.8.0 and 3.7.5, this test
    # for __class_getitem__ fails. Presumably this was added
    # in a patch release (it's not in the PEP.) Sigh.
    # https://bugs.python.org/issue38979
    'test_context.ContextTest.test_contextvar_getitem',
    # The same patch that fixed that removed this test,
    # because it would now fail.
    'test_context.ContextTest.test_context_var_new_2',

]


if OSX:
    disabled_tests += [
        # These are timing dependent, and sometimes run into the OS X
        # kernel bug leading to 'Protocol wrong type for socket'.
        # See discussion at https://github.com/benoitc/gunicorn/issues/1487
        'test_ssl.SimpleBackgroundTests.test_connect_capath',
        'test_ssl.SimpleBackgroundTests.test_connect_with_context',
    ]

if PYPY:
    disabled_tests += [
        # The exact error message the code code checks for is different
        # (possibly just on macOS?). Plain PyPy3 fails as well.
        'test_signal.WakeupSignalTests.test_wakeup_write_error',
    ]

if 'thread' in os.getenv('GEVENT_FILE', ''):
    disabled_tests += [
        'test_subprocess.ProcessTestCase.test_double_close_on_error'
        # Fails with "OSError: 9 invalid file descriptor"; expect GC/lifetime issues
    ]


if LIBUV:
    # epoll appears to work with these just fine in some cases;
    # kqueue (at least on OS X, the only tested kqueue system)
    # never does (failing with abort())
    # (epoll on Raspbian 8.0/Debian Jessie/Linux 4.1.20 works;
    # on a VirtualBox image of Ubuntu 15.10/Linux 4.2.0 both tests fail;
    # Travis CI Ubuntu 12.04 precise/Linux 3.13 causes one of these tests to hang forever)
    # XXX: Retry this with libuv 1.12+
    disabled_tests += [
        # A 2.7 test. Tries to fork, and libuv cannot fork
        'test_signal.InterProcessSignalTests.test_main',
        # Likewise, a forking problem
        'test_signal.SiginterruptTest.test_siginterrupt_off',
    ]

    disabled_tests += [
        # This test wants to pass an arbitrary fileno
        # to a socket and do things with it. libuv doesn't like this,
        # it raises EPERM. It is disabled on windows already.
        # It depends on whether we had a fd already open and multiplexed with
        'test_socket.GeneralModuleTests.test_unknown_socket_family_repr',
        # And yes, there's a typo in some versions.
        'test_socket.GeneralModuleTests.test_uknown_socket_family_repr',
        # This test sometimes fails at line 358. It's apparently
        # extremely sensitive to timing.
        'test_selectors.PollSelectorTestCase.test_timeout',
    ]

    if OSX:
        disabled_tests += [
            # XXX: Starting when we upgraded from libuv 1.18.0
            # to 1.19.2, this sometimes (usually) started having
            # a series of calls ('select.poll(0)', 'select.poll(-1)')
            # take longer than the allowed 0.5 seconds. Debugging showed that
            # it was the second call that took longer, for no apparent reason.
            # There doesn't seem to be a change in the source code to libuv that
            # would affect this.
            # XXX-XXX: This actually disables too many tests :(
            'test_selectors.PollSelectorTestCase.test_timeout',
        ]

    if RUN_COVERAGE:

        disabled_tests += [
            # Starting with #1145 this test (actually
            # TestTLS_FTPClassMixin) becomes sensitive to timings
            # under coverage.
            'test_ftplib.TestFTPClass.test_storlines',
        ]


    if sys.platform.startswith('linux'):
        disabled_tests += [
            # crashes with EPERM, which aborts the epoll loop, even
            # though it was allowed in in the first place.
            'test_asyncore.FileWrapperTest.test_dispatcher',
        ]


        if PYPY:
            disabled_tests += [
                # appears to timeout?
                'test_threading.ThreadTests.test_finalize_with_trace',
                'test_asyncore.DispatcherWithSendTests_UsePoll.test_send',
                'test_asyncore.DispatcherWithSendTests.test_send',

                # More unexpected timeouts
                'test_ssl.ContextTests.test__https_verify_envvar',
                'test_subprocess.ProcessTestCase.test_check_output',
                'test_telnetlib.ReadTests.test_read_eager_A',

                # But on Windows, our gc fix for that doesn't work anyway
                # so we have to disable it.
                'test_urllib2_localnet.TestUrlopen.test_https_with_cafile',

                # These tests hang. see above.
                'test_threading.ThreadJoinOnShutdown.test_1_join_on_shutdown',
                'test_threading.ThreadingExceptionTests.test_print_exception',

                # Our copy of these in test__subprocess.py also hangs.
                # Anything that uses Popen.communicate or directly uses
                # Popen.stdXXX.read hangs. It's not clear why.
                'test_subprocess.ProcessTestCase.test_communicate',
                'test_subprocess.ProcessTestCase.test_cwd',
                'test_subprocess.ProcessTestCase.test_env',
                'test_subprocess.ProcessTestCase.test_stderr_pipe',
                'test_subprocess.ProcessTestCase.test_stdout_pipe',
                'test_subprocess.ProcessTestCase.test_stdout_stderr_pipe',
                'test_subprocess.ProcessTestCase.test_stderr_redirect_with_no_stdout_redirect',
                'test_subprocess.ProcessTestCase.test_stdout_filedes_of_stdout',
                'test_subprocess.ProcessTestcase.test_stdout_none',
                'test_subprocess.ProcessTestcase.test_universal_newlines',
                'test_subprocess.ProcessTestcase.test_writes_before_communicate',
                'test_subprocess.Win32ProcessTestCase._kill_process',
                'test_subprocess.Win32ProcessTestCase._kill_dead_process',
                'test_subprocess.Win32ProcessTestCase.test_shell_sequence',
                'test_subprocess.Win32ProcessTestCase.test_shell_string',
                'test_subprocess.CommandsWithSpaces.with_spaces',
            ]


    if WIN:

        disabled_tests += [
            # This test winds up hanging a long time.
            # Inserting GCs doesn't fix it.
            'test_ssl.ThreadedTests.test_handshake_timeout',

            # These sometimes raise LoopExit, for no apparent reason,
            # mostly but not exclusively on Python 2. Sometimes (often?)
            # this happens in the setUp() method when we attempt to get a client
            # connection
            'test_socket.BufferIOTest.testRecvFromIntoBytearray',
            'test_socket.BufferIOTest.testRecvFromIntoArray',
            'test_socket.BufferIOTest.testRecvIntoArray',
            'test_socket.BufferIOTest.testRecvIntoMemoryview',
            'test_socket.BufferIOTest.testRecvFromIntoEmptyBuffer',
            'test_socket.BufferIOTest.testRecvFromIntoMemoryview',
            'test_socket.BufferIOTest.testRecvFromIntoSmallBuffer',
            'test_socket.BufferIOTest.testRecvIntoBytearray',
        ]

    if PYPY:

        if TRAVIS:

            disabled_tests += [
                # This sometimes causes a segfault for no apparent reason.
                # See https://travis-ci.org/gevent/gevent/jobs/327328704
                # Can't reproduce locally.
                'test_subprocess.ProcessTestCase.test_universal_newlines_communicate',
            ]

if RUN_COVERAGE and CFFI_BACKEND:
    disabled_tests += [
        # This test hangs in this combo for some reason
        'test_socket.GeneralModuleTests.test_sendall_interrupted',
        # This can get a timeout exception instead of the Alarm
        'test_socket.TCPTimeoutTest.testInterruptedTimeout',

        # This test sometimes gets the wrong answer (due to changed timing?)
        'test_socketserver.SocketServerTest.test_ForkingUDPServer',

        # Timing and signals are off, so a handler exception doesn't get raised.
        # Seen under libev
        'test_signal.InterProcessSignalTests.test_main',
    ]


if PYPY and sys.pypy_version_info[:2] == (7, 3): # pylint:disable=no-member

    if OSX:
        disabled_tests += [
            # This is expected to produce an SSLError, but instead it appears to
            # actually work. See above for when it started failing the same on
            # Travis.
            'test_ssl.ThreadedTests.test_alpn_protocols',
            # This fails, presumably due to the OpenSSL it's compiled with.
            'test_ssl.ThreadedTests.test_default_ecdh_curve',
        ]

if PYPY3 and TRAVIS:
    disabled_tests += [
        # If socket.SOCK_CLOEXEC is defined, this creates a socket
        # and tests its type with ``sock.type & socket.SOCK_CLOEXEC``
        # We have a ``@property`` for ``type`` that takes care of
        # ``SOCK_NONBLOCK`` on Linux, but otherwise it's just a pass-through.
        # This started failing with PyPy 7.3.1 and it's not clear why.
        'test_socket.InheritanceTest.test_SOCK_CLOEXEC',
    ]

if PYPY3 and WIN:
    disabled_tests += [
        # test_httpservers.CGIHTTPServerTestCase all seem to hang.
        # There seem to be some general subprocess issues. This is
        # ignored entirely from known_failures.py

        # This produces:
        #
        #  OSError: [Errno 10014] The system detected an invalid
        #  pointer address in attempting to use a pointer argument in
        #  a call
        #
        # When calling socket.socket(fileno=fd) when we actually
        # call ``self._socket =self._gevent_sock_class()``.
        'test_socket.GeneralModuleTests.test_socket_fileno',

        # This doesn't respect the scope properly
        #
        #  self.assertEqual(sockaddr, ('ff02::1de:c0:face:8d', 1234, 0, ifindex))
        #   AssertionError: Tuples differ: ('ff02::1de:c0:face:8d%42', 1234, 0, 42) != ('ff02::1de:c0:face:8d', 1234, 0, 42
        #
        'test_socket.GeneralModuleTests.test_getaddrinfo_ipv6_scopeid_numeric',

        # self.assertEqual(newsock.get_inheritable(), False)
        #  AssertionError: True != False
        'test_socket.InheritanceTest.test_dup',
    ]

def _make_run_with_original(mod_name, func_name):
    @contextlib.contextmanager
    def with_orig():
        mod = __import__(mod_name)
        now = getattr(mod, func_name)
        from gevent.monkey import get_original
        orig = get_original(mod_name, func_name)
        try:
            setattr(mod, func_name, orig)
            yield
        finally:
            setattr(mod, func_name, now)
    return with_orig

@contextlib.contextmanager
def _gc_at_end():
    try:
        yield
    finally:
        import gc
        gc.collect()
        gc.collect()

@contextlib.contextmanager
def _flaky_socket_timeout():
    import socket
    try:
        yield
    except socket.timeout:
        flaky.reraiseFlakyTestTimeout()

# Map from FQN to a context manager that will be wrapped around
# that test.
wrapped_tests = {
}



class _PatchedTest(object):
    def __init__(self, test_fqn):
        self._patcher = wrapped_tests[test_fqn]

    def __call__(self, orig_test_fn):

        @functools.wraps(orig_test_fn)
        def test(*args, **kwargs):
            with self._patcher():
                return orig_test_fn(*args, **kwargs)
        return test


if OSX:
    disabled_tests += [
        'test_subprocess.POSIXProcessTestCase.test_run_abort',
        # causes Mac OS X to show "Python crashes" dialog box which is annoying
    ]

if WIN:
    disabled_tests += [
        # Issue with Unix vs DOS newlines in the file vs from the server
        'test_ssl.ThreadedTests.test_socketserver',
        # This sometimes hangs (only on appveyor)
        'test_ssl.ThreadedTests.test_asyncore_server',
        # On appveyor, this sometimes produces 'A non-blocking socket
        # operation could not be completed immediately', followed by
        # 'No connection could be made because the target machine
        # actively refused it'
        'test_socket.NonBlockingTCPTests.testAccept',

        # On appveyor, this test has been seen to fail on 3.9 and 3.8
    ]

    if sys.version_info[:2] <= (3, 9):
        disabled_tests += [
            'test_context.HamtTest.test_hamt_collision_3',
            # Sometimes fails::
            #
            #     self.assertIn('got more than ', str(cm.exception))
            # AssertionError: 'got more than ' not found in
            #    'Remote end closed connection without response'
            #
            'test_httplib.BasicTest.test_overflowing_header_limit_after_100',

        ]

    # These are a problem on 3.5; on 3.6+ they wind up getting (accidentally) disabled.
    wrapped_tests.update({
        'test_socket.SendfileUsingSendTest.testWithTimeout': _flaky_socket_timeout,
        'test_socket.SendfileUsingSendTest.testOffset': _flaky_socket_timeout,
        'test_socket.SendfileUsingSendTest.testRegularFile': _flaky_socket_timeout,
        'test_socket.SendfileUsingSendTest.testCount': _flaky_socket_timeout,
    })

if PYPY:
    disabled_tests += [
        # Does not exist in the CPython test suite, tests for a specific bug
        # in PyPy's forking. Only runs on linux and is specific to the PyPy
        # implementation of subprocess (possibly explains the extra parameter to
        # _execut_child)
        'test_subprocess.ProcessTestCase.test_failed_child_execute_fd_leak',
        # On some platforms, this returns "zlib_compression", but the test is looking for
        # "ZLIB"
        'test_ssl.ThreadedTests.test_compression',

        # These are flaxy, apparently a race condition? Began with PyPy 2.7-7 and 3.6-7
        'test_asyncore.TestAPI_UsePoll.test_handle_error',
        'test_asyncore.TestAPI_UsePoll.test_handle_read',
    ]

    if WIN:
        disabled_tests += [
            # Starting in 7.3.1 on Windows, this stopped raising ValueError; it appears to
            # be a bug in PyPy.
            'test_signal.WakeupFDTests.test_invalid_fd',
            # Likewise for 7.3.1. See the comments for PY35
            'test_socket.GeneralModuleTests.test_sock_ioctl',
        ]


    disabled_tests += [
        # These are flaky, beginning in 3.6-alpha 7.0, not finding some flag
        # set, apparently a race condition
        'test_asyncore.TestAPI_UveIPv6Poll.test_handle_accept',
        'test_asyncore.TestAPI_UveIPv6Poll.test_handle_accepted',
        'test_asyncore.TestAPI_UveIPv6Poll.test_handle_close',
        'test_asyncore.TestAPI_UveIPv6Poll.test_handle_write',

        'test_asyncore.TestAPI_UseIPV6Select.test_handle_read',

        # These are reporting 'ssl has no attribute ...'
        # This could just be an OSX thing
        'test_ssl.ContextTests.test__create_stdlib_context',
        'test_ssl.ContextTests.test_create_default_context',
        'test_ssl.ContextTests.test_get_ciphers',
        'test_ssl.ContextTests.test_options',
        'test_ssl.ContextTests.test_constants',

        # These tend to hang for some reason, probably not properly
        # closed sockets.
        'test_socketserver.SocketServerTest.test_write',

        # This uses ctypes to do funky things including using ptrace,
        # it hangs
        'test_subprocess.ProcessTestcase.test_child_terminated_in_stopped_state',

        # Certificate errors; need updated test
        'test_urllib2_localnet.TestUrlopen.test_https',
    ]

# Generic Python 3



disabled_tests += [
    # Triggers the crash reporter
    'test_threading.SubinterpThreadingTests.test_daemon_threads_fatal_error',

    # Relies on an implementation detail, Thread._tstate_lock
    'test_threading.ThreadTests.test_tstate_lock',
    # Relies on an implementation detail (reprs); we have our own version
    'test_threading.ThreadTests.test_various_ops',
    'test_threading.ThreadTests.test_various_ops_large_stack',
    'test_threading.ThreadTests.test_various_ops_small_stack',

    # Relies on Event having a _cond and an _reset_internal_locks()
    # XXX: These are commented out in the source code of test_threading because
    # this doesn't work.
    # 'lock_tests.EventTests.test_reset_internal_locks',

    # Python bug 13502. We may or may not suffer from this as its
    # basically a timing race condition.
    # XXX Same as above
    # 'lock_tests.EventTests.test_set_and_clear',

    # These tests want to assert on the type of the class that implements
    # `Popen.stdin`; we use a FileObject, but they expect different subclasses
    # from the `io` module
    'test_subprocess.ProcessTestCase.test_io_buffered_by_default',
    'test_subprocess.ProcessTestCase.test_io_unbuffered_works',

    # 3.3 exposed the `endtime` argument to wait accidentally.
    # It is documented as deprecated and not to be used since 3.4
    # This test in 3.6.3 wants to use it though, and we don't have it.
    'test_subprocess.ProcessTestCase.test_wait_endtime',

    # These all want to inspect the string value of an exception raised
    # by the exec() call in the child. The _posixsubprocess module arranges
    # for better exception handling and printing than we do.
    'test_subprocess.POSIXProcessTestCase.test_exception_bad_args_0',
    'test_subprocess.POSIXProcessTestCase.test_exception_bad_executable',
    'test_subprocess.POSIXProcessTestCase.test_exception_cwd',
    # Relies on a 'fork_exec' attribute that we don't provide
    'test_subprocess.POSIXProcessTestCase.test_exception_errpipe_bad_data',
    'test_subprocess.POSIXProcessTestCase.test_exception_errpipe_normal',

    # Python 3 fixed a bug if the stdio file descriptors were closed;
    # we still have that bug
    'test_subprocess.POSIXProcessTestCase.test_small_errpipe_write_fd',

    # Relies on implementation details (some of these tests were added in 3.4,
    # but PyPy3 is also shipping them.)
    'test_socket.GeneralModuleTests.test_SocketType_is_socketobject',
    'test_socket.GeneralModuleTests.test_dealloc_warn',
    'test_socket.GeneralModuleTests.test_repr',
    'test_socket.GeneralModuleTests.test_str_for_enums',
    'test_socket.GeneralModuleTests.testGetaddrinfo',

]
if TRAVIS:
    disabled_tests += [
        # test_cwd_with_relative_executable tends to fail
        # on Travis...it looks like the test processes are stepping
        # on each other and messing up their temp directories. We tend to get things like
        #    saved_dir = os.getcwd()
        #   FileNotFoundError: [Errno 2] No such file or directory
        'test_subprocess.ProcessTestCase.test_cwd_with_relative_arg',
        'test_subprocess.ProcessTestCaseNoPoll.test_cwd_with_relative_arg',
        'test_subprocess.ProcessTestCase.test_cwd_with_relative_executable',

        # In 3.7 and 3.8 on Travis CI, this appears to take the full 3 seconds.
        # Can't reproduce it locally. We have our own copy of this that takes
        # timing on CI into account.
        'test_subprocess.RunFuncTestCase.test_run_with_shell_timeout_and_capture_output',
    ]

disabled_tests += [
    # XXX: BUG: We simply don't handle this correctly. On CPython,
    # we wind up raising a BlockingIOError and then
    # BrokenPipeError and then some random TypeErrors, all on the
    # server. CPython 3.5 goes directly to socket.send() (via
    # socket.makefile), whereas CPython 3.6 uses socket.sendall().
    # On PyPy, the behaviour is much worse: we hang indefinitely, perhaps exposing a problem
    # with our signal handling.

    # In actuality, though, this test doesn't fully test the EINTR it expects
    # to under gevent (because if its EWOULDBLOCK retry behaviour.)
    # Instead, the failures were all due to `pthread_kill` trying to send a signal
    # to a greenlet instead of a real thread. The solution is to deliver the signal
    # to the real thread by letting it get the correct ID, and we previously
    # used make_run_with_original to make it do that.
    #
    # But now that we have disabled our wrappers around Thread.join() in favor
    # of the original implementation, that causes problems:
    # background.join() thinks that it is the current thread, and won't let it
    # be joined.
    'test_wsgiref.IntegrationTests.test_interrupted_write',
]

# PyPy3 3.5.5 v5.8-beta

if PYPY3:


    disabled_tests += [
        # This raises 'RuntimeError: reentrant call' when exiting the
        # process tries to close the stdout stream; no other platform does this.
        # Seen in both 3.3 and 3.5 (5.7 and 5.8)
        'test_signal.SiginterruptTest.test_siginterrupt_off',
    ]

    disabled_tests += [
        # This fails to close all the FDs, at least on CI. On OS X, many of the
        # POSIXProcessTestCase fd tests have issues.
        'test_subprocess.POSIXProcessTestCase.test_close_fds_when_max_fd_is_lowered',

        # This has the wrong constants in 5.8 (but worked in 5.7), at least on
        # OS X. It finds "zlib compression" but expects "ZLIB".
        'test_ssl.ThreadedTests.test_compression',

        # The below are new with 5.10.1
        # This gets an EOF in violation of protocol; again, even without gevent
        # (at least on OS X; it's less consistent about that on travis)
        'test_ssl.NetworkedBIOTests.test_handshake',

        # This passes various "invalid" strings and expects a ValueError. not sure why
        # we don't see errors on CPython.
        'test_subprocess.ProcessTestCase.test_invalid_env',
    ]

    if OSX:
        disabled_tests += [
            # These all fail with "invalid_literal for int() with base 10: b''"
            'test_subprocess.POSIXProcessTestCase.test_close_fds',
            'test_subprocess.POSIXProcessTestCase.test_close_fds_after_preexec',
            'test_subprocess.POSIXProcessTestCase.test_pass_fds',
            'test_subprocess.POSIXProcessTestCase.test_pass_fds_inheritable',
            'test_subprocess.POSIXProcessTestCase.test_pipe_cloexec',


            # The below are new with 5.10.1
            # These fail with 'OSError: received malformed or improperly truncated ancillary data'
            'test_socket.RecvmsgSCMRightsStreamTest.testCmsgTruncLen0',
            'test_socket.RecvmsgSCMRightsStreamTest.testCmsgTruncLen0Plus1',
            'test_socket.RecvmsgSCMRightsStreamTest.testCmsgTruncLen1',
            'test_socket.RecvmsgSCMRightsStreamTest.testCmsgTruncLen2Minus1',

            # Using the provided High Sierra binary, these fail with
            # 'ValueError: invalid protocol version _SSLMethod.PROTOCOL_SSLv3'.
            # gevent code isn't involved and running them unpatched has the same issue.
            'test_ssl.ContextTests.test_constructor',
            'test_ssl.ContextTests.test_protocol',
            'test_ssl.ContextTests.test_session_stats',
            'test_ssl.ThreadedTests.test_echo',
            'test_ssl.ThreadedTests.test_protocol_sslv23',
            'test_ssl.ThreadedTests.test_protocol_sslv3',
            'test_ssl.ThreadedTests.test_protocol_tlsv1',
            'test_ssl.ThreadedTests.test_protocol_tlsv1_1',
            # Similar, they fail without monkey-patching.
            'test_ssl.TestPostHandshakeAuth.test_pha_no_pha_client',
            'test_ssl.TestPostHandshakeAuth.test_pha_optional',
            'test_ssl.TestPostHandshakeAuth.test_pha_required',

            # This gets None instead of http1.1, even without gevent
            'test_ssl.ThreadedTests.test_npn_protocols',

            # This fails to decode a filename even without gevent,
            # at least on High Sierra. Newer versions of the tests actually skip this.
            'test_httpservers.SimpleHTTPServerTestCase.test_undecodable_filename',
        ]

    disabled_tests += [
        # This seems to be a buffering issue? Something isn't
        # getting flushed. (The output is wrong). Under PyPy3 5.7,
        # I couldn't reproduce locally in Ubuntu 16 in a VM
        # or a laptop with OS X. Under 5.8.0, I can reproduce it, but only
        # when run by the testrunner, not when run manually on the command line,
        # so something is changing in stdout buffering in those situations.
        'test_threading.ThreadJoinOnShutdown.test_2_join_in_forked_process',
        'test_threading.ThreadJoinOnShutdown.test_1_join_in_forked_process',
    ]

    if TRAVIS:
        disabled_tests += [
            # Likewise, but I haven't produced it locally.
            'test_threading.ThreadJoinOnShutdown.test_1_join_on_shutdown',
        ]

if PYPY:

    wrapped_tests.update({
        # XXX: gevent: The error that was raised by that last call
        # left a socket open on the server or client. The server gets
        # to http/server.py(390)handle_one_request and blocks on
        # self.rfile.readline which apparently is where the SSL
        # handshake is done. That results in the exception being
        # raised on the client above, but apparently *not* on the
        # server. Consequently it sits trying to read from that
        # socket. On CPython, when the client socket goes out of scope
        # it is closed and the server raises an exception, closing the
        # socket. On PyPy, we need a GC cycle for that to happen.
        # Without the socket being closed and exception being raised,
        # the server cannot be stopped (it runs each request in the
        # same thread that would notice it had been stopped), and so
        # the cleanup method added by start_https_server to stop the
        # server blocks "forever".

        # This is an important test, so rather than skip it in patched_tests_setup,
        # we do the gc before we return.
        'test_urllib2_localnet.TestUrlopen.test_https_with_cafile': _gc_at_end,

        'test_httpservers.BaseHTTPServerTestCase.test_command': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_handler': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_head_keep_alive': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_head_via_send_error': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_header_close': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_internal_key_error': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_request_line_trimming': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_return_custom_status': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_return_header_keep_alive': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_send_blank': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_send_error': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_version_bogus': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_version_digits': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_version_invalid': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_version_none': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_version_none_get': _gc_at_end,
        'test_httpservers.BaseHTTPServerTestCase.test_get': _gc_at_end,
        'test_httpservers.SimpleHTTPServerTestCase.test_get': _gc_at_end,
        'test_httpservers.SimpleHTTPServerTestCase.test_head': _gc_at_end,
        'test_httpservers.SimpleHTTPServerTestCase.test_invalid_requests': _gc_at_end,
        'test_httpservers.SimpleHTTPServerTestCase.test_path_without_leading_slash': _gc_at_end,
        'test_httpservers.CGIHTTPServerTestCase.test_invaliduri': _gc_at_end,
        'test_httpservers.CGIHTTPServerTestCase.test_issue19435': _gc_at_end,

        'test_httplib.TunnelTests.test_connect': _gc_at_end,
        'test_httplib.SourceAddressTest.testHTTPConnectionSourceAddress': _gc_at_end,

        # Unclear
        'test_urllib2_localnet.ProxyAuthTests.test_proxy_with_bad_password_raises_httperror': _gc_at_end,
        'test_urllib2_localnet.ProxyAuthTests.test_proxy_with_no_password_raises_httperror': _gc_at_end,
    })



disabled_tests += [
    'test_subprocess.ProcessTestCase.test_threadsafe_wait',
    # XXX: It seems that threading.Timer is not being greened properly, possibly
    # due to a similar issue to what gevent.threading documents for normal threads.
    # In any event, this test hangs forever


    'test_subprocess.POSIXProcessTestCase.test_preexec_errpipe_does_not_double_close_pipes',
    # Subclasses Popen, and overrides _execute_child. Expects things to be done
    # in a particular order in an exception case, but we don't follow that
    # exact order


    'test_selectors.PollSelectorTestCase.test_above_fd_setsize',
    # This test attempts to open many many file descriptors and
    # poll on them, expecting them all to be ready at once. But
    # libev limits the number of events it will return at once. Specifically,
    # on linux with epoll, it returns a max of 64 (ev_epoll.c).

    # XXX: Hangs (Linux only)
    'test_socket.NonBlockingTCPTests.testInitNonBlocking',
    # We don't handle the Linux-only SOCK_NONBLOCK option
    'test_socket.NonblockConstantTest.test_SOCK_NONBLOCK',

    # Tries to use multiprocessing which doesn't quite work in
    # monkey_test module (Windows only)
    'test_socket.TestSocketSharing.testShare',

    # Windows-only: Sockets have a 'ioctl' method in Python 3
    # implemented in the C code. This test tries to check
    # for the presence of the method in the class, which we don't
    # have because we don't inherit the C implementation. But
    # it should be found at runtime.
    'test_socket.GeneralModuleTests.test_sock_ioctl',

    # XXX This fails for an unknown reason
    'test_httplib.HeaderTests.test_parse_all_octets',
]

if OSX:
    disabled_tests += [
        # These raise "OSError: 12 Cannot allocate memory" on both
        # patched and unpatched runs
        'test_socket.RecvmsgSCMRightsStreamTest.testFDPassEmpty',
    ]

    if TRAVIS:
        # This has been seen to produce "Inconsistency detected by
        # ld.so: dl-open.c: 231: dl_open_worker: Assertion
        # `_dl_debug_initialize (0, args->nsid)->r_state ==
        # RT_CONSISTENT' failed!" and fail.
        disabled_tests += [
            'test_threading.ThreadTests.test_is_alive_after_fork',
            # This has timing constraints that are strict and do not always
            # hold.
            'test_selectors.PollSelectorTestCase.test_timeout',
        ]

if TRAVIS:
    disabled_tests += [
        'test_subprocess.ProcessTestCase.test_double_close_on_error',
        # This test is racy or OS-dependent. It passes locally (sufficiently fast machine)
        # but fails under Travis
    ]


disabled_tests += [
    # XXX: Hangs
    'test_ssl.ThreadedTests.test_nonblocking_send',
    'test_ssl.ThreadedTests.test_socketserver',
    # Uses direct sendfile, doesn't properly check for it being enabled
    'test_socket.GeneralModuleTests.test__sendfile_use_sendfile',


    # Relies on the regex of the repr having the locked state (TODO: it'd be nice if
    # we did that).
    # XXX: These are commented out in the source code of test_threading because
    # this doesn't work.
    # 'lock_tests.LockTests.lest_locked_repr',
    # 'lock_tests.LockTests.lest_repr',


    # This test opens a socket, creates a new socket with the same fileno,
    # closes the original socket (and hence fileno) and then
    # expects that the calling setblocking() on the duplicate socket
    # will raise an error. Our implementation doesn't work that way because
    # setblocking() doesn't actually touch the file descriptor.
    # That's probably OK because this was a GIL state error in CPython
    # see https://github.com/python/cpython/commit/fa22b29960b4e683f4e5d7e308f674df2620473c
    'test_socket.TestExceptions.test_setblocking_invalidfd',
]


if ARES:
    disabled_tests += [
        # These raise different errors or can't resolve
        # the IP address correctly
        'test_socket.GeneralModuleTests.test_host_resolution',
        'test_socket.GeneralModuleTests.test_getnameinfo',
    ]


disabled_tests += [
    'test_threading.MiscTestCase.test__all__',
]

# We don't actually implement socket._sendfile_use_sendfile,
# so these tests, which think they're using that and os.sendfile,
# fail.
disabled_tests += [
    'test_socket.SendfileUsingSendfileTest.testCount',
    'test_socket.SendfileUsingSendfileTest.testCountSmall',
    'test_socket.SendfileUsingSendfileTest.testCountWithOffset',
    'test_socket.SendfileUsingSendfileTest.testOffset',
    'test_socket.SendfileUsingSendfileTest.testRegularFile',
    'test_socket.SendfileUsingSendfileTest.testWithTimeout',
    'test_socket.SendfileUsingSendfileTest.testEmptyFileSend',
    'test_socket.SendfileUsingSendfileTest.testNonBlocking',
    'test_socket.SendfileUsingSendfileTest.test_errors',
]

# Ditto
disabled_tests += [
    'test_socket.GeneralModuleTests.test__sendfile_use_sendfile',
]

disabled_tests += [
    # This test requires Linux >= 4.3. When we were running 'dist:
    # trusty' on the 4.4 kernel, it passed (~July 2017). But when
    # trusty became the default dist in September 2017 and updated
    # the kernel to 4.11.6, it begain failing. It fails on `res =
    # op.recv(assoclen + len(plain) + taglen)` (where 'op' is the
    # client socket) with 'OSError: [Errno 22] Invalid argument'
    # for unknown reasons. This is *after* having successfully
    # called `op.sendmsg_afalg`. Post 3.6.0, what we test with,
    # the test was changed to require Linux 4.9 and the data was changed,
    # so this is not our fault. We should eventually update this when we
    # update our 3.6 version.
    # See https://bugs.python.org/issue29324
    'test_socket.LinuxKernelCryptoAPI.test_aead_aes_gcm',
]


disabled_tests += [
    # These want to use the private '_communicate' method, which
    # our Popen doesn't have.
    'test_subprocess.MiscTests.test_call_keyboardinterrupt_no_kill',
    'test_subprocess.MiscTests.test_context_manager_keyboardinterrupt_no_kill',
    'test_subprocess.MiscTests.test_run_keyboardinterrupt_no_kill',

    # This wants to check that the underlying fileno is blocking,
    # but it isn't.
    'test_socket.NonBlockingTCPTests.testSetBlocking',

    # 3.7b2 made it impossible to instantiate SSLSocket objects
    # directly, and this tests for that, but we don't follow that change.
    'test_ssl.BasicSocketTests.test_private_init',

    # 3.7b2 made a change to this test that on the surface looks incorrect,
    # but it passes when they run it and fails when we do. It's not
    # clear why.
    'test_ssl.ThreadedTests.test_check_hostname_idn',

    # These appear to hang, haven't investigated why
    'test_ssl.SimpleBackgroundTests.test_get_server_certificate',
    # Probably the same as NetworkConnectionNoServer.test_create_connection_timeout
    'test_socket.NetworkConnectionNoServer.test_create_connection',

    # Internals of the threading module that change.
    'test_threading.ThreadTests.test_finalization_shutdown',
    'test_threading.ThreadTests.test_shutdown_locks',
    # Expects a deprecation warning we don't raise
    'test_threading.ThreadTests.test_old_threading_api',
    # This tries to use threading.interrupt_main() from a new Thread;
    # but of course that's actually the same thread and things don't
    # work as expected.
    'test_threading.InterruptMainTests.test_interrupt_main_subthread',
    'test_threading.InterruptMainTests.test_interrupt_main_noerror',

    # TLS1.3 seems flaky
    'test_ssl.ThreadedTests.test_wrong_cert_tls13',
]


if APPVEYOR:
    disabled_tests += [
        # This sometimes produces ``self.assertEqual(1, len(s.select(0))): 1 != 0``.
        # Probably needs to spin the loop once.
        'test_selectors.BaseSelectorTestCase.test_timeout',
    ]


disabled_tests += [
    # This one seems very strict: doesn't want a pathlike
    # first argument when shell is true.
    'test_subprocess.RunFuncTestCase.test_run_with_pathlike_path',
    # This tests for a warning we don't raise.
    'test_subprocess.RunFuncTestCase.test_bufsize_equal_one_binary_mode',

    # This compares the output of threading.excepthook with
    # data constructed in Python. But excepthook is implemented in C
    # and can't see the patched threading.get_ident() we use, so the
    # output doesn't match.
    'test_threading.ExceptHookTests.test_excepthook_thread_None',
]

if sys.version_info[:3] < (3, 8, 1):
    disabled_tests += [
        # Earlier versions parse differently so the newer test breaks
        'test_ssl.BasicSocketTests.test_parse_all_sans',
        'test_ssl.BasicSocketTests.test_parse_cert_CVE_2013_4238',
    ]

if sys.version_info[:3] < (3, 8, 10):
    disabled_tests += [
        # These were added for fixes sometime between 3.8.1 and 3.8.10
        'test_ftplib.TestFTPClass.test_makepasv_issue43285_security_disabled',
        'test_ftplib.TestFTPClass.test_makepasv_issue43285_security_enabled_default',
        'test_httplib.BasicTest.test_dir_with_added_behavior_on_status',
        'test_httplib.TunnelTests.test_tunnel_connect_single_send_connection_setup',
        'test_ssl.TestSSLDebug.test_msg_callback_deadlock_bpo43577',
        # This one fails with the updated certs
        'test_ssl.ContextTests.test_load_verify_cadata',
        # This one times out on 3.7.1 on Appveyor
        'test_ftplib.TestTLS_FTPClassMixin.test_retrbinary_rest',
    ]

if RESOLVER_DNSPYTHON:
    disabled_tests += [
        # This does two things DNS python doesn't. First, it sends it
        # capital letters and expects them to be returned lowercase.
        # Second, it expects the symbolic scopeid to be stripped from the end.
        'test_socket.GeneralModuleTests.test_getaddrinfo_ipv6_scopeid_symbolic',
    ]

# if 'signalfd' in os.environ.get('GEVENT_BACKEND', ''):
#     # tests that don't interact well with signalfd
#     disabled_tests.extend([
#         'test_signal.SiginterruptTest.test_siginterrupt_off',
#         'test_socketserver.SocketServerTest.test_ForkingTCPServer',
#         'test_socketserver.SocketServerTest.test_ForkingUDPServer',
#         'test_socketserver.SocketServerTest.test_ForkingUnixStreamServer'])

# LibreSSL reports OPENSSL_VERSION_INFO (2, 0, 0, 0, 0) regardless of its version,
# so this is known to fail on some distros. We don't want to detect this because we
# don't want to trigger the side-effects of importing ssl prematurely if we will
# be monkey-patching, so we skip this test everywhere. It doesn't do much for us
# anyway.
disabled_tests += [
    'test_ssl.BasicSocketTests.test_openssl_version'
]

if OSX:

    disabled_tests += [
        # This sometimes produces OSError: Errno 40: Message too long
        'test_socket.RecvmsgIntoTCPTest.testRecvmsgIntoGenerator',

        # These sometime timeout. Cannot reproduce locally.
        'test_ftp.TestTLS_FTPClassMixin.test_mlsd',
        'test_ftp.TestTLS_FTPClassMixin.test_retrlines_too_long',
        'test_ftp.TestTLS_FTPClassMixin.test_storlines',
        'test_ftp.TestTLS_FTPClassMixin.test_retrbinary_rest',
    ]

    if RESOLVER_ARES and PY38 and not RUNNING_ON_CI:
        disabled_tests += [
            # When updating to 1.16.0 this was seen locally, but not on CI.
            # Tuples differ: ('ff02::1de:c0:face:8d', 1234, 0, 0)
            #             != ('ff02::1de:c0:face:8d', 1234, 0, 1)
            'test_socket.GeneralModuleTests.test_getaddrinfo_ipv6_scopeid_symbolic',
        ]

if PY39:

    disabled_tests += [
        # Depends on exact details of the repr. Eww.
        'test_subprocess.ProcessTestCase.test_repr',
        # Tries to wait for the process without using Popen APIs, and expects the
        # ``returncode`` attribute to stay None. But we have already hooked SIGCHLD, so
        # we see and set the ``returncode``; there is no way to wait that doesn't do that.
        'test_subprocess.POSIXProcessTestTest.test_send_signal_race',
    ]

    if sys.version_info[:3] < (3, 9, 5):
        disabled_tests += [
            # These were added for fixes sometime between 3.9.1 and 3.9.5
            'test_ftplib.TestFTPClass.test_makepasv_issue43285_security_disabled',
            'test_ftplib.TestFTPClass.test_makepasv_issue43285_security_enabled_default',
            'test_httplib.BasicTest.test_dir_with_added_behavior_on_status',
            'test_httplib.TunnelTests.test_tunnel_connect_single_send_connection_setup',
            'test_ssl.TestSSLDebug.test_msg_callback_deadlock_bpo43577',
            # This one fails with the updated certs
            'test_ssl.ContextTests.test_load_verify_cadata',
            # These time out on 3.9.1 on Appveyor
            'test_ftplib.TestTLS_FTPClassMixin.test_retrbinary_rest',
            'test_ftplib.TestTLS_FTPClassMixin.test_retrlines_too_long',
        ]

if PY310:
    disabled_tests += [
        # They arbitrarily made some types so that they can't be created;
        # that's an implementation detail we're not going to follow (
        # it would require them to be factory functions).
        'test_select.SelectTestCase.test_disallow_instantiation',
        'test_threading.ThreadTests.test_disallow_instantiation',
        # This wants two true threads to work, but a CPU bound loop
        # in a greenlet can't be interrupted.
        'test_threading.InterruptMainTests.test_can_interrupt_tight_loops',
        # We don't currently implement pipesize.
        'test_subprocess.ProcessTestCase.test_pipesize_default',
        'test_subprocess.ProcessTestCase.test_pipesizes',
        # Unknown
        'test_signal.SiginterruptTest.test_siginterrupt_off',
    ]

    if TRAVIS:
        disabled_tests += [
            # The mixing of subinterpreters (with threads) and gevent apparently
            # leads to a segfault on Ubuntu/GitHubActions/3.10rc1. Not clear why.
            # But that's not a great use case for gevent.
            'test_threading.SubinterpThreadingTests.test_threads_join',
            'test_threading.SubinterpThreadingTests.test_threads_join_2',
        ]

if PY311:
    disabled_tests += [
        # CPython issue #27718: This wants to require all objects to
        # have a __module__ of 'signal' because pydoc. Obviously our patches don't.
        'test_signal.GenericTests.test_functions_module_attr',
        # 3.11 added subprocess._USE_VFORK and subprocess._USE_POSIX_SPAWN.
        # We don't support either of those (although USE_VFORK might be possible?)
        'test_subprocess.ProcessTestCase.test__use_vfork',
    ]

    if sys.version_info[:3] < (3, 11, 8):
        # New tests in that version that won't pass on earlier versions.
        disabled_tests += [
            'test_threading.ThreadTests.test_main_thread_after_fork_from_dummy_thread',
            'tets_ssl.TestPreHandshakeClose.test_preauth_data_to_tls_client',
            'test_ssl.TestPreHandshakeClose.test_preauth_data_to_tls_server',
            'test_signal.PosixTests.test_no_repr_is_called_on_signal_handler',
            'test_socket.GeneralModuleTests.testInvalidInterfaceIndexToName',
        ]

        if WIN:
            disabled_tests += [
                'test_subprocess.ProcessTestCase.test_win32_duplicate_envs',
                'test_ssl.SimpleBackgroundTests.test_transport_eof',
                'test_ssl.SimpleBackgroundTests.test_bio_read_write_data',
                'test_ssl.SimpleBackgroundTests.test_bio_handshake',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_readline_without_limit',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_readline',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_read1_unbounded',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_read1_bounded',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_read1',
                'test_httplib.HeaderTests.test_ipv6host_header',
            ]

if PY312:
    disabled_tests += [
        # This test is new in 3.12.1; it appears to essentially rely
        # on blocking sockets to fully read data in one call, and our
        # version delivers a short initial read.
        'test_ssl.ThreadedTests.test_recv_into_buffer_protocol_len',
    ]

    if sys.version_info[:3] < (3, 12, 1):
        # Appveyor still has 3.12.0 when we added the 3.12.1 tests.
        # Some of them depend on changes to the stdlib/interpreter.
        disabled_tests += [
            'test_httplib.HeaderTests.test_ipv6host_header',
            'test_interpreters.TestInterpreterClose.test_subthreads_still_running',
            'test_interpreters.TestInterpreterIsRunning.test_main',
            'test_interpreters.TestInterpreterIsRunning.test_with_only_background_threads',
            'test_interpreters.TestInterpreterRun.test_with_background_threads_still_running',
            'test_interpreters.FinalizationTests.test_gh_109793',
            'test_interpreters.StartupTests.test_sys_path_0',
            'test_threading.SubinterpThreadingTests.test_threads_join_with_no_main',
            'test_threading.MiscTestCase.test_gh112826_missing__thread__is_main_interpreter',
        ]

    if RUN_COVERAGE:
        disabled_tests += [
            # This test wants to look for installed tracing functions, and
            # having a coverage tracer function installed breaks it.
            'test_threading.ThreadTests.test_gettrace_all_threads',
        ]

    if WIN:
        disabled_tests += [
            # These three are looking for an error string that matches,
            # and ours differs very slightly
            'test_socket.BasicHyperVTest.testCreateHyperVSocketAddrNotTupleFailure',
            'test_socket.BasicHyperVTest.testCreateHyperVSocketAddrServiceIdNotValidUUIDFailure',
            'test_socket.BasicHyperVTest.testCreateHyperVSocketAddrVmIdNotValidUUIDFailure',
        ]
        # Like the case for 3.12.1, these need VM or stdlib updates.
        if sys.version_info[:3] < (3, 12, 2):
            disabled_tests += [
                'test_socket.GeneralModuleTests.testInvalidInterfaceIndexToName',
                'test_subprocess.ProcessTestCase.test_win32_duplicate_envs',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_readline_without_limit',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_readline',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_read1_unbounded',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_read1_bounded',
                'test_httplib.ExtendedReadTestContentLengthKnown.test_read1',
            ]

    if LINUX and RUNNING_ON_CI:
        disabled_tests += [
            # These two try to forcibly close a socket, preventing some data
            # from reaching its destination. That works OK on some platforms, but
            # in this set of circumstances, because of the event loop, gevent is
            # able to send that data.
            'test_ssl.TestPreHandshakeClose.test_preauth_data_to_tls_client',
            'test_ssl.TestPreHandshakeClose.test_preauth_data_to_tls_server',
        ]

    if ARES:
        disabled_tests += [
            # c-ares doesn't like the IPv6 syntax it uses here.
            'test_socket.GeneralModuleTests.test_getaddrinfo_ipv6_scopeid_symbolic',
        ]

if TRAVIS:
    disabled_tests += [
        # These tests frequently break when we try to use newer Travis CI images,
        # due to different versions of OpenSSL being available. See above for some
        # specific examples. Usually the tests catch up, eventually (e.g., at this writing,
        # the 3.9b1 tests are fine on Ubuntu Bionic, but all other versions fail).
        'test_ssl.ContextTests.test_options',
        'test_ssl.ThreadedTests.test_alpn_protocols',
        'test_ssl.ThreadedTests.test_default_ecdh_curve',
        'test_ssl.ThreadedTests.test_shared_ciphers',

    ]

if RUNNING_ON_MUSLLINUX:
    disabled_tests += [
        # This is supposed to *not* crash, but on the muslilnux image, it
        # does crash (exitcode -11, ie, SIGSEGV)
        'test_threading.ThreadingExceptionTests.test_recursion_limit',
    ]


# Now build up the data structure we'll use to actually find disabled tests
# to avoid a linear scan for every file (it seems the list could get quite large)
# (First, freeze the source list to make sure it isn't modified anywhere)

def _build_test_structure(sequence_of_tests):

    _disabled_tests = frozenset(sequence_of_tests)

    disabled_tests_by_file = collections.defaultdict(set)
    for file_case_meth in _disabled_tests:
        file_name, _case, _meth = file_case_meth.split('.')

        by_file = disabled_tests_by_file[file_name]

        by_file.add(file_case_meth)

    return disabled_tests_by_file

_disabled_tests_by_file = _build_test_structure(disabled_tests)

_wrapped_tests_by_file = _build_test_structure(wrapped_tests)


def disable_tests_in_source(source, filename):
    # Source and filename are both native strings.

    if filename.startswith('./'):
        # turn "./test_socket.py" (used for auto-complete) into "test_socket.py"
        filename = filename[2:]

    if filename.endswith('.py'):
        filename = filename[:-3]


    # XXX ignoring TestCase class name (just using function name).
    # Maybe we should do this with the AST, or even after the test is
    # imported.
    my_disabled_tests = _disabled_tests_by_file.get(filename, ())
    my_wrapped_tests = _wrapped_tests_by_file.get(filename, {})


    if my_disabled_tests or my_wrapped_tests:
        # Insert our imports early in the file.
        # If we do it on a def-by-def basis, we can break syntax
        # if the function is already decorated
        pattern = r'^import .*'
        replacement = r'from gevent.testing import patched_tests_setup as _GEVENT_PTS;'
        replacement += r'import unittest as _GEVENT_UTS;'
        replacement += r'\g<0>'
        source, n = re.subn(pattern, replacement, source, 1, re.MULTILINE)

        print("Added imports", n)

    # Test cases will always be indented some,
    # so use [ \t]+. Without indentation, test_main, commonly used as the
    # __main__ function at the top level, could get matched. \s matches
    # newlines even in MULTILINE mode so it would still match that.
    my_disabled_testcases = set()
    for test in my_disabled_tests:
        testcase = test.split('.')[-1]
        my_disabled_testcases.add(testcase)
        # def foo_bar(self)
        # ->
        # @_GEVENT_UTS.skip('Removed by patched_tests_setup')
        # def foo_bar(self)
        pattern = r"^([ \t]+)def " + testcase
        replacement = r"\1@_GEVENT_UTS.skip('Removed by patched_tests_setup: %s')\n" % (test,)
        replacement += r"\g<0>"
        source, n = re.subn(pattern, replacement, source, 0, re.MULTILINE)
        print('Skipped %s (%d)' % (testcase, n), file=sys.stderr)


    for test in my_wrapped_tests:
        testcase = test.split('.')[-1]
        if testcase in my_disabled_testcases:
            print("Not wrapping %s because it is skipped" % (test,))
            continue

        # def foo_bar(self)
        # ->
        # @_GEVENT_PTS._PatchedTest('file.Case.name')
        # def foo_bar(self)
        pattern = r"^([ \t]+)def " + testcase
        replacement = r"\1@_GEVENT_PTS._PatchedTest('%s')\n" % (test,)
        replacement += r"\g<0>"

        source, n = re.subn(pattern, replacement, source, 0, re.MULTILINE)
        print('Wrapped %s (%d)' % (testcase, n), file=sys.stderr)

    return source
