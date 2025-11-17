from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged("post_install", "-at_install")
class TestPosDiscountScreen(TestPointOfSaleHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.main_pos_config.iface_discount = True
        cls.main_pos_config.module_pos_discount = True
        cls.main_pos_config.discount_product_id = cls.env["product.product"].create(
            {
                "name": "discount",
                "available_in_pos": True,
                "pos_categ_ids": [Command.set(cls.pos_desk_misc_test.ids)],
            },
        )
        cls.main_pos_config.discount_pc = 20

    def test_numpad(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "pos_discount_numpad",
            login="pos_user",
        )
