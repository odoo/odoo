# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time
from json import loads

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo import fields, Command



class TestMrpReplenish(TestMrpCommon):

    def _create_wizard(self, product, warehouse):
        return self.env['product.replenish'].with_context(default_product_tmpl_id=product.product_tmpl_id.id).create({
                'product_id': product.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 1,
                'warehouse_id': warehouse.id,
            })

    def test_mrp_delay(self):
        """Open the replenish view and check if delay is taken into account
            in the base date computation
        """
        route = self.warehouse_1.manufacture_pull_id.route_id
        product = self.product_4
        product.route_ids = route

        with freeze_time("2023-01-01"):
            wizard = self._create_wizard(product, self.warehouse_1)
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            route.rule_ids[0].delay = 2
            wizard3 = self._create_wizard(product, self.warehouse_1)
            self.assertEqual(fields.Datetime.from_string('2023-01-03 00:00:00'), wizard3.date_planned)

    def test_mrp_orderpoint_leadtime(self):
        self.env.company.horizon_days = 0
        route_manufacture = self.warehouse_1.manufacture_pull_id.route_id
        route_manufacture.supplied_wh_id = self.warehouse_1
        route_manufacture.supplier_wh_id = self.warehouse_1
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
            'location_id': self.stock_location.id,
            'product_id': product_1.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })

        info = self.env['stock.replenishment.info'].create({'orderpoint_id': rr.id})

        # for manufacturing delay should be taken from the bom
        self.assertEqual("4.0 days", info.wh_replenishment_option_ids.lead_time)

    def test_rr_picking_type_id(self):
        """Check manufacturing order take bom according to picking type of the rule triggered by an
        orderpoint."""

        self.product_4.route_ids = self.warehouse_1.manufacture_pull_id.route_id
        picking_type_2 = self.picking_type_manu.copy({'sequence': 100})
        self.product_4.bom_ids.picking_type_id = picking_type_2
        rr = self.env['stock.warehouse.orderpoint'].create({
            'name': 'Cake RR',
            'location_id': self.warehouse_1.lot_stock_id.id,
            'product_id': self.product_4.id,
            'product_min_qty': 5,
            'product_max_qty': 10,
        })

        rr.action_replenish()
        mo = self.env['mrp.production'].search([
            ('product_id', '=', self.product_4.id),
            ('picking_type_id', '=', picking_type_2.id)
        ])
        self.assertTrue(mo)

    def test_mrp_delay_bom(self):
        route = self.warehouse_1.manufacture_pull_id.route_id
        product = self.product_4
        bom = product.bom_ids
        product.route_ids = route
        with freeze_time("2023-01-01"):
            wizard = self._create_wizard(product, self.warehouse_1)
            self.assertEqual(fields.Datetime.from_string('2023-01-01 00:00:00'), wizard.date_planned)
            bom.produce_delay = 2
            wizard2 = self._create_wizard(product, self.warehouse_1)
            self.assertEqual(fields.Datetime.from_string('2023-01-03 00:00:00'), wizard2.date_planned)
            bom.days_to_prepare_mo = 4
            wizard3 = self._create_wizard(product, self.warehouse_1)
            self.assertEqual(fields.Datetime.from_string('2023-01-07 00:00:00'), wizard3.date_planned)

    def test_replenish_from_scrap(self):
        """ Test that when ticking replenish on the scrap wizard of a MO, the new move
        is linked to the MO and validating it will automatically reserve the quantity
        on the MO. """
        self.warehouse_1.manufacture_steps = 'pbm'
        basic_mo, dummy1, dummy2, product_to_scrap, other_product = self.generate_mo(qty_final=1, qty_base_1=1, qty_base_2=1)
        for product in (product_to_scrap, other_product):
            self.env['stock.quant'].create({
                'product_id': product.id,
                'location_id': self.stock_location.id,
                'quantity': 2
            })
        self.assertEqual(basic_mo.move_raw_ids.location_id, self.warehouse_1.pbm_loc_id)
        basic_mo.action_confirm()
        self.assertEqual(len(basic_mo.picking_ids), 1)
        basic_mo.picking_ids.action_assign()
        basic_mo.picking_ids.button_validate()
        self.assertEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])

        scrap_form = Form.from_action(self.env, basic_mo.button_scrap())
        scrap_form.product_id = product_to_scrap
        scrap_form.should_replenish = True
        self.assertEqual(scrap_form.location_id, self.warehouse_1.pbm_loc_id)
        scrap_form.save().action_validate()
        self.assertNotEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])
        self.assertEqual(len(basic_mo.picking_ids), 2)
        replenish_picking = basic_mo.picking_ids.filtered(lambda x: x.state == 'assigned')
        replenish_picking.button_validate()
        self.assertEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])

    def test_scrap_replenishment_reassigns_required_qty_to_component(self):
        """ Test that when validating the scrap replenishment transfer, the required quantity
        is re-assigned to the component for the final manufacturing product. """
        self.warehouse_1.manufacture_steps = 'pbm'
        basic_mo, _, _, product_to_scrap, other_product = self.generate_mo(qty_final=1, qty_base_1=10, qty_base_2=10)
        for product in (product_to_scrap, other_product):
            self.env['stock.quant'].create({
                'product_id': product.id,
                'location_id': self.stock_location.id,
                'quantity': 20
            })
        self.assertEqual(basic_mo.move_raw_ids.location_id, self.warehouse_1.pbm_loc_id)
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
        self.assertEqual(scrap_form.location_id, self.warehouse_1.pbm_loc_id)
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

    def test_global_horizon_days_affect_lead_time_manufacture_rule(self):
        """ Ensure global horizon days will only be captured one time in an orderpoint's
        lead_days/json_lead_days.
        """
        self.warehouse_1.manufacture_steps = 'pbm'
        finished_product = self.product_4
        finished_product.route_ids = [Command.set(self.warehouse_1.manufacture_pull_id.route_id.ids)]

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': finished_product.id,
            'location_id': self.stock_location.id,
        })
        out_picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'move_ids': [Command.create({
                'product_id': finished_product.id,
                'product_uom_qty': 2,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
            })],
        })
        out_picking.with_context(global_horizon_days=365).action_assign()
        r = orderpoint.action_stock_replenishment_info()
        repl_info = self.env[r['res_model']].browse(r['res_id'])
        lead_horizon_date = datetime.strptime(
            loads(repl_info.json_lead_days)['lead_horizon_date'], '%m/%d/%Y').date()
        self.assertEqual(lead_horizon_date, fields.Date.today() + timedelta(days=365))

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
        # Error is triggered for date_start <= lead_horizon_date < date_finished
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

    def test_orderpoint_warning_mrp(self):
        """ Checks that the warning correctly computes depending on if there's a bom. """
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product_4.id,
            'product_min_qty': 10,
            'product_max_qty': 50,
        })
        self.product_4.bom_ids.active = False
        self.assertTrue(orderpoint.show_supply_warning)

        # Archive the boms linked to the product
        self.product_4.with_context(active_test=False).bom_ids.active = True
        orderpoint.invalidate_recordset(fnames=['rule_ids', 'show_supply_warning'])
        self.assertFalse(orderpoint.show_supply_warning)

        # Add a manufacture route to the product
        self.product_4.route_ids |= self.route_manufacture
        orderpoint.invalidate_recordset(fnames=['show_supply_warning'])
        self.assertFalse(orderpoint.show_supply_warning)

    def test_set_bom_on_orderpoint(self):
        """ Test that action_set_bom_on_orderpoint correctly sets a bom on selected orderpoint. """
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.product_4.id,
            'product_min_qty': 10,
            'product_max_qty': 50,
        })
        self.product_4.bom_ids.with_context(orderpoint_id=orderpoint.id).action_set_bom_on_orderpoint()
        self.assertEqual(orderpoint.bom_id.id, self.product_4.bom_ids.id)

    def test_effective_bom(self):
        route = self.env['stock.route'].create({
            'name': 'Manufacture',
            'rule_ids': [
                Command.create({
                    'name': 'Manufacture',
                    'location_dest_id': self.stock_location.id,
                    'action': 'manufacture',
                    'picking_type_id': self.picking_type_in.id,
                }),
            ],
        })

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'product_id': self.productA.id,
            'product_min_qty': 2,
            'product_max_qty': 4,
        })
        # The Manufacture route is not set on the product -> no effective BoM
        self.assertFalse(orderpoint.effective_bom_id)

        self.productA.write({
            'route_ids': [(4, route.id)],
        })
        self.env.invalidate_all()
        # The route is set, but there is no BoM -> no effective BoM
        self.assertFalse(orderpoint.effective_bom_id)

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.productA.product_tmpl_id.id,
            'product_qty': 1,
            'code': 'Ref 1234',
        })

        self.env.invalidate_all()
        # The route is set and there is a BoM -> effective BoM is available
        self.assertEqual(orderpoint.effective_bom_id, bom)
        self.assertEqual(orderpoint.bom_id_placeholder, 'Ref 1234: Product A')
        # The actual BoM remains empty
        self.assertFalse(orderpoint.bom_id)

    def test_lead_time_with_no_bom(self):
        """Test that lead time is incremented by 365 days (1 year) when there
        is no BoM defined.
        """
        route_manufacture = self.warehouse_1.manufacture_pull_id.route_id
        product = self.env['product.product'].create({
            'name': 'test',
            'is_storable': True,
            'route_ids': route_manufacture.ids,
        })
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': 'test',
            'location_id': self.warehouse_1.lot_stock_id.id,
            'product_id': product.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })
        self.assertEqual(orderpoint.lead_days, 365)
