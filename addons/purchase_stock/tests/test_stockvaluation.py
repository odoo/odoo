from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import Form, tagged
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from .common import PurchaseTestCommon


@tagged("post_install", "-at_install")
class TestStockValuationWithCOA(PurchaseTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1, cls.product2 = cls.env["product.product"].create(
            [
                {
                    "name": "product1",
                    "is_storable": True,
                    "categ_id": cls.category_fifo_auto.id,
                },
                {
                    "name": "product2",
                    "is_storable": True,
                    "categ_id": cls.category_fifo_auto.id,
                },
            ]
        )

    def test_anglosaxon_valuation_price_total_diff_discount(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 110.0
        order = po_form.save()
        order.action_confirm()

        receipt = order.picking_ids[0]
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        invoice = order.create_invoice()
        invoice.invoice_date = invoice.date
        invoice.invoice_line_ids.price_unit = 100.0
        invoice.invoice_line_ids.discount = 10.0
        invoice.action_post()

        self.assertEqual(receipt.move_ids.value, 90.0)
        self.assertEqual(self.product1.total_value, 90.0)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 90.0
        )

    def test_anglosaxon_valuation_discount(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 100.0
        order = po_form.save()
        order.action_confirm()

        receipt = order.picking_ids[0]
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        invoice = order.create_invoice()
        invoice.invoice_date = invoice.date
        invoice.invoice_line_ids.tax_ids = [Command.clear()]
        invoice.invoice_line_ids.discount = 10.0
        invoice.action_post()

        self.assertEqual(receipt.move_ids.value, 90.0)
        self.assertEqual(self.product1.total_value, 90.0)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 90.0
        )

    def test_anglosaxon_valuation_price_unit_diff_discount(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 90.0
        order = po_form.save()
        order.action_confirm()

        receipt = order.picking_ids[0]
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        invoice = order.create_invoice()
        invoice.invoice_date = invoice.date
        invoice.invoice_line_ids.price_unit = 100.0
        invoice.invoice_line_ids.discount = 10.0
        invoice.action_post()

        self.assertEqual(receipt.move_ids.value, 90.0)
        self.assertEqual(self.product1.total_value, 90.0)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 90.0
        )

    def test_pdiff_and_aml_labels(self):
        self._use_price_diff()
        self.product1.type = "consu"
        self.product1.categ_id.property_cost_method = "fifo"
        self.product1.categ_id.property_valuation = "real_time"

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product2
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        po = po_form.save()
        po.action_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.move_line_ids.quantity = 1
        receipt01.button_validate()

        bill = po.create_invoice()
        bill.invoice_date = fields.Date.today()
        label01, label02 = bill.invoice_line_ids.mapped("name")
        self.assertTrue(label01)
        self.assertTrue(label02)

        bill.invoice_line_ids.price_unit = 11.0
        bill.action_post()
        self.assertEqual(bill.invoice_line_ids.mapped("name"), [label01, label02])

    def test_pdiff_lot_valuation(self):
        product = self.env["product.product"].create(
            {
                "name": "product_lot",
                "is_storable": True,
                "tracking": "serial",
                "categ_id": self.category_avco_auto.id,
                "lot_valuated": True,
            }
        )

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 3.0,
                            "product_uom_id": product.uom_id.id,
                            "price_unit": 100.0,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()

        receipt = po.picking_ids
        for i, line in enumerate(receipt.move_ids.move_line_ids, start=1):
            line.write({"lot_name": "lot_%s" % i, "quantity": 1})
        receipt.move_ids.picked = True
        receipt.button_validate()

        lots = receipt.move_line_ids.lot_id
        self.assertEqual(receipt.state, "done")
        self.assertEqual(lots.mapped("standard_price"), [100.0, 100.0, 100.0])
        self.assertEqual(product.total_value, 300.0)

        bill = po.create_invoice()
        bill.invoice_date = fields.Date.today()
        bill.invoice_line_ids.price_unit = 150.0
        bill.action_post()

        self.assertEqual(lots.mapped("standard_price"), [150.0, 150.0, 150.0])
        self.assertRecordValues(
            product,
            [
                {
                    "standard_price": 150.0,
                    "total_value": 450.0,
                }
            ],
        )
        self.assertEqual(receipt.move_ids.value, 450.0)

    def test_purchase_with_backorders_and_return_and_price_changes(self):
        self.product1.categ_id = self.category_avco_auto
        self.product1.bill_policy = "transferred"

        po = self._create_purchase(self.product1, quantity=100, price_unit=10.0)

        receipt01 = self._receive(po, quantity=30)
        self.assertEqual(receipt01.value, 300.0)
        self._create_bill(purchase_order=po, price_unit=12)
        self.assertEqual(receipt01.value, 360.0)

        receipt02 = self._receive(po, quantity=30)
        self.assertEqual(receipt02.value, 300.0)
        self._create_bill(purchase_order=po, price_unit=13)
        self.assertEqual(receipt01.value, 375.0)
        self.assertEqual(receipt02.value, 375.0)

        self._make_return(receipt02, 10)

        receipt03 = self._receive(po, quantity=30)
        self.assertEqual(receipt03.value, 300.0)
        self.assertRecordValues(
            self.product1,
            [
                {
                    "total_value": 925.0,
                    "standard_price": 11.5625,
                }
            ],
        )

    def test_invoice_on_ordered_qty_with_backorder_and_different_currency_automated(
        self,
    ):
        usd_currency = self.env.ref("base.USD")
        self.env.company.currency_id = usd_currency.id
        self.product1.categ_id.property_cost_method = "fifo"
        self.product1.categ_id.property_valuation = "real_time"
        self.product1.bill_policy = "ordered"

        price_unit_EUR = 100
        price_unit_USD = self.env.ref("base.EUR")._convert(
            price_unit_EUR,
            usd_currency,
            self.env.company,
            fields.Date.today(),
            round=False,
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": self.env.ref("base.EUR").id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product1.name,
                            "product_id": self.product1.id,
                            "product_qty": 12.0,
                            "product_uom_id": self.product1.uom_id.id,
                            "price_unit": 100.0,
                            "date_commitment": datetime.today().strftime(
                                DEFAULT_SERVER_DATETIME_FORMAT
                            ),
                        },
                    ),
                ],
            }
        )
        po.action_confirm()
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = 10
        move.picked = True
        res_dict = picking.button_validate()
        self.assertEqual(res_dict["res_model"], "stock.backorder.confirmation")
        wizard = (
            self.env[(res_dict.get("res_model"))]
            .browse(res_dict.get("res_id"))
            .with_context(res_dict["context"])
        )
        wizard.process()
        self.assertAlmostEqual(move.value, 10 * price_unit_USD, places=2)

        po.create_invoice()

        picking2 = po.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        move2.quantity = 2
        move2.picked = True
        picking2.button_validate()
        self.assertAlmostEqual(move2.value, 2 * price_unit_USD, places=2)

    def test_invoice_on_ordered_qty_with_backorder_and_different_currency_manual(self):
        usd_currency = self.env.ref("base.USD")
        self.env.company.currency_id = usd_currency.id
        self.product1.categ_id = self.category_fifo
        self.product1.bill_policy = "ordered"

        price_unit_EUR = 100
        price_unit_USD = self.env.ref("base.EUR")._convert(
            price_unit_EUR,
            usd_currency,
            self.env.company,
            fields.Date.today(),
            round=False,
        )
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": self.env.ref("base.EUR").id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product1.name,
                            "product_id": self.product1.id,
                            "product_qty": 12.0,
                            "product_uom_id": self.product1.uom_id.id,
                            "price_unit": 100.0,
                            "date_commitment": datetime.today().strftime(
                                DEFAULT_SERVER_DATETIME_FORMAT
                            ),
                        },
                    ),
                ],
            }
        )
        po.action_confirm()
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = 10
        move.picked = True
        res_dict = picking.button_validate()
        self.assertEqual(res_dict["res_model"], "stock.backorder.confirmation")
        wizard = (
            self.env[(res_dict.get("res_model"))]
            .browse(res_dict.get("res_id"))
            .with_context(res_dict["context"])
        )
        wizard.process()
        self.assertAlmostEqual(move.value, 10 * price_unit_USD, places=2)

        po.create_invoice()

        picking2 = po.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        move2.quantity = 2
        move2.picked = True
        picking2.button_validate()
        self.assertAlmostEqual(move2.value, 2 * price_unit_USD, places=2)

    def test_bill_with_zero_qty(self):
        product1 = self.product1
        product2 = self.product2

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product2
            po_line.product_qty = 1
            po_line.price_unit = 20.0
        po = po_form.save()
        po.action_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1
        receipt.button_validate()

        bill01 = po.create_invoice()
        bill01.invoice_date = fields.Date.today()
        bill01.invoice_line_ids.filtered(
            lambda l: l.product_id == product2
        ).quantity = 0
        bill01.action_post()

        self.assertEqual(bill01.state, "posted")
        self.assertRecordValues(
            po.line_ids,
            [
                {"product_id": product1.id, "qty_invoiced": 1.0},
                {"product_id": product2.id, "qty_invoiced": 0.0},
            ],
        )

        bill02 = self._create_bill(purchase_order=po)
        self.assertEqual(bill02.state, "posted")
        self.assertRecordValues(
            po.line_ids,
            [
                {"product_id": product1.id, "qty_invoiced": 1.0},
                {"product_id": product2.id, "qty_invoiced": 1.0},
            ],
        )

        self.assertRecordValues(
            receipt.move_ids,
            [
                {"product_id": product1.id, "value": 10.0},
                {"product_id": product2.id, "value": 20.0},
            ],
        )

    def _test_fifo_and_returns_common(self):
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        po = po_form.save()
        po.action_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1
        receipt.button_validate()

        self._create_bill(purchase_order=po)

    def test_fifo_return_and_receive_all_on_backorder(self):
        self._test_fifo_and_returns_common()

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 4
            po_line.price_unit = 25.0
        po = po_form.save()
        po.action_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        action = receipt01.button_validate()
        backorder_wizard = Form(
            self.env["stock.backorder.confirmation"].with_context(action["context"])
        ).save()
        backorder_wizard.process()

        self._make_return(receipt01.move_ids, receipt01.move_ids.quantity)

        receipt02 = receipt01.backorder_ids
        receipt02.move_ids.quantity = 4
        receipt02.button_validate()

        self._create_bill(purchase_order=po)

        self.assertRecordValues(
            self.product1,
            [
                {
                    "qty_available": 5,
                    "total_value": 125.0,
                    "standard_price": 25.0,
                }
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 110.0
        )

    def test_fifo_return_twice_and_bill(self):
        self._test_fifo_and_returns_common()

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 25.0
        po = po_form.save()
        po.action_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        receipt01.button_validate()

        receipt01_return = self._make_return(
            receipt01.move_ids, receipt01.move_ids.quantity
        )
        self._make_return(receipt01_return, receipt01_return.quantity)
        self._create_bill(purchase_order=po)

        self.assertRecordValues(
            self.product1,
            [
                {
                    "qty_available": 2,
                    "total_value": 50.0,
                    "standard_price": 25.0,
                }
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 35.0
        )

    def test_fifo_bill_return_refund(self):
        self._test_fifo_and_returns_common()

        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 25.0
        po = po_form.save()
        po.action_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        receipt01.button_validate()

        self._create_bill(purchase_order=po)
        self._make_return(receipt01.move_ids, receipt01.move_ids.quantity)
        self._create_bill(purchase_order=po)

        self.assertRecordValues(
            self.product1,
            [
                {
                    "qty_available": 1,
                    "total_value": 25.0,
                    "standard_price": 25.0,
                }
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 10.0
        )

    def test_incoming_with_negative_qty(self):
        product1 = self.product1
        shipping_partner = self.env["res.partner"].create(
            {
                "name": "Shipping Partner",
                "street": "234 W 18th Ave",
                "city": "Columbus",
                "state_id": self.env.ref("base.state_us_30").id,
                "country_id": self.env.ref("base.us").id,
                "zip": "43210",
            }
        )
        po_form = Form(self.env["purchase.order"])
        po_form.partner_id = self.vendor
        with po_form.line_ids.new() as po_line:
            po_line.product_id = product1
            po_line.product_qty = -2
            po_line.price_unit = 10.0
        po = po_form.save()
        po.action_confirm()
        delivery = po.picking_ids
        delivery.partner_id = shipping_partner
        move_line_vals = delivery.move_ids._prepare_move_line_vals()
        move_line = self.env["stock.move.line"].create(move_line_vals)
        move_line.quantity = 2.0
        delivery.button_validate()
        self.assertEqual(delivery.state, "done")

    def test_return_a_return_avco_prod_with_exchange_diff(self):
        self.product1.categ_id.property_cost_method = "average"
        avco_prod = self.product1
        (self.env.ref("base.EUR") + self.env.ref("base.CHF")).active = True
        euro_id = self.env.ref("base.EUR").id
        franc_id = self.env.ref("base.CHF").id
        self.env["res.currency.rate"].create(
            [
                {"currency_id": euro_id, "rate": 0.95},
                {"currency_id": franc_id, "rate": 0.8},
            ]
        )
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": euro_id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": avco_prod.id,
                            "product_qty": 5,
                            "price_unit": 10,
                        }
                    )
                ],
            }
        )
        purchase_order.action_confirm()
        receipt1 = purchase_order.picking_ids
        receipt1.button_validate()

        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.owner.id,
                "currency_id": franc_id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": avco_prod.id,
                            "product_qty": 5,
                        }
                    )
                ],
            }
        )
        purchase_order.action_confirm()
        receipt2 = purchase_order.picking_ids
        receipt2.button_validate()

        receipt2_return1 = self._make_return(
            receipt2.move_ids, receipt2.move_ids.quantity
        )
        self._make_return(receipt2_return1, receipt2_return1.quantity)
        pre_bill_cost = avco_prod.standard_price
        purchase_order.create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        self.assertEqual(avco_prod.standard_price, pre_bill_cost)

    def test_manual_non_standard_cost_bill_post(self):
        self.env.company.account_config_id.anglo_saxon_accounting = False
        self.product1.categ_id = self.category_avco
        product = self.product1
        tax = self.company.account_config_id.account_purchase_tax_id
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 10,
                            "price_unit": 100,
                            "tax_ids": [Command.set(tax.ids)],
                        }
                    )
                ],
            }
        )
        purchase_order.action_confirm()
        purchase_order.picking_ids.button_validate()
        with Form(self.env["stock.scrap"]) as scrap_form:
            scrap_form.product_id = product
            scrap_form.scrap_qty = 10
            scrap = scrap_form.save()
        scrap.action_validate()
        purchase_order.create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_line_ids.price_unit = 120
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        tax_account = tax.invoice_repartition_line_ids.account_id
        self.assertRecordValues(
            bill.line_ids,
            [
                {"account_id": self.account_expense.id, "debit": 1200.0, "credit": 0.0},
                {"account_id": tax_account.id, "debit": 180.0, "credit": 0.0},
                {"account_id": self.account_payable.id, "debit": 0.0, "credit": 1380.0},
            ],
        )

    def test_100_percent_discount(self):
        product = self.product1
        product.categ_id = self.category_avco_auto
        purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 2,
                            "discount": 100,
                        }
                    )
                ],
            }
        )
        purchase_order.action_confirm()
        receipt = purchase_order.picking_ids
        receipt.button_validate()
        purchase_order.create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        move = receipt.move_ids
        self.assertEqual(move.value, 0)
        self.assertEqual(move.quantity, 2)

    def test_standard_valuation_return_credit_note(self):
        self.env.company.account_config_id.anglo_saxon_accounting = True
        self.product1.categ_id = self.category_standard_auto
        with freeze_time("2020-01-01"):
            self.product1.standard_price = 100

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": self.product1.name,
                            "product_id": self.product1.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                            "date_commitment": datetime.today().strftime(
                                DEFAULT_SERVER_DATETIME_FORMAT
                            ),
                        }
                    ),
                ],
            }
        )
        po.action_confirm()
        receipt_po = po.picking_ids[0]
        receipt_po.button_validate()

        self._create_bill(purchase_order=po)
        self._make_return(receipt_po.move_ids, receipt_po.move_ids.quantity)
        self._create_bill(purchase_order=po)

        self.assertRecordValues(
            self.product1,
            [
                {
                    "qty_available": 0,
                    "total_value": 0.0,
                }
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 0.0
        )

    def test_move_value_invoice_manual_rate(self):
        grp_currencies = self.env.ref("base.group_multi_currency")
        self.env.user.write({"group_ids": [(4, grp_currencies.id)]})
        product = self.env["product.product"].create(
            {
                "name": "product_a",
                "standard_price": 100.0,
            }
        )
        partner = self.env["res.partner"].create({"name": "testpartner"})
        eur_currency = self.env.ref("base.EUR")
        eur_currency.active = True
        eur_currency.write(
            {
                "rate_ids": [
                    Command.create(
                        {
                            "rate": 2,
                        }
                    )
                ]
            }
        )
        product.product_tmpl_id.categ_id.property_cost_method = "average"
        product.product_tmpl_id.categ_id.property_valuation = "real_time"

        po = self.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "currency_id": eur_currency.id,
                "line_ids": [
                    Command.create(
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                        }
                    ),
                ],
            }
        )
        po.action_confirm()
        receipt_po = po.picking_ids[0]
        receipt_po.button_validate()
        self.assertEqual(po.picking_ids.move_ids.value, 50)

        bill = po.create_invoice()
        bill.invoice_date = fields.Date.today()
        with Form(bill) as move_form:
            move_form.invoice_currency_rate = 4
        bill.action_post()
        self.assertEqual(po.picking_ids.move_ids.value, 25)

    def test_price_diff_with_partial_bills_and_delivered_qties(self):
        product = self.product1
        po = self._create_purchase(product, quantity=10, price_unit=50.0)
        receipt = self._receive(po)
        self.assertEqual(receipt.value, 500.0)

        self._make_out_move(product, 5)
        self.assertEqual(product.total_value, 250.0)

        self._create_bill(purchase_order=po, quantity=5, price_unit=60.0)
        self.assertEqual(product.total_value, 275.0)
        self._create_bill(purchase_order=po, quantity=5, price_unit=60.0)

        self.assertEqual(receipt.value, 600.0)
        self.assertRecordValues(
            product,
            [
                {
                    "qty_available": 5.0,
                    "total_value": 300.0,
                    "standard_price": 60.0,
                }
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 600.0
        )

    def test_pdiff_and_credit_notes(self):
        product = self.product1
        po = self._create_purchase(product, quantity=12, price_unit=10.0)
        self._receive(po, quantity=4)
        self._receive(po, quantity=3)
        self._receive(po, quantity=5)
        self.assertEqual(product.total_value, 120.0)

        bill01 = self._create_bill(purchase_order=po, quantity=3, price_unit=12.0)
        bill02 = self._create_bill(purchase_order=po, quantity=2, price_unit=11.0)
        self._create_bill(purchase_order=po, quantity=1, price_unit=15.0)
        bill04 = self._create_bill(purchase_order=po, quantity=4, price_unit=9.0)
        bill05 = self._create_bill(purchase_order=po, quantity=2, price_unit=10.0)
        self.assertEqual(product.total_value, 129.0)

        self._refund(bill01, 1.0)
        self._refund(bill02)
        self._refund(bill04, 2.0)
        self._refund(bill05, 1.0)
        self.assertEqual(product.total_value, 127.0)

        self._create_bill(purchase_order=po, price_unit=18.0)

        self.assertRecordValues(
            product,
            [
                {
                    "qty_available": 12.0,
                    "total_value": 175.0,
                }
            ],
        )
        self.assertAlmostEqual(product.standard_price, 175 / 12)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 175.0
        )

    def test_pdiff_with_credit_notes_and_delivered_qties(self):
        product = self.product1
        po = self._create_purchase(product, quantity=10, price_unit=10.0)
        self._receive(po, quantity=10)
        self.assertEqual(product.total_value, 100.0)

        bill01 = self._create_bill(purchase_order=po, price_unit=12.0)
        self.assertRecordValues(
            product,
            [
                {
                    "total_value": 120.0,
                    "standard_price": 12.0,
                }
            ],
        )

        self._make_out_move(product, 3)
        self.assertRecordValues(
            product,
            [
                {
                    "qty_available": 7.0,
                    "total_value": 84.0,
                }
            ],
        )

        self._refund(bill01)
        self.assertRecordValues(
            product,
            [
                {
                    "total_value": 70.0,
                    "standard_price": 10.0,
                }
            ],
        )

        bill02 = self._create_bill(purchase_order=po, price_unit=9.0)
        self.assertRecordValues(
            product,
            [
                {
                    "total_value": 63.0,
                    "standard_price": 9.0,
                }
            ],
        )

        self._make_out_move(product, 1)
        self.assertEqual(product.qty_available, 6.0)

        self._refund(bill02)
        self.assertRecordValues(
            product,
            [
                {
                    "total_value": 60.0,
                    "standard_price": 10.0,
                }
            ],
        )

        self._create_bill(purchase_order=po, price_unit=10.0)
        self.assertRecordValues(
            product,
            [
                {
                    "qty_available": 6.0,
                    "total_value": 60.0,
                    "standard_price": 10.0,
                }
            ],
        )

    def test_pdiff_with_returns_and_credit_notes(self):
        product = self.product1
        po = self._create_purchase(product, quantity=10, price_unit=10.0)
        receipt = self._receive(po, quantity=10)
        self.assertEqual(product.total_value, 100.0)

        return01 = self._make_return(receipt, 3)
        self.assertRecordValues(
            product,
            [
                {
                    "qty_available": 7.0,
                    "total_value": 70.0,
                }
            ],
        )

        self._make_return(return01, 3)
        self.assertRecordValues(
            product,
            [
                {
                    "qty_available": 10.0,
                    "total_value": 100.0,
                }
            ],
        )

        bill = self._create_bill(purchase_order=po, quantity=10, price_unit=12.0)
        self.assertEqual(product.total_value, 114.0)
        self.assertAlmostEqual(product.standard_price, 11.4)

        self._make_return(receipt, 1)
        self.assertRecordValues(
            product,
            [
                {
                    "qty_available": 9.0,
                    "total_value": 102.0,
                }
            ],
        )

        refund = self._create_bill(purchase_order=po, price_unit=12.0)
        self.assertEqual(refund.move_type, "in_refund")
        self.assertAlmostEqual(product.total_value, 100.8)

        self._make_return(receipt, 5)
        self.assertEqual(product.qty_available, 4.0)
        self.assertAlmostEqual(product.total_value, 41.8)

        self._refund(bill, quantity=5)
        self.assertEqual(product.qty_available, 4.0)
        self.assertAlmostEqual(product.total_value, 40.8)
        self.assertAlmostEqual(product.standard_price, 10.2)

    def test_pdiff_multi_curr_and_rates(self):
        product = self.product1
        product.categ_id = self.category_avco_auto
        eur = self.env.ref("base.EUR")
        eur.active = True
        self.env.company.currency_id = self.env.ref("base.USD").id

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        self.env["res.currency.rate"].search([("currency_id", "=", eur.id)]).unlink()
        self.env["res.currency.rate"].create(
            [
                {
                    "name": day,
                    "rate": 1 / rate,
                    "currency_id": eur.id,
                    "company_id": self.env.company.id,
                }
                for (day, rate) in [
                    (today, 1.5),
                    (yesterday, 1.3),
                    (two_days_ago, 1.25),
                ]
            ]
        )

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": eur.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        po.action_confirm()
        receipt = self._receive(po)
        self.assertEqual(receipt.value, 150.0)
        self.assertEqual(product.total_value, 150.0)

        bill = po.create_invoice()
        bill.invoice_date = two_days_ago
        bill.date = yesterday
        bill.action_post()

        self.assertEqual(receipt.value, 125.0)
        self.assertRecordValues(
            product,
            [
                {
                    "total_value": 125.0,
                    "standard_price": 125.0,
                }
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 125.0
        )

    def test_multicurrency_bill_before_receipt_values_at_bill_rate(self):
        product = self.product1
        product.bill_policy = "ordered"
        eur = self.env.ref("base.EUR")
        eur.active = True
        self.env.company.currency_id = self.env.ref("base.USD").id

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        self.env["res.currency.rate"].search([("currency_id", "=", eur.id)]).unlink()
        self.env["res.currency.rate"].create(
            [
                {
                    "name": day,
                    "rate": 1 / rate,
                    "currency_id": eur.id,
                    "company_id": self.env.company.id,
                }
                for (day, rate) in [(today, 0.4), (yesterday, 0.5)]
            ]
        )

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": eur.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 1.0,
                            "price_unit": 100.0,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        po.action_confirm()

        bill = po.create_invoice()
        bill.invoice_date = bill.date = yesterday
        bill.action_post()

        receipt = self._receive(po)

        self.assertEqual(receipt.value, 50.0)
        self.assertRecordValues(
            product,
            [
                {
                    "total_value": 50.0,
                    "standard_price": 50.0,
                    "qty_available": 1.0,
                }
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 50.0
        )

    def test_multicurrency_bill_after_delivery_revalues_at_bill_rate(self):
        product = self.product1
        product.categ_id = self.category_avco_auto
        eur = self.env.ref("base.EUR")
        eur.active = True
        self.env.company.currency_id = self.env.ref("base.USD").id

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        self.env["res.currency.rate"].search([("currency_id", "=", eur.id)]).unlink()
        self.env["res.currency.rate"].create(
            [
                {
                    "name": day,
                    "rate": 1 / rate,
                    "currency_id": eur.id,
                    "company_id": self.env.company.id,
                }
                for (day, rate) in [(today, 2.5), (yesterday, 2.0)]
            ]
        )

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": eur.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 1.0,
                            "price_unit": 1000.0,
                            "tax_ids": False,
                        }
                    )
                ],
            }
        )
        po.action_confirm()

        receipt = self._receive(po)
        self.assertEqual(receipt.value, 2500.0)
        self.assertEqual(product.total_value, 2500.0)

        out_move = self._make_out_move(product, 1)
        self.assertEqual(product.total_value, 0.0)
        self.assertEqual(out_move.value, 2500.0)

        bill = po.create_invoice()
        bill.invoice_date = bill.date = yesterday
        bill.action_post()

        self.assertEqual(receipt.value, 2000.0)
        self.assertEqual(out_move.value, 2500.0)
        self.assertEqual(product.total_value, 0.0)
