# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged, HttpCase

from odoo.addons.delivery.tests.common import DeliveryCommon


@tagged("post_install", "-at_install")
class TestChooseDeliveryCarrier(DeliveryCommon, HttpCase):
    _test_user_groups = (
        "product.group_product_manager",
        "sales_team.group_sale_salesman",
    )

    _test_user_name = "Test Sales & Product Manager"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._enable_uom()

        cls.env.company.country_id = cls.env.ref("base.us").id

        cls.product.weight = 1.0
        cls.product_delivery_normal = cls._prepare_carrier_product(
            name="Normal Delivery Charges", list_price=10.0
        )
        cls.normal_delivery = cls._prepare_carrier(
            product=cls.product_delivery_normal,
            name="Normal Delivery Charges",
            delivery_type="fixed",
            fixed_price=10.0,
        )

    def test_get_all_rates(self):
        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "partner_invoice_id": self.partner.id,
            "partner_shipping_id": self.partner.id,
            "carrier_id": self.normal_delivery.id,
            "order_line": [Command.create({"product_id": self.product.id, "price_unit": 750.00})],
        })

        self.start_tour(f"/odoo/sales/{sale_order.id}", "test_get_all_rates", login="admin")

        # check that shipping was added
        line = sale_order.order_line.filtered("is_delivery")
        self.assertEqual(len(line), 1, "Delivery cost is not Added")
