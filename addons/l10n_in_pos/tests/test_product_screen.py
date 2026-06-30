from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericIN(TestGenericLocalization):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.company_id.write({
            'country_id': cls.env.ref("base.in")
        })

    def test_product_long_press_india(self):
        """ Test the long press on product to open the product info """
        self.main_pos_config.company_id.country_id.vat_label = 'Should stay GST even after editing vat_label'

        self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100,
            'available_in_pos': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_product_long_press_india')
