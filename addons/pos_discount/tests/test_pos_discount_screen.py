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

    def test_service_fee_global_discount(self):
        """
        A fee based on the total after discount includes the global discount line
        in its base. Reduced apart from the products, that line used to add a second
        fee line on every recompute under a discount.
        """
        self.env["product.product"].create({
            "name": "SF Product",
            "available_in_pos": True,
            "list_price": 100.0,
            "taxes_id": [Command.set([])],
        })
        preset_post_discount = self.env["pos.preset"].create({
            "name": "Percent 10 after discount",
            "service_fee": True,
            "service_fee_type": "percent",
            "service_fee_amount": 0.1,
            "service_fee_based_on": "post_discount",
        })
        preset_pre_discount = self.env["pos.preset"].create({
            "name": "Percent 10 before discount",
            "service_fee": True,
            "service_fee_type": "percent",
            "service_fee_amount": 0.1,
            "service_fee_based_on": "pre_discount",
        })
        self.main_pos_config.write({
            "use_presets": True,
            "default_preset_id": preset_post_discount.id,
            "available_preset_ids": [Command.set([preset_pre_discount.id])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosDiscountServiceFeePresetSwitchTour",
            login="pos_user",
        )
