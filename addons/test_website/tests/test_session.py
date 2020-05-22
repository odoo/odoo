import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteSession(odoo.tests.HttpCase):

    def test_01_run_test(self):
        with self.assertQueryCount(__system__=2185):
            self.start_tour('/', 'test_json_auth')
