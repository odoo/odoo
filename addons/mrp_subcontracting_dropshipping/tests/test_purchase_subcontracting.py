# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestSubcontractingDropshippingFlows(TestMrpSubcontractingCommon):

    def test_mrp_subcontracting_dropshipping_1(self):
        """ Mark the subcontracted product with the route dropship and add the
        subcontractor as seller. The component has the routes 'MTO', 'Replenish
        on order' and 'Buy'. Also another partner is set as vendor on the comp.
        Create a SO and check that:
        - Delivery between subcontractor and customer for subcontracted product.
        - Delivery for the component to the subcontractor for the specified wh.
        - Po created for the component.
        """
        mto_route = self.env['stock.location.route'].search([('name', '=', 'Replenish on Order (MTO)')])
        resupply_route = self.env['stock.location.route'].search([('name', '=', 'Resupply Subcontractor on Order')])
        buy_route = self.env['stock.location.route'].search([('name', '=', 'Buy')])
        dropship_route = self.env['stock.location.route'].search([('name', '=', 'Dropship')])
        self.comp2.write({'route_ids': [(4, buy_route.id), (4, mto_route.id), (4, resupply_route.id)]})
        self.finished.write({'route_ids': [(4, dropship_route.id)]})

        warehouse = self.env['stock.warehouse'].create({
            'name': 'Warehouse For subcontract',
            'code': 'WFS'
        })

        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.finished.product_tmpl_id.id,
            'name': self.subcontractor_partner1.id
        })

        partner = self.env['res.partner'].create({
            'name': 'Toto'
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.comp2.product_tmpl_id.id,
            'name': partner.id
        })

        # Create a receipt picking from the subcontractor
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = partner
        so_form.warehouse_id = warehouse
        with so_form.order_line.new() as line:
            line.product_id = self.finished
            line.product_uom_qty = 1
        so = so_form.save()
        so.action_confirm()

        # Pickings should directly be created
        po = self.env['purchase.order'].search([('origin', 'ilike', so.name)])
        self.assertTrue(po)

        po.button_approve()

        picking_finished = po.picking_ids
        self.assertEqual(len(picking_finished), 1.0)
        self.assertEqual(picking_finished.location_dest_id, partner.property_stock_customer)
        self.assertEqual(picking_finished.location_id, self.subcontractor_partner1.property_stock_supplier)
        self.assertEqual(picking_finished.state, 'assigned')

        picking_delivery = self.env['stock.move'].search([
            ('product_id', '=', self.comp2.id),
            ('location_id', '=', warehouse.lot_stock_id.id),
            ('location_dest_id', '=', self.subcontractor_partner1.property_stock_subcontractor.id),
        ]).picking_id
        self.assertTrue(picking_delivery)
        self.assertEqual(picking_delivery.state, 'waiting')

        po = self.env['purchase.order.line'].search([
            ('product_id', '=', self.comp2.id),
            ('partner_id', '=', partner.id),
        ]).order_id
        self.assertTrue(po)
