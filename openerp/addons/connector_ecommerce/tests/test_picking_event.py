# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2015 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import mock

import openerp.tests.common as common


class TestPickingEvent(common.TransactionCase):
    """ Test if the events on the pickings are fired correctly """

    def setUp(self):
        super(TestPickingEvent, self).setUp()
        self.picking_model = self.env['stock.picking']
        self.sale_model = self.env['sale.order']
        self.sale_line_model = self.env['sale.order.line']

        partner_model = self.env['res.partner']
        partner = partner_model.create({'name': 'Benjy'})
        self.sale = self.sale_model.create({'partner_id': partner.id})
        self.sale_line_model.create({
            'order_id': self.sale.id,
            'product_id': self.env.ref('product.product_product_33').id,
            'name': "[HEAD-USB] Headset USB",
            'product_uom_qty': 42,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'price_unit': 65,
        })
        self.sale_line_model.create({
            'order_id': self.sale.id,
            'product_id': self.env.ref('product.product_product_28').id,
            'name': "[EXT-HDD] External Hard disk",
            'product_uom_qty': 2,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'price_unit': 405,
        })
        self.sale.signal_workflow('order_confirm')
        self.picking = self.sale.picking_ids

    def test_event_on_picking_out_done(self):
        """ Test if the ``on_picking_out_done`` event is fired
        when an outgoing picking is done """
        self.picking.force_assign()
        event = ('openerp.addons.connector_ecommerce.'
                 'stock.on_picking_out_done')
        with mock.patch(event) as event_mock:
            self.picking.action_done()
            self.assertEquals(self.picking.state, 'done')
            event_mock.fire.assert_called_with(mock.ANY,
                                               'stock.picking',
                                               self.picking.id,
                                               'complete')

    def test_event_on_picking_out_done_partial(self):
        """ Test if the ``on_picking_out_done`` informs of the partial
        pickings """
        self.picking.force_assign()
        self.picking.do_prepare_partial()
        for operation in self.picking.pack_operation_ids:
            operation.product_qty = 1
        event = ('openerp.addons.connector_ecommerce.'
                 'stock.on_picking_out_done')
        with mock.patch(event) as event_mock:
            self.picking.do_transfer()
            self.assertEquals(self.picking.state, 'done')
            event_mock.fire.assert_called_with(mock.ANY,
                                               'stock.picking',
                                               self.picking.id,
                                               'partial')

    def test_event_on_tracking_number_added(self):
        """ Test if the ``on_tracking_number_added`` event is fired
        when a tracking number is added """
        event = ('openerp.addons.connector_ecommerce.'
                 'stock.on_tracking_number_added')
        with mock.patch(event) as event_mock:
            self.picking.carrier_tracking_ref = 'XYZ'
            event_mock.fire.assert_called_with(mock.ANY,
                                               'stock.picking',
                                               self.picking.id)
