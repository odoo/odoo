from odoo.tests import tagged
from .test_common import TestHttpBase


@tagged('-at_install', 'post_install')
class TestXSS(TestHttpBase):
    # In case a XSS isn't filtered, it'll load /test_http/fail which logs an error.
    # browser_js only returns when it finds "test successful" in the logs.
    fake_success = "console.log('test successfulness cannot be determined via JS')"
    #                            ^^^^^^^^^^^^^^^

    def test_xss_static(self):
        self.browser_js('/test_http/static/src/img/xss.svg', self.fake_success)

    def test_xss_web_content(self):
        self.browser_js('/web/content/test_http.xss_svg', self.fake_success)

    def test_xss_web_image(self):
        self.browser_js('/web/image/test_http.xss_svg', self.fake_success)
