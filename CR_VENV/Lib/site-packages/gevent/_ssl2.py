# (No idea where this comes from; it warns about 'configuration')
# pylint:disable=invalid-all-format
# Wrapper module for _ssl. Written by Bill Janssen.
# Ported to gevent by Denis Bilenko.
"""
SSL wrapper for socket objects on Python 2.7.8 and below.

For the documentation, refer to :mod:`ssl` module manual.

This module implements cooperative SSL socket wrappers.

.. deprecated:: 1.3
   This module is not secure. Support for Python versions
   with only this level of SSL will be dropped in gevent 1.4.
"""

from __future__ import absolute_import
# Our import magic sadly makes this warning useless
# pylint: disable=undefined-variable,arguments-differ,no-member

import ssl as __ssl__

_ssl = __ssl__._ssl

import sys
import errno
from gevent._socket2 import socket
from gevent.socket import _fileobject, timeout_default
from gevent.socket import error as socket_error, EWOULDBLOCK
from gevent.socket import timeout as _socket_timeout
from gevent._compat import PYPY
from gevent._util import copy_globals


__implements__ = [
    'SSLSocket',
    'wrap_socket',
    'get_server_certificate',
    'sslwrap_simple',
]

# Import all symbols from Python's ssl.py, except those that we are implementing
# and "private" symbols.
__imports__ = copy_globals(__ssl__, globals(),
                           # SSLSocket *must* subclass gevent.socket.socket; see issue 597
                           names_to_ignore=__implements__ + ['socket'],
                           dunder_names_to_keep=())


# Py2.6 can get RAND_status added twice
__all__ = list(set(__implements__) | set(__imports__))
if 'namedtuple' in __all__:
    __all__.remove('namedtuple')

class SSLSocket(socket):
    """
    gevent `ssl.SSLSocket <https://docs.python.org/2.6/library/ssl.html#sslsocket-objects>`_
    for Pythons < 2.7.9.
    """

    def __init__(self, sock, keyfile=None, certfile=None,
                 server_side=False, cert_reqs=CERT_NONE,
                 ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                 do_handshake_on_connect=True,
                 suppress_ragged_eofs=True,
                 ciphers=None):
        socket.__init__(self, _sock=sock)

        if PYPY:
            sock._drop()

        if certfile and not keyfile:
            keyfile = certfile
        # see if it's connected
        try:
            socket.getpeername(self)
        except socket_error as e:
            if e.args[0] != errno.ENOTCONN:
                raise
            # no, no connection yet
            self._sslobj = None
        else:
            # yes, create the SSL object
            if ciphers is None:
                self._sslobj = _ssl.sslwrap(self._sock, server_side,
                                            keyfile, certfile,
                                            cert_reqs, ssl_version, ca_certs)
            else:
                self._sslobj = _ssl.sslwrap(self._sock, server_side,
                                            keyfile, certfile,
                                            cert_reqs, ssl_version, ca_certs,
                                            ciphers)
            if do_handshake_on_connect:
                self.do_handshake()
        self.keyfile = keyfile
        self.certfile = certfile
        self.cert_reqs = cert_reqs
        self.ssl_version = ssl_version
        self.ca_certs = ca_certs
        self.ciphers = ciphers
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self._makefile_refs = 0

    def read(self, len=1024):
        """Read up to LEN bytes and return them.
        Return zero-length string on EOF."""
        while True:
            try:
                return self._sslobj.read(len)
            except SSLError as ex:
                if ex.args[0] == SSL_ERROR_EOF and self.suppress_ragged_eofs:
                    return ''
                if ex.args[0] == SSL_ERROR_WANT_READ:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    self._wait(self._read_event, timeout_exc=_SSLErrorReadTimeout)
                elif ex.args[0] == SSL_ERROR_WANT_WRITE:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    # note: using _SSLErrorReadTimeout rather than _SSLErrorWriteTimeout below is intentional
                    self._wait(self._write_event, timeout_exc=_SSLErrorReadTimeout)
                else:
                    raise

    def write(self, data):
        """Write DATA to the underlying SSL channel.  Returns
        number of bytes of DATA actually transmitted."""
        while True:
            try:
                return self._sslobj.write(data)
            except SSLError as ex:
                if ex.args[0] == SSL_ERROR_WANT_READ:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    self._wait(self._read_event, timeout_exc=_SSLErrorWriteTimeout)
                elif ex.args[0] == SSL_ERROR_WANT_WRITE:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    self._wait(self._write_event, timeout_exc=_SSLErrorWriteTimeout)
                else:
                    raise

    def getpeercert(self, binary_form=False):
        """Returns a formatted version of the data in the
        certificate provided by the other end of the SSL channel.
        Return None if no certificate was provided, {} if a
        certificate was provided, but not validated."""
        return self._sslobj.peer_certificate(binary_form)

    def cipher(self):
        if not self._sslobj:
            return None
        return self._sslobj.cipher()

    def send(self, data, flags=0, timeout=timeout_default):
        if timeout is timeout_default:
            timeout = self.timeout
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to send() on %s" %
                    self.__class__)
            while True:
                try:
                    v = self._sslobj.write(data)
                except SSLError as x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        if self.timeout == 0.0:
                            return 0
                        sys.exc_clear()
                        self._wait(self._read_event)
                    elif x.args[0] == SSL_ERROR_WANT_WRITE:
                        if self.timeout == 0.0:
                            return 0
                        sys.exc_clear()
                        self._wait(self._write_event)
                    else:
                        raise
                else:
                    return v
        else:
            return socket.send(self, data, flags, timeout)
    # is it possible for sendall() to send some data without encryption if another end shut down SSL?

    def sendall(self, data, flags=0):
        try:
            socket.sendall(self, data)
        except _socket_timeout as ex:
            if self.timeout == 0.0:
                # Python 2 simply *hangs* in this case, which is bad, but
                # Python 3 raises SSLWantWriteError. We do the same.
                raise SSLError(SSL_ERROR_WANT_WRITE)
            # Convert the socket.timeout back to the sslerror
            raise SSLError(*ex.args)

    def sendto(self, *args):
        if self._sslobj:
            raise ValueError("sendto not allowed on instances of %s" %
                             self.__class__)
        return socket.sendto(self, *args)

    def recv(self, buflen=1024, flags=0):
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv() on %s" %
                    self.__class__)
            # QQQ Shouldn't we wrap the SSL_WANT_READ errors as socket.timeout errors to match socket.recv's behavior?
            return self.read(buflen)
        return socket.recv(self, buflen, flags)

    def recv_into(self, buffer, nbytes=None, flags=0):
        if buffer and (nbytes is None):
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv_into() on %s" %
                    self.__class__)
            while True:
                try:
                    tmp_buffer = self.read(nbytes)
                    v = len(tmp_buffer)
                    buffer[:v] = tmp_buffer
                    return v
                except SSLError as x:
                    if x.args[0] == SSL_ERROR_WANT_READ:
                        if self.timeout == 0.0:
                            raise
                        sys.exc_clear()
                        self._wait(self._read_event)
                        continue
                    raise
        else:
            return socket.recv_into(self, buffer, nbytes, flags)

    def recvfrom(self, *args):
        if self._sslobj:
            raise ValueError("recvfrom not allowed on instances of %s" %
                             self.__class__)
        return socket.recvfrom(self, *args)

    def recvfrom_into(self, *args):
        if self._sslobj:
            raise ValueError("recvfrom_into not allowed on instances of %s" %
                             self.__class__)
        return socket.recvfrom_into(self, *args)

    def pending(self):
        if self._sslobj:
            return self._sslobj.pending()
        return 0

    def _sslobj_shutdown(self):
        while True:
            try:
                return self._sslobj.shutdown()
            except SSLError as ex:
                if ex.args[0] == SSL_ERROR_EOF and self.suppress_ragged_eofs:
                    return ''
                if ex.args[0] == SSL_ERROR_WANT_READ:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    self._wait(self._read_event, timeout_exc=_SSLErrorReadTimeout)
                elif ex.args[0] == SSL_ERROR_WANT_WRITE:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    self._wait(self._write_event, timeout_exc=_SSLErrorWriteTimeout)
                else:
                    raise

    def unwrap(self):
        if not self._sslobj:
            raise ValueError("No SSL wrapper around " + str(self))
        s = self._sslobj_shutdown()
        self._sslobj = None
        return socket(_sock=s)

    def shutdown(self, how):
        self._sslobj = None
        socket.shutdown(self, how)

    def close(self):
        if self._makefile_refs < 1:
            self._sslobj = None
            socket.close(self)
        else:
            self._makefile_refs -= 1

    if PYPY:

        def _reuse(self):
            self._makefile_refs += 1

        def _drop(self):
            if self._makefile_refs < 1:
                self.close()
            else:
                self._makefile_refs -= 1

    def do_handshake(self):
        """Perform a TLS/SSL handshake."""
        while True:
            try:
                return self._sslobj.do_handshake()
            except SSLError as ex:
                if ex.args[0] == SSL_ERROR_WANT_READ:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    self._wait(self._read_event, timeout_exc=_SSLErrorHandshakeTimeout)
                elif ex.args[0] == SSL_ERROR_WANT_WRITE:
                    if self.timeout == 0.0:
                        raise
                    sys.exc_clear()
                    self._wait(self._write_event, timeout_exc=_SSLErrorHandshakeTimeout)
                else:
                    raise

    def connect(self, addr): # renamed addr -> address in Python 3 pylint:disable=arguments-renamed
        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""
        # Here we assume that the socket is client-side, and not
        # connected at the time of the call.  We connect it, then wrap it.
        if self._sslobj:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        socket.connect(self, addr)
        if self.ciphers is None:
            self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile, self.certfile,
                                        self.cert_reqs, self.ssl_version,
                                        self.ca_certs)
        else:
            self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile, self.certfile,
                                        self.cert_reqs, self.ssl_version,
                                        self.ca_certs, self.ciphers)
        if self.do_handshake_on_connect:
            self.do_handshake()

    def accept(self):
        """Accepts a new connection from a remote client, and returns
        a tuple containing that new connection wrapped with a server-side
        SSL channel, and the address of the remote client."""
        sock = self._sock
        while True:
            try:
                client_socket, address = sock.accept()
                break
            except socket_error as ex:
                if ex.args[0] != EWOULDBLOCK or self.timeout == 0.0:
                    raise
                sys.exc_clear()
            self._wait(self._read_event)

        sslobj = SSLSocket(client_socket,
                           keyfile=self.keyfile,
                           certfile=self.certfile,
                           server_side=True,
                           cert_reqs=self.cert_reqs,
                           ssl_version=self.ssl_version,
                           ca_certs=self.ca_certs,
                           do_handshake_on_connect=self.do_handshake_on_connect,
                           suppress_ragged_eofs=self.suppress_ragged_eofs,
                           ciphers=self.ciphers)

        return sslobj, address

    def makefile(self, mode='r', bufsize=-1):
        """Make and return a file-like object that
        works with the SSL connection.  Just use the code
        from the socket module."""
        if not PYPY:
            self._makefile_refs += 1
        # close=True so as to decrement the reference count when done with
        # the file-like object.
        return _fileobject(self, mode, bufsize, close=True)

if PYPY or not hasattr(SSLSocket, 'timeout'):
    # PyPy (and certain versions of CPython) doesn't have a direct
    # 'timeout' property on raw sockets, because that's not part of
    # the documented specification. We may wind up wrapping a raw
    # socket (when ssl is used with PyWSGI) or a gevent socket, which
    # does have a read/write timeout property as an alias for
    # get/settimeout, so make sure that's always the case because
    # pywsgi can depend on that.
    SSLSocket.timeout = property(lambda self: self.gettimeout(),
                                 lambda self, value: self.settimeout(value))


_SSLErrorReadTimeout = SSLError('The read operation timed out')
_SSLErrorWriteTimeout = SSLError('The write operation timed out')
_SSLErrorHandshakeTimeout = SSLError('The handshake operation timed out')


def wrap_socket(sock, keyfile=None, certfile=None,
                server_side=False, cert_reqs=CERT_NONE,
                ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True, ciphers=None):
    """Create a new :class:`SSLSocket` instance."""
    return SSLSocket(sock, keyfile=keyfile, certfile=certfile,
                     server_side=server_side, cert_reqs=cert_reqs,
                     ssl_version=ssl_version, ca_certs=ca_certs,
                     do_handshake_on_connect=do_handshake_on_connect,
                     suppress_ragged_eofs=suppress_ragged_eofs,
                     ciphers=ciphers)


def get_server_certificate(addr, ssl_version=PROTOCOL_SSLv23, ca_certs=None):
    """Retrieve the certificate from the server at the specified address,
    and return it as a PEM-encoded string.
    If 'ca_certs' is specified, validate the server cert against it.
    If 'ssl_version' is specified, use it in the connection attempt."""

    if ca_certs is not None:
        cert_reqs = CERT_REQUIRED
    else:
        cert_reqs = CERT_NONE
    s = wrap_socket(socket(), ssl_version=ssl_version,
                    cert_reqs=cert_reqs, ca_certs=ca_certs)
    s.connect(addr)
    dercert = s.getpeercert(True)
    s.close()
    return DER_cert_to_PEM_cert(dercert)


def sslwrap_simple(sock, keyfile=None, certfile=None):
    """A replacement for the old socket.ssl function.  Designed
    for compatibility with Python 2.5 and earlier.  Will disappear in
    Python 3.0."""
    return SSLSocket(sock, keyfile, certfile)
