import requests
from urllib3.util.ssl_ import create_urllib3_context

from .structured_reference import *
from .dict_to_xml import dict_to_xml


class LegacyHTTPAdapter(requests.adapters.HTTPAdapter):
    """ An adapter to allow unsafe legacy renegotiation necessary to connect to
    gravely outdated ETA production servers.
    """

    def init_poolmanager(self, *args, **kwargs):
        # This is not defined before Python 3.12
        # cfr. https://github.com/python/cpython/pull/93927
        # Origin: https://github.com/openssl/openssl/commit/ef51b4b9
        OP_LEGACY_SERVER_CONNECT = 0x04
        context = create_urllib3_context(options=OP_LEGACY_SERVER_CONNECT)
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)
