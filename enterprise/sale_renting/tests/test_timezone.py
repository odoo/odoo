# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged

from .common import SaleRentingCommon


@tagged('post_install', '-at_install')
class TestSaleRentingTimezone(SaleRentingCommon):

    def test_1_month_computed(self):
        """Renting a month has to return a duration of 1 month, even when the timezone makes us
        switch month."""
        self.env.user.tz = "Europe/Brussels"
        start_date = fields.Datetime.to_datetime("2025-11-30 23:00")  # 01/12/2025 00h00 (UTC+1)
        end_date = fields.Datetime.to_datetime("2025-12-31 22:59")  # 31/12/2025 23h59 (UTC+1)
        vals = self.env['product.pricing']._compute_duration_vals(start_date, end_date)
        self.assertEqual(vals['month'], 1)
