from datetime import timedelta
from freezegun import freeze_time

from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import users
from odoo import Command


class TestLotValuation(TestStockValuationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.product_avco.create({
            **cls.product_common_vals,
            'name': 'Lot Valuated Product',
            'categ_id': cls.category_avco.id,
            'lot_valuated': True,
            'tracking': 'lot',
            'standard_price': 10,
        })
        cls.lot1, cls.lot2, cls.lot3 = cls.env['stock.lot'].create([
            {'name': 'lot1', 'product_id': cls.product.id},
            {'name': 'lot2', 'product_id': cls.product.id},
            {'name': 'lot3', 'product_id': cls.product.id},
        ])

    def test_lot_normal_1(self):
        """ Lots have their own valuation """
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product, 10, 7, lot_ids=[self.lot3])
        self.assertAlmostEqual(self.product.standard_price, 6.0)
        self.assertEqual(self.lot1.standard_price, 5)
        self._make_out_move(self.product, 2, lot_ids=[self.lot1])

        # lot1 has a cost different than the product it self. So a out move should recompute the
        # product cost
        self.assertAlmostEqual(self.product.standard_price, 6.1111111, places=2)  # 110 % 18 = 6.1111111
        self.assertEqual(self.lot1.total_value, 15)
        self.assertEqual(self.lot1.product_qty, 3)
        self.assertEqual(self.lot1.standard_price, 5)
        quant = self.lot1.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        self.assertEqual(quant.value, 15)
        self.assertEqual(self.lot2.total_value, 25)
        self.assertEqual(self.lot2.product_qty, 5)
        self.assertEqual(self.lot2.standard_price, 5)
        quant = self.lot2.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        self.assertEqual(quant.value, 25)
        self.assertEqual(self.lot3.total_value, 70)
        self.assertEqual(self.lot3.product_qty, 10)
        self.assertEqual(self.lot3.standard_price, 7)
        quant = self.lot3.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        self.assertEqual(quant.value, 70)

    def test_lot_normal_2(self):
        """ Lot standard_price is set at creation (not at delivery) """
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        out_move = self._make_out_move(self.product, 2, lot_ids=[self.lot3])

        # lot3.standard_price was set to product.standard_price at lot creation (= 10)
        # The out move uses lot3.standard_price = 10, not the current product price
        self.assertEqual(self.product.qty_available, 8)
        self.assertEqual(self.lot3.product_qty, -2)
        self.assertEqual(out_move.value / out_move.quantity, 10)

    def test_lot_normal_3(self):
        """ Test lot valuation and dropship"""
        self._make_dropship_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])

        # Dropship: product goes supplier->customer (not via stock)
        # Net effect: lots have 0 stock, so total_value = 0
        self.assertEqual(self.lot1.total_value, 0)
        self.assertEqual(self.lot1.standard_price, 5)
        self.assertEqual(self.lot2.total_value, 0)
        self.assertEqual(self.lot2.standard_price, 5)
        self.assertEqual(self.product.total_value, 0)

    def test_real_time_valuation(self):
        """ Test account move lines for real_time valuation with lot_valuated """
        self.product.categ_id = self.category_avco_auto
        self._use_inventory_location_accounting()

        in_move1 = self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2], location_id=self.inventory_location.id)
        in_move2 = self._make_in_move(self.product, 10, 7, lot_ids=[self.lot3], location_id=self.inventory_location.id)
        out_move = self._make_out_move(self.product, 2, lot_ids=[self.lot1], location_dest_id=self.inventory_location.id)

        # in_move1: 10u@5 = 50 total
        self.assertRecordValues(in_move1.account_move_id.line_ids, [
            {'debit': 0.0, 'credit': 50.0},
            {'debit': 50.0, 'credit': 0.0},
        ])
        # in_move2: 10u@7 = 70 total
        self.assertRecordValues(in_move2.account_move_id.line_ids, [
            {'debit': 0.0, 'credit': 70.0},
            {'debit': 70.0, 'credit': 0.0},
        ])
        # out_move: 2u of lot1@5 = 10 total
        self.assertRecordValues(out_move.account_move_id.line_ids, [
            {'debit': 0.0, 'credit': 10.0},
            {'debit': 10.0, 'credit': 0.0},
        ])

    def test_disable_lot_valuation(self):
        """ Disabling lot valuation: product valuation unchanged, lot values go to 0.
            product valuation is standard """
        self.product.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product.product_tmpl_id.standard_price = 10

        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product, 10, 7, lot_ids=[self.lot3])
        self._make_out_move(self.product, 2, lot_ids=[self.lot1])
        self._make_out_move(self.product, 2, lot_ids=[self.lot3])
        self._make_in_move(self.product, 9, 8, lot_ids=[self.lot1, self.lot2, self.lot3])

        self.assertEqual(self.product.total_value, 250)
        self.assertEqual(self.product.qty_available, 25)
        self.assertEqual(self.lot1.total_value, 60)
        self.assertEqual(self.lot1.product_qty, 6)
        self.assertEqual(self.lot2.total_value, 80)
        self.assertEqual(self.lot2.product_qty, 8)
        self.assertEqual(self.lot3.total_value, 110)
        self.assertEqual(self.lot3.product_qty, 11)

        self.product.product_tmpl_id.lot_valuated = False

        self.assertEqual(self.product.total_value, 250)
        self.assertEqual(self.product.qty_available, 25)
        self.assertEqual(self.lot1.total_value, 0)
        self.assertEqual(self.lot2.total_value, 0)
        self.assertEqual(self.lot3.total_value, 0)

    def test_enable_lot_valuation(self):
        """ Enabling lot valuation should compute lot values from existing stock.
            product valuation is standard """
        self.product.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product.product_tmpl_id.standard_price = 10

        self.product.lot_valuated = False

        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product, 10, 7, lot_ids=[self.lot3])
        self._make_out_move(self.product, 2, lot_ids=[self.lot1])
        self._make_out_move(self.product, 2, lot_ids=[self.lot3])
        self._make_in_move(self.product, 9, 8, lot_ids=[self.lot1, self.lot2, self.lot3])

        self.assertEqual(self.product.total_value, 250)
        self.assertEqual(self.product.qty_available, 25)
        self.assertEqual(self.lot1.total_value, 0)
        self.assertEqual(self.lot2.total_value, 0)
        self.assertEqual(self.lot3.total_value, 0)

        self.product.product_tmpl_id.lot_valuated = True

        self.assertEqual(self.product.total_value, 250)
        self.assertEqual(self.product.qty_available, 25)
        self.assertEqual(self.lot1.total_value, 60)
        self.assertEqual(self.lot1.product_qty, 6)
        self.assertEqual(self.lot2.total_value, 80)
        self.assertEqual(self.lot2.product_qty, 8)
        self.assertEqual(self.lot3.total_value, 110)
        self.assertEqual(self.lot3.product_qty, 11)

    def test_enable_lot_valuation_variant(self):
        """ test enabling the lot valuation for template with multiple variant"""
        self.size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'value_ids': [
                Command.create({'name': 'S'}),
                Command.create({'name': 'M'}),
                Command.create({'name': 'L'}),
            ]
        })
        template = self.env['product.template'].create({
            'name': 'Sofa',
            'tracking': 'lot',
            'is_storable': True,
            'uom_id': self.uom.id,
            'categ_id': self.category_avco.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.size_attribute.id,
                    'value_ids': [
                        Command.link(self.size_attribute.value_ids[0].id),
                        Command.link(self.size_attribute.value_ids[1].id),
                ]}),
            ],
        })
        productA, productB = template.product_variant_ids
        lotA_1, lotA_2, lotB_1, lotB_2 = self.env['stock.lot'].create([
            {'name': 'lot1', 'product_id': productA.id},
            {'name': 'lot2', 'product_id': productA.id},
            {'name': 'lot1', 'product_id': productB.id},
            {'name': 'lot2', 'product_id': productB.id},
        ])
        self._make_in_move(productA, 10, 5, lot_ids=[lotA_1, lotA_2])
        self._make_in_move(productA, 10, 7, lot_ids=[lotA_2])
        self._make_in_move(productB, 10, 4, lot_ids=[lotB_1, lotB_2])
        self._make_in_move(productB, 10, 8, lot_ids=[lotB_2])
        # productA = 20u 120, productB = 20u 120
        # A_1 = 5u 25, A_2 = 15u 95, B_1 =5u 20, B_2 =15u 100
        self._make_out_move(productA, 2, lot_ids=[lotA_1, lotA_2])
        self._make_out_move(productB, 4, lot_ids=[lotB_1, lotB_2])
        # productA = 18u 108, productB = 16u 96
        # A_1 = 4u 20, A_2 = 14u 88.67, B_1 =3u 12, B_2 =13u 86.67
        self._make_in_move(productA, 6, 8, lot_ids=[lotA_1, lotA_2])
        self._make_in_move(productB, 6, 8, lot_ids=[lotB_1, lotB_2])
        # productA = 24u 156, productB = 22u 144
        # A_1 = 7u 44, A_2 = 17u 112.67, B_1 =6u 36, B_2 =16u 110.67

        self.assertEqual(productA.total_value, 156)
        self.assertEqual(productA.qty_available, 24)
        self.assertEqual(productB.total_value, 144)
        self.assertEqual(productB.qty_available, 22)

        template.lot_valuated = True

        # product totals are now sum of lot totals
        self.assertEqual(productA.total_value, 156.67)
        self.assertEqual(productA.qty_available, 24)
        self.assertEqual(productB.total_value, 146.67)
        self.assertEqual(productB.qty_available, 22)

        # Lot values computed via lot-specific AVCO
        self.assertEqual(lotA_1.product_qty, 7)
        self.assertEqual(lotA_1.total_value, 44)
        self.assertEqual(lotA_2.product_qty, 17)
        self.assertEqual(lotA_2.total_value, 112.67)
        self.assertEqual(lotB_1.product_qty, 6)
        self.assertEqual(lotB_1.total_value, 36)
        self.assertEqual(lotB_2.product_qty, 16)
        self.assertEqual(lotB_2.total_value, 110.67)

    def test_enforce_lot_receipt(self):
        """ lot/sn is mandatory on receipt if the product is lot valuated """
        self.picking_type_in.use_create_lots = False
        with self.assertRaises(UserError):
            self._make_in_move(self.product, 10, 5)

    def test_enforce_lot_inventory(self):
        """ lot/sn is mandatory on quant if the product is lot valuated """
        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product.id,
            'inventory_quantity': 10
        })
        with self.assertRaises(UserError):
            inventory_quant.action_apply_inventory()

    def test_inventory_adjustment_existing_lot(self):
        """ If a lot exist, inventory takes its cost, if not, takes standard price """
        self.product.product_tmpl_id.standard_price = 10
        shelf1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1])
        inventory_quant = self.env['stock.quant'].create({
            'location_id': shelf1.id,
            'product_id': self.product.id,
            'lot_id': self.lot1.id,
            'inventory_quantity': 1
        })

        inventory_quant.action_apply_inventory()
        # lot1 now has 11u at standard_price=5 (from the in move)
        self.assertEqual(self.lot1.standard_price, 5)
        self.assertEqual(self.lot1.product_qty, 11)
        self.assertEqual(self.lot1.total_value, 55)

    def test_inventory_adjustment_new_lot(self):
        """ If a lot exist, inventory takes its cost, if not, takes standard price """
        shelf1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1])
        self._make_in_move(self.product, 10, 9, lot_ids=[self.lot2])
        self.assertEqual(self.product.standard_price, 7)
        lot4 = self.env['stock.lot'].create({
            'name': 'lot4',
            'product_id': self.product.id,
        })
        inventory_quant = self.env['stock.quant'].create({
            'location_id': shelf1.id,
            'product_id': self.product.id,
            'lot_id': lot4.id,
            'inventory_quantity': 1,
        })

        inventory_quant.action_apply_inventory()
        # lot4 was created when product.standard_price = 7
        self.assertEqual(lot4.standard_price, 7)
        self.assertEqual(lot4.product_qty, 1)
        self.assertEqual(lot4.total_value, 7)

    def test_change_standard_price(self):
        """ Changing product's standard price will reevaluate all lots """
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product, 8, 7, lot_ids=[self.lot3])
        self._make_in_move(self.product, 6, 8, lot_ids=[self.lot2, self.lot3])
        self.assertEqual(self.lot1.total_value, 25)
        self.assertEqual(self.lot2.total_value, 49)
        self.assertEqual(self.lot3.total_value, 80)
        self.product.product_tmpl_id.standard_price = 10

        self.assertEqual(self.lot1.total_value, 50)
        self.assertEqual(self.lot1.standard_price, 10)
        self.assertEqual(self.lot2.total_value, 80)
        self.assertEqual(self.lot2.standard_price, 10)
        self.assertEqual(self.lot3.total_value, 110)
        self.assertEqual(self.lot3.standard_price, 10)

    def test_value_multicompanies(self):
        """ Test having multiple layers on different companies give a correct value"""
        c1 = self.company
        c2 = self.other_company
        self.product.product_tmpl_id.with_company(c2).categ_id.property_cost_method = 'average'
        # c1 moves
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product, 8, 7, lot_ids=[self.lot3])
        self._make_in_move(self.product, 6, 8, lot_ids=[self.lot2, self.lot3])
        # c2 move
        self._make_in_move(self.product, 9, 6, company=c2, lot_ids=[self.lot1, self.lot2, self.lot3])
        self.assertEqual(self.lot1.with_company(c1).total_value, 25)
        self.assertEqual(self.lot2.with_company(c1).total_value, 49)
        self.assertEqual(self.lot3.with_company(c1).total_value, 80)
        self.assertEqual(self.lot1.with_company(c2).total_value, 18)
        self.assertEqual(self.lot2.with_company(c2).total_value, 18)
        self.assertEqual(self.lot3.with_company(c2).total_value, 18)

    def test_change_cost_method(self):
        """ Prevent changing cost method if lot valuated """
        # change cost method on category
        self._make_in_move(self.product, 1, 5, lot_ids=[self.lot1])
        self._make_in_move(self.product, 1, 7, lot_ids=[self.lot1])
        self._make_out_move(self.product, 1, lot_ids=[self.lot1])
        self.assertEqual(self.lot1.total_value, 6)

        self.product.categ_id = self.category_fifo
        self.assertEqual(self.lot1.total_value, 7)

        self.product.categ_id.property_cost_method = 'average'
        self.assertEqual(self.lot1.total_value, 6)

    def test_change_lot_cost(self):
        """ Changing the cost of a lot will reevaluate the lot """
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product, 10, 7, lot_ids=[self.lot3])
        self._make_out_move(self.product, 2, lot_ids=[self.lot1])
        self.assertAlmostEqual(self.product.standard_price, (15 + 25 + 70) / 18, places=2)
        self.lot1.standard_price = 10
        self.assertEqual(self.lot1.total_value, 30)
        self.assertEqual(self.lot1.product_qty, 3)
        self.assertEqual(self.lot1.standard_price, 10)
        # product cost should be updated as well
        self.assertAlmostEqual(self.product.standard_price, (30 + 25 + 70) / 18, places=2)
        # rest remains unchanged
        self.assertEqual(self.lot2.total_value, 25)
        self.assertEqual(self.lot2.product_qty, 5)
        self.assertEqual(self.lot2.standard_price, 5)
        self.assertEqual(self.lot3.total_value, 70)
        self.assertEqual(self.lot3.product_qty, 10)
        self.assertEqual(self.lot3.standard_price, 7)

    def test_lot_move_update_after_done(self):
        """validate a stock move. Edit the move line in done state."""
        move = self._make_in_move(self.product, 8, 5, create_picking=True, lot_ids=[self.lot1, self.lot2])
        move.picking_id.action_toggle_is_locked()
        # 4 lot 1, 6 lot 2 and 3 lot 3
        move.move_line_ids = [
            Command.update(move.move_line_ids[1].id, {'quantity': 6}),
            Command.create({
                'product_id': self.product.id,
                'product_uom_id': self.product.uom_id.id,
                'quantity': 3,
                'lot_id': self.lot3.id,
            }),
        ]
        move.value_manual = 13 * 5  # Small trick to simulate move revaluation
        self.assertEqual(self.lot1.product_qty, 4)
        self.assertEqual(self.lot2.product_qty, 6)
        self.assertEqual(self.lot3.product_qty, 3)
        self.assertEqual(self.lot1.total_value, 4 * 5)
        self.assertEqual(self.lot2.total_value, 6 * 5)
        self.assertEqual(self.lot3.total_value, 3 * 5)

    def test_lot_average_vacuum(self):
        """ Test lot AVCO with negative stock fill """
        with freeze_time(fields.Datetime.now() - timedelta(seconds=10)):
            self.product.standard_price = 9
        self._make_out_move(self.product, 2, lot_ids=[self.lot1])
        self._make_out_move(self.product, 3, lot_ids=[self.lot2])
        self._make_in_move(self.product, 10, 7, lot_ids=[self.lot3])

        self.assertEqual(self.lot3.standard_price, 7)
        self._make_in_move(self.product, 10, 5, lot_ids=[self.lot1, self.lot2])
        self.assertEqual(self.lot1.standard_price, 5)
        self.assertEqual(self.lot3.standard_price, 7)

    def test_return_lot_valuated(self):
        with freeze_time(fields.Datetime.now() - timedelta(seconds=10)):
            self.product.standard_price = 9
        move = self._make_out_move(self.product, 3, create_picking=True, lot_ids=[self.lot1, self.lot2, self.lot3])
        self.assertEqual(self.product.total_value, -27)
        self.assertEqual(move.value, 27)
        return_move = self._make_return(move, 2)
        self.assertEqual(return_move.state, 'done')
        # Return move has positive value (in move restoring 2 lots)
        self.assertEqual(return_move.value, 18)
        self.assertEqual(self.product.total_value, -9)

    def test_lot_inventory(self):
        """Test setting quantity for a new lot via inventory adjustment fallback on the product cost
        The product is set to avco cost """
        self.product.standard_price = 9
        lot = self.env['stock.lot'].create({
            'product_id': self.product.id,
            'name': 'test',
        })
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'lot_id': lot.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 3
        })
        quant.action_apply_inventory()
        self.assertEqual(lot.standard_price, 9)
        self.assertEqual(lot.total_value, 27)

    def test_lot_valuation_after_tracking_update(self):
        """
        Test that 'lot_valuated' is set to False when the tracking is changed to 'none'.
        """
        # update the tracking from product.product
        self.assertEqual(self.product.tracking, 'lot')
        self.product.lot_valuated = True
        self.assertTrue(self.product.lot_valuated)
        self.product.tracking = 'none'
        self.assertFalse(self.product.lot_valuated)
        # update the tracking from product.template
        self.product.tracking = 'lot'
        self.product.lot_valuated = True
        self.product.product_tmpl_id.tracking = 'none'
        self.assertFalse(self.product.lot_valuated)

    def test_lot_valuation_lot_product_price_diff(self):
        """
        This test ensure that when the product.standard_price and the lot.standard_price differ,
        no discrepancy is created when setting lot_valuated to True.
        When lot_valuated is set to True, the lot.standard_price is updated to match with the product.standard_price
        """
        self.product.lot_valuated = False
        self.product.standard_price = 1

        lot = self.env['stock.lot'].create({
            'product_id': self.product.id,
            'name': 'LOT-WITH-COST',
            'standard_price': 2,
        })
        lot2 = self.env['stock.lot'].create({
            'product_id': self.product.id,
            'name': 'LOT-NO-COST',
        })
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'lot_id': lot.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 10,
        })
        quant.action_apply_inventory()

        self.assertEqual(self.product.total_value, 10)  # 10 units with product standard_price = $1
        self.assertEqual(lot.standard_price, 2)
        self.assertEqual(lot2.standard_price, 0)

        self.product.lot_valuated = True

        self.assertEqual(lot2.standard_price, 1)
        self.assertEqual(lot.standard_price, 1)  # lot.standard_price was updated
        self.assertEqual(lot.total_value, 10)

        quant.inventory_quantity = 0
        quant.action_apply_inventory()

        self.assertEqual(lot.total_value, 0)

    def test_lot_valuated_update_from_product_product(self):
        tmpl1 = self.product.product_tmpl_id
        tmpl1.standard_price = 1
        tmpl1.tracking = 'lot'
        tmpl1.lot_valuated = False

        lot = self.env['stock.lot'].create({
            'product_id': self.product.id,
            'name': 'test',
        })
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'lot_id': lot.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 1
        })
        quant.action_apply_inventory()

        self.assertEqual(self.product.qty_available, 1)
        self.assertEqual(self.product.total_value, 1)
        self.assertEqual(lot.product_qty, 1)  # physical qty always reflects stock, regardless of lot_valuated
        self.assertEqual(lot.total_value, 0)

        self.product.lot_valuated = True  # The update is done from the ProductProduct model
        self.env.cr.flush()
        self.assertEqual(lot.product_qty, 1)
        self.assertEqual(lot.total_value, 1)
        self.assertEqual(self.product.qty_available, 1)
        self.assertEqual(self.product.total_value, 1)

        self.product.lot_valuated = False  # Check that
        self.env.cr.flush()

        self.assertEqual(self.product.qty_available, 1)
        self.assertEqual(self.product.total_value, 1)
        self.assertEqual(lot.product_qty, 1)  # physical qty unchanged, only valuation is cleared
        self.assertEqual(lot.total_value, 0)

    def test_no_lot_valuation_if_quant_without_lot(self):
        """ Ensure that it is not possible to set lot_valuated to True
        if there is valued quantities without lot in on hand.
        This is because you can't validate a move without lot when lot valuation is enabled.
        The user would hence be unable to use the quant without lot anyway.
        """
        self.product.tracking = 'none'
        self.product.lot_valuated = False
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 1
        })
        quant.action_apply_inventory()

        self.product.tracking = 'lot'
        with self.assertRaises(UserError):
            self.product.lot_valuated = True

    def test_lot_revaluation_with_remaining_qty(self):
        """
        Test manual lot revaluation: setting lot.standard_price updates total_value.
        After disabling lot_valuated, lot total_value becomes 0.
        """
        self._make_in_move(self.product, 7, lot_ids=[self.lot1])

        # lot1 has stock; setting standard_price updates total_value
        self.lot1.standard_price = 15
        self.assertEqual(self.lot1.standard_price, 15)
        self.assertEqual(self.lot1.total_value, 7 * 15)

        # After disabling lot_valuated, lot total_value = 0
        self.product.lot_valuated = False
        self.assertEqual(self.lot1.total_value, 0)
        self.assertGreater(self.product.total_value, 0)

    @users('inventory_user')
    def test_deliveries_with_minimal_access_rights(self):
        """ Check that an inventory user is able to process a delivery. """
        move = self._make_out_move(self.product, 5, create_picking=True, lot_ids=[self.lot1])
        delivery = move.picking_id
        self.assertEqual(delivery.state, 'done')
        self.assertRecordValues(delivery.move_ids, [
            {'quantity': 5.0, 'state': 'done', 'lot_ids': self.lot1.ids}
        ])

    def test_in_move_lot_valuated_standard_price(self):
        """Check that when the standard price is used to value a move
        with a single lot, the standard price of the lot is used instead of the
        standard price of the product
        """
        self.product.categ_id.property_valuation = 'real_time'
        self._make_in_move(self.product, 1, 10, lot_ids=[self.lot1])
        self._make_in_move(self.product, 1, 16, lot_ids=[self.lot2])
        self.assertEqual(self.product.standard_price, 13)
        self.assertEqual(self.lot1.standard_price, 10)
        self.assertEqual(self.lot2.standard_price, 16)

        # Second receipt for lot1 at same cost: lot price unchanged, product AVCO recalculated
        self._make_in_move(self.product, 1, 10, lot_ids=[self.lot1])
        self.assertEqual(self.lot1.standard_price, 10)
        self.assertEqual(self.product.standard_price, 12)
