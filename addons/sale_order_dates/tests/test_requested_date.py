# -*- coding: utf-8 -*-
from datetime import timedelta
from openerp import fields
from openerp.addons.sale_order_dates.tests.common import TestSaleOrderDatesCommon


class TestSaleOrderDates(TestSaleOrderDatesCommon):
    def test_sale_order_requested_date(self):

        #In order to test the Requested Date feature in Sale Orders in Odoo,
        #I update a demo Sale Order with Requested Date on 2010-12-17
        self.sale_order.write({'requested_date': '2010-07-12'})
        self.sale_order.order_line.write({'product_uom_qty': 4})
        #I confirm the Sale Order.
        self.sale_order.action_confirm()
        #I verify that the Procurements and Stock Moves have been generated with the
        #correct date
        security_delay = timedelta(days=self.sale_order.company_id.security_lead)
        requested_date = fields.Datetime.from_string(self.sale_order.requested_date)
        right_date = fields.Datetime.to_string(requested_date - security_delay)
        for line in self.sale_order.order_line:
            self.assertTrue(line.procurement_ids, "Procurement should be created")
            self.assertEqual(line.procurement_ids[0].date_planned, right_date, "The planned date for the Procurement Order is wrong")
            self.assertTrue(line.procurement_ids[0].move_ids, "No Move ids")
            self.assertEqual(line.procurement_ids[0].move_ids[0].date_expected, right_date, "The expected date for the Stock Move is wrong")
