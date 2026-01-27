# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_mrp.tests import test_sale_mrp_flow
from odoo.fields import Command
from odoo.tests import common, Form


@common.tagged('post_install', '-at_install')
class TestSaleMrpFlow(test_sale_mrp_flow.TestSaleMrpFlowCommon):

    def test_kit_cost_calculation(self):
        """ Check that the average cost price is computed correctly after SO confirmation:
            BOM 1:
                - 1 unit of “super kit”:
                    - 2 units of “component a”
            BOM 2:
                - 1 unit of “component a”:
                    - 3 units of "component b"
            1 unit of "component b" = $10
            1 unit of "super kit" = 2 * 3 * $10 = *$60
        """
        super_kit = self._cls_create_product('Super Kit', self.uom_unit)
        (super_kit + self.component_a + self.component_b).categ_id.property_cost_method = 'average'
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.component_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': self.component_b.id,
                'product_qty': 3.0,
            })]
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': super_kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': self.component_a.id,
                'product_qty': 2.0,
            })]
        })
        self.component_b.standard_price = 10
        self.component_a.button_bom_cost()
        super_kit.button_bom_cost()
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = super_kit
        so = so_form.save()
        self.assertEqual(so.order_line.purchase_price, 60)
        so.action_confirm()
        self.assertEqual(so.order_line.purchase_price, 60)

    def test_kit_cost_calculation_2(self):
        """ Check that the average cost price is computed correctly after receipt validation:
            Lovely KIT BOM for 10:
                - 1O unit of Kit $50
                - 10 units of “component b” $10
            -> $60 per Lovely Kit
            SUB KIT BOM:
                - 1 units of “component a” 1 x $30 = $30
                - 2 units of “component b” 2 x $10 = $20
            -> $50 per SUB Kit
        """
        sub_kit, kit = self._cls_create_product('Sub Kit', self.uom_unit), self._cls_create_product('Lovely Kit', self.uom_ten)
        kit.uom_ids = [Command.set([self.uom_unit.id, self.uom_ten.id])]
        self.product_category.property_cost_method = 'average'
        (kit + sub_kit + self.component_a + self.component_b).categ_id = self.product_category
        self.env['mrp.bom'].create([
            {
                'product_tmpl_id': sub_kit.product_tmpl_id.id,
                'product_qty': 1.0,
                'type': 'phantom',
                'bom_line_ids': [
                    Command.create({
                        'product_id': self.component_a.id,
                        'product_qty': 1.0,
                    }),
                    Command.create({
                        'product_id': self.component_b.id,
                        'product_qty': 2.0,
                    }),
                ],
            },
            {
                'product_tmpl_id': kit.product_tmpl_id.id,
                'product_uom_id': kit.uom_id.id,
                'product_qty': 1.0,
                'type': 'phantom',
                'bom_line_ids': [
                    Command.create({
                        'product_id': sub_kit.id,
                        'product_qty': 10.0,
                    }),
                    Command.create({
                        'product_id': self.component_b.id,
                        'product_qty': 10.0,
                    }),
                ],
            },
        ])
        self.component_a.standard_price = 30
        self.component_b.standard_price = 10
        sub_kit.action_bom_cost()
        kit.action_bom_cost()
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': kit.id,
                'product_uom_qty': 3,
                'product_uom_id': self.uom_ten.id
            })]
        })
        self.assertEqual(so.order_line.purchase_price, 600)
        so.action_confirm()
        self.assertEqual(so.order_line.purchase_price, 600)
        for move in so.picking_ids.move_ids:
            move.quantity = move.product_uom_qty
        self.assertRecordValues(so.order_line, [{'purchase_price': 600, 'qty_delivered': 0.0}])
        so.picking_ids.button_validate()
        self.assertEqual(so.picking_ids.state, 'done')
        self.assertRecordValues(so.order_line, [{'purchase_price': 600, 'qty_delivered': 3.0}])
        self.assertEqual(so.order_line.purchase_price, 600)
