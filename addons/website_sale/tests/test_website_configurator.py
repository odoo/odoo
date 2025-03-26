# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon


@tagged('post_install', '-at_install')
class TestWebsiteConfigurator(TestConfiguratorCommon):

    def test_website_configurator(self):
        website = self.env['website'].create({'name': "E-commerce website"})
        self.start_tour(
            '/website/force/%s?path=%%2Fwebsite%%2Fconfigurator' % website.id,
            'website_sale_configurator',
            login='admin',
        )
