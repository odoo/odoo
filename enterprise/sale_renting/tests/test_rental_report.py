# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo.tests import tagged

from .common import SaleRentingCommon


@tagged('post_install', '-at_install')
class TestRentalReport(SaleRentingCommon):

    def test_5_days_rental_generates_5_rows_with_5_dates(self):
        """Test that a rental order of 5 days generates 5 rows, with 5 dates."""
        rental_order = self._create_rental_order(days=5)  # 5 days from 00h00 to 23h59m59
        report_lines = self.env['sale.rental.report'].search(
            [('order_id', '=', rental_order.id)]
        )
        self.assertEqual(len(report_lines), 5, "The report should have 5 rows")
        # Verify dates
        report_dates = [line.date.date() for line in report_lines]
        rental_dates = [
            (rental_order.rental_start_date.date() + timedelta(days=i)) for i in range(5)
        ]
        self.assertEqual(report_dates, rental_dates, "Report dates should match rental dates.")
        # Verify product and price
        for line in report_lines:
            self.assertEqual(line.product_id.id, rental_order.order_line.product_id.id)
            self.assertEqual(line.price, rental_order.order_line.price_unit / 5)
