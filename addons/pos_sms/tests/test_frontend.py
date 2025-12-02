from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestAutofill(TestPointOfSaleHttpCommon):
    def test_01_pos_number_autofill(self):
        self.partner_full.write({'phone': '9876543210'})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.main_pos_config.module_pos_sms = True
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            'AutofillTour',
            login="pos_user",
        )
