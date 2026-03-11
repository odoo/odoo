# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_mrp.tests import test_sale_mrp_flow
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

    def test_kit_cost_calculation_multi_qty_bom(self):
        """ Check that the average cost price is correctly normalized by bom.product_qty.

            BOM: 12 units of "Kit X" = 12 x Comp A + 12 x Comp B
            Comp A cost = $10, Comp B cost = $20
            Per-unit cost of Kit X = (12*10 + 12*20) / 12 = $30

            Without normalization the cost would incorrectly be 12*10 + 12*20 = $360.
        """
        kit_x = self._cls_create_product('Kit X', self.uom_unit)
        (kit_x + self.component_a + self.component_b).categ_id.property_cost_method = 'average'
        self.env['mrp.bom'].create({
            'product_tmpl_id': kit_x.product_tmpl_id.id,
            'product_qty': 12.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.component_a.id, 'product_qty': 12.0}),
                (0, 0, {'product_id': self.component_b.id, 'product_qty': 12.0}),
            ],
        })
        self.component_a.standard_price = 10
        self.component_b.standard_price = 20

        stock_location = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1,
        ).lot_stock_id
        self.env['stock.quant']._update_available_quantity(self.component_a, stock_location, 100)
        self.env['stock.quant']._update_available_quantity(self.component_b, stock_location, 100)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = kit_x
        so = so_form.save()
        so.action_confirm()
        self.assertEqual(so.order_line.purchase_price, 30)
