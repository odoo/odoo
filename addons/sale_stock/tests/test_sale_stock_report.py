# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests.common import Form
from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestSaleStockReports(TestReportsCommon):
    def test_report_forecast_1_sale_order_replenishment(self):
        """ Create and confirm two sale orders: one for the next week and one
        for tomorrow. Then check in the report it's the most urgent who is
        linked to the qty. on stock.
        """
        today = datetime.today()
        # Put some quantity in stock.
        quant_vals = {
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'location_id': self.stock_location.id,
            'quantity': 5,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(quant_vals)
        # Create a first SO for the next week.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        # so_form.validity_date = today + timedelta(days=7)
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so_1 = so_form.save()
        so_1.action_confirm()
        so_1.picking_ids.scheduled_date = today + timedelta(days=7)

        # Create a second SO for tomorrow.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        # so_form.validity_date = today + timedelta(days=1)
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so_2 = so_form.save()
        so_2.action_confirm()
        so_2.picking_ids.scheduled_date = today + timedelta(days=1)

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 2)
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1['quantity'], 5)
        self.assertTrue(line_1['replenishment_filled'])
        self.assertEqual(line_1['document_out'].id, so_2.id)
        self.assertEqual(line_2['quantity'], 5)
        self.assertEqual(line_2['replenishment_filled'], False)
        self.assertEqual(line_2['document_out'].id, so_1.id)
