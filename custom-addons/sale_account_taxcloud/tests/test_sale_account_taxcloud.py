# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_taxcloud.tests.common import TestAccountTaxcloudCommon
from odoo.tests.common import tagged


@tagged("external")
class TestSaleAccountTaxCloud(TestAccountTaxcloudCommon):
    def test_01_taxcloud_full_flow(self):
        """ Test a full sales flow: SO, validation, downpayment, invoice, payment"""
        # Create Sale Order
        sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "fiscal_position_id": self.fiscal_position.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "tax_id": None,})
                ],
            }
        )

        # Get the tax from Taxcloud
        sale_order.validate_taxes_on_sales_order()

        # Check if a tax was created based on the create_date in the test transaction
        # Note: this means this test can only be run once, further test will fail
        # since the tax will have been created previously
        self.env.cr.execute(
            "SELECT id FROM account_tax WHERE create_date=now() at time zone 'UTC'"
        )
        tax_ids = self.env.cr.fetchone()
        self.assertNotEqual(
            len(tax_ids), 0, "At least one tax rate should have been created"
        )
        tax_id = tax_ids[0]
        tax = self.env["account.tax"].browse(tax_id)

        # add another line
        sale_order.write(
            {"order_line": [(0, 0, {"product_id": self.product_1.id, "tax_id": None,})]}
        )

        # Test Sale Order Confirmation triggres a Tax Update.
        # Confirm Sale Order and get the all tax values
        sale_order.action_confirm()
        # The same tax should have be re-fetched from db.
        # This check might fail due to rounding issue.
        # When called, TaxCloud is returning the tax amount for each line.
        # This tax amount depends on many factors like the category of the product and the address of the customer.
        # When we receive a response from TaxCloud, we compute the tax rate with this formula: (tax_amount / price * 100)
        # If no tax exists with that tax rate, the tax is created. Otherwise, it is reused.
        # Depending on the address and the price, it is possible that the computation of the tax rate for the 2 lines
        # is slightly different (like 8.225% for the first line and 8.230% for the second one, for example).
        # In that case, a second tax is created for the second SO line, making this assert fail.
        self.assertEqual(
            sale_order.order_line.tax_id, tax, "Tax should be taken from DB."
        )
        # create downpayment
        payment_ctx = {
            "active_model": "sale.order",
            "active_ids": [sale_order.id],
            "active_id": sale_order.id,
            "default_journal_id": self.journal.id,
        }
        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(**payment_ctx)
            .create({"advance_payment_method": "fixed", "fixed_amount": 100,})
        )
        payment.create_invoices()
        # the deposit product should have the 'Gift Card' category
        downpayment_invoice = sale_order.invoice_ids
        downpayment_product = downpayment_invoice.invoice_line_ids.product_id
        self.assertEqual(
            downpayment_product.tic_category_id.code,
            10005,
            "Downpayment product should have the 'Gift Card' TIC",
        )
        self.assertEqual(
            downpayment_invoice.invoice_line_ids.tax_ids, tax, "Tax on the downpayment should be the same than on the SO."
        )
        downpayment_tax_amount = downpayment_invoice.amount_tax
        downpayment_invoice.action_post()
        self.assertEqual(
            downpayment_invoice.amount_tax,
            downpayment_tax_amount,
            "Posting a downpayment should not recompute the taxes.",
        )
        # create and post invoice, register payment
        payment = (
            self.env["sale.advance.payment.inv"]
            .with_context(**payment_ctx)
            .create({"advance_payment_method": "delivered",})
        )
        payment.create_invoices()
        invoice = sale_order.invoice_ids - downpayment_invoice
        invoice.action_post()

        payment = (
            self.env['account.payment.register']
            .with_context(active_model='account.move', active_ids=invoice.ids)
            .create({})
            ._create_payments()
        )
        self.assertEqual(payment.amount, 1101.75)
        self.assertEqual(payment.state, "posted")
        self.assertEqual(invoice.payment_state, "in_payment")

    def test_compute_taxes_on_send(self):
        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "fiscal_position_id": self.fiscal_position.id,
            "order_line": [
                (0, 0, {"product_id": self.product.id, "tax_id": None, })
            ],
        })

        for line in sale_order.order_line:
            self.assertEqual(len(line.tax_id), 0,
                             "There should be no tax rate on the line.")

        sale_order.action_quotation_send()

        for line in sale_order.order_line:
            self.assertEqual(len(line.tax_id), 1,
                             "Taxcloud should have generated a unique tax rate for the line.")

    def test_compute_taxes_on_mark_as_sent(self):
        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "fiscal_position_id": self.fiscal_position.id,
            "order_line": [
                (0, 0, {"product_id": self.product.id, "tax_id": None, })
            ],
        })

        for line in sale_order.order_line:
            self.assertEqual(len(line.tax_id), 0,
                             "There should be no tax rate on the line.")

        sale_order.action_quotation_sent()

        for line in sale_order.order_line:
            self.assertEqual(len(line.tax_id), 1,
                             "Taxcloud should have generated a unique tax rate for the line.")
