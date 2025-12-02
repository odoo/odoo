# Part of Odoo. See LICENSE file for full copyright and licensing details.
""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from unittest import skip

from odoo.fields import Command
from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo.tests import Form
from odoo.tests.common import tagged


@skip('Temporary to fast merge new valuation')
class TestMrpValuationCommon(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMrpValuationCommon, cls).setUpClass()
        cls.component_category = cls.env['product.category'].create(
            {'name': 'category2'}
        )
        cls.component = cls.env['product.product'].create({
            'name': 'component1',
            'is_storable': True,
            'categ_id': cls.component_category.id,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product1.id,
            'product_tmpl_id': cls.product1.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.component.id, 'product_qty': 1})
            ]})

    def _make_mo(self, bom, quantity=1):
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = bom.product_id
        mo_form.bom_id = bom
        mo_form.product_qty = quantity
        mo = mo_form.save()
        mo.action_confirm()
        return mo

    def _produce(self, mo, quantity=0):
        mo_form = Form(mo)
        if not quantity:
            quantity = mo.product_qty - mo.qty_produced
        mo_form.qty_producing += quantity
        mo = mo_form.save()


@skip('Temporary to fast merge new valuation')
class TestMrpValuationStandard(TestMrpValuationCommon):
    def test_fifo_fifo_1(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo, 1)
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo = mo.production_group_id.production_ids[-1]
        self.assertEqual(self.component.value_svl, 20)
        self.assertEqual(self.product1.value_svl, 10)
        self.assertEqual(self.component.quantity_svl, 1)
        self.assertEqual(self.product1.quantity_svl, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)

    def test_fifo_fifo_2(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)
        self._make_out_move(self.product1, 1)
        self.assertEqual(self.product1.value_svl, 15)

    def test_fifo_byproduct(self):
        """ Check that a MO byproduct with a cost share calculates correct svl """
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)

        # add byproduct
        byproduct_cost_share = 10
        byproduct = self.env['product.product'].create({
            'name': 'byproduct',
            'is_storable': True,
            'categ_id': self.product1.product_tmpl_id.categ_id.id,
        })
        self.bom.write({
            'byproduct_ids': [(0, 0, {'product_id': byproduct.id, 'product_uom_id': self.uom_unit.id, 'product_qty': 1, 'cost_share': byproduct_cost_share})]
        })

        mo = self._make_mo(self.bom, 2)
        self._produce(mo, 1)
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo = mo.production_group_id.production_ids[-1]
        self.assertEqual(self.component.value_svl, 20)
        self.assertEqual(self.product1.value_svl, 10 * (100 - byproduct_cost_share) / 100)
        self.assertEqual(byproduct.value_svl, 10 * byproduct_cost_share / 100)
        self.assertEqual(self.component.quantity_svl, 1)
        self.assertEqual(self.product1.quantity_svl, 1)
        self.assertEqual(byproduct.quantity_svl, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 30 * (100 - byproduct_cost_share) / 100)
        self.assertEqual(byproduct.value_svl, 30 * byproduct_cost_share / 100)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)
        self.assertEqual(byproduct.quantity_svl, 2)

    def test_fifo_unbuild(self):
        """ This test creates an MO and then creates an unbuild
        orders and checks the stock valuation.
        """
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        # ---------------------------------------------------
        #       MO
        # ---------------------------------------------------
        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 20)
        # ---------------------------------------------------
        #       Unbuild
        # ---------------------------------------------------
        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = mo
        unbuild_form.save().action_unbuild()
        self.assertEqual(self.component.value_svl, 30)

    def test_fifo_produce_deliver_return_unbuild(self):
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.component.write({
            'type': 'consu',
            'standard_price': 10.0,
        })

        mo = self._make_mo(self.bom, 1)
        self._produce(mo)
        mo.button_mark_done()

        out_move = self._make_out_move(self.product1, 1.0, create_picking=True)
        self._make_return(out_move, 1.0)

        unbuild_form = Form(self.env['mrp.unbuild'])
        unbuild_form.mo_id = mo
        unbuild_form.save().action_unbuild()

        self.assertRecordValues(self.product1.stock_valuation_layer_ids, [
            {'value': 10.0, 'quantity': 1.0, 'remaining_value': 0.0, 'remaining_qty': 0.0},
            {'value': -10.0, 'quantity': -1.0, 'remaining_value': 0.0, 'remaining_qty': 0.0},
            {'value': 10.0, 'quantity': 1.0, 'remaining_value': 0.0, 'remaining_qty': 0.0},
            {'value': -10.0, 'quantity': -1.0, 'remaining_value': 0.0, 'remaining_qty': 0.0},
        ])

    def test_fifo_avco_1(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo, 1)
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo = mo.production_group_id.production_ids[-1]
        self.assertEqual(self.component.value_svl, 20)
        self.assertEqual(self.product1.value_svl, 10)
        self.assertEqual(self.component.quantity_svl, 1)
        self.assertEqual(self.product1.quantity_svl, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)

    def test_fifo_avco_2(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)
        self._make_out_move(self.product1, 1)
        self.assertEqual(self.product1.value_svl, 15)

    def test_fifo_std_1(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.standard_price = 8.8

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo, 1)
        mo._post_inventory()
        self.assertEqual(self.component.value_svl, 20)
        self.assertEqual(self.product1.value_svl, 8.8)
        self.assertEqual(self.component.quantity_svl, 1)
        self.assertEqual(self.product1.quantity_svl, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 8.8 * 2)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)

    def test_fifo_std_2(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.standard_price = 8.8

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 8.8 * 2)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)
        self._make_out_move(self.product1, 1)
        self.assertEqual(self.product1.value_svl, 8.8)

    def test_std_avco_1(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.component.standard_price = 8.8

        self._make_in_move(self.component, 1)
        self._make_in_move(self.component, 1)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo, 1)
        mo._post_inventory()
        self.assertEqual(self.component.value_svl, 8.8)
        self.assertEqual(self.product1.value_svl, 8.8)
        self.assertEqual(self.component.quantity_svl, 1)
        self.assertEqual(self.product1.quantity_svl, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 8.8 * 2)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)

    def test_std_avco_2(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.component.standard_price = 8.8

        self._make_in_move(self.component, 1)
        self._make_in_move(self.component, 1)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 8.8 * 2)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)
        self.assertEqual(self.product1.standard_price, 8.8)

        self._make_out_move(self.product1, 1)
        self.assertEqual(self.product1.value_svl, 8.8)

        # Update component price
        self.component.standard_price = 0

        self._make_in_move(self.component, 3)
        mo = self._make_mo(self.bom, 3)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.product1.value_svl, 8.8)
        self.assertEqual(self.product1.quantity_svl, 4)
        self.assertEqual(self.product1.standard_price, 2.2)

    def test_std_std_1(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.component.standard_price = 8.8
        self.product1.standard_price = 7.2

        self._make_in_move(self.component, 1)
        self._make_in_move(self.component, 1)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo, 1)
        mo._post_inventory()
        self.assertEqual(self.component.value_svl, 8.8)
        self.assertEqual(self.product1.value_svl, 7.2)
        self.assertEqual(self.component.quantity_svl, 1)
        self.assertEqual(self.product1.quantity_svl, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 7.2 * 2)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)

    def test_std_std_2(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.component.standard_price = 8.8
        self.product1.standard_price = 7.2

        self._make_in_move(self.component, 1)
        self._make_in_move(self.component, 1)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 7.2 * 2)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)
        self._make_out_move(self.product1, 1)
        self.assertEqual(self.product1.value_svl, 7.2)

    def test_avco_avco_1(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo, 1)
        mo._post_inventory()
        self.assertEqual(self.component.value_svl, 15)
        self.assertEqual(self.product1.value_svl, 15)
        self.assertEqual(self.component.quantity_svl, 1)
        self.assertEqual(self.product1.quantity_svl, 1)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)

    def test_avco_avco_2(self):
        self.component.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        self._make_in_move(self.component, 1, 10)
        self._make_in_move(self.component, 1, 20)
        mo = self._make_mo(self.bom, 2)
        self._produce(mo)
        mo.button_mark_done()
        self.assertEqual(self.component.value_svl, 0)
        self.assertEqual(self.product1.value_svl, 30)
        self.assertEqual(self.component.quantity_svl, 0)
        self.assertEqual(self.product1.quantity_svl, 2)
        self._make_out_move(self.product1, 1)
        self.assertEqual(self.product1.value_svl, 15)

    def test_validate_draft_kit(self):
        """
        Create a draft receipt, add a kit to its move lines and directly
        validate it. From client side, such a behaviour is possible with
        the Barcode app.
        """
        self.component.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.type = 'consu'
        self.bom.type = 'phantom'
        self.component.standard_price = 1424

        receipt = self.env['stock.picking'].create({
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'state': 'draft',
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'quantity': 1,
                'product_uom_id': self.product1.uom_id.id,
                'location_id': self.customer_location.id,
                'location_dest_id': self.stock_location.id,
            })]
        })
        receipt.move_ids.picked = True
        receipt.button_validate()

        self.assertEqual(receipt.state, 'done')
        self.assertRecordValues(receipt.move_ids, [
            {'product_id': self.component.id, 'quantity': 1, 'state': 'done'},
        ])
        self.assertEqual(self.component.qty_available, 1)
        self.assertEqual(self.component.value_svl, 1424)

    def test_average_cost_unbuild_with_byproducts(self):
        """ Ensures that an unbuild for a manufacturing order using avg cost products won't copy
            the value of the main product for every byproduct line, regardless of their real value.
        """
        byproduct = self.env['product.product'].create({
            'name': 'byproduct',
            'is_storable': True,
            'categ_id': self.product1.categ_id.id,
        })
        self.product1.categ_id.property_cost_method = 'average'
        self.component.standard_price = 100

        self.bom.write({'byproduct_ids': [
            Command.create({'product_id': byproduct.id, 'product_qty': 1, 'cost_share': 20}),
        ]})

        self._make_in_move(self.component, 1)
        production = self._make_mo(self.bom, 1)
        self._produce(production)
        production.button_mark_done()

        self.assertRecordValues(production.move_finished_ids.stock_valuation_layer_ids, [
            {'product_id': self.product1.id, 'value': 80},
            {'product_id': byproduct.id, 'value': 20},
        ])

        action = production.button_unbuild()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.product_qty = 1
        unbuild = wizard.save()
        unbuild.action_validate()

        unbuild_svls = self.env['stock.valuation.layer'].search([('reference', '=', unbuild.name)])
        self.assertRecordValues(unbuild_svls, [
            {'product_id': self.product1.id, 'value': -80},
            {'product_id': byproduct.id, 'value': -20},
            {'product_id': self.component.id, 'value': 100}
        ])


@tagged("post_install", "-at_install")
@skip('Temporary to fast merge new valuation')
class TestMrpStockValuation(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.production_account = cls.env['account.account'].create({
            'name': 'Cost of Production',
            'code': 'ProductionCost',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        cls.product1.categ_id.property_stock_account_production_cost_id = cls.production_account

    def _get_production_cost_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.production_account.id),
        ], order='date, id')

    def test_production_account_00(self):
        """Create move into/out of a production location, test we create account
        entries with the Production Cost account.
        """
        production_location = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.env.company.id)])
        picking_type_in = self.env.ref('stock.picking_type_in')
        picking_type_out = self.env.ref('stock.picking_type_out')

        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.standard_price = 10

        # move into production location
        production_in = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': production_location.id,
            'picking_type_id': picking_type_out.id,
        })
        move = self.env['stock.move'].create({
            'picking_id': production_in.id,
            'location_id': self.stock_location.id,
            'location_dest_id': production_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        production_in.action_confirm()
        move.quantity = 10
        move.picked = True
        production_in.button_validate()

        in_aml = self._get_production_cost_move_lines()
        self.assertEqual(in_aml.debit, 100)
        self.assertEqual(in_aml.product_id, self.product1)

        # move out of production location
        production_out = self.env['stock.picking'].create({
            'location_id': production_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': picking_type_in.id,
        })
        move = self.env['stock.move'].create({
            'picking_id': production_out.id,
            'location_id': production_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        production_out.action_confirm()
        move.quantity = 10
        move.picked = True
        production_out.button_validate()

        out_aml = self._get_production_cost_move_lines() - in_aml
        self.assertEqual(out_aml.credit, 100)
        self.assertEqual(in_aml.product_id, self.product1)

    def test_production_account_01(self):
        """Create move into/out of a production location with its own stock accounts
        test we create account entries with those accounts instead of Production
        Cost account.
        """
        production_out_account = self.env['account.account'].create({
            'name': 'Production out',
            'code': 'ProductionOut',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        production_in_account = self.env['account.account'].create({
            'name': 'Production in',
            'code': 'ProductionIn',
            'account_type': 'liability_current',
            'reconcile': True,
        })

        production_location = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.env.company.id)])
        production_location.write({
            'valuation_in_account_id': production_in_account.id,
            'valuation_out_account_id': production_out_account.id,
        })
        picking_type_in = self.env.ref('stock.picking_type_in')
        picking_type_out = self.env.ref('stock.picking_type_out')

        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.standard_price = 10

        # move into production location
        production_in = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': production_location.id,
            'picking_type_id': picking_type_out.id,
        })
        move = self.env['stock.move'].create({
            'picking_id': production_in.id,
            'location_id': self.stock_location.id,
            'location_dest_id': production_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        production_in.action_confirm()
        move.quantity = 10
        move.picked = True
        production_in.button_validate()

        in_aml = self.env['account.move.line'].search([
            ('account_id', '=', production_in_account.id),
        ], order='date, id')
        self.assertEqual(in_aml.debit, 100)
        self.assertEqual(in_aml.product_id, self.product1)

        # move out of production location
        production_out = self.env['stock.picking'].create({
            'location_id': production_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': picking_type_in.id,
        })
        move = self.env['stock.move'].create({
            'picking_id': production_out.id,
            'location_id': production_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        production_out.action_confirm()
        move.quantity = 10
        move.picked = True
        production_out.button_validate()

        out_aml = self.env['account.move.line'].search([
            ('account_id', '=', production_out_account.id),
        ], order='date, id')
        self.assertEqual(out_aml.credit, 100)
        self.assertEqual(in_aml.product_id, self.product1)

    def test_average_cost_unbuild_component_change_move_qty(self):
        """
        Ensures that we can modify the quantity on the stock move of the components after an unbuild
        """
        avco_category = self.env['product.category'].create({
            'name': 'AVCO',
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
        })
        comp_1, final_product = self.product1, self.product2
        (comp_1 | final_product).categ_id = avco_category
        final_product_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': comp_1.id,
                'product_qty': 1,
            })],
        })
        mo = self.env['mrp.production'].create({
            'product_qty': 1.0,
            'bom_id': final_product_bom.id,
        })
        mo.action_confirm()
        mo.button_mark_done()
        action = mo.button_unbuild()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.product_qty = 1
        unbuild = wizard.save()
        unbuild.action_validate()
        # check that changing the quantity on the move form does not create an error
        comp_move = mo.unbuild_ids.produce_line_ids.filtered(lambda move: move.product_id.id == comp_1.id)
        with Form(comp_move.move_line_ids[0]) as form:
            form.quantity = 0
