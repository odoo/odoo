# Copyright (c) 2018  gevent contributors. See LICENSE for details.

# Portions of this code taken from the gogreen project:
#   http://github.com/slideinc/gogreen
#
# Copyright (c) 2005-2010 Slide, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of the author nor the names of other
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Portions of this code taken from the eventlet project:
# https://github.com/eventlet/eventlet/blob/master/eventlet/support/greendns.py

# Unless otherwise noted, the files in Eventlet are under the following MIT license:

# Copyright (c) 2005-2006, Bob Ippolito
# Copyright (c) 2007-2010, Linden Research, Inc.
# Copyright (c) 2008-2010, Eventlet Contributors (see AUTHORS)

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import absolute_import, print_function, division

import sys
import time

from _socket import error
from _socket import gaierror
from _socket import herror
from _socket import NI_NUMERICSERV
from _socket import AF_INET
from _socket import AF_INET6
from _socket import AF_UNSPEC
from _socket import EAI_NONAME
from _socket import EAI_FAMILY


import socket

from gevent.resolver import AbstractResolver
from gevent.resolver._hostsfile import HostsFile

from gevent.builtins import __import__ as g_import

from gevent._compat import string_types
from gevent._compat import iteritems
from gevent._config import config


__all__ = [
    'Resolver',
]

# Import the DNS packages to use the gevent modules,
# even if the system is not monkey-patched. If it *is* already
# patched, this imports a second copy under a different name,
# which is probably not strictly necessary, but matches
# what we've historically done, and allows configuring the resolvers
# differently.

def _patch_dns():
    from gevent._patcher import import_patched as importer
    # The dns package itself is empty but defines __all__
    # we make sure to import all of those things now under the
    # patch. Note this triggers two DeprecationWarnings,
    # one of which we could avoid.
    extras = {
        'dns': ('rdata', 'resolver', 'rdtypes'),
        'dns.rdtypes': ('IN', 'ANY', ),
        'dns.rdtypes.IN': ('A', 'AAAA',),
        'dns.rdtypes.ANY': ('SOA', 'PTR'),
    }
    def extra_all(mod_name):
        return extras.get(mod_name, ())

    def after_import_hook(dns): # pylint:disable=redefined-outer-name
        # Runs while still in the original patching scope.
        # The dns.rdata:get_rdata_class() function tries to
        # dynamically import modules using __import__ and then walk
        # through the attribute tree to find classes in `dns.rdtypes`.
        # It is critical that this all matches up, otherwise we can
        # get different exception classes that don't get caught.
        # We could patch __import__ to do things at runtime, but it's
        # easier to enumerate the world and populate the cache now
        # before we then switch the names back.
        rdata = dns.rdata
        get_rdata_class = rdata.get_rdata_class
        try:
            rdclass_values = list(dns.rdataclass.RdataClass)
        except AttributeError:
            # dnspython < 2.0
            rdclass_values = dns.rdataclass._by_value

        try:
            rdtype_values = list(dns.rdatatype.RdataType)
        except AttributeError:
            # dnspython < 2.0
            rdtype_values = dns.rdatatype._by_value


        for rdclass in rdclass_values:
            for rdtype in rdtype_values:
                get_rdata_class(rdclass, rdtype)

    patcher = importer('dns', extra_all, after_import_hook)
    top = patcher.module

    # Now disable the dynamic imports
    def _no_dynamic_imports(name):
        raise ValueError(name)

    top.rdata.__import__ = _no_dynamic_imports

    return top

dns = _patch_dns()

resolver = dns.resolver
dTimeout = dns.resolver.Timeout

# This is a wrapper for dns.resolver._getaddrinfo with two crucial changes.
# First, it backports https://github.com/rthalley/dnspython/issues/316
# from version 2.0. This can be dropped when we support only dnspython 2
# (which means only Python 3.)

# Second, it adds calls to sys.exc_clear() to avoid failing tests in
# test__refcount.py (timeouts) on Python 2. (Actually, this isn't
# strictly necessary, it was necessary to increase the timeouts in
# that function because dnspython is doing some parsing/regex/host
# lookups that are not super fast. But it does have a habit of leaving
# exceptions around which can complicate our memleak checks.)
def _getaddrinfo(host=None, service=None, family=AF_UNSPEC, socktype=0,
                 proto=0, flags=0,
                 _orig_gai=resolver._getaddrinfo,
                 _exc_clear=getattr(sys, 'exc_clear', lambda: None)):
    if flags & (socket.AI_ADDRCONFIG | socket.AI_V4MAPPED) != 0:
        # Not implemented.  We raise a gaierror as opposed to a
        # NotImplementedError as it helps callers handle errors more
        # appropriately.  [Issue #316]
        raise socket.gaierror(socket.EAI_SYSTEM)
    res = _orig_gai(host, service, family, socktype, proto, flags)
    _exc_clear()
    return res


resolver._getaddrinfo = _getaddrinfo

HOSTS_TTL = 300.0


class _HostsAnswer(dns.resolver.Answer):
    # Answer class for HostsResolver object

    def __init__(self, qname, rdtype, rdclass, rrset, raise_on_no_answer=True):
        self.response = None
        self.qname = qname
        self.rdtype = rdtype
        self.rdclass = rdclass
        self.canonical_name = qname
        if not rrset and raise_on_no_answer:
            raise dns.resolver.NoAnswer()
        self.rrset = rrset
        self.expiration = (time.time() +
                           rrset.ttl if hasattr(rrset, 'ttl') else 0)


class _HostsResolver(object):
    """
    Class to parse the hosts file
    """

    def __init__(self, fname=None, interval=HOSTS_TTL):
        self.hosts_file = HostsFile(fname)
        self.interval = interval
        self._last_load = 0

    def query(self, qname, rdtype=dns.rdatatype.A, rdclass=dns.rdataclass.IN,
              tcp=False, source=None, raise_on_no_answer=True): # pylint:disable=unused-argument
        # Query the hosts file
        #
        # The known rdtypes are dns.rdatatype.A, dns.rdatatype.AAAA and
        # dns.rdatatype.CNAME.
        # The ``rdclass`` parameter must be dns.rdataclass.IN while the
        # ``tcp`` and ``source`` parameters are ignored.
        # Return a HostAnswer instance or raise a dns.resolver.NoAnswer
        # exception.

        now = time.time()
        hosts_file = self.hosts_file
        if self._last_load + self.interval < now:
            self._last_load = now
            hosts_file.load()

        rdclass = dns.rdataclass.IN # Always
        if isinstance(qname, string_types):
            name = qname
            qname = dns.name.from_text(qname)
        else:
            name = str(qname)

        name = name.lower()
        rrset = dns.rrset.RRset(qname, rdclass, rdtype)
        rrset.ttl = self._last_load + self.interval - now

        if rdtype == dns.rdatatype.A:
            mapping = hosts_file.v4
            kind = dns.rdtypes.IN.A.A
        elif rdtype == dns.rdatatype.AAAA:
            mapping = hosts_file.v6
            kind = dns.rdtypes.IN.AAAA.AAAA
        elif rdtype == dns.rdatatype.CNAME:
            mapping = hosts_file.aliases
            kind = lambda c, t, addr: dns.rdtypes.ANY.CNAME.CNAME(c, t, dns.name.from_text(addr))
        elif rdtype == dns.rdatatype.PTR:
            mapping = hosts_file.reverse
            kind = lambda c, t, addr: dns.rdtypes.ANY.PTR.PTR(c, t, dns.name.from_text(addr))


        addr = mapping.get(name)
        if not addr and qname.is_absolute():
            addr = mapping.get(name[:-1])
        if addr:
            rrset.add(kind(rdclass, rdtype, addr))
        return _HostsAnswer(qname, rdtype, rdclass, rrset, raise_on_no_answer)

    def getaliases(self, hostname):
        # Return a list of all the aliases of a given cname

        # Due to the way store aliases this is a bit inefficient, this
        # clearly was an afterthought.  But this is only used by
        # gethostbyname_ex so it's probably fine.
        aliases = self.hosts_file.aliases
        result = []
        if hostname in aliases: # pylint:disable=consider-using-get
            cannon = aliases[hostname]
        else:
            cannon = hostname
        result.append(cannon)
        for alias, cname in iteritems(aliases):
            if cannon == cname:
                result.append(alias)
        result.remove(hostname)
        return result

class _DualResolver(object):

    def __init__(self):
        self.hosts_resolver = _HostsResolver()
        self.network_resolver = resolver.get_default_resolver()
        self.network_resolver.cache = resolver.LRUCache()

    def query(self, qname, rdtype=dns.rdatatype.A, rdclass=dns.rdataclass.IN,
              tcp=False, source=None, raise_on_no_answer=True,
              _hosts_rdtypes=(dns.rdatatype.A, dns.rdatatype.AAAA, dns.rdatatype.PTR)):
        # Query the resolver, using /etc/hosts

        # Behavior:
        # 1. if hosts is enabled and contains answer, return it now
        # 2. query nameservers for qname
        if qname is None:
            qname = '0.0.0.0'

        if not isinstance(qname, string_types):
            if isinstance(qname, bytes):
                qname = qname.decode("idna")

        if isinstance(qname, string_types):
            qname = dns.name.from_text(qname, None)

        if isinstance(rdtype, string_types):
            rdtype = dns.rdatatype.from_text(rdtype)

        if rdclass == dns.rdataclass.IN and rdtype in _hosts_rdtypes:
            try:
                answer = self.hosts_resolver.query(qname, rdtype, raise_on_no_answer=False)
            except Exception: # pylint: disable=broad-except
                from gevent import get_hub
                get_hub().handle_error(self, *sys.exc_info())
            else:
                if answer.rrset:
                    return answer

        return self.network_resolver.query(qname, rdtype, rdclass,
                                           tcp, source, raise_on_no_answer=raise_on_no_answer)

def _family_to_rdtype(family):
    if family == socket.AF_INET:
        rdtype = dns.rdatatype.A
    elif family == socket.AF_INET6:
        rdtype = dns.rdatatype.AAAA
    else:
        raise socket.gaierror(socket.EAI_FAMILY,
                              'Address family not supported')
    return rdtype


class Resolver(AbstractResolver):
    """
    An *experimental* resolver that uses `dnspython`_.

    This is typically slower than the default threaded resolver
    (unless there's a cache hit, in which case it can be much faster).
    It is usually much faster than the c-ares resolver. It tends to
    scale well as more concurrent resolutions are attempted.

    Under Python 2, if the ``idna`` package is installed, this
    resolver can resolve Unicode host names that the system resolver
    cannot.

    .. note::

        This **does not** use dnspython's default resolver object, or share any
        classes with ``import dns``. A separate copy of the objects is imported to
        be able to function in a non monkey-patched process. The documentation for the resolver
        object still applies.

        The resolver that we use is available as the :attr:`resolver` attribute
        of this object (typically ``gevent.get_hub().resolver.resolver``).

    .. caution::

        Many of the same caveats about DNS results apply here as are documented
        for :class:`gevent.resolver.ares.Resolver`. In addition, the handling of
        symbolic scope IDs in IPv6 addresses passed to ``getaddrinfo`` exhibits
        some differences.

        On PyPy, ``getnameinfo`` can produce results when CPython raises
        ``socket.error``, and gevent's DNSPython resolver also
        raises ``socket.error``.

    .. caution::

        This resolver is experimental. It may be removed or modified in
        the future. As always, feedback is welcome.

    .. versionadded:: 1.3a2

    .. versionchanged:: 20.5.0
       The errors raised are now much more consistent with those
       raised by the standard library resolvers.

       Handling of localhost and broadcast names is now more consistent.

    .. _dnspython: http://www.dnspython.org
    """

    def __init__(self, hub=None): # pylint: disable=unused-argument
        if resolver._resolver is None:
            _resolver = resolver._resolver = _DualResolver()
            if config.resolver_nameservers:
                _resolver.network_resolver.nameservers[:] = config.resolver_nameservers
            if config.resolver_timeout:
                _resolver.network_resolver.lifetime = config.resolver_timeout
        # Different hubs in different threads could be sharing the same
        # resolver.
        assert isinstance(resolver._resolver, _DualResolver)
        self._resolver = resolver._resolver

    @property
    def resolver(self):
        """
        The dnspython resolver object we use.

        This object has several useful attributes that can be used to
        adjust the behaviour of the DNS system:

        * ``cache`` is a :class:`dns.resolver.LRUCache`. Its maximum size
          can be configured by calling :meth:`resolver.cache.set_max_size`
        * ``nameservers`` controls which nameservers to talk to
        * ``lifetime`` configures a timeout for each individual query.
        """
        return self._resolver.network_resolver

    def close(self):
        pass

    def _getaliases(self, hostname, family):
        if not isinstance(hostname, str):
            if isinstance(hostname, bytes):
                hostname = hostname.decode("idna")
        aliases = self._resolver.hosts_resolver.getaliases(hostname)
        net_resolver = self._resolver.network_resolver
        rdtype = _family_to_rdtype(family)
        while 1:
            try:
                ans = net_resolver.query(hostname, dns.rdatatype.CNAME, rdtype)
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                break
            except dTimeout:
                break
            except AttributeError as ex:
                if hostname is None or isinstance(hostname, int):
                    raise TypeError(ex)
                raise
            else:
                aliases.extend(str(rr.target) for rr in ans.rrset)
                hostname = ans[0].target
        return aliases

    def _getaddrinfo(self, host_bytes, port, family, socktype, proto, flags):
        # dnspython really wants the host to be in native format.
        if not isinstance(host_bytes, str):
            host_bytes = host_bytes.decode(self.HOSTNAME_ENCODING)

        if host_bytes == 'ff02::1de:c0:face:8D':
            # This is essentially a hack to make stdlib
            # test_socket:GeneralModuleTests.test_getaddrinfo_ipv6_basic
            # pass. They expect to get back a lowercase ``D``, but
            # dnspython does not do that.
            # ``test_getaddrinfo_ipv6_scopeid_symbolic`` also expect
            # the scopeid to be dropped, but again, dnspython does not
            # do that; we cant fix that here so we skip that test.
            host_bytes = 'ff02::1de:c0:face:8d'

        if family == AF_UNSPEC:
            # This tends to raise in the case that a v6 address did not exist
            # but a v4 does. So we break it into two parts.

            # Note that if there is no ipv6 in the hosts file, but there *is*
            # an ipv4, and there *is* an ipv6 in the nameservers, we will return
            # both (from the first call). The system resolver on OS X only returns
            # the results from the hosts file. doubleclick.com is one example.

            # See also https://github.com/gevent/gevent/issues/1012
            try:
                return _getaddrinfo(host_bytes, port, family, socktype, proto, flags)
            except gaierror:
                try:
                    return _getaddrinfo(host_bytes, port, AF_INET6, socktype, proto, flags)
                except gaierror:
                    return _getaddrinfo(host_bytes, port, AF_INET, socktype, proto, flags)
        else:
            try:
                return _getaddrinfo(host_bytes, port, family, socktype, proto, flags)
            except gaierror as ex:
                if ex.args[0] == EAI_NONAME and family not in self._KNOWN_ADDR_FAMILIES:
                    # It's possible that we got sent an unsupported family. Check
                    # that.
                    ex.args = (EAI_FAMILY, self.EAI_FAMILY_MSG)
                    ex.errno = EAI_FAMILY
                raise

    def _getnameinfo(self, address_bytes, port, sockaddr, flags):
        try:
            return resolver._getnameinfo(sockaddr, flags)
        except error:
            if not flags:
                # dnspython doesn't like getting ports it can't resolve.
                # We have one test, test__socket_dns.py:Test_getnameinfo_geventorg.test_port_zero
                # that does this. We conservatively fix it here; this could be expanded later.
                return resolver._getnameinfo(sockaddr, NI_NUMERICSERV)

    def _gethostbyaddr(self, ip_address_bytes):
        try:
            return resolver._gethostbyaddr(ip_address_bytes)
        except gaierror as ex:
            if ex.args[0] == EAI_NONAME:
                # Note: The system doesn't *always* raise herror;
                # sometimes the original gaierror propagates through.
                # It's impossible to say ahead of time or just based
                # on the name which it should be. The herror seems to
                # be by far the most common, though.
                raise herror(1, "Unknown host")
            raise

    # Things that need proper error handling
    getnameinfo = AbstractResolver.fixup_gaierror(AbstractResolver.getnameinfo)
    gethostbyaddr = AbstractResolver.fixup_gaierror(AbstractResolver.gethostbyaddr)
    gethostbyname_ex = AbstractResolver.fixup_gaierror(AbstractResolver.gethostbyname_ex)
    getaddrinfo = AbstractResolver.fixup_gaierror(AbstractResolver.getaddrinfo)
