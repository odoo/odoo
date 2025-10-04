# Copyright (c) 2018  gevent contributors. See LICENSE for details.

import _socket
from _socket import AF_INET
from _socket import AF_UNSPEC
from _socket import AI_CANONNAME
from _socket import AI_PASSIVE
from _socket import AI_NUMERICHOST
from _socket import EAI_NONAME
from _socket import EAI_SERVICE
from _socket import SOCK_DGRAM
from _socket import SOCK_STREAM
from _socket import SOL_TCP
from _socket import error
from _socket import gaierror
from _socket import getaddrinfo as native_getaddrinfo
from _socket import getnameinfo as native_getnameinfo
from _socket import gethostbyaddr as native_gethostbyaddr
from _socket import gethostbyname as native_gethostbyname
from _socket import gethostbyname_ex as native_gethostbyname_ex
from _socket import getservbyname as native_getservbyname


from gevent._compat import string_types
from gevent._compat import text_type
from gevent._compat import hostname_types
from gevent._compat import integer_types
from gevent._compat import PYPY
from gevent._compat import MAC

from gevent.resolver._addresses import is_ipv6_addr
# Nothing public here.
__all__ = ()

# trigger import of encodings.idna to avoid https://github.com/gevent/gevent/issues/349
u'foo'.encode('idna')


def _lookup_port(port, socktype):
    # pylint:disable=too-many-branches
    socktypes = []
    if isinstance(port, string_types):
        try:
            port = int(port)
        except ValueError:
            try:
                if socktype == 0:
                    origport = port
                    try:
                        port = native_getservbyname(port, 'tcp')
                        socktypes.append(SOCK_STREAM)
                    except error:
                        port = native_getservbyname(port, 'udp')
                        socktypes.append(SOCK_DGRAM)
                    else:
                        try:
                            if port == native_getservbyname(origport, 'udp'):
                                socktypes.append(SOCK_DGRAM)
                        except error:
                            pass
                elif socktype == SOCK_STREAM:
                    port = native_getservbyname(port, 'tcp')
                elif socktype == SOCK_DGRAM:
                    port = native_getservbyname(port, 'udp')
                else:
                    raise gaierror(EAI_SERVICE, 'Servname not supported for ai_socktype')
            except error as ex:
                if 'not found' in str(ex):
                    raise gaierror(EAI_SERVICE, 'Servname not supported for ai_socktype')
                raise gaierror(str(ex))
            except UnicodeEncodeError:
                raise error('Int or String expected', port)
    elif port is None:
        port = 0
    elif isinstance(port, integer_types):
        pass
    else:
        raise error('Int or String expected', port, type(port))
    port = int(port % 65536)
    if not socktypes and socktype:
        socktypes.append(socktype)
    return port, socktypes



def _resolve_special(hostname, family):
    if not isinstance(hostname, hostname_types):
        raise TypeError("argument 1 must be str, bytes or bytearray, not %s" % (type(hostname),))

    if hostname in (u'', b''):
        result = native_getaddrinfo(None, 0, family, SOCK_DGRAM, 0, AI_PASSIVE)
        if len(result) != 1:
            raise error('wildcard resolved to multiple address')
        return result[0][4][0]
    return hostname


class AbstractResolver(object):

    HOSTNAME_ENCODING = 'idna'

    _LOCAL_HOSTNAMES = (
        b'localhost',
        b'ip6-localhost',
        b'::1',
        b'127.0.0.1',
    )

    _LOCAL_AND_BROADCAST_HOSTNAMES = _LOCAL_HOSTNAMES + (
        b'255.255.255.255',
        b'<broadcast>',
    )

    EAI_NONAME_MSG = (
        'nodename nor servname provided, or not known'
        if MAC else
        'Name or service not known'
    )

    EAI_FAMILY_MSG = (
        'ai_family not supported'
    )

    _KNOWN_ADDR_FAMILIES = {
        v
        for k, v in vars(_socket).items()
        if k.startswith('AF_')
    }

    _KNOWN_SOCKTYPES = {
        v
        for k, v in vars(_socket).items()
        if k.startswith('SOCK_')
        and k not in ('SOCK_CLOEXEC', 'SOCK_MAX_SIZE')
    }

    def close(self):
        """
        Release resources held by this object.

        Subclasses that define resources should override.

        .. versionadded:: 22.10.1
        """

    @staticmethod
    def fixup_gaierror(func):
        import functools

        @functools.wraps(func)
        def resolve(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except gaierror as ex:
                if ex.args[0] == EAI_NONAME and len(ex.args) == 1:
                    # dnspython doesn't set an error message
                    ex.args = (EAI_NONAME, self.EAI_NONAME_MSG)
                    ex.errno = EAI_NONAME
                raise
        return resolve

    def _hostname_to_bytes(self, hostname):
        if isinstance(hostname, text_type):
            hostname = hostname.encode(self.HOSTNAME_ENCODING)
        elif not isinstance(hostname, (bytes, bytearray)):
            raise TypeError('Expected str, bytes or bytearray, not %s' % type(hostname).__name__)

        return bytes(hostname)

    def gethostbyname(self, hostname, family=AF_INET):
        # The native ``gethostbyname`` and ``gethostbyname_ex`` have some different
        # behaviour with special names. Notably, ``gethostbyname`` will handle
        # both "<broadcast>" and "255.255.255.255", while ``gethostbyname_ex`` refuses to
        # handle those; they result in different errors, too. So we can't
        # pass those through.
        hostname = self._hostname_to_bytes(hostname)
        if hostname in self._LOCAL_AND_BROADCAST_HOSTNAMES:
            return native_gethostbyname(hostname)
        hostname = _resolve_special(hostname, family)
        return self.gethostbyname_ex(hostname, family)[-1][0]

    def _gethostbyname_ex(self, hostname_bytes, family):
        """Raise an ``herror`` or a ``gaierror``."""
        aliases = self._getaliases(hostname_bytes, family)
        addresses = []
        tuples = self.getaddrinfo(hostname_bytes, 0, family,
                                  SOCK_STREAM,
                                  SOL_TCP, AI_CANONNAME)
        canonical = tuples[0][3]
        for item in tuples:
            addresses.append(item[4][0])
        # XXX we just ignore aliases
        return (canonical, aliases, addresses)

    def gethostbyname_ex(self, hostname, family=AF_INET):
        hostname = self._hostname_to_bytes(hostname)
        if hostname in self._LOCAL_AND_BROADCAST_HOSTNAMES:
            # The broadcast specials aren't handled here, but they may produce
            # special errors that are hard to replicate across all systems.
            return native_gethostbyname_ex(hostname)
        return self._gethostbyname_ex(hostname, family)

    def _getaddrinfo(self, host_bytes, port, family, socktype, proto, flags):
        raise NotImplementedError

    def getaddrinfo(self, host, port, family=0, socktype=0, proto=0, flags=0):
        host = self._hostname_to_bytes(host) if host is not None else None

        if (
                not isinstance(host, bytes)  # 1, 2
                or (flags & AI_NUMERICHOST) # 3
                or host in self._LOCAL_HOSTNAMES # 4
                or (is_ipv6_addr(host) and host.startswith(b'fe80')) # 5
        ):
            # This handles cases which do not require network access
            # 1) host is None
            # 2) host is of an invalid type
            # 3) AI_NUMERICHOST flag is set
            # 4) It's a well-known alias. TODO: This is special casing for c-ares that we don't
            #    really want to do. It's here because it resolves a discrepancy with the system
            #    resolvers caught by test cases. In gevent 20.4.0, this only worked correctly on
            #    Python 3 and not Python 2, by accident.
            # 5) host is a link-local ipv6; dnspython returns the wrong
            #    scope-id for those.
            return native_getaddrinfo(host, port, family, socktype, proto, flags)

        return self._getaddrinfo(host, port, family, socktype, proto, flags)

    def _getaliases(self, hostname, family):
        # pylint:disable=unused-argument
        return []

    def _gethostbyaddr(self, ip_address_bytes):
        """Raises herror."""
        raise NotImplementedError

    def gethostbyaddr(self, ip_address):
        ip_address = _resolve_special(ip_address, AF_UNSPEC)
        ip_address = self._hostname_to_bytes(ip_address)
        if ip_address in self._LOCAL_AND_BROADCAST_HOSTNAMES:
            return native_gethostbyaddr(ip_address)

        return self._gethostbyaddr(ip_address)

    def _getnameinfo(self, address_bytes, port, sockaddr, flags):
        raise NotImplementedError

    def getnameinfo(self, sockaddr, flags):
        if not isinstance(flags, integer_types):
            raise TypeError('an integer is required')
        if not isinstance(sockaddr, tuple):
            raise TypeError('getnameinfo() argument 1 must be a tuple')

        address = sockaddr[0]
        address = self._hostname_to_bytes(sockaddr[0])

        if address in self._LOCAL_AND_BROADCAST_HOSTNAMES:
            return native_getnameinfo(sockaddr, flags)

        port = sockaddr[1]
        if not isinstance(port, integer_types):
            raise TypeError('port must be an integer, not %s' % type(port))

        if not PYPY and port >= 65536:
            # System resolvers do different things with an
            # out-of-bound port; macOS CPython 3.8 raises ``gaierror: [Errno 8]
            # nodename nor servname provided, or not known``, while
            # manylinux CPython 2.7 appears to ignore it and raises ``error:
            # sockaddr resolved to multiple addresses``. TravisCI, at least ot
            # one point, successfully resolved www.gevent.org to ``(readthedocs.org, '0')``.
            # But c-ares 1.16 would raise ``gaierror(25, 'ARES_ESERVICE: unknown')``.
            # Doing this appears to get the expected results on CPython
            port = 0
        if PYPY and (port < 0 or port >= 65536):
            # PyPy seems to always be strict about that and produce the same results
            # on all platforms.
            raise OverflowError("port must be 0-65535.")

        if len(sockaddr) > 2:
            # Must be IPv6: (host, port, [flowinfo, [scopeid]])
            flowinfo = sockaddr[2]
            if flowinfo > 0xfffff:
                raise OverflowError("getnameinfo(): flowinfo must be 0-1048575.")

        return self._getnameinfo(address, port, sockaddr, flags)
