import logging

import odoo
from odoo.addons.web.tests.test_js import unit_test_error_checker

_logger = logging.getLogger(__name__)


@odoo.tests.tagged("post_install", "-at_install")
class ExternalTestSuite(odoo.tests.HttpCase):
    def fetch_proxy(self, url):
        _logger.info('blocking external request on %s during js tests', url)
        return {
            'body': '',
            'responseCode': 404,
            'responseHeaders': [],
        }

    def test_external_livechat(self):
        # webclient external test suite
        self.browser_js(
            "/web/tests/livechat?headless&loglevel=2&preset=desktop",
            "",
            "",
            login='admin',
            timeout=1800,
            success_signal="[HOOT] test suite succeeded",
            error_checker=unit_test_error_checker
        )
