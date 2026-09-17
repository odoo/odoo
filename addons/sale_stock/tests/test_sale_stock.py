from datetime import datetime, timedelta

from odoo import Command
from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user

from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


@tagged("post_install", "-at_install")
class TestSaleStock(TestSaleStockCommon, ValuationReconciliationTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_product = cls.env["product.product"].create(
            {
                "name": "new_product",
                "type": "consu",
                "is_storable": True,
            }
        )

    def _get_new_sale_order(self, amount=10.0, product=False, sol_vals=False):
        sol_vals = sol_vals or {}
        product = product or self.company_data["product_delivery_no"]
        sale_order_vals = {
            "partner_id": self.partner_a.id,
            "partner_invoice_id": self.partner_a.id,
            "partner_shipping_id": self.partner_a.id,
            "line_ids": [
                Command.create(
                    {
                        "product_id": product.id,
                        "product_qty": amount,
                        "price_unit": product.list_price,
                        **sol_vals,
                    }
                )
            ],
        }
        return self.env["sale.order"].create(sale_order_vals)

    def test_00_sale_stock_invoice(self):
        self.so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_qty": 2,
                            "price_unit": p.list_price,
                        },
                    )
                    for p in (
                        self.company_data["product_order_no"],
                        self.company_data["product_service_delivery"],
                        self.company_data["product_service_order"],
                        self.company_data["product_delivery_no"],
                    )
                ],
                "picking_policy": "direct",
            }
        )

        self.so.action_confirm()
        self.assertTrue(
            self.so.picking_ids,
            'Sale Stock: no picking created for "invoice on delivery" storable products',
        )
        inv_ordered = self.so._create_invoices()
        inv_ordered.action_post()

        self.assertEqual(
            self.so.invoice_state,
            "partial",
            'Sale Stock: so invoice_state should be "partial" after invoicing ordered products',
        )
        pick = self.so.picking_ids
        pick.move_ids.write({"quantity": 1, "picked": True})
        Form.from_action(self.env, pick.button_validate()).save().process()
        self.assertEqual(
            self.so.invoice_state,
            "partial",
            'Sale Stock: so invoice_state should be "partial" after partial '
            "delivery - the ordered products are already invoiced and the "
            "delivered ones are not",
        )
        del_qties = [sol.qty_transferred for sol in self.so.line_ids]
        del_qties_truth = [
            1.0 if sol.product_id.type == "consu" else 0.0 for sol in self.so.line_ids
        ]
        self.assertEqual(
            del_qties,
            del_qties_truth,
            "Sale Stock: delivered quantities are wrong after partial delivery",
        )
        inv_1 = self.so._create_invoices()
        self.assertTrue(
            all(
                il.product_id.invoice_policy == "transferred"
                for il in inv_1.invoice_line_ids
            ),
            'Sale Stock: invoice should only contain "invoice on delivery" products',
        )
        inv_1.action_post()

        self.assertEqual(
            self.so.invoice_state,
            "partial",
            'Sale Stock: so invoice_state should be "partial" after partial delivery and invoicing',
        )
        self.assertEqual(
            len(self.so.picking_ids), 2, "Sale Stock: number of pickings should be 2"
        )
        pick_2 = self.so.picking_ids.filtered("backorder_id")
        pick_2.move_ids.write({"quantity": 1, "picked": True})
        self.assertTrue(
            pick_2.button_validate(),
            "Sale Stock: second picking should be final without need for a backorder",
        )
        self.assertEqual(
            self.so.invoice_state,
            "partial",
            'Sale Stock: so invoice_state should be "partial" after complete delivery (some already invoiced)',
        )
        del_qties = [sol.qty_transferred for sol in self.so.line_ids]
        del_qties_truth = [
            2.0 if sol.product_id.type == "consu" else 0.0 for sol in self.so.line_ids
        ]
        self.assertEqual(
            del_qties,
            del_qties_truth,
            "Sale Stock: delivered quantities are wrong after complete delivery",
        )
        self.so.line_ids.sorted()[1]["qty_transferred"] = 2.0

        self.env.flush_all()
        self.env.invalidate_all()

        inv_id = self.so._create_invoices()
        inv_id.action_post()
        self.assertEqual(
            self.so.invoice_state,
            "done",
            'Sale Stock: so invoice_state should be "fully invoiced" after complete delivery and invoicing',
        )

    def test_01_sale_stock_order(self):
        product_list = (
            self.company_data["product_order_no"],
            self.company_data["product_service_delivery"],
            self.company_data["product_service_order"],
            self.company_data["product_delivery_no"],
        )

        for product in product_list:
            product.invoice_policy = "ordered"

        self.so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_qty": 2,
                            "price_unit": p.list_price,
                        },
                    )
                    for p in product_list
                ],
                "picking_policy": "direct",
            }
        )
        self.so.line_ids._compute_product_readonly()
        self.assertFalse(self.so.line_ids.sorted()[0].product_readonly)
        self.so.action_confirm()
        self.so.line_ids._compute_product_readonly()
        self.assertTrue(self.so.line_ids.sorted()[0].product_readonly)
        self.assertTrue(
            self.so.picking_ids,
            'Sale Stock: no picking created for "invoice on order" storable products',
        )

        adv_wiz = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=[self.so.id])
            .create(
                {
                    "advance_payment_method": "percentage",
                    "amount": 5.0,
                }
            )
        )
        act = adv_wiz.create_invoices()
        inv = self.env["account.move"].browse(act["res_id"])
        self.assertEqual(
            inv.amount_untaxed,
            self.so.amount_untaxed * 5.0 / 100.0,
            "Sale Stock: deposit invoice is wrong",
        )
        self.assertEqual(
            self.so.invoice_state,
            "to do",
            "Sale Stock: so should be to do after invoicing deposit",
        )
        final_inv = self.so._create_invoices(final=True)
        final_inv.action_post()
        self.assertEqual(
            self.so.invoice_state,
            "done",
            "Sale Stock: so should be fully invoiced after second invoice",
        )

        pick = self.so.picking_ids
        pick.move_ids.write({"quantity": 2, "picked": True})
        self.assertTrue(
            pick.button_validate(),
            "Sale Stock: complete delivery should not need a backorder",
        )
        del_qties = [sol.qty_transferred for sol in self.so.line_ids]
        del_qties_truth = [
            2.0 if sol.product_id.type == "consu" else 0.0 for sol in self.so.line_ids
        ]
        self.assertEqual(
            del_qties,
            del_qties_truth,
            "Sale Stock: delivered quantities are wrong after partial delivery",
        )
        with self.assertRaises(UserError):
            self.so._create_invoices()

    def test_02_sale_stock_return(self):
        self.product = self.company_data["product_delivery_no"]
        so_vals = {
            "partner_id": self.partner_a.id,
            "partner_invoice_id": self.partner_a.id,
            "partner_shipping_id": self.partner_a.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": self.product.name,
                        "product_id": self.product.id,
                        "product_qty": 5.0,
                        "price_unit": self.product.list_price,
                    },
                )
            ],
        }
        self.so = self.env["sale.order"].create(so_vals)

        self.so.action_confirm()
        self.assertTrue(
            self.so.picking_ids,
            'Sale Stock: no picking created for "invoice on delivery" storable products',
        )

        self.assertEqual(
            self.so.invoice_state,
            "to do",
            'Sale Stock: so invoice_state should be "to do" instead of "%s" - '
            "the lines are 'no' only because nothing has been delivered yet"
            % self.so.invoice_state,
        )

        pick = self.so.picking_ids
        pick.move_ids.write({"quantity": 5, "picked": True})
        pick.button_validate()

        del_qty = sum(sol.qty_transferred for sol in self.so.line_ids)
        self.assertEqual(
            del_qty,
            5.0,
            "Sale Stock: delivered quantity should be 5.0 instead of %s after complete delivery"
            % del_qty,
        )

        self.assertEqual(
            self.so.invoice_state,
            "to do",
            'Sale Stock: so invoice_state should be "to do" instead of "%s" before invoicing'
            % self.so.invoice_state,
        )
        self.inv_1 = self.so._create_invoices()
        self.assertEqual(
            len(self.inv_1),
            1,
            'Sale Stock: only one invoice instead of "%s" should be created'
            % len(self.inv_1),
        )
        self.assertEqual(
            self.inv_1.amount_untaxed,
            self.inv_1.amount_untaxed,
            "Sale Stock: amount in SO and invoice should be the same",
        )
        self.inv_1.action_post()
        self.assertEqual(
            self.so.invoice_state,
            "done",
            'Sale Stock: so invoice_state should be "done" instead of "%s" after invoicing'
            % self.so.invoice_state,
        )

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=pick.ids,
                active_id=pick.sorted().ids[0],
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 2.0
        return_wiz.product_return_moves.to_refund = True
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])

        return_pick.move_ids.write({"quantity": 2, "picked": True})
        return_pick.button_validate()

        self.assertEqual(
            self.so.invoice_state,
            "to do",
            'Sale Stock: so invoice_state should be "to do" instead of "%s" after picking return'
            % self.so.invoice_state,
        )
        self.assertAlmostEqual(
            self.so.line_ids.sorted()[0].qty_transferred,
            3.0,
            msg='Sale Stock: delivered quantity should be 3.0 instead of "%s" after picking return'
            % self.so.line_ids.sorted()[0].qty_transferred,
        )
        adv_wiz = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=[self.so.id])
            .create(
                {
                    "advance_payment_method": "delivered",
                }
            )
        )
        adv_wiz.create_invoices()
        self.inv_2 = self.so.invoice_ids.filtered(lambda r: r.state == "draft")
        self.assertAlmostEqual(
            self.inv_2.invoice_line_ids.sorted()[0].quantity,
            2.0,
            msg='Sale Stock: refund quantity on the invoice should be 2.0 instead of "%s".'
            % self.inv_2.invoice_line_ids.sorted()[0].quantity,
        )
        self.inv_2.action_post()
        self.assertEqual(
            self.so.invoice_state,
            "done",
            'Sale Stock: so invoice_state should be "done" instead of "%s" after invoicing the return'
            % self.so.invoice_state,
        )

    def test_03_sale_stock_delivery_partial(self):
        self.product = self.company_data["product_delivery_no"]
        so_vals = {
            "partner_id": self.partner_a.id,
            "partner_invoice_id": self.partner_a.id,
            "partner_shipping_id": self.partner_a.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": self.product.name,
                        "product_id": self.product.id,
                        "product_qty": 5.0,
                        "product_uom_id": self.product.uom_id.id,
                        "price_unit": self.product.list_price,
                    },
                )
            ],
        }
        self.so = self.env["sale.order"].create(so_vals)

        self.so.action_confirm()
        self.assertTrue(
            self.so.picking_ids,
            'Sale Stock: no picking created for "invoice on delivery" storable products',
        )

        self.assertEqual(
            self.so.invoice_state,
            "to do",
            'Sale Stock: so invoice_state should be "to do" - nothing is '
            "invoiceable yet, but the delivery is still owed",
        )

        pick = self.so.picking_ids
        pick.move_ids.write({"quantity": 4})
        res_dict = pick.button_validate()
        wizard = Form(
            self.env[(res_dict.get("res_model"))].with_context(res_dict["context"])
        ).save()
        wizard.action_cancel_backorder()

        activity = self.env["mail.activity"].search(
            [("res_id", "=", self.so.id), ("res_model", "=", "sale.order")]
        )
        self.assertEqual(
            len(activity),
            1,
            "When no backorder is created for a partial delivery, a warning error should be logged in its origin SO",
        )

        del_qty = sum(sol.qty_transferred for sol in self.so.line_ids)
        self.assertEqual(
            del_qty,
            4.0,
            "Sale Stock: delivered quantity should be 4.0 after partial delivery",
        )

        self.assertEqual(
            self.so.invoice_state,
            "to do",
            'Sale Stock: so invoice_state should be "to do" before invoicing',
        )
        self.inv_1 = self.so._create_invoices()
        self.assertEqual(
            len(self.inv_1), 1, "Sale Stock: only one invoice should be created"
        )
        self.inv_1.action_post()
        self.assertEqual(
            self.so.invoice_state,
            "done",
            'Sale Stock: so invoice_state should be "done" when set to done',
        )

    def test_04_create_picking_update_saleorderline(self):
        item1 = self.company_data["product_order_no"]
        item1.type = "consu"
        item2 = self.company_data["product_delivery_no"]
        item2.is_storable = True

        self.so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "price_unit": item1.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": item2.name,
                            "product_id": item2.id,
                            "product_qty": 1,
                            "price_unit": item2.list_price,
                        },
                    ),
                ],
            }
        )
        self.so.action_confirm()

        self.assertEqual(len(self.so.picking_ids), 1)
        res_dict = self.so.picking_ids.sorted()[0].button_validate()
        wizard = Form.from_action(self.env, res_dict).save()
        self.assertEqual(wizard._name, "stock.backorder.confirmation")
        wizard.process()

        self.assertEqual(len(self.so.picking_ids), 2)
        for picking in self.so.picking_ids:
            move = picking.move_ids
            if picking.backorder_id:
                self.assertEqual(move.product_id.id, item2.id)
                self.assertEqual(move.state, "confirmed")
            else:
                self.assertEqual(picking.move_ids.product_id.id, item1.id)
                self.assertEqual(move.state, "done")

        self.so.write(
            {
                "line_ids": [
                    (1, self.so.line_ids.sorted()[0].id, {"product_qty": 2}),
                    (1, self.so.line_ids.sorted()[1].id, {"product_qty": 2}),
                ]
            }
        )
        self.assertEqual(len(self.so.picking_ids), 2)
        backorder = self.so.picking_ids.filtered(lambda p: p.backorder_id)
        self.assertEqual(len(backorder.move_ids), 2)
        for backorder_move in backorder.move_ids:
            if backorder_move.product_id.id == item1.id:
                self.assertEqual(backorder_move.product_qty, 1)
            elif backorder_move.product_id.id == item2.id:
                self.assertEqual(backorder_move.product_qty, 2)

        self.so.write(
            {
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "price_unit": item1.list_price,
                        },
                    ),
                ]
            }
        )
        self.assertEqual(
            sum(
                backorder.move_ids.filtered(
                    lambda m: m.product_id.id == item1.id
                ).mapped("product_qty")
            ),
            2,
        )

    def test_05_create_picking_update_saleorderline(self):
        item1 = self.company_data["product_order_no"]
        item1.type = "consu"
        item2 = self.company_data["product_delivery_no"]
        item2.is_storable = True

        self.env["stock.quant"]._update_available_quantity(
            item2, self.company_data["default_warehouse"].lot_stock_id, 2
        )
        self.so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "price_unit": item1.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": item2.name,
                            "product_id": item2.id,
                            "product_qty": 1,
                            "price_unit": item2.list_price,
                        },
                    ),
                ],
            }
        )
        self.so.action_confirm()

        self.assertEqual(len(self.so.picking_ids), 1)
        self.so.picking_ids.sorted()[0].button_validate()
        self.assertEqual(self.so.picking_ids.sorted()[0].state, "done")

        self.so.write(
            {
                "line_ids": [
                    (1, self.so.line_ids.sorted()[0].id, {"product_qty": 2}),
                    (1, self.so.line_ids.sorted()[1].id, {"product_qty": 2}),
                ]
            }
        )
        self.assertEqual(len(self.so.picking_ids), 2)

    def test_05_confirm_cancel_confirm(self):
        item1 = self.company_data["product_order_no"]
        partner1 = self.partner_a.id
        partner2 = self.env["res.partner"].create({"name": "Another Test Partner"})
        so1 = self.env["sale.order"].create(
            {
                "partner_id": partner1,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "price_unit": item1.list_price,
                        },
                    )
                ],
            }
        )
        so1.action_confirm()
        self.assertEqual(len(so1.picking_ids), 1)
        self.assertEqual(so1.picking_ids.partner_id.id, partner1)
        so1._action_cancel()
        so1.action_draft()
        so1.partner_id = partner2
        so1.partner_shipping_id = partner2
        so1.action_confirm()
        self.assertEqual(len(so1.picking_ids), 2)
        picking2 = so1.picking_ids.filtered(lambda p: p.state != "cancel")
        self.assertEqual(picking2.partner_id.id, partner2.id)

    def test_06_uom(self):
        self.env.ref("uom.decimal_product_uom").digits = 0
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        item1 = self.company_data["product_order_no"]

        self.assertEqual(item1.uom_id.id, uom_unit.id)

        so1 = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create({"name": "UoM Test", "display_type": "line_note"}),
                    Command.create(
                        {"product_id": item1.id, "product_uom_id": uom_dozen.id}
                    ),
                    Command.create({"name": "Downpayment", "is_downpayment": True}),
                ],
            }
        )
        so1.action_confirm()

        move1 = so1.picking_ids.move_ids[0]
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.product_uom_id.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 12)

        product_line = so1.line_ids.filtered("product_id")
        so1.write(
            {
                "line_ids": [
                    Command.update(product_line.id, {"product_qty": 2}),
                ]
            }
        )
        move1 = so1.picking_ids.move_ids[0]
        self.assertEqual(move1.product_uom_qty, 24)
        self.assertEqual(move1.product_uom_id.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 24)

        self.env["ir.config_parameter"].sudo().set_param("stock.propagate_uom", "1")
        so1.write(
            {
                "line_ids": [
                    Command.update(product_line.id, {"product_qty": 3}),
                ]
            }
        )
        move2 = so1.picking_ids.move_ids.filtered(
            lambda m: m.product_uom_id.id == uom_dozen.id
        )
        self.assertEqual(move2.product_uom_qty, 1)
        self.assertEqual(move2.product_uom_id.id, uom_dozen.id)
        self.assertEqual(move2.product_qty, 12)

        move1.write({"quantity": 24, "picked": True})
        move2.write({"quantity": 1, "picked": True})
        so1.picking_ids.button_validate()

        self.assertEqual(product_line.qty_transferred, 3.0)

    def test_07_forced_qties(self):
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        item1 = self.company_data["product_order_no"]

        self.assertEqual(item1.uom_id.id, uom_unit.id)

        so1 = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "product_uom_id": uom_dozen.id,
                            "price_unit": item1.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "product_uom_id": uom_dozen.id,
                            "price_unit": item1.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "product_uom_id": uom_dozen.id,
                            "price_unit": item1.list_price,
                        },
                    ),
                ],
            }
        )
        so1.action_confirm()

        self.assertEqual(len(so1.picking_ids.move_ids), 3)
        self.assertEqual(len(so1.picking_ids.move_line_ids), 3)
        so1.picking_ids.move_ids.picked = True
        so1.picking_ids.button_validate()
        self.assertEqual(so1.picking_ids.state, "done")
        self.assertEqual(so1.line_ids.mapped("qty_transferred"), [1, 1, 1])

    def test_08_quantities(self):
        self.env["stock.picking.type"].search([("code", "=", "incoming")]).write(
            {"code": "internal"}
        )

        item1 = self.company_data["product_order_no"]
        uom_unit = self.env.ref("uom.product_uom_unit")
        so1 = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 10,
                            "product_uom_id": uom_unit.id,
                            "price_unit": item1.list_price,
                        },
                    ),
                ],
            }
        )
        so1.action_confirm()

        picking = so1.picking_ids
        picking.button_validate()

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.sorted().ids[0],
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({"quantity": 5, "to_refund": True})
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])
        return_pick.button_validate()

        self.assertEqual(so1.line_ids.qty_transferred, 5)

        so1.write(
            {
                "line_ids": [
                    (1, so1.line_ids.sorted()[0].id, {"product_qty": 15}),
                ]
            }
        )

        self.assertEqual(so1.line_ids.qty_transferred, 5)
        self.assertEqual(so1.picking_ids.sorted("id")[-1].move_ids.product_qty, 10)

    def test_09_qty_available(self):
        item1 = self.company_data["product_order_no"]
        item1.is_storable = True

        warehouse1 = self.company_data["default_warehouse"]
        self.env["stock.quant"]._update_available_quantity(
            item1, warehouse1.lot_stock_id, 10
        )
        self.env["stock.quant"]._update_reserved_quantity(
            item1, warehouse1.lot_stock_id, 3
        )

        warehouse2 = self.env["stock.warehouse"].create(
            {
                "partner_id": self.partner_a.id,
                "name": "Zizizatestwarehouse",
                "code": "Test",
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            item1, warehouse2.lot_stock_id, 5
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 1,
                            "price_unit": item1.list_price,
                        },
                    ),
                ],
            }
        )
        line = so.line_ids[0]
        self.assertAlmostEqual(
            line.date_planned, datetime.now(), delta=timedelta(seconds=10)
        )
        self.assertEqual(line.qty_available_virtual_at_date, 10)
        self.assertEqual(line.qty_free_today, 7)
        self.assertEqual(line.qty_available_today, 10)
        self.assertEqual(line.warehouse_id, warehouse1)
        self.assertEqual(line.qty_to_transfer, 1)
        so.warehouse_id = warehouse2
        self.env.invalidate_all()
        self.assertEqual(line.qty_available_virtual_at_date, 5)
        self.assertEqual(line.qty_free_today, 5)
        self.assertEqual(line.qty_available_today, 5)
        self.assertEqual(line.warehouse_id, warehouse2)
        self.assertEqual(line.qty_to_transfer, 1)

    def test_10_qty_available(self):
        item1 = self.company_data["product_order_no"]
        item1.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            item1, self.company_data["default_warehouse"].lot_stock_id, 10
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 5,
                            "price_unit": item1.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 5,
                            "price_unit": item1.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": item1.name,
                            "product_id": item1.id,
                            "product_qty": 5,
                            "price_unit": item1.list_price,
                        },
                    ),
                ],
            }
        )
        self.assertEqual(so.line_ids.mapped("qty_free_today"), [10, 5, 0])

    def test_11_return_with_refund(self):
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)
        picking = sale_order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking.button_validate()

        self.assertEqual(sale_order.line_ids.qty_transferred, 10)
        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wizard = return_picking_form.save()
        self.assertEqual(return_wizard.product_return_moves.to_refund, True)
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)

        return_wizard.product_return_moves.quantity = 10
        res = return_wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.move_ids.write({"quantity": 10, "picked": True})
        return_picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)

    def test_12_return_without_refund(self):
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)
        picking = sale_order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking.button_validate()

        self.assertEqual(sale_order.line_ids.qty_transferred, 10)
        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wizard = return_picking_form.save()
        self.assertEqual(return_wizard.product_return_moves.to_refund, True)
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.to_refund = False
        return_wizard.product_return_moves.quantity = 10
        res = return_wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.move_ids.write({"quantity": 10, "picked": True})
        return_picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 10)

    def test_13_delivered_qty(self):
        product_inv_on_delivered = self.company_data["product_delivery_no"]
        product_inv_on_order = self.env["product.product"].create(
            {
                "name": "Shenaniffluffy",
                "type": "consu",
                "invoice_policy": "ordered",
                "list_price": 55.0,
            }
        )
        sale_order = self._get_new_sale_order(amount=3)
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.line_ids), 1)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)
        picking = sale_order.picking_ids
        initial_product = sale_order.line_ids.product_id
        picking.picking_type_id.show_operations = True
        picking_form = Form(picking)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 5
        with picking_form.move_ids.new() as new_move:
            new_move.product_id = product_inv_on_order
            new_move.quantity = 5
        picking = picking_form.save()
        picking.move_ids.picked = True
        picking.button_validate()

        self.assertEqual(len(sale_order.line_ids), 2)
        so_line_1 = sale_order.line_ids[0]
        so_line_2 = sale_order.line_ids[1]
        self.assertEqual(so_line_1.product_id.id, product_inv_on_delivered.id)
        self.assertEqual(so_line_1.product_qty, 3)
        self.assertEqual(so_line_1.qty_transferred, 5)
        self.assertEqual(so_line_1.price_unit, 70.0)
        self.assertEqual(so_line_2.product_id.id, product_inv_on_order.id)
        self.assertEqual(so_line_2.product_qty, 0)
        self.assertEqual(so_line_2.qty_transferred, 5)
        self.assertEqual(
            so_line_2.price_unit,
            0,
            "Shouldn't get the product price as the invoice policy is on qty. ordered",
        )

        self.assertRecordValues(
            sale_order.picking_ids.move_ids,
            [
                {"product_id": initial_product.id, "quantity": 5},
                {"product_id": product_inv_on_order.id, "quantity": 5},
            ],
        )

        sale_order = self._get_new_sale_order(product=product_inv_on_order, amount=3)
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.line_ids), 1)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)
        picking = sale_order.picking_ids

        picking_form = Form(picking)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 5
        with picking_form.move_ids.new() as new_move:
            new_move.product_id = product_inv_on_delivered
            new_move.quantity = 5
        picking = picking_form.save()
        picking.move_ids.picked = True
        picking.button_validate()

        self.assertEqual(len(sale_order.line_ids), 2)
        so_line_1 = sale_order.line_ids[0]
        so_line_2 = sale_order.line_ids[1]
        self.assertEqual(so_line_1.product_id.id, product_inv_on_order.id)
        self.assertEqual(so_line_1.product_qty, 3)
        self.assertEqual(so_line_1.qty_transferred, 5)
        self.assertEqual(so_line_1.price_unit, 55.0)
        self.assertEqual(so_line_2.product_id.id, product_inv_on_delivered.id)
        self.assertEqual(so_line_2.product_qty, 0)
        self.assertEqual(so_line_2.qty_transferred, 5)
        self.assertEqual(
            so_line_2.price_unit,
            70.0,
            "Should get the product price as the invoice policy is on qty. delivered",
        )

    def test_14_delivered_qty_in_multistep(self):
        warehouse = self.company_data["default_warehouse"]
        warehouse.delivery_steps = "pick_ship"
        product_inv_on_order = self.env["product.product"].create(
            {
                "name": "Shenaniffluffy",
                "type": "consu",
                "invoice_policy": "ordered",
                "list_price": 55.0,
            }
        )
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.line_ids), 1)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)
        pick = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == "internal"
        )
        pick.picking_type_id.show_operations = True
        picking_form = Form(pick)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        pick = picking_form.save()
        pick.move_ids.picked = True
        pick.button_validate()

        delivery = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing"
        )
        delivery.picking_type_id.show_operations = True
        picking_form = Form(delivery)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        delivery = picking_form.save()
        delivery.move_ids.picked = True
        delivery.button_validate()

        self.assertEqual(len(sale_order.line_ids), 1)
        self.assertEqual(sale_order.line_ids.product_qty, 10)
        self.assertEqual(sale_order.line_ids.qty_transferred, 10)
        self.assertEqual(sale_order.line_ids.price_unit, 70.0)

        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.line_ids), 1)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)
        pick = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == "internal"
        )

        picking_form = Form(pick)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        with picking_form.move_ids.new() as new_move:
            new_move.product_id = product_inv_on_order
            new_move.quantity = 10
        pick = picking_form.save()
        pick.move_ids.picked = True
        pick.button_validate()

        delivery = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing"
        )
        picking_form = Form(delivery)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        with picking_form.move_ids.edit(1) as new_move:
            new_move.quantity = 10
        delivery = picking_form.save()
        delivery.move_ids.picked = True
        delivery.button_validate()

        self.assertEqual(len(sale_order.line_ids), 2)
        so_line_1 = sale_order.line_ids[0]
        so_line_2 = sale_order.line_ids[1]
        self.assertEqual(
            so_line_1.product_id.id, self.company_data["product_delivery_no"].id
        )
        self.assertEqual(so_line_1.product_qty, 10)
        self.assertEqual(so_line_1.qty_transferred, 10)
        self.assertEqual(so_line_1.price_unit, 70.0)
        self.assertEqual(so_line_2.product_id.id, product_inv_on_order.id)
        self.assertEqual(so_line_2.product_qty, 0)
        self.assertEqual(so_line_2.qty_transferred, 10)
        self.assertEqual(so_line_2.price_unit, 0)

    def test_08_sale_return_qty_and_cancel(self):
        partner = self.partner_a
        product = self.company_data["product_delivery_no"]
        so_vals = {
            "partner_id": partner.id,
            "partner_invoice_id": partner.id,
            "partner_shipping_id": partner.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "name": product.name,
                        "product_id": product.id,
                        "product_qty": 5.0,
                        "price_unit": product.list_price,
                    },
                )
            ],
        }
        so = self.env["sale.order"].create(so_vals)

        so.action_confirm()

        pick = so.picking_ids
        pick.move_ids.write({"quantity": 3, "picked": True})

        Form.from_action(self.env, pick.button_validate()).save().process()

        inv_1 = so._create_invoices()
        inv_1.action_post()
        self.assertEqual(inv_1.state, "posted", "invoice should be in posted state")

        pick_2 = so.picking_ids.filtered("backorder_id")
        pick_2.move_ids.write({"quantity": 2, "picked": True})
        pick_2.button_validate()

        inv_2 = so._create_invoices()
        self.assertEqual(inv_2.state, "draft", "invoice should be in draft state")

        so.action_cancel()
        self.assertEqual(
            inv_1.state, "posted", "A posted invoice state should remain posted"
        )
        self.assertEqual(
            inv_2.state, "cancel", "A drafted invoice state should be cancelled"
        )

    def test_reservation_method_w_sale(self):
        picking_type_out = self.company_data["default_warehouse"].out_type_id
        picking_type_out.reservation_method = "at_confirm"
        product = self.company_data["product_delivery_no"]
        product.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            product, self.company_data["default_warehouse"].lot_stock_id, 20
        )

        sale_order1 = self._get_new_sale_order(amount=10.0)
        sale_order1.action_confirm()
        picking1 = sale_order1.picking_ids
        self.assertTrue(picking1)
        self.assertEqual(picking1.state, "assigned")
        picking1.unlink()

        picking_type_out.reservation_method = "manual"
        sale_order2 = self._get_new_sale_order(amount=10.0)
        sale_order2.action_confirm()
        picking2 = sale_order2.picking_ids
        self.assertTrue(picking2)
        self.assertEqual(picking2.state, "confirmed")
        picking2.unlink()

        picking_type_out.reservation_method = "by_date"
        picking_type_out.reservation_days_before = 2
        sale_order3 = self._get_new_sale_order(amount=10.0)
        sale_order3.date_commitment = datetime.now() + timedelta(days=10)
        sale_order3.action_confirm()
        picking3 = sale_order3.picking_ids
        self.assertTrue(picking3)
        self.assertEqual(picking3.state, "confirmed")
        picking3.unlink()
        sale_order4 = self._get_new_sale_order(amount=10.0)
        sale_order4.date_commitment = datetime.now() + timedelta(days=1)
        sale_order4.action_confirm()
        self.assertTrue(sale_order4.picking_ids)
        self.assertEqual(sale_order4.picking_ids.state, "assigned")

    def test_15_cancel_delivery(self):
        group_auto_done = self.env.ref("sale.group_auto_done_setting")
        self.group_user.implied_ids = [Command.link(group_auto_done.id)]

        product = self.product_a
        product.invoice_policy = "transferred"
        partner = self.partner_a
        so = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 2,
                            "price_unit": product.list_price,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        self.assertEqual(so.state, "done")
        self.assertTrue(so.locked)
        so.picking_ids.action_cancel()

        self.assertEqual(
            so.invoice_state,
            "to do",
            "cancelling the picking leaves the order lines in place, so the "
            "quantities are still owed rather than settled",
        )

    def test_16_multi_uom(self):
        yards_uom = self.env["uom.uom"].create(
            {
                "name": "Yards",
                "relative_factor": 0.9144,
                "relative_uom_id": self.env.ref("uom.product_uom_meter").id,
            }
        )
        product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "uom_id": self.env.ref("uom.product_uom_meter").id,
            }
        )
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 4.0,
                            "product_uom_id": yards_uom.id,
                            "price_unit": 1.0,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        picking = so.picking_ids[0]
        picking.move_ids.write({"quantity": 3.66, "picked": True})
        picking.button_validate()
        self.assertEqual(
            so.line_ids.mapped("qty_transferred"),
            [4.0],
            'Sale: no conversion error on delivery in different uom"',
        )

    def test_17_qty_update_propagation(self):
        warehouse = self.company_data["default_warehouse"]
        warehouse.delivery_steps = "pick_ship"
        product = self.company_data["product_delivery_no"]
        product.is_storable = True

        self.env["stock.quant"]._update_available_quantity(
            product, self.company_data["default_warehouse"].lot_stock_id, 50
        )
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 50,
                            "price_unit": product.list_price,
                        },
                    ),
                ],
            }
        )
        sale_order.action_confirm()

        self.assertEqual(
            len(sale_order.picking_ids),
            1,
            'Only the "Pick" picking should have been created.',
        )
        customer_location = self.env.ref("stock.stock_location_customers")
        move_pick = sale_order.picking_ids.filtered(
            lambda p: p.location_dest_id.id != customer_location.id
        ).move_ids
        self.assertEqual(
            len(move_pick), 1, "Only one move should be created for a single product."
        )
        self.assertEqual(
            move_pick.product_qty,
            50,
            "The move quantity should be the same as the quantity sold.",
        )

        sale_order.line_ids.write({"product_qty": 30})
        self.assertEqual(
            move_pick.product_qty,
            30,
            "The move quantity should have been decreased as the sale order line was.",
        )
        self.assertEqual(
            len(sale_order.picking_ids),
            1,
            "No additionnal picking should have been created.",
        )

        sale_order.line_ids.write({"product_qty": 40})
        self.assertEqual(
            move_pick.product_qty,
            40,
            "The move quantity should have been increased as the sale order line was.",
        )
        move_pick.write({"quantity": 40, "picked": True})
        move_pick._action_done()

        self.assertEqual(
            len(sale_order.picking_ids),
            2,
            "The delivery picking should have been created as well.",
        )
        move_out = sale_order.picking_ids.filtered(
            lambda p: p.location_dest_id.id == customer_location.id
        ).move_ids
        self.assertEqual(
            move_out.product_qty,
            40,
            "The move quantity should have been increased as the sale order line and the pick line were.",
        )

        sale_order.line_ids.write({"product_qty": 50})
        self.assertEqual(
            len(sale_order.picking_ids),
            3,
            'A new "Pick" picking should have been created for the missing quantity.',
        )
        move_pick_2 = sale_order.picking_ids.filtered(
            lambda p: (
                p.location_dest_id.id != customer_location.id and p.state != "done"
            )
        ).move_ids
        self.assertEqual(
            move_pick_2.product_qty,
            10,
            "The move quantity should be the missing quantity.",
        )

    def test_18_deliver_more_and_multi_uom(self):
        uom_m_id = self.ref("uom.product_uom_meter")
        uom_km_id = self.ref("uom.product_uom_km")
        self.product_b.write(
            {
                "uom_id": uom_m_id,
            }
        )

        so = self._get_new_sale_order(product=self.product_a)
        so.action_confirm()

        picking = so.picking_ids
        self.env["stock.move"].create(
            {
                "picking_id": picking.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "product_id": self.product_b.id,
                "product_uom_qty": 1,
                "product_uom_id": uom_km_id,
                "quantity": 1,
            }
        )
        picking.button_validate()

        self.assertEqual(so.line_ids[1].product_id, self.product_b)
        self.assertEqual(so.line_ids[1].qty_transferred, 1)
        self.assertEqual(so.line_ids[1].product_uom_id.id, uom_km_id)

    def test_19_deliver_update_so_line_qty(self):
        self.product_a.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            self.product_a, self.company_data["default_warehouse"].lot_stock_id, 10
        )

        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()

        picking = sale_order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking.button_validate()

        with Form(sale_order.with_context(import_file=True)) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 777

        self.assertEqual(len(sale_order.picking_ids), 2)

    def test_update_so_line_qty_with_package(self):
        self.product_a.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            self.product_a,
            self.company_data["default_warehouse"].lot_stock_id,
            10,
            package_id=self.env["stock.package"].create({"name": "PacMan"}),
        )

        sale_order = self._get_new_sale_order(product=self.product_a)
        sale_order.action_confirm()

        with Form(sale_order.with_context(import_file=True)) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 0

        self.assertFalse(sale_order.picking_ids.move_line_ids)

    def test_multiple_returns(self):
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking.button_validate()

        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wizard = return_picking_form.save()
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.quantity = 2
        res = return_wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.move_ids.write({"quantity": 2, "picked": True})
        return_picking.button_validate()

    def test_return_for_exchange_negativ(self):
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking.button_validate()

        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=picking.id, active_model="stock.picking"
            )
        )
        with return_picking_form.product_return_moves.new() as line:
            line.product_id = self.new_product
            line.quantity = 2
        return_wizard = return_picking_form.save()
        return_wizard.product_return_moves[0].quantity = 2

        res = return_wizard.action_create_exchanges()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        self.assertTrue(return_picking)
        self.assertEqual(len(return_picking.move_ids), 2)
        new_product_moves = self.env["stock.move"].search(
            [("product_id", "=", self.new_product.id)]
        )
        self.assertEqual(
            len(new_product_moves),
            1,
            "The new product should not create extra procurement",
        )
        sol = self.env["sale.order.line"].search(
            [("product_id", "=", self.new_product.id)]
        )
        self.assertFalse(sol)
        return_picking.button_validate()
        sol = self.env["sale.order.line"].search(
            [("product_id", "=", self.new_product.id)]
        )
        self.assertTrue(sol)
        self.assertEqual(sol.product_qty, 0)
        self.assertEqual(sol.qty_transferred, -2)
        self.assertEqual(sol.order_id, sale_order)

    def test_return_for_exchange_and_cancel_sol_qty(self):
        warehouse = self.company_data["default_warehouse"]
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref("stock.stock_location_customers")

        so = self._get_new_sale_order()
        so.action_confirm()

        delivery = so.picking_ids
        delivery.move_ids.write({"quantity": 10, "picked": True})
        delivery.button_validate()

        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=delivery.id, active_model="stock.picking"
            )
        )
        with return_picking_form.product_return_moves.edit(0) as line:
            line.quantity = 10
        return_wizard = return_picking_form.save()
        res = return_wizard.action_create_exchanges()

        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.move_ids.write({"quantity": 10, "picked": True})
        return_picking.button_validate()

        so.line_ids.product_qty = 0
        self.assertRecordValues(
            so.picking_ids.move_ids.sorted(key="id"),
            [
                {
                    "location_id": stock_location.id,
                    "location_dest_id": customer_location.id,
                    "state": "done",
                },
                {
                    "location_id": customer_location.id,
                    "location_dest_id": stock_location.id,
                    "state": "done",
                },
                {
                    "location_id": stock_location.id,
                    "location_dest_id": customer_location.id,
                    "state": "cancel",
                },
            ],
        )

    def test_procurement_qty_legacy_moves_without_rule(self):
        so = self._get_new_sale_order(amount=12.0)
        so.action_confirm()

        delivery = so.picking_ids
        delivery.move_ids.rule_id = False
        delivery.move_ids.write({"quantity": 12, "picked": True})
        delivery.button_validate()

        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=delivery.id, active_model="stock.picking"
            )
        )
        with return_picking_form.product_return_moves.edit(0) as line:
            line.quantity = 2
        return_wizard = return_picking_form.save()
        return_wizard.product_return_moves.to_refund = True
        return_picking = self.env["stock.picking"].browse(
            return_wizard.action_create_returns()["res_id"]
        )
        return_picking.move_ids.write({"quantity": 2, "picked": True})
        return_picking.button_validate()

        sol = so.line_ids
        self.assertEqual(sol.qty_transferred, 10.0)
        self.assertEqual(sol._get_procurement_qty(), 10.0)

        pickings_before = so.picking_ids
        sol.product_qty = 10.0

        self.assertEqual(so.picking_ids, pickings_before)
        self.assertEqual(sol._get_procurement_qty(), 10.0)
        self.assertEqual(sol.qty_to_transfer, 0.0)

    def _transit_route_setup(self):
        warehouse = self.company_data["default_warehouse"]
        warehouse.delivery_steps = "pick_ship"
        ship_rule, out_rule = warehouse.delivery_route_id.rule_ids[:2]
        transit = self.env["stock.location"].create(
            {
                "name": "Shipping transit",
                "usage": "transit",
                "company_id": self.env.company.id,
                "location_id": warehouse.view_location_id.id,
            }
        )
        so = self._get_new_sale_order(amount=10.0)
        so.action_confirm()
        sol = so.line_ids
        sol.move_ids.unlink()
        return {
            "sol": sol,
            "stock": warehouse.lot_stock_id,
            "transit": transit,
            "customers": self.env.ref("stock.stock_location_customers"),
            "ship_rule": ship_rule,
            "out_rule": out_rule,
            "warehouse": warehouse,
        }

    def _transit_leg(
        self,
        setup,
        source,
        destination,
        rule,
        *,
        qty=10.0,
        final=False,
        refund=False,
        origin=False,
        after=False,
        warehouse=True,
    ):
        sol = setup["sol"]
        move = self.env["stock.move"].create(
            {
                "product_id": sol.product_id.id,
                "product_uom_qty": qty,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "location_final_id": final and final.id,
                "rule_id": rule and rule.id,
                "warehouse_id": warehouse and setup["warehouse"].id,
                "sale_line_id": sol.id,
                "to_refund": refund,
                "origin_returned_move_id": origin and origin.id,
                "move_orig_ids": after and [Command.link(after.id)],
            }
        )
        move.write({"quantity": qty, "state": "done"})
        return move

    def _assert_no_new_picking(self, sol):
        pickings_before = sol.order_id.picking_ids
        sol.product_qty = sol.product_qty
        self.assertEqual(sol.order_id.picking_ids, pickings_before)

    def test_procurement_qty_transit_reship_counted_once(self):
        setup = self._transit_route_setup()
        sol, stock = setup["sol"], setup["stock"]
        transit, customers = setup["transit"], setup["customers"]
        ship_rule, out_rule = setup["ship_rule"], setup["out_rule"]

        ship = self._transit_leg(setup, stock, transit, ship_rule, final=customers)
        out = self._transit_leg(
            setup, transit, customers, out_rule, final=customers, after=ship
        )
        self._transit_leg(setup, customers, stock, out_rule, refund=True, origin=out)
        reversal = self._transit_leg(
            setup, stock, stock, ship_rule, refund=True, origin=ship
        )
        reship = self._transit_leg(
            setup, stock, transit, ship_rule, final=stock, refund=True, origin=reversal
        )
        self._transit_leg(
            setup, transit, customers, out_rule, refund=True, after=reship
        )

        self.assertEqual(sol.qty_transferred, 10.0)
        self.assertEqual(sol._get_procurement_qty(), 10.0)
        self._assert_no_new_picking(sol)

    def test_procurement_qty_transit_reversal_without_customer_leg(self):
        setup = self._transit_route_setup()
        sol, stock = setup["sol"], setup["stock"]
        transit, customers = setup["transit"], setup["customers"]
        ship_rule, out_rule = setup["ship_rule"], setup["out_rule"]

        ship = self._transit_leg(setup, stock, transit, ship_rule, final=customers)
        reversal = self._transit_leg(
            setup, transit, stock, ship_rule, refund=True, origin=ship
        )
        reship = self._transit_leg(
            setup, stock, transit, ship_rule, refund=True, origin=reversal
        )
        self._transit_leg(
            setup, transit, customers, out_rule, final=customers, after=reship
        )

        self.assertEqual(sol.qty_transferred, 10.0)
        self.assertEqual(sol._get_procurement_qty(), 10.0)
        self.assertEqual(sol.qty_to_transfer, 0.0)
        self._assert_no_new_picking(sol)

    def test_procurement_qty_counts_a_leg_still_on_its_way(self):
        setup = self._transit_route_setup()
        sol = setup["sol"]

        self._transit_leg(
            setup,
            setup["stock"],
            setup["transit"],
            setup["ship_rule"],
            final=setup["customers"],
        )

        self.assertEqual(sol.qty_transferred, 0.0, "nothing has reached the customer")
        self.assertEqual(sol._get_procurement_qty(), 10.0, "but the line is covered")
        self._assert_no_new_picking(sol)

    def test_procurement_qty_ignores_a_leg_that_came_straight_back(self):
        setup = self._transit_route_setup()
        sol, stock, transit = setup["sol"], setup["stock"], setup["transit"]

        ship = self._transit_leg(
            setup, stock, transit, setup["ship_rule"], final=setup["customers"]
        )
        self._transit_leg(
            setup, transit, stock, setup["ship_rule"], refund=True, origin=ship
        )

        self.assertEqual(sol.qty_transferred, 0.0)
        self.assertEqual(sol._get_procurement_qty(), 0.0)
        self.assertEqual(sol.qty_to_transfer, 10.0)

    def test_procurement_qty_direct_delivery_supersedes_staged_leg(self):
        setup = self._transit_route_setup()
        sol, stock = setup["sol"], setup["stock"]

        ship = self._transit_leg(
            setup, stock, setup["transit"], setup["ship_rule"], final=setup["customers"]
        )
        self._transit_leg(
            setup,
            setup["transit"],
            stock,
            setup["ship_rule"],
            refund=True,
            origin=ship,
        )
        self._transit_leg(
            setup,
            stock,
            setup["customers"],
            setup["out_rule"],
            final=setup["customers"],
        )

        self.assertEqual(sol.qty_transferred, 10.0)
        self.assertEqual(sol._get_procurement_qty(), 10.0)
        self._assert_no_new_picking(sol)

    def test_procurement_qty_one_shipment_counted_once_without_warehouse(self):
        setup = self._transit_route_setup()
        sol, stock = setup["sol"], setup["stock"]

        ship = self._transit_leg(
            setup,
            stock,
            setup["transit"],
            setup["ship_rule"],
            qty=4.0,
            final=setup["customers"],
            warehouse=False,
        )
        out = self._transit_leg(
            setup,
            setup["transit"],
            setup["customers"],
            setup["out_rule"],
            qty=4.0,
            final=setup["customers"],
            after=ship,
            warehouse=False,
        )
        self._transit_leg(
            setup,
            setup["customers"],
            stock,
            setup["out_rule"],
            qty=1.0,
            refund=True,
            origin=out,
            after=out,
        )

        self.assertEqual(sol.qty_transferred, 3.0)
        self.assertEqual(sol._get_procurement_qty(), 3.0)
        self.assertEqual(sol.qty_to_transfer, 7.0)

    def test_return_multisteps_receipt(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.reception_steps = "three_steps"
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking.button_validate()

        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=picking.id, active_model="stock.picking"
            )
        )
        with return_picking_form.product_return_moves.new() as line:
            line.product_id = self.new_product
            line.quantity = 2
        return_wizard = return_picking_form.save()
        res = return_wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        self.assertEqual(return_picking.location_id, picking.location_dest_id)
        self.assertEqual(
            return_picking.location_dest_id,
            warehouse.in_type_id.default_location_dest_id,
        )
        return_picking.button_validate()
        next_pick = return_picking.move_ids.move_dest_ids.picking_id
        next_pick.button_validate()
        next_pick = next_pick.move_ids.move_dest_ids.picking_id
        next_pick.button_validate()
        sol = self.env["sale.order.line"].search(
            [("product_id", "=", self.new_product.id)]
        )
        self.assertEqual(len(sol), 1)
        self.assertEqual(sol.qty_transferred, -2)

    def test_return_with_mto_and_multisteps(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.delivery_steps = "pick_pack_ship"
        stock_location = warehouse.lot_stock_id
        pack_location, out_location, custo_location = (
            warehouse.delivery_route_id.rule_ids.picking_type_id.default_location_dest_id
        )

        product = self.env["product.product"].create(
            {
                "name": "SuperProduct",
                "is_storable": True,
            }
        )

        self.env["stock.quant"]._update_available_quantity(product, stock_location, 5)

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a
        with so_form.line_ids.new() as line:
            line.product_id = product
            line.product_qty = 5
        so = so_form.save()
        so.action_confirm()

        pick_picking = so.picking_ids
        pick_picking.move_ids.write({"quantity": 5, "picked": True})
        pick_picking.button_validate()
        pack_picking = so.picking_ids - pick_picking
        pack_picking.move_ids.write({"quantity": 5, "picked": True})
        pack_picking.button_validate()

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 3
            so_form.save()

        moves = so.picking_ids.move_ids.sorted("id")
        pick_sm, pack_sm, ship_sm, ret_pick_sm, ret_pack_sm = moves
        self.assertRecordValues(
            moves,
            [
                {
                    "product_uom_qty": 5,
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": pack_sm.ids,
                },
                {
                    "product_uom_qty": 5,
                    "location_id": pack_location.id,
                    "location_dest_id": out_location.id,
                    "move_orig_ids": pick_sm.ids,
                    "move_dest_ids": ship_sm.ids,
                },
                {
                    "product_uom_qty": 3,
                    "location_id": out_location.id,
                    "location_dest_id": custo_location.id,
                    "move_orig_ids": pack_sm.ids,
                    "move_dest_ids": [],
                },
                {
                    "product_uom_qty": 2,
                    "location_id": pack_location.id,
                    "location_dest_id": stock_location.id,
                    "move_orig_ids": ret_pack_sm.ids,
                    "move_dest_ids": [],
                },
                {
                    "product_uom_qty": 2,
                    "location_id": out_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": ret_pick_sm.ids,
                },
            ],
        )

        for picking_type in warehouse.delivery_route_id.rule_ids.picking_type_id:
            step_moves = moves.filtered(
                lambda m, picking_type=picking_type: m.picking_type_id == picking_type
            )
            total_qty = sum(
                m.product_uom_qty
                if m.location_id == picking_type.default_location_src_id
                else -m.product_uom_qty
                for m in step_moves
            )
            self.assertEqual(total_qty, 3)

        ret_pack_sm.picking_id.action_assign()
        self.assertEqual(ret_pack_sm.state, "assigned")
        self.assertEqual(ret_pack_sm.move_line_ids.quantity, 2)

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 5

        moves = so.picking_ids.move_ids.sorted("id")
        self.assertRecordValues(
            moves,
            [
                {
                    "product_uom_qty": 5,
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": pack_sm.ids,
                },
                {
                    "product_uom_qty": 5,
                    "location_id": pack_location.id,
                    "location_dest_id": out_location.id,
                    "move_orig_ids": pick_sm.ids,
                    "move_dest_ids": ship_sm.ids,
                },
                {
                    "product_uom_qty": 3,
                    "location_id": out_location.id,
                    "location_dest_id": custo_location.id,
                    "move_orig_ids": pack_sm.ids,
                    "move_dest_ids": [],
                },
                {
                    "product_uom_qty": 2,
                    "location_id": pack_location.id,
                    "location_dest_id": stock_location.id,
                    "move_orig_ids": ret_pack_sm.ids,
                    "move_dest_ids": [],
                },
                {
                    "product_uom_qty": 2,
                    "location_id": out_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": ret_pick_sm.ids,
                },
                {
                    "product_uom_qty": 2,
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": [],
                },
            ],
        )

        step_moves = moves.filtered(
            lambda m: m.picking_type_id == warehouse.pick_type_id
        )
        total_pick_qty = sum(
            m.product_uom_qty
            if m.location_id == warehouse.pick_type_id.default_location_src_id
            else -m.product_uom_qty
            for m in step_moves
        )
        self.assertEqual(total_pick_qty, 5)

    def test_return_with_mto_and_multisteps_old_pull(self):
        stock_location = self.warehouse_3_steps_pull.lot_stock_id
        pack_location, out_location, custo_location = (
            self.warehouse_3_steps_pull.delivery_route_id.rule_ids.location_dest_id
        )

        product = self.env["product.product"].create(
            {
                "name": "SuperProduct",
                "is_storable": True,
            }
        )

        self.env["stock.quant"]._update_available_quantity(product, stock_location, 5)

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a
        so_form.warehouse_id = self.warehouse_3_steps_pull
        with so_form.line_ids.new() as line:
            line.product_id = product
            line.product_qty = 5
        so = so_form.save()
        so.action_confirm()

        _, pack_picking, pick_picking = so.picking_ids
        (pick_picking + pack_picking).move_ids.write({"quantity": 5, "picked": True})
        (pick_picking + pack_picking).button_validate()
        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 3

        moves = so.picking_ids.move_ids.sorted("id")
        ship_sm, pack_sm, pick_sm, ret_pack_sm, ret_pick_sm = moves
        self.assertRecordValues(
            moves,
            [
                {
                    "product_uom_qty": 3,
                    "location_id": out_location.id,
                    "location_dest_id": custo_location.id,
                    "move_orig_ids": pack_sm.ids,
                    "move_dest_ids": [],
                },
                {
                    "product_uom_qty": 5,
                    "location_id": pack_location.id,
                    "location_dest_id": out_location.id,
                    "move_orig_ids": pick_sm.ids,
                    "move_dest_ids": ship_sm.ids,
                },
                {
                    "product_uom_qty": 5,
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": pack_sm.ids,
                },
                {
                    "product_uom_qty": 2,
                    "location_id": out_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": ret_pick_sm.ids,
                },
                {
                    "product_uom_qty": 2,
                    "location_id": pack_location.id,
                    "location_dest_id": stock_location.id,
                    "move_orig_ids": ret_pack_sm.ids,
                    "move_dest_ids": [],
                },
            ],
        )

        for (
            picking_type
        ) in self.warehouse_3_steps_pull.delivery_route_id.rule_ids.picking_type_id:
            step_moves = moves.filtered(
                lambda m, picking_type=picking_type: m.picking_type_id == picking_type
            )
            total_qty = sum(
                m.product_uom_qty
                if m.location_id == picking_type.default_location_src_id
                else -m.product_uom_qty
                for m in step_moves
            )
            self.assertEqual(total_qty, 3)

        ret_pack_sm.picking_id.action_assign()
        self.assertEqual(ret_pack_sm.state, "assigned")
        self.assertEqual(ret_pack_sm.move_line_ids.quantity, 2)

        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 5

        moves = so.picking_ids.move_ids.sorted("id")
        (
            ship_sm,
            pack_sm,
            pick_sm,
            ret_pack_sm,
            ret_pick_sm,
            new_pack_sm,
            new_pick_sm,
        ) = moves
        self.assertRecordValues(
            moves,
            [
                {
                    "product_uom_qty": 5,
                    "location_id": out_location.id,
                    "location_dest_id": custo_location.id,
                    "move_orig_ids": (pack_sm | new_pack_sm).ids,
                    "move_dest_ids": [],
                },
                {
                    "product_uom_qty": 5,
                    "location_id": pack_location.id,
                    "location_dest_id": out_location.id,
                    "move_orig_ids": pick_sm.ids,
                    "move_dest_ids": ship_sm.ids,
                },
                {
                    "product_uom_qty": 5,
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": pack_sm.ids,
                },
                {
                    "product_uom_qty": 2,
                    "location_id": out_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": ret_pick_sm.ids,
                },
                {
                    "product_uom_qty": 2,
                    "location_id": pack_location.id,
                    "location_dest_id": stock_location.id,
                    "move_orig_ids": ret_pack_sm.ids,
                    "move_dest_ids": [],
                },
                {
                    "product_uom_qty": 2,
                    "location_id": pack_location.id,
                    "location_dest_id": out_location.id,
                    "move_orig_ids": new_pick_sm.ids,
                    "move_dest_ids": ship_sm.ids,
                },
                {
                    "product_uom_qty": 2,
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                    "move_orig_ids": [],
                    "move_dest_ids": new_pack_sm.ids,
                },
            ],
        )

        for (
            picking_type
        ) in self.warehouse_3_steps_pull.delivery_route_id.rule_ids.picking_type_id:
            step_moves = moves.filtered(
                lambda m, picking_type=picking_type: m.picking_type_id == picking_type
            )
            total_qty = sum(
                m.product_uom_qty
                if m.location_id == picking_type.default_location_src_id
                else -m.product_uom_qty
                for m in step_moves
            )
            self.assertEqual(total_qty, 5)

    def test_backorder_and_decrease_sol_qty(self):
        warehouse = self.company_data["default_warehouse"]
        warehouse.delivery_steps = "pick_ship"
        stock_location = warehouse.lot_stock_id
        out_location = warehouse.wh_output_stock_loc_id
        customer_location = self.env.ref("stock.stock_location_customers")

        so = self._get_new_sale_order()
        so.action_confirm()
        pick01 = so.picking_ids

        pick01.move_line_ids.write({"quantity": 6})
        pick01.move_ids.picked = True
        pick01._action_done()

        ship = so.picking_ids.filtered(
            lambda p: p.picking_type_id == warehouse.out_type_id
        )
        ship.move_ids.write({"quantity": 6, "picked": True})
        ship._action_done()

        so.line_ids.product_qty = 7

        self.assertRecordValues(
            so.picking_ids.move_ids.sorted("id"),
            [
                {
                    "location_id": stock_location.id,
                    "location_dest_id": out_location.id,
                    "product_uom_qty": 6.0,
                    "quantity": 6.0,
                    "state": "done",
                },
                {
                    "location_id": stock_location.id,
                    "location_dest_id": out_location.id,
                    "product_uom_qty": 1.0,
                    "quantity": 1.0,
                    "state": "assigned",
                },
                {
                    "location_id": out_location.id,
                    "location_dest_id": customer_location.id,
                    "product_uom_qty": 6.0,
                    "quantity": 6.0,
                    "state": "done",
                },
            ],
        )

    def test_incoterm_in_advance_payment(self):
        incoterm = self.env["account.incoterms"].create(
            {
                "name": "Test Incoterm",
                "code": "TEST",
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "incoterm_id": incoterm.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product_a.name,
                            "product_id": self.product_a.id,
                            "product_qty": 10,
                            "price_unit": 1,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        adv_wiz = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=[so.id])
            .create(
                {
                    "advance_payment_method": "percentage",
                    "amount": 5.0,
                }
            )
        )

        act = adv_wiz.create_invoices()
        invoice = self.env["account.move"].browse(act["res_id"])

        self.assertEqual(invoice.invoice_incoterm_id.id, incoterm.id)

    def test_exception_delivery_partial_multi(self):
        so_1 = self._get_new_sale_order()
        so_1.action_confirm()
        picking_1 = so_1.picking_ids
        picking_1.move_ids.write({"quantity": 1, "picked": True})

        so_2 = self._get_new_sale_order()
        so_2.action_confirm()
        picking_2 = so_2.picking_ids
        picking_2.move_ids.write({"quantity": 2, "picked": True})

        pick = picking_1 | picking_2
        wizard = Form.from_action(self.env, pick.button_validate()).save()
        wizard.backorder_confirmation_line_ids[1].write({"to_backorder": False})
        wizard.process()

        activity = self.env["mail.activity"].search(
            [("res_id", "=", so_2.id), ("res_model", "=", "sale.order")]
        )
        self.assertEqual(
            len(activity),
            1,
            "When no backorder is created for a partial delivery, a warning error should be logged in its origin SO",
        )

    def test_3_steps_and_unpack(self):
        warehouse = self.company_data.get("default_warehouse")
        self.env["res.config.settings"].write(
            {
                "group_stock_tracking_lot": True,
                "group_stock_adv_location": True,
                "group_stock_multi_locations": True,
            }
        )
        warehouse.delivery_steps = "pick_pack_ship"
        self.env["stock.quant"]._update_available_quantity(
            self.test_product_delivery, warehouse.lot_stock_id, 10
        )

        so_1 = self._get_new_sale_order(product=self.test_product_delivery)
        so_1.action_confirm()
        pick_picking = so_1.picking_ids.filtered(
            lambda p: p.picking_type_id == warehouse.pick_type_id
        )

        pick_picking.move_ids.write({"quantity": 2, "picked": True})
        pick_picking.action_put_in_pack()
        Form.from_action(self.env, pick_picking.button_validate()).save().process()

        pack_picking = so_1.picking_ids.filtered(
            lambda p: p.picking_type_id == warehouse.pack_type_id
        )
        pack_picking.move_line_ids.result_package_id = False
        pack_picking.move_ids.write({"quantity": 2, "picked": True})
        pack_picking.button_validate()

        out_picking = so_1.picking_ids.filtered(
            lambda p: p.picking_type_id == warehouse.out_type_id
        )
        self.assertEqual(out_picking.move_line_ids.package_id.id, False)
        self.assertEqual(out_picking.move_line_ids.result_package_id.id, False)

        pick_picking_2 = so_1.picking_ids.filtered(
            lambda x: x.picking_type_id == warehouse.pick_type_id and x.state != "done"
        )

        pick_picking_2.move_ids.write({"quantity": 2, "picked": True})
        package_2 = pick_picking_2.action_put_in_pack()
        Form.from_action(self.env, pick_picking_2.button_validate()).save().process()

        self.assertEqual(out_picking.move_line_ids.package_id.id, False)
        self.assertEqual(out_picking.move_line_ids.result_package_id.id, False)

        pack_picking_2 = so_1.picking_ids.filtered(
            lambda p: p.picking_type_id == warehouse.pack_type_id and p.state != "done"
        )

        pack_picking_2.move_ids.write({"quantity": 2, "picked": True})
        pack_picking_2.button_validate()

        self.assertRecordValues(
            out_picking.move_line_ids,
            [{"result_package_id": False}, {"result_package_id": package_2.id}],
        )

    def test_inventory_admin_no_backorder_not_own_sale_order(self):
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        pick = sale_order.picking_ids
        inventory_admin_user = self.env["res.users"].create(
            {
                "name": "documents test basic user",
                "login": "dtbu",
                "email": "dtbu@yourcompany.com",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            self.ref("base.group_user"),
                            self.ref("stock.group_stock_manager"),
                            self.ref("sale.group_sale_salesman"),
                        ],
                    )
                ],
            }
        )
        pick.with_user(inventory_admin_user).move_ids.write(
            {"quantity": 1, "picked": True}
        )
        Form.from_action(
            self.env(user=inventory_admin_user), pick.button_validate()
        ).save().action_cancel_backorder()

    def test_reduce_qty_ordered_no_backorder(self):
        so_1 = self._get_new_sale_order(amount=3, product=self.test_product_delivery)
        so_1.action_confirm()
        self.assertEqual(so_1.line_ids.product_qty, 3)
        self.assertEqual(len(so_1.picking_ids), 1)

        delivery_picking = so_1.picking_ids
        delivery_picking.move_ids.quantity = 2
        Form.from_action(
            self.env, delivery_picking.button_validate()
        ).save().action_cancel_backorder()
        self.assertEqual(so_1.line_ids.product_qty, 3)
        self.assertEqual(so_1.line_ids.qty_transferred, 2)

        so_1.write(
            {
                "line_ids": [
                    (
                        1,
                        so_1.line_ids.id,
                        {"product_qty": so_1.line_ids.qty_transferred},
                    )
                ]
            }
        )
        self.assertEqual(len(so_1.picking_ids), 1)

    def test_decrease_sol_qty_to_zero(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.delivery_steps = "pick_ship"

        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_qty": 1,
                            "price_unit": p.list_price,
                        },
                    )
                    for p in (
                        self.product_a,
                        self.product_b,
                    )
                ],
            }
        )
        so.action_confirm()

        pick_picking = so.picking_ids
        pick_picking.move_ids.picked = True

        so.line_ids[0].product_qty = 0

        self.assertRecordValues(
            pick_picking.move_ids,
            [
                {
                    "product_id": self.product_a.id,
                    "product_uom_qty": 0,
                    "quantity": 1,
                    "state": "assigned",
                },
                {
                    "product_id": self.product_b.id,
                    "product_uom_qty": 1,
                    "quantity": 1,
                    "state": "assigned",
                },
            ],
        )

    def test_create_so_return_with_tracked_product(self):
        self.product_a.is_storable = True
        self.product_a.tracking = "serial"
        sn1 = self.env["stock.lot"].create(
            {
                "name": "SN0001",
                "product_id": self.product_a.id,
                "company_id": self.env.company.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_a,
            self.company_data["default_warehouse"].lot_stock_id,
            1,
            lot_id=sn1,
        )
        sale_order = self._get_new_sale_order(amount=1, product=self.product_a)
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        picking = sale_order.picking_ids
        picking.button_validate()

        self.assertEqual(sale_order.line_ids.qty_transferred, 1)
        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=picking.ids,
                active_id=picking.id,
                active_model="stock.picking",
            )
        )
        return_wizard = return_picking_form.save()
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.quantity = 1

        res = return_wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(res["res_id"])
        return_picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)
        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=return_picking.ids,
                active_id=return_picking.id,
                active_model="stock.picking",
            )
        )
        return_wizard = return_picking_form.save()
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.quantity = 1

        res = return_wizard.action_create_returns()
        return_picking_2 = self.env["stock.picking"].browse(res["res_id"])
        return_picking_2.button_validate()

    def test_2_steps_pull_and_decrease_sol_qty_to_zero(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        customer_location = self.env.ref("stock.stock_location_customers")

        warehouse.delivery_steps = "pick_ship"
        warehouse.delivery_route_id.rule_ids = [
            (5, 0, 0),
            (
                0,
                0,
                {
                    "name": "Pull out->custo",
                    "action": "pull",
                    "location_src_id": warehouse.wh_output_stock_loc_id.id,
                    "location_dest_id": customer_location.id,
                    "picking_type_id": warehouse.out_type_id.id,
                    "propagate_cancel": True,
                    "procure_method": "make_to_order",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Pull stock->out",
                    "action": "pull",
                    "location_src_id": warehouse.lot_stock_id.id,
                    "location_dest_id": warehouse.wh_output_stock_loc_id.id,
                    "picking_type_id": warehouse.pick_type_id.id,
                    "propagate_cancel": True,
                    "procure_method": "make_to_stock",
                },
            ),
        ]

        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product_a.name,
                            "product_id": self.product_a.id,
                            "product_qty": 1,
                            "price_unit": self.product_a.list_price,
                        },
                    )
                ],
            }
        )
        so.action_confirm()

        so.line_ids.product_qty = 0

        self.assertEqual(so.picking_ids.move_ids.mapped("state"), ["cancel", "cancel"])

    def test_delivery_on_negative_delivered_qty(self):
        product = self.env["product.product"].create(
            {
                "name": "Super product",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "lst_price": 100.0,
                "is_storable": True,
                "invoice_policy": "transferred",
            }
        )
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "state": "draft",
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": -1,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0.0)
        self.assertEqual(sale_order.line_ids.qty_to_invoice, 0.0)
        picking = (
            self.env["stock.move"]
            .browse(
                self.env["stock.move"]
                .search([("sale_line_id", "=", sale_order.line_ids.id)])
                .id
            )
            .picking_id
        )
        picking.action_confirm()
        picking.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, -1.0)
        self.assertEqual(sale_order.line_ids.qty_to_invoice, -1.0)

    def test_reduce_qty_on_partially_moved(self):
        warehouse = self.company_data["default_warehouse"]
        warehouse.delivery_steps = "pick_pack_ship"
        product = self.env["product.product"].create(
            {
                "name": "To be delivered",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 10
        )
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_a
            with so_form.line_ids.new() as line:
                line.product_id = product
                line.product_qty = 10
            sale_order = so_form.save()
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1)

        pick = sale_order.picking_ids
        self.assertEqual(pick.picking_type_id, warehouse.pick_type_id)
        pick.move_ids.write({"quantity": 6, "picked": True})
        pick._action_done()
        pick_backorder = pick.backorder_ids
        self.assertEqual(pick_backorder.move_ids.product_uom_qty, 4)

        pack = sale_order.picking_ids - (pick | pick_backorder)
        self.assertEqual(pack.picking_type_id, warehouse.pack_type_id)
        self.assertEqual(pack.move_ids.product_uom_qty, 6)

        with Form(sale_order) as so_form:
            with so_form.line_ids.edit(0) as line:
                line.product_qty = 5
            sale_order = so_form.save()

        self.assertEqual(
            len(sale_order.picking_ids),
            4,
            "PICK + PICK backorder + PACK + (new) PICK return",
        )
        self.assertEqual(pick_backorder.state, "cancel")
        self.assertEqual(pack.move_ids.product_uom_qty, 5)
        self.assertEqual(pack.state, "assigned")
        pick_return = sale_order.picking_ids - (pick | pick_backorder | pack)
        self.assertEqual(pick_return.picking_type_id, warehouse.pick_type_id)
        self.assertEqual(pick_return.move_ids.product_uom_qty, 1)
        self.assertEqual(pick_return.location_dest_id, warehouse.lot_stock_id)
        self.assertEqual(pick_return.state, "assigned")

    def test_return_partial_delivery(self):
        warehouse = self.company_data["default_warehouse"]
        warehouse.delivery_steps = "pick_pack_ship"
        product = self.env["product.product"].create(
            {
                "name": "To be delivered",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 10
        )
        with Form(self.env["sale.order"]) as so_form:
            so_form.partner_id = self.partner_a
            with so_form.line_ids.new() as line:
                line.product_id = product
                line.product_qty = 3
            sale_order = so_form.save()
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1)
        pick = sale_order.picking_ids
        self.assertEqual(pick.picking_type_id, warehouse.pick_type_id)
        pick.move_ids.write({"quantity": 1, "picked": True})
        pick._action_done()
        pick_backorder = pick.backorder_ids
        self.assertEqual(pick_backorder.move_ids.product_uom_qty, 2)
        pack_1 = sale_order.picking_ids - pick
        pack_1.move_ids.write({"quantity": 1, "picked": True})
        pack_1._action_done()
        pick_backorder.move_ids.write({"quantity": 2, "picked": True})
        pick_backorder._action_done()
        self.assertEqual(pick_backorder.state, "done")
        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=pick_backorder.ids,
                active_id=pick_backorder.sorted().ids[0],
                active_model="stock.picking",
            )
        )
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 2.0
        return_wiz.product_return_moves.to_refund = True
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])
        return_pick.move_ids.write({"quantity": 2, "picked": True})
        return_pick.button_validate()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0)

    def test_sale_order_cancel_with_cyclic_returns(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                        }
                    )
                ],
            }
        )

        sale_order.action_confirm()
        self.assertEqual(sale_order.state, "done")

        picking = sale_order.picking_ids.filtered(
            lambda p: p.state not in ("done", "cancel")
        )
        self.assertTrue(picking, "Delivery picking should exist.")

        def _validate(pick):
            pick.move_ids.write({"quantity": 1, "picked": True})
            pick._action_done()
            return pick

        _validate(picking)

        return_wizard = self.env["stock.return.picking"].with_context(
            active_id=picking.id, active_model="stock.picking"
        )
        return_wiz_1 = return_wizard.create({})
        return_res_1 = return_wiz_1.action_create_returns_all()
        return_picking_1 = self.env["stock.picking"].browse(return_res_1["res_id"])
        _validate(return_picking_1)

        return_wizard2 = self.env["stock.return.picking"].with_context(
            active_id=return_picking_1.id, active_model="stock.picking"
        )
        return_wiz_2 = return_wizard2.create({})
        return_wiz_2.action_create_returns_all()

        sale_order._action_cancel()
        self.assertEqual(sale_order.state, "cancel")

    def test_sol_reserved_qty_wizard_3_steps_delivery(self):
        admin = self.env.ref("base.user_admin")
        admin.write(
            {
                "email": "mitchell.admin@example.com",
            }
        )
        warehouse = self.env.ref("stock.warehouse0").with_user(admin)
        warehouse.delivery_steps = "pick_pack_ship"
        product = self.product_a
        product.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            product, warehouse.lot_stock_id, 10.0
        )
        sale_order = (
            self.env["sale.order"]
            .with_user(admin)
            .create(
                {
                    "company_id": warehouse.company_id.id,
                    "warehouse_id": warehouse.id,
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_qty": 7.0,
                            }
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        pick = sale_order.picking_ids.filtered(
            lambda p: p.location_id == warehouse.lot_stock_id
        )
        self.assertEqual(pick.move_line_ids.quantity, 7.0)
        self.assertEqual(sale_order.line_ids.qty_available_today, 7.0)
        pick.move_ids.quantity = 7.0
        pick.move_ids.picked = True
        pick.button_validate()
        pack = sale_order.picking_ids - pick
        self.assertEqual(sale_order.line_ids.qty_available_today, 7.0)
        pack.move_ids.quantity = 2.0
        pack.move_ids.picked = True
        Form.from_action(self.env(user=admin), pack.button_validate()).save().process()
        backorder = pack.backorder_ids
        ship = sale_order.picking_ids.filtered(
            lambda p: (
                p.location_dest_id == self.env.ref("stock.stock_location_customers")
            )
        )
        self.assertEqual(sum(backorder.move_line_ids.mapped("quantity")), 5.0)
        self.assertEqual(sum(ship.move_line_ids.mapped("quantity")), 2.0)
        self.assertEqual(sale_order.line_ids.qty_available_today, 7.0)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0.0)
        backorder.move_ids.quantity = 5.0
        backorder.move_ids.picked = True
        backorder.button_validate()
        self.assertEqual(sum(ship.move_line_ids.mapped("quantity")), 7.0)
        self.assertEqual(sale_order.line_ids.qty_available_today, 7.0)
        self.assertEqual(sale_order.line_ids.qty_transferred, 0.0)
        ship.move_ids.quantity = 7.0
        ship.move_ids.picked = True
        ship.button_validate()
        self.assertEqual(sale_order.line_ids.qty_available_today, 0.0)
        self.assertEqual(sale_order.line_ids.qty_transferred, 7.0)

    def test_transfer_state(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.delivery_steps = "pick_ship"

        so = self.env["sale.order"].create(
            {
                "partner_id": self.env["res.partner"].create({"name": "My Partner"}).id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "sol_p1",
                            "product_id": self.env["product.product"]
                            .create({"name": "p1"})
                            .id,
                            "product_qty": 10,
                        }
                    ),
                ],
            }
        )
        so.action_confirm()
        self.assertEqual(so.transfer_state, "to do")

        pick01 = so.picking_ids
        pick01.move_ids.write({"quantity": 10, "picked": True})
        pick01.button_validate()
        self.assertEqual(so.transfer_state, "partial")

        ship01 = so.picking_ids.filtered(
            lambda p: p.picking_type_id == warehouse.out_type_id
        )
        ship01.move_ids.write({"quantity": 3, "picked": True})
        Form.from_action(self.env, ship01.button_validate()).save().process()
        self.assertEqual(so.transfer_state, "partial")

        ship02 = ship01.backorder_ids[0]
        ship02.move_ids.write({"quantity": 7, "picked": True})
        ship02.button_validate()
        self.assertEqual(so.transfer_state, "done")

    def test_so_delivery_ignores_shipping_policy_from_picking_type(self):
        picking_type_out = self.company_data["default_warehouse"].out_type_id
        picking_type_out.move_type = "direct"

        so = self._get_new_sale_order()
        so.picking_policy = "one"
        so.action_confirm()

        self.assertEqual(so.picking_ids[0].picking_type_id, picking_type_out)
        self.assertEqual(so.picking_ids[0].move_type, "one")

    def test_double_return_on_so(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "sol_p1",
                            "product_id": self.env["product.product"]
                            .create({"name": "p1"})
                            .id,
                            "product_qty": 5,
                        }
                    ),
                ],
            }
        )
        so.action_confirm()
        delivery = so.picking_ids
        delivery.button_validate()
        self.assertEqual(so.line_ids.qty_transferred, 5.0)
        return_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=delivery.id, active_model="stock.picking"
            )
        )
        return_wiz = return_form.save()
        return_wiz.product_return_moves.write({"quantity": 5.0})
        res = return_wiz.action_create_returns()
        do_return = self.env["stock.picking"].browse(res["res_id"])
        do_return.button_validate()
        self.assertEqual(so.line_ids.qty_transferred, 0.0)
        return_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=do_return.id, active_model="stock.picking"
            )
        )
        return_wiz = return_form.save()
        return_wiz.product_return_moves.write({"quantity": 5.0})
        res = return_wiz.action_create_returns()
        do_return_return = self.env["stock.picking"].browse(res["res_id"])
        do_return_return.button_validate()
        self.assertEqual(so.line_ids.qty_transferred, 5.0)
        with Form(so) as so_form:
            with so_form.line_ids.edit(0) as line_form:
                line_form.product_qty = 8.0
        delivery_2 = so.picking_ids - delivery - do_return - do_return_return
        self.assertTrue(delivery_2)
        self.assertEqual(delivery_2.move_ids.product_uom_qty, 3.0)
        self.assertEqual(so.line_ids.qty_transferred, 5.0)

    def test_warehouse_redirect_warnings(self):
        new_company = self.env["res.company"].create({"name": "Company 2"})
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", new_company.id)], limit=1
        )
        warehouse.active = False
        storable_product = self.env["product.product"].create(
            {
                "name": "Lovely Product",
                "is_storable": True,
            }
        )
        so = (
            self.env["sale.order"]
            .with_company(new_company)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": storable_product.name,
                                "product_id": storable_product.id,
                                "product_qty": 1,
                            }
                        ),
                    ],
                }
            )
        )
        error_message = "Please create a warehouse for company Company 2."
        with (
            self.assertRaisesRegex(RedirectWarning, error_message),
            self.env.cr.savepoint(),
        ):
            so.with_company(new_company).action_confirm()
        warehouse.active = True
        error_message = "You must set a warehouse on your sale order to proceed."
        with self.assertRaisesRegex(UserError, error_message), self.env.cr.savepoint():
            so.with_company(new_company).action_confirm()
        self.env["stock.warehouse"].create(
            {"name": "Warehouse 2", "code": "WH2", "company_id": new_company.id}
        )
        error_message = "You must set a warehouse on your sale order to proceed."
        with self.assertRaisesRegex(UserError, error_message), self.env.cr.savepoint():
            so.with_company(new_company).action_confirm()

    def test_custom_delivery_route_new_sale_line(self):
        warehouse = self.company_data["default_warehouse"]
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref("stock.stock_location_customers")
        transit_location = self.env["stock.location"].create(
            {
                "name": "Transit",
                "usage": "transit",
                "location_id": warehouse.view_location_id.id,
            }
        )
        warehouse.pick_type_id.default_location_dest_id = transit_location

        warehouse.delivery_route_id = self.env["stock.route"].create(
            {
                "name": "2 Steps Pull Delivery Route",
                "warehouse_selectable": True,
                "warehouse_ids": [(4, warehouse.id)],
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Stock to Output",
                            "action": "pull",
                            "location_src_id": stock_location.id,
                            "location_dest_id": transit_location.id,
                            "picking_type_id": warehouse.pick_type_id.id,
                            "procure_method": "make_to_stock",
                        }
                    ),
                    Command.create(
                        {
                            "name": "Output to Customer",
                            "action": "pull",
                            "location_src_id": transit_location.id,
                            "location_dest_id": customer_location.id,
                            "picking_type_id": warehouse.out_type_id.id,
                            "procure_method": "make_to_order",
                        }
                    ),
                ],
            }
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "Test Product",
                            "product_id": self.product_a.id,
                            "product_qty": 1.0,
                            "price_unit": 1.0,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()

        pickings = sale_order.picking_ids
        self.assertEqual(
            len(pickings),
            2,
            "Expected two pickings: Stock->Output and Output->Customer",
        )
        # selected by destination, not by position: `stock.picking._order` ends
        # `id desc`, and both pickings carry the same date_planned, so indexing
        # asserts which one the procurement happened to create last
        to_transit = pickings.filtered(
            lambda picking: picking.location_dest_id == transit_location
        )
        to_customer = pickings.filtered(
            lambda picking: picking.location_dest_id == customer_location
        )
        self.assertEqual(len(to_transit), 1)
        self.assertEqual(len(to_customer), 1)
        self.assertEqual(to_transit.location_id, stock_location)
        self.assertEqual(to_customer.location_id, transit_location)

        to_transit.move_ids.picked = True
        to_transit.button_validate()

        self.assertEqual(to_transit.state, "done")
        self.assertEqual(len(sale_order.line_ids), 1)

    def test_multi_step_product_forecast_availability(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.delivery_steps = "pick_ship"

        self.env["stock.quant"]._update_available_quantity(
            self.new_product, warehouse.lot_stock_id, 1
        )

        so = self._get_new_sale_order(product=self.new_product, amount=1)
        so.action_confirm()

        self.assertEqual(
            so.picking_ids.move_ids.forecast_availability,
            1.0,
            "Forecast availability should be 1.0 because 1.0 quantity is available."
            "So forecast availability icon should appear green.",
        )
        self.assertEqual(
            so.line_ids.qty_free_today,
            1.0,
            "Free quantity today should be 1.0, indicating the quantity is usable for this SO.",
        )

    def test_extra_return_product_so_sequence(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 2,
                            "sequence": 42,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_b.id,
                            "product_qty": 3,
                            "sequence": 43,
                        },
                    ),
                ],
            }
        )
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.button_validate()
        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=picking.id, active_model="stock.picking"
            )
        )
        with return_picking_form.product_return_moves.new() as line:
            line.product_id = self.new_product
            line.quantity = 4
        return_wiz = return_picking_form.save()
        res = return_wiz.action_create_returns()
        return_pick = self.env["stock.picking"].browse(res["res_id"])
        return_pick.button_validate()
        self.assertEqual(sale_order.line_ids.mapped("sequence"), [42, 43, 44])

    def test_move_description(self):
        product_with_description = self.env["product.template"].create(
            {
                "name": "Product with description",
                "description_pickingout": "Deliver with care",
                "description_sale": "Sale description",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": self.color_attribute.id,
                            "value_ids": [
                                Command.set(self.color_attribute.value_ids.ids)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "attribute_id": self.no_variant_attribute.id,
                            "value_ids": [
                                Command.set(self.no_variant_attribute.value_ids.ids)
                            ],
                        }
                    ),
                ],
            }
        )
        so = self._get_new_sale_order(
            product=product_with_description.product_variant_ids.filtered(
                lambda p: p.product_template_attribute_value_ids.name == "red"
            ),
            amount=1,
            sol_vals={
                "product_no_variant_attribute_value_ids": [
                    Command.set(
                        product_with_description.attribute_line_ids[1]
                        .product_template_value_ids[0]
                        .ids
                    )
                ],
            },
        )
        self.assertEqual(
            so.line_ids.name,
            "Product with description (red)\nSale description\nNo variant: extra",
        )
        so.line_ids.name += "\nRandom sale notes"
        so.action_confirm()
        self.assertEqual(
            so.picking_ids.move_ids.description_picking,
            "No variant: extra\nDeliver with care",
        )

    def test_move_description_uses_custom_attribute_values(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        product = self.new_product
        product.with_context(lang="fr_FR").name = "French Sofa"
        self.partner_b.lang = "fr_FR"
        attribute_line = self.env["product.template.attribute.line"].create(
            {
                "product_tmpl_id": self.product_template_sofa.id,
                "attribute_id": self.no_variant_attribute.id,
                "value_ids": [Command.set([self.no_variant_attribute.value_ids[0].id])],
            }
        )
        order_line_vals = {
            "product_id": product.id,
            "product_custom_attribute_value_ids": [
                Command.create(
                    {
                        "custom_product_template_attribute_value_id": attribute_line.product_template_value_ids.id,
                        "custom_value": "Best",
                    }
                )
            ],
        }
        sale_orders = self.env["sale.order"].create(
            [
                {
                    "partner_id": partner.id,
                    "line_ids": [Command.create(order_line_vals)],
                }
                for partner in [self.partner_a, self.partner_b]
            ]
        )
        sale_orders.action_confirm()
        self.assertEqual(
            sale_orders.picking_ids.move_ids.mapped("description_picking"),
            ["No variant: extra: Best", "No variant: extra: Best\nFrench Sofa"],
        )

    def test_multicompany_transit_with_one_company_for_user(self):
        company_a = self.env["res.company"].create({"name": "Company A"})
        company_b = self.env["res.company"].create({"name": "Company B"})
        user_a = self.env["res.users"].create(
            {
                "name": "user only in company a",
                "login": "user a",
                "company_id": company_a.id,
                "company_ids": [Command.link(company_a.id)],
                "group_ids": [
                    Command.link(self.env.ref("sale.group_sale_salesman").id)
                ],
            }
        )
        product = self.new_product
        so = (
            self.env["sale.order"]
            .with_user(user_a)
            .create(
                {
                    "partner_id": company_b.partner_id.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                            }
                        ),
                    ],
                }
            )
        )
        so.action_confirm()
        intercom_location = self.env.ref("stock.stock_location_inter_company")
        self.assertEqual(so.picking_ids.location_dest_id, intercom_location)
        self.assertEqual(so.picking_ids.move_ids.location_dest_id, intercom_location)

    def test_sale_order_line_quantity_forecast_widget_display(self):
        self.product_a.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            self.product_a, self.company_data["default_warehouse"].lot_stock_id, 15
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create({"product_id": self.product_a.id, "product_qty": 5}),
                ],
            }
        )
        sale_order.action_confirm()
        self.assertTrue(sale_order.line_ids.display_qty_widget)
        picking = sale_order.picking_ids
        picking.move_ids[0].quantity = 2
        backorder_wizard_dict = picking.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().action_cancel_backorder()
        self.assertFalse(sale_order.line_ids.display_qty_widget)

    def test_create_route_update_so_quantity(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        warehouse.delivery_steps = "pick_pack_ship"
        stock_location = warehouse.lot_stock_id
        pack_location, out_location, _ = (
            warehouse.delivery_route_id.rule_ids.picking_type_id.default_location_dest_id
        )

        self.product_a.is_storable = True
        self.env["stock.quant"]._update_available_quantity(
            self.product_a, stock_location, 5
        )
        loc_perso = self.env["stock.location"].create(
            {
                "name": "Locperso",
                "location_id": stock_location.id,
            }
        )
        warehouse.delivery_route_id.rule_ids = [
            Command.create(
                {
                    "name": "Push stock->Locperso",
                    "action": "push",
                    "location_src_id": loc_perso.id,
                    "location_dest_id": out_location.id,
                    "picking_type_id": warehouse.int_type_id.id,
                    "propagate_cancel": False,
                    "procure_method": "make_to_stock",
                }
            ),
        ]
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": self.product_a.name,
                            "product_id": self.product_a.id,
                            "product_qty": 1,
                            "price_unit": self.product_a.list_price,
                        }
                    )
                ],
            }
        )
        so.action_confirm()
        picking_1 = so.picking_ids
        self.assertRecordValues(
            picking_1,
            [
                {
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                },
            ],
        )
        picking_1.location_dest_id = loc_perso
        picking_1.button_validate()
        so.line_ids.product_qty = 2

        self.assertRecordValues(
            so.picking_ids.move_ids.sorted("id"),
            [
                {
                    "location_id": stock_location.id,
                    "location_dest_id": loc_perso.id,
                    "quantity": 1,
                },
                {
                    "location_id": loc_perso.id,
                    "location_dest_id": out_location.id,
                    "quantity": 1,
                },
                {
                    "location_id": stock_location.id,
                    "location_dest_id": pack_location.id,
                    "quantity": 1,
                },
            ],
        )

    def test_a_replenishment_receipt_on_the_sale_reference_is_not_one_of_its_transfers(
        self,
    ):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create({"product_id": self.product_a.id, "product_qty": 1})
                ],
            }
        )
        sale_order.action_confirm()
        delivery = sale_order.picking_ids
        warehouse = delivery.picking_type_id.warehouse_id
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        stock_location = delivery.location_id
        self.assertTrue(delivery.reference_ids.sale_ids)

        def picking_on_the_sale_reference(picking_type, source, destination, **move):
            return self.env["stock.picking"].create(
                {
                    "picking_type_id": picking_type.id,
                    "location_id": source.id,
                    "location_dest_id": destination.id,
                    "move_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "product_uom_qty": 1,
                                "location_id": source.id,
                                "location_dest_id": destination.id,
                                "reference_ids": [
                                    Command.set(delivery.reference_ids.ids)
                                ],
                                **move,
                            }
                        )
                    ],
                }
            )

        receipt = picking_on_the_sale_reference(
            warehouse.in_type_id, supplier_location, stock_location
        )
        put_away = picking_on_the_sale_reference(
            warehouse.int_type_id,
            stock_location,
            stock_location,
            move_orig_ids=[Command.link(receipt.move_ids.id)],
        )
        transit_receipt = picking_on_the_sale_reference(
            warehouse.in_type_id,
            self.env.ref("stock.stock_location_inter_company"),
            stock_location,
        )
        untracked_delivery = picking_on_the_sale_reference(
            warehouse.out_type_id, stock_location, delivery.location_dest_id
        )

        self.assertEqual(receipt.reference_ids.sale_ids, sale_order)
        self.assertFalse(receipt.sale_id)
        self.assertFalse(put_away.sale_id)
        self.assertFalse(transit_receipt.sale_id)
        self.assertEqual(untracked_delivery.sale_id, sale_order)
        self.assertEqual(sale_order.picking_ids, delivery | untracked_delivery)

    def test_update_picking_sale_order(self):
        self.new_product.is_storable = False
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 1,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        so_delivery = sale_order.picking_ids
        self.assertEqual(so_delivery.move_ids.sale_line_id, sale_order.line_ids)

        new_delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": so_delivery.picking_type_id.id,
                "location_id": so_delivery.location_id.id,
                "location_dest_id": so_delivery.location_dest_id.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_uom_qty": 2,
                            "location_id": so_delivery.location_id.id,
                            "location_dest_id": so_delivery.location_dest_id.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.new_product.id,
                            "product_uom_qty": 3,
                            "location_id": so_delivery.location_id.id,
                            "location_dest_id": so_delivery.location_dest_id.id,
                        }
                    ),
                ],
            }
        )
        new_delivery.action_confirm()
        self.assertFalse(new_delivery.sale_id)
        self.assertRecordValues(
            new_delivery.move_ids,
            [
                {"product_id": self.product_a.id, "sale_line_id": False},
                {"product_id": self.new_product.id, "sale_line_id": False},
            ],
        )

        new_delivery.sale_id = sale_order
        self.assertRecordValues(
            new_delivery.move_ids,
            [
                {
                    "product_id": self.product_a.id,
                    "sale_line_id": sale_order.line_ids.id,
                },
                {"product_id": self.new_product.id, "sale_line_id": False},
            ],
        )

        new_delivery.button_validate()
        self.assertRecordValues(
            new_delivery.move_ids,
            [
                {
                    "product_id": self.product_a.id,
                    "sale_line_id": sale_order.line_ids[0].id,
                },
                {
                    "product_id": self.new_product.id,
                    "sale_line_id": sale_order.line_ids[1].id,
                },
            ],
        )
        self.assertRecordValues(
            sale_order.line_ids,
            [
                {
                    "product_id": self.product_a.id,
                    "product_qty": 1,
                    "qty_transferred": 2,
                },
                {
                    "product_id": self.new_product.id,
                    "product_qty": 0,
                    "qty_transferred": 3,
                },
            ],
        )

        so_delivery.sale_id = False
        self.assertRecordValues(
            so_delivery.move_ids,
            [
                {"product_id": self.product_a.id, "sale_line_id": False},
            ],
        )
        so_delivery.button_validate()
        self.assertRecordValues(
            sale_order.line_ids,
            [
                {
                    "product_id": self.product_a.id,
                    "product_qty": 1,
                    "qty_transferred": 2,
                },
                {
                    "product_id": self.new_product.id,
                    "product_qty": 0,
                    "qty_transferred": 3,
                },
            ],
        )

    def test_sale_line_route_overrides_product_routes(self):
        warehouse = self.company_data["default_warehouse"]
        customer_location = self.env.ref("stock.stock_location_customers")
        transit_location = self.env["stock.location"].create(
            {
                "name": "Transit",
                "usage": "transit",
                "location_id": warehouse.view_location_id.id,
            }
        )

        route_product, route_so = self.env["stock.route"].create(
            [
                {
                    "name": "Route set in the product",
                    "warehouse_ids": [Command.link(warehouse.id)],
                    "rule_ids": [
                        Command.create(
                            {
                                "name": "Stock to transit",
                                "action": "pull",
                                "location_src_id": warehouse.lot_stock_id.id,
                                "location_dest_id": transit_location.id,
                                "picking_type_id": warehouse.int_type_id.id,
                                "procure_method": "make_to_stock",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Transit to Customer",
                                "action": "pull",
                                "location_src_id": transit_location.id,
                                "location_dest_id": customer_location.id,
                                "picking_type_id": warehouse.out_type_id.id,
                                "procure_method": "make_to_order",
                            }
                        ),
                    ],
                },
                {
                    "name": "Route set in the SOL",
                    "warehouse_ids": [Command.link(warehouse.id)],
                    "sale_selectable": True,
                    "rule_ids": [
                        Command.create(
                            {
                                "name": "Stock to transit",
                                "action": "pull",
                                "location_src_id": warehouse.lot_stock_id.id,
                                "location_dest_id": transit_location.id,
                                "picking_type_id": warehouse.int_type_id.id,
                                "procure_method": "make_to_stock",
                            }
                        ),
                        Command.create(
                            {
                                "name": "Transit to Customer",
                                "action": "pull",
                                "location_src_id": transit_location.id,
                                "location_dest_id": customer_location.id,
                                "picking_type_id": warehouse.out_type_id.id,
                                "procure_method": "make_to_order",
                            }
                        ),
                    ],
                },
            ]
        )

        product = self.env["product.product"].create(
            {
                "name": "SuperProduct",
                "is_storable": True,
                "route_ids": [route_product.id],
            }
        )

        so = self.env["sale.order"].create(
            [
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": product.name,
                                "product_id": product.id,
                                "product_qty": 8.0,
                                "price_unit": product.list_price,
                                "route_ids": [route_so.id],
                            }
                        ),
                    ],
                },
            ]
        )
        so.action_confirm()

        self.assertRecordValues(
            so.picking_ids.move_ids.rule_id, [{"route_id": route_so.id}] * 2
        )

    def test_set_sale_reference_on_delivery(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        delivery = self.env["stock.picking"].create(
            {
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": self.ref("stock.stock_location_customers"),
                "move_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 2,
                            "product_uom_id": self.product.uom_id.id,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": self.ref(
                                "stock.stock_location_customers"
                            ),
                        }
                    )
                ],
            }
        )
        self.assertFalse(delivery.reference_ids | delivery.move_ids.reference_ids)
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
            }
        )
        delivery.sale_id = sale_order
        self.assertEqual(delivery.reference_ids.sale_ids, sale_order)
        self.assertEqual(delivery.move_ids.reference_ids, delivery.reference_ids)

    def test_sale_partner_propagation_3_step_pull(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "warehouse_id": self.warehouse_3_steps_pull.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "product_qty": 1,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        self.assertRecordValues(
            sale_order.picking_ids.sorted(lambda p: p.picking_type_id.name)[::-1],
            [
                {
                    "partner_id": self.partner_a.id,
                    "picking_type_id": self.warehouse_3_steps_pull.pick_type_id.id,
                },
                {
                    "partner_id": self.partner_a.id,
                    "picking_type_id": self.warehouse_3_steps_pull.pack_type_id.id,
                },
                {
                    "partner_id": self.partner_a.id,
                    "picking_type_id": self.warehouse_3_steps_pull.out_type_id.id,
                },
            ],
        )

    def test_compute_sale_order_count_with_stock_user(self):
        user = new_test_user(
            self.env,
            login="fgh",
            groups="base.group_user,stock.group_stock_user, sale.group_sale_salesman",
        )
        self.new_product.tracking = "lot"
        lot = self.env["stock.lot"].create(
            {
                "name": "SN001",
                "product_id": self.new_product.id,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.new_product,
            self.company_data["default_warehouse"].lot_stock_id,
            2,
            lot_id=lot,
        )
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.new_product.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        sale_order.picking_ids.button_validate()
        self.assertEqual(sale_order.picking_ids.state, "done")
        self.assertEqual(lot.with_user(user).sale_order_count, 0)
        sale_order_2 = (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.new_product.id,
                                "product_qty": 1.0,
                            }
                        )
                    ],
                }
            )
        )
        sale_order_2.action_confirm()
        sale_order_2.picking_ids.button_validate()
        self.assertEqual(sale_order_2.picking_ids.state, "done")
        lot.invalidate_recordset()
        self.assertEqual(lot.with_user(user).sale_order_count, 1)
        self.assertEqual(lot.with_user(user).sale_order_ids, sale_order_2)

    def test_invoice_zero_quantity_after_delivery_fifo(self):
        self.env.company.write(
            {
                "cost_method": "fifo",
                "inventory_valuation": "real_time",
            }
        )

        sale = self._get_new_sale_order(product=self.new_product, amount=1)
        sale.action_confirm()

        picking = sale.picking_ids
        self.assertEqual(len(picking), 1)

        picking.move_ids.quantity = 1
        picking.button_validate()

        invoice = sale._create_invoices()
        invoice.invoice_line_ids.quantity = 0
        invoice.action_post()

        self.assertEqual(invoice.state, "posted")

    def test_decrease_qty_logs_one_exception_per_line(self):
        so = self._get_new_sale_order(amount=12.0)
        so.action_confirm()

        delivery = so.picking_ids
        delivery.move_ids.write({"quantity": 12, "picked": True})
        delivery.button_validate()

        return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_id=delivery.id, active_model="stock.picking"
            )
        )
        with return_picking_form.product_return_moves.edit(0) as line:
            line.quantity = 2
        return_wizard = return_picking_form.save()
        return_wizard.product_return_moves.to_refund = True
        return_picking = self.env["stock.picking"].browse(
            return_wizard.action_create_returns()["res_id"]
        )
        return_picking.move_ids.write({"quantity": 2, "picked": True})
        return_picking.button_validate()

        sol = so.line_ids
        self.assertEqual(len(sol.move_ids), 2)

        documents = (
            self.env["mixin.stock.activity"]
            .sudo()
            ._get_log_activity_documents({sol: (10.0, 12.0)}, "move_ids", "UP")
        )
        self.assertEqual(
            sum(len(rendering_context[0]) for rendering_context in documents.values()),
            2,
        )

        activities_before = self.env["mail.activity"].search([])
        so._log_decrease_ordered_quantity(documents)
        activity = self.env["mail.activity"].search([]) - activities_before

        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.note.count("ordered instead of"), 1)
        self.assertEqual(activity.note.count("<li"), 1)
