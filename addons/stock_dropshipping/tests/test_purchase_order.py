# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests.common import tagged


@tagged('-at_install', 'post_install')
class TestPurchaseOrder(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dropship_picking_type = cls.env['stock.picking.type'].search([
            ('code', '=', 'dropship'),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)

    def test_qty_received_does_sync_after_changing_validated_move_quantity(self):
        """ After validating a picking, if it is unlocked and has its move quantity modified,
        the underlying purchase order's qty_delivered value should reflect the change.
        """
        self.product_a.standard_price = 5.0
        cost_methods = ['standard', 'fifo', 'average']
        picking_types = [
            self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('company_id', '=', self.env.company.id),
            ], limit=1),
            self.dropship_picking_type,
        ]

        for cost_method in cost_methods:
            for picking_type in picking_types:
                self.product_a.categ_id.property_cost_method = cost_method
                po = self.env['purchase.order'].create({
                    'name': 'test_picking_qty_changed_after_validate picking',
                    'partner_id': self.partner_a.id,
                    'order_line': [Command.create({
                        'product_id': self.product_a.id,
                        'product_qty': 10.0,
                        'price_unit': 15.0,
                        'uom_id': self.product_a.uom_id.id,
                    })],
                    'picking_type_id': picking_type.id,
                })
                po.button_confirm()
                dropship = po.picking_ids
                dropship.move_ids[0].quantity = 10.0
                dropship.button_validate()
                dropship.action_toggle_is_locked()
                dropship.move_ids[0].quantity = 5.0

                self.assertEqual(
                    po.order_line[0].qty_received, 5.0,
                    f'picking_type={picking_type.code}, cost_method={cost_method}'
                )
                self.assertEqual(
                    self.product_a.standard_price, 5.0 if cost_method == 'standard' else 15.0,
                    f'picking_type={picking_type.code}, cost_method={cost_method}'
                )

    def test_project_propagation_from_so_with_dropshipping(self):
        """ Test that the project is propagated from the sale order to the purchase order
        when using dropshipping.
        """
        # check that the module project is installed
        if self.env['ir.module.module']._get('sale_project').state != 'installed':
            self.skipTest("Skipping test: the 'project' module is not installed.")
        # Create a dropshippable product
        dropship_product = self.env['product.product'].create({
            'name': 'Dropship Product',
            'seller_ids': [Command.create({
                'partner_id': self.partner_b.id,
            })],
            'route_ids': [Command.set([
                self.env.ref('stock_dropshipping.route_drop_shipping').id
            ])],
        })
        self.env.user.group_ids |= (
            self.quick_ref('project.group_project_manager') |
            self.quick_ref('sales_team.group_sale_salesman')
        )
        project = self.env['project.project'].create({
            'name': 'Test Project',
            'partner_id': self.partner_a.id,
        })

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': dropship_product.id,
                'product_uom_qty': 1.0,
            })],
            'project_id': project.id,
        })
        so.action_confirm()

        # Check that a purchase order was created and the project is set
        po = self.env['purchase.order'].search([
            ('origin', '=', so.name),
            ('partner_id', '=', self.partner_b.id),
        ], limit=1)

        self.assertTrue(po, "A Purchase Order should be created from the Sale Order.")
        self.assertEqual(po.project_id, project, "The project should be propagated from the Sale Order to the Purchase Order.")

    def test_dropship_serial_return_credit_note(self):
        '''
            Ensure that a partial refund after a dropship return of a serial-tracked
            product displays the right returned serial number on the credit note report.
        '''
        self.env.user.write({
            'group_ids': [
                Command.link(self.env.ref('stock_account.group_lot_on_invoice').id),
                Command.link(self.env.ref('sales_team.group_sale_salesman').id),
            ],
        })
        self.dropshipping_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        supplier = self.env['res.partner'].create({'name': 'Vendor'})
        customer = self.env['res.partner'].create({'name': 'Customer'})

        serial_dropship_product = self.env['product.product'].create({
            'name': 'Serial product',
            'is_storable': True,
            'tracking': 'serial',
            'seller_ids': [Command.create({
                'partner_id': supplier.id,
            })],
            'route_ids': [Command.link(self.dropshipping_route.id)],
        })
        serials = _, serial2 = self.env['stock.lot'].create([{
            'name': name,
            'product_id': serial_dropship_product.id,
            'company_id': self.env.company.id,
        } for name in ['SN 1', 'SN 2']])

        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [Command.create({
                'product_id': serial_dropship_product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        so.action_confirm()

        po = so._get_purchase_orders()
        po.button_confirm()

        dropship = po.picking_ids
        dropship.move_ids.lot_ids = serials
        dropship.button_validate()

        invoice = so._create_invoices()
        invoice.action_post()

        return_picking = dropship._create_return()
        return_picking.move_ids.product_uom_qty = 1
        return_picking.move_ids.lot_ids = serial2
        return_picking.action_assign()
        return_picking.button_validate()

        reversal_wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
        ).create({
            'reason': 'Test Partial Refund',
            'journal_id': invoice.journal_id.id,
        })
        res = reversal_wizard.reverse_moves()
        credit_note = self.env['account.move'].browse(res['res_id'])
        credit_note.invoice_line_ids[0].quantity = 1
        credit_note.action_post()

        self.assertEqual(
            [(rec['product_name'], rec['lot_id']) for rec in credit_note._get_invoiced_lot_values()],
            [(serial_dropship_product.name, serial2.id)],
        )
