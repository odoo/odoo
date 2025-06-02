# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo import Command


@tagged('post_install', '-at_install')
class TestProjectPurchaseStockSubcontracting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env['ir.module.module']._get('mrp_subcontracting').state != 'installed':
            cls.skipTest(cls, "mrp_subcontracting is not installed")

        cls.project = cls.env['project.project'].create({'name': 'Test Project'})
        cls.subcontractor = cls.env['res.partner'].create({'name': 'Subcontractor'})
        cls.finished_product, cls.component = cls.env['product.product'].create([
            {
                'name': 'Finished Product',
                'is_storable': True,
                'seller_ids': [Command.create({
                    'partner_id': cls.subcontractor.id,
                    'price': 1.0,
                })],
            },
            {
                'name': 'Component',
                'is_storable': True,
            },
        ])
        cls.bom = cls.env['mrp.bom'].create({  # noqa: OLS03001
            'product_tmpl_id': cls.finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(cls.subcontractor.id)],
            'bom_line_ids': [Command.create({
                'product_id': cls.component.id,
                'product_qty': 1.0,
            })],
        })

    def test_project_is_propagated_to_subcontracting_resupply_picking(self):
        """
        Test project propagation from PO through subcontracting flow.

        Scenario:
        - Create PO for subcontracted product with project
        - Confirm PO --> receipt picking created with project
        - Receipt has existing MO with resupply picking
        - Resupply picking should have project inherited
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor.id,
            'project_id': self.project.id,
            'order_line': [Command.create({
                'product_id': self.finished_product.id,
                'product_qty': 1.0,
                'price_unit': 1.0,
            })],
        })
        po.button_confirm()

        # Verify receipt picking inherits project from PO
        receipt = po.picking_ids
        self.assertEqual(receipt.project_id, self.project, "Receipt should inherit project from PO")

        # Get the subcontracting MO created for this receipt
        subcontracting_mo = receipt._get_subcontract_production()
        self.assertEqual(len(subcontracting_mo), 1, "One MO should be created for subcontracting")

        # Get resupply picking from MO
        resupply_picking = subcontracting_mo.picking_ids.filtered(
            lambda picking: picking.picking_type_id == receipt.picking_type_id.warehouse_id.subcontracting_resupply_type_id
        )
        self.assertEqual(len(resupply_picking), 1, "One resupply picking should be created")

        # Verify resupply picking inherits project
        self.assertEqual(resupply_picking.project_id, self.project, "Resupply picking should inherit project")

    def test_project_is_propagated_to_auto_generated_subcontracting_purchase(self):
        """
        Test project propagation when reordering rule auto-creates PO for component.

        Scenario:
        - Finished product has subcontracting BoM with component
        - Component has a seller and a reordering rule to buy from subcontractor
        - Create PO for finished product with project, confirm it
        - Auto-generated PO for component should inherit the project
        """
        self.component.seller_ids = [Command.create({
            'partner_id': self.subcontractor.id,
            'price': 1.0,
        })]

        # Reordering rule for component, triggers PO creation when stock is needed
        warehouse = self.env.ref('stock.warehouse0')
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Reorder Component',
            'product_id': self.component.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_min_qty': 0.0,
            'product_max_qty': 1.0,
        })

        # Create and confirm PO for finished product with project
        po = self.env['purchase.order'].create({
            'partner_id': self.subcontractor.id,
            'project_id': self.project.id,
            'order_line': [Command.create({
                'product_id': self.finished_product.id,
                'product_qty': 1.0,
                'price_unit': 1.0,
            })],
        })
        po.button_confirm()

        # Verify that PO for component was auto-created with project
        po_component = self.env['purchase.order'].search([
            ('partner_id', '=', self.subcontractor.id),
            ('state', '=', 'draft'),
            ('order_line.product_id', '=', self.component.id),
        ], limit=1)
        self.assertTrue(po_component, "Reordering rule should auto-create PO for component")
        self.assertEqual(po_component.project_id, self.project, "Auto-generated PO for component should inherit project")
