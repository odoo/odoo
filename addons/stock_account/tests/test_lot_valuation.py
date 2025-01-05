# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo import Command


class TestLotValuation(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        cls.product1.write({
            'lot_valuated': True,
            'tracking': 'lot',
        })
        cls.lot1, cls.lot2, cls.lot3 = cls.env['stock.lot'].create([
            {'name': 'lot1', 'product_id': cls.product1.id},
            {'name': 'lot2', 'product_id': cls.product1.id},
            {'name': 'lot3', 'product_id': cls.product1.id},
        ])

    def test_lot_normal_1(self):
        """ Lots have their own valuation """
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 10, 7, lot_ids=[self.lot3])
        self.assertEqual(self.product1.standard_price, 6.0)
        self.assertEqual(self.lot1.standard_price, 5)
        self._make_out_move(self.product1, 2, lot_ids=[self.lot1])

        # lot1 has a cost different than the product it self. So a out move should recompute the
        # product cost
        self.assertEqual(self.product1.standard_price, 6.11)
        self.assertEqual(len(self.lot1.stock_valuation_layer_ids), 2)
        self.assertEqual(self.lot1.stock_valuation_layer_ids.mapped('lot_id'), self.lot1)
        self.assertEqual(self.lot1.value_svl, 15)
        self.assertEqual(self.lot1.quantity_svl, 3)
        self.assertEqual(self.lot1.standard_price, 5)
        quant = self.lot1.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        self.assertEqual(quant.value, 15)
        self.assertEqual(len(self.lot2.stock_valuation_layer_ids), 1)
        self.assertEqual(self.lot2.stock_valuation_layer_ids.mapped('lot_id'), self.lot2)
        self.assertEqual(self.lot2.value_svl, 25)
        self.assertEqual(self.lot2.quantity_svl, 5)
        self.assertEqual(self.lot2.standard_price, 5)
        quant = self.lot2.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        self.assertEqual(quant.value, 25)
        self.assertEqual(len(self.lot3.stock_valuation_layer_ids), 1)
        self.assertEqual(self.lot3.stock_valuation_layer_ids.mapped('lot_id'), self.lot3)
        self.assertEqual(self.lot3.value_svl, 70)
        self.assertEqual(self.lot3.quantity_svl, 10)
        self.assertEqual(self.lot3.standard_price, 7)
        quant = self.lot3.quant_ids.filtered(lambda q: q.location_id.usage == 'internal')
        self.assertEqual(quant.value, 70)

    def test_lot_normal_2(self):
        """ Product valuation is a fallback in case lot is created at delivery """
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        out_move = self._make_out_move(self.product1, 2, lot_ids=[self.lot3])

        self.assertEqual(self.product1.value_svl, 40)
        self.assertEqual(self.product1.quantity_svl, 8)

        self.assertEqual(out_move.stock_valuation_layer_ids.unit_cost, 5)
        self.assertEqual(self.lot3.value_svl, -10)
        self.assertEqual(self.lot3.quantity_svl, -2)

    def test_lot_normal_3(self):
        """ Test lot valuation and dropship"""
        self._make_dropship_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])

        layers1 = self.lot1.stock_valuation_layer_ids
        layers2 = self.lot2.stock_valuation_layer_ids
        self.assertEqual(len(layers1), 2)
        self.assertEqual(len(layers2), 2)
        product_layers = self.product1.stock_valuation_layer_ids
        self.assertEqual(product_layers, layers1 | layers2)
        self.assertEqual(layers1[0].value, 25)
        self.assertEqual(layers1[1].value, -25)
        self.assertEqual(layers2[0].value, 25)
        self.assertEqual(layers2[1].value, -25)

    def test_real_time_valuation(self):
        """ Test account move lines contains lot """
        self.stock_input_account, self.stock_output_account, self.stock_valuation_account, self.expense_account, self.stock_journal = _create_accounting_data(self.env)
        self.product1.categ_id.write({
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 10, 7, lot_ids=[self.lot3])
        self._make_out_move(self.product1, 2, lot_ids=[self.lot1])
        aml = self.product1.stock_valuation_layer_ids.account_move_id.line_ids
        self.assertRecordValues(aml, [
            {'debit': 0.0, 'credit': 25.0},
            {'debit': 25.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 25.0},
            {'debit': 25.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 70.0},
            {'debit': 70.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 10.0},
            {'debit': 10.0, 'credit': 0.0},
            ])

    def test_disable_lot_valuation(self):
        """ Disabling lot valuation should compansate lots layer untouched a one product only layer.
            product valuation is standard """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10

        m_in1 = self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        m_in2 = self._make_in_move(self.product1, 10, 7, lot_ids=[self.lot3])
        m_out1 = self._make_out_move(self.product1, 2, lot_ids=[self.lot1])
        m_out2 = self._make_out_move(self.product1, 2, lot_ids=[self.lot3])
        m_in3 = self._make_in_move(self.product1, 9, 8, lot_ids=[self.lot1, self.lot2, self.lot3])

        self.assertEqual(self.product1.value_svl, 250)
        self.assertEqual(self.product1.quantity_svl, 25)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('lot_id'), self.lot1 | self.lot2 | self.lot3)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 8)
        self.assertEqual(self.lot1.value_svl, 60)
        self.assertEqual(self.lot1.quantity_svl, 6)
        self.assertEqual(self.lot2.value_svl, 80)
        self.assertEqual(self.lot2.quantity_svl, 8)
        self.assertEqual(self.lot3.value_svl, 110)
        self.assertEqual(self.lot3.quantity_svl, 11)
        self.assertEqual(len(m_in1.stock_valuation_layer_ids), 2)
        self.assertEqual(len(m_in2.stock_valuation_layer_ids), 1)
        self.assertEqual(len(m_out1.stock_valuation_layer_ids), 1)
        self.assertEqual(len(m_out2.stock_valuation_layer_ids), 1)
        self.assertEqual(len(m_in3.stock_valuation_layer_ids), 3)

        self.product1.product_tmpl_id.lot_valuated = False

        self.assertEqual(self.product1.value_svl, 250)
        self.assertEqual(self.product1.quantity_svl, 25)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 12)
        self.assertEqual(self.lot1.value_svl, 0)
        self.assertEqual(self.lot1.quantity_svl, 0)
        self.assertEqual(self.lot2.value_svl, 0)
        self.assertEqual(self.lot2.quantity_svl, 0)
        self.assertEqual(self.lot3.value_svl, 0)
        self.assertEqual(self.lot3.quantity_svl, 0)
        remaining_qty_layers = self.env['stock.valuation.layer'].search([
            ('product_id', '=', self.product1.id),
            ('remaining_qty', '>', 0),
        ])
        self.assertTrue(remaining_qty_layers)
        self.assertFalse(remaining_qty_layers.lot_id)

    def test_enable_lot_valuation(self):
        """ Disabling lot valuation should left the lots layer untouched.
            product valuation is standard """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.standard_price = 10

        self.product1.lot_valuated = False

        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 10, 7, lot_ids=[self.lot3])
        self._make_out_move(self.product1, 2, lot_ids=[self.lot1])
        self._make_out_move(self.product1, 2, lot_ids=[self.lot3])
        self._make_in_move(self.product1, 9, 8, lot_ids=[self.lot1, self.lot2, self.lot3])

        self.assertEqual(self.product1.value_svl, 250)
        self.assertEqual(self.product1.quantity_svl, 25)
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 5)
        self.assertEqual(self.lot1.value_svl, 0)
        self.assertEqual(self.lot1.quantity_svl, 0)
        self.assertEqual(self.lot2.value_svl, 0)
        self.assertEqual(self.lot2.quantity_svl, 0)
        self.assertEqual(self.lot3.value_svl, 0)
        self.assertEqual(self.lot3.quantity_svl, 0)

        self.product1.product_tmpl_id.lot_valuated = True

        self.assertEqual(self.product1.value_svl, 250)
        self.assertEqual(self.product1.quantity_svl, 25)
        self.assertEqual(self.product1.stock_valuation_layer_ids.lot_id, self.lot1 | self.lot2 | self.lot3)

        # 5 original + 1 empty stock + 3 for the lots
        self.assertEqual(len(self.product1.stock_valuation_layer_ids), 9)
        self.assertEqual(self.lot1.value_svl, 60)
        self.assertEqual(self.lot1.quantity_svl, 6)
        self.assertEqual(self.lot2.value_svl, 80)
        self.assertEqual(self.lot2.quantity_svl, 8)
        self.assertEqual(self.lot3.value_svl, 110)
        self.assertEqual(self.lot3.quantity_svl, 11)

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
            'uom_id': self.uom_unit.id,
            'categ_id': self.env.ref('product.product_category_goods').id,
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
        self._make_out_move(productA, 2, lot_ids=[lotA_1, lotA_2])
        self._make_out_move(productB, 4, lot_ids=[lotB_1, lotB_2])
        self._make_in_move(productA, 6, 8, lot_ids=[lotA_1, lotA_2])
        self._make_in_move(productB, 6, 8, lot_ids=[lotB_1, lotB_2])

        self.assertEqual(productA.value_svl, 156)
        self.assertEqual(productA.quantity_svl, 24)
        self.assertEqual(len(productA.stock_valuation_layer_ids), 4)
        self.assertEqual(productB.value_svl, 144)
        self.assertEqual(productB.quantity_svl, 22)
        self.assertEqual(len(productB.stock_valuation_layer_ids), 4)

        template.lot_valuated = True

        self.assertEqual(productA.value_svl, 156)
        self.assertEqual(productA.quantity_svl, 24)
        self.assertEqual(productB.value_svl, 144.1)  # 144.1 because of multiplying quantity with rounded standard price
        self.assertEqual(productB.quantity_svl, 22)

        # 4 original + 1 empty stock + 2 for the lots
        self.assertEqual(len(productA.stock_valuation_layer_ids), 7)
        self.assertEqual(len(productB.stock_valuation_layer_ids), 7)
        self.assertEqual(lotA_1.value_svl, 45.5)
        self.assertEqual(lotA_1.quantity_svl, 7)
        self.assertEqual(lotA_2.value_svl, 110.5)
        self.assertEqual(lotA_2.quantity_svl, 17)
        self.assertEqual(lotB_1.value_svl, 39.3)
        self.assertEqual(lotB_1.quantity_svl, 6)
        self.assertEqual(lotB_2.value_svl, 104.8)
        self.assertEqual(lotB_2.quantity_svl, 16)

    def test_enforce_lot_receipt(self):
        """ lot/sn is mandatory on receipt if the product is lot valuated """
        with self.assertRaises(UserError):
            self._make_in_move(self.product1, 10, 5)

    def test_enforce_lot_inventory(self):
        """ lot/sn is mandatory on quant if the product is lot valuated """
        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
            'inventory_quantity': 10
        })
        with self.assertRaises(UserError):
            stock_confirmation_action = inventory_quant.action_apply_inventory()
            stock_confirmation_wizard_form = Form(
                self.env['stock.track.confirmation'].with_context(
                    **stock_confirmation_action['context'])
            )

            stock_confirmation_wizard = stock_confirmation_wizard_form.save()
            stock_confirmation_wizard.action_confirm()

    def test_inventory_adjustment_existing_lot(self):
        """ If a lot exist, inventory takes its cost, if not, takes standard price """
        self.product1.product_tmpl_id.standard_price = 10
        shelf1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1])
        inventory_quant = self.env['stock.quant'].create({
            'location_id': shelf1.id,
            'product_id': self.product1.id,
            'lot_id': self.lot1.id,
            'inventory_quantity': 1
        })

        inventory_quant.action_apply_inventory()
        layers = self.lot1.stock_valuation_layer_ids
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers.mapped('unit_cost'), [5, 5])

    def test_inventory_adjustment_new_lot(self):
        """ If a lot exist, inventory takes its cost, if not, takes standard price """
        shelf1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        lot4 = self.env['stock.lot'].create({
            'name': 'lot4',
            'product_id': self.product1.id,
        })
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1])
        self._make_in_move(self.product1, 10, 9, lot_ids=[self.lot2])
        self.assertEqual(self.product1.standard_price, 7)
        inventory_quant = self.env['stock.quant'].create({
            'location_id': shelf1.id,
            'product_id': self.product1.id,
            'lot_id': lot4.id,
            'inventory_quantity': 1,
        })

        inventory_quant.action_apply_inventory()
        layers = lot4.stock_valuation_layer_ids
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers.unit_cost, 7)

    def test_change_standard_price(self):
        """ Changing product's standard price will reevaluate all lots """
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 8, 7, lot_ids=[self.lot3])
        self._make_in_move(self.product1, 6, 8, lot_ids=[self.lot2, self.lot3])
        self.assertEqual(self.lot1.value_svl, 25)
        self.assertEqual(self.lot2.value_svl, 49)
        self.assertEqual(self.lot3.value_svl, 80)
        self.product1.product_tmpl_id.standard_price = 10

        self.assertEqual(self.lot1.value_svl, 50)
        self.assertEqual(self.lot1.standard_price, 10)
        self.assertEqual(self.lot2.value_svl, 80)
        self.assertEqual(self.lot2.standard_price, 10)
        self.assertEqual(self.lot3.value_svl, 110)
        self.assertEqual(self.lot3.standard_price, 10)

    def test_value_multicompanies(self):
        """ Test having multiple layers on different companies give a correct value"""
        c1 = self.env.company
        c2 = self.env['res.company'].create({
            'name': 'Test Company',
        })
        self.product1.product_tmpl_id.with_company(c2).categ_id.property_cost_method = 'average'
        # c1 moves
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 8, 7, lot_ids=[self.lot3])
        self._make_in_move(self.product1, 6, 8, lot_ids=[self.lot2, self.lot3])
        # c2 move
        c2_stock_loc = self.env['stock.warehouse'].search([('company_id', '=', c2.id)], limit=1).lot_stock_id
        move1 = self.env['stock.move'].with_company(c2).create({
            'name': 'IN 10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': c2_stock_loc.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 9.0,
            'price_unit': 6.0,
        })
        move1._action_confirm()
        move1.move_line_ids.unlink()
        move1.move_line_ids = [Command.create({
            'product_id': self.product1.id,
            'quantity': 3.0,
            'lot_id': lot.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': c2_stock_loc.id,
        }) for lot in [self.lot1, self.lot2, self.lot3]]
        move1.picked = True
        move1._action_done()
        self.assertEqual(self.lot1.with_company(c1).value_svl, 25)
        self.assertEqual(self.lot2.with_company(c1).value_svl, 49)
        self.assertEqual(self.lot3.with_company(c1).value_svl, 80)
        self.assertEqual(self.lot1.with_company(c2).value_svl, 18)
        self.assertEqual(self.lot2.with_company(c2).value_svl, 18)
        self.assertEqual(self.lot3.with_company(c2).value_svl, 18)

    def test_prevent_change_cost_method(self):
        """ Prevent changing cost method if lot valuated """
        # change cost method on category
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        with self.assertRaises(UserError):
            self.product1.categ_id.property_cost_method = 'fifo'

        new_cat = self.env['product.category'].create({
            'name': 'New Category',
            'property_cost_method': 'fifo',
        })
        with self.assertRaises(UserError):
            self.product1.categ_id = new_cat

    def test_change_lot_cost(self):
        """ Changing the cost of a lot will reevaluate the lot """
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 10, 7, lot_ids=[self.lot3])
        self._make_out_move(self.product1, 2, lot_ids=[self.lot1])
        self.lot1.standard_price = 10
        self.assertEqual(len(self.lot1.stock_valuation_layer_ids), 3)
        self.assertEqual(self.lot1.stock_valuation_layer_ids.mapped('lot_id'), self.lot1)
        self.assertEqual(self.lot1.value_svl, 30)
        self.assertEqual(self.lot1.quantity_svl, 3)
        self.assertEqual(self.lot1.standard_price, 10)
        # product cost should be updated al well
        self.assertEqual(self.product1.standard_price, 6.94)
        # rest remains unchanged
        self.assertEqual(len(self.lot2.stock_valuation_layer_ids), 1)
        self.assertEqual(self.lot2.stock_valuation_layer_ids.mapped('lot_id'), self.lot2)
        self.assertEqual(self.lot2.value_svl, 25)
        self.assertEqual(self.lot2.quantity_svl, 5)
        self.assertEqual(self.lot2.standard_price, 5)
        self.assertEqual(len(self.lot3.stock_valuation_layer_ids), 1)
        self.assertEqual(self.lot3.stock_valuation_layer_ids.mapped('lot_id'), self.lot3)
        self.assertEqual(self.lot3.value_svl, 70)
        self.assertEqual(self.lot3.quantity_svl, 10)
        self.assertEqual(self.lot3.standard_price, 7)

    def test_average_manual_lot_revaluation(self):
        self.product1.categ_id.property_cost_method = 'average'

        self._make_in_move(self.product1, 8, 5, lot_ids=[self.lot1, self.lot2])
        self._make_in_move(self.product1, 6, 7, lot_ids=[self.lot1])
        self.assertEqual(self.lot1.standard_price, 6.2)
        self.assertEqual(self.lot1.value_svl, 62)
        self.assertEqual(self.product1.standard_price, 5.86)

        Form(self.env['stock.valuation.layer.revaluation'].with_context({
            'default_product_id': self.product1.id,
            'default_company_id': self.env.company.id,
            'default_added_value': 8.0,
            'default_lot_id': self.lot1.id,
        })).save().action_validate_revaluation()

        layers = self.lot1.stock_valuation_layer_ids
        self.assertEqual(len(layers), 3)
        self.assertEqual(layers.lot_id, self.lot1)
        self.assertEqual(self.lot1.standard_price, 7, "lot1 cost changed")
        self.assertEqual(self.lot1.value_svl, 70, "lot1 value changed")
        self.assertEqual(self.lot2.standard_price, 5, "lot2 cost remains unchanged")
        self.assertEqual(self.product1.standard_price, 6.43, "product cost changed too")

    def test_lot_move_update_after_done(self):
        """validate a stock move. Edit the move line in done state."""
        move = self._make_in_move(self.product1, 8, 5, create_picking=True, lot_ids=[self.lot1, self.lot2])
        move.picking_id.action_toggle_is_locked()
        move.move_line_ids = [
            Command.update(move.move_line_ids[1].id, {'quantity': 6}),
            Command.create({
                'product_id': self.product1.id,
                'product_uom_id': self.product1.uom_id.id,
                'quantity': 3,
                'lot_id': self.lot3.id,
            }),
        ]
        self.assertRecordValues(self.lot1.stock_valuation_layer_ids, [
            {'value': 20, 'lot_id': self.lot1.id, 'quantity': 4},
        ])
        self.assertRecordValues(self.lot2.stock_valuation_layer_ids, [
            {'value': 20, 'lot_id': self.lot2.id, 'quantity': 4},
            {'value': 10, 'lot_id': self.lot2.id, 'quantity': 2},
        ])
        self.assertRecordValues(self.lot3.stock_valuation_layer_ids, [
            {'value': 15, 'lot_id': self.lot3.id, 'quantity': 3},
        ])

    def test_lot_change_lot_after_done(self):
        """validate a stock move. Change the lot or a quant on a move line in done state should
        update the valuation accordingly. The product standard_price should be updated as well."""
        move = self._make_in_move(self.product1, 8, 5, create_picking=True, lot_ids=[self.lot1, self.lot2])
        move.picking_id.action_toggle_is_locked()
        move.move_line_ids = [
            Command.update(move.move_line_ids[1].id, {'lot_id': self.lot3.id}),
        ]
        self.assertRecordValues(move.stock_valuation_layer_ids, [
            {'value': 20, 'lot_id': self.lot1.id, 'quantity': 4},
            {'value': 20, 'lot_id': self.lot2.id, 'quantity': 4},
            {'value': -20, 'lot_id': self.lot2.id, 'quantity': -4},
            {'value': 20, 'lot_id': self.lot3.id, 'quantity': 4},
        ])
        self.assertEqual(self.product1.standard_price, 5)

        self._make_in_move(self.product1, 4, 4, create_picking=True, lot_ids=[self.lot3])
        self.assertEqual(self.product1.standard_price, 4.67)

        move = self._make_out_move(self.product1, 3, create_picking=True, lot_ids=[self.lot1])
        self.assertEqual(self.product1.standard_price, 4.56)

        quant = self.env['stock.quant'].search([
            ('lot_id', '=', self.lot3.id),
            ('location_id', '=', self.stock_location.id),
        ])
        move.picking_id.action_toggle_is_locked()
        move.move_line_ids = [
            Command.update(move.move_line_ids.id, {'quant_id': quant.id}),
        ]
        self.assertEqual(self.product1.standard_price, 4.72)

        self.assertRecordValues(move.stock_valuation_layer_ids, [
            {'value': -15, 'lot_id': self.lot1.id, 'quantity': -3},
            {'value': 15, 'lot_id': self.lot1.id, 'quantity': 3},
            {'value': -13.5, 'lot_id': self.lot3.id, 'quantity': -3},
        ])

    def test_lot_fifo_vaccum(self):
        """ Test lot fifo vacuum"""
        self.product1.standard_price = 9
        self._make_out_move(self.product1, 2, lot_ids=[self.lot1])
        self._make_out_move(self.product1, 3, lot_ids=[self.lot2])
        self._make_in_move(self.product1, 10, 7, lot_ids=[self.lot3])
        self.assertEqual(self.lot1.standard_price, 9)
        self.assertEqual(self.lot3.standard_price, 7)
        self._make_in_move(self.product1, 10, 5, lot_ids=[self.lot1, self.lot2])
        self.assertEqual(self.lot1.standard_price, 5)
        self.assertEqual(self.lot3.standard_price, 7)

    def test_return_lot_valuated(self):
        self.product1.standard_price = 9
        move = self._make_out_move(self.product1, 3, create_picking=True, lot_ids=[self.lot1, self.lot2, self.lot3])
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_id=move.picking_id.id, active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        self.assertEqual(len(return_pick.move_ids.move_line_ids), 2)
        return_pick.move_ids.picked = True
        return_pick._action_done()
        self.assertRecordValues(return_pick.move_ids.stock_valuation_layer_ids, [
            {'value': 9, 'lot_id': self.lot1.id, 'quantity': 1},
            {'value': 9, 'lot_id': self.lot2.id, 'quantity': 1},
        ])

    def test_new_lot_inventory_std(self):
        """Test setting quantity for a new lot via inventory adjustment fallback on the product cost
        The product is set to standard cost """
        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.standard_price = 9
        lot = self.env['stock.lot'].create({
            'product_id': self.product1.id,
            'name': 'test',
        })
        quant = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'lot_id': lot.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 3
        })
        quant.action_apply_inventory()
        self.assertEqual(lot.standard_price, 9)
        self.assertEqual(lot.value_svl, 27)

    def test_new_lot_inventory_avco(self):
        """Test setting quantity for a new lot via inventory adjustment fallback on the product cost
        The product is set to avco cost """
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.standard_price = 9
        lot = self.env['stock.lot'].create({
            'product_id': self.product1.id,
            'name': 'test',
        })
        quant = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'lot_id': lot.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 3
        })
        quant.action_apply_inventory()
        self.assertEqual(lot.standard_price, 9)
        self.assertEqual(lot.value_svl, 27)

    def test_lot_valuation_after_tracking_update(self):
        """
        Test that 'lot_valuated' is set to False when the tracking is changed to 'none'.
        """
        # update the tracking from product.product
        self.assertEqual(self.product1.tracking, 'lot')
        self.product1.lot_valuated = True
        self.assertTrue(self.product1.lot_valuated)
        self.product1.tracking = 'none'
        self.assertFalse(self.product1.lot_valuated)
        # update the tracking from product.template
        self.product1.tracking = 'lot'
        self.product1.lot_valuated = True
        self.product1.product_tmpl_id.tracking = 'none'
        self.assertFalse(self.product1.product_tmpl_id.lot_valuated)
