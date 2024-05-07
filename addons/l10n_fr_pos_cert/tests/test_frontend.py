import odoo
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestPointOfSaleFRCertHttpCommon(TestPointOfSaleHttpCommon):

    def test_modify_saved_unpaid_order(self):
        self.product_a.available_in_pos = True
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ModifySavedUnpaidOrder', login="pos_user")

    def test_unpaid_order_line_merging(self):
        self.product_a.available_in_pos = True
        self.product_b.available_in_pos = True
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'MergeLinesUnpaidOrder', login="pos_user")
