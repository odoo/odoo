# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from datetime import date, datetime, timedelta
from odoo.tests import common, Form
from odoo import Command
from odoo.tools.date_utils import start_of


class TestMpsMps(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Define a multi level BoM and generate a production schedule with
        default value for each of the products.
        BoM 1:
                                    Table
                                      |
                        ------------------------------------
                    1 Drawer                            2 Table Legs
                        |                                   |
                ----------------                    -------------------
            4 Screw         2 Table Legs        4 Screw             4 Bolt
                                |
                        -------------------
                    4 Screw             4 Bolt

        BoM 2 and 3:
                Wardrobe              Chair
                    |                   |
                3 Drawer            4 Table Legs
        """
        super().setUpClass()

        cls.mps_dates_month = cls.env.company._get_date_range()
        cls.manufacture_route = cls.env.ref('mrp.route_warehouse0_manufacture')

        cls.table = cls.env['product.product'].create({
            'name': 'Table',
            'is_storable': True,
            'route_ids': [Command.set([cls.manufacture_route.id])],
        })
        cls.drawer = cls.env['product.product'].create({
            'name': 'Drawer',
            'is_storable': True,
            'route_ids': [Command.set([cls.manufacture_route.id])],
        })
        cls.table_leg = cls.env['product.product'].create({
            'name': 'Table Leg',
            'is_storable': True,
            'route_ids': [Command.set([cls.manufacture_route.id])],
        })
        cls.screw = cls.env['product.product'].create({
            'name': 'Screw',
            'is_storable': True,
        })
        cls.bolt = cls.env['product.product'].create({
            'name': 'Bolt',
            'is_storable': True,
        })
        bom_form_table = Form(cls.env['mrp.bom'])
        bom_form_table.product_tmpl_id = cls.table.product_tmpl_id
        bom_form_table.product_qty = 1
        cls.bom_table = bom_form_table.save()

        with Form(cls.bom_table) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.drawer
                line.product_qty = 1
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.table_leg
                line.product_qty = 2

        bom_form_drawer = Form(cls.env['mrp.bom'])
        bom_form_drawer.product_tmpl_id = cls.drawer.product_tmpl_id
        bom_form_drawer.product_qty = 1
        cls.bom_drawer = bom_form_drawer.save()

        with Form(cls.bom_drawer) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.table_leg
                line.product_qty = 2
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.screw
                line.product_qty = 4

        bom_form_table_leg = Form(cls.env['mrp.bom'])
        bom_form_table_leg.product_tmpl_id = cls.table_leg.product_tmpl_id
        bom_form_table_leg.product_qty = 1
        cls.bom_table_leg = bom_form_table_leg.save()

        with Form(cls.bom_table_leg) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.bolt
                line.product_qty = 4
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.screw
                line.product_qty = 4

        cls.wardrobe = cls.env['product.product'].create({
            'name': 'Wardrobe',
            'is_storable': True,
        })

        bom_form_wardrobe = Form(cls.env['mrp.bom'])
        bom_form_wardrobe.product_tmpl_id = cls.wardrobe.product_tmpl_id
        bom_form_wardrobe.product_qty = 1
        cls.bom_wardrobe = bom_form_wardrobe.save()

        with Form(cls.bom_wardrobe) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.drawer
                # because pim-odoo said '3 drawers because 4 is too much'
                line.product_qty = 3

        cls.chair = cls.env['product.product'].create({
            'name': 'Chair',
            'is_storable': True,
        })

        bom_form_chair = Form(cls.env['mrp.bom'])
        bom_form_chair.product_tmpl_id = cls.chair.product_tmpl_id
        bom_form_chair.product_qty = 1
        cls.bom_chair = bom_form_chair.save()

        with Form(cls.bom_chair) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = cls.table_leg
                line.product_qty = 4

        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.mps_table = cls.env['mrp.production.schedule'].create({
            'product_id': cls.table.id,
            'warehouse_id': cls.warehouse.id,
            'bom_id': cls.bom_table.id,
        })
        cls.mps_wardrobe = cls.env['mrp.production.schedule'].create({
            'product_id': cls.wardrobe.id,
            'warehouse_id': cls.warehouse.id,
            'bom_id': cls.bom_wardrobe.id,
        })
        cls.mps_chair = cls.env['mrp.production.schedule'].create({
            'product_id': cls.chair.id,
            'warehouse_id': cls.warehouse.id,
            'bom_id': cls.bom_chair.id,
        })
        cls.mps_drawer = cls.env['mrp.production.schedule'].create({
            'product_id': cls.drawer.id,
            'warehouse_id': cls.warehouse.id,
            'bom_id': cls.bom_drawer.id,
        })
        cls.mps_table_leg = cls.env['mrp.production.schedule'].create({
            'product_id': cls.table_leg.id,
            'warehouse_id': cls.warehouse.id,
            'bom_id': cls.bom_table_leg.id,
        })
        cls.mps_screw = cls.env['mrp.production.schedule'].search([
            ('product_id', '=', cls.screw.id)
        ])
        cls.mps_bolt = cls.env['mrp.production.schedule'].search([
            ('product_id', '=', cls.bolt.id)
        ])
        cls.mps = cls.mps_table | cls.mps_wardrobe | cls.mps_chair |\
            cls.mps_drawer | cls.mps_table_leg | cls.mps_screw | cls.mps_bolt

    def test_basic_state(self):
        """ Testing master product scheduling default values for client
        action rendering.
        """
        mps_state = self.mps.get_mps_view_state()
        self.assertTrue(len(mps_state['manufacturing_period']), 12)

        # Remove demo data
        production_schedule_ids = [s for s in mps_state['production_schedule_ids'] if s['id'] in self.mps.ids]
        # Check that 7 states are returned (one by production schedule)
        self.assertEqual(len(production_schedule_ids), 7)
        self.assertEqual(mps_state['company_id'], self.env.user.company_id.id)
        company_groups = mps_state['groups'][0]
        self.assertTrue(company_groups['mrp_mps_show_starting_inventory'])
        self.assertTrue(company_groups['mrp_mps_show_demand_forecast'])
        self.assertTrue(company_groups['mrp_mps_show_indirect_demand'])
        self.assertTrue(company_groups['mrp_mps_show_to_replenish'])
        self.assertTrue(company_groups['mrp_mps_show_safety_stock'])

        self.assertFalse(company_groups['mrp_mps_show_actual_demand'])
        self.assertFalse(company_groups['mrp_mps_show_actual_replenishment'])
        self.assertFalse(company_groups['mrp_mps_show_available_to_promise'])

        # Check that quantity on forecast are empty
        self.assertTrue(all([not forecast['starting_inventory_qty'] for forecast in production_schedule_ids[0]['forecast_ids']]))
        self.assertTrue(all([not forecast['forecast_qty'] for forecast in production_schedule_ids[0]['forecast_ids']]))
        self.assertTrue(all([not forecast['replenish_qty'] for forecast in production_schedule_ids[0]['forecast_ids']]))
        self.assertTrue(all([not forecast['safety_stock_qty'] for forecast in production_schedule_ids[0]['forecast_ids']]))
        self.assertTrue(all([not forecast['indirect_demand_qty'] for forecast in production_schedule_ids[0]['forecast_ids']]))
        # Check that there is 12 periods for each forecast
        self.assertTrue(all([len(production_schedule_id['forecast_ids']) == 12 for production_schedule_id in production_schedule_ids]))

    def test_forecast_1(self):
        """ Testing master product scheduling """
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': date.today(),
            'forecast_qty': 100
        })
        screw_mps_state = self.mps_screw.get_production_schedule_view_state()[0]
        forecast_at_first_period = screw_mps_state['forecast_ids'][0]
        self.assertEqual(forecast_at_first_period['forecast_qty'], 100)
        self.assertEqual(forecast_at_first_period['replenish_qty'], 100)
        self.assertEqual(forecast_at_first_period['safety_stock_qty'], 0)

        self.env['stock.quant']._update_available_quantity(self.mps_screw.product_id, self.warehouse.lot_stock_id, 50)
        # Invalidate qty_available on product.product
        self.env.invalidate_all()
        screw_mps_state = self.mps_screw.get_production_schedule_view_state()[0]
        forecast_at_first_period = screw_mps_state['forecast_ids'][0]
        self.assertEqual(forecast_at_first_period['forecast_qty'], 100)
        self.assertEqual(forecast_at_first_period['replenish_qty'], 50)
        self.assertEqual(forecast_at_first_period['safety_stock_qty'], 0)

        self.mps_screw.enable_max_replenish = True
        self.mps_screw.max_to_replenish_qty = 20
        screw_mps_state = self.mps_screw.get_production_schedule_view_state()[0]
        forecast_at_first_period = screw_mps_state['forecast_ids'][0]
        self.assertEqual(forecast_at_first_period['forecast_qty'], 100)
        self.assertEqual(forecast_at_first_period['replenish_qty'], 20)
        self.assertEqual(forecast_at_first_period['safety_stock_qty'], -30)
        forecast_at_second_period = screw_mps_state['forecast_ids'][1]
        self.assertEqual(forecast_at_second_period['forecast_qty'], 0)
        self.assertEqual(forecast_at_second_period['replenish_qty'], 20)
        self.assertEqual(forecast_at_second_period['safety_stock_qty'], -10)
        forecast_at_third_period = screw_mps_state['forecast_ids'][2]
        self.assertEqual(forecast_at_third_period['forecast_qty'], 0)
        self.assertEqual(forecast_at_third_period['replenish_qty'], 10)
        self.assertEqual(forecast_at_third_period['safety_stock_qty'], 0)

    def test_replenish(self):
        """ Test to run procurement for forecasts. Check that replenish for
        different periods will not merger purchase order line and create
        multiple docurements. Also modify the existing quantity replenished on
        a forecast and run the replenishment again, ensure the purchase order
        line is updated.
        """
        self.mps_screw.replenish_trigger = 'manual'
        forecast_screw = self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': self.mps_dates_month[0][0],
            'forecast_qty': 100
        })
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': self.mps_dates_month[1][0],
            'forecast_qty': 100
        })

        partner = self.env['res.partner'].create({
            'name': 'Jhon'
        })
        seller = self.env['product.supplierinfo'].create({
            'partner_id': partner.id,
            'price': 12.0,
            'delay': 0
        })
        self.screw.seller_ids = [(6, 0, [seller.id])]
        self.mps_screw.action_replenish()
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)])
        self.assertTrue(purchase_order_line)

        # It should not create a procurement since it exists already one for the
        # current period and the sum of lead time should be 0.
        self.mps_screw.action_replenish(based_on_lead_time=True)
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)])
        self.assertEqual(len(purchase_order_line), 1)

        self.mps_screw.action_replenish()
        purchase_order_lines = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)])
        self.assertEqual(len(purchase_order_lines), 2)
        self.assertEqual(len(purchase_order_lines.mapped('order_id')), 2)

        # This replenish should be withtout effect since everything is already
        # plannified.
        self.mps_screw.action_replenish()
        purchase_order_lines = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)])
        self.assertEqual(len(purchase_order_lines), 2)

        # Replenish an existing forecast with a procurement in progress
        forecast_screw.forecast_qty = 150
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(screw_forecast_1['state'], 'to_relaunch')
        self.assertTrue(screw_forecast_1['to_replenish'])
        self.assertTrue(screw_forecast_1['forced_replenish'])

        self.mps_screw.action_replenish(based_on_lead_time=True)
        purchase_order_lines = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)])
        self.assertEqual(len(purchase_order_lines), 2)
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)], order='date_planned', limit=1)
        self.assertEqual(purchase_order_line.product_qty, 150)

        forecast_screw.forecast_qty = 50
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(screw_forecast_1['state'], 'to_correct')
        self.assertFalse(screw_forecast_1['to_replenish'])
        self.assertFalse(screw_forecast_1['forced_replenish'])

    def test_lead_times(self):
        """ Manufacture, supplier and rules uses delay. The forecasts to
        replenish are impacted by those delay. Ensure that the MPS state and
        the period to replenish are correct.
        """
        self.env.company.manufacturing_period = 'week'
        partner = self.env['res.partner'].create({
            'name': 'Jhon'
        })
        seller = self.env['product.supplierinfo'].create({
            'partner_id': partner.id,
            'price': 12.0,
            'delay': 7,
        })
        self.screw.seller_ids = [(6, 0, [seller.id])]

        self.mps_screw.replenish_trigger = 'manual'
        mps_dates_week = self.env.company._get_date_range()
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': mps_dates_week[0][0],
            'forecast_qty': 100
        })

        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        screw_forecast_3 = mps_screw['forecast_ids'][2]

        # Check screw forecasts state
        self.assertEqual(screw_forecast_1['state'], 'to_launch')
        # launched because it's in lead time frame but it do not require a
        # replenishment. The state launched is used in order to render the cell
        # with a grey background.
        self.assertEqual(screw_forecast_2['state'], 'launched')
        self.assertEqual(screw_forecast_3['state'], 'to_launch')
        self.assertTrue(screw_forecast_1['to_replenish'])
        self.assertFalse(screw_forecast_2['to_replenish'])
        self.assertFalse(screw_forecast_3['to_replenish'])
        self.assertTrue(screw_forecast_1['forced_replenish'])
        self.assertFalse(screw_forecast_2['forced_replenish'])
        self.assertFalse(screw_forecast_3['forced_replenish'])

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': mps_dates_week[1][0],
            'forecast_qty': 100
        })

        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        screw_forecast_3 = mps_screw['forecast_ids'][2]
        self.assertEqual(screw_forecast_1['state'], 'to_launch')
        self.assertEqual(screw_forecast_2['state'], 'to_launch')
        self.assertEqual(screw_forecast_3['state'], 'to_launch')
        self.assertTrue(screw_forecast_1['to_replenish'])
        self.assertTrue(screw_forecast_2['to_replenish'])
        self.assertFalse(screw_forecast_3['to_replenish'])
        self.assertTrue(screw_forecast_1['forced_replenish'])
        self.assertFalse(screw_forecast_2['forced_replenish'])
        self.assertFalse(screw_forecast_3['forced_replenish'])
        seller.delay = 14
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        screw_forecast_3 = mps_screw['forecast_ids'][2]
        self.assertEqual(screw_forecast_1['state'], 'to_launch')
        self.assertEqual(screw_forecast_2['state'], 'to_launch')
        self.assertEqual(screw_forecast_3['state'], 'launched')
        self.assertTrue(screw_forecast_1['to_replenish'])
        self.assertTrue(screw_forecast_2['to_replenish'])
        self.assertFalse(screw_forecast_3['to_replenish'])
        self.assertTrue(screw_forecast_1['forced_replenish'])
        self.assertFalse(screw_forecast_2['forced_replenish'])
        self.assertFalse(screw_forecast_3['forced_replenish'])

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': mps_dates_week[2][0],
            'forecast_qty': 100
        })
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        screw_forecast_3 = mps_screw['forecast_ids'][2]
        self.assertEqual(screw_forecast_1['state'], 'to_launch')
        self.assertEqual(screw_forecast_2['state'], 'to_launch')
        self.assertEqual(screw_forecast_3['state'], 'to_launch')
        self.assertTrue(screw_forecast_1['to_replenish'])
        self.assertTrue(screw_forecast_2['to_replenish'])
        self.assertTrue(screw_forecast_3['to_replenish'])
        self.assertTrue(screw_forecast_1['forced_replenish'])
        self.assertFalse(screw_forecast_2['forced_replenish'])
        self.assertFalse(screw_forecast_3['forced_replenish'])

        self.mps_screw.action_replenish(based_on_lead_time=True)
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)])
        self.assertEqual(len(purchase_order_line.mapped('order_id')), 3)

        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        screw_forecast_3 = mps_screw['forecast_ids'][2]
        self.assertEqual(screw_forecast_1['state'], 'launched')
        self.assertEqual(screw_forecast_2['state'], 'launched')
        self.assertEqual(screw_forecast_3['state'], 'launched')
        self.assertFalse(screw_forecast_1['to_replenish'])
        self.assertFalse(screw_forecast_2['to_replenish'])
        self.assertFalse(screw_forecast_3['to_replenish'])
        self.assertFalse(screw_forecast_1['forced_replenish'])
        self.assertFalse(screw_forecast_2['forced_replenish'])
        self.assertFalse(screw_forecast_3['forced_replenish'])

    def test_lead_times_2(self):
        """ In the case of a multilevel bom with each their own lead time, we want
        to make sure that indirect demand forecast is made at the correct time.

        E.g.:
        - table bom has a lead time of 10 day
        - drawer bom has a lead time of 15 day
        - table leg bom has a lead time of 10 day

        if a forecast demand of 1 table is made for June, the indirect demand for all components will be:
        - 1 drawer for May: 1st of June minus lead time of 10 days
        - 4 table legs for May: 2 from table bom (June 1st - 10 days) and 2 from table>drawer boms (June 1st - 10+15 days)
        - 12 screws for May: 4 from table>drawer (June 1st - 10+15 days)
            and 8 from table>table leg (June 1st - 10+10 days)
        - 8 screws for April: table>drawer>table leg (June 1st - 10+15+10 days)
        - 8 bolts for May: table>table leg (June 1st - 10+10 days)
        - 8 bolts for April: table>drawer>table leg (June 1st - 10+15+10 days)
        """
        self.env.company.manufacturing_period = 'month'
        self.table.write({
            'route_ids': [(6, 0, [self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.drawer.write({
            'route_ids': [(6, 0, [self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.table_leg.write({
            'route_ids': [(6, 0, [self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.bom_table.produce_delay = 10
        self.bom_drawer.produce_delay = 15
        self.bom_table_leg.produce_delay = 10

        # Create a forecast demand of 1 for table 4 months from now, on the 1st
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_table.id,
            'date': self.mps_dates_month[3][0],
            'forecast_qty': 1
        })
        drawer_forecasts = self.mps_drawer.get_production_schedule_view_state()[0]['forecast_ids']
        self.assertEqual(drawer_forecasts[2]['indirect_demand_qty'], 1)
        table_leg_forecasts = self.mps_table_leg.get_production_schedule_view_state()[0]['forecast_ids']
        self.assertEqual(table_leg_forecasts[2]['indirect_demand_qty'], 4)
        screw_forecasts = self.mps_screw.get_production_schedule_view_state()[0]['forecast_ids']
        self.assertEqual(screw_forecasts[2]['indirect_demand_qty'], 12)
        self.assertEqual(screw_forecasts[1]['indirect_demand_qty'], 8)
        bolt_forecasts = self.mps_bolt.get_production_schedule_view_state()[0]['forecast_ids']
        self.assertEqual(bolt_forecasts[2]['indirect_demand_qty'], 8)
        self.assertEqual(bolt_forecasts[1]['indirect_demand_qty'], 8)

    @freeze_time('2024-10-01')
    def test_lead_times_3(self):
        """ When showing a bigger period type (e.g. year > week), we want to make sure
        that lead times are applied on the day of the forecast and not the first day
        of the period. """
        self.env.company.manufacturing_period = 'month'
        self.table.write({
            'route_ids': [Command.set([self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.bom_table.produce_delay = 1
        self.mps_table.set_forecast_qty(1, 10)
        self.mps_table.set_forecast_qty(2, 10)
        self.mps_table.set_forecast_qty(3, 10)
        self.mps_table.set_forecast_qty(4, 10)

        mps_table, mps_drawer = (self.mps_table | self.mps_drawer).get_production_schedule_view_state(period_scale='year')
        self.assertListEqual([f['forecast_qty'] for f in mps_table['forecast_ids']], [20, 20, 0])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_drawer['forecast_ids']], [30, 10, 0])

    def test_lead_times_4(self):
        """ If the top product has a lead time and a max replenish, ensure that the
        indirect demand of the component is correctly distributed across multiple
        period if applicable."""
        self.env.company.manufacturing_period = 'month'
        self.table.write({
            'route_ids': [Command.set([self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.bom_table.produce_delay = 1
        self.mps_table.write({'max_to_replenish_qty': 10, 'enable_max_replenish': True})
        self.mps_table.set_forecast_qty(1, 40)
        mps_drawer = self.mps_drawer.get_production_schedule_view_state()[0]
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_drawer['forecast_ids'][:5]],[10, 10, 10, 10, 0])

    def test_lead_times_with_multi_lvl_bom(self):
        """ Using the configuration from setup BOM 1 with:
           - the table has lead time
           - the table leg has lead time and a safety stock target
        ensure that the indirect demand of the component is correctly distributed across multiple
        period when creating a table for week 3.
        Material needed for producing the table in week 3:
          - Table leg:
            - week 2: 4
          - Screws:
            - week 2: 20
        For the Safety stock of the table leg:
          - Screws:
            - week 0: 40
        """
        self.env.company.manufacturing_period = 'week'
        self.table.write({
            'route_ids': [Command.set([self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.bom_table.produce_delay = 1
        self.bom_table_leg.produce_delay = 1
        self.mps_table_leg.write({'forecast_target_qty': 10})
        self.mps_table.set_forecast_qty(3, 1)
        mps_table = self.mps_table.get_production_schedule_view_state()[0]
        mps_table_leg = self.mps_table_leg.get_production_schedule_view_state()[0]
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]

        self.assertListEqual([f['indirect_demand_qty'] for f in mps_table['forecast_ids'][:4]], [0, 0, 0, 0])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_table_leg['forecast_ids'][:4]], [0, 0, 4, 0])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_screw['forecast_ids'][:4]], [40, 0, 20, 0])

        self.assertListEqual([f['starting_inventory_qty'] for f in mps_table['forecast_ids'][:4]], [0, 0, 0, 0])
        self.assertListEqual([f['starting_inventory_qty'] for f in mps_table_leg['forecast_ids'][:4]], [0, 10, 10, 10])
        self.assertListEqual([f['starting_inventory_qty'] for f in mps_screw['forecast_ids'][:4]], [0, 0, 0, 0])

        self.assertListEqual([f['replenish_qty'] for f in mps_table['forecast_ids'][:4]], [0, 0, 0, 1])
        self.assertListEqual([f['replenish_qty'] for f in mps_table_leg['forecast_ids'][:4]], [10, 0, 4, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_screw['forecast_ids'][:4]], [40, 0, 20, 0])

    def test_long_lead_times_with_multi_lvl_bom(self):
        """ Using the configuration from setup BOM 1 with:
           - the table has a long lead time.
           - the drawers has a long lead time.
           - the table leg has a lead time and a safety stock target.
        ensure that the indirect demand of the component is correctly distributed across multiple
        period when creating a table for week 6 and a drawer in week 5.
        Material needed for producing the table in week 6:
          - Drawers:
            - week 2: 1
          - Table leg:
            - week 2: 2
            - week 1: 2
          - Screws:
            - week 2: 8
            - week 1: 12
        For producing the drawer in week 5:
          - Table leg:
            - week 3: 2
          - Screws:
            - week 3: 12
        For the Safety stock of the table leg:
          - Screws:
            - week 0: 40
        """
        self.env.company.manufacturing_period = 'week'
        self.table.write({
            'route_ids': [Command.set([self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.bom_table.produce_delay = 22
        self.bom_drawer.produce_delay = 8
        self.bom_table_leg.produce_delay = 1
        self.mps_table_leg.write({'forecast_target_qty': 10})
        self.mps_table.set_forecast_qty(6, 1)
        self.mps_drawer.set_forecast_qty(5, 1)
        mps_table = self.mps_table.get_production_schedule_view_state()[0]
        mps_drawer = self.mps_drawer.get_production_schedule_view_state()[0]
        mps_table_leg = self.mps_table_leg.get_production_schedule_view_state()[0]
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]

        self.assertListEqual([f['indirect_demand_qty'] for f in mps_table['forecast_ids'][:8]], [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_drawer['forecast_ids'][:8]], [0, 0, 1, 0, 0, 0, 0, 0])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_table_leg['forecast_ids'][:8]], [0, 2, 2, 2, 0, 0, 0, 0])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_screw['forecast_ids'][:8]], [40, 12, 8, 12, 0, 0, 0, 0])

        self.assertListEqual([f['starting_inventory_qty'] for f in mps_table['forecast_ids'][:8]], [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertListEqual([f['starting_inventory_qty'] for f in mps_drawer['forecast_ids'][:8]], [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertListEqual([f['starting_inventory_qty'] for f in mps_table_leg['forecast_ids'][:8]], [0, 10, 10, 10, 10, 10, 10, 10])
        self.assertListEqual([f['starting_inventory_qty'] for f in mps_screw['forecast_ids'][:8]], [0, 0, 0, 0, 0, 0, 0, 0])

        self.assertListEqual([f['replenish_qty'] for f in mps_table['forecast_ids'][:8]], [0, 0, 0, 0, 0, 0, 1, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_drawer['forecast_ids'][:8]], [0, 0, 1, 0, 0, 1, 0, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_table_leg['forecast_ids'][:8]], [10, 2, 2, 2, 0, 0, 0, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_screw['forecast_ids'][:8]], [40, 12, 8, 12, 0, 0, 0, 0])

    def test_indirect_demand(self):
        """ On a multiple BoM relation, ensure that the replenish quantity on
        a production schedule impact the indirect demand on other production
        that have a component as product.
        """

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_table.id,
            'date': self.mps_dates_month[0][0],
            'forecast_qty': 2
        })

        # 2 drawer from table
        mps_drawer = self.mps_drawer.get_production_schedule_view_state()[0]
        drawer_forecast_1 = mps_drawer['forecast_ids'][0]
        self.assertEqual(drawer_forecast_1['indirect_demand_qty'], 2)
        # Screw for 2 tables:
        # 2 * 2 legs * 4 screw = 16
        # 1 drawer = 4 + 2 * legs * 4 = 12
        # 16 + 2 drawers = 16 + 24 = 40
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(screw_forecast_1['indirect_demand_qty'], 40)

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_wardrobe.id,
            'date': self.mps_dates_month[0][0],
            'forecast_qty': 3
        })

        # 2 drawer from table + 9 from wardrobe (3 x 3)
        mps_drawer, mps_screw = (self.mps_drawer | self.mps_screw).get_production_schedule_view_state()
        drawer_forecast_1 = mps_drawer['forecast_ids'][0]
        self.assertEqual(drawer_forecast_1['indirect_demand_qty'], 11)
        # Screw for 2 tables + 3 wardrobe:
        # 11 drawer = 11 * 12 = 132
        # + 2 * 2 legs * 4 = 16
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(screw_forecast_1['indirect_demand_qty'], 148)

        # Ensure that a forecast on another period will not impact the forecast
        # for current period.
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_table.id,
            'date': self.mps_dates_month[1][0],
            'forecast_qty': 2
        })
        mps_drawer, mps_screw = (self.mps_drawer | self.mps_screw).get_production_schedule_view_state()
        drawer_forecast_1 = mps_drawer['forecast_ids'][0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(drawer_forecast_1['indirect_demand_qty'], 11)
        self.assertEqual(screw_forecast_1['indirect_demand_qty'], 148)
        self.assertEqual(screw_forecast_2['indirect_demand_qty'], 40)

        # Ensure that a forecast on an intermediate schedule will correctly be added.
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_table_leg.id,
            'date': self.mps_dates_month[1][0],
            'forecast_qty': 4
        })
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(screw_forecast_2['indirect_demand_qty'], 56)

        # Ensure that a manual replenish on an intermediate schedule will correctly
        # move the difference to the next period
        self.mps_table_leg.set_replenish_qty(date_index=1, quantity=3)
        mps_screw = self.mps_screw.get_production_schedule_view_state()[0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        screw_forecast_3 = mps_screw['forecast_ids'][2]
        self.assertEqual(screw_forecast_2['indirect_demand_qty'], 20)
        self.assertEqual(screw_forecast_3['indirect_demand_qty'], 36)

    def test_indirect_demand_kit(self):
        """ On changing demand of a product whose BOM contains kit with a
        component, ensure that the replenish quantity on a production schedule
        impacts the indirect demand of kit's component.
        """
        cabinet = self.env['product.product'].create({
            'name': 'Cabinet',
            'is_storable': True,
        })
        wood_kit = self.env['product.product'].create({
            'name': 'Wood Kit',
            'is_storable': True,
        })
        wood = self.env['product.product'].create({
            'name': 'Wood',
            'is_storable': True,
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': cabinet.product_tmpl_id.id,
            'product_qty': 1,
            'bom_line_ids': [
                Command.create({'product_id': wood_kit.id, 'product_qty': 1}),
            ],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': wood_kit.product_tmpl_id.id,
            'product_qty': 1,
            'bom_line_ids': [
                Command.create({'product_id': wood.id, 'product_qty': 2}),
            ],
        })

        mps_cabinet = self.env['mrp.production.schedule'].create({
            'product_id': cabinet.id,
            'warehouse_id': self.warehouse.id,
        })

        mps_wood = self.env['mrp.production.schedule'].create({
            'product_id': wood.id,
            'warehouse_id': self.warehouse.id,
        })

        self.mps |= mps_cabinet | mps_wood

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': mps_cabinet.id,
            'date': self.mps_dates_month[0][0],
            'forecast_qty': 2
        })

        # 4 wood from cabinet
        mps_wood = mps_wood.get_production_schedule_view_state()[0]
        wood_forecast_1 = mps_wood['forecast_ids'][0]
        self.assertEqual(wood_forecast_1['indirect_demand_qty'], 4)

    def test_delivery_quantity_kit(self):
        """On ordering a kit product containing a component ressuplied from another warehouse,
        ensure the correct amount of component are ordered.
        """
        second_warehouse = self.env['stock.warehouse'].create({
            'name': 'Second Warehouse',
            'code': 'WH2',
            'resupply_wh_ids': [Command.link(self.warehouse.id)],
        })

        resupply_route = self.env['stock.route'].search([('supplier_wh_id', '=', self.warehouse.id), ('supplied_wh_id', '=', second_warehouse.id)], limit=1)
        self.drawer.route_ids = [Command.set(resupply_route.ids)]

        self.env['mrp.bom'].create({
            'product_tmpl_id': self.wardrobe.product_tmpl_id.id,
            'type': 'phantom',
            'product_qty': 2,
            'bom_line_ids': [
                Command.create({'product_id': self.drawer.id, 'product_qty': 6}),
            ],
        })

        mps_wardrobe = self.env['mrp.production.schedule'].create({
            'product_id': self.wardrobe.id,
            'warehouse_id': second_warehouse.id,
            'route_id': resupply_route.id,
        })

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': mps_wardrobe.id,
            'date': self.mps_dates_month[0][0],
            'forecast_qty': 4,
        })

        mps_wardrobe.action_replenish()
        self.assertEqual(self.env['stock.move'].search([('product_id', '=', self.drawer.id)], limit=1).product_qty, 12)

    def test_impacted_schedule(self):
        impacted_schedules = self.mps_screw.get_impacted_schedule()
        self.assertEqual(sorted(impacted_schedules), sorted((self.mps - (self.mps_screw | self.mps_bolt)).ids))

        impacted_schedules = self.mps_drawer.get_impacted_schedule()
        self.assertEqual(sorted(impacted_schedules), sorted((self.mps_table |
            self.mps_wardrobe | self.mps_table_leg | self.mps_screw | self.mps_bolt).ids))

    def test_3_steps(self):
        self.warehouse.manufacture_steps = 'pbm_sam'
        self.table_leg.write({
            'route_ids': [(6, 0, [self.ref('mrp.route_warehouse0_manufacture')])]
        })
        self.mps_table_leg.replenish_trigger = 'manual'

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_table_leg.id,
            'date': date.today(),
            'forecast_qty': 25
        })

        self.mps_table_leg.action_replenish()
        mps_table_leg = self.mps_table_leg.get_production_schedule_view_state()[0]
        self.assertEqual(mps_table_leg['forecast_ids'][0]['forecast_qty'], 25.0, "Wrong resulting value of to_supply")
        self.assertEqual(mps_table_leg['forecast_ids'][0]['incoming_qty'], 25.0, "Wrong resulting value of incoming quantity")

    def test_interwh_delay(self):
        """
        Suppose an interwarehouse configuration. The user adds some delays on
        each rule of the interwh route. Then, the user defines a replenishment
        qty on the MPS view and calls the replenishment action. This test
        ensures that the MPS view includes the delays for the incoming quantity
        """
        main_warehouse = self.warehouse
        second_warehouse = self.env['stock.warehouse'].create({
            'name': 'Second Warehouse',
            'code': 'WH02',
        })
        main_warehouse.write({
            'resupply_wh_ids': [(6, 0, second_warehouse.ids)]
        })

        interwh_route = self.env['stock.route'].search([('supplied_wh_id', '=', main_warehouse.id), ('supplier_wh_id', '=', second_warehouse.id)])
        interwh_route.rule_ids.delay = 1

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
            'route_ids': [(6, 0, interwh_route.ids)],
        })

        mps = self.env['mrp.production.schedule'].create({
            'product_id': product.id,
            'warehouse_id': main_warehouse.id,
        })
        interval_index = 3
        mps.set_replenish_qty(interval_index, 1)
        mps.action_replenish()

        state = mps.get_production_schedule_view_state()[0]
        for index, forecast in enumerate(state['forecast_ids']):
            self.assertEqual(forecast['incoming_qty'], 1 if index == interval_index else 0, 'Incoming qty is incorrect for index %s' % index)

    def test_outgoing_sm_and_lead_time_out_of_date_range(self):
        """
        Set a lead time on delivery rule. Then generate an outgoing SM based on
        that rule with:
        - its date in dates range of MPS
        - its date + rule's lead time outside the dates range of MPS
        As a result, for the product mps, each outgoing quantity should be zero
        """
        self.env.company.manufacturing_period = 'day'
        self.env.company.manufacturing_period_to_display_day = 10

        customer_location = self.env.ref('stock.stock_location_customers')
        stock_location = self.warehouse.lot_stock_id

        delivery_rule = self.env['stock.rule'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('location_src_id', '=', stock_location.id),
            ('location_dest_id', '=', customer_location.id),
            ('action', '=', 'pull')
        ], limit=1)
        delivery_rule.delay = 15

        product = self.env['product.product'].create({'name': 'SuperProduct', 'is_storable': True})
        procurement = self.env["procurement.group"].Procurement(
            product, 1, product.uom_id,
            customer_location,
            product.name,
            "/",
            self.env.company,
            {
                "warehouse_id": self.warehouse,
                "date_planned": date.today() + timedelta(days=16),
            }
        )
        self.env["procurement.group"].run([procurement])

        tomorrow = start_of(datetime.now() + timedelta(days=1), 'day')
        move = self.env['stock.move'].search([('product_id', '=', product.id)], limit=1)
        self.assertEqual(move.date, tomorrow)

        mps = self.env['mrp.production.schedule'].create({
            'product_id': product.id,
            'warehouse_id': self.warehouse.id,
        })
        state = mps.get_production_schedule_view_state()[0]
        self.assertTrue(all(forecast['outgoing_qty'] == 0 for forecast in state['forecast_ids']))

    def test_product_variants_in_mps(self):
        """
        Test that only the impacted  components are updated when the forecast demand of a product is changed.
        """
        # create the attribute size with two values ('M', 'L')
        size_attribute = self.env['product.attribute'].create({'name': 'Size', 'sequence': 4})
        self.env['product.attribute.value'].create([{
            'name': name,
            'attribute_id': size_attribute.id,
            'sequence': 1,
        } for name in ('M', 'L')])
        product, c1, c2 = self.env['product.product'].create([{
            'name': i,
            'is_storable': True,
        } for i in range(3)])
        product_template = product.product_tmpl_id
        size_attribute_line = self.env['product.template.attribute.line'].create([{
                'product_tmpl_id': product_template.id,
                 'attribute_id': size_attribute.id,
                 'value_ids': [(6, 0, size_attribute.value_ids.ids)]
            }])
        # Check that two product variant are created
        self.assertEqual(product_template.product_variant_count, 2)
        # Create a BoM with two components ('c1 applied only in m'  and 'c2 applied only in L')
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_uom_id': product_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': c1.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [(4, size_attribute_line.product_template_value_ids[0].id)]}), # M size
                Command.create({
                    'product_id': c2.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [(4, size_attribute_line.product_template_value_ids[1].id)]}), # L size
            ]
        })

        mps_p_m, mps_p_l, mps_c1, mps_c2 = self.env['mrp.production.schedule'].create([{
            'product_id': product,
            'warehouse_id': self.warehouse.id,
        } for product in (product_template.product_variant_ids[0] | product_template.product_variant_ids[1] | c1 | c2).ids])

        # check the mps of the product variant M
        mps_impacted = mps_p_m[0].get_impacted_schedule()
        self.assertEqual(len(mps_impacted), 1)
        self.assertEqual(mps_impacted[0], mps_c1.id)
        # check the mps of the product variant L
        mps_impacted = mps_p_l[0].get_impacted_schedule()
        self.assertEqual(len(mps_impacted), 1)
        self.assertEqual(mps_impacted[0], mps_c2.id)

    def test_replenish_trigger(self):
        """Test that the replenish_trigger of components is 'never'
        and that 'automated' correctly triggers in the cron.
        """
        mps_components = self.mps_drawer + self.mps_table_leg + self.mps_screw + self.mps_bolt
        self.assertTrue(all(record.replenish_trigger == 'never' for record in mps_components))

        partner = self.env['res.partner'].create({'name': 'Bob Palindrome MacScam'})
        seller = self.env['product.supplierinfo'].create({
            'partner_id': partner.id,
            'price': 2,
            'delay': 3
        })
        self.screw.seller_ids = [(6, 0, [seller.id])]
        self.mps_screw.write({
            'replenish_trigger': 'automated',
            'supplier_id': seller.id
        })

        self.env.company.manufacturing_period = 'month'
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_table.id,
            'date': datetime.today(),
            'forecast_qty': 1
        })

        self.env['mrp.production.schedule'].action_cron_replenish()
        purchase_order_line = self.env['purchase.order.line'].search([('product_id', '=', self.screw.id)])
        self.assertTrue(purchase_order_line)
        self.assertEqual(purchase_order_line.date_planned.date(), self.mps_dates_month[0][0])
        self.assertEqual(purchase_order_line.date_order.date(), self.mps_dates_month[0][0] - timedelta(days=3))
        self.assertEqual(purchase_order_line.product_qty, 20)
        self.assertEqual(purchase_order_line.price_subtotal, 40)

    def test_set_forecast_qty(self):
        """ Test that adding/removing quantities from the MPS
        when manufacturing_period is 'month' or 'week'.
        """
        self.env.company.manufacturing_period = 'month'
        for delta in (3, 6, 12, 21):
            self.env['mrp.product.forecast'].create({
                'production_schedule_id': self.mps_table.id,
                'date': self.mps_dates_month[1][0] + timedelta(days=delta),
                'forecast_qty': delta
            })

        forecast_records = self.env['mrp.product.forecast'].search([('production_schedule_id', '=', self.mps_table.id)])
        self.assertEqual(len(forecast_records), 4)
        self.assertEqual(sum(forecast_records.mapped('forecast_qty')), 42, 'This is not the Answer to Life, the Universe, and Everything.')

        self.mps_table.set_forecast_qty(1, 64)
        forecast_records = self.env['mrp.product.forecast'].search([('production_schedule_id', '=', self.mps_table.id)])
        self.assertEqual(len(forecast_records), 5)
        self.assertEqual(forecast_records.mapped('forecast_qty'), [22, 3, 6, 12, 21])
        self.assertEqual(forecast_records[0].date, self.mps_dates_month[1][0])

        self.mps_table.set_forecast_qty(1, 84)
        self.assertEqual(forecast_records.mapped('forecast_qty'), [42, 3, 6, 12, 21])

        self.mps_table.set_forecast_qty(1, 72)
        self.assertEqual(forecast_records.mapped('forecast_qty'), [42, 3, 6, 12, 9])

        self.mps_table.set_forecast_qty(1, 50)
        self.assertEqual(forecast_records.mapped('forecast_qty'), [42, 3, 5, 0, 0])

        self.mps_table.set_forecast_qty(1, 21)
        self.assertEqual(forecast_records.mapped('forecast_qty'), [21, 0, 0, 0, 0])

        self.mps_table.set_forecast_qty(1, -13)
        self.assertEqual(forecast_records.mapped('forecast_qty'), [-13, 0, 0, 0, 0])

    def test_mps_sequence(self):
        """ Test that products added automatically have a higher sequence than their parent. """
        self.assertEqual(self.mps_table.mps_sequence, 10)
        self.assertEqual(self.mps_chair.mps_sequence, 10)
        self.assertEqual(self.mps_wardrobe.mps_sequence, 10)
        self.assertEqual(self.mps_table_leg.mps_sequence, 11)
        self.assertEqual(self.mps_drawer.mps_sequence, 11)
        self.assertEqual(self.mps_screw.mps_sequence, 12)
        self.assertEqual(self.mps_bolt.mps_sequence, 12)

    def test_mps_sequence_2(self):
        shelf = self.env['product.product'].create({
            'name': 'shelf',
            'is_storable': True,
        })
        plank = self.env['product.product'].create({
            'name': 'plank',
            'is_storable': True,
        })
        wood = self.env['product.product'].create({
            'name': 'wood',
            'is_storable': True,
        })
        bom_shelf = self.env['mrp.bom'].create({
            'product_id': shelf.id,
            'product_tmpl_id': shelf.product_tmpl_id.id,
            'product_uom_id': shelf.uom_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': plank.id, 'product_qty': 2}),
                Command.create({'product_id': self.screw.id, 'product_qty': 3}),
            ],
        })
        bom_plank = self.env['mrp.bom'].create({
            'product_id': plank.id,
            'product_tmpl_id': plank.product_tmpl_id.id,
            'product_uom_id': plank.uom_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': wood.id, 'product_qty': 2}),
            ],
        })
        mps_wood = self.env['mrp.production.schedule'].create({
            'product_id': wood.id,
            'warehouse_id': self.warehouse.id,
        })
        self.assertEqual(mps_wood.mps_sequence, 10)
        mps_shelf = self.env['mrp.production.schedule'].create({
            'product_id': shelf.id,
            'warehouse_id': self.warehouse.id,
            'bom_id': bom_shelf.id
        })
        self.assertEqual(mps_shelf.mps_sequence, 10)
        self.assertEqual(self.mps_screw.mps_sequence, 11)
        self.assertEqual(mps_wood.mps_sequence, 12)

        mps_plank = self.env['mrp.production.schedule'].create({
            'product_id': plank.id,
            'warehouse_id': self.warehouse.id,
            'bom_id': bom_plank.id
        })
        self.assertEqual(mps_plank.mps_sequence, 11)
        self.assertEqual(mps_wood.mps_sequence, 12)

    def test_is_indirect(self):
        """ Test that products added automatically are flagged as indirect demand products. """
        mps_components = self.mps_drawer + self.mps_table_leg + self.mps_screw + self.mps_bolt
        self.assertTrue(all(record.is_indirect for record in mps_components))

    def test_no_route_product_in_mps(self):
        """ Test that adding a product with no route enabled does not trigger an error. """
        self.mps_table.unlink()
        self.table.route_ids = [Command.clear()]
        self.assertEqual(len(self.table.route_ids), 0)

        mps_table_2 = self.env['mrp.production.schedule'].create({
            'product_id': self.table.id,
            'warehouse_id': self.warehouse.id,
            'bom_id': self.bom_table.id,
        })
        self.assertFalse(mps_table_2.route_id)

    @freeze_time('2024-01-01')
    def test_periods_display(self):
        """ Test that each period type (year, month, week, day) returns the correct
        number of columns with the correct column title. """
        self.env.company.manufacturing_period_to_display_year = 5
        self.env.company.manufacturing_period_to_display_month = 15
        self.env.company.manufacturing_period_to_display_week = 7
        self.env.company.manufacturing_period_to_display_day = 21

        mps_state_default = self.mps.get_mps_view_state()
        self.assertEqual(mps_state_default['manufacturing_period'], 'month')
        self.assertEqual(len(mps_state_default['dates']), self.env.company.manufacturing_period_to_display_month)
        self.assertListEqual(mps_state_default['dates'][9:], ['Oct 2024', 'Nov 2024', 'Dec 2024', 'Jan 2025', 'Feb 2025', 'Mar 2025'])

        mps_state_year = self.mps.get_mps_view_state(period_scale='year')
        self.assertEqual(mps_state_year['manufacturing_period'], 'year')
        self.assertEqual(len(mps_state_year['dates']), self.env.company.manufacturing_period_to_display_year)
        self.assertListEqual(mps_state_year['dates'], ['2024', '2025', '2026', '2027', '2028'])

        mps_state_week = self.mps.get_mps_view_state(period_scale='week')
        self.assertEqual(len(mps_state_week['dates']), self.env.company.manufacturing_period_to_display_week)
        self.assertEqual(mps_state_week['dates'][2:5], ['Week 3 (15-21/Jan)', 'Week 4 (22-28/Jan)', 'Week 5 (29-4/Feb)'])

        mps_state_day = self.mps.get_mps_view_state(period_scale='day')
        self.assertEqual(len(mps_state_day['dates']), self.env.company.manufacturing_period_to_display_day)
        self.assertEqual(mps_state_day['dates'][7:12], ['Jan 8', 'Jan 9', 'Jan 10', 'Jan 11', 'Jan 12'])

    def test_outgoing_move_with_different_uom(self):
        """
        Test that the outgoing and incoming quantities are computed in the product's UoM.
        """
        product_a = self.env['product.product'].create({
            'name': 'product a test',
            'is_storable': True,
        })
        mps = self.env['mrp.production.schedule'].create({
            'product_id': product_a.id,
            'warehouse_id': self.warehouse.id,
        })
        outgoing_move = self.env['stock.move'].create({
            'name': product_a.name,
            'product_id': product_a.id,
            'product_uom_qty': 1,
            'product_uom': self.env.ref('uom.product_uom_dozen').id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        incoming_move = self.env['stock.move'].create({
            'name': product_a.name,
            'product_id': product_a.id,
            'product_uom_qty': 1,
            'product_uom': self.env.ref('uom.product_uom_dozen').id,
            'location_id': self.env.ref('stock.stock_location_customers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        (outgoing_move | incoming_move)._action_confirm()
        state = mps.get_production_schedule_view_state()[0]
        outgoing_qty = state['forecast_ids'][0]['outgoing_qty']
        incoming_qty = state['forecast_ids'][0]['incoming_qty']
        self.assertEqual(outgoing_qty, 12, 'outgoing qty is incorrect')
        self.assertEqual(incoming_qty, 12, 'outgoing qty is incorrect')

    def test_forecast_target_qty(self):
        """ Test that adding a safety stock target does not break indirect demand computation. """
        # Base case, set the safety stock target for the schedule of a final product
        self.mps_table.forecast_target_qty = 3
        mps_table, mps_table_leg, mps_screw = (self.mps_table | self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        table_forecast_10 = mps_table['forecast_ids'][9]
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(leg_forecast_1['replenish_qty'], 12)
        self.assertEqual(screw_forecast_1['replenish_qty'], 60)
        self.assertEqual(table_forecast_10['starting_inventory_qty'], 3)

        # Manually set the replenish qty of that same schedule
        self.mps_table.set_replenish_qty(date_index=0, quantity=1)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        leg_forecast_2 = mps_table_leg['forecast_ids'][1]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(leg_forecast_1['replenish_qty'], 4)
        self.assertEqual(screw_forecast_1['replenish_qty'], 20)
        self.assertEqual(leg_forecast_2['replenish_qty'], 8)
        self.assertEqual(screw_forecast_2['replenish_qty'], 40)

        # Set the forecasted demand of that same intermediate component
        self.mps_table_leg.set_forecast_qty(date_index=0, quantity=1)
        mps_bolt, mps_screw = (self.mps_bolt | self.mps_screw).get_production_schedule_view_state()
        bolt_forecast_1 = mps_bolt['forecast_ids'][0]
        bolt_forecast_2 = mps_bolt['forecast_ids'][1]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(bolt_forecast_1['replenish_qty'], 20)
        self.assertEqual(bolt_forecast_2['replenish_qty'], 32)
        self.assertEqual(screw_forecast_1['replenish_qty'], 24)

        # Manually set the replenish qty of that same intermediate component
        self.mps_table_leg.set_replenish_qty(date_index=0, quantity=6)
        mps_table_leg, mps_bolt = (self.mps_table_leg | self.mps_bolt).get_production_schedule_view_state()
        leg_forecast_2 = mps_table_leg['forecast_ids'][1]
        bolt_forecast_2 = mps_bolt['forecast_ids'][1]
        self.assertEqual(leg_forecast_2['replenish_qty'], 7)
        self.assertEqual(bolt_forecast_2['replenish_qty'], 28)

        # Set the safety stock target of an intermediate component that needs the previous component
        self.mps_drawer.forecast_target_qty = 5
        mps_drawer, mps_table_leg, mps_screw = (self.mps_drawer | self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        drawer_forecast_1 = mps_drawer['forecast_ids'][0]
        drawer_forecast_9 = mps_drawer['forecast_ids'][8]
        leg_forecast_2 = mps_table_leg['forecast_ids'][1]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(drawer_forecast_1['replenish_qty'], 6)
        self.assertEqual(drawer_forecast_9['starting_inventory_qty'], 5)
        self.assertEqual(leg_forecast_2['replenish_qty'], 17)
        self.assertEqual(screw_forecast_1['replenish_qty'], 48)
        self.assertEqual(screw_forecast_2['replenish_qty'], 76)

    def test_min_max_to_replenish_qty(self):
        """ Test that setting a minimum and/or maximum qty to replenish like a logical person computes correctly.
        Meaning that the min to replenish is inferior to the max to replenish. """
        self.mps_table_leg.write({'min_to_replenish_qty': 5, 'max_to_replenish_qty': 10, 'enable_max_replenish': True})

        # Replenish qty is inferior to min_to_replenish_qty
        self.mps_table.set_forecast_qty(date_index=0, quantity=1)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 4)
        self.assertEqual(leg_forecast_1['replenish_qty'], 5)
        self.assertEqual(screw_forecast_1['replenish_qty'], 24)

        # Replenish qty is between min_to_replenish_qty and max_to_replenish_qty
        self.mps_table.set_forecast_qty(date_index=0, quantity=2)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 8)
        self.assertEqual(leg_forecast_1['replenish_qty'], 8)
        self.assertEqual(screw_forecast_1['replenish_qty'], 40)

        # Replenish qty is superior to max_to_replenish_qty
        self.mps_table.set_forecast_qty(date_index=0, quantity=3)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        leg_forecast_2 = mps_table_leg['forecast_ids'][1]
        leg_forecast_11 = mps_table_leg['forecast_ids'][10]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 12)
        self.assertEqual(leg_forecast_1['replenish_qty'], 10)
        self.assertEqual(leg_forecast_2['starting_inventory_qty'], -2)
        self.assertEqual(leg_forecast_2['replenish_qty'], 5)
        self.assertEqual(leg_forecast_11['starting_inventory_qty'], 3)
        self.assertEqual(screw_forecast_1['replenish_qty'], 52)
        self.assertEqual(screw_forecast_2['replenish_qty'], 20)

        # Set the min_to_replenish_qty of a product above in the bom hierarchy
        self.mps_drawer.min_to_replenish_qty = 4
        mps_drawer, mps_table_leg, mps_screw = (self.mps_drawer | self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        drawer_forecast_8 = mps_drawer['forecast_ids'][9]
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        leg_forecast_11 = mps_table_leg['forecast_ids'][10]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(drawer_forecast_8['starting_inventory_qty'], 1)
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 14)
        self.assertEqual(leg_forecast_11['starting_inventory_qty'], 1)
        self.assertEqual(screw_forecast_1['replenish_qty'], 56)

    def test_min_max_to_replenish_qty_2(self):
        """ Test that setting a minimum and/or maximum qty to replenish like a crazy person computes correctly.
        Meaning that the min to replenish is superior to the max to replenish. """
        self.mps_table_leg.write({'min_to_replenish_qty': 10, 'max_to_replenish_qty': 5, 'enable_max_replenish': True})

        # Replenish qty is inferior to max_to_replenish_qty => apply min_to_replenish_qty
        self.mps_table.set_forecast_qty(date_index=0, quantity=1)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        leg_forecast_6 = mps_table_leg['forecast_ids'][5]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 4)
        self.assertEqual(leg_forecast_1['replenish_qty'], 10)
        self.assertEqual(leg_forecast_6['starting_inventory_qty'], 6)
        self.assertEqual(screw_forecast_1['replenish_qty'], 44)

        # Replenish qty is superior to max_to_replenish_qty => apply max_to_replenish_qty
        self.mps_table.set_forecast_qty(date_index=0, quantity=2)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        leg_forecast_2 = mps_table_leg['forecast_ids'][1]
        leg_forecast_6 = mps_table_leg['forecast_ids'][5]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 8)
        self.assertEqual(leg_forecast_1['replenish_qty'], 5)
        self.assertEqual(leg_forecast_2['starting_inventory_qty'], -3)
        self.assertEqual(leg_forecast_2['replenish_qty'], 10)
        self.assertEqual(leg_forecast_6['starting_inventory_qty'], 7)
        self.assertEqual(screw_forecast_1['replenish_qty'], 28)
        self.assertEqual(screw_forecast_2['replenish_qty'], 40)

    def test_min_max_to_replenish_qty_3(self):
        """ Atypical cases: null max_to_replenish_qty, min == max. """
        self.mps_table_leg.write({'min_to_replenish_qty': 6, 'max_to_replenish_qty': 6, 'enable_max_replenish': True})

        # Replenish qty is inferior to min/max_to_replenish_qty
        self.mps_table.set_forecast_qty(date_index=0, quantity=1)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        leg_forecast_8 = mps_table_leg['forecast_ids'][7]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 4)
        self.assertEqual(leg_forecast_1['replenish_qty'], 6)
        self.assertEqual(leg_forecast_8['starting_inventory_qty'], 2)
        self.assertEqual(screw_forecast_1['replenish_qty'], 28)

        # Replenish qty is superior to min/max_to_replenish_qty
        self.mps_table.set_forecast_qty(date_index=0, quantity=3)
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        leg_forecast_2 = mps_table_leg['forecast_ids'][1]
        leg_forecast_8 = mps_table_leg['forecast_ids'][7]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 12)
        self.assertEqual(leg_forecast_1['replenish_qty'], 6)
        self.assertEqual(leg_forecast_2['starting_inventory_qty'], -6)
        self.assertEqual(leg_forecast_2['replenish_qty'], 6)
        self.assertEqual(leg_forecast_8['starting_inventory_qty'], 0)
        self.assertEqual(screw_forecast_1['replenish_qty'], 36)
        self.assertEqual(screw_forecast_2['replenish_qty'], 24)

        # Set max_to_replenish_qty of table_leg to zero
        self.mps_table_leg.max_to_replenish_qty = 0
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        leg_forecast_1 = mps_table_leg['forecast_ids'][0]
        leg_forecast_8 = mps_table_leg['forecast_ids'][7]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(leg_forecast_1['indirect_demand_qty'], 12)
        self.assertEqual(leg_forecast_1['replenish_qty'], 0)
        self.assertEqual(leg_forecast_8['starting_inventory_qty'], -12)
        self.assertEqual(screw_forecast_1['replenish_qty'], 12)

    @freeze_time('2025-01-01')
    def test_starting_inventory_qty(self):
        self.env['stock.quant'].create({
            'product_id': self.table.id,
            'inventory_quantity': 5,
            'location_id': self.warehouse.lot_stock_id.id
        }).action_apply_inventory()

        self.mps_table.set_forecast_qty(2, 3)
        mps_table = self.mps_table.get_production_schedule_view_state()[0]
        table_forecast_1 = mps_table['forecast_ids'][0]
        table_forecast_3 = mps_table['forecast_ids'][2]
        table_forecast_5 = mps_table['forecast_ids'][4]
        self.assertEqual(table_forecast_1['starting_inventory_qty'], 5)
        self.assertEqual(table_forecast_3['starting_inventory_qty'], 5)
        self.assertEqual(table_forecast_3['replenish_qty'], 0)
        self.assertEqual(table_forecast_3['safety_stock_qty'], 2)
        self.assertEqual(table_forecast_5['starting_inventory_qty'], 2)

        self.mps_table.set_forecast_qty(1, 4)
        mps_table, mps_table_leg, mps_screw = (self.mps_table | self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        table_forecast_2 = mps_table['forecast_ids'][1]
        table_forecast_3 = mps_table['forecast_ids'][2]
        table_forecast_7 = mps_table['forecast_ids'][6]
        leg_forecast_3 = mps_table_leg['forecast_ids'][2]
        screw_forecast_3 = mps_screw['forecast_ids'][2]
        self.assertEqual(table_forecast_2['starting_inventory_qty'], 5)
        self.assertEqual(table_forecast_2['replenish_qty'], 0)
        self.assertEqual(table_forecast_2['safety_stock_qty'], 1)
        self.assertEqual(table_forecast_3['starting_inventory_qty'], 1)
        self.assertEqual(table_forecast_3['replenish_qty'], 2)
        self.assertEqual(table_forecast_7['starting_inventory_qty'], 0)
        self.assertEqual(leg_forecast_3['replenish_qty'], 8)
        self.assertEqual(screw_forecast_3['replenish_qty'], 40)

        # test with lead times
        self.bom_table.produce_delay = 1
        self.table.write({'route_ids': [Command.set([self.ref('mrp.route_warehouse0_manufacture')])]})
        mps_table, mps_table_leg, mps_screw = (self.mps_table | self.mps_table_leg | self.mps_screw).get_production_schedule_view_state()
        table_forecast_7 = mps_table['forecast_ids'][6]
        leg_forecast_2 = mps_table_leg['forecast_ids'][1]
        screw_forecast_2 = mps_screw['forecast_ids'][1]
        self.assertEqual(table_forecast_7['starting_inventory_qty'], 0)
        self.assertEqual(leg_forecast_2['replenish_qty'], 8)
        self.assertEqual(screw_forecast_2['replenish_qty'], 40)

        # test with lead times and period switches
        # Switch period type to week
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state(period_scale='week')
        leg_forecast_8 = mps_table_leg['forecast_ids'][7] # 3rd week of February 2025
        leg_forecast_9 = mps_table_leg['forecast_ids'][8] # last week of February 2025
        screw_forecast_9 = mps_screw['forecast_ids'][8] # last week of February 2025
        self.assertEqual(leg_forecast_8['indirect_demand_qty'], 0)
        self.assertEqual(leg_forecast_9['indirect_demand_qty'], 8)
        self.assertEqual(screw_forecast_9['indirect_demand_qty'], 40)

        # While in week view, set new forecasted demand
        self.mps_table.set_forecast_qty(8, 0, period_scale='week') # last week of February 2025 (ends on March 2nd), set to 0
        self.mps_table.set_forecast_qty(9, 3, period_scale='week') # first FULL week of March 2025, set to 3
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state(period_scale='week')
        leg_forecast_9 = mps_table_leg['forecast_ids'][8] # last week of February 2025
        screw_forecast_9 = mps_screw['forecast_ids'][8] # last week of February 2025
        self.assertEqual(leg_forecast_9['indirect_demand_qty'], 8)
        self.assertEqual(screw_forecast_9['indirect_demand_qty'], 40)

        # Switch period type back to month
        # The indirect demand should be on the same month as the forecasted
        # demand because the previous week is still part of the same month.
        mps_table_leg, mps_screw = (self.mps_table_leg | self.mps_screw).get_production_schedule_view_state(period_scale='month')
        leg_forecast_2 = mps_table_leg['forecast_ids'][1] # February 2025
        leg_forecast_3 = mps_table_leg['forecast_ids'][2] # March 2025
        screw_forecast_3 = mps_screw['forecast_ids'][2] # March 2025
        self.assertEqual(leg_forecast_2['indirect_demand_qty'], 0)
        self.assertEqual(leg_forecast_3['indirect_demand_qty'], 8)
        self.assertEqual(screw_forecast_3['indirect_demand_qty'], 40)

    def test_multi_options(self):
        """ Test applying multiple settings all at once:
        - table: forecast demand = 5 on the 4th period
        - drawer: safety stock = 3, max replenish = 8
        - table leg: safety stock = 4, min replenish = 6, max replenish = 10
        - bolt: min replenish = 15, max replenish = 30
        - screw: min replenish = 80, max replenish = 200
        """
        self.mps_table.set_forecast_qty(3, 5)
        self.env.company.manufacturing_period_to_display_month = 7
        self.mps_drawer.write({'forecast_target_qty': 3, 'enable_max_replenish': True, 'max_to_replenish_qty': 2})
        self.mps_table_leg.write({'forecast_target_qty': 4, 'min_to_replenish_qty': 6, 'enable_max_replenish': True, 'max_to_replenish_qty': 8})
        self.mps_bolt.write({'min_to_replenish_qty': 15, 'enable_max_replenish': True, 'max_to_replenish_qty': 30})
        self.mps_screw.write({'forecast_target_qty': 30, 'min_to_replenish_qty': 80, 'enable_max_replenish': True, 'max_to_replenish_qty': 200})
        mps_table, mps_drawer, mps_leg, mps_bolt, mps_screw = (self.mps_table | self.mps_drawer | self.mps_table_leg | self.mps_bolt | self.mps_screw).get_production_schedule_view_state()

        self.assertListEqual([f['starting_inventory_qty'] for f in mps_table['forecast_ids']], [0, 0, 0, 0, 0, 0, 0])
        self.assertListEqual([f['forecast_qty'] for f in mps_table['forecast_ids']], [0, 0, 0, 5, 0, 0, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_table['forecast_ids']], [0, 0, 0, 5, 0, 0, 0])

        self.assertListEqual([f['starting_inventory_qty'] for f in mps_drawer['forecast_ids']], [0, 2, 3, 3, 0, 2, 3])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_drawer['forecast_ids']], [0, 0, 0, 5, 0, 0, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_drawer['forecast_ids']], [2, 1, 0, 2, 2, 1, 0])

        self.assertListEqual([f['starting_inventory_qty'] for f in mps_leg['forecast_ids']], [0, 4, 8, 8, 2, 4, 8])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_leg['forecast_ids']], [4, 2, 0, 14, 4, 2, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_leg['forecast_ids']], [8, 6, 0, 8, 6, 6, 0])

        self.assertListEqual([f['starting_inventory_qty'] for f in mps_bolt['forecast_ids']], [0, -2, 0, 0, -2, 0, 0])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_bolt['forecast_ids']], [32, 24, 0, 32, 24, 24, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_bolt['forecast_ids']], [30, 26, 0, 30, 26, 24, 0])

        self.assertListEqual([f['starting_inventory_qty'] for f in mps_screw['forecast_ids']], [0, 40, 92, 92, 52, 100, 72])
        self.assertListEqual([f['indirect_demand_qty'] for f in mps_screw['forecast_ids']], [40, 28, 0, 40, 32, 28, 0])
        self.assertListEqual([f['replenish_qty'] for f in mps_screw['forecast_ids']], [80, 80, 0, 0, 80, 0, 0])

    def test_actual_demand_multisteps(self):
        """ Test that actual demand is correctly calculated when deliveries are in multi-steps.
        It should only take into account the last move of the delivery chain.
        When that move is marked as done, it should instead use the next move if there's one. """
        self.env['stock.quant']._update_available_quantity(self.table, self.warehouse.lot_stock_id, 5)
        self.warehouse.delivery_steps = 'pick_pack_ship'
        pg = self.env['procurement.group'].create({'name': 'Test-MPS-actual-demand-multisteps'})
        self.env['procurement.group'].run([
            pg.Procurement(
                self.table,
                5.0,
                self.table.uom_id,
                self.env.ref('stock.stock_location_customers'),
                pg.name,
                pg.name,
                self.warehouse.company_id,
                {
                    'warehouse_id': self.warehouse,
                    'group_id': pg,
                },
            ),
        ])

        # Check that the outgoing quantity is 5 and that the related picking is the pick_picking
        pick_picking = pg.stock_move_ids.picking_id
        mps_table = self.mps_table.get_production_schedule_view_state()[0]
        self.assertEqual(mps_table['forecast_ids'][0]['outgoing_qty'], 5, 'actual demand qty is incorrect')
        # Get the domain_moves, it is always the same so no need to get it again
        domain_moves = self.mps_table._get_moves_domain(self.mps_dates_month[0][0], self.mps_dates_month[0][1], 'outgoing')
        mps_picking_1 = self.mps_table._get_moves_and_date(domain_moves)[0][0].picking_id
        self.assertEqual(mps_picking_1, pick_picking, 'It should be the pick_picking')

        # Validate the pick_picking, check that the outgoing quantity is still 5 and that the related picking is the pack_picking
        pick_picking.button_validate()
        pack_picking = pick_picking.move_ids.move_dest_ids.picking_id
        mps_table = self.mps_table.get_production_schedule_view_state()[0]
        mps_picking_2 = self.mps_table._get_moves_and_date(domain_moves)[0][0].picking_id
        self.assertEqual(mps_table['forecast_ids'][0]['outgoing_qty'], 5, 'actual demand qty is incorrect')
        self.assertEqual(mps_picking_2, pack_picking, 'It should be the pack_picking')

        # Validate the pack_picking, check that the outgoing quantity is still 5 and that the related picking is the ship_picking
        pack_picking.button_validate()
        ship_picking = pack_picking.move_ids.move_dest_ids.picking_id
        mps_table = self.mps_table.get_production_schedule_view_state()[0]
        mps_picking_3 = self.mps_table._get_moves_and_date(domain_moves)[0][0].picking_id
        self.assertEqual(mps_table['forecast_ids'][0]['outgoing_qty'], 5, 'actual demand qty is incorrect')
        self.assertEqual(mps_picking_3, ship_picking, 'It should be the ship_picking')

    def test_actual_demand_multisteps_2(self):
        """ Test that actual demand is correctly calculated when inter-warehouse deliveries are in multi-steps.
        It should only take into account the move 'Output -> Transit' from the first warehouse since it is
        created from the start. """
        # Create a second warehouse CC that is supplied by WH
        second_warehouse = self.env['stock.warehouse'].create({
            'name': 'Cainhurst Castle',
            'code': 'CC',
            'resupply_wh_ids': [Command.link(self.warehouse.id)],
        })
        # Link the resupply route to the product
        resupply_route = self.env['stock.route'].search([('supplier_wh_id', '=', self.warehouse.id), ('supplied_wh_id', '=', second_warehouse.id)])
        self.table.route_ids = [Command.set([resupply_route.id])]
        self.env['stock.quant']._update_available_quantity(self.table, self.warehouse.lot_stock_id, 5)
        self.warehouse.delivery_steps = 'pick_pack_ship'
        pg = self.env['procurement.group'].create({'name': 'Test-MPS-actual-demand-multisteps-interwarehouse'})
        self.env['procurement.group'].run([
            pg.Procurement(
                self.table,
                5.0,
                self.table.uom_id,
                second_warehouse.lot_stock_id,
                pg.name,
                pg.name,
                second_warehouse.company_id,
                {
                    'warehouse_id': second_warehouse,
                    'group_id': pg,
                },
            ),
        ])

        # Check that the outgoing quantity is 5 and that the related picking is the transit picking for WH
        wh_transit_picking = pg.stock_move_ids.filtered(lambda m: m.location_dest_id.usage == 'transit').picking_id
        mps_table_wh0 = self.mps_table.get_production_schedule_view_state()[0]
        self.assertEqual(mps_table_wh0['forecast_ids'][0]['outgoing_qty'], 5, 'actual demand qty is incorrect')
        # Get the domain_moves for outgoing moves for WH
        domain_moves = self.mps_table._get_moves_domain(self.mps_dates_month[0][0], self.mps_dates_month[0][1], 'outgoing')
        mps_picking_wh_out = self.mps_table._get_moves_and_date(domain_moves)[0][0].picking_id
        self.assertEqual(mps_picking_wh_out, wh_transit_picking, 'It should be the transit picking for WH')

        # Create an MPS record for Table for the second warehouse CC
        mps_record_table_cc = self.env['mrp.production.schedule'].create({
            'product_id': self.table.id,
            'warehouse_id': second_warehouse.id,
            'bom_id': self.bom_table.id,
        })
        # Check that the incoming quantity is 5 and that the related picking is the transit picking for CC
        cc_transit_picking = pg.stock_move_ids.filtered(lambda m: m.location_id.usage == 'transit').picking_id
        mps_table_cc0 = mps_record_table_cc.get_production_schedule_view_state()[0]
        self.assertEqual(mps_table_cc0['forecast_ids'][0]['incoming_qty'], 5, 'actual replenishment qty is incorrect')
        # Get the domain_moves for incoming moves for CC
        domain_moves = mps_record_table_cc._get_moves_domain(self.mps_dates_month[0][0], self.mps_dates_month[0][1], 'incoming')
        mps_picking_cc_in = mps_record_table_cc._get_moves_and_date(domain_moves)[0][0].picking_id
        self.assertEqual(mps_picking_cc_in, cc_transit_picking, 'It should be the transit picking for CC')

    def test_indirect_demand_different_uoms(self):
        """ Test that the MPS correctly computes the indirect demand when
        the final product and the component are in different units of measure
        with different rounding.
        The final product also has safety stock and minimum replenish qty:
        Settings:
        - final product:
            - rounding: 1.0
            - safety stock target: 1
            - minimum replenish qty: 4
        - component:
            - rounding: 0.01
        """
        # Create final product & component
        varnished_table, varnish = self.env['product.product'].create([{
            'name': n,
            'is_storable': True,
        } for n in ('varnished_table', 'varnish')])
        # Set a new UoM on the final product, rounding = 1.0
        varnished_table.uom_id = self.env['uom.uom'].create({
            'name': 'Integer Unit',
            'category_id': self.env.ref('uom.product_uom_unit').category_id.id,
            'uom_type': 'bigger',
            'factor_inv': 1,
            'rounding': 1,
        })
        # Create the BoM
        varnish_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': varnished_table.product_tmpl_id.id,
            'product_qty': 4,
            'bom_line_ids': [
                Command.create({'product_id': varnish.id, 'product_qty': 0.1}),
            ],
        })
        # Create the MPS records, set the safety stock and the minimum replenish qty
        mps_varnished_table = self.env['mrp.production.schedule'].create({
            'product_id': varnished_table.id,
            'warehouse_id': self.warehouse.id,
            'bom_id': varnish_bom.id,
            'forecast_target_qty': 1,
            'min_to_replenish_qty': 4
        })
        mps_varnish = self.env['mrp.production.schedule'].search([('product_id', '=', varnish.id)])
        # Check that the rounding of the final product does not hide the indirect demand by rounding to zero
        forecast_varnished_table, forecast_varnish = (mps_varnished_table | mps_varnish).get_production_schedule_view_state()
        self.assertEqual(forecast_varnished_table['forecast_ids'][0]['replenish_qty'], 4)
        self.assertEqual(forecast_varnish['forecast_ids'][0]['replenish_qty'], 0.1)

    def test_isolated_access(self):
        dummy = self.env['res.users'].create({
            'name': 'mps user',
            'login': 'mps',
            'email': 'test@test.test',
            # no 'Admin / Access Rights' group
            'groups_id': [Command.set((
                self.env.ref('mrp.group_mrp_manager').id,
            ))],
        })
        for fname in self.env.company._fields:
            if self.env.company._is_field_mps_display_group(fname):
                self.env.company.with_user(dummy).write({fname: not self.env.company[fname]})
        # no access errors
        self.assertTrue(True)

    def test_indirect_multiple_boms(self):
        """ This test ensure that having multiples BoMs for a product does not negatively impact the MPS.
        MPS should select in priority the BoM configured on the schedule, not the BoM returned by `_bom_find`
        """

        # Create final product & component
        fns, cmp = self.env['product.product'].create([{
            'name': n,
            'is_storable': True,
        } for n in ('fns', 'cmp')])

        # Create the BoMs
        # This V1 BoM is not used in mps, but will be the one returned by `_bom_find`
        self.env['mrp.bom'].create({
            'code': 'V1',
            'product_tmpl_id': fns.product_tmpl_id.id,
            'product_qty': 1,
            'bom_line_ids': [],
        })
        fns_bom_2 = self.env['mrp.bom'].create({
            'code': 'V2',
            'product_tmpl_id': fns.product_tmpl_id.id,
            'product_qty': 1,
            'bom_line_ids': [
                Command.create({'product_id': cmp.id, 'product_qty': 1}),
            ],
        })

        # Create the MPS records, set the safety stock and the minimum replenish qty
        mps_fns = self.env['mrp.production.schedule'].create({
            'product_id': fns.id,
            'warehouse_id': self.warehouse.id,
            'bom_id': fns_bom_2.id,
        })
        mps_cmp = self.env['mrp.production.schedule'].search([('product_id', '=', cmp.id)])
        self.assertTrue(bool(mps_cmp))

        mps_fns.set_forecast_qty(0, 10)

        # Check that the rounding of the final product does not hide the indirect demand by rounding to zero
        forecast_fns, forecast_cmp = (mps_fns | mps_cmp).get_production_schedule_view_state()
        self.assertEqual(forecast_fns['forecast_ids'][0]['forecast_qty'], 10)
        self.assertEqual(forecast_cmp['forecast_ids'][0]['indirect_demand_qty'], 10)
