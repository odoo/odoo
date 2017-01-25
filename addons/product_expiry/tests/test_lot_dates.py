# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestLotDates(TransactionCase):

    def test_00_lot_dates(self):

        # locations
        location_id = self.ref('stock.stock_location_suppliers')
        location_dest_id = self.ref('stock.stock_location_stock')
        # life_date is 10 days later from today
        life_date = datetime.today() + timedelta(days=10)
        product_life_time = 7
        product_use_time = 5
        product_removal_time = 8
        product_alert_time = 6

        # create a product with lot tracking and expiry days
        productA = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'uom_id': self.ref('product.product_uom_unit'),
            'tracking': 'lot',
            'life_time': product_life_time,
            'use_time': product_use_time,
            'removal_time': product_removal_time,
            'alert_time': product_alert_time})

        # create a incoming picking
        picking_in = self.env['stock.picking'].create({
            'partner_id': self.ref('base.res_partner_4'),
            'picking_type_id': self.ref('stock.picking_type_in'),
            'location_id': location_id,
            'location_dest_id': location_dest_id})

        # create a move for picking
        self.env['stock.move'].create({
            'name': productA.name,
            'product_id': productA.id,
            'product_uom_qty': 1,
            'product_uom': productA.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id})

        # confirm incoming picking
        picking_in.action_confirm()

        # create stock pack operation lot
        self.env['stock.pack.operation.lot'].create({
            'lot_name': 'Lot A',
            'qty': 1,
            'life_date': fields.Datetime.to_string(life_date),
            'operation_id': picking_in.pack_operation_product_ids.ids[0]})

        # need to change done qty of stock pack operation
        picking_in.pack_operation_product_ids.write({'qty_done': 1})

        # validate picking
        picking_in.do_new_transfer()

        # get newly created lot
        incoming_lot = picking_in.pack_operation_product_ids.pack_lot_ids.lot_id

        # calculate date for tests, op_date is life_date - product's life time
        op_date = life_date - timedelta(days=product_life_time)
        use_date = fields.Datetime.to_string(op_date + timedelta(days=product_use_time))
        alert_date = fields.Datetime.to_string(op_date + timedelta(days=product_alert_time))
        removal_date = fields.Datetime.to_string(op_date + timedelta(days=product_removal_time))

        # test lot's dates
        self.assertEqual(incoming_lot.life_date, fields.Datetime.to_string(life_date), "Lot's Life Date is incorrect.")
        self.assertEqual(incoming_lot.use_date, use_date, "Lot's Use Date is incorrect.")
        self.assertEqual(incoming_lot.alert_date, alert_date, "Lot's Alert Date is incorrect.")
        self.assertEqual(incoming_lot.removal_date, removal_date, "Lot's Removal Date is incorrect.")
