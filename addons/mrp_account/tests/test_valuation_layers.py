# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Implementation of "INVENTORY VALUATION TESTS (With valuation layers)" spreadsheet. """

from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon
from odoo.tests import Form


class TestMrpValuationCommon(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMrpValuationCommon, cls).setUpClass()
        cls.component_category = cls.env['product.category'].create(
            {'name': 'category2'}
        )
        cls.component = cls.env['product.product'].create({
            'name': 'component1',
            'type': 'product',
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
        mo = mo.procurement_group_id.mrp_production_ids[-1]
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
            'type': 'product',
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
        mo = mo.procurement_group_id.mrp_production_ids[-1]
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
        mo = mo.procurement_group_id.mrp_production_ids[-1]
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
        self._make_out_move(self.product1, 1)
        self.assertEqual(self.product1.value_svl, 8.8)

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
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'product_uom_id': self.product1.uom_id.id,
                'location_id': self.customer_location.id,
                'location_dest_id': self.stock_location.id,
            })]
        })
        receipt.button_validate()

        self.assertEqual(receipt.state, 'done')
        self.assertRecordValues(receipt.move_ids, [
            {'product_id': self.component.id, 'quantity_done': 1, 'state': 'done'},
        ])
        self.assertEqual(self.component.qty_available, 1)
        self.assertEqual(self.component.value_svl, 1424)
