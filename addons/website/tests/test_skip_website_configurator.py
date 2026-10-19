from odoo.tests import tagged
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon


@tagged('post_install', '-at_install')
class TestAutomaticEditor(TestConfiguratorCommon):

    def test_skip_website_configurator(self):
        self.start_tour('/odoo/action-website.action_website_configuration', 'skip_website_configurator', login='admin')
