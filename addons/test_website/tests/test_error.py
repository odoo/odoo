import odoo.tests
from odoo.tools import mute_logger


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteError(odoo.tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_run_test(self):
        self.start_tour("/test_error_view", 'test_error_website')

    def test_02_run_test(self):
        website_snippets = self.env.ref('website.snippets')
        self.env['ir.ui.view'].create([{
            'type': 'qweb',
            'inherit_id': website_snippets.id,
            'arch': """
                <xpath expr="//t[@t-snippet='website.s_parallax']" position="after">
                    <t t-snippet="test_website.s_crashing_snippet" group="content"/>
                </xpath>
            """,
        }])
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_version_outdated', login='admin')
