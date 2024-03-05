import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteError(odoo.tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_run_test(self):
        self.start_tour("/test_error_view", 'test_error_website')

    def test_02_bad_ro_callback(self):
        res = self.url_open('/test_bad_ro_callback')
        self.assertEqual(res.status_code, 500)
        # should it be a nice website page? or is the dull black on
        # white "500 Internal Server Error" fine?
