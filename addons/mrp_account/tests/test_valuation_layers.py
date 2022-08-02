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

    def test_change_produced_qty_in_done_mo_fifo(self):
        """Change in produced quantity then check done mo's valuation layers"""
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self._make_in_move(self.component, 1, 50)
        mo = self._make_mo(self.bom, 1)
        self._produce(mo)
        mo.button_mark_done()
        mo.action_toggle_is_locked()
        mo.write({'qty_producing': 5.0})
        valuation_domain = mo.action_view_stock_valuation_layers().get('domain')
        layers = self.env['stock.valuation.layer'].search(valuation_domain)
        main_product_cost = sum(layers.filtered(lambda l: l.product_id.id == self.product1.id).mapped('value'))
        main_product_quantity = sum(layers.filtered(lambda l: l.product_id.id == self.product1.id).mapped('quantity'))
        main_product_cost_per_unit = main_product_cost / main_product_quantity
        component_cost = sum(layers.filtered(lambda l: l.product_id.id == self.component.id).mapped('value'))
        self.assertEqual(main_product_cost, 50.0)
        self.assertEqual(main_product_cost_per_unit, 10)
        self.assertEqual(component_cost, -50.0)

    def test_change_component_qty_in_done_mo_fifo(self):
        """Change in component quantity then check done mo's valuation layers"""
        self.component.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self._make_in_move(self.component, 1, 10)
        mo = self._make_mo(self.bom, 1)
        self._produce(mo)
        mo.button_mark_done()
        mo.action_toggle_is_locked()
        mo.move_raw_ids.write({'quantity_done': 5.0})
        valuation_domain = mo.action_view_stock_valuation_layers().get('domain')
        layers = self.env['stock.valuation.layer'].search(valuation_domain)
        main_product_cost = sum(layers.filtered(lambda l: l.product_id.id == self.product1.id).mapped('value'))
        main_product_quantity = sum(layers.filtered(lambda l: l.product_id.id == self.product1.id).mapped('quantity'))
        main_product_cost_per_unit = main_product_cost / main_product_quantity
        component_cost = sum(layers.filtered(lambda l: l.product_id.id == self.component.id).mapped('value'))
        self.assertEqual(main_product_cost, 50.0)
        self.assertEqual(main_product_cost_per_unit, 50)
        self.assertEqual(component_cost, -50.0)
