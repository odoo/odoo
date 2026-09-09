from odoo.tests import Form, common


@common.tagged("post_install", "-at_install")
class TestDeliveryCost(common.TransactionCase):
    def test_delivery_real_cost(self):
        self.partner_18 = self.env["res.partner"].create({"name": "My Test Customer"})
        self.product_4 = self.env["product.product"].create(
            {"name": "A product to deliver", "weight": 1.0}
        )

        product_delivery = self.env["product.product"].create(
            {
                "name": "Delivery Charges",
                "type": "service",
                "list_price": 40.0,
                "categ_id": self.env.ref("delivery.product_category_deliveries").id,
            }
        )
        delivery_carrier = self.env["delivery.carrier"].create(
            {
                "name": "Delivery Now Free Over 100",
                "fixed_price": 40,
                "margin": 50,
                "delivery_type": "fixed",
                "invoice_policy": "real",
                "product_id": product_delivery.id,
                "free_over": False,
            }
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_18.id,
                "partner_invoice_id": self.partner_18.id,
                "partner_shipping_id": self.partner_18.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "PC Assamble + 2GB RAM",
                            "product_id": self.product_4.id,
                            "product_qty": 2,
                            "price_unit": 120.00,
                        },
                    )
                ],
            }
        )

        delivery_wizard = Form(
            self.env["choose.delivery.carrier"].with_context(
                {
                    "default_order_id": so.id,
                    "default_carrier_id": delivery_carrier.id,
                }
            )
        )
        delivery_wizard.save().button_confirm()

        delivery_line = so.line_ids.filtered("is_delivery")
        self.assertEqual(len(delivery_line), 1)
        self.assertEqual(
            delivery_line.price_unit,
            0,
            "The invoicing policy of the carrier is set to 'real cost' and that cost is not yet "
            "known, hence the 0 value",
        )
        so.action_confirm()

        picking = so.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, so.carrier_id.id)
        picking.move_ids[0].quantity = 1.0
        self.assertGreater(picking.shipping_weight, 0.0)

        picking.move_ids.picked = True
        picking._action_done()
        self.assertEqual(picking.carrier_price, 40.0)
        self.assertEqual(delivery_line.price_unit, picking.carrier_price)

        bo = picking.backorder_ids
        bo.move_ids[0].quantity = 1.0
        self.assertGreater(bo.shipping_weight, 0.0)
        bo.move_ids.picked = True
        bo._action_done()
        self.assertEqual(bo.carrier_price, 40.0)

        new_delivery_line = so.line_ids.filtered("is_delivery") - delivery_line
        self.assertEqual(len(new_delivery_line), 1)
        self.assertEqual(new_delivery_line.price_unit, bo.carrier_price)

    def test_get_packages_from_order_splits_commodities_without_aliasing(self):
        partner = self.env["res.partner"].create({"name": "Customs Test Customer"})
        product = self.env["product.product"].create(
            {"name": "Consumable widget", "type": "consu", "weight": 1.0}
        )
        product_delivery = self.env["product.product"].create(
            {
                "name": "Delivery Charges",
                "type": "service",
                "categ_id": self.env.ref("delivery.product_category_deliveries").id,
            }
        )
        delivery_carrier = self.env["delivery.carrier"].create(
            {
                "name": "Test Carrier",
                "fixed_price": 10,
                "delivery_type": "fixed",
                "product_id": product_delivery.id,
            }
        )
        package_type = self.env["stock.package.type"].create(
            {"name": "Small Box", "max_weight": 1.0, "base_weight": 0.0}
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Consumable widget",
                            "product_id": product.id,
                            "product_qty": 5,
                            "price_unit": 10.0,
                        },
                    )
                ],
            }
        )

        packages = delivery_carrier._get_packages_from_order(so, package_type)

        self.assertEqual(
            len(packages), 5, "5kg of stock at 1kg/package should need 5 packages"
        )
        total_qty = sum(
            commodity.qty for package in packages for commodity in package.commodities
        )
        self.assertEqual(
            total_qty,
            5,
            "the commodity quantities across all packages must add up to the "
            "order's true total, not be floor-divided down",
        )
        packages[0].commodities[0].qty = 999
        self.assertNotEqual(
            packages[1].commodities[0].qty,
            999,
            "each package must get its own commodity objects, not share the same "
            "ones across packages",
        )
