"""Backwards compatibility alias for :mod:`gevent.resolver.ares`.

.. deprecated:: 1.3
   Use :mod:`gevent.resolver.ares`
"""
import warnings
warnings.warn(
    "gevent.resolver_ares is deprecated and will be removed in 1.5. "
    "Use gevent.resolver.ares instead.",
    DeprecationWarning,
    stacklevel=2
)
del warnings
from gevent.resolver.ares import * # pylint:disable=wildcard-import,unused-wildcard-import
import gevent.resolver.ares as _ares
__all__ = _ares.__all__
del _ares
