# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests import tagged

from .common import TestWebsiteSaleRentingCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install')
class TestWebsiteSaleRentingTimezone(TestWebsiteSaleRentingCommon):

    def test_1_month_computed(self):
        """Renting a month has to return a duration of 1 month, even when the timezone makes us
        switch month."""
        start_date = fields.Datetime.to_datetime("2025-11-30 23:00")  # 01/12/2025 00h00 (UTC+1)
        end_date = fields.Datetime.to_datetime("2025-12-31 22:59")  # 31/12/2025 23h59 (UTC+1)
        with MockRequest(self.env, website=self.website):
            vals = self.env['product.pricing']._compute_duration_vals(start_date, end_date)
            self.assertEqual(vals['month'], 1)
