# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.exceptions import UserError


class TestStockProductionLot(TestStockCommon):

    def test_00_stock_production_lot(self):
        """ Test Scheduled Task on lot with an alert_date in the past creates an activity """

        # create product 
        self.productAAA = self.ProductObj.create({
            'name': 'Product AAA',
            'type': 'product',
            'tracking':'lot'
        })

        # create a new lot with with alert date in the past
        self.lot1_productAAA = self.LotObj.create({
            'name': 'Lot 1 ProductAAA',
            'product_id': self.productAAA.id,
            'alert_date': fields.Date.to_string(datetime.today() - relativedelta(days=15))
        })

        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })

        move_a = self.MoveObj.create({
            'name': self.productAAA.name,
            'product_id': self.productAAA.id,
            'product_uom_qty': 33,
            'product_uom': self.productAAA.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })
        
        self.assertEqual(picking_in.move_lines.state, 'draft', 'Wrong state of move line.')
        picking_in.action_confirm()
        self.assertEqual(picking_in.move_lines.state, 'assigned', 'Wrong state of move line.')

        # Replace pack operation of incoming shipments.
        picking_in.action_assign()
        move_a.move_line_ids.qty_done = 33
        move_a.move_line_ids.lot_id = self.lot1_productAAA.id

        # Transfer Incoming Shipment.
        picking_in.action_done()

        # run scheduled tasks
        self.env['stock.production.lot']._alert_date_exceeded()

        # check a new activity has been created
        activity_id = self.env.ref('product_expiry.mail_activity_type_alert_date_reached').id
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 1, 'No activity created while there should be one')

        # run the scheduler a second time
        self.env['stock.production.lot']._alert_date_exceeded()

        # check there is still only one activity, no additional activity is created if there is already an existing activity
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 1, 'There should be one and only one activity')

        # mark the activity as done
        mail_activity = self.env['mail.activity'].search([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        mail_activity.action_done()

        # check there is no more activity (because it is already done)
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 0,"As activity is done, there shouldn't be any related activity")
                
        # run the scheduler a third time
        self.env['stock.production.lot']._alert_date_exceeded()

        # check there is no activity created
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=',self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 0, "As there is already an activity marked as done, there shouldn't be any related activity created for this lot")


    def test_01_stock_production_lot(self):
        """ Test Scheduled Task on lot with an alert_date in future does not create an activity """

        # create product 
        self.productBBB = self.ProductObj.create({
            'name': 'Product BBB', 
            'type': 'product',
            'tracking':'lot'
        })

        # create a new lot with with alert date in the past
        self.lot1_productBBB = self.LotObj.create({
            'name': 'Lot 1 ProductBBB',
            'product_id': self.productBBB.id,
            'alert_date': fields.Date.to_string(datetime.today() + relativedelta(days=15))
        })

        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        move_b = self.MoveObj.create({
            'name': self.productBBB.name,
            'product_id': self.productBBB.id,
            'product_uom_qty': 44,
            'product_uom': self.productBBB.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        
        self.assertEqual(picking_in.move_lines.state, 'draft', 'Wrong state of move line.')
        picking_in.action_confirm()
        self.assertEqual(picking_in.move_lines.state, 'assigned', 'Wrong state of move line.')

        # Replace pack operation of incoming shipments.
        picking_in.action_assign()
        move_b.move_line_ids.qty_done = 44
        move_b.move_line_ids.lot_id = self.lot1_productBBB.id

        # Transfer Incoming Shipment.
        picking_in.action_done()

        # run scheduled tasks
        self.env['stock.production.lot']._alert_date_exceeded()

        # check a new activity has not been created
        activity_id = self.env.ref('product_expiry.mail_activity_type_alert_date_reached').id
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productBBB.id)
        ])
        self.assertEqual(activity_count, 0, "An activity has been created while it shouldn't")


    def test_02_stock_production_lot(self):
        """ Test Scheduled Task on lot without an alert_date does not create an activity """

        # create product 
        self.productCCC = self.ProductObj.create({'name': 'Product CCC', 'type': 'product', 'tracking':'lot'})

        # create a new lot with with alert date in the past
        self.lot1_productCCC = self.LotObj.create({'name': 'Lot 1 ProductCCC', 'product_id': self.productCCC.id})

        picking_in = self.PickingObj.create({
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        move_c = self.MoveObj.create({
            'name': self.productCCC.name,
            'product_id': self.productCCC.id,
            'product_uom_qty': 44,
            'product_uom': self.productCCC.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        
        self.assertEqual(picking_in.move_lines.state, 'draft', 'Wrong state of move line.')
        picking_in.action_confirm()
        self.assertEqual(picking_in.move_lines.state, 'assigned', 'Wrong state of move line.')

        # Replace pack operation of incoming shipments.
        picking_in.action_assign()
        move_c.move_line_ids.qty_done = 55
        move_c.move_line_ids.lot_id = self.lot1_productCCC.id

        # Transfer Incoming Shipment.
        picking_in.action_done()

        # run scheduled tasks
        self.env['stock.production.lot']._alert_date_exceeded()

        # check a new activity has not been created
        activity_id = self.env.ref('product_expiry.mail_activity_type_alert_date_reached').id
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productCCC.id)
        ])
        self.assertEqual(activity_count, 0, "An activity has been created while it shouldn't")
