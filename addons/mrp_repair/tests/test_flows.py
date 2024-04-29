# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.fields import Command


@tagged('post_install', '-at_install')
class TestMrpRepairFlows(TestMrpCommon):
    def test_possible_to_add_kit_after_confirm(self):
        """
        Test that it is possible to add a kit manufactured product to an already confirmed Repair Order
        """
        repaired, part1, part2, kit = self.env['product.product'].create([
            {'name': 'Repaired'},
            {'name': 'Kit Component1'},
            {'name': 'Kit Component2'},
            {'name': 'Kit', 'type': 'product'},
        ])
        self.env['mrp.bom'].create({
            'product_id': kit.id,
            'product_tmpl_id': kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': part1.id,
                    'product_qty': 1.0,
                }),
                Command.create({
                    'product_id': part2.id,
                    'product_qty': 1.0,
                }),
            ],
        })

        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = repaired
        ro = ro_form.save()
        ro.action_validate()

        ro.partner_id = self.env['res.partner'].create({'name': 'Bob'})
        ro.action_create_sale_order()

        self.env['stock.move'].create({
            'repair_id': ro.id,
            'product_id': kit.id,
            'repair_line_type': 'add',
        })

        self.assertEqual(ro.move_ids.product_id, part1 | part2, "Repair order moves should correspond to the kit components")

        # Make sure we don't create unnecessary sale order lines
        repair_sol = self.env['sale.order.line'].search([('order_id', '=', ro.sale_order_id.id)])
        self.assertEqual(repair_sol.product_id, part1 | part2, "Sale Order Lines should correspond to the kit components (no sol for kit itself)")
