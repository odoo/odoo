# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo import fields
from odoo.tests import tagged

from datetime import timedelta


@tagged('post_install', '-at_install')
class TestSaleStockLeadTime(TestSaleCommon, ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Update the product_1 with type and Customer Lead Time
        cls.test_product_order.sale_delay = 5.0

    def test_00_product_company_level_delays(self):
        """ In order to check schedule date, set product's Customer Lead Time
            and company's Sales Safety Days."""

        # Update company with Sales Safety Days
        self.env.company.security_lead = 3.00

        # Create sale order of product_1
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'picking_policy': 'direct',
            'warehouse_id': self.company_data['default_warehouse'].id,
            'order_line': [(0, 0, {'name': self.test_product_order.name,
                                   'product_id': self.test_product_order.id,
                                   'product_uom_qty': 10,
                                   'product_uom': self.env.ref('uom.product_uom_unit').id,
                                   'customer_lead': self.test_product_order.sale_delay})]})

        # Confirm our standard sale order
        order.action_confirm()

        # Check the picking crated or not
        self.assertTrue(order.picking_ids, "Picking should be created.")

        # Check schedule date of picking
        out_date = fields.Datetime.from_string(order.date_order) + timedelta(days=self.test_product_order.sale_delay) - timedelta(days=self.env.company.security_lead)
        min_date = fields.Datetime.from_string(order.picking_ids[0].scheduled_date)
        self.assertTrue(abs(min_date - out_date) <= timedelta(seconds=1), 'Schedule date of picking should be equal to: order date + Customer Lead Time - Sales Safety Days.')

    def test_01_product_route_level_delays(self):
        """ In order to check schedule dates, set product's Customer Lead Time
            and warehouse route's delay."""

        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.company_data['default_warehouse'].write({'delivery_steps': 'pick_pack_ship'})

        # Set delay on pull rule
        for pull_rule in self.company_data['default_warehouse'].delivery_route_id.rule_ids:
            pull_rule.write({'delay': 2})

        # Create sale order of product_1
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'picking_policy': 'direct',
            'warehouse_id': self.company_data['default_warehouse'].id,
            'order_line': [(0, 0, {'name': self.test_product_order.name,
                                   'product_id': self.test_product_order.id,
                                   'product_uom_qty': 5,
                                   'product_uom': self.env.ref('uom.product_uom_unit').id,
                                   'customer_lead': self.test_product_order.sale_delay})]})

        # Confirm our standard sale order
        order.action_confirm()

        # Check the picking crated or not
        self.assertTrue(order.picking_ids, "Pickings should be created.")

        # Check schedule date of ship type picking
        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.company_data['default_warehouse'].out_type_id)
        out_min_date = fields.Datetime.from_string(out.scheduled_date)
        out_date = fields.Datetime.from_string(order.date_order) + timedelta(days=self.test_product_order.sale_delay) - timedelta(days=out.move_lines[0].rule_id.delay)
        self.assertTrue(abs(out_min_date - out_date) <= timedelta(seconds=1), 'Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.')

        # Check schedule date of pack type picking
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.company_data['default_warehouse'].pack_type_id)
        pack_min_date = fields.Datetime.from_string(pack.scheduled_date)
        pack_date = out_date - timedelta(days=pack.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pack_min_date - pack_date) <= timedelta(seconds=1), 'Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.')

        # Check schedule date of pick type picking
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.company_data['default_warehouse'].pick_type_id)
        pick_min_date = fields.Datetime.from_string(pick.scheduled_date)
        pick_date = pack_date - timedelta(days=pick.move_lines[0].rule_id.delay)
        self.assertTrue(abs(pick_min_date - pick_date) <= timedelta(seconds=1), 'Schedule date of pick type picking should be equal to: Schedule date of pack type picking - pull rule delay.')

    def test_02_delivery_date_propagation(self):
        """ In order to check deadline date propagation, set product's Customer Lead Time
            and warehouse route's delay in stock rules"""

        # Example :
        # -> Set Warehouse with Outgoing Shipments : pick + pack + ship
        # -> Set Delay : 5 days on stock rules
        # -> Set Customer Lead Time on product : 30 days
        # -> Set Sales Safety Days : 2 days
        # -> Create an SO and confirm it with confirmation Date : 12/18/2018

        # -> Pickings : OUT -> Scheduled Date : 01/12/2019, Deadline Date: 01/14/2019
        #              PACK -> Scheduled Date : 01/07/2019, Deadline Date: 01/09/2019
        #              PICK -> Scheduled Date : 01/02/2019, Deadline Date: 01/04/2019

        # -> Now, change commitment_date in the sale order = out_deadline_date + 5 days

        # -> Deadline Date should be changed and Scheduled date should be unchanged:
        #              OUT  -> Deadline Date : 01/19/2019
        #              PACK -> Deadline Date : 01/14/2019
        #              PICK -> Deadline Date : 01/09/2019

        # Update company with Sales Safety Days
        self.env.company.security_lead = 2.00

        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.company_data['default_warehouse'].write({'delivery_steps': 'pick_pack_ship'})

        # Set delay on pull rule
        self.company_data['default_warehouse'].delivery_route_id.rule_ids.write({'delay': 5})

        # Update the product_1 with type and Customer Lead Time
        self.test_product_order.write({'type': 'product', 'sale_delay': 30.0})

        # Now, create sale order of product_1 with customer_lead set on product
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'picking_policy': 'direct',
            'warehouse_id': self.company_data['default_warehouse'].id,
            'order_line': [(0, 0, {'name': self.test_product_order.name,
                                   'product_id': self.test_product_order.id,
                                   'product_uom_qty': 5,
                                   'product_uom': self.env.ref('uom.product_uom_unit').id,
                                   'customer_lead': self.test_product_order.sale_delay})]})

        # Confirm our standard sale order
        order.action_confirm()

        # Check the picking crated or not
        self.assertTrue(order.picking_ids, "Pickings should be created.")

        # Check schedule/deadline date of ship type picking
        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.company_data['default_warehouse'].out_type_id)
        deadline_date = order.date_order + timedelta(days=self.test_product_order.sale_delay) - timedelta(days=out.move_lines[0].rule_id.delay)
        self.assertAlmostEqual(
            out.date_deadline, deadline_date, delta=timedelta(seconds=1),
            msg='Deadline date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.')
        out_scheduled_date = deadline_date - timedelta(days=self.env.company.security_lead)
        self.assertAlmostEqual(
            out.scheduled_date, out_scheduled_date, delta=timedelta(seconds=1),
            msg='Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay - security_lead')

        # Check schedule/deadline date of pack type picking
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.company_data['default_warehouse'].pack_type_id)
        pack_scheduled_date = out_scheduled_date - timedelta(days=pack.move_lines[0].rule_id.delay)
        self.assertAlmostEqual(
            pack.scheduled_date, pack_scheduled_date, delta=timedelta(seconds=1),
            msg='Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.')
        deadline_date -= timedelta(days=pack.move_lines[0].rule_id.delay)
        self.assertAlmostEqual(
            pack.date_deadline, deadline_date, delta=timedelta(seconds=1),
            msg='Deadline date of pack type picking should be equal to: Deadline date of ship type picking - pull rule delay.')

        # Check schedule/deadline date of pick type picking
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.company_data['default_warehouse'].pick_type_id)
        pick_scheduled_date = pack_scheduled_date - timedelta(days=pick.move_lines[0].rule_id.delay)
        self.assertAlmostEqual(
            pick.scheduled_date, pick_scheduled_date, delta=timedelta(seconds=1),
            msg='Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.')
        deadline_date -= timedelta(days=pick.move_lines[0].rule_id.delay)
        self.assertAlmostEqual(
            pick.date_deadline, deadline_date, delta=timedelta(seconds=1),
            msg='Deadline date of pack type picking should be equal to: Deadline date of ship type picking - pull rule delay.')

        # Now change the commitment date (Delivery Date) of the sale order
        new_deadline = deadline_date + timedelta(days=5)
        order.write({'commitment_date': new_deadline})

        # Now check date_deadline of pick, pack and out are forced
        # TODO : add note in case of change of deadline and check
        self.assertEqual(out.date_deadline, new_deadline)
        new_deadline -= timedelta(days=pack.move_lines[0].rule_id.delay)
        self.assertEqual(pack.date_deadline, new_deadline)
        new_deadline -= timedelta(days=pick.move_lines[0].rule_id.delay)
        self.assertEqual(pick.date_deadline, new_deadline)
