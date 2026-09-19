from unittest import skip

from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


@tagged("post_install", "-at_install")
class TestStockValuation(ValuationReconciliationTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.stock_location = cls.company_data["default_warehouse"].lot_stock_id
        cls.partner_id = cls.env["res.partner"].create({"name": "My Test Partner"})
        cls.product1 = cls.env["product.product"].create(
            {
                "name": "Large Desk",
                "is_storable": True,
                "categ_id": cls.stock_account_product_categ.id,
                "taxes_id": [(6, 0, [])],
            }
        )

    def _dropship_product1(self):
        dropshipping_route = self.quick_ref("stock_dropshipping.route_drop_shipping")
        self.product1.write({"route_ids": [(6, 0, [dropshipping_route.id])]})

        vendor1 = self.env["res.partner"].create({"name": "vendor1"})
        self.product1.write(
            {
                "seller_ids": [
                    Command.create(
                        {
                            "partner_id": vendor1.id,
                            "price": 8,
                        }
                    )
                ]
            }
        )

        self.sale_order1 = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.partner.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.product1.id,
                                "price_unit": 12,
                                "tax_ids": [Command.set([])],
                            }
                        )
                    ],
                    "picking_policy": "direct",
                }
            )
        )
        self.sale_order1.action_confirm()

        self.purchase_order1 = self.env["purchase.order"].search(
            [("reference_ids", "=", self.sale_order1.reference_ids.id)]
        )
        self.purchase_order1.action_confirm()

        self.assertEqual(len(self.sale_order1.picking_ids), 1)
        self.sale_order1.picking_ids.button_validate()
        self.assertEqual(self.sale_order1.picking_ids.state, "done")

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        move_form.partner_id = vendor1
        move_form.purchase_vendor_bill_id = self.env["purchase.bill.match"].browse(
            -self.purchase_order1.id
        )
        move_form.invoice_date = move_form.date
        for i in range(len(self.purchase_order1.line_ids)):
            with move_form.invoice_line_ids.edit(i) as line_form:
                line_form.tax_ids.clear()
        self.vendor_bill1 = move_form.save()
        self.vendor_bill1.action_post()

        self.customer_invoice1 = self.sale_order1._create_invoices()
        self.customer_invoice1.action_post()

        all_amls = self.vendor_bill1.line_ids + self.customer_invoice1.line_ids
        if self.sale_order1.picking_ids.move_ids.account_move_id:
            all_amls |= self.sale_order1.picking_ids.move_ids.account_move_id.line_ids
        return all_amls

    def _check_results(self, expected_aml, expected_aml_count, all_amls):
        result_aml = {}
        for aml in all_amls:
            account_id = aml.account_id.id
            if result_aml.get(account_id):
                debit = result_aml[account_id][0]
                credit = result_aml[account_id][1]
                result_aml[account_id] = (debit + aml.debit, credit + aml.credit)
            else:
                result_aml[account_id] = (aml.debit, aml.credit)

        self.assertEqual(len(all_amls), expected_aml_count)

        for k, v in expected_aml.items():
            self.assertEqual(result_aml[k], v)

    def test_dropship_standard_perpetual_continental_ordered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.categ_id.property_cost_method = "standard"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "ordered"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (8.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_standard_perpetual_continental_delivered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.categ_id.property_cost_method = "standard"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "transferred"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (8.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_fifo_perpetual_continental_ordered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = False
        self.product1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "ordered"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (8.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    def test_dropship_fifo_perpetual_continental_delivered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = False

        self.product1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "transferred"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (8.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
        }

        self._check_results(expected_aml, 4, all_amls)

    @skip(
        "Asserts on `default_account_stock_in`; this fork replaced the stock "
        "input/output accounts with a single Stock Variation account, so the "
        "expected entries have to be rewritten."
    )
    def test_dropship_standard_perpetual_anglosaxon_ordered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = "standard"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "ordered"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (10.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
            self.company_data["default_account_stock_in"].id: (8.0, 10.0),
            self.company_data["default_account_stock_out"].id: (10.0, 10.0),
        }

        self._check_results(expected_aml, 10, all_amls)

    @skip(
        "Asserts on `default_account_stock_in`; this fork replaced the stock "
        "input/output accounts with a single Stock Variation account, so the "
        "expected entries have to be rewritten."
    )
    def test_dropship_standard_perpetual_anglosaxon_delivered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = "standard"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "transferred"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (10.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
            self.company_data["default_account_stock_in"].id: (8.0, 10.0),
            self.company_data["default_account_stock_out"].id: (10.0, 10.0),
        }

        self._check_results(expected_aml, 10, all_amls)

    @skip(
        "Asserts on `default_account_stock_in`; this fork replaced the stock "
        "input/output accounts with a single Stock Variation account, so the "
        "expected entries have to be rewritten."
    )
    def test_dropship_fifo_perpetual_anglosaxon_ordered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "ordered"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (8.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
            self.company_data["default_account_stock_in"].id: (8.0, 8.0),
            self.company_data["default_account_stock_out"].id: (8.0, 8.0),
        }

        self._check_results(expected_aml, 10, all_amls)

    @skip(
        "Asserts on `default_account_stock_in`; this fork replaced the stock "
        "input/output accounts with a single Stock Variation account, so the "
        "expected entries have to be rewritten."
    )
    def test_dropship_fifo_perpetual_anglosaxon_delivered(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "transferred"

        all_amls = self._dropship_product1()

        expected_aml = {
            self.company_data["default_account_payable"].id: (0.0, 8.0),
            self.company_data["default_account_expense"].id: (8.0, 0.0),
            self.company_data["default_account_receivable"].id: (12.0, 0.0),
            self.company_data["default_account_revenue"].id: (0.0, 12.0),
            self.company_data["default_account_stock_in"].id: (8.0, 8.0),
            self.company_data["default_account_stock_out"].id: (8.0, 8.0),
        }
        self._check_results(expected_aml, 10, all_amls)

    @skip(
        "Asserts on `default_account_stock_in`; this fork replaced the stock "
        "input/output accounts with a single Stock Variation account, so the "
        "expected entries have to be rewritten."
    )
    def test_dropship_standard_perpetual_anglosaxon_ordered_return(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = "standard"
        self.product1.product_tmpl_id.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "ordered"

        all_amls = self._dropship_product1()

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=self.sale_order1.picking_ids.ids,
                active_id=self.sale_order1.picking_ids.ids[0],
                active_model="stock.picking",
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env["stock.picking"].browse(
            stock_return_picking_action["res_id"]
        )
        return_pick.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick.move_ids[0].picked = True
        return_pick._action_done()
        self.assertEqual(return_pick.move_ids._is_dropshipped_returned(), True)

        all_amls_return = self.vendor_bill1.line_ids + self.customer_invoice1.line_ids
        if self.sale_order1.picking_ids.mapped("move_ids.account_move_id"):
            all_amls_return |= self.sale_order1.picking_ids.mapped(
                "move_ids.account_move_id.line_ids"
            )

        expected_aml = {
            self.company_data["default_account_stock_in"].id: (10.0, 0.0),
            self.company_data["default_account_stock_out"].id: (0.0, 10.0),
        }

        self._check_results(expected_aml, 4, all_amls_return - all_amls)

    @skip(
        "Reads `stock.valuation.layer`, removed in this fork; value now lives on "
        "`stock.move.value`. The assertions have to be re-derived, not renamed."
    )
    def test_dropship_fifo_return(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "ordered"

        self._dropship_product1()
        self.assertTrue(
            8
            in self.purchase_order1.picking_ids.move_ids.stock_valuation_layer_ids.mapped(
                "value"
            )
        )
        self.assertTrue(
            -8
            in self.purchase_order1.picking_ids.move_ids.stock_valuation_layer_ids.mapped(
                "value"
            )
        )

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=self.sale_order1.picking_ids.ids,
                active_id=self.sale_order1.picking_ids.ids[0],
                active_model="stock.picking",
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env["stock.picking"].browse(
            stock_return_picking_action["res_id"]
        )
        return_pick.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick.move_ids[0].picked = True
        return_pick._action_done()

        self.assertTrue(
            8 in return_pick.move_ids.stock_valuation_layer_ids.mapped("value")
        )
        self.assertTrue(
            -8 in return_pick.move_ids.stock_valuation_layer_ids.mapped("value")
        )

        stock_return_picking_form_2 = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=return_pick.ids,
                active_id=return_pick.ids[0],
                active_model="stock.picking",
            )
        )
        stock_return_picking_2 = stock_return_picking_form_2.save()
        stock_return_picking_2.product_return_moves.quantity = 1.0
        stock_return_picking_action_2 = stock_return_picking_2.action_create_returns()
        return_pick_2 = self.env["stock.picking"].browse(
            stock_return_picking_action_2["res_id"]
        )
        return_pick_2.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick_2.move_ids[0].picked = True
        return_pick_2._action_done()

        self.assertTrue(
            8 in return_pick_2.move_ids.stock_valuation_layer_ids.mapped("value")
        )
        self.assertTrue(
            -8 in return_pick_2.move_ids.stock_valuation_layer_ids.mapped("value")
        )

    @skip(
        "Reads `stock.valuation.layer`, removed in this fork; value now lives on "
        "`stock.move.value`. The assertions have to be re-derived, not renamed."
    )
    def test_dropship_cogs_multiple_invoices(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = "fifo"
        self.product1.product_tmpl_id.categ_id.property_valuation = "real_time"
        self.product1.product_tmpl_id.invoice_policy = "ordered"
        account_output = self.product1.product_tmpl_id.categ_id.property_stock_account_output_categ_id

        self._dropship_product1()

        dropship1_layers = (
            self.purchase_order1.line_ids.move_ids.stock_valuation_layer_ids
        )
        self.assertEqual(len(dropship1_layers), 2)
        self.assertEqual(dropship1_layers[0].value, 8)
        dropship1_cogs_line = self.customer_invoice1.line_ids.filtered(
            lambda aml: aml.account_id.id == account_output.id
        )
        self.assertEqual(dropship1_cogs_line.balance, -8)

        self.sale_order1.line_ids.product_qty = 2
        self.purchase_order2 = self.env["purchase.order"].search(
            [
                ("reference_ids", "=", self.sale_order1.reference_ids.id),
                ("state", "=", "draft"),
            ]
        )
        self.purchase_order2.line_ids.price_unit = 16
        self.purchase_order2.action_confirm()

        dropship2 = self.sale_order1.picking_ids.filtered(
            lambda pck: pck.state != "done"
        )
        dropship2.move_ids.quantity = 1
        dropship2.move_ids.picked = True
        dropship2._action_done()
        self.assertEqual(dropship2.state, "done")

        customer_invoice2 = self.sale_order1._create_invoices()
        customer_invoice2.action_post()

        dropship2_layers = dropship2.move_ids.stock_valuation_layer_ids
        self.assertEqual(len(dropship2_layers), 2)
        self.assertEqual(dropship2_layers[0].value, 16)
        dropship2_cogs_line = customer_invoice2.line_ids.filtered(
            lambda aml: aml.account_id.id == account_output.id
        )
        self.assertEqual(dropship2_cogs_line.balance, -16)

        self.sale_order1.line_ids.product_qty = 3
        self.purchase_order3 = self.env["purchase.order"].search(
            [
                ("reference_ids", "=", self.sale_order1.reference_ids.id),
                ("state", "=", "draft"),
            ]
        )
        self.purchase_order3.line_ids.price_unit = 24
        self.purchase_order3.action_confirm()

        dropship3 = self.sale_order1.picking_ids.filtered(
            lambda pck: pck.state != "done"
        )
        dropship3.move_ids.quantity = 1
        dropship3.move_ids.picked = True
        dropship3._action_done()
        self.assertEqual(dropship3.state, "done")

        ret_model = self.env["stock.return.picking"].with_context(
            active_id=dropship3.id, active_model="stock.picking"
        )
        pck_return_wiz = Form(ret_model).save()
        pck_return_wiz.product_return_moves.quantity = 1.0
        pck_return_action = pck_return_wiz.action_create_returns()
        dropship3_return = self.env["stock.picking"].browse(pck_return_action["res_id"])
        dropship3_return.move_ids.quantity = 1
        dropship3_return.move_ids.picked = True
        dropship3_return._action_done()

        ret_model = ret_model.with_context(active_id=dropship3_return.id)
        pck_return_wiz = Form(ret_model).save()
        pck_return_wiz.product_return_moves.quantity = 1.0
        pck_return_action = pck_return_wiz.action_create_returns()
        dropship3_return_return = self.env["stock.picking"].browse(
            pck_return_action["res_id"]
        )
        dropship3_return_return.move_ids.quantity = 1
        dropship3_return_return.move_ids.picked = True
        dropship3_return_return._action_done()

        customer_invoice3 = self.sale_order1._create_invoices()
        customer_invoice3.action_post()

        dropship3_pcks = dropship3 | dropship3_return | dropship3_return_return
        dropship3_layers = dropship3_pcks.move_ids.stock_valuation_layer_ids
        self.assertEqual(len(dropship3_layers), 6)
        self.assertEqual(dropship3_layers[0].value, 24)
        dropship3_cogs_line = customer_invoice3.line_ids.filtered(
            lambda aml: aml.account_id.id == account_output.id
        )
        self.assertEqual(dropship3_cogs_line.balance, -24)

    @skip(
        "Reads `stock.valuation.layer`, removed in this fork; value now lives on "
        "`stock.move.value`. The assertions have to be re-derived, not renamed."
    )
    def test_dropship_standard_perpetual_anglosaxon_ordered_return_internal_aml(self):
        self.env.user.group_ids |= self.env.ref("stock.group_stock_multi_locations")
        self.env.company.account_config_id.anglo_saxon_accounting = True

        product = self.env["product.product"].create(
            {
                "name": "product",
                "type": "consu",
                "is_storable": True,
                "standard_price": 10,
                "route_ids": [(6, 0, [self.dropship_route.id])],
                "seller_ids": [(0, 0, {"partner_id": self.supplier.id})],
            }
        )
        product.product_tmpl_id.categ_id = self.env.ref(
            "product.product_category_goods"
        )
        self._setup_category_stock_journals()
        product.product_tmpl_id.categ_id.property_cost_method = "standard"
        product.product_tmpl_id.categ_id.property_valuation = "real_time"
        product.product_tmpl_id.invoice_policy = "ordered"
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "picking_policy": "direct",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 1,
                        },
                    ),
                ],
            }
        )
        sale_order.action_confirm()
        self.env["purchase.order"].search([], order="id desc", limit=1).action_confirm()
        self.assertEqual(sale_order.line_ids.qty_transferred, 0.0)
        picking = sale_order.picking_ids
        picking.button_validate()

        stock_return_picking_form = Form(
            self.env["stock.return.picking"].with_context(
                active_ids=sale_order.picking_ids.ids,
                active_id=sale_order.picking_ids.ids[0],
                active_model="stock.picking",
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.write({"quantity": 1.0})
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env["stock.picking"].browse(
            stock_return_picking_action["res_id"]
        )
        return_pick.location_dest_id = self.warehouse_id.lot_stock_id
        return_pick.move_ids[0].move_line_ids[0].quantity = 1.0
        return_pick.move_ids[0].picked = True
        return_pick._action_done()
        self.assertEqual(return_pick.move_ids._is_dropshipped_returned(), True)

        stock_valuation_account = (
            product.product_tmpl_id.categ_id.property_stock_valuation_account_id
        )
        stock_interim_delivered = (
            product.product_tmpl_id.categ_id.property_stock_account_output_categ_id
        )
        stock_interim_received = (
            product.product_tmpl_id.categ_id.property_stock_account_input_categ_id
        )
        original_move_in_svl_amls = picking.move_ids.stock_valuation_layer_ids.filtered(
            lambda svl: svl.value >= 0
        ).account_move_id.line_ids.sorted("debit")
        original_move_out_svl_amls = (
            picking.move_ids.stock_valuation_layer_ids.filtered(
                lambda svl: svl.value < 0
            ).account_move_id.line_ids.sorted("debit")
        )
        return_move_amls = return_pick.move_ids.stock_valuation_layer_ids.account_move_id.line_ids.sorted(
            "debit"
        )

        self.assertRecordValues(
            original_move_in_svl_amls,
            [
                {"credit": 10, "debit": 0, "account_id": stock_interim_received.id},
                {"credit": 0, "debit": 10, "account_id": stock_valuation_account.id},
            ],
        )
        self.assertRecordValues(
            original_move_out_svl_amls,
            [
                {"credit": 10, "debit": 0, "account_id": stock_valuation_account.id},
                {"credit": 0, "debit": 10, "account_id": stock_interim_delivered.id},
            ],
        )
        self.assertRecordValues(
            return_move_amls,
            [
                {"credit": 10, "debit": 0, "account_id": stock_interim_delivered.id},
                {"credit": 0, "debit": 10, "account_id": stock_valuation_account.id},
            ],
        )
