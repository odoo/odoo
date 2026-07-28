# Copyright (c) 2009-2014 Denis Bilenko and gevent contributors. See LICENSE for details.
from __future__ import absolute_import

# standard functions and classes that this module re-implements in a gevent-aware way:
_implements = [
    'create_connection',
    'socket',
    'SocketType',
    'fromfd',
    'socketpair',
]

__dns__ = [
    'getaddrinfo',
    'gethostbyname',
    'gethostbyname_ex',
    'gethostbyaddr',
    'getnameinfo',
    'getfqdn',
]

_implements += __dns__

# non-standard functions that this module provides:
__extensions__ = [
    'cancel_wait',
    'wait_read',
    'wait_write',
    'wait_readwrite',
]

# standard functions and classes that this module re-imports
__imports__ = [
    'error',
    'gaierror',
    'herror',
    'htonl',
    'htons',
    'ntohl',
    'ntohs',
    'inet_aton',
    'inet_ntoa',
    'inet_pton',
    'inet_ntop',
    'timeout',
    'gethostname',
    'getprotobyname',
    'getservbyname',
    'getservbyport',
    'getdefaulttimeout',
    'setdefaulttimeout',
    # Windows:
    'errorTab',
    # Python 3
    'AddressFamily',
    'SocketKind',
    'CMSG_LEN',
    'CMSG_SPACE',
    'dup',
    'if_indextoname',
    'if_nameindex',
    'if_nametoindex',
    'sethostname',
    'create_server',
    'has_dualstack_ipv6',
]


import time

from gevent._hub_local import get_hub_noargs as get_hub
from gevent._compat import string_types, integer_types
from gevent._compat import PY39
from gevent._compat import WIN as is_windows
from gevent._compat import OSX as is_macos
from gevent._compat import exc_clear
from gevent._util import copy_globals
from gevent._greenlet_primitives import get_memory as _get_memory
from gevent._hub_primitives import wait_on_socket as _wait_on_socket

from gevent.timeout import Timeout


if PY39:
    __imports__.extend([
        'recv_fds',
        'send_fds',
    ])

# pylint:disable=no-name-in-module,unused-import
if is_windows:
    # no such thing as WSAEPERM or error code 10001 according to winsock.h or MSDN
    from errno import WSAEINVAL as EINVAL
    from errno import WSAEWOULDBLOCK as EWOULDBLOCK
    from errno import WSAEINPROGRESS as EINPROGRESS
    from errno import WSAEALREADY as EALREADY
    from errno import WSAEISCONN as EISCONN
    from gevent.win32util import formatError as strerror
    EAGAIN = EWOULDBLOCK
else:
    from errno import EINVAL
    from errno import EWOULDBLOCK
    from errno import EINPROGRESS
    from errno import EALREADY
    from errno import EAGAIN
    from errno import EISCONN
    from os import strerror

try:
    from errno import EBADF
except ImportError:
    EBADF = 9

try:
    from errno import EHOSTUNREACH
except ImportError:
    EHOSTUNREACH = -1

try:
    from errno import ECONNREFUSED
except ImportError:
    ECONNREFUSED = -1

# macOS can return EPROTOTYPE when writing to a socket that is shutting
# Down. Retrying the write should return the expected EPIPE error.
# Downstream classes (like pywsgi) know how to handle/ignore EPIPE.
# This set is used by socket.send() to decide whether the write should
# be retried. The default is to retry only on EWOULDBLOCK. Here we add
# EPROTOTYPE on macOS to handle this platform-specific race condition.
GSENDAGAIN = (EWOULDBLOCK,)
if is_macos:
    from errno import EPROTOTYPE
    GSENDAGAIN += (EPROTOTYPE,)

import _socket
_realsocket = _socket.socket
import socket as __socket__
try:
    # Provide implementation of socket.socketpair on Windows < 3.5.
    import backports.socketpair
except ImportError:
    pass

_SocketError = __socket__.error

_name = _value = None
__imports__ = copy_globals(__socket__, globals(),
                           only_names=__imports__,
                           ignore_missing_names=True)

for _name in __socket__.__all__:
    _value = getattr(__socket__, _name)
    if isinstance(_value, (integer_types, string_types)):
        globals()[_name] = _value
        __imports__.append(_name)

del _name, _value

_timeout_error = timeout # pylint: disable=undefined-variable

from gevent import _hub_primitives
_hub_primitives.set_default_timeout_error(_timeout_error)

wait = _hub_primitives.wait_on_watcher
wait_read = _hub_primitives.wait_read
wait_write = _hub_primitives.wait_write
wait_readwrite = _hub_primitives.wait_readwrite

#: The exception raised by default on a call to :func:`cancel_wait`
class cancel_wait_ex(error): # pylint: disable=undefined-variable
    def __init__(self):
        super(cancel_wait_ex, self).__init__(
            EBADF,
            'File descriptor was closed in another greenlet')


def cancel_wait(watcher, error=cancel_wait_ex):
    """See :meth:`gevent.hub.Hub.cancel_wait`"""
    get_hub().cancel_wait(watcher, error)


def gethostbyname(hostname):
    """
    gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.

    .. seealso:: :doc:`/dns`
    """
    return get_hub().resolver.gethostbyname(hostname)


def gethostbyname_ex(hostname):
    """
    gethostbyname_ex(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    Resolve host and port into list of address info entries.

    .. seealso:: :doc:`/dns`
    """
    return get_hub().resolver.gethostbyname_ex(hostname)

def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """
    Resolve host and port into list of address info entries.

    Translate the host/port argument into a sequence of 5-tuples that contain
    all the necessary arguments for creating a socket connected to that service.
    host is a domain name, a string representation of an IPv4/v6 address or
    None. port is a string service name such as 'http', a numeric port number or
    None. By passing None as the value of host and port, you can pass NULL to
    the underlying C API.

    The family, type and proto arguments can be optionally specified in order to
    narrow the list of addresses returned. Passing zero as a value for each of
    these arguments selects the full range of results.

    .. seealso:: :doc:`/dns`
    """
    # Also, on Python 3, we need to translate into the special enums.
    # Our lower-level resolvers, including the thread and blocking, which use _socket,
    # function simply with integers.
    addrlist = get_hub().resolver.getaddrinfo(host, port, family, type, proto, flags)
    result = [
        # pylint:disable=undefined-variable
        (_intenum_converter(af, AddressFamily),
         _intenum_converter(socktype, SocketKind),
         proto, canonname, sa)
        for af, socktype, proto, canonname, sa
        in addrlist
    ]
    return result

def _intenum_converter(value, enum_klass):
    try:
        return enum_klass(value)
    except ValueError: # pragma: no cover
        return value


def gethostbyaddr(ip_address):
    """
    gethostbyaddr(ip_address) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.

    .. seealso:: :doc:`/dns`
    """
    return get_hub().resolver.gethostbyaddr(ip_address)


def getnameinfo(sockaddr, flags):
    """
    getnameinfo(sockaddr, flags) -> (host, port)

    Get host and port for a sockaddr.

    .. seealso:: :doc:`/dns`
    """
    return get_hub().resolver.getnameinfo(sockaddr, flags)


def getfqdn(name=''):
    """Get fully qualified domain name from name.

    An empty argument is interpreted as meaning the local host.

    First the hostname returned by gethostbyaddr() is checked, then
    possibly existing aliases. In case no FQDN is available, hostname
    from gethostname() is returned.

    .. versionchanged:: 23.7.0
       The IPv6 generic address '::' now returns the result of
       ``gethostname``, like the IPv4 address '0.0.0.0'.
    """
    # pylint: disable=undefined-variable
    name = name.strip()
    # IPv6 added in a late Python 3.10/3.11 patch release.
    # https://github.com/python/cpython/issues/100374
    if not name or name in ('0.0.0.0', '::'):
        name = gethostname()
    try:
        hostname, aliases, _ = gethostbyaddr(name)
    except error:
        pass
    else:
        aliases.insert(0, hostname)
        for name in aliases: # EWW! pylint:disable=redefined-argument-from-local
            if isinstance(name, bytes):
                if b'.' in name:
                    break
            elif '.' in name:
                break
        else:
            name = hostname
    return name

def __send_chunk(socket, data_memory, flags, timeleft, end, timeout=_timeout_error):
    """
    Send the complete contents of ``data_memory`` before returning.
    This is the core loop around :meth:`send`.

    :param timeleft: Either ``None`` if there is no timeout involved,
       or a float indicating the timeout to use.
    :param end: Either ``None`` if there is no timeout involved, or
       a float giving the absolute end time.
    :return: An updated value for ``timeleft`` (or None)
    :raises timeout: If ``timeleft`` was given and elapsed while
       sending this chunk.
    """
    data_sent = 0
    len_data_memory = len(data_memory)
    started_timer = 0
    while data_sent < len_data_memory:
        chunk = data_memory[data_sent:]
        if timeleft is None:
            data_sent += socket.send(chunk, flags)
        elif started_timer and timeleft <= 0:
            # Check before sending to guarantee a check
            # happens even if each chunk successfully sends its data
            # (especially important for SSL sockets since they have large
            # buffers). But only do this if we've actually tried to
            # send something once to avoid spurious timeouts on non-blocking
            # sockets.
            raise timeout('timed out')
        else:
            started_timer = 1
            data_sent += socket.send(chunk, flags, timeout=timeleft)
            timeleft = end - time.time()

    return timeleft

def _sendall(socket, data_memory, flags,
             SOL_SOCKET=__socket__.SOL_SOCKET,  # pylint:disable=no-member
             SO_SNDBUF=__socket__.SO_SNDBUF):  # pylint:disable=no-member
    """
    Send the *data_memory* (which should be a memoryview)
    using the gevent *socket*, performing well on PyPy.
    """

    # On PyPy up through 5.10.0, both PyPy2 and PyPy3, subviews
    # (slices) of a memoryview() object copy the underlying bytes the
    # first time the builtin socket.send() method is called. On a
    # non-blocking socket (that thus calls socket.send() many times)
    # with a large input, this results in many repeated copies of an
    # ever smaller string, depending on the networking buffering. For
    # example, if each send() can process 1MB of a 50MB input, and we
    # naively pass the entire remaining subview each time, we'd copy
    # 49MB, 48MB, 47MB, etc, thus completely killing performance. To
    # workaround this problem, we work in reasonable, fixed-size
    # chunks. This results in a 10x improvement to bench_sendall.py,
    # while having no measurable impact on CPython (since it doesn't
    # copy at all the only extra overhead is a few python function
    # calls, which is negligible for large inputs).

    # On one macOS machine, PyPy3 5.10.1 produced ~ 67.53 MB/s before this change,
    # and ~ 616.01 MB/s after.

    # See https://bitbucket.org/pypy/pypy/issues/2091/non-blocking-socketsend-slow-gevent

    # Too small of a chunk (the socket's buf size is usually too
    # small) results in reduced perf due to *too many* calls to send and too many
    # small copies. With a buffer of 143K (the default on my system), for
    # example, bench_sendall.py yields ~264MB/s, while using 1MB yields
    # ~653MB/s (matching CPython). 1MB is arbitrary and might be better
    # chosen, say, to match a page size?

    len_data_memory = len(data_memory)
    if not len_data_memory:
        # Don't try to send empty data at all, no point, and breaks ssl
        # See issue 719
        return 0


    chunk_size = max(socket.getsockopt(SOL_SOCKET, SO_SNDBUF), 1024 * 1024)

    data_sent = 0
    end = None
    timeleft = None
    if socket.timeout is not None:
        timeleft = socket.timeout
        end = time.time() + timeleft

    while data_sent < len_data_memory:
        chunk_end = min(data_sent + chunk_size, len_data_memory)
        chunk = data_memory[data_sent:chunk_end]

        timeleft = __send_chunk(socket, chunk, flags, timeleft, end)
        data_sent += len(chunk) # Guaranteed it sent the whole thing

# pylint:disable=no-member
_RESOLVABLE_FAMILIES = (__socket__.AF_INET,)
if __socket__.has_ipv6:
    _RESOLVABLE_FAMILIES += (__socket__.AF_INET6,)

def _resolve_addr(sock, address):
    # Internal method: resolve the AF_INET[6] address using
    # getaddrinfo.
    if sock.family not in _RESOLVABLE_FAMILIES or not isinstance(address, tuple):
        return address
    # address is (host, port) (ipv4) or (host, port, flowinfo, scopeid) (ipv6).
    # If it's already resolved, no need to go through getaddrinfo() again.
    # That can lose precision (e.g., on IPv6, it can lose scopeid). The standard library
    # does this in socketmodule.c:setipaddr. (This is only part of the logic, the real
    # thing is much more complex.)
    try:
        if __socket__.inet_pton(sock.family, address[0]):
            return address
    except AttributeError: # pragma: no cover
        # inet_pton might not be available.
        pass
    except _SocketError:
        # Not parseable, needs resolved.
        pass


    # We don't pass the port to getaddrinfo because the C
    # socket module doesn't either (on some systems its
    # illegal to do that without also passing socket type and
    # protocol). Instead we join the port back at the end.
    # See https://github.com/gevent/gevent/issues/1252
    host, port = address[:2]
    r = getaddrinfo(host, None, sock.family)
    address = r[0][-1]
    if len(address) == 2:
        address = (address[0], port)
    else:
        address = (address[0], port, address[2], address[3])
    return address


timeout_default = object()

class SocketMixin(object):
    # pylint:disable=too-many-public-methods
    __slots__ = (
        'hub',
        'timeout',
        '_read_event',
        '_write_event',
        '_sock',
        '__weakref__',
    )

    def __init__(self):
        # Writing:
        #    (self.a, self.b) = (None,) * 2
        # generates the fastest bytecode. But At least on PyPy,
        # where the SSLSocket subclass has a timeout property,
        # it results in the settimeout() method getting the tuple
        # as the value, not the unpacked None.
        self._read_event = None
        self._write_event = None
        self._sock = None
        self.hub = None
        self.timeout = None

    def _drop_events_and_close(self, closefd=True, _cancel_wait_ex=cancel_wait_ex):
        hub = self.hub
        read_event = self._read_event
        write_event = self._write_event
        self._read_event = self._write_event = None
        hub.cancel_waits_close_and_then(
            (read_event, write_event),
            _cancel_wait_ex,
            # Pass the socket to keep it alive until such time as
            # the waiters are guaranteed to be closed.
            self._drop_ref_on_close if closefd else id,
            self._sock
        )

    def _drop_ref_on_close(self, sock):
        raise NotImplementedError

    def _get_ref(self):
        return self._read_event.ref or self._write_event.ref

    def _set_ref(self, value):
        self._read_event.ref = value
        self._write_event.ref = value

    ref = property(_get_ref, _set_ref)

    _wait = _wait_on_socket

    ###
    # Common methods defined here need to be added to the
    # API documentation specifically.
    ###

    def settimeout(self, howlong):
        if howlong is not None:
            try:
                f = howlong.__float__
            except AttributeError:
                raise TypeError('a float is required', howlong, type(howlong))
            howlong = f()
            if howlong < 0.0:
                raise ValueError('Timeout value out of range')
        # avoid recursion with any property on self.timeout
        SocketMixin.timeout.__set__(self, howlong)

    def gettimeout(self):
        # avoid recursion with any property on self.timeout
        return SocketMixin.timeout.__get__(self, type(self))

    def setblocking(self, flag):
        # Beginning in 3.6.0b3 this is supposed to raise
        # if the file descriptor is closed, but the test for it
        # involves closing the fileno directly. Since we
        # don't touch the fileno here, it doesn't make sense for
        # us.
        if flag:
            self.timeout = None
        else:
            self.timeout = 0.0

    def shutdown(self, how):
        if how == 0:  # SHUT_RD
            self.hub.cancel_wait(self._read_event, cancel_wait_ex)
        elif how == 1:  # SHUT_WR
            self.hub.cancel_wait(self._write_event, cancel_wait_ex)
        else:
            self.hub.cancel_wait(self._read_event, cancel_wait_ex)
            self.hub.cancel_wait(self._write_event, cancel_wait_ex)
        self._sock.shutdown(how)

    # pylint:disable-next=undefined-variable
    family = property(lambda self: _intenum_converter(self._sock.family, AddressFamily))
    # pylint:disable-next=undefined-variable
    type = property(lambda self: _intenum_converter(self._sock.type, SocketKind))
    proto = property(lambda self: self._sock.proto)

    def fileno(self):
        return self._sock.fileno()

    def getsockname(self):
        return self._sock.getsockname()

    def getpeername(self):
        return self._sock.getpeername()

    def bind(self, address):
        return self._sock.bind(address)

    def listen(self, *args):
        return self._sock.listen(*args)

    def getsockopt(self, *args):
        return self._sock.getsockopt(*args)

    def setsockopt(self, *args):
        return self._sock.setsockopt(*args)

    if hasattr(__socket__.socket, 'ioctl'): # os.name == 'nt'
        def ioctl(self, *args):
            return self._sock.ioctl(*args)
    if hasattr(__socket__.socket, 'sleeptaskw'): # os.name == 'riscos
        def sleeptaskw(self, *args):
            return self._sock.sleeptaskw(*args)

    def getblocking(self):
        """
        Returns whether the socket will approximate blocking
        behaviour.

        .. versionadded:: 1.3a2
            Added in Python 3.7.
        """
        return self.timeout != 0.0

    def connect(self, address):
        """
        Connect to *address*.

        .. versionchanged:: 20.6.0
            If the host part of the address includes an IPv6 scope ID,
            it will be used instead of ignored, if the platform supplies
            :func:`socket.inet_pton`.
        """
        # In the standard library, ``connect`` and ``connect_ex`` are implemented
        # in C, and they both call a C function ``internal_connect`` to do the real
        # work. This means that it is a visible behaviour difference to have our
        # Python implementation of ``connect_ex`` simply call ``connect``:
        # it could be overridden in a subclass or at runtime! Because of our exception handling,
        # this can make a difference for known subclasses like SSLSocket.
        self._internal_connect(address)

    def connect_ex(self, address):
        """
        Connect to *address*, returning a result code.

        .. versionchanged:: 23.7.0
           No longer uses an overridden ``connect`` method on
           this object. Instead, like the standard library, this method always
           uses a non-replacable internal connection function.
        """
        try:
            return self._internal_connect(address) or 0
        except __socket__.timeout:
            return EAGAIN
        except __socket__.gaierror: # pylint:disable=try-except-raise
            # gaierror/overflowerror/typerror is not silenced by connect_ex;
            # gaierror extends error so catch it first
            raise
        except _SocketError as ex:
            # Python 3: error is now OSError and it has various subclasses.
            # Only those that apply to actually connecting are silenced by
            # connect_ex.
            # On Python 3, we want to check ex.errno; on Python 2
            # there is no such attribute, we need to look at the first
            # argument.
            try:
                err = ex.errno
            except AttributeError:
                err = ex.args[0]
            if err:
                return err
            raise

    def _internal_connect(self, address):
        # Like the C function ``internal_connect``, not meant to be overridden,
        # but exposed for testing.
        if self.timeout == 0.0:
            return self._sock.connect(address)
        address = _resolve_addr(self._sock, address)
        with Timeout._start_new_or_dummy(self.timeout, __socket__.timeout("timed out")):
            while 1:
                err = self.getsockopt(__socket__.SOL_SOCKET, __socket__.SO_ERROR)
                if err:
                    raise _SocketError(err, strerror(err))
                result = self._sock.connect_ex(address)

                if not result or result == EISCONN:
                    break
                if (result in (EWOULDBLOCK, EINPROGRESS, EALREADY)) or (result == EINVAL and is_windows):
                    self._wait(self._write_event)
                else:
                    if (isinstance(address, tuple)
                            and address[0] == 'fe80::1'
                            and result == EHOSTUNREACH):
                        # On Python 3.7 on mac, we see EHOSTUNREACH
                        # returned for this link-local address, but it really is
                        # supposed to be ECONNREFUSED according to the standard library
                        # tests (test_socket.NetworkConnectionNoServer.test_create_connection)
                        # (On previous versions, that code passed the '127.0.0.1' IPv4 address, so
                        # ipv6 link locals were never a factor; 3.7 passes 'localhost'.)
                        # It is something of a mystery how the stdlib socket code doesn't
                        # produce EHOSTUNREACH---I (JAM) can't see how socketmodule.c would avoid
                        # that. The normal connect just calls connect_ex much like we do.
                        result = ECONNREFUSED
                    raise _SocketError(result, strerror(result))

    def recv(self, *args):
        while 1:
            try:
                return self._sock.recv(*args)
            except _SocketError as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                # QQQ without clearing exc_info test__refcount.test_clean_exit fails
                exc_clear() # Python 2
            self._wait(self._read_event)

    def recvfrom(self, *args):
        while 1:
            try:
                return self._sock.recvfrom(*args)
            except _SocketError as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                exc_clear() # Python 2
            self._wait(self._read_event)

    def recvfrom_into(self, *args):
        while 1:
            try:
                return self._sock.recvfrom_into(*args)
            except _SocketError as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                exc_clear() # Python 2
            self._wait(self._read_event)

    def recv_into(self, *args):
        while 1:
            try:
                return self._sock.recv_into(*args)
            except _SocketError as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                exc_clear() # Python 2
            self._wait(self._read_event)

    def sendall(self, data, flags=0):
        # this sendall is also reused by gevent.ssl.SSLSocket subclass,
        # so it should not call self._sock methods directly
        data_memory = _get_memory(data)
        return _sendall(self, data_memory, flags)

    def sendto(self, *args):
        try:
            return self._sock.sendto(*args)
        except _SocketError as ex:
            if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                raise
            exc_clear()
            self._wait(self._write_event)

            try:
                return self._sock.sendto(*args)
            except _SocketError as ex2:
                if ex2.args[0] == EWOULDBLOCK:
                    exc_clear()
                    return 0
                raise

    def send(self, data, flags=0, timeout=timeout_default):
        if timeout is timeout_default:
            timeout = self.timeout
        try:
            return self._sock.send(data, flags)
        except _SocketError as ex:
            if ex.args[0] not in GSENDAGAIN or timeout == 0.0:
                raise
            exc_clear()
            self._wait(self._write_event)
            try:
                return self._sock.send(data, flags)
            except _SocketError as ex2:
                if ex2.args[0] == EWOULDBLOCK:
                    exc_clear()
                    return 0
                raise

    @classmethod
    def _fixup_docstrings(cls):
        for k, v in vars(cls).items():
            if k.startswith('_'):
                continue
            if not hasattr(v, '__doc__') or v.__doc__:
                continue
            smeth =  getattr(__socket__.socket, k, None)
            if not smeth or not smeth.__doc__:
                continue

            try:
                v.__doc__ = smeth.__doc__
            except (AttributeError, TypeError):
                # slots can't have docs. Py2 raises TypeError,
                # Py3 raises AttributeError
                continue

SocketMixin._fixup_docstrings()
del SocketMixin._fixup_docstrings
