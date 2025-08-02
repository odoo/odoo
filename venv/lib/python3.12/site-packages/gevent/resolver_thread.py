"""Backwards compatibility alias for :mod:`gevent.resolver.thread`.

.. deprecated:: 1.3
   Use :mod:`gevent.resolver.thread`
"""
import warnings
warnings.warn(
    "gevent.resolver_thread is deprecated and will be removed in 1.5. "
    "Use gevent.resolver.thread instead.",
    DeprecationWarning,
    stacklevel=2
)
del warnings
from gevent.resolver.thread import * # pylint:disable=wildcard-import,unused-wildcard-import
import gevent.resolver.thread as _thread
__all__ = _thread.__all__
del _thread
