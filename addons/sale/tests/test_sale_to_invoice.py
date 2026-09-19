from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import Form, tagged
from odoo.tools import float_is_zero

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged("-at_install", "post_install")
class TestSaleToInvoice(TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "partner_invoice_id": cls.partner_a.id,
                "partner_shipping_id": cls.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.company_data["product_order_no"].id,
                            "product_qty": 5,
                            "tax_ids": False,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.company_data[
                                "product_service_delivery"
                            ].id,
                            "product_qty": 4,
                            "tax_ids": False,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.company_data["product_service_order"].id,
                            "product_qty": 3,
                            "tax_ids": False,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": cls.company_data["product_delivery_no"].id,
                            "product_qty": 2,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )

        (
            cls.sol_prod_order,
            cls.sol_serv_deliver,
            cls.sol_serv_order,
            cls.sol_prod_deliver,
        ) = cls.sale_order.line_ids

        cls.context = {
            "active_model": "sale.order",
            "active_ids": [cls.sale_order.id],
            "active_id": cls.sale_order.id,
            "default_journal_id": cls.company_data["default_journal_sale"].id,
        }

    def _check_order_search(self, orders, domain, expected_result):
        domain += [("id", "in", orders.ids)]
        result = self.env["sale.order"].search(domain)
        self.assertEqual(result, expected_result, "Unexpected result on search orders")

    def test_search_invoice_ids(self):
        self.sol_prod_order.product_qty = 0
        self.sale_order.action_confirm()

        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.sale_order
        )
        self._check_order_search(
            self.sale_order, [("invoice_ids", "!=", False)], self.env["sale.order"]
        )

        moves = self.sale_order._create_invoices()

        self._check_order_search(
            self.sale_order, [("invoice_ids", "in", moves.ids)], self.sale_order
        )
        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.env["sale.order"]
        )
        self._check_order_search(
            self.sale_order, [("invoice_ids", "!=", False)], self.sale_order
        )

    def test_downpayment(self):
        self.sale_order.action_confirm()
        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.sale_order
        )
        downpayment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 50,
                }
            )
        )
        downpayment.create_invoices()
        downpayment2 = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 50,
                }
            )
        )
        downpayment2.create_invoices()
        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.env["sale.order"]
        )

        self.assertEqual(
            len(self.sale_order.invoice_ids), 2, "Invoice should be created for the SO"
        )
        downpayment_line = self.sale_order.line_ids.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        self.assertEqual(
            len(downpayment_line), 2, "SO line downpayment should be created on SO"
        )

        self.sale_order.invoice_ids.action_post()

        self.sol_serv_deliver.write({"qty_transferred": 4.0})
        self.sol_prod_deliver.write({"qty_transferred": 2.0})

        payment = (
            self.env["sale.advance.payment.inv"].with_context(self.context).create({})
        )
        payment.create_invoices()

        self.assertEqual(
            len(self.sale_order.invoice_ids), 3, "Invoice should be created for the SO"
        )

        invoice = self.sale_order.invoice_ids.sorted(key=lambda x: x.id)[-1]
        self.assertEqual(
            len(
                invoice.invoice_line_ids.filtered(
                    lambda l: (
                        not (
                            l.display_type == "line_section"
                            and l.name == "Down Payments"
                        )
                    )
                )
            ),
            len(
                self.sale_order.line_ids.filtered(
                    lambda l: (
                        not (
                            l.display_type == "line_section"
                            and l.name == "Down Payments"
                        )
                    )
                )
            ),
            "All lines should be invoiced",
        )
        self.assertEqual(
            len(
                invoice.invoice_line_ids.filtered(
                    lambda l: (
                        l.display_type == "line_section" and l.name == "Down Payments"
                    )
                )
            ),
            1,
            "A single section for downpayments should be present",
        )
        self.assertEqual(
            invoice.amount_total,
            self.sale_order.amount_total - sum(downpayment_line.mapped("price_unit")),
            "Downpayment should be applied",
        )

    def test_a_down_payment_is_deducted_by_one_final_invoice_only(self):
        self.sale_order.action_confirm()
        self.env["sale.advance.payment.inv"].with_context(self.context).create(
            {"advance_payment_method": "fixed", "fixed_amount": 50}
        ).create_invoices()
        self.sale_order.invoice_ids.action_post()
        self.sol_serv_deliver.write({"qty_transferred": 4.0})
        self.sol_prod_deliver.write({"qty_transferred": 2.0})

        def deductions(invoice):
            return invoice.invoice_line_ids.filtered(
                lambda line: line.is_downpayment and line.display_type == "product"
            )

        final_invoice = self.sale_order._create_invoices(final=True)
        self.assertEqual(deductions(final_invoice).quantity, -1.0)
        final_invoice.action_post()

        self.sol_serv_deliver.write({"qty_transferred": 5.0})
        next_invoice = self.sale_order._create_invoices(final=True)

        self.assertTrue(next_invoice)
        self.assertFalse(deductions(next_invoice))

    def test_downpayment_validation(self):
        self.env.user.group_ids += self.env.ref("sale.group_auto_done_setting")

        self.sale_order.action_confirm()
        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.sale_order
        )
        downpayment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create(
                {
                    "advance_payment_method": "percentage",
                    "amount": 10,
                }
            )
        )
        downpayment.create_invoices()
        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.env["sale.order"]
        )

        self.sol_serv_deliver.write({"qty_transferred": 4.0})
        self.sol_prod_deliver.write({"qty_transferred": 2.0})

        self.sale_order.invoice_ids.action_post()

    def test_downpayment_line_remains_on_SO(self):
        sale_order = (
            self.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.company_data["product_order_no"].id,
                                "product_qty": 5,
                                "tax_ids": False,
                            }
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        sale_order.line_ids.write({"qty_transferred": 5.0})
        context = {
            "active_model": "sale.order",
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }
        downpayment = (
            self.env["sale.advance.payment.inv"]
            .with_context(context)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 50,
                }
            )
        )
        downpayment.create_invoices()
        payment = self.env["sale.advance.payment.inv"].with_context(context).create({})
        payment.create_invoices()

        downpayment_line = sale_order.line_ids.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        self.assertEqual(
            downpayment_line[0].price_unit,
            50,
            "The down payment unit price should not change on SO",
        )
        sale_order.invoice_ids.action_post()
        self.assertEqual(
            downpayment_line[0].price_unit,
            50,
            "The down payment unit price should not change on SO",
        )

    def test_downpayment_line_name(self):
        sale_order = (
            self.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.company_data["product_order_no"].id,
                                "product_qty": 5,
                                "tax_ids": False,
                            }
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        sale_order.line_ids.write({"qty_transferred": 5.0})
        context = {
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }
        self.env["sale.advance.payment.inv"].with_context(context).create(
            {
                "sale_order_ids": [Command.set(sale_order.ids)],
                "advance_payment_method": "fixed",
                "fixed_amount": 50,
            }
        ).create_invoices()
        dp_line = sale_order.line_ids.filtered(
            lambda sol: sol.is_downpayment and not sol.display_type
        )

        dp_line.name = "whatever"

        invoice = sale_order.invoice_ids
        invoice.action_post()

        self.assertNotEqual(
            dp_line.name,
            "whatever",
            "DP lines description should be recomputed when the linked invoice is posted",
        )

    def test_downpayment_fixed_amount_with_zero_total_amount(self):
        sale_order = (
            self.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.company_data["product_order_no"].id,
                                "product_qty": 5,
                                "price_unit": 0,
                                "tax_ids": False,
                            }
                        ),
                    ],
                }
            )
        )
        sale_order.action_confirm()
        sale_order.line_ids.write({"qty_transferred": 5.0})
        context = {
            "active_model": "sale.order",
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }
        downpayment = (
            self.env["sale.advance.payment.inv"]
            .with_context(context)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 50,
                }
            )
        )
        downpayment.create_invoices()
        self.assertEqual(
            downpayment.amount, 0.0, "The down payment amount should be 0.0"
        )

    def test_downpayment_percentage_tax_icl(self):
        tax_incl = self.company_data["default_tax_sale"].copy(
            {
                "name": "default price included",
                "price_include_override": "tax_included",
            }
        )
        self.sale_order.line_ids.filtered(
            lambda l: not l.display_type
        ).tax_ids = tax_incl
        self.sale_order.action_confirm()
        self.assertTrue(
            self.sale_order.amount_tax,
            "The order should carry an included tax for this scenario.",
        )
        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create(
                {
                    "advance_payment_method": "percentage",
                    "amount": 50,
                }
            )
        )
        payment.create_invoices()

        self.assertEqual(
            len(self.sale_order.invoice_ids), 1, "Invoice should be created for the SO"
        )
        downpayment_line = self.sale_order.line_ids.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        self.assertEqual(
            len(downpayment_line), 1, "SO line downpayment should be created on SO"
        )
        self.assertEqual(
            downpayment_line.price_unit,
            self.sale_order.amount_total / 2,
            "downpayment should have the correct amount",
        )

        invoice = self.sale_order.invoice_ids[0]
        downpayment_aml = invoice.line_ids.filtered(
            lambda l: (
                not (l.display_type == "line_section" and l.name == "Down Payments")
            )
        )[0]
        self.assertEqual(
            downpayment_aml.price_total,
            self.sale_order.amount_total / 2,
            "downpayment should have the correct amount",
        )
        self.assertEqual(
            downpayment_aml.price_unit,
            self.sale_order.amount_total / 2,
            "downpayment should have the correct amount",
        )
        invoice.action_post()
        self.assertEqual(
            downpayment_line.price_unit,
            self.sale_order.amount_total / 2,
            "downpayment should have the correct amount",
        )

    def test_downpayment_invoice_and_partial_credit_note(self):
        self.sale_order.action_confirm()

        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 100,
                }
            )
        )
        payment.create_invoices()

        downpayment_line = self.sale_order.line_ids.filtered(
            lambda l: l.is_downpayment and not l.display_type
        )
        self.assertEqual(downpayment_line.price_unit, 100)

        downpayment_invoice = (
            downpayment_line.order_id.line_ids.invoice_line_ids.move_id
        )
        downpayment_invoice.action_post()
        self.assertEqual(downpayment_line.price_unit, 100)

        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(
                active_model="account.move",
                active_ids=downpayment_invoice.ids,
            )
            .create(
                {
                    "date": "2020-02-01",
                    "reason": "no reason",
                    "journal_id": downpayment_invoice.journal_id.id,
                }
            )
        )
        reversal_action = move_reversal.reverse_moves()
        reverse_move = self.env["account.move"].browse(reversal_action["res_id"])
        with Form(reverse_move) as form_reverse:
            with form_reverse.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 20.0
        reverse_move.action_post()

        self.assertEqual(
            downpayment_line.price_unit,
            80,
            "The downpayment line amount should be equal to the sum of the invoice and credit note amount",
        )

    def test_invoice_with_discount(self):
        self.sol_prod_order.write({"discount": 20.0})
        self.sol_serv_deliver.write({"discount": 20.0, "qty_transferred": 4.0})
        self.sol_serv_order.write({"discount": -10.0})
        self.sol_prod_deliver.write({"qty_transferred": 2.0})

        for line in self.sale_order.line_ids.filtered(lambda l: l.discount):
            product_price = line.price_unit * line.product_uom_qty
            self.assertEqual(
                line.discount,
                (product_price - line.price_subtotal) / product_price * 100,
                "Discount should be applied on order line",
            )

        for line in self.sale_order.line_ids:
            self.assertTrue(
                float_is_zero(line.amount_taxexc_to_invoice, precision_digits=2),
                "The amount to invoice should be zero, as the line is in draf state",
            )
            self.assertTrue(
                float_is_zero(line.amount_taxexc_invoiced, precision_digits=2),
                "The invoiced amount should be zero, as the line is in draft state",
            )

        self.sale_order.action_confirm()

        for line in self.sale_order.line_ids:
            self.assertTrue(
                float_is_zero(line.amount_taxexc_invoiced, precision_digits=2),
                "The invoiced amount should be zero, as the line is in draft state",
            )

        self.assertEqual(
            self.sol_serv_order.amount_taxexc_to_invoice,
            297,
            "The untaxed amount to invoice is wrong",
        )
        self.assertEqual(
            self.sol_serv_deliver.amount_taxexc_to_invoice,
            576,
            "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)",
        )

        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create({"advance_payment_method": "delivered"})
        )
        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.sale_order
        )
        payment.create_invoices()
        self._check_order_search(
            self.sale_order, [("invoice_ids", "=", False)], self.env["sale.order"]
        )
        invoice = self.sale_order.invoice_ids[0]
        invoice.action_post()

        compared = 0
        for inv_line in invoice.invoice_line_ids:
            for order_line in inv_line.sale_line_ids:
                self.assertEqual(
                    order_line.discount,
                    inv_line.discount,
                    "Discount on lines of order and invoice should be same",
                )
                compared += 1
        self.assertTrue(compared, "No invoice line was linked back to an order line")

    def test_invoice(self):
        for line in self.sale_order.line_ids:
            self.assertTrue(
                float_is_zero(line.amount_taxexc_to_invoice, precision_digits=2),
                "The amount to invoice should be zero, as the line is in draf state",
            )
            self.assertTrue(
                float_is_zero(line.amount_taxexc_invoiced, precision_digits=2),
                "The invoiced amount should be zero, as the line is in draft state",
            )

        self.sale_order.action_confirm()

        for line in self.sale_order.line_ids:
            if line.product_id.invoice_policy == "transferred":
                self.assertEqual(
                    line.qty_to_invoice,
                    0.0,
                    "Quantity to invoice should be same as ordered quantity",
                )
                self.assertEqual(
                    line.qty_invoiced,
                    0.0,
                    "Invoiced quantity should be zero as no any invoice created for SO",
                )
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    0.0,
                    "The amount to invoice should be zero, as the line based on delivered quantity",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    0.0,
                    "The invoiced amount should be zero, as the line based on delivered quantity",
                )
            else:
                self.assertEqual(
                    line.qty_to_invoice,
                    line.product_uom_qty,
                    "Quantity to invoice should be same as ordered quantity",
                )
                self.assertEqual(
                    line.qty_invoiced,
                    0.0,
                    "Invoiced quantity should be zero as no any invoice created for SO",
                )
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    line.product_uom_qty * line.price_unit,
                    "The amount to invoice should the total of the line, as the line is confirmed",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    0.0,
                    "The invoiced amount should be zero, as the line is confirmed",
                )

        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create({"advance_payment_method": "delivered"})
        )
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]

        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 3.0
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 2.0
        invoice = move_form.save()

        for line in self.sale_order.line_ids:
            if line.product_id.invoice_policy == "transferred":
                self.assertEqual(
                    line.qty_to_invoice, 0.0, "Quantity to invoice should be zero"
                )
                self.assertEqual(
                    line.qty_invoiced,
                    0.0,
                    "Invoiced quantity should be zero as delivered lines are not delivered yet",
                )
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    0.0,
                    "The amount to invoice should be zero, as the line based on delivered quantity (no confirmed invoice)",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    0.0,
                    "The invoiced amount should be zero, as no invoice are validated for now",
                )
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(
                        line.qty_to_invoice,
                        2.0,
                        "Changing the quantity on a draft invoice updates the "
                        "qty to invoice on SO lines",
                    )
                    self.assertEqual(line.qty_invoiced, 3.0)
                else:
                    self.assertEqual(
                        line.qty_to_invoice,
                        1.0,
                        "Changing the quantity on a draft invoice updates the "
                        "qty to invoice on SO lines",
                    )
                    self.assertEqual(line.qty_invoiced, 2.0)
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    line.product_uom_qty * line.price_unit,
                    "The amount to invoice should the total of the line, as the line is confirmed (no confirmed invoice)",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    0.0,
                    "The invoiced amount should be zero, as no invoice are validated for now",
                )

        invoice.action_cancel()
        for line in self.sale_order.line_ids:
            if line.product_id.invoice_policy == "transferred":
                self.assertEqual(
                    line.qty_to_invoice,
                    0.0,
                    "Quantity to invoice should be same as ordered quantity",
                )
                self.assertEqual(
                    line.qty_invoiced,
                    0.0,
                    "Invoiced quantity should be zero as no any invoice created for SO",
                )
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    0.0,
                    "The amount to invoice should be zero, as the line based on delivered quantity",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    0.0,
                    "The invoiced amount should be zero, as the line based on delivered quantity",
                )
            else:
                self.assertEqual(
                    line.qty_to_invoice,
                    line.product_uom_qty,
                    "Quantity to invoice should be same as ordered quantity",
                )
                self.assertEqual(
                    line.qty_invoiced,
                    0.0,
                    "Invoiced quantity should be zero as no any invoice created for SO",
                )
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    line.product_uom_qty * line.price_unit,
                    "The amount to invoice should the total of the line, as the line is confirmed",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    0.0,
                    "The invoiced amount should be zero, as the line is confirmed",
                )

        invoice.action_draft()
        invoice.action_post()

        for line in self.sale_order.line_ids:
            if line.product_id.invoice_policy == "transferred":
                self.assertEqual(
                    line.qty_to_invoice,
                    0.0,
                    "Quantity to invoice should be same as ordered quantity",
                )
                self.assertEqual(
                    line.qty_invoiced,
                    0.0,
                    "Invoiced quantity should be zero as no any invoice created for SO",
                )
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    0.0,
                    "The amount to invoice should be zero, as the line based on delivered quantity",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    0.0,
                    "The invoiced amount should be zero, as the line based on delivered quantity",
                )
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(
                        line.qty_to_invoice,
                        2.0,
                        "The ordered sale line are totally invoiced (qty to invoice is zero)",
                    )
                    self.assertEqual(
                        line.qty_invoiced,
                        3.0,
                        "The ordered (prod) sale line are totally invoiced (qty invoiced come from the invoice lines)",
                    )
                else:
                    self.assertEqual(
                        line.qty_to_invoice,
                        1.0,
                        "The ordered sale line are totally invoiced (qty to invoice is zero)",
                    )
                    self.assertEqual(
                        line.qty_invoiced,
                        2.0,
                        "The ordered (serv) sale line are totally invoiced (qty invoiced = the invoice lines)",
                    )
                self.assertEqual(
                    line.amount_taxexc_to_invoice,
                    line.price_unit * line.qty_to_invoice,
                    "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products",
                )
                self.assertEqual(
                    line.amount_taxexc_invoiced,
                    line.price_unit * line.qty_invoiced,
                    "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products",
                )

    def test_multiple_sale_orders_on_same_invoice(self):
        self.sale_order.action_confirm()
        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create({"advance_payment_method": "delivered"})
        )
        payment.create_invoices()

        sale_order_data = self.sale_order.copy_data()[0]
        sale_order_data["line_ids"] = [
            (
                0,
                0,
                line.copy_data(
                    {
                        "invoice_line_ids": [(6, 0, line.invoice_line_ids.ids)],
                    }
                )[0],
            )
            for line in self.sale_order.line_ids
        ]
        self.sale_order.create(sale_order_data)

        invoice = self.sale_order.invoice_ids[0]
        self.assertTrue(
            any(len(move_line.sale_line_ids) > 1 for move_line in invoice.line_ids)
        )

        invoice.action_post()
        invoice.action_draft()
        invoice.action_cancel()

    def test_invoice_with_sections(self):
        sale_order = (
            self.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                }
            )
        )

        SaleOrderLine = self.env["sale.order.line"].with_context(tracking_disable=True)
        SaleOrderLine.create(
            {
                "name": "Section",
                "display_type": "line_section",
                "order_id": sale_order.id,
            }
        )
        sol_prod_deliver = SaleOrderLine.create(
            {
                "product_id": self.company_data["product_order_no"].id,
                "product_qty": 5,
                "order_id": sale_order.id,
                "tax_ids": False,
            }
        )

        sale_order.action_confirm()

        sol_prod_deliver.write({"qty_transferred": 5.0})

        self.context = {
            "active_model": "sale.order",
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }

        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create({"advance_payment_method": "delivered"})
        )
        payment.create_invoices()

        invoice = sale_order.invoice_ids[0]

        self.assertEqual(invoice.line_ids[0].display_type, "line_section")

    def test_invoice_combo_product(self):
        product_a = self._create_product(
            name="Horse-meat burger", invoice_policy="transferred"
        )
        product_b = self._create_product(
            name="French fries", invoice_policy="transferred"
        )
        combo_a = self.env["product.combo"].create(
            {
                "name": "Burger",
                "combo_item_ids": [
                    Command.create({"product_id": product_a.id}),
                ],
            }
        )
        combo_b = self.env["product.combo"].create(
            {
                "name": "Side",
                "combo_item_ids": [
                    Command.create({"product_id": product_b.id}),
                ],
            }
        )
        product_combo = self._create_product(
            name="Meal Menu",
            list_price=10.0,
            type="combo",
            combo_ids=[
                Command.link(combo_a.id),
                Command.link(combo_b.id),
            ],
        )

        sale_order = (
            self.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": "Meal Menu",
                                "product_id": product_combo.id,
                                "product_qty": 3,
                                "price_unit": 0,
                                "tax_ids": [],
                            }
                        ),
                    ],
                }
            )
        )
        sale_order.line_ids = [
            Command.create(
                {
                    "product_id": product.id,
                    "product_qty": 3,
                    "price_unit": 5.0,
                    "tax_ids": [],
                    "combo_item_id": combo.combo_item_ids.id,
                    "linked_line_id": sale_order.line_ids.id,
                }
            )
            for product, combo in zip(
                product_a + product_b, combo_a + combo_b, strict=True
            )
        ]

        sale_order.action_confirm()

        self.assertEqual(sale_order.line_ids.mapped("qty_to_invoice"), [0.0, 0.0, 0.0])
        deliverables = sale_order.line_ids.filtered(
            lambda sol: sol.product_id.invoice_policy == "transferred",
        )
        self.assertEqual(
            deliverables,
            sale_order.line_ids.linked_line_ids,
            "Only combo item lines should be invoiced on delivery.",
        )
        deliverables.qty_transferred = 3
        deliverables.flush_recordset()
        self.assertEqual(
            sale_order.line_ids.mapped("qty_to_invoice"),
            [3.0, 3.0, 3.0],
            "Delivering the combo items lines should update the combo product line as well.",
        )

        self.context = {
            "active_model": "sale.order",
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }

        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create({"advance_payment_method": "delivered"})
        )
        payment.create_invoices()

        invoice = sale_order.invoice_ids[0]

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    "name": "Meal Menu x 3",
                    "display_type": "line_section",
                    "product_id": False,
                    "quantity": 3,
                    "price_unit": 0,
                    "sequence": 0,
                },
                {
                    "name": "Horse-meat burger",
                    "display_type": "product",
                    "product_id": product_a.id,
                    "quantity": 3,
                    "price_unit": 5.0,
                    "sequence": 1,
                },
                {
                    "name": "French fries",
                    "display_type": "product",
                    "product_id": product_b.id,
                    "quantity": 3,
                    "price_unit": 5.0,
                    "sequence": 2,
                },
            ],
        )
        invoice.action_post()
        self.assertRecordValues(
            sale_order.line_ids,
            [
                {
                    "product_id": product_combo.id,
                    "qty_to_invoice": 0,
                    "qty_invoiced": 3,
                },
                {
                    "product_id": product_a.id,
                    "qty_to_invoice": 0,
                    "qty_invoiced": 3,
                },
                {
                    "product_id": product_b.id,
                    "qty_to_invoice": 0,
                    "qty_invoiced": 3,
                },
            ],
        )

    def test_qty_invoiced(self):
        sale_order = (
            self.env["sale.order"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "partner_invoice_id": self.partner_a.id,
                    "partner_shipping_id": self.partner_a.id,
                }
            )
        )

        SaleOrderLine = self.env["sale.order.line"].with_context(tracking_disable=True)
        sol_prod_deliver = SaleOrderLine.create(
            {
                "product_id": self.company_data["product_order_no"].id,
                "product_qty": 5,
                "order_id": sale_order.id,
                "tax_ids": False,
            }
        )

        sale_order.action_confirm()

        sol_prod_deliver.write({"qty_transferred": 5.0})
        self.context = {
            "active_model": "sale.order",
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }

        invoicing_wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(self.context)
            .create({"advance_payment_method": "delivered"})
        )
        invoicing_wizard.create_invoices()

        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)

        sale_order.invoice_ids.action_post()
        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)

        sale_order.invoice_ids.action_draft()
        quantity = 5.13
        move_form = Form(sale_order.invoice_ids)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = quantity
        move_form.save()

        sale_order.invoice_ids.action_post()

        qty_invoiced_field = sol_prod_deliver._fields.get("qty_invoiced")
        sol_prod_deliver.env.add_to_compute(qty_invoiced_field, sol_prod_deliver)
        self.assertEqual(sol_prod_deliver.qty_invoiced, quantity)

        sale_order.invoice_ids.action_draft()
        sol_prod_deliver.product_uom_id.rounding *= 10
        sol_prod_deliver.product_uom_id.flush_recordset(["rounding"])
        sale_order.invoice_ids.action_post()
        expected_qty = 5.2
        qty_invoiced_field = sol_prod_deliver._fields.get("qty_invoiced")
        sol_prod_deliver.env.add_to_compute(qty_invoiced_field, sol_prod_deliver)
        self.assertEqual(sol_prod_deliver.qty_invoiced, expected_qty)

    def test_invoice_state_over_invoiced_ordered_policy(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 5,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )
        line = sale_order.line_ids
        self.assertEqual(line.product_id.invoice_policy, "ordered")

        sale_order.action_confirm()

        invoice = sale_order._create_invoices()
        invoice.action_post()
        self.assertEqual(line.qty_invoiced, 5.0)
        self.assertEqual(line.invoice_state, "done")

        line.write({"product_qty": 3})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(line.qty_to_invoice, -2.0)
        self.assertEqual(
            line.invoice_state,
            "over done",
            'Over-invoiced ordered-policy line should be "over done"',
        )

    def test_invoice_state_zero_qty_line_does_not_hold_order_partial(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 5,
                            "tax_ids": False,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 0,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )
        invoiced_line, zero_qty_line = sale_order.line_ids

        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(invoiced_line.invoice_state, "done")
        self.assertEqual(zero_qty_line.invoice_state, "no")
        self.assertEqual(
            sale_order.invoice_state,
            "done",
            "SO fully invoiced apart from a zero-quantity line should be "
            '"done", not "partial"',
        )

    def test_invoice_state_pending_transferred_line_keeps_order_partial(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 5,
                            "tax_ids": False,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.company_data["product_delivery_no"].id,
                            "product_qty": 5,
                            "tax_ids": False,
                        }
                    ),
                ],
            }
        )
        ordered_line, delivered_line = sale_order.line_ids
        self.assertEqual(delivered_line.product_id.invoice_policy, "transferred")

        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(ordered_line.invoice_state, "done")
        self.assertEqual(delivered_line.invoice_state, "no")
        self.assertEqual(
            sale_order.invoice_state,
            "partial",
            'SO with an undelivered transferred-policy line should stay "partial"',
        )

    def test_multi_company_invoice(self):
        so_company_id = self.sale_order.company_id.id
        yet_another_company_id = self.company_data_2["company"].id
        so_for_downpayment = self.sale_order.copy()

        self.context.update(
            allowed_company_ids=[yet_another_company_id, self.env.company.id],
            company_id=yet_another_company_id,
        )
        context_for_downpayment = self.context.copy()
        context_for_downpayment.update(
            active_ids=[so_for_downpayment.id], active_id=so_for_downpayment.id
        )

        no_journal_ctxt = dict(self.context)
        no_journal_ctxt.pop("default_journal_id", None)
        no_journal_ctxt.pop("journal_id", None)

        self.sale_order.with_context(self.context).action_confirm()
        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(no_journal_ctxt)
            .create(
                {
                    "advance_payment_method": "percentage",
                    "amount": 50,
                }
            )
        )
        payment.create_invoices()
        self.assertEqual(
            self.sale_order.invoice_ids[0].company_id.id,
            so_company_id,
            "The company of the invoice should be the same as the one from the SO",
        )

        so_for_downpayment.with_context(context_for_downpayment).action_confirm()
        downpayment = (
            self.env["sale.advance.payment.inv"]
            .with_context(context_for_downpayment)
            .create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 50,
                }
            )
        )
        downpayment.create_invoices()
        self.assertEqual(
            so_for_downpayment.invoice_ids[0].company_id.id,
            so_company_id,
            "The company of the downpayment invoice should be the same as the one from the SO",
        )

    def test_invoice_analytic_distribution_model(self):
        analytic_plan_default = self.env["account.analytic.plan"].create(
            {"name": "default"}
        )
        analytic_account_default = self.env["account.analytic.account"].create(
            {"name": "default", "plan_id": analytic_plan_default.id}
        )

        self.env["account.analytic.distribution.model"].create(
            {
                "analytic_distribution": {analytic_account_default.id: 100},
                "product_id": self.product_a.id,
            }
        )

        so_form = Form(self.env["sale.order"])
        so_form.partner_id = self.partner_a

        with so_form.line_ids.new() as sol:
            sol.product_id = self.product_a
            sol.product_qty = 1

        so = so_form.save()
        so.action_confirm()
        so._force_lines_to_invoice_policy_order()

        so_context = {
            "active_model": "sale.order",
            "active_ids": [so.id],
            "active_id": so.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }
        down_payment = (
            self.env["sale.advance.payment.inv"].with_context(so_context).create({})
        )
        down_payment.create_invoices()

        aml = self.env["account.move.line"].search(
            [("move_id", "in", so.invoice_ids.ids)]
        )[0]
        self.assertRecordValues(
            aml, [{"analytic_distribution": {str(analytic_account_default.id): 100}}]
        )

    def test_invoice_analytic_rule_with_account_prefix(self):
        self.env.user.group_ids += self.env.ref("analytic.group_analytic_accounting")
        analytic_plan_default = self.env["account.analytic.plan"].create(
            {
                "name": "default",
                "applicability_ids": [
                    Command.create(
                        {
                            "business_domain": "invoice",
                            "applicability": "optional",
                        }
                    )
                ],
            }
        )
        analytic_account_default = self.env["account.analytic.account"].create(
            {"name": "default", "plan_id": analytic_plan_default.id}
        )
        analytic_plan_2 = self.env["account.analytic.plan"].create({"name": "manual"})
        analytic_account_2 = self.env["account.analytic.account"].create(
            {"name": "manual", "plan_id": analytic_plan_2.id}
        )
        analytic_distribution_manual = {str(analytic_account_2.id): 100}

        analytic_distribution_model = self.env[
            "account.analytic.distribution.model"
        ].create(
            {
                "account_prefix": "400000",
                "analytic_distribution": {analytic_account_default.id: 100},
                "product_id": self.product_a.id,
            }
        )

        so = self.env["sale.order"].create({"partner_id": self.partner_a.id})
        self.env["sale.order.line"].create(
            {"order_id": so.id, "name": "test", "product_id": self.product_a.id}
        )
        self.assertFalse(
            so.line_ids.analytic_distribution, "There should be no tag set."
        )
        so.line_ids.analytic_distribution = analytic_distribution_manual
        so.action_confirm()
        so.line_ids.qty_transferred = 1
        aml = so._create_invoices().invoice_line_ids
        self.assertRecordValues(
            aml,
            [
                {
                    "analytic_distribution": analytic_distribution_model.analytic_distribution
                    | analytic_distribution_manual
                }
            ],
        )

    def test_invoice_after_product_return_price_not_default(self):
        so = self.env["sale.order"].create(
            {
                "name": "Sale order",
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.product_a.name,
                            "product_id": self.product_a.id,
                            "product_qty": 1,
                            "price_unit": 123,
                        },
                    ),
                ],
            }
        )
        self._check_order_search(so, [("invoice_ids", "=", False)], so)
        so.action_confirm()
        so_context = {
            "active_model": "sale.order",
            "active_ids": [so.id],
            "active_id": so.id,
            "default_journal_id": self.company_data["default_journal_sale"].id,
        }
        invoicing_wizard = (
            self.env["sale.advance.payment.inv"].with_context(so_context).create({})
        )
        invoicing_wizard.create_invoices()
        self.assertTrue(so.invoice_ids, "The invoice was not created")
        so.invoice_ids.action_post()
        so.line_ids.product_qty = 0
        self.assertEqual(
            so.line_ids.price_unit,
            123,
            "The unit price should be the same as the one used to create the sales order line",
        )

    def test_group_invoice(self):
        eur_pricelist = self.env["product.pricelist"].create(
            {"name": "EUR", "currency_id": self.env.ref("base.EUR").id}
        )
        so1 = self.sale_order.with_context(mail_notrack=True).copy()
        so1.pricelist_id = eur_pricelist
        so2 = so1.copy()
        usd_pricelist = self.env["product.pricelist"].create(
            {"name": "USD", "currency_id": self.env.ref("base.USD").id}
        )
        so3 = so1.copy()
        so1.pricelist_id = usd_pricelist
        orders = so1 | so2 | so3
        orders.action_confirm()
        wiz = (
            self.env["sale.advance.payment.inv"]
            .with_context(active_ids=orders.ids)
            .create({})
        )
        res = wiz.create_invoices()
        self.assertEqual(
            len(res["domain"][0][2]),
            2,
            "Invoicing 3 orders for the same partner with 2 currencies"
            "should create exactly 2 invoices.",
        )

    def test_so_note_to_invoice(self):
        self.sale_order.line_ids = [
            Command.create(
                {
                    "name": "This is a note",
                    "display_type": "line_note",
                    "product_id": False,
                    "product_qty": 0,
                    "product_uom_id": False,
                    "price_unit": 0,
                    "order_id": self.sale_order.id,
                    "tax_ids": False,
                }
            )
        ]

        self.sale_order.action_confirm()

        invoice = self.sale_order._create_invoices()

        self.assertEqual(
            len(
                invoice.invoice_line_ids.filtered(
                    lambda line: line.display_type == "line_note"
                )
            ),
            1,
            "Note SO line should have been pushed to the invoice",
        )

    def test_sale_order_standard_flow_with_invoicing(self):
        self.sale_order.line_ids.product_qty = 2.0
        self.sale_order.line_ids.read(
            ["name", "price_unit", "product_uom_qty", "price_total"]
        )

        self.assertEqual(
            self.sale_order.amount_total, 1240.0, "Sale: total amount is wrong"
        )
        self.sale_order.line_ids._compute_product_readonly()
        self.assertFalse(self.sale_order.line_ids[0].product_readonly)
        email_act = self.sale_order.action_send_quotation()
        email_ctx = email_act.get("context", {})
        self.sale_order.with_context(**email_ctx).message_post_with_source(
            self.env["mail.template"].browse(email_ctx.get("default_template_id")),
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(self.sale_order.sent, "Sale: sent flag after sending is wrong")
        self.sale_order.line_ids._compute_product_readonly()
        self.assertFalse(self.sale_order.line_ids[0].product_readonly)

        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == "done")
        self.assertTrue(self.sale_order.invoice_state == "to do")

        invoice = self.sale_order._create_invoices()
        self.assertEqual(
            len(invoice.invoice_line_ids), 2, "Sale: invoice is missing lines"
        )
        self.assertEqual(
            invoice.amount_total, 740.0, "Sale: invoice total amount is wrong"
        )
        invoice.action_post()
        self.assertTrue(
            self.sale_order.invoice_state == "partial",
            'Sale: SO status after invoicing order-based lines should be "partial" (delivery lines pending)',
        )
        self.assertTrue(
            len(self.sale_order.invoice_ids) == 1, "Sale: invoice is missing"
        )
        self.sale_order.line_ids._compute_product_readonly()
        self.assertTrue(self.sale_order.line_ids[0].product_readonly)

        for line in self.sale_order.line_ids:
            line.qty_transferred = 2 if line.product_id.expense_policy == "no" else 0
        self.assertEqual(
            self.sale_order.invoice_state,
            "partial",
            'Sale: SO status after delivery should be "partial" - a first '
            "invoice is already posted and the newly delivered quantities are "
            "not, so the order has progressed rather than not started",
        )
        invoice2 = self.sale_order._create_invoices()
        self.assertEqual(
            len(invoice2.invoice_line_ids), 2, "Sale: second invoice is missing lines"
        )
        self.assertEqual(
            invoice2.amount_total, 500.0, "Sale: second invoice total amount is wrong"
        )
        invoice2.action_post()
        self.assertTrue(
            self.sale_order.invoice_state == "done",
            'Sale: SO status after invoicing everything should be "done"',
        )
        self.assertTrue(
            len(self.sale_order.invoice_ids) == 2, "Sale: invoice is missing"
        )

        self.sol_serv_order.write({"qty_transferred": 10})
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertTrue(
            self.sale_order.invoice_state == "done",
            'Sale: SO invoice_state stays "done" -- the excess delivered on an '
            "ordered-quantity line is not billable until the order is increased",
        )
        self.assertTrue(
            self.sale_order.has_upsell_opportunity,
            "Sale: SO should have upselling opportunity when delivered qty exceeds ordered qty",
        )

        self.sol_serv_order.write({"product_qty": 10})

        self.env.flush_all()
        self.env.invalidate_all()

        invoice3 = self.sale_order._create_invoices()
        self.assertEqual(
            len(invoice3.invoice_line_ids), 1, "Sale: third invoice is missing lines"
        )
        self.assertEqual(
            invoice3.amount_total, 720.0, "Sale: third invoice total amount is wrong"
        )
        invoice3.action_post()
        self.assertTrue(
            self.sale_order.invoice_state == "done",
            'Sale: SO status after invoicing everything (including the upsell) should be "done"',
        )
        self.assertFalse(
            self.sale_order.has_upsell_opportunity,
            "Sale: SO should no longer have upselling opportunity after increasing order qty",
        )

    def test_so_create_multicompany(self):
        product_shared = self.env["product.template"].create(
            {
                "name": "shared product",
                "invoice_policy": "ordered",
                "taxes_id": [
                    (
                        6,
                        False,
                        (
                            self.company_data["default_tax_sale"]
                            + self.company_data_2["default_tax_sale"]
                        ).ids,
                    )
                ],
                "property_account_income_id": self.company_data[
                    "default_account_revenue"
                ].id,
            }
        )

        so_1 = (
            self.env["sale.order"]
            .with_user(self.company_data["default_user_salesman"])
            .create(
                {
                    "partner_id": self.env["res.partner"]
                    .create({"name": "A partner"})
                    .id,
                    "company_id": self.company_data["company"].id,
                }
            )
        )
        so_1.write(
            {
                "line_ids": [
                    Command.create({"product_id": product_shared.product_variant_id.id})
                ],
            }
        )
        self.assertEqual(so_1.line_ids.product_uom_qty, 1)

        self.assertEqual(
            so_1.line_ids.tax_ids,
            self.company_data["default_tax_sale"],
            "Only taxes from the right company are put by default",
        )
        so_1.action_confirm()
        inv = (
            so_1.sudo()
            .with_context(
                allowed_company_ids=(
                    self.company_data["company"] + self.company_data_2["company"]
                ).ids
            )
            ._create_invoices()
        )
        self.assertEqual(
            inv.company_id,
            self.company_data["company"],
            "invoices should be created in the company of the SO, not the main company of the context",
        )

    def test_partial_invoicing_interaction_with_invoicing_switch_threshold(self):
        if not self.env["ir.module.module"].search(
            [("name", "=", "account_accountant"), ("state", "=", "installed")]
        ):
            self.skipTest(
                "This test requires the installation of the account_account module"
            )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_delivery_no"].id,
                            "product_qty": 20,
                            "price_unit": 30,
                        }
                    ),
                ],
            }
        )
        line = sale_order.line_ids[0]

        sale_order.action_confirm()

        line.qty_transferred = 10

        invoice = sale_order._create_invoices()
        invoice.action_post()

        self.assertEqual(line.qty_invoiced, 10)

        self.env["res.config.settings"].create(
            {
                "invoicing_switch_threshold": fields.Date.add(
                    invoice.invoice_date, days=30
                ),
            }
        ).execute()

        invoice.invalidate_model(fnames=["payment_state"])

        self.assertEqual(line.qty_invoiced, 10)
        line.qty_transferred = 15
        self.assertEqual(line.qty_invoiced, 10)
        self.assertEqual(line.amount_taxexc_invoiced, 300)
        self.assertEqual(sale_order.amount_taxinc_to_invoice, 150)

    def test_salesperson_in_invoice_followers(self):
        self.env = self.env(context={})
        salesperson = self.env["res.users"].create(
            {
                "name": "Salesperson",
                "login": "salesperson",
                "email": "test@test.com",
                "group_ids": [(6, 0, [self.env.ref("sale.group_sale_salesman").id])],
            }
        )

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "user_id": salesperson.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 1,
                        },
                    )
                ],
            }
        )
        sale_order.action_confirm()
        invoice = sale_order._create_invoices(final=True)

        self.assertIn(
            salesperson.partner_id,
            invoice.message_partner_ids,
            "Salesperson not in the followers list of invoice created from SO",
        )

    def test_amount_to_invoice_multiple_so(self):
        sale_order_1 = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_delivery_no"].id,
                            "product_qty": 10,
                        }
                    ),
                ],
            }
        )
        sale_order_2 = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_delivery_no"].id,
                            "product_qty": 20,
                        }
                    ),
                ],
            }
        )

        sale_order_1.action_confirm()
        sale_order_2.action_confirm()
        sale_order_1.line_ids.qty_transferred = 10
        sale_order_2.line_ids.qty_transferred = 20

        self.env["sale.advance.payment.inv"].create(
            {
                "advance_payment_method": "delivered",
                "sale_order_ids": [Command.set((sale_order_1 + sale_order_2).ids)],
            }
        ).create_invoices()

        sale_order_1.invoice_ids.action_post()

        self.assertEqual(sale_order_1.amount_taxinc_to_invoice, 0.0)
        self.assertEqual(sale_order_2.amount_taxinc_to_invoice, 0.0)

    def test_amount_to_invoice_one_line_multiple_so(self):
        sale_order_1 = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_delivery_no"].id,
                            "product_qty": 10,
                        }
                    ),
                ],
            }
        )
        sale_order_2 = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_delivery_no"].id,
                            "product_qty": 20,
                        }
                    ),
                ],
            }
        )

        sale_order_1.action_confirm()
        sale_order_2.action_confirm()
        sale_order_1.line_ids.qty_transferred = 10
        sale_order_2.line_ids.qty_transferred = 20

        self.env["sale.advance.payment.inv"].create(
            {
                "advance_payment_method": "delivered",
                "sale_order_ids": [Command.set((sale_order_2).ids)],
            }
        ).create_invoices()

        sale_order_1.invoice_ids = sale_order_2.invoice_ids
        sale_order_1.invoice_ids.line_ids.sale_line_ids += sale_order_1.line_ids

        sale_order_1.invoice_ids.action_post()

        self.assertEqual(sale_order_1.amount_taxinc_to_invoice, -700.0)
        self.assertEqual(sale_order_2.amount_taxinc_to_invoice, 0.0)

    def test_amount_to_invoice_price_unit_change(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
            }
        )

        sol_prod_deliver = self.env["sale.order.line"].create(
            {
                "product_id": self.company_data["product_order_no"].id,
                "product_qty": 5,
                "order_id": so.id,
                "tax_ids": False,
            }
        )

        so.action_confirm()
        sol_prod_deliver.write({"qty_transferred": 5.0})

        invoice_vals = (
            self.env["sale.advance.payment.inv"]
            .create(
                {
                    "advance_payment_method": "delivered",
                    "sale_order_ids": [Command.set(so.ids)],
                }
            )
            .create_invoices()
        )

        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)
        self.assertEqual(
            sol_prod_deliver.amount_taxinc_to_invoice, sol_prod_deliver.price_total
        )
        self.assertEqual(sol_prod_deliver.amount_taxinc_invoiced, 0.0)

        invoice = self.env[invoice_vals["res_model"]].browse(invoice_vals["res_id"])
        invoice.invoice_line_ids.price_unit /= 2
        invoice.action_post()

        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)
        self.assertEqual(sol_prod_deliver.amount_taxinc_to_invoice, 0.0)
        self.assertEqual(
            sol_prod_deliver.amount_taxinc_invoiced, sol_prod_deliver.price_total / 2
        )

    def test_amount_to_invoice_with_discount(self):
        so = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data["product_order_no"].id,
                            "product_qty": 5,
                            "price_unit": 100,
                            "discount": 10,
                        }
                    ),
                ],
            }
        )

        so.action_confirm()

        self.assertEqual(
            so.amount_taxinc_to_invoice, 450.0, "The amount to invoice should be 450.0"
        )

        invoice = so._create_invoices()
        invoice.invoice_line_ids.quantity = 3
        invoice.action_post()

        self.assertEqual(
            so.amount_taxinc_to_invoice, 180.0, "The amount to invoice should be 180.0"
        )

    def test_invoice_line_name_has_product_name(self):
        so = self.sale_order

        so.line_ids[1].product_id = so.line_ids[0].product_id
        so.line_ids[3].product_id = so.line_ids[2].product_id

        so.line_ids[0].name = "just a description"
        so.line_ids[1].name = so.line_ids[1].product_id.display_name
        so.line_ids[
            2
        ].name = f"{so.line_ids[2].product_id.display_name} with more description"
        so.line_ids[3].name = "product"

        so.action_confirm()
        inv = self.sale_order._create_invoices()

        self.assertEqual(
            inv.invoice_line_ids[0].name,
            f"{so.line_ids[0].product_id.display_name}\n{so.line_ids[0].name}",
            "When the description doesn't contain the product name, it should be added to the invoice line name",
        )
        self.assertEqual(
            inv.invoice_line_ids[1].name,
            f"{so.line_ids[1].name}",
            "When the description is the product name, the invoice line name should only be the description",
        )
        self.assertEqual(
            inv.invoice_line_ids[2].name,
            f"{so.line_ids[2].name}",
            "When description contains the product name, the invoice line name should only be the description",
        )
        self.assertEqual(
            inv.invoice_line_ids[3].name,
            f"{so.line_ids[3].product_id.display_name}\n{so.line_ids[3].name}",
            "When the product name contains the description, the invoice line name should contain the product name and the description",
        )

    def test_credit_note_automatic_matching(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.company_data[
                                "product_service_delivery"
                            ].id,
                        }
                    ),
                ],
            }
        )
        sale_order.action_confirm()

        sale_order.line_ids.qty_transferred = 1

        invoice = sale_order._create_invoices()
        invoice.action_post()

        sale_order.line_ids.qty_transferred = 0

        with patch.object(
            self.env.registry["account.move"],
            "_refunds_origin_required",
            lambda move: True,
        ):
            wizard_context = {
                "active_model": "sale.order",
                "active_id": sale_order.id,
            }
            credit_note = (
                self.env["sale.advance.payment.inv"]
                .with_context(wizard_context)
                .create({})
                ._create_invoices(sale_order)
            )
        credit_note.action_post()

        self.assertEqual(credit_note.reversed_entry_id.id, invoice.id)

    def test_credit_note_no_automatic_matching(self):
        product = self.company_data["product_service_delivery"]

        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
            }
        )
        sale_line1 = self.env["sale.order.line"].create(
            {
                "product_id": product.id,
                "product_qty": 1,
                "price_unit": 200.0,
                "order_id": sale_order.id,
            }
        )
        sale_line2 = self.env["sale.order.line"].create(
            {
                "product_id": product.id,
                "product_qty": 1,
                "price_unit": 100.0,
                "order_id": sale_order.id,
            }
        )
        sale_order.action_confirm()

        sale_line1.qty_transferred = 1

        invoice = sale_order._create_invoices()
        invoice.action_post()

        sale_line2.qty_transferred = 1
        sale_line1.qty_transferred = 0

        with patch.object(
            self.env.registry["account.move"],
            "_refunds_origin_required",
            lambda move: True,
        ):
            wizard_context = {
                "active_model": "sale.order",
                "active_id": sale_order.id,
            }
            credit_note = (
                self.env["sale.advance.payment.inv"]
                .with_context(wizard_context)
                .create({})
                ._create_invoices(sale_order)
            )
        credit_note.action_post()

        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(len(credit_note.invoice_line_ids), 2)
        self.assertFalse(credit_note.reversed_entry_id)

    def test_invoice_from_order_without_lines(self):
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 1,
                        }
                    )
                ],
            }
        )
        sale_order.action_confirm()
        wizard = (
            self.env["sale.advance.payment.inv"]
            .with_context(
                {
                    "active_model": "sale.order",
                    "active_ids": [sale_order.id],
                    "active_id": sale_order.id,
                    "default_journal_id": self.company_data["default_journal_sale"].id,
                }
            )
            .create(
                {
                    "advance_payment_method": "percentage",
                    "amount": 10,
                }
            )
        )
        action_values = wizard.create_invoices()

        invoice = self.env["account.move"].browse(action_values["res_id"])
        self.assertTrue(invoice)
        self.assertEqual(invoice.partner_id, sale_order.partner_id)

    def test_view_draft_invoices_domain(self):
        wizard = (
            self.env["sale.advance.payment.inv"].with_context(self.context).create({})
        )
        action = wizard.view_draft_invoices()
        self.env["account.move"].search(action["domain"])

    def test_downpayment_storno(self):
        def create_so_with_downpayments():
            sale_order = self.env["sale.order"].create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.company_data[
                                    "product_delivery_no"
                                ].id,
                                "product_qty": 20,
                                "price_unit": 30,
                            }
                        ),
                    ],
                }
            )
            sale_order.action_confirm()
            sale_order.line_ids[0].qty_transferred = 20

            downpayment = self.env["sale.advance.payment.inv"].create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 50,
                    "sale_order_ids": sale_order,
                }
            )
            downpayment.create_invoices()
            downpayment2 = self.env["sale.advance.payment.inv"].create(
                {
                    "advance_payment_method": "fixed",
                    "fixed_amount": 50,
                    "sale_order_ids": sale_order,
                }
            )
            downpayment2.create_invoices()

            self.assertEqual(
                len(sale_order.invoice_ids), 2, "Invoices should be created for the SO"
            )
            for invoice in sale_order.invoice_ids:
                self.assertEqual(
                    len(invoice.line_ids),
                    2,
                    "Downpayment invoice line should be created",
                )
                self.assertRecordValues(
                    invoice.line_ids,
                    [
                        {
                            "debit": 0,
                            "credit": 50,
                            "balance": -50,
                            "is_downpayment": True,
                            "account_type": "income",
                            "display_type": "product",
                        },
                        {
                            "debit": 50,
                            "credit": 0,
                            "balance": 50,
                            "is_downpayment": False,
                            "account_type": "asset_receivable",
                            "display_type": "payment_term",
                        },
                    ],
                )

            sale_order.invoice_ids.action_post()

            payment = self.env["sale.advance.payment.inv"].create(
                {
                    "sale_order_ids": sale_order,
                }
            )
            payment.create_invoices()
            sale_order.invoice_ids.sorted(key=lambda x: x.id)[-1].action_post()

            self.assertEqual(
                len(sale_order.invoice_ids), 3, "Invoice should be created for the SO"
            )
            return sale_order

        sale_order_no_storno = create_so_with_downpayments()
        invoice_no_storno = sale_order_no_storno.invoice_ids.sorted(key=lambda x: x.id)[
            -1
        ]
        self.assertEqual(
            len(invoice_no_storno.line_ids), 5, "Invoice line should be created"
        )
        self.assertRecordValues(
            invoice_no_storno.line_ids,
            [
                {
                    "debit": 0,
                    "credit": 600.0,
                    "balance": -600.0,
                    "is_downpayment": False,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 0,
                    "credit": 0,
                    "balance": 0,
                    "is_downpayment": False,
                    "account_type": False,
                    "display_type": "line_section",
                },
                {
                    "debit": 50.0,
                    "credit": 0,
                    "balance": 50.0,
                    "is_downpayment": True,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 50.0,
                    "credit": 0,
                    "balance": 50.0,
                    "is_downpayment": True,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 500.0,
                    "credit": 0,
                    "balance": 500.0,
                    "is_downpayment": False,
                    "account_type": "asset_receivable",
                    "display_type": "payment_term",
                },
            ],
        )

        self.env.company.account_config_id.account_storno = True
        sale_order_storno = create_so_with_downpayments()
        invoice_storno = sale_order_storno.invoice_ids.sorted(key=lambda x: x.id)[-1]
        self.assertEqual(
            len(invoice_storno.line_ids), 5, "Invoice line should be created"
        )
        self.assertRecordValues(
            invoice_storno.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 600.0,
                    "balance": -600.0,
                    "is_downpayment": False,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "balance": 0.0,
                    "is_downpayment": False,
                    "account_type": False,
                    "display_type": "line_section",
                },
                {
                    "debit": 0.0,
                    "credit": -50.0,
                    "balance": 50.0,
                    "is_downpayment": True,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 0.0,
                    "credit": -50.0,
                    "balance": 50.0,
                    "is_downpayment": True,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 500.0,
                    "credit": 0.0,
                    "balance": 500.0,
                    "is_downpayment": False,
                    "account_type": "asset_receivable",
                    "display_type": "payment_term",
                },
            ],
        )

    def test_negative_amount_storno(self):
        def create_sale_order_with_negative_amount():
            sale_order = self.env["sale.order"].create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.company_data[
                                    "product_delivery_no"
                                ].id,
                                "product_qty": 20,
                                "price_unit": 30,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.company_data[
                                    "product_delivery_no"
                                ].id,
                                "product_qty": 5,
                                "price_unit": -10,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.company_data[
                                    "product_delivery_no"
                                ].id,
                                "product_qty": -5,
                                "price_unit": 20,
                            }
                        ),
                    ],
                }
            )
            sale_order.action_confirm()
            sale_order.line_ids[0].qty_transferred = 20
            sale_order.line_ids[1].qty_transferred = 5
            sale_order.line_ids[2].qty_transferred = -5

            payment = self.env["sale.advance.payment.inv"].create(
                {
                    "sale_order_ids": sale_order,
                }
            )
            payment.create_invoices()
            sale_order.invoice_ids.action_post()

            self.assertEqual(
                len(sale_order.invoice_ids), 1, "Invoice should be created for the SO"
            )
            return sale_order

        sale_order_no_storno = create_sale_order_with_negative_amount()
        invoice_no_storno = sale_order_no_storno.invoice_ids
        self.assertEqual(
            len(invoice_no_storno.line_ids), 4, "Invoice line should be created"
        )
        self.assertRecordValues(
            invoice_no_storno.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 600.0,
                    "balance": -600.0,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 50.0,
                    "credit": 0.0,
                    "balance": 50.0,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 100.0,
                    "credit": 0.0,
                    "balance": 100.0,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 450.0,
                    "credit": 0.0,
                    "balance": 450.0,
                    "account_type": "asset_receivable",
                    "display_type": "payment_term",
                },
            ],
        )

        self.env.company.account_config_id.account_storno = True
        sale_order_storno = create_sale_order_with_negative_amount()
        invoice_storno = sale_order_storno.invoice_ids
        self.assertEqual(
            len(invoice_storno.line_ids), 4, "Invoice line should be created"
        )
        self.assertRecordValues(
            invoice_storno.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 600.0,
                    "balance": -600.0,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 0.0,
                    "credit": -50.0,
                    "balance": 50.0,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 0.0,
                    "credit": -100.0,
                    "balance": 100.0,
                    "account_type": "income",
                    "display_type": "product",
                },
                {
                    "debit": 450.0,
                    "credit": 0.0,
                    "balance": 450.0,
                    "account_type": "asset_receivable",
                    "display_type": "payment_term",
                },
            ],
        )
