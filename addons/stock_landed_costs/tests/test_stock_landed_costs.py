# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


@common.at_install(False)
@common.post_install(True)
class TestStockLandedCosts(common.TransactionCase):

    def setUp(self):
        super(TestStockLandedCosts, self).setUp()

        # In order to test the landed costs feature of stock, I create a landed cost, confirm it and check its account move created
        self.Product = self.env['product.product']
        self.Picking = self.env['stock.picking']
        self.StockLandedCost = self.env['stock.landed.cost']
        self.StockMove = self.env['stock.move']
        self.product_uom_unit_id = self.ref('product.product_uom_unit')
        self.picking_type_id = self.ref('stock.picking_type_out')
        self.stock_location_id = self.ref('stock.stock_location_stock')
        self.stock_location_customers_id = self.ref('stock.stock_location_customers')

         # Create Journal Account
        self.expenses_journal = self.env['account.journal'].create({
            'name': 'Vendor Bills - Test',
            'code': 'TEXJ',
            'type': 'purchase',
            'refund_sequence': True})

        # I create 2 products with different volume and gross weight and configure them for real_time valuation and real price costing method
        self.product_laptop = self.Product.create({
            'name': 'Laptops',
            'cost_method': 'real',
            'valuation': 'real_time',
            'weight': 10,
            'volume': 1})
        self.product_watch = self.Product.create({
            'name': 'Digital Watch',
            'cost_method': 'real',
            'valuation': 'real_time',
            'weight': 20,
            'volume': 1.5})

        #I create 2 picking moving those products
        self.picking_out_1 = self.Picking.create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.stock_location_customers_id})
        self.StockMove.create({
            'name': self.product_laptop.name,
            'product_id': self.product_laptop.id,
            'product_uom_qty': 5,
            'product_uom': self.product_uom_unit_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.stock_location_customers_id,
            'picking_id': self.picking_out_1.id})

        self.picking_out_2 = self.Picking.create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.stock_location_customers_id})
        self.StockMove.create({
            'name': self.product_watch.name,
            'product_id': self.product_watch.id,
            'product_uom_qty': 10,
            'product_uom': self.product_uom_unit_id,
            'location_id': self.stock_location_id,
            'location_dest_id': self.stock_location_customers_id,
            'picking_id': self.picking_out_2.id})

        self.labour_equal = self._create_services('Labour Cost')
        self.brokerage_quantity = self._create_services('Brokerage Cost')
        self.transportation_weight = self._create_services('Transportation Cost')
        self.packaging_volume = self._create_services('Packaging Cost')

        #I create a landed cost for those 2 pickings
        self.stock_landed_cost = self.StockLandedCost.create(dict(
            picking_ids=[(6, 0, [self.picking_out_1.id, self.picking_out_2.id])],
            account_journal_id=self.expenses_journal.id,
            cost_lines=[(0, 0, {'name': 'equal split',
                                'split_method': 'equal',
                                'price_unit': 10,
                                'product_id': self.labour_equal.id}),
                        (0, 0, {'name': 'split by quantity',
                                'split_method': 'by_quantity',
                                'price_unit': 150,
                                'product_id': self.brokerage_quantity.id}),
                        (0, 0, {'name': 'split by weight',
                                'split_method': 'by_weight',
                                'price_unit': 250,
                                'product_id': self.transportation_weight.id}),
                        (0, 0, {'name': 'split by volume',
                                'split_method': 'by_volume',
                                'price_unit': 20,
                                'product_id': self.packaging_volume.id})
                        ]
        ))

    def test_stock_landed_costs(self):
        """ Test landed cost on outgoing shipment """
        #
        # (A) Purchase product

        #         Services           Quantity       Weight      Volume
        #         -----------------------------------------------------
        #         1. Laptops             5            10          1
        #         2. Digital Watch       10           20          1.5

        # (B) Add some costs on purchase

        #         Services           Amount     Split Method
        #         -------------------------------------------
        #         1. Labour            10        By Equal
        #         2. Brokerage         150       By Quantity
        #         3. Transportation    250       By Weight
        #         4. Packaging         20        By Volume

        #I compute the landed cost  using Compute button
        self.stock_landed_cost.compute_landed_cost()

        valid_vals = {
            'equal': 5.0,
            'by_quantity_laptop': 50.0,
            'by_quantity_watch': 100.0,
            'by_weight_laptop': 50.0,
            'by_weight_watch': 200,
            'by_volume_laptop': 5.0,
            'by_volume_watch': 15.0}

        # Check valuation adjustment line recognized or not
        self._validate_additional_landed_cost_lines(self.stock_landed_cost, valid_vals)

        #I confirm the landed cost
        self.stock_landed_cost.button_validate()
        #I check that the landed cost is now "Closed" and that it has an accounting entry
        self.assertEqual(self.stock_landed_cost.state, 'done', 'Landed costs should be in done state')
        self.assertTrue(self.stock_landed_cost.account_move_id, 'Landed costs should be available account move')
        self.assertEqual(len(self.stock_landed_cost.account_move_id.line_ids), 16, 'Landed cost account move lines should be 16 instead of %s' % (len(self.stock_landed_cost.account_move_id.line_ids)))

    def _create_services(self, name):
        return self.Product.create({
            'name': name,
            'landed_cost_ok': True,
            'type': 'service'})

    def _validate_additional_landed_cost_lines(self, stock_landed_cost, valid_vals):
        for valuation in stock_landed_cost.valuation_adjustment_lines:
            add_cost = valuation.additional_landed_cost
            split_method = valuation.cost_line_id.split_method
            product = valuation.move_id.product_id
            if split_method == 'equal':
                self.assertEqual(add_cost, valid_vals['equal'], self._error_message(valid_vals['equal'], add_cost))
            elif split_method == 'by_quantity' and product == self.product_laptop:
                self.assertEqual(add_cost, valid_vals['by_quantity_laptop'], self._error_message(valid_vals['by_quantity_laptop'], add_cost))
            elif split_method == 'by_quantity' and product == self.product_watch:
                self.assertEqual(add_cost, valid_vals['by_quantity_watch'], self._error_message(valid_vals['by_quantity_watch'], add_cost))
            elif split_method == 'by_weight' and product == self.product_laptop:
                self.assertEqual(add_cost, valid_vals['by_weight_laptop'], self._error_message(valid_vals['by_weight_laptop'], add_cost))
            elif split_method == 'by_weight' and product == self.product_watch:
                self.assertEqual(add_cost, valid_vals['by_weight_watch'], self._error_message(valid_vals['by_weight_watch'], add_cost))
            elif split_method == 'by_volume' and product == self.product_laptop:
                self.assertEqual(add_cost, valid_vals['by_volume_laptop'], self._error_message(valid_vals['by_volume_laptop'], add_cost))
            elif split_method == 'by_volume' and product == self.product_watch:
                self.assertEqual(add_cost, valid_vals['by_volume_watch'], self._error_message(valid_vals['by_volume_watch'], add_cost))

    def _error_message(self, actucal_cost, computed_cost):
        return 'Additional Landed Cost should be %s instead of %s' % (actucal_cost, computed_cost)
