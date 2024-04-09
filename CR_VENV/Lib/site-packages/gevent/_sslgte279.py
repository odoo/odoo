# Wrapper module for _ssl. Written by Bill Janssen.
# Ported to gevent by Denis Bilenko.
"""SSL wrapper for socket objects on Python 2.7.9 and above.

For the documentation, refer to :mod:`ssl` module manual.

This module implements cooperative SSL socket wrappers.
"""

from __future__ import absolute_import
# Our import magic sadly makes this warning useless
# pylint: disable=undefined-variable
# pylint: disable=too-many-instance-attributes,too-many-locals,too-many-statements,too-many-branches
# pylint: disable=arguments-differ,too-many-public-methods

import ssl as __ssl__

_ssl = __ssl__._ssl # pylint:disable=no-member

import errno
from gevent._socket2 import socket
from gevent._socket2 import AF_INET # pylint:disable=no-name-in-module
from gevent.socket import timeout_default
from gevent.socket import create_connection
from gevent.socket import error as socket_error
from gevent.socket import timeout as _socket_timeout
from gevent._compat import PYPY
from gevent._util import copy_globals

__implements__ = [
    'SSLContext',
    'SSLSocket',
    'wrap_socket',
    'get_server_certificate',
    'create_default_context',
    '_create_unverified_context',
    '_create_default_https_context',
    '_create_stdlib_context',
    '_fileobject',
]

# Import all symbols from Python's ssl.py, except those that we are implementing
# and "private" symbols.
__imports__ = copy_globals(__ssl__, globals(),
                           # SSLSocket *must* subclass gevent.socket.socket; see issue 597 and 801
                           names_to_ignore=__implements__ + ['socket', 'create_connection'],
                           dunder_names_to_keep=())

try:
    _delegate_methods # pylint:disable=used-before-assignment
except NameError: # PyPy doesn't expose this detail
    _delegate_methods = ('recv', 'recvfrom', 'recv_into', 'recvfrom_into', 'send', 'sendto')

__all__ = __implements__ + __imports__
if 'namedtuple' in __all__:
    __all__.remove('namedtuple')

# See notes in _socket2.py. Python 3 returns much nicer
# `io` object wrapped around a SocketIO class.
if hasattr(__ssl__, '_fileobject'):
    assert not hasattr(__ssl__._fileobject, '__enter__') # pylint:disable=no-member

class _fileobject(getattr(__ssl__, '_fileobject', object)): # pylint:disable=no-member

    def __enter__(self):
        return self

    def __exit__(self, *args):
        # pylint:disable=no-member
        if not self.closed:
            self.close()


orig_SSLContext = __ssl__.SSLContext # pylint: disable=no-member

class SSLContext(orig_SSLContext):

    __slots__ = ()

    def wrap_socket(self, sock, server_side=False,
                    do_handshake_on_connect=True,
                    suppress_ragged_eofs=True,
                    server_hostname=None):
        return SSLSocket(sock=sock, server_side=server_side,
                         do_handshake_on_connect=do_handshake_on_connect,
                         suppress_ragged_eofs=suppress_ragged_eofs,
                         server_hostname=server_hostname,
                         _context=self)


def create_default_context(purpose=Purpose.SERVER_AUTH, cafile=None,
                           capath=None, cadata=None):
    """Create a SSLContext object with default settings.

    NOTE: The protocol and settings may change anytime without prior
          deprecation. The values represent a fair balance between maximum
          compatibility and security.
    """
    if not isinstance(purpose, _ASN1Object):
        raise TypeError(purpose)

    context = SSLContext(PROTOCOL_SSLv23)

    # SSLv2 considered harmful.
    context.options |= OP_NO_SSLv2 # pylint:disable=no-member

    # SSLv3 has problematic security and is only required for really old
    # clients such as IE6 on Windows XP
    context.options |= OP_NO_SSLv3 # pylint:disable=no-member

    # disable compression to prevent CRIME attacks (OpenSSL 1.0+)
    context.options |= getattr(_ssl, "OP_NO_COMPRESSION", 0) # pylint:disable=no-member

    if purpose == Purpose.SERVER_AUTH:
        # verify certs and host name in client mode
        context.verify_mode = CERT_REQUIRED
        context.check_hostname = True # pylint: disable=attribute-defined-outside-init
    elif purpose == Purpose.CLIENT_AUTH:
        # Prefer the server's ciphers by default so that we get stronger
        # encryption
        context.options |= getattr(_ssl, "OP_CIPHER_SERVER_PREFERENCE", 0) # pylint:disable=no-member

        # Use single use keys in order to improve forward secrecy
        context.options |= getattr(_ssl, "OP_SINGLE_DH_USE", 0) # pylint:disable=no-member
        context.options |= getattr(_ssl, "OP_SINGLE_ECDH_USE", 0) # pylint:disable=no-member

        # disallow ciphers with known vulnerabilities
        context.set_ciphers(_RESTRICTED_SERVER_CIPHERS)

    if cafile or capath or cadata:
        context.load_verify_locations(cafile, capath, cadata)
    elif context.verify_mode != CERT_NONE:
        # no explicit cafile, capath or cadata but the verify mode is
        # CERT_OPTIONAL or CERT_REQUIRED. Let's try to load default system
        # root CA certificates for the given purpose. This may fail silently.
        context.load_default_certs(purpose)
    return context

def _create_unverified_context(protocol=PROTOCOL_SSLv23, cert_reqs=None,
                               check_hostname=False, purpose=Purpose.SERVER_AUTH,
                               certfile=None, keyfile=None,
                               cafile=None, capath=None, cadata=None):
    """Create a SSLContext object for Python stdlib modules

    All Python stdlib modules shall use this function to create SSLContext
    objects in order to keep common settings in one place. The configuration
    is less restrict than create_default_context()'s to increase backward
    compatibility.
    """
    if not isinstance(purpose, _ASN1Object):
        raise TypeError(purpose)

    context = SSLContext(protocol)
    # SSLv2 considered harmful.
    context.options |= OP_NO_SSLv2 # pylint:disable=no-member
    # SSLv3 has problematic security and is only required for really old
    # clients such as IE6 on Windows XP
    context.options |= OP_NO_SSLv3 # pylint:disable=no-member

    if cert_reqs is not None:
        context.verify_mode = cert_reqs
    context.check_hostname = check_hostname # pylint: disable=attribute-defined-outside-init

    if keyfile and not certfile:
        raise ValueError("certfile must be specified")
    if certfile or keyfile:
        context.load_cert_chain(certfile, keyfile)

    # load CA root certs
    if cafile or capath or cadata:
        context.load_verify_locations(cafile, capath, cadata)
    elif context.verify_mode != CERT_NONE:
        # no explicit cafile, capath or cadata but the verify mode is
        # CERT_OPTIONAL or CERT_REQUIRED. Let's try to load default system
        # root CA certificates for the given purpose. This may fail silently.
        context.load_default_certs(purpose)

    return context

# Used by http.client if no context is explicitly passed.
_create_default_https_context = create_default_context


# Backwards compatibility alias, even though it's not a public name.
_create_stdlib_context = _create_unverified_context

class SSLSocket(socket):
    """
    gevent `ssl.SSLSocket <https://docs.python.org/2/library/ssl.html#ssl-sockets>`_
    for Pythons >= 2.7.9 but less than 3.
    """

    def __init__(self, sock=None, keyfile=None, certfile=None,
                 server_side=False, cert_reqs=CERT_NONE,
                 ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                 do_handshake_on_connect=True,
                 family=AF_INET, type=SOCK_STREAM, proto=0, fileno=None,
                 suppress_ragged_eofs=True, npn_protocols=None, ciphers=None,
                 server_hostname=None,
                 _context=None):
        # fileno is ignored
        # pylint: disable=unused-argument
        if _context:
            self._context = _context
        else:
            if server_side and not certfile:
                raise ValueError("certfile must be specified for server-side "
                                 "operations")
            if keyfile and not certfile:
                raise ValueError("certfile must be specified")
            if certfile and not keyfile:
                keyfile = certfile
            self._context = SSLContext(ssl_version)
            self._context.verify_mode = cert_reqs
            if ca_certs:
                self._context.load_verify_locations(ca_certs)
            if certfile:
                self._context.load_cert_chain(certfile, keyfile)
            if npn_protocols:
                self._context.set_npn_protocols(npn_protocols)
            if ciphers:
                self._context.set_ciphers(ciphers)
            self.keyfile = keyfile
            self.certfile = certfile
            self.cert_reqs = cert_reqs
            self.ssl_version = ssl_version
            self.ca_certs = ca_certs
            self.ciphers = ciphers
        # Can't use sock.type as other flags (such as SOCK_NONBLOCK) get
        # mixed in.
        if sock.getsockopt(SOL_SOCKET, SO_TYPE) != SOCK_STREAM:
            raise NotImplementedError("only stream sockets are supported")

        if PYPY:
            socket.__init__(self, _sock=sock)
            sock._drop()
        else:
            # CPython: XXX: Must pass the underlying socket, not our
            # potential wrapper; test___example_servers fails the SSL test
            # with a client-side EOF error. (Why?)
            socket.__init__(self, _sock=sock._sock)

        # The initializer for socket overrides the methods send(), recv(), etc.
        # in the instance, which we don't need -- but we want to provide the
        # methods defined in SSLSocket.
        for attr in _delegate_methods:
            try:
                delattr(self, attr)
            except AttributeError:
                pass
        if server_side and server_hostname:
            raise ValueError("server_hostname can only be specified "
                             "in client mode")
        if self._context.check_hostname and not server_hostname:
            raise ValueError("check_hostname requires server_hostname")
        self.server_side = server_side
        self.server_hostname = server_hostname
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self.settimeout(sock.gettimeout())

        # See if we are connected
        try:
            self.getpeername()
        except socket_error as e:
            if e.errno != errno.ENOTCONN:
                raise
            connected = False
        else:
            connected = True

        self._makefile_refs = 0
        self._closed = False
        self._sslobj = None
        self._connected = connected
        if connected:
            # create the SSL object
            try:
                self._sslobj = self._context._wrap_socket(self._sock, server_side,
                                                          server_hostname, ssl_sock=self)
                if do_handshake_on_connect:
                    timeout = self.gettimeout()
                    if timeout == 0.0:
                        # non-blocking
                        raise ValueError("do_handshake_on_connect should not be specified for non-blocking sockets")
                    self.do_handshake()

            except socket_error as x:
                self.close()
                raise x


    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, ctx):
        self._context = ctx
        self._sslobj.context = ctx

    def dup(self):
        raise NotImplementedError("Can't dup() %s instances" %
                                  self.__class__.__name__)

    def _checkClosed(self, msg=None):
        # raise an exception here if you wish to check for spurious closes
        pass

    def _check_connected(self):
        if not self._connected:
            # getpeername() will raise ENOTCONN if the socket is really
            # not connected; note that we can be connected even without
            # _connected being set, e.g. if connect() first returned
            # EAGAIN.
            self.getpeername()

    def read(self, len=1024, buffer=None):
        """Read up to LEN bytes and return them.
        Return zero-length string on EOF."""
        self._checkClosed()

        while 1:
            if not self._sslobj:
                raise ValueError("Read on closed or unwrapped SSL socket.")
            if len == 0:
                return b'' if buffer is None else 0
            if len < 0 and buffer is None:
                # This is handled natively in python 2.7.12+
                raise ValueError("Negative read length")
            try:
                if buffer is not None:
                    return self._sslobj.read(len, buffer)
                return self._sslobj.read(len or 1024)
            except SSLWantReadError:
                if self.timeout == 0.0:
                    raise
                self._wait(self._read_event, timeout_exc=_SSLErrorReadTimeout)
            except SSLWantWriteError:
                if self.timeout == 0.0:
                    raise
                # note: using _SSLErrorReadTimeout rather than _SSLErrorWriteTimeout below is intentional
                self._wait(self._write_event, timeout_exc=_SSLErrorReadTimeout)
            except SSLError as ex:
                if ex.args[0] == SSL_ERROR_EOF and self.suppress_ragged_eofs:
                    if buffer is not None:
                        return 0
                    return b''
                raise

    def write(self, data):
        """Write DATA to the underlying SSL channel.  Returns
        number of bytes of DATA actually transmitted."""
        self._checkClosed()

        while 1:
            if not self._sslobj:
                raise ValueError("Write on closed or unwrapped SSL socket.")

            try:
                return self._sslobj.write(data)
            except SSLError as ex:
                if ex.args[0] == SSL_ERROR_WANT_READ:
                    if self.timeout == 0.0:
                        raise
                    self._wait(self._read_event, timeout_exc=_SSLErrorWriteTimeout)
                elif ex.args[0] == SSL_ERROR_WANT_WRITE:
                    if self.timeout == 0.0:
                        raise
                    self._wait(self._write_event, timeout_exc=_SSLErrorWriteTimeout)
                else:
                    raise

    def getpeercert(self, binary_form=False):
        """Returns a formatted version of the data in the
        certificate provided by the other end of the SSL channel.
        Return None if no certificate was provided, {} if a
        certificate was provided, but not validated."""

        self._checkClosed()
        self._check_connected()
        return self._sslobj.peer_certificate(binary_form)

    def selected_npn_protocol(self):
        self._checkClosed()
        if not self._sslobj or not _ssl.HAS_NPN:
            return None
        return self._sslobj.selected_npn_protocol()

    if hasattr(_ssl, 'HAS_ALPN'):
        # 2.7.10+
        def selected_alpn_protocol(self):
            self._checkClosed()
            if not self._sslobj or not _ssl.HAS_ALPN: # pylint:disable=no-member
                return None
            return self._sslobj.selected_alpn_protocol()

    def cipher(self):
        self._checkClosed()
        if not self._sslobj:
            return None
        return self._sslobj.cipher()

    def compression(self):
        self._checkClosed()
        if not self._sslobj:
            return None
        return self._sslobj.compression()

    def __check_flags(self, meth, flags):
        if flags != 0:
            raise ValueError(
                "non-zero flags not allowed in calls to %s on %s" %
                (meth, self.__class__))

    def send(self, data, flags=0, timeout=timeout_default):
        self._checkClosed()
        self.__check_flags('send', flags)

        if timeout is timeout_default:
            timeout = self.timeout

        if not self._sslobj:
            return socket.send(self, data, flags, timeout)

        while True:
            try:
                return self._sslobj.write(data)
            except SSLWantReadError:
                if self.timeout == 0.0:
                    return 0
                self._wait(self._read_event)
            except SSLWantWriteError:
                if self.timeout == 0.0:
                    return 0
                self._wait(self._write_event)

    def sendto(self, data, flags_or_addr, addr=None):
        self._checkClosed()
        if self._sslobj:
            raise ValueError("sendto not allowed on instances of %s" %
                             self.__class__)
        if addr is None:
            return socket.sendto(self, data, flags_or_addr)
        return socket.sendto(self, data, flags_or_addr, addr)

    def sendmsg(self, *args, **kwargs):
        # Ensure programs don't send data unencrypted if they try to
        # use this method.
        raise NotImplementedError("sendmsg not allowed on instances of %s" %
                                  self.__class__)

    def sendall(self, data, flags=0):
        self._checkClosed()
        self.__check_flags('sendall', flags)

        try:
            socket.sendall(self, data)
        except _socket_timeout as ex:
            if self.timeout == 0.0:
                # Python 2 simply *hangs* in this case, which is bad, but
                # Python 3 raises SSLWantWriteError. We do the same.
                raise SSLWantWriteError("The operation did not complete (write)")
            # Convert the socket.timeout back to the sslerror
            raise SSLError(*ex.args)

    def recv(self, buflen=1024, flags=0):
        self._checkClosed()
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv() on %s" %
                    self.__class__)
            if buflen == 0:
                return b''
            return self.read(buflen)
        return socket.recv(self, buflen, flags)

    def recv_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if buffer is not None and (nbytes is None):
            # Fix for python bug #23804: bool(bytearray()) is False,
            # but we should read 0 bytes.
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        if self._sslobj:
            if flags != 0:
                raise ValueError(
                    "non-zero flags not allowed in calls to recv_into() on %s" %
                    self.__class__)
            return self.read(nbytes, buffer)
        return socket.recv_into(self, buffer, nbytes, flags)

    def recvfrom(self, buflen=1024, flags=0):
        self._checkClosed()
        if self._sslobj:
            raise ValueError("recvfrom not allowed on instances of %s" %
                             self.__class__)
        return socket.recvfrom(self, buflen, flags)

    def recvfrom_into(self, buffer, nbytes=None, flags=0):
        self._checkClosed()
        if self._sslobj:
            raise ValueError("recvfrom_into not allowed on instances of %s" %
                             self.__class__)
        return socket.recvfrom_into(self, buffer, nbytes, flags)

    def recvmsg(self, *args, **kwargs):
        raise NotImplementedError("recvmsg not allowed on instances of %s" %
                                  self.__class__)

    def recvmsg_into(self, *args, **kwargs):
        raise NotImplementedError("recvmsg_into not allowed on instances of "
                                  "%s" % self.__class__)

    def pending(self):
        self._checkClosed()
        if self._sslobj:
            return self._sslobj.pending()
        return 0

    def shutdown(self, how):
        self._checkClosed()
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

        s = self._sock
        try:
            s = self._sslobj_shutdown()
        except socket_error as ex:
            if ex.args[0] != 0:
                raise

        self._sslobj = None
        # match _ssl2; critical to drop/reuse here on PyPy
        # XXX: _ssl3 returns an SSLSocket. Is that what the standard lib does on
        # Python 2? Should we do that?
        return socket(_sock=s)

    def _real_close(self):
        self._sslobj = None
        socket._real_close(self) # pylint: disable=no-member

    def do_handshake(self):
        """Perform a TLS/SSL handshake."""
        self._check_connected()
        while True:
            try:
                self._sslobj.do_handshake()
                break
            except SSLWantReadError:
                if self.timeout == 0.0:
                    raise
                self._wait(self._read_event, timeout_exc=_SSLErrorHandshakeTimeout)
            except SSLWantWriteError:
                if self.timeout == 0.0:
                    raise
                self._wait(self._write_event, timeout_exc=_SSLErrorHandshakeTimeout)

        if self._context.check_hostname:
            if not self.server_hostname:
                raise ValueError("check_hostname needs server_hostname "
                                 "argument")
            match_hostname(self.getpeercert(), self.server_hostname)

    def _real_connect(self, addr, connect_ex):
        if self.server_side:
            raise ValueError("can't connect in server-side mode")
        # Here we assume that the socket is client-side, and not
        # connected at the time of the call.  We connect it, then wrap it.
        if self._connected:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        self._sslobj = self._context._wrap_socket(self._sock, False, self.server_hostname, ssl_sock=self)
        try:
            if connect_ex:
                rc = socket.connect_ex(self, addr)
            else:
                rc = None
                socket.connect(self, addr)
            if not rc:
                self._connected = True
                if self.do_handshake_on_connect:
                    self.do_handshake()
            return rc
        except socket_error:
            self._sslobj = None
            raise

    def connect(self, addr): # pylint:disable=arguments-renamed
        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""
        self._real_connect(addr, False)

    def connect_ex(self, addr): # pylint:disable=arguments-renamed
        """Connects to remote ADDR, and then wraps the connection in
        an SSL channel."""
        return self._real_connect(addr, True)

    def accept(self):
        """Accepts a new connection from a remote client, and returns
        a tuple containing that new connection wrapped with a server-side
        SSL channel, and the address of the remote client."""

        newsock, addr = socket.accept(self)
        newsock._drop_events_and_close(closefd=False) # Why, again?
        newsock = self._context.wrap_socket(newsock,
                                            do_handshake_on_connect=self.do_handshake_on_connect,
                                            suppress_ragged_eofs=self.suppress_ragged_eofs,
                                            server_side=True)
        return newsock, addr

    def makefile(self, mode='r', bufsize=-1):

        """Make and return a file-like object that
        works with the SSL connection.  Just use the code
        from the socket module."""
        if not PYPY:
            self._makefile_refs += 1
        # close=True so as to decrement the reference count when done with
        # the file-like object.
        return _fileobject(self, mode, bufsize, close=True)

    def get_channel_binding(self, cb_type="tls-unique"):
        """Get channel binding data for current connection.  Raise ValueError
        if the requested `cb_type` is not supported.  Return bytes of the data
        or None if the data is not available (e.g. before the handshake).
        """
        if cb_type not in CHANNEL_BINDING_TYPES:
            raise ValueError("Unsupported channel binding type")
        if cb_type != "tls-unique":
            raise NotImplementedError(
                "{0} channel binding type not implemented"
                .format(cb_type))
        if self._sslobj is None:
            return None
        return self._sslobj.tls_unique_cb()

    def version(self):
        """
        Return a string identifying the protocol version used by the
        current SSL channel, or None if there is no established channel.
        """
        if self._sslobj is None:
            return None
        return self._sslobj.version()

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
                suppress_ragged_eofs=True,
                ciphers=None):

    return SSLSocket(sock=sock, keyfile=keyfile, certfile=certfile,
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

    _, _ = addr
    if ca_certs is not None:
        cert_reqs = CERT_REQUIRED
    else:
        cert_reqs = CERT_NONE
    context = _create_stdlib_context(ssl_version,
                                     cert_reqs=cert_reqs,
                                     cafile=ca_certs)
    with closing(create_connection(addr)) as sock:
        with closing(context.wrap_socket(sock)) as sslsock:
            dercert = sslsock.getpeercert(True)
    return DER_cert_to_PEM_cert(dercert)
