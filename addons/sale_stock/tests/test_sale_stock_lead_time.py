# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.addons.stock.tests.common2 import TestStockCommon


class TestSaleStockLeadTime(TestStockCommon):

    def setUp(self):
        super(TestSaleStockLeadTime, self).setUp()

        # Update the product_1 with type and Customer Lead Time
        self.product_1.write({'type': 'product',
                              'sale_delay': 5.0})

    def test_00_product_company_level_delays(self):
        """ In order to check schedule date, set product's Customer Lead Time
            and company's Sales Safety Days."""

        company = self.env.ref('base.main_company')

        # Update company with Sales Safety Days
        company.write({'security_lead': 3.00})

        # Create sale order of product_1
        order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'partner_invoice_id': self.partner_1.id,
            'partner_shipping_id': self.partner_1.id,
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
            'warehouse_id': self.warehouse_1.id,
            'order_line': [(0, 0, {'name': self.product_1.name,
                                   'product_id': self.product_1.id,
                                   'product_uom_qty': 10,
                                   'product_uom': self.uom_unit.id,
                                   'customer_lead': self.product_1.sale_delay})]})

        # Confirm our standard sale order
        order.action_confirm()

        # Check the picking crated or not
        self.assertTrue(order.picking_ids, "Picking should be created.")

        # Check schedule date of picking
        out_date = fields.Datetime.from_string(order.date_order) + timedelta(days=self.product_1.sale_delay) - timedelta(days=company.security_lead)
        min_date = fields.Datetime.from_string(order.picking_ids[0].scheduled_date)
        self.assertTrue(abs(min_date - out_date) <= timedelta(seconds=1), 'Schedule date of picking should be equal to: order date + Customer Lead Time - Sales Safety Days.')

    def test_01_product_route_level_delays(self):
        """ In order to check schedule dates, set product's Customer Lead Time
            and warehouse route's delay."""

        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        # Set delay on pull rule
        for pull_rule in self.warehouse_1.delivery_route_id.pull_ids:
            pull_rule.write({'delay': 2})

        # Create sale order of product_1
        order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'partner_invoice_id': self.partner_1.id,
            'partner_shipping_id': self.partner_1.id,
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
            'warehouse_id': self.warehouse_1.id,
            'order_line': [(0, 0, {'name': self.product_1.name,
                                   'product_id': self.product_1.id,
                                   'product_uom_qty': 5,
                                   'product_uom': self.uom_unit.id,
                                   'customer_lead': self.product_1.sale_delay})]})

        # Confirm our standard sale order
        order.action_confirm()

        # Check the picking crated or not
        self.assertTrue(order.picking_ids, "Pickings should be created.")

        # Check schedule date of ship type picking
        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.out_type_id)
        out_min_date = fields.Datetime.from_string(out.scheduled_date)
        out_date = fields.Datetime.from_string(order.date_order) + timedelta(days=self.product_1.sale_delay) - timedelta(days=out.move_lines[0].rule_id.delay)
        self.assertTrue(abs(out_min_date - out_date) <= timedelta(seconds=1), 'Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.')

        # Check schedule date of pack type picking
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pack_min_date = fields.Datetime.from_string(pack.scheduled_date)
        pack_date = out_date - timedelta(days=pack.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pack_min_date - pack_date) <= timedelta(seconds=1), 'Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.')

        # Check schedule date of pick type picking
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)
        pick_min_date = fields.Datetime.from_string(pick.scheduled_date)
        pick_date = pack_date - timedelta(days=pick.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pick_min_date - pick_date) <= timedelta(seconds=1), 'Schedule date of pick type picking should be equal to: Schedule date of pack type picking - pull rule delay.')
