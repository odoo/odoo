# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
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

#from openerp.test.common import TransactionCase
from datetime import date
from openerp.tests import common
from openerp import netsvc


class TestAveragePrice(common.TransactionCase):
    def setUp(self):
        super(TestAveragePrice, self).setUp()
        cr, uid, context = self.cr, self.uid, {}
        self.ir_model_data = self.registry('ir.model.data')
        self.product_product = self.registry('product.product')
        self.purchase_order = self.registry('purchase.order')
        self.purchase_order_line = self.registry('purchase.order.line')
        self.pricelist = self.registry('product.pricelist')
        self.stock_location = self.registry('stock.location')
        self.stock_picking = self.registry('stock.picking')
        self.stock_move = self.registry('stock.move')
        self.stock_partial_move = self.registry('stock.partial.move')
        self.stock_partial_move_line = self.registry('stock.partial.move.line')
        self.partial_picking = self.registry('stock.partial.picking')
        self.partial_picking_line = self.registry('stock.partial.picking.line')
        change_product_qty = self.registry('stock.change.product.qty')

        _, partner_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'res_partner_1')
        _, pricelist_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'product', 'list0')
        _, self.location_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
        _, self.supplier_location_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_suppliers')
        _, input_account_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'xfa')
        _, output_account_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'account', 'xfa')
        wf_service = netsvc.LocalService("workflow")

        self.standard_price = 10
        self.order_price_unit = 20
        self.available_qty = 1
        self.order_qty = 1
        self.picking_qty = 1

        self.product_id = self.product_product.create(cr, uid, {
            'name': 'Average product',
            'cost_method': 'average',
            'valuation': 'real_time',
            'property_stock_account_input': input_account_id,
            'property_stock_account_output': output_account_id,
        }, context=context)

        self.product_product.do_change_standard_price(
            cr, uid, [self.product_id], {
                'new_price': self.standard_price,
                'stock_input_account': input_account_id,
                'stock_output_account': output_account_id})

        change_product_qty_id = change_product_qty.create(
            cr, uid, {
                'location_id': self.location_id,
                'new_quantity': self.available_qty,
                'product_id': self.product_id})
        change_product_qty.change_product_qty(
            cr, uid, [change_product_qty_id], {
                'active_model': 'product.product',
                'active_id': self.product_id,
                'active_ids': [self.product_id]})

        self.po_01_id = self.purchase_order.create(cr, uid, {
            'partner_id': partner_id,
            'location_id': self.location_id,
            'pricelist_id': pricelist_id,
        }, context=context)

        self.order_line_10 = self.purchase_order_line.create(cr, uid, {
            'order_id': self.po_01_id,
            'product_id': self.product_id,
            'name': 'description',
            'date_planned': date.today(),
            'product_qty': self.order_qty,
            'price_unit': self.order_price_unit
        }, context=context)

        wf_service.trg_validate(uid, 'purchase.order', self.po_01_id, 'purchase_confirm', cr)


    def test_10_stock_move_action_done(self):
        cr, uid, context = self.cr, self.uid, {}
        picking_id = self.purchase_order.read(cr, uid, [self.po_01_id], ['picking_ids'])[0]['picking_ids']
        move_lines_ids = self.stock_picking.read(cr, uid, picking_id, ['move_lines'])[0]['move_lines']
        for move in self.stock_move.browse(cr, uid, move_lines_ids, context=context):
            move.action_done()

        new_price = self.product_product.read(cr, uid, self.product_id, ['standard_price'], context=context)['standard_price']
        self.assertAlmostEqual(
            new_price,
            (self.available_qty * self.standard_price + self.order_qty * self.order_price_unit)
            /(self.available_qty + self.order_qty))

    def test_20_partial_stock_move(self):
        cr, uid, context = self.cr, self.uid, {}
        picking_ids = self.purchase_order.read(cr, uid, [self.po_01_id], ['picking_ids'])[0]['picking_ids']
        product = self.product_product.browse(cr, uid, self.product_id, context=context)

        partial_move_id = self.stock_partial_move.create(cr, uid, {
            'date': date.today(),
            'picking_id': picking_ids[0]
        }, context=context)

        move_lines_ids = self.stock_picking.read(cr, uid, picking_ids, ['move_lines'])[0]['move_lines']
        for move in self.stock_move.browse(cr, uid, move_lines_ids, context=context):
            self.stock_partial_move_line.create(cr, uid, {
                'product_id': self.product_id,
                'quantity': self.picking_qty,
                'product_uom': product.uom_id.id,
                'location_dest_id': self.location_id,
                'location_id': self.supplier_location_id,
                'move_id': move.id,
                'cost': self.order_price_unit,
                'wizard_id': partial_move_id,
            }, context=context)

        self.stock_partial_move.do_partial(cr, uid, [partial_move_id], context=context)

        new_price = self.product_product.read(cr, uid, self.product_id, ['standard_price'], context=context)['standard_price']
        self.assertAlmostEqual(
            new_price,
            (self.available_qty * self.standard_price + self.order_qty * self.order_price_unit)
            /(self.available_qty + self.order_qty))

    def test_30_partial_stock_picking(self):
        cr, uid, context = self.cr, self.uid, {}
        picking_ids = self.purchase_order.read(cr, uid, [self.po_01_id], ['picking_ids'])[0]['picking_ids']
        product = self.product_product.browse(cr, uid, self.product_id, context=context)

        partial_picking_id = self.partial_picking.create(cr, uid, {
            'date': date.today(),
            'picking_id': picking_ids[0],
        }, context=context)

        move_lines_ids = self.stock_picking.read(cr, uid, picking_ids, ['move_lines'])[0]['move_lines']
        for move in self.stock_move.browse(cr, uid, move_lines_ids, context=context):
            self.partial_picking_line.create(cr, uid, {
                'product_id': self.product_id,
                'quantity': self.picking_qty,
                'product_uom': product.uom_id.id,
                'location_dest_id': self.location_id,
                'location_id': self.supplier_location_id,
                'move_id': move.id,
                'cost': self.order_price_unit,
                'wizard_id': partial_picking_id,
            }, context=context)

        self.partial_picking.do_partial(cr, uid, [partial_picking_id], context=context)

        new_price = self.product_product.read(cr, uid, self.product_id, ['standard_price'], context=context)['standard_price']
        self.assertAlmostEqual(
            new_price,
            (self.available_qty * self.standard_price + self.order_qty * self.order_price_unit)
            /(self.available_qty + self.order_qty))

