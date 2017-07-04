# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMultistepManufacturing(TestMrpCommon):

    def setUp(self):
        super(TestMultistepManufacturing, self).setUp()

        # Create warehouse
        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        self.route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        self.route_mto = self.warehouse.mto_pull_id.route_id.id
        self.Partner = self.env.ref('base.res_partner_1')
        self.uom_unit = self.env.ref('product.product_uom_unit')
        self.product_manu = self.env['product.product'].create({
            'name': 'Stick',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id})
        self.product_raw = self.env['product.product'].create({
            'name': 'raw Stick',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id})
        self.product_manu.write({'route_ids': [(6, 0, [self.route_manufacture, self.route_mto])]})
        self.bom_prod_manu = self.env['mrp.bom'].create({
            'product_id': self.product_manu.id,
            'product_tmpl_id': self.product_manu.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_raw.id, 'product_qty': 2})
            ]})

        # Create sale order
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.Partner.id,
            'picking_policy': 'direct',
            'warehouse_id': self.warehouse.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_manu.name,
                    'product_id': self.product_manu.id,
                    'product_uom_qty': 1.0,
                    'product_uom': self.uom_unit.id,
                    'price_unit': 10.0
                })
            ]
        })

    def test_00_manufacturing_step_one(self):
        """ Testing for Step-1 """
        # Change steps of manufacturing.
        self.warehouse.manufacture_steps = 'manu_only'
        # Confirm sale order.
        self.sale_order.action_confirm()
        # Check all procurements for created sale order
        mo_procurement = self.env['mrp.production'].search([('procurement_group_id', '=', self.sale_order.procurement_group_id.id)])
        # Get manufactured procurement
        self.assertEqual(mo_procurement.location_src_id.id, self.warehouse.lot_stock_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")
        self.assertEqual(len(mo_procurement), 1, "No Procurement !")
     
    def test_01_manufacturing_step_two(self):
        """ Testing for Step-2 """
        self.warehouse.manufacture_steps = 'pick_manu'
        self.sale_order.action_confirm()
        # Get manufactured procurement
        mo_procurement = self.env['mrp.production'].search([('procurement_group_id', '=', self.sale_order.procurement_group_id.id)])
        self.assertEqual(mo_procurement.location_src_id.id, self.warehouse.wh_input_manu_loc_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")

        self.assertEqual(len(mo_procurement), 1, "No Procurement !")
