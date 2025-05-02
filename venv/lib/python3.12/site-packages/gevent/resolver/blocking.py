# Copyright (c) 2018  gevent contributors. See LICENSE for details.

import _socket

__all__ = [
    'Resolver',
]

class Resolver(object):
    """
    A resolver that directly uses the system's resolver functions.

    .. caution::

        This resolver is *not* cooperative.

    This resolver has the lowest overhead of any resolver and
    typically approaches the speed of the unmodified :mod:`socket`
    functions. However, it is not cooperative, so if name resolution
    blocks, the entire thread and all its greenlets will be blocked.

    This can be useful during debugging, or it may be a good choice if
    your operating system provides a good caching resolver (such as
    macOS's Directory Services) that is usually very fast and
    functionally non-blocking.

    .. versionchanged:: 1.3a2
       This was previously undocumented and existed in :mod:`gevent.socket`.

    """

    def __init__(self, hub=None):
        pass

    def close(self):
        pass

    for method in (
            'gethostbyname',
            'gethostbyname_ex',
            'getaddrinfo',
            'gethostbyaddr',
            'getnameinfo'
    ):
        locals()[method] = staticmethod(getattr(_socket, method))
