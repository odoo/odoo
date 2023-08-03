# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


class TestStockValuationCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationCommon, cls).setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.picking_type_in = cls.env.ref('stock.picking_type_in')
        cls.picking_type_out = cls.env.ref('stock.picking_type_out')
        cls.env.ref('base.EUR').active = True

    def setUp(self):
        super(TestStockValuationCommon, self).setUp()
        # Counter automatically incremented by `_make_in_move` and `_make_out_move`.
        self.days = 0

    def _make_in_move(self, product, quantity, unit_cost=None, create_picking=False, loc_dest=None, pick_type=None):
        """ Helper to create and validate a receipt move.
        """
        unit_cost = unit_cost or product.standard_price
        loc_dest = loc_dest or self.stock_location
        pick_type = pick_type or self.picking_type_in
        in_move = self.env['stock.move'].create({
            'name': 'in %s units @ %s per unit' % (str(quantity), str(unit_cost)),
            'product_id': product.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': loc_dest.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': quantity,
            'price_unit': unit_cost,
            'picking_type_id': pick_type.id,
        })

        if create_picking:
            picking = self.env['stock.picking'].create({
                'picking_type_id': in_move.picking_type_id.id,
                'location_id': in_move.location_id.id,
                'location_dest_id': in_move.location_dest_id.id,
            })
            in_move.write({'picking_id': picking.id})

        in_move._action_confirm()
        in_move._action_assign()
        in_move.move_line_ids.qty_done = quantity
        in_move._action_done()

        self.days += 1
        return in_move.with_context(svl=True)

    def _make_out_move(self, product, quantity, force_assign=None, create_picking=False, loc_src=None, pick_type=None):
        """ Helper to create and validate a delivery move.
        """
        loc_src = loc_src or self.stock_location
        pick_type = pick_type or self.picking_type_out
        out_move = self.env['stock.move'].create({
            'name': 'out %s units' % str(quantity),
            'product_id': product.id,
            'location_id': loc_src.id,
            'location_dest_id': self.customer_location.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': quantity,
            'picking_type_id': pick_type.id,
        })

        if create_picking:
            picking = self.env['stock.picking'].create({
                'picking_type_id': out_move.picking_type_id.id,
                'location_id': out_move.location_id.id,
                'location_dest_id': out_move.location_dest_id.id,
            })
            out_move.write({'picking_id': picking.id})

        out_move._action_confirm()
        out_move._action_assign()
        if force_assign:
            self.env['stock.move.line'].create({
                'move_id': out_move.id,
                'product_id': out_move.product_id.id,
                'product_uom_id': out_move.product_uom.id,
                'location_id': out_move.location_id.id,
                'location_dest_id': out_move.location_dest_id.id,
            })
        out_move.move_line_ids.qty_done = quantity
        out_move._action_done()

        self.days += 1
        return out_move.with_context(svl=True)

    def _make_dropship_move(self, product, quantity, unit_cost=None):
        dropshipped = self.env['stock.move'].create({
            'name': 'dropship %s units' % str(quantity),
            'product_id': product.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.customer_location.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': quantity,
            'picking_type_id': self.picking_type_out.id,
        })
        if unit_cost:
            dropshipped.price_unit = unit_cost
        dropshipped._action_confirm()
        dropshipped._action_assign()
        dropshipped.move_line_ids.qty_done = quantity
        dropshipped._action_done()
        return dropshipped

    def _make_return(self, move, quantity_to_return):
        stock_return_picking = Form(self.env['stock.return.picking']\
            .with_context(active_ids=[move.picking_id.id], active_id=move.picking_id.id, active_model='stock.picking'))
        stock_return_picking = stock_return_picking.save()
        stock_return_picking.product_return_moves.quantity = quantity_to_return
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].qty_done = quantity_to_return
        return_pick._action_done()
        return return_pick.move_ids


class TestStockValuationStandard(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        cls.product1.product_tmpl_id.standard_price = 10

    def test_normal_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 15)

        self.assertEqual(self.product1.value_svl, 50)
        self.assertEqual(self.product1.quantity_svl, 5)

    def test_change_in_past_increase_in_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 15)
        move1.move_line_ids.qty_done = 15

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_change_in_past_decrease_in_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 15)
        move1.move_line_ids.qty_done = 5

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_change_in_past_add_ml_in_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 15)
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 5,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_change_in_past_increase_out_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_out_move(self.product1, 1)
        move2.move_line_ids.qty_done = 5

        self.assertEqual(self.product1.value_svl, 50)
        self.assertEqual(self.product1.quantity_svl, 5)

    def test_change_in_past_decrease_out_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_out_move(self.product1, 5)
        move2.move_line_ids.qty_done = 1

        self.assertEqual(self.product1.value_svl, 90)
        self.assertEqual(self.product1.quantity_svl, 9)

    def test_change_standard_price_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 15)

        # change cost from 10 to 15
        self.product1.standard_price = 15.0

        self.assertEqual(self.product1.value_svl, 75)
        self.assertEqual(self.product1.quantity_svl, 5)
        self.assertEqual(self.product1.stock_valuation_layer_ids.sorted()[-1].description, 'Product value manually modified (from 10.0 to 15.0)')

    def test_negative_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_out_move(self.product1, 15)
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 10,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })

        self.assertEqual(self.product1.value_svl, 50)
        self.assertEqual(self.product1.quantity_svl, 5)

    def test_dropship_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_dropship_move(self.product1, 10)

        valuation_layers = self.product1.stock_valuation_layer_ids
        self.assertEqual(len(valuation_layers), 2)
        self.assertEqual(valuation_layers[0].value, 100)
        self.assertEqual(valuation_layers[1].value, -100)
        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_change_in_past_increase_dropship_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_dropship_move(self.product1, 10)
        move1.move_line_ids.qty_done = 15

        valuation_layers = self.product1.stock_valuation_layer_ids
        self.assertEqual(len(valuation_layers), 4)
        self.assertEqual(valuation_layers[0].value, 100)
        self.assertEqual(valuation_layers[1].value, -100)
        self.assertEqual(valuation_layers[2].value, 50)
        self.assertEqual(valuation_layers[3].value, -50)
        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_empty_stock_move_valorisation(self):
        product1 = self.env['product.product'].create({
            'name': 'p1',
            'type': 'product',
        })
        product2 = self.env['product.product'].create({
            'name': 'p2',
            'type': 'product',
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
        })
        for product in (product1, product2):
            product.standard_price = 10
            in_move = self.env['stock.move'].create({
                'name': 'in %s units @ %s per unit' % (2, str(10)),
                'product_id': product.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 2,
                'price_unit': 10,
                'picking_type_id': self.picking_type_in.id,
                'picking_id': picking.id
            })

        picking.action_confirm()
        # set quantity done only on one move
        in_move.move_line_ids.qty_done = 2
        res_dict = picking.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].with_context(res_dict.get('context')).browse(res_dict.get('res_id'))
        res_dict_for_back_order = wizard.process()

        self.assertTrue(product2.stock_valuation_layer_ids)
        self.assertFalse(product1.stock_valuation_layer_ids)

    def test_currency_precision_and_standard_svl_value(self):
        currency = self.env['res.currency'].create({
            'name': 'Odoo',
            'symbol': 'O',
            'rounding': 1,
        })
        new_company = self.env['res.company'].create({
            'name': 'Super Company',
            'currency_id': currency.id,
        })

        old_company = self.env.user.company_id
        try:
            self.env.user.company_id = new_company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', new_company.id)])
            product = self.product1.with_company(new_company)
            product.standard_price = 3

            self._make_in_move(product, 0.5, loc_dest=warehouse.lot_stock_id, pick_type=warehouse.in_type_id)
            self._make_out_move(product, 0.5, loc_src=warehouse.lot_stock_id, pick_type=warehouse.out_type_id)

            self.assertEqual(product.value_svl, 0.0)
        finally:
            self.env.user.company_id = old_company

class TestStockValuationAVCO(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

    def test_normal_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        self.assertEqual(self.product1.standard_price, 10)
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        self.assertEqual(self.product1.standard_price, 15)
        self.assertEqual(move2.stock_valuation_layer_ids.value, 200)
        move3 = self._make_out_move(self.product1, 15)
        self.assertEqual(self.product1.standard_price, 15)
        self.assertEqual(move3.stock_valuation_layer_ids.value, -225)

        self.assertEqual(self.product1.value_svl, 75)
        self.assertEqual(self.product1.quantity_svl, 5)

    def test_change_in_past_increase_in_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 15)
        move1.move_line_ids.qty_done = 15

        self.assertEqual(self.product1.value_svl, 125)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_change_in_past_decrease_in_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 15)
        move1.move_line_ids.qty_done = 5

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_change_in_past_add_ml_in_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 15)
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 5,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })

        self.assertEqual(self.product1.value_svl, 125)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.standard_price, 12.5)

    def test_change_in_past_add_move_in_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 15)
        self.env['stock.move.line'].create({
            'product_id': move1.product_id.id,
            'qty_done': 5,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
            'state': 'done',
            'picking_id': move1.picking_id.id,
        })

        self.assertEqual(self.product1.value_svl, 150)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.standard_price, 15)

    def test_change_in_past_increase_out_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 15)
        move3.move_line_ids.qty_done = 20

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)
        self.assertEqual(self.product1.standard_price, 15)

    def test_change_in_past_decrease_out_1(self):
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 15)
        move3.move_line_ids.qty_done = 10

        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 10)
        self.assertEqual(self.product1.value_svl, 150)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.standard_price, 15)

    def test_negative_1(self):
        """ Ensures that, in AVCO, the `remaining_qty` field is computed and the vacuum is ran
        when necessary.
        """
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 30)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, -10)
        move4 = self._make_in_move(self.product1, 10, unit_cost=30)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 0)
        move5 = self._make_in_move(self.product1, 10, unit_cost=40)

        self.assertEqual(self.product1.value_svl, 400)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_negative_2(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.standard_price = 10
        move1 = self._make_out_move(self.product1, 1, force_assign=True)
        move2 = self._make_in_move(self.product1, 1, unit_cost=15)

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_negative_3(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_out_move(self.product1, 2, force_assign=True)
        self.assertEqual(move1.stock_valuation_layer_ids.value, 0)
        move2 = self._make_in_move(self.product1, 20, unit_cost=3.33)
        self.assertEqual(move1.stock_valuation_layer_ids[1].value, -6.66)

        self.assertEqual(self.product1.standard_price, 3.33)
        self.assertEqual(self.product1.value_svl, 59.94)
        self.assertEqual(self.product1.quantity_svl, 18)

    def test_return_receipt_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_return(move1, 1)

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)
        self.assertEqual(self.product1.standard_price, 15)

    def test_return_delivery_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1, create_picking=True)
        move4 = self._make_return(move3, 1)

        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.product1.quantity_svl, 2)
        self.assertEqual(self.product1.standard_price, 15)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 2)

    def test_rereturn_receipt_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_return(move1, 1)  # -15, current avco
        move5 = self._make_return(move4, 1)  # +10, original move's price unit

        self.assertEqual(self.product1.value_svl, 15)
        self.assertEqual(self.product1.quantity_svl, 1)
        self.assertEqual(self.product1.standard_price, 15)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 1)

    def test_rereturn_delivery_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1, create_picking=True)
        move4 = self._make_return(move3, 1)
        move5 = self._make_return(move4, 1)

        self.assertEqual(self.product1.value_svl, 15)
        self.assertEqual(self.product1.quantity_svl, 1)
        self.assertEqual(self.product1.standard_price, 15)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 1)

    def test_dropship_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_dropship_move(self.product1, 1, unit_cost=10)

        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.product1.quantity_svl, 2)
        self.assertEqual(self.product1.standard_price, 15)

    def test_rounding_slv_1(self):
        self._make_in_move(self.product1, 1, unit_cost=1.00)
        self._make_in_move(self.product1, 1, unit_cost=1.00)
        self._make_in_move(self.product1, 1, unit_cost=1.01)

        self.assertAlmostEqual(self.product1.value_svl, 3.01)

        move_out = self._make_out_move(self.product1, 3, create_picking=True)

        self.assertIn('Rounding Adjustment: -0.01', move_out.stock_valuation_layer_ids.description)

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)
        self.assertEqual(self.product1.standard_price, 1.00)

    def test_rounding_slv_2(self):
        self._make_in_move(self.product1, 1, unit_cost=1.02)
        self._make_in_move(self.product1, 1, unit_cost=1.00)
        self._make_in_move(self.product1, 1, unit_cost=1.00)

        self.assertAlmostEqual(self.product1.value_svl, 3.02)

        move_out = self._make_out_move(self.product1, 3, create_picking=True)

        self.assertIn('Rounding Adjustment: +0.01', move_out.stock_valuation_layer_ids.description)

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)
        self.assertEqual(self.product1.standard_price, 1.01)

    def test_rounding_svl_3(self):
        self._make_in_move(self.product1, 1000, unit_cost=0.17)
        self._make_in_move(self.product1, 800, unit_cost=0.23)

        self.assertEqual(self.product1.standard_price, 0.20)

        self._make_out_move(self.product1, 1000, create_picking=True)
        self._make_out_move(self.product1, 800, create_picking=True)

        self.assertEqual(self.product1.value_svl, 0)

    def test_rounding_svl_4(self):
        """
        The first 2 In moves result in a rounded standard_price at 3.4943, which is rounded at 3.49.
        This test ensures that no rounding error is generated with small out quantities.
        """
        self.product1.categ_id.property_cost_method = 'average'
        self._make_in_move(self.product1, 2, unit_cost=4.63)
        self._make_in_move(self.product1, 5, unit_cost=3.04)
        self.assertEqual(self.product1.standard_price, 3.49)

        for _ in range(70):
            self._make_out_move(self.product1, 0.1)

        self.assertEqual(self.product1.quantity_svl, 0)
        self.assertEqual(self.product1.value_svl, 0)

    def test_return_delivery_2(self):
        self.product1.write({"standard_price": 1})
        move1 = self._make_out_move(self.product1, 10, create_picking=True, force_assign=True)
        self._make_in_move(self.product1, 10, unit_cost=2)
        self._make_return(move1, 10)

        self.assertEqual(self.product1.value_svl, 20)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.standard_price, 2)

    def test_return_delivery_rounding(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.write({"standard_price": 1})
        self._make_in_move(self.product1, 1, unit_cost=13.13)
        self._make_in_move(self.product1, 1, unit_cost=12.20)
        move3 = self._make_out_move(self.product1, 2, create_picking=True)
        move4 = self._make_return(move3, 2)

        self.assertAlmostEqual(abs(move3.stock_valuation_layer_ids[0].value), abs(move4.stock_valuation_layer_ids[0].value))
        self.assertAlmostEqual(self.product1.value_svl, 25.33)
        self.assertEqual(self.product1.quantity_svl, 2)


class TestStockValuationFIFO(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'

    def test_normal_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 15)

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 5)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 5)

    def test_negative_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 30)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, -10)
        move4 = self._make_in_move(self.product1, 10, unit_cost=30)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 0)
        move5 = self._make_in_move(self.product1, 10, unit_cost=40)

        self.assertEqual(self.product1.value_svl, 400)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_change_in_past_decrease_in_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 20, unit_cost=10)
        move2 = self._make_out_move(self.product1, 10)
        move1.move_line_ids.qty_done = 10

        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 0)

    def test_change_in_past_decrease_in_2(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 20, unit_cost=10)
        move2 = self._make_out_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 10)
        move1.move_line_ids.qty_done = 10
        move4 = self._make_in_move(self.product1, 20, unit_cost=15)

        self.assertEqual(self.product1.value_svl, 150)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_change_in_past_increase_in_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=15)
        move3 = self._make_out_move(self.product1, 20)
        move1.move_line_ids.qty_done = 20

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_change_in_past_increase_in_2(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=12)
        move3 = self._make_out_move(self.product1, 15)
        move4 = self._make_out_move(self.product1, 20)
        move5 = self._make_in_move(self.product1, 100, unit_cost=15)
        move1.move_line_ids.qty_done = 20

        self.assertEqual(self.product1.value_svl, 1375)
        self.assertEqual(self.product1.quantity_svl, 95)

    def test_change_in_past_increase_out_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 20, unit_cost=10)
        move2 = self._make_out_move(self.product1, 10)
        move3 = self._make_in_move(self.product1, 20, unit_cost=15)
        move2.move_line_ids.qty_done = 25

        self.assertEqual(self.product1.value_svl, 225)
        self.assertEqual(self.product1.quantity_svl, 15)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 15)

    def test_change_in_past_decrease_out_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 20, unit_cost=10)
        move2 = self._make_out_move(self.product1, 15)
        move3 = self._make_in_move(self.product1, 20, unit_cost=15)
        move2.move_line_ids.qty_done = 5

        self.assertEqual(self.product1.value_svl, 450)
        self.assertEqual(self.product1.quantity_svl, 35)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 35)

    def test_change_in_past_add_ml_out_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 20, unit_cost=10)
        move2 = self._make_out_move(self.product1, 10)
        move3 = self._make_in_move(self.product1, 20, unit_cost=15)
        self.env['stock.move.line'].create({
            'move_id': move2.id,
            'product_id': move2.product_id.id,
            'qty_done': 5,
            'product_uom_id': move2.product_uom.id,
            'location_id': move2.location_id.id,
            'location_dest_id': move2.location_dest_id.id,
        })

        self.assertEqual(self.product1.value_svl, 350)
        self.assertEqual(self.product1.quantity_svl, 25)
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 25)

    def test_return_delivery_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_out_move(self.product1, 10, create_picking=True)
        move3 = self._make_in_move(self.product1, 10, unit_cost=20)
        move4 = self._make_return(move2, 10)

        self.assertEqual(self.product1.value_svl, 300)
        self.assertEqual(self.product1.quantity_svl, 20)

    def test_return_receipt_1(self):
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        move1 = self._make_in_move(self.product1, 10, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_return(move1, 2)

        self.assertEqual(self.product1.value_svl, 280)
        self.assertEqual(self.product1.quantity_svl, 18)

    def test_rereturn_receipt_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10, create_picking=True)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1)
        move4 = self._make_return(move1, 1)
        move5 = self._make_return(move4, 1)

        self.assertEqual(self.product1.value_svl, 20)
        self.assertEqual(self.product1.quantity_svl, 1)

    def test_rereturn_delivery_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1, create_picking=True)
        move4 = self._make_return(move3, 1)
        move5 = self._make_return(move4, 1)

        self.assertEqual(self.product1.value_svl, 10)
        self.assertEqual(self.product1.quantity_svl, 1)

    def test_dropship_1(self):
        move1 = self._make_in_move(self.product1, 1, unit_cost=10)
        move2 = self._make_in_move(self.product1, 1, unit_cost=20)
        move3 = self._make_dropship_move(self.product1, 1, unit_cost=10)

        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.product1.quantity_svl, 2)
        self.assertAlmostEqual(self.product1.standard_price, 10)

    def test_return_delivery_2(self):
        self._make_in_move(self.product1, 1, unit_cost=10)
        self.product1.standard_price = 0
        self._make_in_move(self.product1, 1, unit_cost=0)

        self._make_out_move(self.product1, 1)
        out_move02 = self._make_out_move(self.product1, 1, create_picking=True)

        returned = self._make_return(out_move02, 1)
        self.assertEqual(returned.stock_valuation_layer_ids.value, 0)

    def test_return_delivery_3(self):
        self.product1.write({"standard_price": 1})
        move1 = self._make_out_move(self.product1, 10, create_picking=True, force_assign=True)
        self._make_in_move(self.product1, 10, unit_cost=2)
        self._make_return(move1, 10)

        self.assertEqual(self.product1.value_svl, 20)
        self.assertEqual(self.product1.quantity_svl, 10)

    def test_currency_precision_and_fifo_svl_value(self):
        currency = self.env['res.currency'].create({
            'name': 'Odoo',
            'symbol': 'O',
            'rounding': 1,
        })
        new_company = self.env['res.company'].create({
            'name': 'Super Company',
            'currency_id': currency.id,
        })

        old_company = self.env.user.company_id
        try:
            self.env.user.company_id = new_company
            product = self.product1.with_company(new_company)
            product.product_tmpl_id.categ_id.property_cost_method = 'fifo'
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', new_company.id)])

            self._make_in_move(product, 0.5, loc_dest=warehouse.lot_stock_id, pick_type=warehouse.in_type_id, unit_cost=3)
            self._make_out_move(product, 0.5, loc_src=warehouse.lot_stock_id, pick_type=warehouse.out_type_id)

            self.assertEqual(product.value_svl, 0.0)
        finally:
            self.env.user.company_id = old_company


class TestStockValuationChangeCostMethod(TestStockValuationCommon):
    def test_standard_to_fifo_1(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.product_tmpl_id.standard_price = 10

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 1)

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.assertEqual(self.product1.value_svl, 190)
        self.assertEqual(self.product1.quantity_svl, 19)

        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 5)
        for svl in self.product1.stock_valuation_layer_ids.sorted()[-2:]:
            self.assertEqual(svl.description, 'Costing method change for product category All: from standard to fifo.')

    def test_standard_to_fifo_2(self):
        """ We want the same result as `test_standard_to_fifo_1` but by changing the category of
        `self.product1` to another one, not changing the current one.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.product_tmpl_id.standard_price = 10

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 1)

        cat2 = self.env['product.category'].create({'name': 'fifo'})
        cat2.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id = cat2
        self.assertEqual(self.product1.value_svl, 190)
        self.assertEqual(self.product1.quantity_svl, 19)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 5)

    def test_avco_to_fifo(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1)

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.assertEqual(self.product1.value_svl, 285)
        self.assertEqual(self.product1.quantity_svl, 19)

    def test_fifo_to_standard(self):
        """ The accounting impact of this cost method change is not neutral as we will use the last
        fifo price as the new standard price.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1)

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.assertEqual(self.product1.value_svl, 380)
        self.assertEqual(self.product1.quantity_svl, 19)

    def test_fifo_to_avco(self):
        """ The accounting impact of this cost method change is not neutral as we will use the last
        fifo price as the new AVCO.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1)

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.assertEqual(self.product1.value_svl, 380)
        self.assertEqual(self.product1.quantity_svl, 19)

    def test_avco_to_standard(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        move1 = self._make_in_move(self.product1, 10, unit_cost=10)
        move2 = self._make_in_move(self.product1, 10, unit_cost=20)
        move3 = self._make_out_move(self.product1, 1)

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.assertEqual(self.product1.value_svl, 285)
        self.assertEqual(self.product1.quantity_svl, 19)

    def test_standard_to_avco(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.product_tmpl_id.standard_price = 10

        move1 = self._make_in_move(self.product1, 10)
        move2 = self._make_in_move(self.product1, 10)
        move3 = self._make_out_move(self.product1, 1)

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.assertEqual(self.product1.value_svl, 190)
        self.assertEqual(self.product1.quantity_svl, 19)


class TestStockValuationChangeValuation(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationChangeValuation, cls).setUpClass()
        cls.stock_input_account, cls.stock_output_account, cls.stock_valuation_account, cls.expense_account, cls.stock_journal = _create_accounting_data(cls.env)
        cls.product1.categ_id.property_valuation = 'real_time'
        cls.product1.write({
            'property_account_expense_id': cls.expense_account.id,
        })
        cls.product1.categ_id.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
        })
        cls.env.company.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
        })

    def _get_stock_account_balance(self, stock_valuation_layer):
        """Return the accounting balance from the stock valuation account for the given SVL"""
        stock_valuation_account = stock_valuation_layer.product_id.categ_id.property_stock_valuation_account_id
        return stock_valuation_layer.account_move_id.line_ids.filtered(lambda line: line.account_id == stock_valuation_account).balance


    def test_standard_manual_to_auto_1(self):
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.product_tmpl_id.standard_price = 10
        move1 = self._make_in_move(self.product1, 10)

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 0)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 1)

        self.product1.product_tmpl_id.categ_id.write({
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
        })

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        # An accounting entry should only be created for the replenish now that the category is perpetual.
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 1)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 3)
        # Check the entry's value
        last_svl = self.product1.stock_valuation_layer_ids.sorted()[-1]
        self.assertEqual(self._get_stock_account_balance(last_svl), self.product1.value_svl)
        for svl in self.product1.stock_valuation_layer_ids.sorted()[-2:]:
            self.assertEqual(svl.description, 'Valuation method change for product category All: from manual_periodic to real_time.')

    def test_standard_manual_to_auto_2(self):
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.product_tmpl_id.standard_price = 10
        move1 = self._make_in_move(self.product1, 10)

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 0)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 1)

        cat2 = self.env['product.category'].create({'name': 'standard auto'})
        cat2.property_cost_method = 'standard'
        cat2.property_valuation = 'real_time'
        cat2.write({
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })

        # Try to change the product category with a `default_detailed_type` key in the context and
        # check it doesn't break the account move generation.
        self.product1.with_context(default_detailed_type='product').categ_id = cat2
        self.assertEqual(self.product1.categ_id, cat2)

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        # An accounting entry should only be created for the replenish now that the category is perpetual.
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 1)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 3)
        # Check the entry's value
        last_svl = self.product1.stock_valuation_layer_ids.sorted()[-1]
        self.assertEqual(self._get_stock_account_balance(last_svl), self.product1.value_svl)

    def test_standard_manual_to_auto_3(self):
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'
        self.product1.product_tmpl_id.standard_price = 10
        self._make_out_move(self.product1, 10, force_assign=True)

        self.assertEqual(self.product1.value_svl, -100)
        self.assertEqual(self.product1.quantity_svl, -10)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.account_move_id), 0)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 1)

        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        self.assertEqual(self.product1.value_svl, -100)
        self.assertEqual(self.product1.quantity_svl, -10)
        # An accounting entry should only be created for the replenish now that the category is perpetual.
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.account_move_id), 1)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 3)
        # Check the entry's value
        last_svl = self.product1.stock_valuation_layer_ids.sorted()[-1]
        self.assertEqual(self._get_stock_account_balance(last_svl), self.product1.value_svl)
        for svl in self.product1.stock_valuation_layer_ids.sorted()[-2:]:
            self.assertEqual(svl.description, 'Valuation method change for product category All: from manual_periodic to real_time.')

    def test_standard_auto_to_manual_1(self):
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.standard_price = 10
        move1 = self._make_in_move(self.product1, 10)

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 1)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 1)

        self.product1.product_tmpl_id.categ_id.property_valuation = 'manual_periodic'

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        # An accounting entry should only be created for the emptying now that the category is manual.
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 2)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 3)

    def test_standard_auto_to_manual_2(self):
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.standard_price = 10
        move1 = self._make_in_move(self.product1, 10)

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 1)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 1)

        cat2 = self.env['product.category'].create({'name': 'fifo'})
        cat2.property_cost_method = 'standard'
        cat2.property_valuation = 'manual_periodic'
        self.product1.with_context(debug=True).categ_id = cat2

        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        # An accounting entry should only be created for the emptying now that the category is manual.
        self.assertEqual(len(self.product1.stock_valuation_layer_ids.mapped('account_move_id')), 2)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 3)

@tagged('post_install', '-at_install')
class TestAngloSaxonAccounting(AccountTestInvoicingCommon, TestStockValuationCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env.ref('base.EUR').active = True
        cls.company_data['company'].anglo_saxon_accounting = True
        cls.stock_location = cls.env['stock.location'].create({
            'name': 'stock location',
            'usage': 'internal',
        })
        cls.customer_location = cls.env['stock.location'].create({
            'name': 'customer location',
            'usage': 'customer',
        })
        cls.supplier_location = cls.env['stock.location'].create({
            'name': 'supplier location',
            'usage': 'supplier',
        })
        cls.warehouse_in = cls.env['stock.warehouse'].create({
            'name': 'warehouse in',
            'company_id': cls.company_data['company'].id,
            'code': '1',
        })
        cls.warehouse_out = cls.env['stock.warehouse'].create({
            'name': 'warehouse out',
            'company_id': cls.company_data['company'].id,
            'code': '2',
        })
        cls.picking_type_in = cls.env['stock.picking.type'].create({
            'name': 'pick type in',
            'sequence_code': '1',
            'code': 'incoming',
            'company_id': cls.company_data['company'].id,
            'warehouse_id': cls.warehouse_in.id,
        })
        cls.picking_type_out = cls.env['stock.picking.type'].create({
            'name': 'pick type in',
            'sequence_code': '2',
            'code': 'outgoing',
            'company_id': cls.company_data['company'].id,
            'warehouse_id': cls.warehouse_out.id,
        })
        cls.stock_input_account = cls.env['account.account'].create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.stock_output_account = cls.env['account.account'].create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.stock_valuation_account = cls.env['account.account'].create({
            'name': 'Stock Valuation',
            'code': 'StockValuation',
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.expense_account = cls.env['account.account'].create({
            'name': 'Expense Account',
            'code': 'ExpenseAccount',
            'account_type': 'expense',
            'reconcile': True,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'property_account_expense_id': cls.expense_account.id,
        })
        cls.product1.categ_id.write({
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.company_data['default_journal_misc'].id,
        })

    def _make_in_move(self, product, quantity, unit_cost=None, create_picking=False, loc_dest=None, pick_type=None):
        """ Helper to create and validate a receipt move.
        """
        unit_cost = unit_cost or product.standard_price
        loc_dest = loc_dest or self.stock_location
        pick_type = pick_type or self.picking_type_in
        in_move = self.env['stock.move'].create({
            'name': 'in %s units @ %s per unit' % (str(quantity), str(unit_cost)),
            'product_id': product.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': loc_dest.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': quantity,
            'price_unit': unit_cost,
            'picking_type_id': pick_type.id,
        })

        if create_picking:
            picking = self.env['stock.picking'].create({
                'picking_type_id': in_move.picking_type_id.id,
                'location_id': in_move.location_id.id,
                'location_dest_id': in_move.location_dest_id.id,
            })
            in_move.write({'picking_id': picking.id})

        in_move._action_confirm()
        in_move._action_assign()
        in_move.move_line_ids.qty_done = quantity
        in_move._action_done()

        return in_move.with_context(svl=True)

    def _make_dropship_move(self, product, quantity, unit_cost=None):
        dropshipped = self.env['stock.move'].create({
            'name': 'dropship %s units' % str(quantity),
            'product_id': product.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.customer_location.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': quantity,
            'picking_type_id': self.picking_type_out.id,
        })
        if unit_cost:
            dropshipped.price_unit = unit_cost
        dropshipped._action_confirm()
        dropshipped._action_assign()
        dropshipped.move_line_ids.qty_done = quantity
        dropshipped._action_done()
        return dropshipped

    def _make_return(self, move, quantity_to_return):
        stock_return_picking = Form(self.env['stock.return.picking']\
            .with_context(active_ids=[move.picking_id.id], active_id=move.picking_id.id, active_model='stock.picking'))
        stock_return_picking = stock_return_picking.save()
        stock_return_picking.product_return_moves.quantity = quantity_to_return
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].qty_done = quantity_to_return
        return_pick._action_done()
        return return_pick.move_ids

    def test_avco_and_credit_note(self):
        """
        When reversing an invoice that contains some anglo-saxo AML, the new anglo-saxo AML should have the same value
        """
        # Required for `account_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('account.group_account_readonly')
        self.product1.categ_id.property_cost_method = 'average'

        self._make_in_move(self.product1, 2, unit_cost=10)

        invoice_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        invoice_form.partner_id = self.env['res.partner'].create({'name': 'Super Client'})
        with invoice_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.product_id = self.product1
            invoice_line_form.quantity = 2
            invoice_line_form.price_unit = 25
            invoice_line_form.account_id = self.company_data['default_journal_purchase'].default_account_id
            invoice_line_form.tax_ids.clear()
        invoice = invoice_form.save()
        invoice.action_post()

        self._make_in_move(self.product1, 2, unit_cost=20)
        self.assertEqual(self.product1.standard_price, 15)

        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'refund_method': 'refund',
            'journal_id': invoice.journal_id.id,
        })
        action = refund_wizard.reverse_moves()
        reverse_invoice = self.env['account.move'].browse(action['res_id'])
        with Form(reverse_invoice) as reverse_invoice_form:
            with reverse_invoice_form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        reverse_invoice.action_post()

        anglo_lines = reverse_invoice.line_ids.filtered(lambda l: l.display_type == 'cogs')
        self.assertEqual(len(anglo_lines), 2)
        self.assertEqual(abs(anglo_lines[0].balance), 10)
        self.assertEqual(abs(anglo_lines[1].balance), 10)

    def test_return_delivery_storno(self):
        """ When using STORNO accounting, reverse accounting moves should have negative values for credit/debit.
        """
        self.env.company.account_storno = True
        self.product1.categ_id.property_cost_method = 'fifo'

        self._make_in_move(self.product1, 10, unit_cost=10)
        out_move = self._make_out_move(self.product1, 10, create_picking=True)
        return_move = self._make_return(out_move, 10)

        valuation_line = out_move.account_move_ids.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        stock_out_line = out_move.account_move_ids.line_ids.filtered(lambda l: l.account_id == self.stock_output_account)

        self.assertEqual(valuation_line.credit, 100)
        self.assertEqual(valuation_line.debit, 0)
        self.assertEqual(stock_out_line.credit, 0)
        self.assertEqual(stock_out_line.debit, 100)

        valuation_line = return_move.account_move_ids.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        stock_out_line = return_move.account_move_ids.line_ids.filtered(lambda l: l.account_id == self.stock_output_account)

        self.assertEqual(valuation_line.credit, -100)
        self.assertEqual(valuation_line.debit, 0)
        self.assertEqual(stock_out_line.credit, 0)
        self.assertEqual(stock_out_line.debit, -100)

    def test_dropship_return_accounts_1(self):
        """
        When returning a dropshipped move, make sure the correct accounts are used
        """
        # pylint: disable=bad-whitespace
        self.product1.categ_id.property_cost_method = 'fifo'

        move1 = self._make_dropship_move(self.product1, 2, unit_cost=10)
        move2 = self._make_return(move1, 2)

        # First: Input -> Valuation
        # Second: Valuation -> Output
        origin_svls = move1.stock_valuation_layer_ids.sorted('quantity', reverse=True)
        # First: Output -> Valuation
        # Second: Valuation -> Input
        return_svls = move2.stock_valuation_layer_ids.sorted('quantity', reverse=True)
        self.assertEqual(len(origin_svls), 2)
        self.assertEqual(len(return_svls), 2)

        acc_in, acc_out, acc_valuation = self.stock_input_account, self.stock_output_account, self.stock_valuation_account

        # Dropshipping should be: Input -> Output
        self.assertRecordValues(origin_svls[0].account_move_id.line_ids, [
            {'account_id': acc_in.id,        'debit': 0,  'credit': 20},
            {'account_id': acc_valuation.id, 'debit': 20, 'credit': 0},
        ])
        self.assertRecordValues(origin_svls[1].account_move_id.line_ids, [
            {'account_id': acc_valuation.id, 'debit': 0,  'credit': 20},
            {'account_id': acc_out.id,       'debit': 20, 'credit': 0},
        ])
        # Return should be: Output -> Input
        self.assertRecordValues(return_svls[0].account_move_id.line_ids, [
            {'account_id': acc_out.id,       'debit': 0,  'credit': 20},
            {'account_id': acc_valuation.id, 'debit': 20, 'credit': 0},
        ])
        self.assertRecordValues(return_svls[1].account_move_id.line_ids, [
            {'account_id': acc_valuation.id, 'debit': 0,  'credit': 20},
            {'account_id': acc_in.id,        'debit': 20, 'credit': 0},
        ])

    def test_dropship_return_accounts_2(self):
        """
        When returning a dropshipped move, make sure the correct accounts are used
        """
        # pylint: disable=bad-whitespace
        self.product1.categ_id.property_cost_method = 'fifo'

        move1 = self._make_dropship_move(self.product1, 2, unit_cost=10)

        # return to WH/Stock
        stock_return_picking = Form(self.env['stock.return.picking']\
            .with_context(active_ids=[move1.picking_id.id], active_id=move1.picking_id.id, active_model='stock.picking'))
        stock_return_picking = stock_return_picking.save()
        stock_return_picking.product_return_moves.quantity = 2
        stock_return_picking.location_id = self.stock_location
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].qty_done = 2
        return_pick._action_done()
        move2 = return_pick.move_ids

        # First: Input -> Valuation
        # Second: Valuation -> Output
        origin_svls = move1.stock_valuation_layer_ids.sorted('quantity', reverse=True)
        # Only one: Output -> Valuation
        return_svl = move2.stock_valuation_layer_ids
        self.assertEqual(len(origin_svls), 2)
        self.assertEqual(len(return_svl), 1)

        acc_in, acc_out, acc_valuation = self.stock_input_account, self.stock_output_account, self.stock_valuation_account

        # Dropshipping should be: Input -> Output
        self.assertRecordValues(origin_svls[0].account_move_id.line_ids, [
            {'account_id': acc_in.id,        'debit': 0,  'credit': 20},
            {'account_id': acc_valuation.id, 'debit': 20, 'credit': 0},
        ])
        self.assertRecordValues(origin_svls[1].account_move_id.line_ids, [
            {'account_id': acc_valuation.id, 'debit': 0,  'credit': 20},
            {'account_id': acc_out.id,       'debit': 20, 'credit': 0},
        ])
        # Return should be: Output -> Valuation
        self.assertRecordValues(return_svl.account_move_id.line_ids, [
            {'account_id': acc_out.id,       'debit': 0,  'credit': 20},
            {'account_id': acc_valuation.id, 'debit': 20, 'credit': 0},
        ])
