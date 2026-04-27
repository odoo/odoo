from datetime import timedelta

from odoo.fields import Command, Datetime
from odoo.tests import tagged

from odoo.addons.sale_stock_renting.tests.test_rental_common import TestRentalCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestRentalInvoicing(TestRentalCommon, AccountTestInvoicingCommon):

    def test_no_cogs_for_rental_invoice_anglo_saxon(self):
        """Ensure no COGS or inventory valuation journal entries are created for rental products in Anglo-Saxon mode."""

        # Setup: Anglo-Saxon mode and real-time inventory valuation
        self.env.company.anglo_saxon_accounting = True
        self.product_id.categ_id.property_valuation = 'real_time'
        self.product_id.standard_price = 100.0

        sale_order = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.now(),
            'rental_return_date': Datetime.now() + timedelta(days=3),
            'order_line': [
                Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 2,
                    'price_unit': 1000.0,
                    'is_rental': True,
                }),
                Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 1,
                    'price_unit': 1000.0,
                }),
            ],
        })

        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()

        # Get the invoice lines
        rental_lines = invoice.line_ids.filtered(lambda l: any(sl.is_rental for sl in l.sale_line_ids))
        non_rental_lines = invoice.line_ids.filtered(lambda l: all(not sl.is_rental for sl in l.sale_line_ids))

        # Fetch valuation-related journal lines from the invoice's journal entry
        move_lines = invoice.line_ids
        valuation_account_ids = {
            self.product_id.categ_id.property_stock_valuation_account_id.id,
            self.product_id.categ_id.property_account_expense_categ_id.id,
        }

        valuation_lines = move_lines.filtered(lambda l: l.account_id.id in valuation_account_ids)

        # Check: No valuation entries tied to rental lines
        for rental_line in rental_lines:
            self.assertFalse(
                valuation_lines.filtered(lambda l: l.cogs_origin_id == rental_line),
                "Rental invoice line should not generate COGS or inventory valuation journal entries."
            )

        # Check: Non-rental line should generate valuation
        self.assertTrue(
            valuation_lines.filtered(lambda l: l.cogs_origin_id == non_rental_lines[0]),
            "Non-rental invoice line should generate COGS or valuation entry."
        )
