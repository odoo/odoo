from unittest import SkipTest


import gevent.testing as greentest

from . import test__example_wsgiserver


@greentest.skipOnCI("Timing issues sometimes lead to a connection refused")
@greentest.skipWithoutExternalNetwork("Tries to reach google.com")
class Test_webproxy(test__example_wsgiserver.Test_wsgiserver):
    example = 'webproxy.py'

    def _run_all_tests(self):
        status, data = self.read('/')
        self.assertEqual(status, '200 OK')
        self.assertIn(b"gevent example", data)
        status, data = self.read('/http://www.google.com')
        self.assertEqual(status, '200 OK')
        self.assertIn(b'google', data.lower())

    def test_a_blocking_client(self):
        # Not applicable
        raise SkipTest("Not applicable")



if __name__ == '__main__':
    greentest.main()
