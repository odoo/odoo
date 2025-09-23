from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged
from odoo.fields import Command


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericLocalization(TestPointOfSaleHttpCommon):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.name = "AAAA Generic Partner"
        cls.partner_a.vat = "32345678"
        cls.whiteboard_pen.write({
            'standard_price': 10.0,
            'taxes_id': [Command.link(cls.tax_sale_a.id)]
        })

        cls.wall_shelf.write({
            'standard_price': 10.0,
            'taxes_id': [Command.link(cls.tax_sale_a.id)]
        })

    def test_generic_localization(self):
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id
        self.start_pos_tour("generic_localization_tour", login="accountman")
        self.assertEqual(current_session.state, 'closed')
