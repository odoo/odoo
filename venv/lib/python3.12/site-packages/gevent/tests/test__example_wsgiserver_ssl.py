import ssl

import gevent.testing as greentest

from gevent.testing import params

from . import test__example_wsgiserver


@greentest.skipOnCI("Timing issues sometimes lead to a connection refused")
class Test_wsgiserver_ssl(test__example_wsgiserver.Test_wsgiserver):
    example = 'wsgiserver_ssl.py'
    URL = 'https://%s:8443' % (params.DEFAULT_LOCAL_HOST_ADDR,)
    PORT = 8443
    _use_ssl = True

    if hasattr(ssl, '_create_unverified_context'):
        # Disable verification for our self-signed cert
        # on Python >= 2.7.9 and 3.4
        ssl_ctx = ssl._create_unverified_context()


if __name__ == '__main__':
    greentest.main()
