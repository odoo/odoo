# Copyright (c) 2009-2014 Denis Bilenko and gevent contributors. See LICENSE for details.

"""Cooperative low-level networking interface.

This module provides socket operations and some related functions.
The API of the functions and classes matches the API of the corresponding
items in the standard :mod:`socket` module exactly, but the synchronous functions
in this module only block the current greenlet and let the others run.

For convenience, exceptions (like :class:`error <socket.error>` and :class:`timeout <socket.timeout>`)
as well as the constants from the :mod:`socket` module are imported into this module.
"""
# Our import magic sadly makes this warning useless
# pylint: disable=undefined-variable


from gevent._compat import PY311
from gevent._compat import exc_clear
from gevent._util import copy_globals



from gevent import _socket3 as _source


# define some things we're expecting to overwrite; each module
# needs to define these
__implements__ = __dns__ = __all__ = __extensions__ = __imports__ = ()


class error(Exception):
    errno = None


def getfqdn(*args):
    # pylint:disable=unused-argument
    raise NotImplementedError()

copy_globals(_source, globals(),
             dunder_names_to_keep=('__implements__', '__dns__', '__all__',
                                   '__extensions__', '__imports__', '__socket__'),
             cleanup_globs=False)

# The _socket2 and _socket3 don't import things defined in
# __extensions__, to help avoid confusing reference cycles in the
# documentation and to prevent importing from the wrong place, but we
# *do* need to expose them here. (NOTE: This may lead to some sphinx
# warnings like:
#    WARNING: missing attribute mentioned in :members: or __all__:
#             module gevent._socket2, attribute cancel_wait
# These can be ignored.)
from gevent import _socketcommon
copy_globals(_socketcommon, globals(),
             only_names=_socketcommon.__extensions__)

try:
    _GLOBAL_DEFAULT_TIMEOUT = __socket__._GLOBAL_DEFAULT_TIMEOUT
except AttributeError:
    _GLOBAL_DEFAULT_TIMEOUT = object()


def create_connection(address, timeout=_GLOBAL_DEFAULT_TIMEOUT, source_address=None, *,
                      all_errors=False):
    """
    create_connection(address, timeout=None, source_address=None, *, all_errors=False) -> socket

    Connect to *address* and return the :class:`gevent.socket.socket`
    object.

    Convenience function. Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object. Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect. If no *timeout* is supplied, the
    global default timeout setting returned by
    :func:`getdefaulttimeout` is used. If *source_address* is set it
    must be a tuple of (host, port) for the socket to bind as a source
    address before making the connection. A host of '' or port 0 tells
    the OS to use the default.

    .. versionchanged:: 20.6.0
        If the host part of the address includes an IPv6 scope ID,
        it will be used instead of ignored, if the platform supplies
        :func:`socket.inet_pton`.
    .. versionchanged:: 22.08.0
        Add the *all_errors* argument. This only has meaning on Python 3.11+;
        it is a programming error to pass it on earlier versions.
    .. versionchanged:: 23.7.0
        You can pass a value for ``all_errors`` on any version of Python.
        It is forced to false for any version before 3.11 inside the function.
    """
    # Sigh. This function is a near-copy of the CPython implementation.
    # Even though we simplified some things, it's still a little complex to
    # cope with error handling, which got even more complicated in 3.11.
    # pylint:disable=too-many-locals,too-many-branches
    if not PY311:
        all_errors = False

    host, port = address
    exceptions = []
    # getaddrinfo is documented as returning a list, but our interface
    # is pluggable, so be sure it does.
    addrs = list(getaddrinfo(host, port, 0, SOCK_STREAM))
    if not addrs:
        raise error("getaddrinfo returns an empty list")

    for res in addrs:
        af, socktype, proto, _canonname, sa = res
        sock = None
        try:
            sock = socket(af, socktype, proto)
            if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)

        except error as exc:
            if not all_errors:
                exceptions = [exc] # raise only the last error
            else:
                exceptions.append(exc)
            del exc # cycle
            if sock is not None:
                sock.close()
            sock = None
            if res is addrs[-1]:
                if not all_errors:
                    del exceptions[:]
                    raise
                try:
                    raise ExceptionGroup("create_connection failed", exceptions)
                finally:
                    # Break explicitly a reference cycle
                    del exceptions[:]
            # without exc_clear(), if connect() fails once, the socket
            # is referenced by the frame in exc_info and the next
            # bind() fails (see test__socket.TestCreateConnection)
            # that does not happen with regular sockets though,
            # because _socket.socket.connect() is a built-in. this is
            # similar to "getnameinfo loses a reference" failure in
            # test_socket.py
            exc_clear()
        except BaseException:
            # Things like GreenletExit,  Timeout and KeyboardInterrupt.
            # These get raised immediately, being sure to
            # close the socket
            if sock is not None:
                sock.close()
            sock = None
            raise
        else:
            # break reference cycles
            del exceptions[:]
            try:
                return sock
            finally:
                sock = None


# This is promised to be in the __all__ of the _source, but, for circularity reasons,
# we implement it in this module. Mostly for documentation purposes, put it
# in the _source too.
_source.create_connection = create_connection
