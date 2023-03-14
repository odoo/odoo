# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os import getenv
from odoo.tests import tagged
from .test_static import TestHttpStatic, TestHttpStaticCache


# Small configuration to run the tests against a web server.
# WEB_SERVER_URL=http://localhost:80 odoo-bin -i test_http --test-tags webserver
WEB_SERVER_URL = getenv('WEB_SERVER_URL', 'http://localhost:80')


@tagged('webserver', '-standard', '-at_install')
class TestHttpStaticWebServer(TestHttpStatic, TestHttpStaticCache):
    @classmethod
    def base_url(cls):
        return WEB_SERVER_URL

    def assertDownloadGizeh(self, url, x_sendfile=None, assert_filename='gizeh.png'):
        # X-Sendfile and X-Accel-Redirect http response headers should
        # have been consummed by the web server. We should get the
        # ultimate response which holds the file.
        return super().assertDownloadGizeh(
            url,
            x_sendfile=False,
            assert_filename=assert_filename
        )
