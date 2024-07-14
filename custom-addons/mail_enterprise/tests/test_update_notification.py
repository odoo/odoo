# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.test_cloc import TestClocCustomization
from ast import literal_eval


class TestClocICP(TestClocCustomization):

    def test_check_cloc_result_in_icp(self):
        self.create_field('x_invoice_count')
        message = self.env["publisher_warranty.contract"]._get_message()
        self.assertTrue('maintenance' in message)
        store_cloc = self.env["ir.config_parameter"].get_param('publisher_warranty.cloc')
        self.assertEqual(literal_eval(store_cloc)['modules']['odoo/studio'], 1)
