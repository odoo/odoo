# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests.common import Form
from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestSalePurchaseStockReports(TestReportsCommon):
    def test_report_forecast_1_so_waiting_po(self):
        """ Creates a sale order for a product buy MTO and checks the sale order
        is correclty linked to the generated purchase order in the report.
        """
        # Product config.
        warehouse = self.env.ref('stock.warehouse0')
        route_mto = warehouse.mto_pull_id.route_id.id
        route_buy = self.ref('purchase_stock.route_warehouse0_buy')
        supplier_info1 = self.env['product.supplierinfo'].create({
            'name': self.partner.id,
            'price': 50,
        })
        self.product.seller_ids = supplier_info1.ids
        self.product.route_ids = [(6, 0, [route_buy, route_mto])]

        # Create a sale order.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so = so_form.save()
        so.action_confirm()

        # Get back the purchase order and confirms it.
        po = self.env['purchase.order'].search([('product_id', '=', self.product.id)])
        po.button_confirm()

        # Checks the report values.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in'].id, po.id)
        self.assertEqual(lines[0]['document_out'].id, so.id)

    def test_report_forecast_2_multi_step_so_waiting_po(self):
        """ With a multi-step receipt and multi-step delivery config, creates a
        sale order for a product buy MTO and checks the sale order is correclty
        linked to the generated purchase order in the report.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})
        # Product config.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.reception_steps = 'three_steps'
        warehouse.delivery_steps = 'pick_pack_ship'
        route_mto = warehouse.mto_pull_id.route_id.id
        route_buy = self.ref('purchase_stock.route_warehouse0_buy')
        supplier_info1 = self.env['product.supplierinfo'].create({
            'name': self.partner.id,
            'price': 50,
        })
        self.product.seller_ids = supplier_info1.ids
        self.product.route_ids = [(6, 0, [route_buy, route_mto])]

        # Create a sale order.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        with so_form.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 5
        so = so_form.save()
        so.action_confirm()

        # Get back the purchase order and confirms it.
        po = self.env['purchase.order'].search([('product_id', '=', self.product.id)])
        po.button_confirm()

        # Checks the report values.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in'].id, po.id)
        self.assertEqual(lines[0]['document_out'].id, so.id)

        receipt = po.picking_ids
        input_to_qc = receipt.move_lines.move_dest_ids.picking_id
        qc_to_stock = input_to_qc.move_lines.move_dest_ids.picking_id
        delivery = so.order_line.move_ids.picking_id
        pack = delivery.move_lines.move_orig_ids.picking_id
        pick = pack.move_lines.move_orig_ids.picking_id
        # Change the pickings scheduled date.
        today = datetime.today()
        receipt.scheduled_date = today
        input_to_qc.scheduled_date = today + timedelta(days=1)
        qc_to_stock.scheduled_date = today + timedelta(days=2)
        pick.scheduled_date = today + timedelta(days=3)
        pack.scheduled_date = today + timedelta(days=4)
        delivery.scheduled_date = today + timedelta(days=5)
