#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase
from odoo import tools


class TestStockForecast(TransactionCase):

    def setUp(self):
        super(TestStockForecast, self).setUp()

        self.product_a = self.env['product.product'].create({'name': 'Product A', 'type': 'product'})
        self.wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.supplier = self.env['res.partner'].create({'name': 'Supplier', 'supplier': True})
        self.customer = self.env['res.partner'].create({'name': 'Customer', 'customer': True})

        self.date_day_1 = datetime.now()
        self.date_day_2 = self.date_day_1 + timedelta(days=1)
        self.view_stock_forecast = self.env.ref('stock.view_move_forecast_qweb')

    def test_reschedule_1(self):
        """ Check the behaviour of the 'Reschedule' function.
        """

        # Initial State :
        # ===============
        # Day 1 : Starting Stock = 10, OUT1 = -5, OUT2 = -5, OUT3 = -5
        # Day 2 : Starting Stock = 0, IN1 = +10, OUT4 = -5, OUT5 = -5

        # After reschedule :
        # ==================
        # When applying a reschedule, OUT3 should be moved to Day 2, but OUT5 should stay at Day 2
        # as there no more moves incoming after.

        # Setting up 'Day 1' stock state
        self.env['stock.quant']._update_available_quantity(self.product_a, self.wh.lot_stock_id, 10.0)
        moves_day_1 = self.env['stock.move'].create([
            {
                'name': 'OUT1',
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'product_uom': self.product_a.uom_id.id,
                'location_id': self.wh.lot_stock_id.id,
                'location_dest_id': self.customer.property_stock_customer.id,
                'date_expected': self.date_day_1
            }, {
                'name': 'OUT2',
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'product_uom': self.product_a.uom_id.id,
                'location_id': self.wh.lot_stock_id.id,
                'location_dest_id': self.customer.property_stock_customer.id,
                'date_expected': self.date_day_1
            }, {
                'name': 'OUT3',
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'product_uom': self.product_a.uom_id.id,
                'location_id': self.wh.lot_stock_id.id,
                'location_dest_id': self.customer.property_stock_customer.id,
                'date_expected': self.date_day_1
            }
        ])
        move_out_1 = moves_day_1[0]
        move_out_2 = moves_day_1[1]
        move_out_3 = moves_day_1[2]

        # Setting up 'Day 2' stock state
        moves_day_2 = self.env['stock.move'].create([
            {
                'name': 'IN1',
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom': self.product_a.uom_id.id,
                'location_id': self.customer.property_stock_supplier.id,
                'location_dest_id': self.wh.lot_stock_id.id,
                'date_expected': self.date_day_2
            }, {
                'name': 'OUT4',
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'product_uom': self.product_a.uom_id.id,
                'location_id': self.wh.lot_stock_id.id,
                'location_dest_id': self.customer.property_stock_customer.id,
                'date_expected': self.date_day_2
            }, {
                'name': 'OUT5',
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'product_uom': self.product_a.uom_id.id,
                'location_id': self.wh.lot_stock_id.id,
                'location_dest_id': self.customer.property_stock_customer.id,
                'date_expected': self.date_day_2
            }
        ])
        move_in_1 = moves_day_2[0]
        move_out_4 = moves_day_2[1]
        move_out_5 = moves_day_2[2]


        # We generate the initial state of the view and make sure everything was correctly set
        domain = []
        forecasted_moves = moves_day_1 + moves_day_2
        forecasted_moves._action_confirm()
        qcontext_values = self.env['stock.move'].with_context({
            'date_from': self.date_day_1.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        })._qweb_prepare_qcontext(self.view_stock_forecast.id, domain)

        lines = qcontext_values['lines']
        line_product_a = False
        for line in lines:
            if line[0]['product_id'] == self.product_a.id:
                line_product_a = line

        self.assertNotEquals(line_product_a, False)
        product_details = line_product_a[0]
        day_1 = line_product_a[1]
        day_2 = line_product_a[2]

        self.assertEquals(product_details['product_id'], self.product_a.id)
        self.assertEquals(len(day_1['moves_info']), 3)
        self.assertEquals(len(day_2['moves_info']), 3)
        self.assertEquals(moves_day_1.ids, [day_1['moves_info'][0]['id'], day_1['moves_info'][1]['id'], day_1['moves_info'][2]['id']])
        self.assertEquals(moves_day_2.ids, [day_2['moves_info'][0]['id'], day_2['moves_info'][1]['id'], day_2['moves_info'][2]['id']])

        self.assertEquals(day_1['virtual_available'], 10)
        self.assertEquals(day_1['cumulative_virtual_available'], -5)
        for move_info in day_1['moves_info']:
            self.assertEquals(move_info['is_out'], True)
            if move_info['id'] == move_out_1.id:
                self.assertEquals(move_info['is_to_reschedule'], False)
            if move_info['id'] == move_out_2.id:
                self.assertEquals(move_info['is_to_reschedule'], False)
            if move_info['id'] == move_out_3.id:
                self.assertEquals(move_info['is_to_reschedule'], True)

        self.assertEquals(day_2['virtual_available'], -5)
        self.assertEquals(day_2['cumulative_virtual_available'], -5)
        for move_info in day_2['moves_info']:
            if move_info['id'] == move_in_1.id:
                self.assertEquals(move_info['is_in'], True)
                self.assertEquals(move_info['is_to_reschedule'], False)
            if move_info['id'] == move_out_4.id:
                self.assertEquals(move_info['is_out'], True)
                self.assertEquals(move_info['is_to_reschedule'], False)
            if move_info['id'] == move_out_5.id:
                self.assertEquals(move_info['is_out'], True)
                self.assertEquals(move_info['is_to_reschedule'], True)

        # We force the context with the moved flagged as 'to_reschedule'
        self.env['stock.move'].with_context({'moves_to_reschedule': (move_out_3 + move_out_5).ids}).action_batch_reschedule()

        moves_day_1_rescheduled = moves_day_1 - move_out_3
        qcontext_values = forecasted_moves._qweb_prepare_qcontext(self.view_stock_forecast.id, domain)

        lines = qcontext_values['lines']
        line_product_a = False
        for line in lines:
            if line[0]['product_id'] == self.product_a.id:
                line_product_a = line

        self.assertNotEquals(line_product_a, False)

        product_details = line_product_a[0]
        day_1 = line_product_a[1]
        day_2 = line_product_a[2]

        self.assertEquals(product_details['product_id'], self.product_a.id)

        # We make sure move_out_3 was correctly put in 'Day 2'
        self.assertEquals(len(day_1['moves_info']), 2)
        self.assertEquals(len(day_2['moves_info']), 4)
        self.assertEquals(moves_day_1_rescheduled.ids, [day_1['moves_info'][0]['id'], day_1['moves_info'][1]['id']])
        day_1_moves_info_ids = []
        day_2_moves_info_ids = []
        for move_info in day_1['moves_info']:
            day_1_moves_info_ids.append(move_info['id'])
        for move_info in day_2['moves_info']:
            day_2_moves_info_ids.append(move_info['id'])
        self.assertNotIn(move_out_3.id, day_1_moves_info_ids)
        self.assertIn(move_out_3.id, day_2_moves_info_ids)

        self.assertEquals(day_1['virtual_available'], 10)
        self.assertEquals(day_1['cumulative_virtual_available'], 0)
        for move_info in day_1['moves_info']:
            self.assertEquals(move_info['is_out'], True)
            if move_info['id'] == move_out_1.id:
                self.assertEquals(move_info['is_to_reschedule'], False)
            if move_info['id'] == move_out_2.id:
                self.assertEquals(move_info['is_to_reschedule'], False)

        self.assertEquals(day_2['virtual_available'], 0)
        self.assertEquals(day_2['cumulative_virtual_available'], -5)
        nb_move_in = 0
        nb_move_out = 0
        nb_in_to_reschedule = 0
        nb_out_to_reschedule = 0
        for move_info in day_2['moves_info']:
            if move_info['is_in']:
                nb_move_in += 1
                if move_info['is_to_reschedule']:
                    nb_in_to_reschedule += 1
            if move_info['is_out']:
                nb_move_out += 1
                if move_info['is_to_reschedule']:
                    nb_out_to_reschedule += 1

        # We don't care about wich move is to reschedule in the end, but there should be only one.
        self.assertEquals(nb_move_in, 1)
        self.assertEquals(nb_move_out, 3)
        self.assertEquals(nb_in_to_reschedule, 0)
        self.assertEquals(nb_out_to_reschedule, 1)

    def test_forecast_period_wizard_1(self):

        new_date_from = self.date_day_1 + timedelta(days=5)
        forecast_period_wiz = self.env['stock.forecast.period'].create({'date_from': new_date_from})
        stock_forecast_act = forecast_period_wiz.set_date_from()

        self.assertEquals(stock_forecast_act['view_id'], self.env.ref('stock.view_move_forecast_qweb').id)
        self.assertEquals(stock_forecast_act['context'].get('date_from'), new_date_from.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))
