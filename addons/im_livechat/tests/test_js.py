# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.web.tests.test_js import unit_test_error_checker


class ExternalTestSuite(odoo.tests.HttpCase):
    def test_external_livechat(self):
        # webclient external test suite
        self.browser_js(
            "/web/tests/livechat?headless&loglevel=2&preset=desktop",
            "",
            "",
            login='admin',
            timeout=1800,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )
