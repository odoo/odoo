# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os

from odoo.tests.common import tagged, TransactionCase
from .common import TestAccountTaxcloudCommon


@tagged("external")
class TestAccountTaxcloud(TestAccountTaxcloudCommon):
    def test_01_taxcloud_tax_rate_on_invoice(self):
        """Test TaxRate Returned from taxcloud assign on invoice line"""
        # Create Invoice
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "fiscal_position_id": self.fiscal_position.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "tax_ids": None,
                            "price_unit": self.product.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_1.id,
                            "tax_ids": None,
                            "price_unit": self.product_1.list_price,
                        },
                    ),
                ],
            }
        )

        for line in invoice.invoice_line_ids:
            self.assertEqual(
                len(line.tax_ids), 0, "There should be no tax rate on the line."
            )

        invoice.action_post()

        for line in invoice.invoice_line_ids:
            self.assertEqual(
                len(line.tax_ids),
                1,
                "Taxcloud should have generated a unique tax rate for the line.",
            )
