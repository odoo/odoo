from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPoSAvatax(TestPointOfSaleHttpCommon):
    def test_pos_avatax_flow(self):
        self.main_pos_config.module_pos_avatax = True
        self.main_pos_config.open_ui()
        self.start_pos_tour('test_pos_avatax_flow', login="accountman")
