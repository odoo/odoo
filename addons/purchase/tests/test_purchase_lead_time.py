# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from .common import TestPurchase


class TestPurchaseLeadTime(TestPurchase):

    def test_00_product_company_level_delays(self):
        """ To check dates, set product's Delivery Lead Time
            and company's Purchase Lead Time."""

        company = self.env.ref('base.main_company')

        # Update company with Purchase Lead Time
        company.write({'po_lead': 3.00})

        # Make procurement request from product_1's form view, create procurement and check it's state
        procurement_product_1 = self._create_make_procurement(self.product_1, 15.00)
        procurement_act_dict = procurement_product_1.make_procurement()
        procurement = self.env['procurement.order'].browse(procurement_act_dict.get("res_id"))
        self.assertEqual(procurement.state, 'running', 'Procurement should be in running state.')

        # Confirm purchase order
        procurement.purchase_id.button_confirm()

        # Check order date of purchase order
        order_date = fields.Datetime.from_string(procurement.date_planned) - timedelta(days=company.po_lead) - timedelta(days=self.product_1.seller_ids.delay)
        po_order_date = fields.Datetime.to_string(order_date)
        self.assertEqual(procurement.purchase_id.date_order, po_order_date, 'Order date should be equal to: Date of the procurement order - Purchase Lead Time - Delivery Lead Time.')

        # Check scheduled date of purchase order
        schedule_date = order_date + timedelta(days=self.product_1.seller_ids.delay)
        po_schedule_date = fields.Datetime.to_string(schedule_date)
        self.assertEqual(procurement.purchase_id.date_planned, po_schedule_date, 'Schedule date should be equal to: Order date of Purchase order + Delivery Lead Time.')

        # check the picking created or not
        self.assertTrue(procurement.purchase_id.picking_ids, "Picking should be created.")

        # Check scheduled date of In Type shipment
        self.assertEqual(procurement.purchase_id.picking_ids.scheduled_date, po_schedule_date, 'Schedule date of In type shipment should be equal to: schedule date of purchase order.')

    def test_01_product_level_delay(self):
        """ To check schedule dates of multiple purchase order line of the same purchase order,
            we create two procurements for the two different product with same vendor
            and different Delivery Lead Time."""

        # Make procurement request from product_1's form view, create procurement and check it's state
        procurement_product_1 = self._create_make_procurement(self.product_1, 10.00)
        procurement_act_dict = procurement_product_1.make_procurement()
        procurement_1 = self.env['procurement.order'].browse(procurement_act_dict.get("res_id"))
        self.assertEqual(procurement_1.state, 'running', 'Procurement of product_1 should be in running state.')

        # Make procurement request from product_2's form view, create procurement and check it's state
        procurement_product_2 = self._create_make_procurement(self.product_2, 5.00)
        procurement_act_dict_2 = procurement_product_2.make_procurement()
        procurement_2 = self.env['procurement.order'].browse(procurement_act_dict_2.get("res_id"))
        self.assertEqual(procurement_2.state, 'running', 'Procurement of product_2 should be in running state.')

        # Check purchase order is same or not
        self.assertEqual(procurement_1.purchase_id, procurement_2.purchase_id, 'Purchase orders should be same for the two different product with same vendor.')

        # Confirm purchase order
        procurement_2.purchase_id.button_confirm()

        # Check order date of purchase order
        order_line_pro_1 = procurement_2.purchase_id.order_line.filtered(lambda r: r.product_id == self.product_1)
        order_line_pro_2 = procurement_2.purchase_id.order_line.filtered(lambda r: r.product_id == self.product_2)
        order_date = fields.Datetime.from_string(procurement_1.date_planned) - timedelta(days=self.product_1.seller_ids.delay)
        po_order_date = fields.Datetime.to_string(order_date)
        self.assertEqual(procurement_2.purchase_id.date_order, po_order_date, 'Order date should be equal to: Date of the procurement order - Delivery Lead Time.')

        # Check scheduled date of purchase order line for product_1
        schedule_date_1 = order_date + timedelta(days=self.product_1.seller_ids.delay)
        schedule_date_line_1 = fields.Datetime.to_string(schedule_date_1)
        self.assertEqual(order_line_pro_1.date_planned, schedule_date_line_1, 'Schedule date of purchase order line for product_1 should be equal to: Order date of purchase order + Delivery Lead Time of product_1.')

        # Check scheduled date of purchase order line for product_2
        schedule_date_2 = order_date + timedelta(days=self.product_2.seller_ids.delay)
        schedule_date_line_2 = fields.Datetime.to_string(schedule_date_2)
        self.assertEqual(order_line_pro_2.date_planned, schedule_date_line_2, 'Schedule date of purchase order line for product_2 should be equal to: Order date of purchase order + Delivery Lead Time of product_2.')

        # Check scheduled date of purchase order
        po_schedule_date = min(schedule_date_line_1, schedule_date_line_2)
        self.assertEqual(procurement_2.purchase_id.date_planned, po_schedule_date, 'Schedule date of purchase order should be minimum of schedule dates of purchase order lines.')

        # Check the picking crated or not
        self.assertTrue(procurement_2.purchase_id.picking_ids, "Picking should be created.")

        # Check scheduled date of In Type shipment
        self.assertEqual(procurement_2.purchase_id.picking_ids.scheduled_date, po_schedule_date, 'Schedule date of In type shipment should be same as schedule date of purchase order.')

    def test_02_product_route_level_delays(self):
        """ In order to check dates, set product's Delivery Lead Time
            and warehouse route's delay."""

        # Update warehouse_1 with Incoming Shipments 3 steps
        self.warehouse_1.write({'reception_steps': 'three_steps'})

        # Set delay on push rule
        for push_rule in self.warehouse_1.reception_route_id.push_ids:
            push_rule.write({'delay': 2})

        # Create procurement order of product_1
        procurement = self.env['procurement.order'].create({
            'product_id': self.product_1.id,
            'product_qty': 5.000,
            'name': 'Test scheduler for RFQ',
            'product_uom': self.uom_unit.id,
            'warehouse_id': self.warehouse_1.id,
            'location_id': self.warehouse_1.lot_stock_id.id,
            'date_planned': fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10)),  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
            'rule_id': self.warehouse_1.buy_pull_id.id
        })

        # Confirm purchase order
        procurement.purchase_id.button_confirm()

        # Check order date of purchase order
        order_date = fields.Datetime.from_string(procurement.date_planned) - timedelta(days=self.product_1.seller_ids.delay)
        po_order_date = fields.Datetime.to_string(order_date)
        self.assertEqual(procurement.purchase_id.date_order, po_order_date, 'Order date should be equal to: Date of the procurement order - Delivery Lead Time.')

        # Check scheduled date of purchase order
        schedule_date = order_date + timedelta(days=self.product_1.seller_ids.delay)
        po_schedule_date = fields.Datetime.to_string(schedule_date)
        self.assertEqual(procurement.date_planned, po_schedule_date, 'Schedule date should be equal to: Order date of Purchase order + Delivery Lead Time.')

        # Check the picking crated or not
        self.assertTrue(procurement.purchase_id.picking_ids, "Picking should be created.")

        # Check scheduled date of In Type shipment
        incomming_shipment = procurement.purchase_id.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.in_type_id and r.location_dest_id == self.warehouse_1.wh_input_stock_loc_id)
        self.assertEqual(incomming_shipment.scheduled_date, po_schedule_date, 'Schedule date of In type shipment should be same as schedule date of purchase order.')

        # Check scheduled date of Internal Type shipment
        incomming_shipment1 = self.env['stock.picking'].search([('picking_type_id', '=', self.warehouse_1.int_type_id.id), ('location_id', '=', self.warehouse_1.wh_input_stock_loc_id.id), ('location_dest_id', '=', self.warehouse_1.wh_qc_stock_loc_id.id)])
        incomming_shipment1_date = schedule_date + timedelta(days=incomming_shipment1.move_lines[0].push_rule_id.delay)
        incomming_shipment1_schedule_date = fields.Datetime.to_string(incomming_shipment1_date)
        self.assertEqual(incomming_shipment1.scheduled_date, incomming_shipment1_schedule_date, 'Schedule date of Internal Type shipment for input stock location should be equal to: schedule date of purchase order + push rule delay.')

        incomming_shipment2 = self.env['stock.picking'].search([('picking_type_id', '=', self.warehouse_1.int_type_id.id), ('location_id', '=', self.warehouse_1.wh_qc_stock_loc_id.id), ('location_dest_id', '=', self.warehouse_1.lot_stock_id.id)])
        incomming_shipment2_date = incomming_shipment1_date + timedelta(days=incomming_shipment2.move_lines[0].push_rule_id.delay)
        incomming_shipment2_schedule_date = fields.Datetime.to_string(incomming_shipment2_date)
        self.assertEqual(incomming_shipment2.scheduled_date, incomming_shipment2_schedule_date, 'Schedule date of Internal Type shipment for quality control stock location should be equal to: schedule date of Internal type shipment for input stock location + push rule delay..')
