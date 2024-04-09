#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
import gevent
from gevent import monkey

import os
import re

import unittest
import socket
from time import time
import traceback

import gevent.socket as gevent_socket
import gevent.testing as greentest

from gevent.testing import util
from gevent.testing.six import xrange
from gevent.testing import flaky
from gevent.testing.skipping import skipWithoutExternalNetwork


resolver = gevent.get_hub().resolver
util.debug('Resolver: %s', resolver)

if getattr(resolver, 'pool', None) is not None:
    resolver.pool.size = 1

from gevent.testing.sysinfo import RESOLVER_NOT_SYSTEM
from gevent.testing.sysinfo import RESOLVER_DNSPYTHON
from gevent.testing.sysinfo import RESOLVER_ARES
from gevent.testing.sysinfo import PY2
from gevent.testing.sysinfo import PYPY

import gevent.testing.timing


assert gevent_socket.gaierror is socket.gaierror
assert gevent_socket.error is socket.error


RUN_ALL_HOST_TESTS = os.getenv('GEVENTTEST_RUN_ALL_ETC_HOST_TESTS', '')


def add(klass, hostname, name=None,
        skip=None, skip_reason=None,
        require_equal_errors=True):

    call = callable(hostname)

    def _setattr(k, n, func):
        if skip:
            func = greentest.skipIf(skip, skip_reason,)(func)
        if not hasattr(k, n):
            setattr(k, n, func)

    if name is None:
        if call:
            name = hostname.__name__
        else:
            name = re.sub(r'[^\w]+', '_', repr(hostname))
        assert name, repr(hostname)

    def test_getaddrinfo_http(self):
        x = hostname() if call else hostname
        self._test('getaddrinfo', x, 'http',
                   require_equal_errors=require_equal_errors)
    test_getaddrinfo_http.__name__ = 'test_%s_getaddrinfo_http' % name
    _setattr(klass, test_getaddrinfo_http.__name__, test_getaddrinfo_http)

    def test_gethostbyname(self):
        x = hostname() if call else hostname
        ipaddr = self._test('gethostbyname', x,
                            require_equal_errors=require_equal_errors)
        if not isinstance(ipaddr, Exception):
            self._test('gethostbyaddr', ipaddr,
                       require_equal_errors=require_equal_errors)
    test_gethostbyname.__name__ = 'test_%s_gethostbyname' % name
    _setattr(klass, test_gethostbyname.__name__, test_gethostbyname)

    def test_gethostbyname_ex(self):
        x = hostname() if call else hostname
        self._test('gethostbyname_ex', x,
                   require_equal_errors=require_equal_errors)
    test_gethostbyname_ex.__name__ = 'test_%s_gethostbyname_ex' % name
    _setattr(klass, test_gethostbyname_ex.__name__, test_gethostbyname_ex)

    def test4(self):
        x = hostname() if call else hostname
        self._test('gethostbyaddr', x,
                   require_equal_errors=require_equal_errors)
    test4.__name__ = 'test_%s_gethostbyaddr' % name
    _setattr(klass, test4.__name__, test4)

    def test5(self):
        x = hostname() if call else hostname
        self._test('getnameinfo', (x, 80), 0,
                   require_equal_errors=require_equal_errors)
    test5.__name__ = 'test_%s_getnameinfo' % name
    _setattr(klass, test5.__name__, test5)

@skipWithoutExternalNetwork("Tries to resolve and compare hostnames/addrinfo")
class TestCase(greentest.TestCase):
    maxDiff = None
    __timeout__ = 30
    switch_expected = None

    TRACE = not util.QUIET and os.getenv('GEVENT_DEBUG', '') == 'trace'
    verbose_dns = TRACE

    def trace(self, message, *args, **kwargs):
        if self.TRACE:
            util.debug(message, *args, **kwargs)

    # Things that the stdlib should never raise and neither should we;
    # these indicate bugs in our code and we want to raise them.
    REAL_ERRORS = (AttributeError, ValueError, NameError)

    def __run_resolver(self, function, args):
        try:
            result = function(*args)
            assert not isinstance(result, BaseException), repr(result)
            return result
        except self.REAL_ERRORS:
            raise
        except Exception as ex: # pylint:disable=broad-except
            if self.TRACE:
                traceback.print_exc()
            return ex

    def __trace_call(self, result, runtime, function, *args):
        util.debug(self.__format_call(function, args))
        self.__trace_fresult(result, runtime)

    def __format_call(self, function, args):
        args = repr(args)
        if args.endswith(',)'):
            args = args[:-2] + ')'
        try:
            module = function.__module__.replace('gevent._socketcommon', 'gevent')
            name = function.__name__
            return '%s:%s%s' % (module, name, args)
        except AttributeError:
            return function + args

    def __trace_fresult(self, result, seconds):
        if isinstance(result, Exception):
            msg = '  -=>  raised %r' % (result, )
        else:
            msg = '  -=>  returned %r' % (result, )
        time_ms = ' %.2fms' % (seconds * 1000.0, )
        space = 80 - len(msg) - len(time_ms)
        if space > 0:
            space = ' ' * space
        else:
            space = ''
        util.debug(msg + space + time_ms)

    if not TRACE:
        def run_resolver(self, function, func_args):
            now = time()
            return self.__run_resolver(function, func_args), time() - now
    else:
        def run_resolver(self, function, func_args):
            self.trace(self.__format_call(function, func_args))
            delta = time()
            result = self.__run_resolver(function, func_args)
            delta = time() - delta
            self.__trace_fresult(result, delta)
            return result, delta

    def setUp(self):
        super(TestCase, self).setUp()
        if not self.verbose_dns:
            # Silence the default reporting of errors from the ThreadPool,
            # we handle those here.
            gevent.get_hub().exception_stream = None

    def tearDown(self):
        if not self.verbose_dns:
            try:
                del gevent.get_hub().exception_stream
            except AttributeError:
                pass # Happens under leak tests
        super(TestCase, self).tearDown()

    def should_log_results(self, result1, result2):
        if not self.verbose_dns:
            return False

        if isinstance(result1, BaseException) and isinstance(result2, BaseException):
            return type(result1) is not type(result2)
        return repr(result1) != repr(result2)

    def _test(self, func_name, *args, **kwargs):
        """
        Runs the function *func_name* with *args* and compares gevent and the system.

        Keyword arguments are passed to the function itself; variable args are
        used for the socket function.

        Returns the gevent result.
        """
        gevent_func = getattr(gevent_socket, func_name)
        real_func = monkey.get_original('socket', func_name)

        tester = getattr(self, '_run_test_' + func_name, self._run_test_generic)
        result = tester(func_name, real_func, gevent_func, args, **kwargs)
        _real_result, time_real, gevent_result, time_gevent = result

        if self.verbose_dns and time_gevent > time_real + 0.02 and time_gevent > 0.03:
            msg = 'gevent:%s%s took %dms versus %dms stdlib' % (
                func_name, args, time_gevent * 1000.0, time_real * 1000.0)

            if time_gevent > time_real + 1:
                word = 'VERY'
            else:
                word = 'quite'

            util.log('\nWARNING: %s slow: %s', word, msg, color='warning')

        return gevent_result

    def _run_test_generic(self, func_name, real_func, gevent_func, func_args,
                          require_equal_errors=True):
        real_result, time_real = self.run_resolver(real_func, func_args)
        gevent_result, time_gevent = self.run_resolver(gevent_func, func_args)
        if util.QUIET and self.should_log_results(real_result, gevent_result):
            util.log('')
            self.__trace_call(real_result, time_real, real_func, func_args)
            self.__trace_call(gevent_result, time_gevent, gevent_func, func_args)

        self.assertEqualResults(real_result, gevent_result, func_name,
                                require_equal_errors=require_equal_errors)
        return real_result, time_real, gevent_result, time_gevent

    def _normalize_result(self, result, func_name):
        norm_name = '_normalize_result_' + func_name
        if hasattr(self, norm_name):
            return getattr(self, norm_name)(result)
        return result

    NORMALIZE_GAI_IGNORE_CANONICAL_NAME = RESOLVER_ARES # It tends to return them even when not asked for
    if not RESOLVER_NOT_SYSTEM:
        def _normalize_result_getaddrinfo(self, result):
            return result
        def _normalize_result_gethostbyname_ex(self, result):
            return result
    else:
        def _normalize_result_gethostbyname_ex(self, result):
            # Often the second and third part of the tuple (hostname, aliaslist, ipaddrlist)
            # can be in different orders if we're hitting different servers,
            # or using the native and ares resolvers due to load-balancing techniques.
            # We sort them.
            if isinstance(result, BaseException):
                return result
            # result[1].sort() # we wind up discarding this

            # On Py2 in test_russion_gethostbyname_ex, this
            # is actually an integer, for some reason. In TestLocalhost.tets__ip6_localhost,
            # the result isn't this long (maybe an error?).
            try:
                result[2].sort()
            except AttributeError:
                pass
            except IndexError:
                return result
            # On some systems, a random alias is found in the aliaslist
            # by the system resolver, but not by cares, and vice versa. We deem the aliaslist
            # unimportant and discard it.
            # On some systems (Travis CI), the ipaddrlist for 'localhost' can come back
            # with two entries 127.0.0.1 (presumably two interfaces?) for c-ares
            ips = result[2]
            if ips == ['127.0.0.1', '127.0.0.1']:
                ips = ['127.0.0.1']
            # On some systems, the hostname can get caps
            return (result[0].lower(), [], ips)

        def _normalize_result_getaddrinfo(self, result):
            # Result is a list
            # (family, socktype, proto, canonname, sockaddr)
            # e.g.,
            # (AF_INET, SOCK_STREAM, IPPROTO_TCP, 'readthedocs.io', (127.0.0.1, 80))
            if isinstance(result, BaseException):
                return result

            # On Python 3, the builtin resolver can return SOCK_RAW results, but
            # c-ares doesn't do that. So we remove those if we find them.
            # Likewise, on certain Linux systems, even on Python 2, IPPROTO_SCTP (132)
            # results may be returned --- but that may not even have a constant in the
            # socket module! So to be safe, we strip out anything that's not
            # SOCK_STREAM or SOCK_DGRAM
            if isinstance(result, list):
                result = [
                    x
                    for x in result
                    if x[1] in (socket.SOCK_STREAM, socket.SOCK_DGRAM)
                    and x[2] in (socket.IPPROTO_TCP, socket.IPPROTO_UDP)
                ]

            if self.NORMALIZE_GAI_IGNORE_CANONICAL_NAME:
                result = [
                    (family, kind, proto, '', addr)
                    for family, kind, proto, _, addr
                    in result
                ]

            if isinstance(result, list):
                result.sort()
            return result

    def _normalize_result_getnameinfo(self, result):
        return result

    NORMALIZE_GHBA_IGNORE_ALIAS = False
    def _normalize_result_gethostbyaddr(self, result):
        if not RESOLVER_NOT_SYSTEM:
            return result

        if self.NORMALIZE_GHBA_IGNORE_ALIAS and isinstance(result, tuple):
            # On some systems, a random alias is found in the aliaslist
            # by the system resolver, but not by cares and vice versa. This is *probably* only the
            # case for localhost or things otherwise in /etc/hosts. We deem the aliaslist
            # unimportant and discard it.
            return (result[0], [], result[2])
        return result

    def _compare_exceptions_strict(self, real_result, gevent_result, func_name):
        if repr(real_result) == repr(gevent_result):
            # Catch things like `OverflowError('port must be 0-65535.',)```
            return

        msg = (func_name, 'system:', repr(real_result), 'gevent:', repr(gevent_result))
        self.assertIs(type(gevent_result), type(real_result), msg)

        if isinstance(real_result, TypeError):
            return

        if PYPY and isinstance(real_result, socket.herror):
            # PyPy doesn't do errno or multiple arguments in herror;
            # it just puts a string like 'host lookup failed: <thehost>';
            # it must be doing that manually.
            return

        self.assertEqual(real_result.args, gevent_result.args, msg)
        if hasattr(real_result, 'errno'):
            self.assertEqual(real_result.errno, gevent_result.errno)

    def _compare_exceptions_lenient(self, real_result, gevent_result, func_name):
        try:
            self._compare_exceptions_strict(real_result, gevent_result, func_name)
        except AssertionError:
            # Allow raising different things in a few rare cases.
            if (
                    func_name not in (
                        'getaddrinfo',
                        'gethostbyaddr',
                        'gethostbyname',
                        'gethostbyname_ex',
                        'getnameinfo',
                    )
                    or type(real_result) not in (socket.herror, socket.gaierror)
                    or type(gevent_result) not in (socket.herror, socket.gaierror, socket.error)
            ):
                raise
            util.log('WARNING: error type mismatch for %s: %r (gevent) != %r (stdlib)',
                     func_name,
                     gevent_result, real_result,
                     color='warning')

    _compare_exceptions = _compare_exceptions_lenient if RESOLVER_NOT_SYSTEM else _compare_exceptions_strict

    def _compare_results(self, real_result, gevent_result, func_name):
        if real_result == gevent_result:
            return True

        compare_func = getattr(self, '_compare_results_' + func_name,
                               self._generic_compare_results)
        return compare_func(real_result, gevent_result, func_name)

    def _generic_compare_results(self, real_result, gevent_result, func_name):
        try:
            if len(real_result) != len(gevent_result):
                return False
        except TypeError:
            return False

        return all(self._compare_results(x, y, func_name)
                   for (x, y)
                   in zip(real_result, gevent_result))

    def _compare_results_getaddrinfo(self, real_result, gevent_result, func_name):
        # On some systems, we find more results with
        # one resolver than we do with the other resolver.
        # So as long as they have some subset in common,
        # we'll take it.
        if not set(real_result).isdisjoint(set(gevent_result)):
            return True
        return self._generic_compare_results(real_result, gevent_result, func_name)

    def _compare_address_strings(self, a, b):
        # IPv6 address from different requests might be different
        a_segments = a.count(':')
        b_segments = b.count(':')
        if a_segments and b_segments:
            if a_segments == b_segments and a_segments in (4, 5, 6, 7):
                return True
            if a.rstrip(':').startswith(b.rstrip(':')) or b.rstrip(':').startswith(a.rstrip(':')):
                return True
            if a_segments >= 2 and b_segments >= 2 and a.split(':')[:2] == b.split(':')[:2]:
                return True

        return a.split('.', 1)[-1] == b.split('.', 1)[-1]

    def _compare_results_gethostbyname(self, real_result, gevent_result, _func_name):
        # Both strings.
        return self._compare_address_strings(real_result, gevent_result)

    def _compare_results_gethostbyname_ex(self, real_result, gevent_result, _func_name):
        # Results are IPv4 only:
        #   (hostname, [aliaslist], [ipaddrlist])
        # As for getaddrinfo, we'll just check the ipaddrlist has something in common.
        return not set(real_result[2]).isdisjoint(set(gevent_result[2]))

    def assertEqualResults(self, real_result, gevent_result, func_name,
                           require_equal_errors=True):
        errors = (
            OverflowError,
            TypeError,
            UnicodeError,
            socket.error,
            socket.gaierror,
            socket.herror,
        )
        if isinstance(real_result, errors) and isinstance(gevent_result, errors):
            if require_equal_errors:
                self._compare_exceptions(real_result, gevent_result, func_name)
            return

        real_result = self._normalize_result(real_result, func_name)
        gevent_result = self._normalize_result(gevent_result, func_name)

        if self._compare_results(real_result, gevent_result, func_name):
            return

        # If we're using a different resolver, allow the real resolver to generate an
        # error that the gevent resolver actually gets an answer to.
        if (
                RESOLVER_NOT_SYSTEM
                and isinstance(real_result, errors)
                and not isinstance(gevent_result, errors)
        ):
            return

        # On PyPy, socket.getnameinfo() can produce results even when the hostname resolves to
        # multiple addresses, like www.gevent.org does. DNSPython (and c-ares?) don't do that,
        # they refuse to pick a name and raise ``socket.error``
        if (
                RESOLVER_NOT_SYSTEM
                and PYPY
                and func_name == 'getnameinfo'
                and isinstance(gevent_result, socket.error)
                and not isinstance(real_result, socket.error)
        ):
            return


        # From 2.7 on, assertEqual does a better job highlighting the results than we would
        # because it calls assertSequenceEqual, which highlights the exact
        # difference in the tuple
        self.assertEqual(real_result, gevent_result)


class TestTypeError(TestCase):
    pass

add(TestTypeError, None)
add(TestTypeError, 25)


class TestHostname(TestCase):
    NORMALIZE_GHBA_IGNORE_ALIAS = True

    def __normalize_name(self, result):
        if (RESOLVER_ARES or RESOLVER_DNSPYTHON) and isinstance(result, tuple):
            # The system resolver can return the FQDN, in the first result,
            # when given certain configurations. But c-ares and dnspython
            # do not.
            name = result[0]
            name = name.split('.', 1)[0]
            result = (name,) + result[1:]
        return result

    def _normalize_result_gethostbyaddr(self, result):
        result = TestCase._normalize_result_gethostbyaddr(self, result)
        return self.__normalize_name(result)

    def _normalize_result_getnameinfo(self, result):
        result = TestCase._normalize_result_getnameinfo(self, result)
        if PY2:
            # Not sure why we only saw this on Python 2
            result = self.__normalize_name(result)
        return result

add(
    TestHostname,
    socket.gethostname,
    skip=greentest.RUNNING_ON_TRAVIS and greentest.RESOLVER_NOT_SYSTEM,
    skip_reason=("Sometimes get a different result for getaddrinfo "
                 "with dnspython; c-ares produces different results for "
                 "localhost on Travis beginning Sept 2019")
)


class TestLocalhost(TestCase):
    # certain tests in test_patched_socket.py only work if getaddrinfo('localhost') does not switch
    # (e.g. NetworkConnectionAttributesTest.testSourceAddress)
    #switch_expected = False
    # XXX: The above has been commented out for some time. Apparently this isn't the case
    # anymore.

    def _normalize_result_getaddrinfo(self, result):
        if RESOLVER_NOT_SYSTEM:
            # We see that some impls (OS X) return extra results
            # like DGRAM that ares does not.
            return ()
        return super(TestLocalhost, self)._normalize_result_getaddrinfo(result)

    NORMALIZE_GHBA_IGNORE_ALIAS = True
    if greentest.RUNNING_ON_TRAVIS and greentest.PY2 and RESOLVER_NOT_SYSTEM:
        def _normalize_result_gethostbyaddr(self, result):
            # Beginning in November 2017 after an upgrade to Travis,
            # we started seeing ares return ::1 for localhost, but
            # the system resolver is still returning 127.0.0.1 under Python 2
            result = super(TestLocalhost, self)._normalize_result_gethostbyaddr(result)
            if isinstance(result, tuple):
                result = (result[0], result[1], ['127.0.0.1'])
            return result


add(
    TestLocalhost, 'ip6-localhost',
    skip=RESOLVER_DNSPYTHON, # XXX: Fix these.
    skip_reason="Can return gaierror(-2)"
)
add(
    TestLocalhost, 'localhost',
    skip=greentest.RUNNING_ON_TRAVIS,
    skip_reason="Can return gaierror(-2)"
)




class TestNonexistent(TestCase):
    pass

add(TestNonexistent, 'nonexistentxxxyyy')


class Test1234(TestCase):
    pass

add(Test1234, '1.2.3.4')


class Test127001(TestCase):
    NORMALIZE_GHBA_IGNORE_ALIAS = True

add(
    Test127001, '127.0.0.1',
    # skip=RESOLVER_DNSPYTHON,
    # skip_reason="Beginning Dec 1 2017, ares started returning ip6-localhost "
    # "instead of localhost"
)



class TestBroadcast(TestCase):
    switch_expected = False

    if RESOLVER_DNSPYTHON:
        # dnspython raises errors for broadcasthost/255.255.255.255, but the system
        # can resolve it.

        @unittest.skip('ares raises errors for broadcasthost/255.255.255.255')
        def test__broadcast__gethostbyaddr(self):
            return

        test__broadcast__gethostbyname = test__broadcast__gethostbyaddr

add(TestBroadcast, '<broadcast>')


from gevent.resolver._hostsfile import HostsFile
class SanitizedHostsFile(HostsFile):
    def iter_all_host_addr_pairs(self):
        for name, addr in super(SanitizedHostsFile, self).iter_all_host_addr_pairs():
            if (RESOLVER_NOT_SYSTEM
                    and (name.endswith('local') # ignore bonjour, ares can't find them
                         # ignore common aliases that ares can't find
                         or addr == '255.255.255.255'
                         or name == 'broadcasthost'
                         # We get extra results from some impls, like OS X
                         # it returns DGRAM results
                         or name == 'localhost')):
                continue # pragma: no cover
            if name.endswith('local'):
                # These can only be found if bonjour is running,
                # and are very slow to do so with the system resolver on OS X
                continue
            yield name, addr


@greentest.skipIf(greentest.RUNNING_ON_CI,
                  "This sometimes randomly fails on Travis with ares and on appveyor, beginning Feb 13, 2018")
# Probably due to round-robin DNS,
# since this is not actually the system's etc hosts file.
# TODO: Rethink this. We need something reliable. Go back to using
# the system's etc hosts?
class TestEtcHosts(TestCase):

    MAX_HOSTS = int(os.getenv('GEVENTTEST_MAX_ETC_HOSTS', '10'))

    @classmethod
    def populate_tests(cls):
        hf = SanitizedHostsFile(os.path.join(os.path.dirname(__file__),
                                             'hosts_file.txt'))
        all_etc_hosts = sorted(hf.iter_all_host_addr_pairs())
        if len(all_etc_hosts) > cls.MAX_HOSTS and not RUN_ALL_HOST_TESTS:
            all_etc_hosts = all_etc_hosts[:cls.MAX_HOSTS]

        for host, ip in all_etc_hosts:
            add(cls, host)
            add(cls, ip)



TestEtcHosts.populate_tests()



class TestGeventOrg(TestCase):
    # For this test to work correctly, it needs to resolve to
    # an address with a single A record; round-robin DNS and multiple A records
    # may mess it up (subsequent requests---and we always make two---may return
    # unequal results). We used to use gevent.org, but that now has multiple A records;
    # trying www.gevent.org which is a CNAME to readthedocs.org then worked, but it became
    # an alias for python-gevent.readthedocs.org, which is an alias for readthedocs.io,
    # and which also has multiple addresses. So we run the resolver twice to try to get
    # the different answers, if needed.
    HOSTNAME = 'www.gevent.org'


    if RESOLVER_NOT_SYSTEM:
        def _normalize_result_gethostbyname(self, result):
            if result == '104.17.33.82':
                result = '104.17.32.82'
            return result

        def _normalize_result_gethostbyname_ex(self, result):
            result = super(TestGeventOrg, self)._normalize_result_gethostbyname_ex(result)
            if result[0] == 'python-gevent.readthedocs.org':
                result = ('readthedocs.io', ) + result[1:]
            return result

    def test_AI_CANONNAME(self):
        # Not all systems support AI_CANONNAME; notably tha manylinux
        # resolvers *sometimes* do not. Specifically, sometimes they
        # provide the canonical name *only* on the first result.

        args = (
            # host
            TestGeventOrg.HOSTNAME,
            # port
            None,
            # family
            socket.AF_INET,
            # type
            0,
            # proto
            0,
            # flags
            socket.AI_CANONNAME
        )
        gevent_result = gevent_socket.getaddrinfo(*args)
        self.assertEqual(gevent_result[0][3], 'readthedocs.io')
        real_result = socket.getaddrinfo(*args)

        self.NORMALIZE_GAI_IGNORE_CANONICAL_NAME = not all(r[3] for r in real_result)
        try:
            self.assertEqualResults(real_result, gevent_result, 'getaddrinfo')
        finally:
            del self.NORMALIZE_GAI_IGNORE_CANONICAL_NAME

add(TestGeventOrg, TestGeventOrg.HOSTNAME)


class TestFamily(TestCase):
    def test_inet(self):
        self._test('getaddrinfo', TestGeventOrg.HOSTNAME, None, socket.AF_INET)

    def test_unspec(self):
        self._test('getaddrinfo', TestGeventOrg.HOSTNAME, None, socket.AF_UNSPEC)

    def test_badvalue(self):
        self._test('getaddrinfo', TestGeventOrg.HOSTNAME, None, 255)
        self._test('getaddrinfo', TestGeventOrg.HOSTNAME, None, 255000)
        self._test('getaddrinfo', TestGeventOrg.HOSTNAME, None, -1)

    @unittest.skipIf(RESOLVER_DNSPYTHON, "Raises the wrong errno")
    def test_badtype(self):
        self._test('getaddrinfo', TestGeventOrg.HOSTNAME, 'x')


class Test_getaddrinfo(TestCase):

    def _test_getaddrinfo(self, *args):
        self._test('getaddrinfo', *args)

    def test_80(self):
        self._test_getaddrinfo(TestGeventOrg.HOSTNAME, 80)

    def test_int_string(self):
        self._test_getaddrinfo(TestGeventOrg.HOSTNAME, '80')

    def test_0(self):
        self._test_getaddrinfo(TestGeventOrg.HOSTNAME, 0)

    def test_http(self):
        self._test_getaddrinfo(TestGeventOrg.HOSTNAME, 'http')

    def test_notexistent_tld(self):
        self._test_getaddrinfo('myhost.mytld', 53)

    def test_notexistent_dot_com(self):
        self._test_getaddrinfo('sdfsdfgu5e66098032453245wfdggd.com', 80)

    def test1(self):
        return self._test_getaddrinfo(TestGeventOrg.HOSTNAME, 52, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, 0)

    def test2(self):
        return self._test_getaddrinfo(TestGeventOrg.HOSTNAME, 53, socket.AF_INET, socket.SOCK_DGRAM, 17)

    @unittest.skipIf(RESOLVER_DNSPYTHON,
                     "dnspython only returns some of the possibilities")
    def test3(self):
        return self._test_getaddrinfo('google.com', 'http', socket.AF_INET6)


    @greentest.skipIf(PY2, "Enums only on Python 3.4+")
    def test_enums(self):
        # https://github.com/gevent/gevent/issues/1310

        # On Python 3, getaddrinfo does special things to make sure that
        # the fancy enums are returned.

        gai = gevent_socket.getaddrinfo('example.com', 80,
                                        socket.AF_INET,
                                        socket.SOCK_STREAM, socket.IPPROTO_TCP)
        af, socktype, _proto, _canonname, _sa = gai[0]
        self.assertIs(socktype, socket.SOCK_STREAM)
        self.assertIs(af, socket.AF_INET)

class TestInternational(TestCase):
    if PY2:
        # We expect these to raise UnicodeEncodeError, which is a
        # subclass of ValueError
        REAL_ERRORS = set(TestCase.REAL_ERRORS) - {ValueError,}

        if RESOLVER_ARES:

            def test_russian_getaddrinfo_http(self):
                # And somehow, test_russion_getaddrinfo_http (``getaddrinfo(name, 'http')``)
                # manages to work with recent versions of Python 2, but our preemptive encoding
                # to ASCII causes it to fail with the c-ares resolver; but only that one test out of
                # all of them.
                self.skipTest("ares fails to encode.")


# dns python can actually resolve these: it uses
# the 2008 version of idna encoding, whereas on Python 2,
# with the default resolver, it tries to encode to ascii and
# raises a UnicodeEncodeError. So we get different results.

# Starting 20221027, on GitHub Actions and *some* versions of Python,
# we started getting a different error result from our own resolver
# compared to the system. This is very weird because our own resolver
# calls the system. I can't reproduce locally. Perhaps the two
# different answers are because of caching? One from the real DNS
# server, one from the local resolver library? Hence
# require_equal_errors=False
# ('system:', "herror(2, 'Host name lookup failure')",
#  'gevent:', "herror(1, 'Unknown host')")
add(TestInternational, u'президент.рф', 'russian',
    skip=(PY2 and RESOLVER_DNSPYTHON),
    skip_reason="dnspython can actually resolve these",
    require_equal_errors=False)
add(TestInternational, u'президент.рф'.encode('idna'), 'idna',
    require_equal_errors=False)

@skipWithoutExternalNetwork("Tries to resolve and compare hostnames/addrinfo")
class TestInterrupted_gethostbyname(gevent.testing.timing.AbstractGenericWaitTestCase):

    # There are refs to a Waiter in the C code that don't go
    # away yet; one gc may or may not do it.
    @greentest.ignores_leakcheck
    def test_returns_none_after_timeout(self):
        super(TestInterrupted_gethostbyname, self).test_returns_none_after_timeout()

    def wait(self, timeout):
        with gevent.Timeout(timeout, False):
            for index in xrange(1000000):
                try:
                    gevent_socket.gethostbyname('www.x%s.com' % index)
                except socket.error:
                    pass
            raise AssertionError('Timeout was not raised')

    def cleanup(self):
        # Depending on timing, this can raise:
        # (This suddenly started happening on Apr 6 2016; www.x1000000.com
        # is apparently no longer around)

        #    File "test__socket_dns.py", line 538, in cleanup
        #     gevent.get_hub().threadpool.join()
        #   File "/home/travis/build/gevent/gevent/src/gevent/threadpool.py", line 108, in join
        #     sleep(delay)
        #   File "/home/travis/build/gevent/gevent/src/gevent/hub.py", line 169, in sleep
        #     hub.wait(loop.timer(seconds, ref=ref))
        #   File "/home/travis/build/gevent/gevent/src/gevent/hub.py", line 651, in wait
        #     result = waiter.get()
        #   File "/home/travis/build/gevent/gevent/src/gevent/hub.py", line 899, in get
        #     return self.hub.switch()
        #   File "/home/travis/build/gevent/gevent/src/greentest/greentest.py", line 520, in switch
        #     return _original_Hub.switch(self, *args)
        #   File "/home/travis/build/gevent/gevent/src/gevent/hub.py", line 630, in switch
        #     return RawGreenlet.switch(self)
        # gaierror: [Errno -2] Name or service not known
        try:
            gevent.get_hub().threadpool.join()
        except Exception: # pragma: no cover pylint:disable=broad-except
            traceback.print_exc()


# class TestInterrupted_getaddrinfo(greentest.GenericWaitTestCase):
#
#     def wait(self, timeout):
#         with gevent.Timeout(timeout, False):
#             for index in range(1000):
#                 try:
#                     gevent_socket.getaddrinfo('www.a%s.com' % index, 'http')
#                 except socket.gaierror:
#                     pass


class TestBadName(TestCase):
    pass

add(TestBadName, 'xxxxxxxxxxxx')

class TestBadIP(TestCase):
    pass

add(TestBadIP, '1.2.3.400')


@greentest.skipIf(greentest.RUNNING_ON_TRAVIS, "Travis began returning ip6-localhost")
class Test_getnameinfo_127001(TestCase):

    def test(self):
        self._test('getnameinfo', ('127.0.0.1', 80), 0)

    def test_DGRAM(self):
        self._test('getnameinfo', ('127.0.0.1', 779), 0)
        self._test('getnameinfo', ('127.0.0.1', 779), socket.NI_DGRAM)

    def test_NOFQDN(self):
        # I get ('localhost', 'www') with _socket but ('localhost.localdomain', 'www') with gevent.socket
        self._test('getnameinfo', ('127.0.0.1', 80), socket.NI_NOFQDN)

    def test_NAMEREQD(self):
        self._test('getnameinfo', ('127.0.0.1', 80), socket.NI_NAMEREQD)


class Test_getnameinfo_geventorg(TestCase):

    @unittest.skipIf(RESOLVER_DNSPYTHON,
                     "dnspython raises an error when multiple results are returned")
    def test_NUMERICHOST(self):
        self._test('getnameinfo', (TestGeventOrg.HOSTNAME, 80), 0)
        self._test('getnameinfo', (TestGeventOrg.HOSTNAME, 80), socket.NI_NUMERICHOST)

    @unittest.skipIf(RESOLVER_DNSPYTHON,
                     "dnspython raises an error when multiple results are returned")
    def test_NUMERICSERV(self):
        self._test('getnameinfo', (TestGeventOrg.HOSTNAME, 80), socket.NI_NUMERICSERV)

    def test_domain1(self):
        self._test('getnameinfo', (TestGeventOrg.HOSTNAME, 80), 0)

    def test_domain2(self):
        self._test('getnameinfo', ('www.gevent.org', 80), 0)

    def test_port_zero(self):
        self._test('getnameinfo', ('www.gevent.org', 0), 0)


class Test_getnameinfo_fail(TestCase):

    def test_port_string(self):
        self._test('getnameinfo', ('www.gevent.org', 'http'), 0)

    def test_bad_flags(self):
        self._test('getnameinfo', ('localhost', 80), 55555555)


class TestInvalidPort(TestCase):

    @flaky.reraises_flaky_race_condition()
    def test_overflow_neg_one(self):
        # An Appveyor beginning 2019-03-21, the system resolver
        # sometimes returns ('23.100.69.251', '65535') instead of
        # raising an error. That IP address belongs to
        # readthedocs[.io?] which is where www.gevent.org is a CNAME
        # to...but it doesn't actually *reverse* to readthedocs.io.
        # Can't reproduce locally, not sure what's happening
        self._test('getnameinfo', ('www.gevent.org', -1), 0)

    # Beginning with PyPy 2.7 7.1 on Appveyor, we sometimes see this
    # return an OverflowError instead of the TypeError about None
    @greentest.skipOnLibuvOnPyPyOnWin("Errors dont match")
    def test_typeerror_none(self):
        self._test('getnameinfo', ('www.gevent.org', None), 0)

    # Beginning with PyPy 2.7 7.1 on Appveyor, we sometimes see this
    # return an TypeError instead of the OverflowError.
    # XXX: But see Test_getnameinfo_fail.test_port_string where this does work.
    @greentest.skipOnLibuvOnPyPyOnWin("Errors don't match")
    def test_typeerror_str(self):
        self._test('getnameinfo', ('www.gevent.org', 'x'), 0)

    def test_overflow_port_too_large(self):
        self._test('getnameinfo', ('www.gevent.org', 65536), 0)


if __name__ == '__main__':
    greentest.main()
