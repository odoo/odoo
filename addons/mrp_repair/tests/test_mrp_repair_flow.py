# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install')
class TestMrpRepairFlow(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})

    def test_repair_with_manufacture_mto_link(self):
        """
        Test the integration between a repair order and a manufacturing order (MTO)
        for a product with 'Make to Order' (MTO) and 'Manufacture' routes.

        Validates that a repair order triggers a manufacturing order with correct product
        and quantity, and ensures proper linking via the procurement group.
        """
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        manufacturing_route = self.env['stock.rule'].search([('action', '=', 'manufacture')]).route_id
        rule = mto_route.rule_ids.filtered(lambda r: r.picking_type_id.code == 'repair_operation')
        rule.procure_method = 'make_to_order'

        product = self.product_2
        product.write({
            'route_ids': [Command.set([mto_route.id, manufacturing_route.id])],
        })

        repair = self.env['repair.order'].create([
            {
                'move_ids': [
                    Command.create({
                        'repair_line_type': 'add',
                        'product_id': product.id,
                        'product_uom_qty': 1.0,
                    })
                ]
            }
        ])

        repair.action_validate()

        production = repair.procurement_group_id.stock_move_ids.created_production_id
        self.assertEqual(production.product_id, product)
        self.assertEqual(production.product_qty, 1.0)
        self.assertEqual(production.move_dest_ids.repair_id, repair)
        self.assertEqual(production.repair_count, 1)
        self.assertEqual(repair.production_count, 1)

    def test_adding_kit_parts_to_confirmed_repair(self):
        """Test adding a kit product to a confirmed repair order.
        This ensures that:
        - Its moves are correctly exploded into their component parts.
        - The generated component moves are properly linked to the repair order.
        """
        repair = self.env['repair.order'].create({
            'product_id': self.product.id,
            'picking_type_id': self.warehouse_1.repair_type_id.id,
        })
        repair.action_validate()
        self.assertEqual(repair.state, 'confirmed')
        self.assertEqual(len(repair.move_ids), 0)
        # Ensure the product is a kit
        self.assertTrue(self.product_5.is_kits)
        # Add the kit to the repair order
        self.env['stock.move'].create({
            'repair_id': repair.id,
            'product_id': self.product_5.id,
            'product_uom_qty': 1.0,
            'repair_line_type': 'add',
        })
        # Check that the kit has been exploded into its components
        self.assertEqual(len(repair.move_ids), 2)
        self.assertEqual(
            set(repair.move_ids.product_id.ids),
            set(self.product_5.bom_ids.bom_line_ids.product_id.ids)
        )
