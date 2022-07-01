from odoo.tests import tagged
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon

@tagged('post_install', '-at_install')
class TestAutomaticEditor(TestConfiguratorCommon):

    def test_01_automatic_editor_on_new_website(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        # We create a lang because if the new website is displayed in this lang
        # instead of the website's default one, the editor won't automatically
        # start.
        self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'automatic_editor_on_new_website', login='admin')
