# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time
from json import loads

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo import Command, fields



class TestMrpReplenish(TestMrpCommon):

    def _create_wizard(self, product, wh):
        return self.env['product.replenish'].with_context(default_product_tmpl_id=product.product_tmpl_id.id).create({
                'product_id': product.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'warehouse_id': wh.id,
            })

    def test_mrp_delay(self):
        """Open the replenish view and check if delay is taken into account
            in the base date computation
        """
        route = self.env.ref('mrp.route_warehouse0_manufacture')
        product = self.product_4
        product.route_ids = route
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        self.env.company.manufacturing_lead = 0
        self.env['ir.config_parameter'].sudo().set_param('mrp.use_manufacturing_lead', True)

        with freeze_time("2023-01-01"):
            wizard = self._create_wizard(product, wh)
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            self.env.company.manufacturing_lead = 3
            wizard2 = self._create_wizard(product, wh)
            self.assertEqual(fields.Datetime.from_string('2023-01-04 00:00:00'), wizard2.date_planned)
            route.rule_ids[0].delay = 2
            wizard3 = self._create_wizard(product, wh)
            self.assertEqual(fields.Datetime.from_string('2023-01-06 00:00:00'), wizard3.date_planned)

    def test_mrp_orderpoint_leadtime(self):
        self.warehouse = self.env.ref('stock.warehouse0')
        route_manufacture = self.warehouse.manufacture_pull_id.route_id
        route_manufacture.supplied_wh_id = self.warehouse
        route_manufacture.supplier_wh_id = self.warehouse
        route_manufacture.rule_ids.delay = 2
        product_1 = self.env['product.product'].create({
            'name': 'Cake',
            'is_storable': True,
            'route_ids': [(6, 0, [route_manufacture.id])]
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': product_1.product_tmpl_id.id,
            'produce_delay': 4,
            'product_qty': 1,
        })

        # setup orderpoint (reordering rule)
        rr = self.env['stock.warehouse.orderpoint'].create({
            'name': 'Cake RR',
            'location_id': self.warehouse.lot_stock_id.id,
            'product_id': product_1.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })

        info = self.env['stock.replenishment.info'].create({'orderpoint_id': rr.id})

        # for manufacturing delay should be taken from the bom
        self.assertEqual("4.0 days", info.wh_replenishment_option_ids.lead_time)

    def test_mrp_delay_bom(self):
        route = self.env.ref('mrp.route_warehouse0_manufacture')
        product = self.product_4
        bom = product.bom_ids
        product.route_ids = route
        wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        self.env.company.manufacturing_lead = 0
        with freeze_time("2023-01-01"):
            wizard = self._create_wizard(product, wh)
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            bom.produce_delay = 2
            wizard2 = self._create_wizard(product, wh)
            self.assertEqual(fields.Datetime.from_string('2023-01-03 00:00:00'), wizard2.date_planned)
            bom.days_to_prepare_mo = 4
            wizard3 = self._create_wizard(product, wh)
            self.assertEqual(fields.Datetime.from_string('2023-01-07 00:00:00'), wizard3.date_planned)

    def test_replenish_from_scrap(self):
        """ Test that when ticking replenish on the scrap wizard of a MO, the new move
        is linked to the MO and validating it will automatically reserve the quantity
        on the MO. """
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.manufacture_steps = 'pbm'
        basic_mo, dummy1, dummy2, product_to_scrap, other_product = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        for product in (product_to_scrap, other_product):
            self.env['stock.quant'].create({
                'product_id': product.id,
                'location_id': warehouse.lot_stock_id.id,
                'quantity': 2
            })
        self.assertEqual(basic_mo.move_raw_ids.location_id, warehouse.pbm_loc_id)
        basic_mo.action_confirm()
        self.assertEqual(len(basic_mo.picking_ids), 1)
        basic_mo.picking_ids.action_assign()
        basic_mo.picking_ids.button_validate()
        self.assertEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])

        scrap_form = Form.from_action(self.env, basic_mo.button_scrap())
        scrap_form.product_id = product_to_scrap
        scrap_form.should_replenish = True
        self.assertEqual(scrap_form.location_id, warehouse.pbm_loc_id)
        scrap_form.save().action_validate()
        self.assertNotEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])
        self.assertEqual(len(basic_mo.picking_ids), 2)
        replenish_picking = basic_mo.picking_ids.filtered(lambda x: x.state == 'assigned')
        replenish_picking.button_validate()
        self.assertEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])

    def test_scrap_replenishment_reassigns_required_qty_to_component(self):
        """ Test that when validating the scrap replenishment transfer, the required quantity
        is re-assigned to the component for the final manufacturing product. """
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.manufacture_steps = 'pbm'
        basic_mo, _, _, product_to_scrap, other_product = self.generate_mo(qty_final=1, qty_base_1=10, qty_base_2=10)
        for product in (product_to_scrap, other_product):
            self.env['stock.quant'].create({
                'product_id': product.id,
                'location_id': warehouse.lot_stock_id.id,
                'quantity': 20
            })
        self.assertEqual(basic_mo.move_raw_ids.location_id, warehouse.pbm_loc_id)
        basic_mo.action_confirm()
        self.assertEqual(len(basic_mo.picking_ids), 1)
        basic_mo.picking_ids.action_assign()
        basic_mo.picking_ids.button_validate()
        self.assertEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])

        # Scrap the product and trigger replenishment
        scrap_form = Form.from_action(self.env, basic_mo.button_scrap())
        scrap_form.product_id = product_to_scrap
        scrap_form.scrap_qty = 5
        scrap_form.should_replenish = True
        self.assertEqual(scrap_form.location_id, warehouse.pbm_loc_id)
        scrap_form.save().action_validate()

        # Assert that the component quantity is reduced
        self.assertNotEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])
        move_to_scrap = basic_mo.move_raw_ids.filtered(lambda m: m.product_id == product_to_scrap)
        move_other = basic_mo.move_raw_ids.filtered(lambda m: m.product_id == other_product)
        self.assertEqual(move_to_scrap.quantity, 5, "Scrapped component should have qty 5")
        self.assertEqual(move_other.quantity, 10, "Other component should remain qty 10")
        self.assertEqual(len(basic_mo.picking_ids), 2)

        replenish_picking = basic_mo.picking_ids.filtered(lambda x: x.state == 'assigned')
        replenish_picking.button_validate()

        # Assert that the component quantity is re-assigned
        self.assertEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])
        self.assertEqual(move_to_scrap.quantity, 10, "Scrapped component should return to qty 10")
        self.assertEqual(move_other.quantity, 10, "Other component should still be qty 10")

    def test_global_visibility_days_affect_lead_time_manufacture_rule(self):
        """ Ensure global visibility days will only be captured one time in an orderpoint's
        lead_days/json_lead_days.
        """
        wh = self.env.user._get_default_warehouse_id()
        wh.manufacture_steps = 'pbm'
        finished_product = self.product_4
        finished_product.route_ids = [(6, 0, self.env['stock.route'].search([('name', '=', 'Manufacture')], limit=1).ids)]
        self.env['ir.config_parameter'].set_param('stock.visibility_days', '365')

        orderpoint = self.env['stock.warehouse.orderpoint'].create({'product_id': finished_product.id})
        out_picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_ids': [Command.create({
                'name': 'TGVDALTMR out move',
                'product_id': finished_product.id,
                'product_uom_qty': 2,
                'location_id': wh.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        out_picking.with_context(global_visibility_days=365).action_assign()
        r = orderpoint.action_stock_replenishment_info()
        repl_info = self.env[r['res_model']].browse(r['res_id'])
        lead_days_date = datetime.strptime(
            loads(repl_info.json_lead_days)['lead_days_date'], '%m/%d/%Y').date()
        self.assertEqual(lead_days_date, fields.Date.today() + timedelta(days=365))

    def test_replenish_multi_level_bom_with_pbm_sam(self):
        """
        Ensure that in a 3-step manufacturing flow ('pbm_sam') with MTO + reordering rule,
        a multi-level BOM triggers separate MOs for each level without constraint errors.
        1.) Set warehouse manufacture to (manufacture_steps == 'pbm_sam')
        2.) Product_1 (enable manufacture and mto routes)
        3.) Product_4 (enable manufacture)
        4.) Add Product_1 as bom for product_4
        5.) Add a reordering rule (manufacture) for product_4
        6.) trigger replenishment for product_4
        """
        self.warehouse = self.env.ref('stock.warehouse0')
        self.warehouse.write({'manufacture_steps': 'pbm_sam'})
        self.warehouse.mto_pull_id.route_id.active = True

        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id

        self.product_1.write({
            'route_ids': [(6, 0, [route_mto, route_manufacture])]
        })  # Component
        self.product_4.write({
            'route_ids': [(6, 0, [route_manufacture])],
            'bom_ids': [(6, 0, [self.bom_1.id])]
        })  # Finished Product

        # Create reordering rule
        self.env['stock.warehouse.orderpoint'].create({
            'location_id': self.warehouse.lot_stock_id.id,
            'product_id': self.product_4.id,
            'route_id': route_manufacture,
            'product_min_qty': 1,
            'product_max_qty': 1,
        })
        self.product_4.orderpoint_ids.action_replenish()

        # Check both MOs were created
        mo_final = self.env['mrp.production'].search([('product_id', '=', self.product_4.id)])
        mo_component = self.env['mrp.production'].search([('product_id', '=', self.product_1.id)])

        self.assertEqual(len(mo_final), 1, "Expected one MO for the final product.")
        self.assertEqual(len(mo_component), 1, "Expected one MO for the manufactured BOM component.")

    def test_orderpoint_onchange_reordering_rule(self):
        """ Ensure onchange logic works properly when editing a reordering rule
            linked to a confirmed MO, which is started but not finished by the
            end of the stock forecast.
        """
        route_manufacture = self.warehouse_1.manufacture_pull_id.route_id

        self.product_4.route_ids = [Command.set([route_manufacture.id])]
        self.product_4.bom_ids.produce_delay = 2

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product_4.id,
            'product_min_qty': 2,
            'product_max_qty': 2,
        })

        orderpoint.action_replenish()

        prod = self.env['mrp.production'].search([('origin', '=', orderpoint.name)])
        # Error is triggered for date_start <= lead_days_date < date_finished
        prod.date_start = fields.Date.today() + timedelta(days=1)

        with Form(orderpoint, view='stock.view_warehouse_orderpoint_tree_editable') as form:
            form.product_min_qty = 3
        self.assertEqual(orderpoint.qty_to_order, 1)

        orderpoint.trigger = 'manual'
        with Form(orderpoint, view='stock.view_warehouse_orderpoint_tree_editable') as form:
            form.product_min_qty = 10
            self.assertEqual(form.qty_to_order, 0)
        self.assertEqual(form.qty_to_order, 8)
        self.assertEqual(orderpoint.qty_to_order, 8)
