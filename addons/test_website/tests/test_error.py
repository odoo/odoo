import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteError(odoo.tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_run_test(self):
        self.start_tour("/test_error_view", 'test_error_website')

    def test_non_existing_record_slugging(self):
        res = self.url_open('/test_lang_url/lang-0')
        self.assertEqual(res.status_code, 404)
