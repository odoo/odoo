# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestSubcontractingDropshippingSerialMassProduce(TransactionCase):

    def test_smp_produce_all(self):
        """Create a PO for a product tracked by serial number with a component to be dropshipped.
        Open the smp wizard through picking line, generate all serial numbers to produce all quantitites.
        """
        # Prepare test environment
        subcontractor = self.env['res.partner'].create({
            'name': 'Subcontractor',
            'company_id': self.env.company.id
        })
        subcontracted_product = self.env['product.product'].create({
            'name': 'Subcontracted',
            'type': 'product',
            'tracking': "serial"
        })
        supplier = self.env['res.partner'].create({
            'name': 'Supplier',
            'company_id': self.env.company.id
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'type': 'product',
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': component.product_tmpl_id.id,
            'name': supplier.id
        })
        route = self.env['stock.location.route'].search([('name', '=', 'Dropship Subcontractor on Order')])
        component.write({'route_ids': [(4, route.id, None)]})
        bom = self.env['mrp.bom'].create({
            'product_id': subcontracted_product.id,
            'product_tmpl_id': subcontracted_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'subcontract',
            'subcontractor_ids': [
                (4, subcontractor.id, None)
            ],
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 1})
            ]
        })
        # Make PO
        quantity = 5
        po = self.env['purchase.order'].create({
            'partner_id': subcontractor.id,
            'order_line': [(0, 0, {
                'product_id': subcontracted_product.id,
                'product_qty': quantity,
                'price_unit': 10,
            })],
        })
        po.button_confirm()
        # Retrieve MO
        mo = self.env['mrp.production'].search([('bom_id', '=', bom.id)])
        # Confirm component PO & mark components received
        dropship_po = self.env['purchase.order'].search([('group_id', '=', mo.procurement_group_id.id)])
        self.assertEqual(dropship_po.dest_address_id.id, subcontractor.id)
        dropship_po.button_confirm()
        dropship_receipt = dropship_po.picking_ids[0]
        dropship_receipt.action_set_quantities_to_reservation()
        dropship_receipt.button_validate()
        # Process receipt from subcontractor
        receipt = po.picking_ids[0]
        form = Form(receipt.move_lines[0], view=self.env.ref('stock.view_stock_move_operations'))
        form.next_serial = "sn#1"
        form.next_serial_count = quantity
        f = form.save()
        f.action_assign_serial_show_details()
        receipt.button_validate()
        # Initial MO should have a backorder-sequenced name and be in done state
        self.assertTrue("-001" in mo.name)
        self.assertEqual(mo.state, "done")
        # Each generated serial number should have its own mo
        self.assertEqual(len(mo.procurement_group_id.mrp_production_ids), quantity)
