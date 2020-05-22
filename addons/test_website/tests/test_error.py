import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteError(odoo.tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_run_test(self):
        with self.assertQueryCount(__system__=1089, demo=0):
            self.start_tour("/test_error_view", 'test_error_website')
