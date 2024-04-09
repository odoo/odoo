"""
Secure Sockets Layer (SSL/TLS) module.
"""
from gevent._compat import PY2
from gevent._util import copy_globals

# things we expect to override, here for static analysis
def wrap_socket(_sock, **_kwargs):
    # pylint:disable=unused-argument
    raise NotImplementedError()

if PY2:
    if hasattr(__import__('ssl'), 'SSLContext'):
        # It's not sufficient to check for >= 2.7.9; some distributions
        # have backported most of PEP 466. Try to accommodate them. See Issue #702.
        # We're just about to import ssl anyway so it's fine to import it here, just
        # don't pollute the namespace
        from gevent import _sslgte279 as _source
    else: # pragma: no cover
        from gevent import _ssl2 as _source
        import warnings
        warnings.warn(
            "This version of Python has an insecure SSL implementation. "
            "gevent is no longer tested with it, and support will be removed "
            "in gevent 1.5. Please use Python 2.7.9 or newer.",
            DeprecationWarning,
            stacklevel=2,
        )
        del warnings
else:
    # Py3
    from gevent import _ssl3 as _source # pragma: no cover


copy_globals(_source, globals())
