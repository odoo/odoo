# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo import Command


@tagged('post_install', '-at_install')
class TestProjectPurchaseStockSubcontracting(TransactionCase):

    def test_project_is_propagated_to_subcontracting_resupply_picking(self):
        """
        Test project propagation from PO through subcontracting flow.

        Scenario:
        - Create PO for subcontracted product with project
        - Confirm PO --> receipt picking created with project
        - Receipt has existing MO with resupply picking
        - Resupply picking should have project inherited
        """
        if 'mrp_subcontracting' not in self.env['ir.module.module']._installed():
            self.skipTest('MRP Subcontracting is not installed but needed for this test')

        project = self.env['project.project'].create({'name': 'Project 1'})
        subcontractor = self.env['res.partner'].create({
            'name': 'Subcontractor',
        })
        finished_product, component_product = self.env['product.product'].create([
            {
                'name': 'Subcontracted Product',
                'is_storable': True,
                'seller_ids': [Command.create({
                    'partner_id': subcontractor.id,
                    'price': 1.0,
                })],
            },
            {
                'name': 'Subcontracted Component',
                'is_storable': True,
            },
        ])

        # Create BOM for the subcontracted product
        self.env['mrp.bom'].create({  # noqa: OLS03001
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(subcontractor.id)],
            'bom_line_ids': [Command.create({
                'product_id': component_product.id,
                'product_qty': 1.0,
            })],
        })

        # Create and confirm PO for finished product with project
        po = self.env['purchase.order'].create({
            'partner_id': subcontractor.id,
            'project_id': project.id,
            'order_line': [Command.create({
                'product_id': finished_product.id,
                'product_qty': 1.0,
                'uom_id': finished_product.uom_id.id,
                'price_unit': 1.0,
            })],
        })
        po.button_confirm()

        # Verify receipt picking inherits project from PO
        receipt = po.picking_ids
        self.assertEqual(receipt.project_id, project, "Receipt should inherit project from PO")

        # Get the subcontracting MO created for this receipt
        subcontracting_mo = receipt._get_subcontract_production()
        self.assertEqual(len(subcontracting_mo), 1, "One MO should be created for subcontracting")

        # Get resupply picking from MO
        resupply_picking = subcontracting_mo.picking_ids.filtered(
            lambda picking: picking.picking_type_id == receipt.picking_type_id.warehouse_id.subcontracting_resupply_type_id
        )
        self.assertEqual(len(resupply_picking), 1, "One resupply picking should be created")

        # Verify resupply picking inherits project
        self.assertEqual(resupply_picking.project_id, project, "Resupply picking should inherit project")

    def test_project_is_propagated_to_auto_generated_subcontracting_purchase(self):
        """
        Test project propagation when reordering rule auto-creates PO for component.

        Scenario:
        - P1 has subcontracting BoM with component P2
        - P2 has a reordering rule to buy from subcontractor
        - Create PO for P1 with project, confirm it
        - Auto-generated PO for P2 should inherit the project
        """
        if 'mrp_subcontracting' not in self.env['ir.module.module']._installed():
            self.skipTest('MRP Subcontracting is not installed but needed for this test')

        project = self.env['project.project'].create({'name': 'Project 2'})
        subcontractor = self.env['res.partner'].create({
            'name': 'Subcontractor',
        })
        p1, p2 = self.env['product.product'].create([
            {
                'name': 'P1 - Finished Product',
                'is_storable': True,
                'seller_ids': [Command.create({
                    'partner_id': subcontractor.id,
                    'price': 1.0,
                })],
            },
            {
                'name': 'P2 - Component',
                'is_storable': True,
                'seller_ids': [Command.create({
                    'partner_id': subcontractor.id,
                    'price': 1.0,
                })],
            },
        ])

        # Create BOM for the nested subcontracting
        self.env['mrp.bom'].create({  # noqa: OLS03001
            'product_tmpl_id': p1.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(subcontractor.id)],
            'bom_line_ids': [Command.create({
                'product_id': p2.id,
                'product_qty': 1.0,
            })],
        })

        # Reordering rule for P2, triggers PO creation when stock is needed
        warehouse = self.env.ref('stock.warehouse0')
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Reorder P2',
            'product_id': p2.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_min_qty': 0.0,
            'product_max_qty': 1.0,
        })

        # Create and confirm PO for P1 with project
        po_p1 = self.env['purchase.order'].create({
            'partner_id': subcontractor.id,
            'project_id': project.id,
            'order_line': [Command.create({
                'product_id': p1.id,
                'product_qty': 1.0,
                'uom_id': p1.uom_id.id,
                'price_unit': 1.0,
            })],
        })
        po_p1.button_confirm()

        # Verify that PO for P2 was auto-created with project
        po_p2 = self.env['purchase.order'].search([
            ('partner_id', '=', subcontractor.id),
            ('state', '=', 'draft'),
            ('order_line.product_id', '=', p2.id),
        ], limit=1)
        self.assertTrue(po_p2, "Reordering rule should auto-create PO for P2")
        self.assertEqual(po_p2.project_id, project, "Auto-generated PO for P2 should inherit project from P1 PO")
