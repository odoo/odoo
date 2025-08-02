#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

import socket
import unittest

import gevent.testing as greentest
from gevent.tests.test__socket_dns import TestCase, add

from gevent.testing.sysinfo import OSX
from gevent.testing.sysinfo import RESOLVER_DNSPYTHON
from gevent.testing.sysinfo import RESOLVER_ARES
from gevent.testing.sysinfo import PYPY
from gevent.testing.sysinfo import PY2

# We can't control the DNS servers on CI (or in general...)
# for the system. This works best with the google DNS servers
# The getnameinfo test can fail on CI.

# Previously only Test6_ds failed, but as of Jan 2018, Test6
# and Test6_google begin to fail:

# First differing element 0:
# 'vm2.test-ipv6.com'
# 'ip119.gigo.com'

# - ('vm2.test-ipv6.com', [], ['2001:470:1:18::125'])
# ?   ---------  ^^                             ^^

# + ('ip119.gigo.com', [], ['2001:470:1:18::119'])
# ?     ^^^^^^^^                             ^^

# These are known to work on jamadden's OS X machine using the google
# resolvers (but not with DNSPython; things don't *quite* match)...so
# by default we skip the tests everywhere else.

class Test6(TestCase):
    NORMALIZE_GHBA_IGNORE_ALIAS = True
    # host that only has AAAA record
    host = 'aaaa.test-ipv6.com'

    def _normalize_result_gethostbyaddr(self, result):
        # This part of the test is effectively disabled. There are multiple address
        # that resolve and which ones you get depend on the settings
        # of the system and ares. They don't match exactly.
        return ()

    if RESOLVER_ARES and PY2:
        def _normalize_result_getnameinfo(self, result):
            # Beginning 2020-07-23,
            # c-ares returns a scope id on the result:
            #    ('2001:470:1:18::115%0', 'http')
            # The standard library does not (on linux or os x).
            # I've only seen '%0', so only remove that
            ipaddr, service = result
            if ipaddr.endswith('%0'):
                ipaddr = ipaddr[:-2]
            return (ipaddr, service)

    if not OSX and RESOLVER_DNSPYTHON:
        # It raises gaierror instead of socket.error,
        # which is not great and leads to failures.
        def _run_test_getnameinfo(self, *_args, **_kwargs):
            return (), 0, (), 0

    def _run_test_gethostbyname(self, *_args, **_kwargs):
        raise unittest.SkipTest("gethostbyname[_ex] does not support IPV6")

    _run_test_gethostbyname_ex = _run_test_gethostbyname

    def test_empty(self):
        self._test('getaddrinfo', self.host, 'http')

    def test_inet(self):
        self._test('getaddrinfo', self.host, None, socket.AF_INET)

    def test_inet6(self):
        self._test('getaddrinfo', self.host, None, socket.AF_INET6)

    def test_unspec(self):
        self._test('getaddrinfo', self.host, None, socket.AF_UNSPEC)


class Test6_google(Test6):
    host = 'ipv6.google.com'

    if greentest.RUNNING_ON_CI:
        # Disabled, there are multiple possibilities
        # and we can get different ones. Even the system resolvers
        # can go round-robin and provide different answers.
        def _normalize_result_getnameinfo(self, result):
            return ()

        if PYPY:
            # PyPy tends to be especially problematic in that area.
            _normalize_result_getaddrinfo = _normalize_result_getnameinfo

add(Test6, Test6.host)
add(Test6_google, Test6_google.host)



class Test6_ds(Test6):
    # host that has both A and AAAA records
    host = 'ds.test-ipv6.com'

    _normalize_result_gethostbyname = Test6._normalize_result_gethostbyaddr

add(Test6_ds, Test6_ds.host)


if __name__ == '__main__':
    greentest.main()
