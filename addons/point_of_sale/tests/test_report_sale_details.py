# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportSaleDetails(TestPoSCommon):

    def setUp(self):
        super(TestReportSaleDetails, self).setUp()
        self.config = self.basic_config

    def test_get_sale_details(self):
        # Check if the get report details function works without any errors
        try:
            report = self.env['report.point_of_sale.report_saledetails']
            report._get_report_values(None, None)
        except Exception:
            self.fail('Get Report Details function failed to execute properly.')
