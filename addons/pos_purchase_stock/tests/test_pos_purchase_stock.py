from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.pos_stock.tests.common import CommonPosStockTest


@tagged("post_install", "-at_install")
class TestPosPurchaseStock(CommonPosStockTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        route_mto = cls.pos_config_usd.warehouse_id.mto_pull_id.route_id
        route_mto.active = True
        vendor = cls.env["res.partner"].create({"name": "Vendor"})
        cls.product = cls.env["product.product"].create({
            "name": "MTO Product",
            "available_in_pos": True,
            "is_storable": True,
            "lst_price": 10.0,
            "route_ids": [Command.set(route_mto.ids)],
            "seller_ids": [Command.create({"partner_id": vendor.id, "price": 5.0})],
        })
        cls.pos_config_usd.write({
            "ship_later": True,
            "payment_method_ids": [Command.set(cls.cash_payment_method.ids)],
        })

    def _create_order(self, qty, ship_later=True):
        order, _ = self.create_backend_pos_order({
            "order_data": {
                "partner_id": self.partner.id,
                "shipping_date": ship_later and fields.Date.to_string(fields.Date.today() + relativedelta(days=1)),
            },
            "line_data": [{"product_id": self.product.id, "qty": qty}],
            "payment_data": [{"payment_method_id": self.cash_payment_method.id}],
        })
        return order, order._get_purchase_orders()

    def _refund(self, order, qty):
        refund = self.env["pos.order"].browse(order.refund()["res_id"])
        refund.lines.qty = -qty
        refund.lines._onchange_amount_line_all()
        refund._compute_prices()
        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        self.env["pos.make.payment"].with_context(**payment_context).create({
            "payment_method_id": self.cash_payment_method.id,
        }).check()
        return refund

    def test_smart_buttons(self):
        order, purchase_order = self._create_order(3)
        self.assertEqual(order.purchase_order_count, 1)
        self.assertEqual(purchase_order.pos_order_count, 1)
        self.assertEqual(purchase_order.action_view_pos_orders()["res_id"], order.id)

    def test_sale_without_ship_later_does_not_trigger_mto(self):
        order, purchase_order = self._create_order(3, ship_later=False)
        self.assertFalse(purchase_order)
        self.assertEqual(order.purchase_order_count, 0)

        self._refund(order, 3)
        self.assertFalse(order._get_purchase_orders())

    def test_partial_refund_reduces_purchase_order(self):
        order, purchase_order = self._create_order(3)
        self.assertEqual(purchase_order.order_line.product_qty, 3)

        self._refund(order, 1)
        self.assertEqual(purchase_order.order_line.product_qty, 2)
        self.assertNotEqual(purchase_order.state, "cancel")

    def test_full_refund_cancels_purchase_order(self):
        order, purchase_order = self._create_order(3)
        purchase_order.button_confirm()

        self._refund(order, 3)
        self.assertEqual(purchase_order.order_line.product_qty, 0)
        self.assertEqual(purchase_order.state, "cancel")
