from odoo.tests import tagged
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon


@tagged('post_install', '-at_install')
class TestPosCtaButton(TestConfiguratorCommon):

    def test_01_pos_cta_button(self):
        if not self.env['ir.module.module'].search([('name', '=', 'pos_restaurant_appointment'), ('state', '=', 'installed')]):
            self.skipTest("This test requires the installation of the pos_restaurant_appointment module")

        website_test = self.env['website'].create({
            'name': 'Test website'
        })
        self.start_tour('/website/force/%s?path=%%2Fwebsite%%2Fconfigurator' % website_test.id, 'pos_cta_button', login='admin')
