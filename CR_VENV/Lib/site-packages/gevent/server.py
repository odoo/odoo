# Copyright (c) 2009-2012 Denis Bilenko. See LICENSE for details.
"""TCP/SSL server"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from contextlib import closing

import sys

from _socket import error as SocketError
from _socket import SOL_SOCKET
from _socket import SO_REUSEADDR
from _socket import AF_INET
from _socket import SOCK_DGRAM

from gevent.baseserver import BaseServer
from gevent.socket import EWOULDBLOCK
from gevent.socket import socket as GeventSocket
from gevent._compat import PYPY, PY3

__all__ = ['StreamServer', 'DatagramServer']


if sys.platform == 'win32':
    # SO_REUSEADDR on Windows does not mean the same thing as on *nix (issue #217)
    DEFAULT_REUSE_ADDR = None
else:
    DEFAULT_REUSE_ADDR = 1


if PY3:
    # sockets and SSL sockets are context managers on Python 3
    def _closing_socket(sock):
        return sock
else:
    # but they are not guaranteed to be so on Python 2
    _closing_socket = closing


class StreamServer(BaseServer):
    """
    A generic TCP server.

    Accepts connections on a listening socket and spawns user-provided
    *handle* function for each connection with 2 arguments: the client
    socket and the client address.

    Note that although the errors in a successfully spawned handler
    will not affect the server or other connections, the errors raised
    by :func:`accept` and *spawn* cause the server to stop accepting
    for a short amount of time. The exact period depends on the values
    of :attr:`min_delay` and :attr:`max_delay` attributes.

    The delay starts with :attr:`min_delay` and doubles with each
    successive error until it reaches :attr:`max_delay`. A successful
    :func:`accept` resets the delay to :attr:`min_delay` again.

    See :class:`~gevent.baseserver.BaseServer` for information on defining the *handle*
    function and important restrictions on it.

    **SSL Support**

    The server can optionally work in SSL mode when given the correct
    keyword arguments. (That is, the presence of any keyword arguments
    will trigger SSL mode.) On Python 2.7.9 and later (any Python
    version that supports the :class:`ssl.SSLContext`), this can be
    done with a configured ``SSLContext``. On any Python version, it
    can be done by passing the appropriate arguments for
    :func:`ssl.wrap_socket`.

    The incoming socket will be wrapped into an SSL socket before
    being passed to the *handle* function.

    If the *ssl_context* keyword argument is present, it should
    contain an :class:`ssl.SSLContext`. The remaining keyword
    arguments are passed to the :meth:`ssl.SSLContext.wrap_socket`
    method of that object. Depending on the Python version, supported arguments
    may include:

    - server_hostname
    - suppress_ragged_eofs
    - do_handshake_on_connect

    .. caution:: When using an SSLContext, it should either be
       imported from :mod:`gevent.ssl`, or the process needs to be monkey-patched.
       If the process is not monkey-patched and you pass the standard library
       SSLContext, the resulting client sockets will not cooperate with gevent.

    Otherwise, keyword arguments are assumed to apply to :func:`ssl.wrap_socket`.
    These keyword arguments may include:

    - keyfile
    - certfile
    - cert_reqs
    - ssl_version
    - ca_certs
    - suppress_ragged_eofs
    - do_handshake_on_connect
    - ciphers

    .. versionchanged:: 1.2a2
       Add support for the *ssl_context* keyword argument.

    """
    # the default backlog to use if none was provided in __init__
    # For TCP, 128 is the (default) maximum at the operating system level on Linux and macOS
    # larger values are truncated to 128.
    #
    # Windows defines SOMAXCONN=0x7fffffff to mean "max reasonable value" --- that value
    # was undocumented and subject to change, but appears to be 200.
    # Beginning in Windows 8 there's SOMAXCONN_HINT(b)=(-(b)) which means "at least
    # as many SOMAXCONN but no more than b" which is a portable way to write 200.
    backlog = 128

    reuse_addr = DEFAULT_REUSE_ADDR

    def __init__(self, listener, handle=None, backlog=None, spawn='default', **ssl_args):
        BaseServer.__init__(self, listener, handle=handle, spawn=spawn)
        try:
            if ssl_args:
                ssl_args.setdefault('server_side', True)
                if 'ssl_context' in ssl_args:
                    ssl_context = ssl_args.pop('ssl_context')
                    self.wrap_socket = ssl_context.wrap_socket
                    self.ssl_args = ssl_args
                else:
                    from gevent.ssl import wrap_socket
                    self.wrap_socket = wrap_socket
                    self.ssl_args = ssl_args
            else:
                self.ssl_args = None
            if backlog is not None:
                if hasattr(self, 'socket'):
                    raise TypeError('backlog must be None when a socket instance is passed')
                self.backlog = backlog
        except:
            self.close()
            raise

    @property
    def ssl_enabled(self):
        return self.ssl_args is not None

    def set_listener(self, listener):
        BaseServer.set_listener(self, listener)

    def _make_socket_stdlib(self, fresh):
        # We want to unwrap the gevent wrapping of the listening socket.
        # This lets us be just a hair more efficient: when our 'do_read' is
        # called, we've already waited on the socket to be ready to accept(), so
        # we don't need to (potentially) do it again. Also we avoid a layer
        # of method calls. The cost, though, is that we have to manually wrap
        # sockets back up to be non-blocking in do_read(). I'm not sure that's worth
        # it.
        #
        # In the past, we only did this when set_listener() was called with a socket
        # object and not an address. It makes sense to do it always though,
        # so that we get consistent behaviour.
        while hasattr(self.socket, '_sock'):
            if fresh:
                if hasattr(self.socket, '_drop_events'):
                    # Discard event listeners. This socket object is not shared,
                    # so we don't need them anywhere else.
                    # This matters somewhat for libuv, where we have to multiplex
                    # listeners, and we're about to create a new listener.
                    # If we don't do this, on Windows libuv tends to miss incoming
                    # connects and our _do_read callback doesn't get called.
                    self.socket._drop_events()
                # XXX: Do we need to _drop() for PyPy?

            self.socket = self.socket._sock # pylint:disable=attribute-defined-outside-init

    def init_socket(self):
        fresh = False
        if not hasattr(self, 'socket'):
            fresh = True
            # FIXME: clean up the socket lifetime
            # pylint:disable=attribute-defined-outside-init
            self.socket = self.get_listener(self.address, self.backlog, self.family)
            self.address = self.socket.getsockname()
        if self.ssl_args:
            self._handle = self.wrap_socket_and_handle
        else:
            self._handle = self.handle
        self._make_socket_stdlib(fresh)

    @classmethod
    def get_listener(cls, address, backlog=None, family=None):
        if backlog is None:
            backlog = cls.backlog
        return _tcp_listener(address, backlog=backlog, reuse_addr=cls.reuse_addr, family=family)

    if PY3:
        def do_read(self):
            sock = self.socket
            try:
                fd, address = sock._accept()
            except BlockingIOError: # python 2: pylint: disable=undefined-variable
                if not sock.timeout:
                    return
                raise

            sock = GeventSocket(sock.family, sock.type, sock.proto, fileno=fd)
            # XXX Python issue #7995? "if no default timeout is set
            # and the listening socket had a (non-zero) timeout, force
            # the new socket in blocking mode to override
            # platform-specific socket flags inheritance."
            return sock, address

    else:
        def do_read(self):
            try:
                client_socket, address = self.socket.accept()
            except SocketError as err:
                if err.args[0] == EWOULDBLOCK:
                    return
                raise

            sockobj = GeventSocket(_sock=client_socket)
            if PYPY:
                # Undo the ref-count bump that the constructor
                # did. We gave it ownership.
                client_socket._drop()
            return sockobj, address

    def do_close(self, sock, *args):
        # pylint:disable=arguments-differ
        sock.close()

    def wrap_socket_and_handle(self, client_socket, address):
        # used in case of ssl sockets
        with _closing_socket(self.wrap_socket(client_socket, **self.ssl_args)) as ssl_socket:
            return self.handle(ssl_socket, address)


class DatagramServer(BaseServer):
    """A UDP server"""

    reuse_addr = DEFAULT_REUSE_ADDR

    def __init__(self, *args, **kwargs):
        # The raw (non-gevent) socket, if possible
        self._socket = None
        BaseServer.__init__(self, *args, **kwargs)
        from gevent.lock import Semaphore
        self._writelock = Semaphore()

    def init_socket(self):
        if not hasattr(self, 'socket'):
            # FIXME: clean up the socket lifetime
            # pylint:disable=attribute-defined-outside-init
            self.socket = self.get_listener(self.address, self.family)
            self.address = self.socket.getsockname()
        self._socket = self.socket
        try:
            self._socket = self._socket._sock
        except AttributeError:
            pass

    @classmethod
    def get_listener(cls, address, family=None):
        return _udp_socket(address, reuse_addr=cls.reuse_addr, family=family)

    def do_read(self):
        try:
            data, address = self._socket.recvfrom(8192)
        except SocketError as err:
            if err.args[0] == EWOULDBLOCK:
                return
            raise
        return data, address

    def sendto(self, *args):
        self._writelock.acquire()
        try:
            self.socket.sendto(*args)
        finally:
            self._writelock.release()


def _tcp_listener(address, backlog=50, reuse_addr=None, family=AF_INET):
    """A shortcut to create a TCP socket, bind it and put it into listening state."""
    sock = GeventSocket(family=family)
    if reuse_addr is not None:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, reuse_addr)
    try:
        sock.bind(address)
    except SocketError as ex:
        strerror = getattr(ex, 'strerror', None)
        if strerror is not None:
            ex.strerror = strerror + ': ' + repr(address)
        raise
    sock.listen(backlog)
    sock.setblocking(0)
    return sock


def _udp_socket(address, backlog=50, reuse_addr=None, family=AF_INET):
    # backlog argument for compat with tcp_listener
    # pylint:disable=unused-argument

    # we want gevent.socket.socket here
    sock = GeventSocket(family=family, type=SOCK_DGRAM)
    if reuse_addr is not None:
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, reuse_addr)
    try:
        sock.bind(address)
    except SocketError as ex:
        strerror = getattr(ex, 'strerror', None)
        if strerror is not None:
            ex.strerror = strerror + ': ' + repr(address)
        raise
    return sock
