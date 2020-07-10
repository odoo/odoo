# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form
from odoo.addons.stock.tests.test_report import TestReportsCommon


class TestSaleMRPStockReports(TestReportsCommon):
    def test_report_forecast_1_so_waiting_mo_multistep(self):
        """ Creates a sale order who will trigger a production order.
        With the pick-pack-ship config and 2 step manufacture, in the report,
        the sale order must be linked to the production order.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})
        # Warehouse config.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.delivery_steps = 'pick_pack_ship'
        warehouse.manufacture_steps = 'pbm_sam'
        route_manufacture = warehouse.manufacture_pull_id.route_id.id
        route_mto = warehouse.mto_pull_id.route_id.id
        # Configures a product.
        product_apple_pie = self.env['product.product'].create({
            'name': 'Apple Pie',
            'type': 'product',
            'route_ids': [(6, 0, [route_manufacture, route_mto])],
        })
        product_apple = self.env['product.product'].create({
            'name': 'Apple',
            'type': 'consu',
        })
        self.env['mrp.bom'].create({
            'product_id': product_apple_pie.id,
            'product_tmpl_id': product_apple_pie.product_tmpl_id.id,
            'product_uom_id': product_apple_pie.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_apple.id, 'product_qty': 5}),
            ],
        })
        # Creates and confirms the SO.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner
        with so_form.order_line.new() as line:
            line.product_id = product_apple_pie
            line.product_uom_qty = 5
        so = so_form.save()
        so.action_confirm()
        # Get back SO's pickings.
        delivery = so.picking_ids.filtered(lambda picking: picking.picking_type_code == 'outgoing')
        pack = delivery.move_lines.move_orig_ids.picking_id
        pick = pack.move_lines.move_orig_ids.picking_id
        sfp = pick.move_lines.move_orig_ids.picking_id
        # Get back the MO and its picking.
        mo = so.procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids
        from_stock_to_preprod = mo.picking_ids
        # Check the report values.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0]['document_in'].id, mo.id,
            "Must refer to the MO even if it's waiting preprod move"
        )
        self.assertEqual(lines[0]['document_out'].id, so.id)
        self.assertEqual(lines[0]['quantity'], 5)

        # Proceeds the pre-prod. transfer and validates it.
        picking_form = Form(from_stock_to_preprod)
        with picking_form.move_line_ids_without_package.edit(0) as line:
            line.qty_done = 25
        from_stock_to_preprod = picking_form.save()
        from_stock_to_preprod.button_validate()
        # Check the report values (still must be the same).
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['document_in'].id, mo.id)
        self.assertEqual(lines[0]['document_out'].id, so.id)
        self.assertEqual(lines[0]['quantity'], 5)

        # Proceeds the MO and validates it.
        mo_form = Form(mo)
        mo_form.qty_producing = 5
        mo = mo_form.save()
        mo.button_mark_done()
        # Check the report values.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0]['document_in'].id, sfp.id,
            "MO is done, must refer to the next transfer"
        )
        self.assertEqual(lines[0]['document_in'].id, sfp.id)
        self.assertEqual(lines[0]['document_out'].id, so.id)
        self.assertEqual(lines[0]['quantity'], 5)

        # Proceeds the post-prod. transfer and validates it.
        picking_form = Form(sfp)
        with picking_form.move_line_ids_without_package.edit(0) as line:
            line.qty_done = 5
        sfp = picking_form.save()
        sfp.button_validate()
        # Check the report values.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0]['document_in'].id, pick.id,
            "MO and SFP are done, must refer to the pick transfer"
        )
        self.assertEqual(lines[0]['document_in'].id, pick.id)
        self.assertEqual(lines[0]['document_out'].id, so.id)
        self.assertEqual(lines[0]['quantity'], 5)

        # Proceeds the pick transfer and validates it.
        pick.move_line_ids_without_package[0].qty_done = 5
        pick.button_validate()
        # Check the report values.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0]['document_in'].id, pack.id,
            "The pick is done, must refer to the pack transfer"
        )
        self.assertEqual(lines[0]['document_in'].id, pack.id)
        self.assertEqual(lines[0]['document_out'].id, so.id)
        self.assertEqual(lines[0]['quantity'], 5)

        # Proceeds the pack transfer and validates it.
        pack.move_line_ids_without_package.qty_done = 5
        pack.button_validate()
        # Check the report values.
        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_apple_pie.product_tmpl_id.ids)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0]['document_in'], False,
            "The pack is done, and as the quantity is in the sotck now, must not refer to a transfer anymore"
        )
        self.assertEqual(lines[0]['replenishment_filled'], True)
        self.assertEqual(lines[0]['document_in'], False)
        self.assertEqual(lines[0]['document_out'].id, so.id)
        self.assertEqual(lines[0]['quantity'], 5)
