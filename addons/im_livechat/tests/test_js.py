# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.web.tests.test_js import qunit_error_checker
from odoo.tests import HttpCase, tagged

@tagged("post_install", "-at_install")
class ExternalTestSuite(HttpCase):
    def test_external_livechat(self):
        # webclient external test suite
        self.browser_js("/web/tests/livechat?mod=web", "", "", login="admin", timeout=1800, error_checker=qunit_error_checker)
