# Part of Odoo. See LICENSE file for full copyright and licensing details.

from os import getenv
from odoo.tests import tagged
from . import test_static


# Small configuration to run the tests against a web server.
# WEB_SERVER_URL=http://localhost:80 odoo-bin -i test_http --test-tags webserver
WEB_SERVER_URL = getenv('WEB_SERVER_URL', 'http://localhost:80')


@tagged('webserver', '-standard', '-at_install')
class TestHttpStaticWebServer(test_static.TestHttpStatic, test_static.TestHttpStaticCache):
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

    def assertDownload(
        self, url, headers, assert_status_code, assert_headers, assert_content=None
    ):
        assert_headers.pop('Content-Length', None)  # nginx compresses on-the-fly
        if assert_headers.pop('X-Sendfile', None):
            assert_headers.pop('X-Accel-Redirect', None)
            assert_content = None
        return super().assertDownload(
            url, headers, assert_status_code, assert_headers, assert_content)

    def test_static_cache3_private(self):
        super().test_static_cache3_private()

        # Extra step: verify that there is no cache leak. Run this test
        # with squid, a web server with http caching capabilities.
        self.authenticate(None, None)
        self.assertDownloadPlaceholder('/web/image/test_http.gizeh_png')
