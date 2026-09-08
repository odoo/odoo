from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.sale_purchase.tests.common import TestSalePurchaseCommon


@tagged("-at_install", "post_install")
class TestPurchaseGeneration(TestSalePurchaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")

    def _create_service(self, uom, seller_uom, **kwargs):
        return self.env["product.product"].create(
            {
                "name": "Outsourced",
                "type": "service",
                "uom_id": uom.id,
                "uom_ids": [Command.set((uom | seller_uom).ids)],
                "taxes_id": False,
                "supplier_taxes_id": False,
                "service_to_purchase": True,
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_vendor_service.id,
                            "product_uom_id": seller_uom.id,
                            "price": 10.0,
                        }
                    )
                ],
                **kwargs,
            }
        )

    def _confirm_order(self, product, qty, uom=None):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "tax_ids": False,
                            **({"product_uom_id": uom.id} if uom else {}),
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    def test_quantity_in_sale_line_uom(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 1.0, uom=self.uom_dozen)
        sale_line = order.line_ids
        self.assertEqual(sale_line.product_uom_id, self.uom_dozen)
        self.assertEqual(sale_line.product_uom_qty, 12.0)
        self.assertEqual(sale_line.purchase_line_ids.product_uom_id, self.uom_unit)
        self.assertEqual(sale_line.purchase_line_ids.product_qty, 12.0)

    def test_quantity_in_vendor_uom(self):
        service = self._create_service(self.uom_unit, self.uom_dozen)
        order = self._confirm_order(service, 24.0)
        purchase_line = order.line_ids.purchase_line_ids
        self.assertEqual(purchase_line.product_uom_id, self.uom_dozen)
        self.assertEqual(purchase_line.product_qty, 2.0)

    def test_increase_updates_draft_purchase(self):
        service = self._create_service(self.uom_unit, self.uom_dozen)
        order = self._confirm_order(service, 12.0)
        sale_line = order.line_ids
        self.assertEqual(sale_line.purchase_line_ids.product_qty, 1.0)

        sale_line.product_qty = 36.0

        self.assertEqual(
            len(sale_line.purchase_line_ids),
            1,
            "A draft RfQ is amended, not duplicated",
        )
        self.assertEqual(sale_line.purchase_line_ids.product_qty, 3.0)

    def test_increase_buys_the_difference_once_confirmed(self):
        service = self._create_service(self.uom_unit, self.uom_dozen)
        order = self._confirm_order(service, 12.0)
        sale_line = order.line_ids
        first_line = sale_line.purchase_line_ids
        first_line.order_id.action_confirm()

        sale_line.product_qty = 24.0

        new_line = sale_line.purchase_line_ids - first_line
        self.assertEqual(len(new_line), 1, "A confirmed PO is not amended")
        self.assertEqual(first_line.product_qty, 1.0, "The confirmed line is untouched")
        self.assertEqual(
            new_line.product_qty,
            1.0,
            "Only the 12 added Units are bought, as 1 Dozen",
        )

    def test_second_increase_only_tops_up_the_open_rfq(self):
        service = self._create_service(self.uom_unit, self.uom_dozen)
        order = self._confirm_order(service, 12.0)
        sale_line = order.line_ids
        confirmed_line = sale_line.purchase_line_ids
        confirmed_line.order_id.action_confirm()

        sale_line.product_qty = 24.0
        open_line = sale_line.purchase_line_ids - confirmed_line
        self.assertEqual(open_line.state, "draft")
        self.assertEqual(open_line.product_qty, 1.0)

        sale_line.product_qty = 36.0

        self.assertEqual(
            sale_line.purchase_line_ids,
            confirmed_line | open_line,
            "The open RfQ absorbs the increase",
        )
        self.assertEqual(confirmed_line.product_qty, 1.0)
        self.assertEqual(
            open_line.product_qty,
            2.0,
            "36 Units ordered less the 12 already bought is 24 Units, i.e. 2 Dozen",
        )

    def test_decrease_and_increase_after_confirm_do_not_touch_the_confirmed_line(self):
        """Once a PO is confirmed, repeated decreases only ever schedule buyer
        activities -- the confirmed line's own quantity never moves, even across
        several decreases -- and a later increase still buys the remainder on a
        new line rather than touching the confirmed one."""
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 10.0)
        sale_line = order.line_ids
        confirmed_line = sale_line.purchase_line_ids
        purchase_order = confirmed_line.order_id
        purchase_order.action_confirm()

        sale_line.product_qty = 6.0

        self.assertEqual(confirmed_line.product_qty, 10.0)
        self.assertEqual(len(purchase_order.activity_ids), 1)

        self.env.invalidate_all()  # a second activity does not refresh the cache
        sale_line.product_qty = 3.0

        self.assertEqual(confirmed_line.product_qty, 10.0)
        self.assertEqual(len(purchase_order.activity_ids), 2)

        sale_line.product_qty = 11.0

        self.assertEqual(confirmed_line.product_qty, 10.0)
        self.assertEqual(
            len(purchase_order.activity_ids),
            2,
            "The increase buys the remainder on a new line, it does not warn the buyer",
        )
        new_line = sale_line.purchase_line_ids - confirmed_line
        self.assertTrue(new_line, "The remainder is bought on a new purchase line")
        self.assertEqual(new_line.product_qty, 8.0, "11 ordered less the 3 left open")

    def test_open_rfq_never_goes_negative(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 10.0)
        sale_line = order.line_ids
        confirmed_line = sale_line.purchase_line_ids
        confirmed_line.order_id.action_confirm()
        sale_line.product_qty = 12.0
        open_line = sale_line.purchase_line_ids - confirmed_line
        self.env.cr.execute(
            "UPDATE purchase_order_line SET product_qty = 100 WHERE id = %s",
            (confirmed_line.id,),
        )
        self.env.invalidate_all()

        sale_line.product_qty = 13.0

        self.assertEqual(open_line.product_qty, 0.0)

    def test_open_rfq_tracks_the_sale_line(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 10.0)
        sale_line = order.line_ids
        confirmed_line = sale_line.purchase_line_ids
        confirmed_line.order_id.action_confirm()
        sale_line.product_qty = 20.0
        open_line = sale_line.purchase_line_ids - confirmed_line
        open_line.product_qty = 4.0

        sale_line.product_qty = 22.0

        self.assertEqual(
            open_line.product_qty,
            12.0,
            "22 ordered less the 10 already bought, not 4 + 2",
        )

    def test_procurement_owned_purchase_lines_are_left_alone(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 10.0)
        sale_line = order.line_ids
        purchase_line = sale_line.purchase_line_ids
        self.assertTrue(purchase_line)
        service.product_tmpl_id.service_to_purchase = False

        sale_line.product_qty = 20.0

        self.assertEqual(
            sale_line.purchase_line_ids,
            purchase_line,
            "No second purchase line for a product this module no longer owns",
        )
        self.assertEqual(purchase_line.product_qty, 10.0, "and none amended")

    def test_decrease_warns_the_buyer(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 10.0)
        sale_line = order.line_ids
        purchase_order = sale_line.purchase_line_ids.order_id

        sale_line.product_qty = 4.0

        self.assertEqual(sale_line.purchase_line_ids.product_qty, 10.0)
        self.assertEqual(len(purchase_order.activity_ids), 1)
        self.assertEqual(purchase_order.activity_ids.user_id, purchase_order.user_id)

    def test_quantity_unchanged_schedules_nothing(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 10.0)
        sale_line = order.line_ids
        purchase_order = sale_line.purchase_line_ids.order_id

        sale_line.write({"product_qty": 10.0, "name": "Renamed"})

        self.assertFalse(purchase_order.activity_ids)
        self.assertEqual(len(sale_line.purchase_line_ids), 1)

    def test_line_added_to_confirmed_order_by_salesperson(self):
        salesperson = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Salesperson",
                    "login": "sale_purchase.salesperson",
                    "email": "salesperson@example.com",
                    "group_ids": [
                        Command.set([self.env.ref("sale.group_sale_salesman").id])
                    ],
                }
            )
        )
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = (
            self.env["sale.order"]
            .with_user(salesperson)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "user_id": salesperson.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.company_data["product_order_no"].id,
                                "product_qty": 1.0,
                                "tax_ids": False,
                            }
                        )
                    ],
                }
            )
        )
        order.action_confirm()

        sale_line = (
            self.env["sale.order.line"]
            .with_user(salesperson)
            .create(
                {
                    "order_id": order.id,
                    "product_id": service.id,
                    "product_qty": 3.0,
                    "tax_ids": False,
                }
            )
        )

        self.assertEqual(len(sale_line.sudo().purchase_line_ids), 1)

    def test_cancellation_warns_even_when_flag_is_off(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 1.0)
        purchase_order = order.line_ids.purchase_line_ids.order_id
        service.product_tmpl_id.service_to_purchase = False

        order._action_cancel()

        self.assertEqual(len(purchase_order.activity_ids), 1)

    def test_origin_has_no_leading_separator(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 1.0)
        purchase_order = order.line_ids.purchase_line_ids.order_id
        purchase_order.origin = False

        order.line_ids._purchase_service_add_origin(purchase_order)

        self.assertEqual(purchase_order.origin, order.name)

    def test_origin_is_not_duplicated(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 1.0)
        purchase_order = order.line_ids.purchase_line_ids.order_id

        order.line_ids._purchase_service_add_origin(purchase_order)

        self.assertEqual(purchase_order.origin, order.name)

    def test_match_supplier_without_warning_returns_empty(self):
        service = self.env["product.product"].create(
            {"name": "No vendor", "type": "service", "taxes_id": False}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {"product_id": service.id, "product_qty": 1.0, "tax_ids": False}
                    )
                ],
            }
        )

        self.assertFalse(order.line_ids._purchase_service_match_supplier(warning=False))

    def test_reinvoiced_service_cannot_be_subcontracted(self):
        with self.assertRaises(ValidationError):
            self.env["product.template"].create(
                {
                    "name": "Reinvoiced",
                    "type": "service",
                    "expense_policy": "cost",
                    "service_to_purchase": True,
                    "seller_ids": [
                        Command.create(
                            {
                                "partner_id": self.partner_vendor_service.id,
                                "price": 1.0,
                            }
                        )
                    ],
                }
            )

    def test_vendor_without_seller_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["product.template"].create(
                {"name": "No vendor", "type": "service", "service_to_purchase": True}
            )

    def test_action_view_purchase_orders(self):
        service = self._create_service(self.uom_unit, self.uom_unit)
        order = self._confirm_order(service, 1.0)
        purchase_order = order.line_ids.purchase_line_ids.order_id

        action = order.action_view_purchase_orders()

        self.assertEqual(action["res_model"], "purchase.order")
        self.assertEqual(action["res_id"], purchase_order.id)
        self.assertEqual(purchase_order.action_view_sale_orders()["res_id"], order.id)
