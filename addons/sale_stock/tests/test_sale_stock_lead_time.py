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
        for pull_rule in self.warehouse_1.delivery_route_id.rule_ids:
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

    def test_02_if_propagate_date(self):
        """ In order to check schedule dates, set product's Customer Lead Time
            and warehouse route's delay with propagate True in stock rules"""

        #Example :
        #-> set 'propagate_date' = True in stock rules
        #-> set propagate_date_minimum_delta = 5 days
        #-> Set Warehouse with Outgoing Shipments : pick + pack + ship
        #-> Set delay and propagate_date_minimum_delta on stock rules : 5 days and propagate_date = True
        #-> Set Customer Lead Time on product : 30 days
        #-> Create an SO and confirm it with confirmation Date : 12/18/2018

        #-> Pickings : OUT  -> Scheduled Date :  01/12/2019
        #              PACK -> Scheduled Date :  01/07/2019
        #              PICK -> Scheduled Date :  01/02/2019

        #-> Now, change date of pick = +5 days

        #-> Scheduled Date should be changed:
        #              OUT  -> Scheduled Date :  01/17/2019
        #              PACK -> Scheduled Date :  01/12/2019
        #              PICK -> Scheduled Date :  01/07/2019

        # set the propagate_date and
        # set propagate_date_minimum_delta = 5 in the stock rule

        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        # Set delay on pull rule
        self.warehouse_1.delivery_route_id.rule_ids.write({'delay': 5, 'propagate_date': True, 'propagate_date_minimum_delta': 5})

        # Update the product_1 with type and Customer Lead Time
        self.product_1.write({'type': 'product',
                              'sale_delay': 30.0})

        # Now, create sale order of product_1 with customer_lead set on product
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
        out_min_date = out.scheduled_date
        out_date = order.date_order + timedelta(days=self.product_1.sale_delay) - timedelta(days=out.move_lines[0].rule_id.delay)
        self.assertTrue(abs(out_min_date - out_date) <= timedelta(seconds=1), 'Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.')

        # Check schedule date of pack type picking
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pack_min_date = pack.scheduled_date
        pack_date = out_date - timedelta(days=pack.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pack_min_date - pack_date) <= timedelta(seconds=1), 'Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.')

        # Check schedule date of pick type picking
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)
        pick_min_date = pick.scheduled_date
        pick_date = pack_date - timedelta(days=pick.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pick_min_date - pick_date) <= timedelta(seconds=1), 'Schedule date of pick type picking should be equal to: Schedule date of pack type picking - pull rule delay.')

        # Now change the schedule date of pick
        # Note : pack and out has change scheduled_date automatically based on delay set on pick
        pick.write({'scheduled_date': pick_min_date + timedelta(days=5)})

        # Now check scheduled_date of pack and out are changed or not based on propagate is true on rules?
        self.assertEquals(pack.scheduled_date, (pack_min_date + timedelta(days=5)),
            'Schedule date of pack should be changed based on delay.')
        self.assertEquals(out.scheduled_date, (out_min_date + timedelta(days=5)),
            'Schedule date of out should be changed based on delay.')

    def test_03_no_propagate_date(self):
        """ In order to check schedule dates, set product's Customer Lead Time
            and warehouse route's delay with propagate False in stock rule"""

        #Example :
        #-> Set Warehouse with Outgoing Shipments : pick + pack + ship
        #-> Set delay on stock rules : 5 days and propagate = False
        #-> Set Customer Lead Time on product : 30 days
        #-> Create an SO and confirm it with confirmation Date : 12/18/2018

        #-> Pickings : OUT  -> Scheduled Date :  01/12/2019
        #              PACK -> Scheduled Date :  01/07/2019
        #              PICK -> Scheduled Date :  01/02/2019

        #-> Now, change date of pick = +5 days

        #-> Scheduled Date should be not changed:
        #              OUT  -> Scheduled Date :  01/12/2019
        #              PACK -> Scheduled Date :  01/07/2019
        #              PICK -> Scheduled Date :  01/07/2019

        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        # Set delay on pull rule
        for pull_rule in self.warehouse_1.delivery_route_id.rule_ids:
            pull_rule.write({'delay': 5, 'propagate_date': False})

        # Update the product_1 with type and Customer Lead Time
        self.product_1.write({'type': 'product',
                              'sale_delay': 30.0})

        #Create sale order of product_1
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
        out_min_date = out.scheduled_date
        out_date = order.date_order + timedelta(days=self.product_1.sale_delay) - timedelta(days=out.move_lines[0].rule_id.delay)
        self.assertTrue(abs(out_min_date - out_date) <= timedelta(seconds=1), 'Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.')

        # Check schedule date of pack type picking
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pack_min_date = pack.scheduled_date
        pack_date = out_date - timedelta(days=pack.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pack_min_date - pack_date) <= timedelta(seconds=1), 'Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.')

        # Check schedule date of pick type picking
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)
        pick_min_date = pick.scheduled_date
        pick_date = pack_date - timedelta(days=pick.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pick_min_date - pick_date) <= timedelta(seconds=1), 'Schedule date of pick type picking should be equal to: Schedule date of pack type picking - pull rule delay.')

        # Now change the schedule date of pick
        pick.write({'scheduled_date': pick_min_date + timedelta(days=5)})

        # Now check scheduled_date of pack and out are changed or not based on propagate is false on rules?
        self.assertEquals(pack.scheduled_date, pack_min_date, 'Schedule date of pack should not be changed.')
        self.assertEquals(out.scheduled_date, out_min_date, 'Schedule date of out should not be changed.')
