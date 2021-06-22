# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time
from unittest.mock import patch

from odoo import fields
from .common import PurchaseTestCommon
from odoo.tests.common import Form


class TestPurchaseLeadTime(PurchaseTestCommon):

    def test_00_product_company_level_delays(self):
        """ To check dates, set product's Delivery Lead Time
            and company's Purchase Lead Time."""

        company = self.env.ref('base.main_company')

        # Update company with Purchase Lead Time
        company.write({'po_lead': 3.00})

        # Make procurement request from product_1's form view, create procurement and check it's state
        date_planned = fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10))
        self._create_make_procurement(self.product_1, 15.00, date_planned=date_planned)
        purchase = self.env['purchase.order.line'].search([('product_id', '=', self.product_1.id)], limit=1).order_id

        # Confirm purchase order
        purchase.button_confirm()

        # Check order date of purchase order
        order_date = fields.Datetime.from_string(date_planned) - timedelta(days=company.po_lead) - timedelta(days=self.product_1.seller_ids.delay)
        self.assertEqual(purchase.date_order, order_date, 'Order date should be equal to: Date of the procurement order - Purchase Lead Time - Delivery Lead Time.')

        # Check scheduled date of purchase order
        schedule_date = datetime.combine(order_date + timedelta(days=self.product_1.seller_ids.delay), time.min).replace(tzinfo=None, hour=12)
        self.assertEqual(purchase.order_line.date_planned, schedule_date, 'Schedule date should be equal to: Order date of Purchase order + Delivery Lead Time.')

        # check the picking created or not
        self.assertTrue(purchase.picking_ids, "Picking should be created.")

        # Check scheduled and deadline date of In Type shipment
        self.assertEqual(purchase.picking_ids.scheduled_date, schedule_date, 'Schedule date of In type shipment should be equal to: schedule date of purchase order.')
        self.assertEqual(purchase.picking_ids.date_deadline, schedule_date + timedelta(days=company.po_lead), 'Deadline date of should be equal to: schedule date of purchase order + lead_po.')

    def test_01_product_level_delay(self):
        """ To check schedule dates of multiple purchase order line of the same purchase order,
            we create two procurements for the two different product with same vendor
            and different Delivery Lead Time."""

        company = self.env.ref('base.main_company')
        company.write({'po_lead': 0.00})

        # Make procurement request from product_1's form view, create procurement and check it's state
        date_planned1 = fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10))
        self._create_make_procurement(self.product_1, 10.00, date_planned=date_planned1)
        purchase1 = self.env['purchase.order.line'].search([('product_id', '=', self.product_1.id)], limit=1).order_id

        # Make procurement request from product_2's form view, create procurement and check it's state
        date_planned2 = fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10))
        self._create_make_procurement(self.product_2, 5.00, date_planned=date_planned2)
        purchase2 = self.env['purchase.order.line'].search([('product_id', '=', self.product_2.id)], limit=1).order_id

        # Check purchase order is same or not
        self.assertEqual(purchase1, purchase2, 'Purchase orders should be same for the two different product with same vendor.')

        # Confirm purchase order
        purchase1.button_confirm()

        # Check order date of purchase order
        order_line_pro_1 = purchase2.order_line.filtered(lambda r: r.product_id == self.product_1)
        order_line_pro_2 = purchase2.order_line.filtered(lambda r: r.product_id == self.product_2)
        order_date = fields.Datetime.from_string(date_planned1) - timedelta(days=self.product_1.seller_ids.delay)
        self.assertEqual(purchase2.date_order, order_date, 'Order date should be equal to: Date of the procurement order - Delivery Lead Time.')

        # Check scheduled date of purchase order line for product_1
        schedule_date_1 = datetime.combine(order_date + timedelta(days=self.product_1.seller_ids.delay), time.min).replace(tzinfo=None, hour=12)
        self.assertEqual(order_line_pro_1.date_planned, schedule_date_1, 'Schedule date of purchase order line for product_1 should be equal to: Order date of purchase order + Delivery Lead Time of product_1.')

        # Check scheduled date of purchase order line for product_2
        schedule_date_2 = datetime.combine(order_date + timedelta(days=self.product_2.seller_ids.delay), time.min).replace(tzinfo=None, hour=12)
        self.assertEqual(order_line_pro_2.date_planned, schedule_date_2, 'Schedule date of purchase order line for product_2 should be equal to: Order date of purchase order + Delivery Lead Time of product_2.')

        # Check scheduled date of purchase order
        po_schedule_date = min(schedule_date_1, schedule_date_2)
        self.assertEqual(purchase2.order_line[1].date_planned, po_schedule_date, 'Schedule date of purchase order should be minimum of schedule dates of purchase order lines.')

        # Check the picking created or not
        self.assertTrue(purchase2.picking_ids, "Picking should be created.")

        # Check scheduled date of In Type shipment
        self.assertEqual(purchase2.picking_ids.scheduled_date, po_schedule_date, 'Schedule date of In type shipment should be same as schedule date of purchase order.')

        # Check deadline of pickings
        self.assertEqual(purchase2.picking_ids.date_deadline, purchase2.date_planned, "Deadline of pickings should be equals to the receipt date of purchase")
        purchase_form = Form(purchase2)
        purchase_form.date_planned = purchase2.date_planned + timedelta(days=2)
        purchase_form.save()
        self.assertEqual(purchase2.picking_ids.date_deadline, purchase2.date_planned, "Deadline of pickings should be propagate")

    def test_02_product_route_level_delays(self):
        """ In order to check dates, set product's Delivery Lead Time
            and warehouse route's delay."""

        company = self.env.ref('base.main_company')
        company.write({'po_lead': 1.00})

        # Update warehouse_1 with Incoming Shipments 3 steps
        self.warehouse_1.write({'reception_steps': 'three_steps'})

        # Set delay on push rule
        for push_rule in self.warehouse_1.reception_route_id.rule_ids:
            push_rule.write({'delay': 2})

        rule_delay = sum(self.warehouse_1.reception_route_id.rule_ids.mapped('delay'))

        date_planned = fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10))
        # Create procurement order of product_1
        self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
            self.product_1, 5.000, self.uom_unit, self.warehouse_1.lot_stock_id, 'Test scheduler for RFQ', '/', self.env.company,
            {
                'warehouse_id': self.warehouse_1,
                'date_planned': date_planned,  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
                'date_deadline': date_planned,  # 10 days added to current date of procurement to get future schedule date and order date of purchase order.
                'rule_id': self.warehouse_1.buy_pull_id,
                'group_id': False,
                'route_ids': [],
            }
        )])

        # Confirm purchase order
        purchase = self.env['purchase.order.line'].search([('product_id', '=', self.product_1.id)], limit=1).order_id
        purchase.button_confirm()

        # Check order date of purchase order
        order_date = fields.Datetime.from_string(date_planned) - timedelta(days=self.product_1.seller_ids.delay + rule_delay + company.po_lead)
        self.assertEqual(purchase.date_order, order_date, 'Order date should be equal to: Date of the procurement order - Delivery Lead Time(supplier and pull rules).')

        # Check scheduled date of purchase order
        schedule_date = order_date + timedelta(days=self.product_1.seller_ids.delay + rule_delay + company.po_lead)
        self.assertEqual(date_planned, str(schedule_date), 'Schedule date should be equal to: Order date of Purchase order + Delivery Lead Time(supplier and pull rules).')

        # Check the picking crated or not
        self.assertTrue(purchase.picking_ids, "Picking should be created.")

        # Check scheduled date of Internal Type shipment
        incoming_shipment1 = self.env['stock.picking'].search([('move_lines.product_id', 'in', (self.product_1.id, self.product_2.id)), ('picking_type_id', '=', self.warehouse_1.int_type_id.id), ('location_id', '=', self.warehouse_1.wh_input_stock_loc_id.id), ('location_dest_id', '=', self.warehouse_1.wh_qc_stock_loc_id.id)])
        incoming_shipment1_date = order_date + timedelta(days=self.product_1.seller_ids.delay + company.po_lead)
        self.assertEqual(incoming_shipment1.scheduled_date, incoming_shipment1_date, 'Schedule date of Internal Type shipment for input stock location should be equal to: schedule date of purchase order + push rule delay.')
        self.assertEqual(incoming_shipment1.date_deadline, incoming_shipment1_date)
        old_deadline1 = incoming_shipment1.date_deadline

        incoming_shipment2 = self.env['stock.picking'].search([('picking_type_id', '=', self.warehouse_1.int_type_id.id), ('location_id', '=', self.warehouse_1.wh_qc_stock_loc_id.id), ('location_dest_id', '=', self.warehouse_1.lot_stock_id.id)])
        incoming_shipment2_date = schedule_date - timedelta(days=incoming_shipment2.move_lines[0].rule_id.delay)
        self.assertEqual(incoming_shipment2.scheduled_date, incoming_shipment2_date, 'Schedule date of Internal Type shipment for quality control stock location should be equal to: schedule date of Internal type shipment for input stock location + push rule delay..')
        self.assertEqual(incoming_shipment2.date_deadline, incoming_shipment2_date)
        old_deadline2 = incoming_shipment2.date_deadline

        # Modify the date_planned of the purchase -> propagate the deadline
        purchase_form = Form(purchase)
        purchase_form.date_planned = purchase.date_planned + timedelta(days=1)
        purchase_form.save()
        self.assertEqual(incoming_shipment2.date_deadline, old_deadline2 + timedelta(days=1), 'Deadline should be propagate')
        self.assertEqual(incoming_shipment1.date_deadline, old_deadline1 + timedelta(days=1), 'Deadline should be propagate')

    def test_merge_po_line(self):
        """Change that merging po line for same procurement is done."""

        # create a product with manufacture route
        product_1 = self.env['product.product'].create({
            'name': 'AAA',
            'route_ids': [(4, self.route_buy)],
            'seller_ids': [(0, 0, {'name': self.partner_1.id, 'delay': 5})]
        })

        # create a move for product_1 from stock to output and reserve to trigger the
        # rule
        move_1 = self.env['stock.move'].create({
            'name': 'move_1',
            'product_id': product_1.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'product_uom_qty': 10,
            'procure_method': 'make_to_order'
        })

        move_1._action_confirm()
        po_line = self.env['purchase.order.line'].search([
            ('product_id', '=', product_1.id),
        ])
        self.assertEqual(len(po_line), 1, 'the purchase order line is not created')
        self.assertEqual(po_line.product_qty, 10, 'the purchase order line has a wrong quantity')

        move_2 = self.env['stock.move'].create({
            'name': 'move_2',
            'product_id': product_1.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            'product_uom_qty': 5,
            'procure_method': 'make_to_order'
        })

        move_2._action_confirm()
        po_line = self.env['purchase.order.line'].search([
            ('product_id', '=', product_1.id),
        ])
        self.assertEqual(len(po_line), 1, 'the purchase order lines should be merged')
        self.assertEqual(po_line.product_qty, 15, 'the purchase order line has a wrong quantity')

    def test_merge_po_line_3(self):
        """Change merging po line if same procurement is done depending on custom values."""
        company = self.env.ref('base.main_company')
        company.write({'po_lead': 0.00})

        # The seller has a specific product name and code which must be kept in the PO line
        self.t_shirt.seller_ids.write({
            'product_name': 'Vendor Name',
            'product_code': 'Vendor Code',
        })
        partner = self.t_shirt.seller_ids[:1].name
        t_shirt = self.t_shirt.with_context(
            lang=partner.lang,
            partner_id=partner.id,
        )

        # Create procurement order of product_1
        ProcurementGroup = self.env['procurement.group']
        procurement_values = {
            'warehouse_id': self.warehouse_1,
            'rule_id': self.warehouse_1.buy_pull_id,
            'date_planned': fields.Datetime.to_string(fields.datetime.now() + timedelta(days=10)),
            'group_id': False,
            'route_ids': [],
        }

        procurement_values['product_description_variants'] = 'Color (Red)'
        order_1_values = procurement_values
        ProcurementGroup.run([self.env['procurement.group'].Procurement(
            self.t_shirt, 5, self.uom_unit, self.warehouse_1.lot_stock_id,
            self.t_shirt.name, '/', self.env.company, order_1_values)
        ])
        purchase_order = self.env['purchase.order.line'].search([('product_id', '=', self.t_shirt.id)], limit=1).order_id
        order_line_description = purchase_order.order_line.product_id._get_description(purchase_order.picking_type_id)
        self.assertEqual(len(purchase_order.order_line), 1, 'wrong number of order line is created')
        self.assertEqual(purchase_order.order_line.name, t_shirt.display_name + "\n" + "Color (Red)", 'wrong description in po lines')

        procurement_values['product_description_variants'] = 'Color (Red)'
        order_2_values = procurement_values
        ProcurementGroup.run([self.env['procurement.group'].Procurement(
            self.t_shirt, 10, self.uom_unit, self.warehouse_1.lot_stock_id,
            self.t_shirt.name, '/', self.env.company, order_2_values)
        ])
        self.env['procurement.group'].run_scheduler()
        self.assertEqual(len(purchase_order.order_line), 1, 'line with same custom value should be merged')
        self.assertEqual(purchase_order.order_line[0].product_qty, 15, 'line with same custom value should be merged and qty should be update')

        procurement_values['product_description_variants'] = 'Color (Green)'

        order_3_values = procurement_values
        ProcurementGroup.run([self.env['procurement.group'].Procurement(
            self.t_shirt, 10, self.uom_unit, self.warehouse_1.lot_stock_id,
            self.t_shirt.name, '/', self.env.company, order_3_values)
        ])
        self.assertEqual(len(purchase_order.order_line), 2, 'line with different custom value should not be merged')
        self.assertEqual(purchase_order.order_line.filtered(lambda x: x.product_qty == 15).name, t_shirt.display_name + "\n" + "Color (Red)", 'wrong description in po lines')
        self.assertEqual(purchase_order.order_line.filtered(lambda x: x.product_qty == 10).name, t_shirt.display_name + "\n" + "Color (Green)", 'wrong description in po lines')

        purchase_order.button_confirm()
        self.assertEqual(purchase_order.picking_ids[0].move_ids_without_package.filtered(lambda x: x.product_uom_qty == 15).description_picking, order_line_description + "\nColor (Red)", 'wrong description in picking')
        self.assertEqual(purchase_order.picking_ids[0].move_ids_without_package.filtered(lambda x: x.product_uom_qty == 10).description_picking, order_line_description + "\nColor (Green)", 'wrong description in picking')

    def test_reordering_days_to_purchase(self):
        company = self.env.ref('base.main_company')
        company2 = self.env['res.company'].create({
            'name': 'Second Company',
        })
        company.write({'po_lead': 0.00})
        self.patcher = patch('odoo.addons.stock.models.stock_orderpoint.fields.Date', wraps=fields.Date)
        self.mock_date = self.patcher.start()

        vendor = self.env['res.partner'].create({
            'name': 'Colruyt'
        })
        vendor2 = self.env['res.partner'].create({
            'name': 'Delhaize'
        })

        self.env.company.days_to_purchase = 2.0

        product = self.env['product.product'].create({
            'name': 'Chicory',
            'type': 'product',
            'seller_ids': [
                (0, 0, {'name': vendor2.id, 'delay': 15.0, 'company_id': company2.id}),
                (0, 0, {'name': vendor.id, 'delay': 1.0, 'company_id': company.id})
            ]
        })
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = product
        orderpoint_form.product_min_qty = 0.0
        orderpoint = orderpoint_form.save()

        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'].with_company(company2))
        orderpoint_form.product_id = product
        orderpoint_form.product_min_qty = 0.0
        orderpoint = orderpoint_form.save()

        warehouse = self.env['stock.warehouse'].search([], limit=1)
        delivery_moves = self.env['stock.move']
        for i in range(0, 6):
            delivery_moves |= self.env['stock.move'].create({
                'name': 'Delivery',
                'date': datetime.today() + timedelta(days=i),
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 5.0,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })
        delivery_moves._action_confirm()
        self.env['procurement.group'].run_scheduler()
        po_line = self.env['purchase.order.line'].search([('product_id', '=', product.id)])
        self.assertEqual(fields.Date.to_date(po_line.order_id.date_order), fields.Date.today() + timedelta(days=2))
        self.assertEqual(len(po_line), 1)
        self.assertEqual(po_line.product_uom_qty, 20.0)
        self.assertEqual(len(po_line.order_id), 1)
        orderpoint_form = Form(orderpoint)
        orderpoint_form.save()

        self.mock_date.today.return_value = fields.Date.today() + timedelta(days=1)
        orderpoint._compute_qty()
        self.env['procurement.group'].run_scheduler()
        po_line = self.env['purchase.order.line'].search([('product_id', '=', product.id)])
        self.assertEqual(len(po_line), 2)
        self.assertEqual(len(po_line.order_id), 2)
        new_order = po_line.order_id.sorted('date_order')[-1]
        self.assertEqual(fields.Date.to_date(new_order.date_order), fields.Date.today() + timedelta(days=2))
        self.assertEqual(new_order.order_line.product_uom_qty, 5.0)
        self.patcher.stop()
