from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericLocalization(TestPointOfSaleHttpCommon):
    allow_inherited_tests_method=True
    def setUp(self):
        super().setUp()
        self.genericTourName = 'generic_localization_tour'
    def test_generic_localization(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour(self.genericTourName)
