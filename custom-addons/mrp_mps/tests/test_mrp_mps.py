# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

        cls.table = cls.env['product.product'].create({
            'name': 'Table',
            'type': 'product',
        })
        cls.drawer = cls.env['product.product'].create({
            'name': 'Drawer',
            'type': 'product',
        })
        cls.table_leg = cls.env['product.product'].create({
            'name': 'Table Leg',
            'type': 'product',
        })
        cls.screw = cls.env['product.product'].create({
            'name': 'Screw',
            'type': 'product',
        })
        cls.bolt = cls.env['product.product'].create({
            'name': 'Bolt',
            'type': 'product',
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
            'type': 'product',
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
            'type': 'product',
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
        })
        cls.mps_wardrobe = cls.env['mrp.production.schedule'].create({
            'product_id': cls.wardrobe.id,
            'warehouse_id': cls.warehouse.id,
        })
        cls.mps_chair = cls.env['mrp.production.schedule'].create({
            'product_id': cls.chair.id,
            'warehouse_id': cls.warehouse.id,
        })
        cls.mps_drawer = cls.env['mrp.production.schedule'].create({
            'product_id': cls.drawer.id,
            'warehouse_id': cls.warehouse.id,
        })
        cls.mps_table_leg = cls.env['mrp.production.schedule'].create({
            'product_id': cls.table_leg.id,
            'warehouse_id': cls.warehouse.id,
        })
        cls.mps_screw = cls.env['mrp.production.schedule'].create({
            'product_id': cls.screw.id,
            'warehouse_id': cls.warehouse.id,
        })
        cls.mps = cls.mps_table | cls.mps_wardrobe | cls.mps_chair |\
            cls.mps_drawer | cls.mps_table_leg | cls.mps_screw

    def test_basic_state(self):
        """ Testing master product scheduling default values for client
        action rendering.
        """
        mps_state = self.mps.get_mps_view_state()
        self.assertTrue(len(mps_state['manufacturing_period']), 12)

        # Remove demo data
        production_schedule_ids = [s for s in mps_state['production_schedule_ids'] if s['id'] in self.mps.ids]
        # Check that 6 states are returned (one by production schedule)
        self.assertEqual(len(production_schedule_ids), 6)
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
        mps_dates = self.env.company._get_date_range()
        forecast_screw = self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': mps_dates[0][0],
            'forecast_qty': 100
        })
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': mps_dates[1][0],
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

        mps_dates = self.env.company._get_date_range()
        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_screw.id,
            'date': mps_dates[0][0],
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
            'date': mps_dates[1][0],
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
            'date': mps_dates[2][0],
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

    def test_indirect_demand(self):
        """ On a multiple BoM relation, ensure that the replenish quantity on
        a production schedule impact the indirect demand on other production
        that have a component as product.
        """
        mps_dates = self.env.company._get_date_range()

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': self.mps_table.id,
            'date': mps_dates[0][0],
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
            'date': mps_dates[0][0],
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
            'date': mps_dates[1][0],
            'forecast_qty': 2
        })
        mps_drawer, mps_screw = (self.mps_drawer | self.mps_screw).get_production_schedule_view_state()
        drawer_forecast_1 = mps_drawer['forecast_ids'][0]
        screw_forecast_1 = mps_screw['forecast_ids'][0]
        self.assertEqual(drawer_forecast_1['indirect_demand_qty'], 11)
        self.assertEqual(screw_forecast_1['indirect_demand_qty'], 148)

    def test_indirect_demand_kit(self):
        """ On changing demand of a product whose BOM contains kit with a
        component, ensure that the replenish quantity on a production schedule
        impacts the indirect demand of kit's component.
        """
        cabinet = self.env['product.product'].create({
            'name': 'Cabinet',
            'type': 'product',
        })
        wood_kit = self.env['product.product'].create({
            'name': 'Wood Kit',
            'type': 'product',
        })
        wood = self.env['product.product'].create({
            'name': 'Wood',
            'type': 'product',
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

        mps_dates = self.env.company._get_date_range()

        self.env['mrp.product.forecast'].create({
            'production_schedule_id': mps_cabinet.id,
            'date': mps_dates[0][0],
            'forecast_qty': 2
        })

        # 4 wood from cabinet
        mps_wood = mps_wood.get_production_schedule_view_state()[0]
        wood_forecast_1 = mps_wood['forecast_ids'][0]
        self.assertEqual(wood_forecast_1['indirect_demand_qty'], 4)

    def test_impacted_schedule(self):
        impacted_schedules = self.mps_screw.get_impacted_schedule()
        self.assertEqual(sorted(impacted_schedules), sorted((self.mps - self.mps_screw).ids))

        impacted_schedules = self.mps_drawer.get_impacted_schedule()
        self.assertEqual(sorted(impacted_schedules), sorted((self.mps_table |
            self.mps_wardrobe | self.mps_table_leg | self.mps_screw).ids))

    def test_3_steps(self):
        self.warehouse.manufacture_steps = 'pbm_sam'
        self.table_leg.write({
            'route_ids': [(6, 0, [self.ref('mrp.route_warehouse0_manufacture')])]
        })

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
            'type': 'product',
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
        self.env.company.manufacturing_period_to_display = 10

        customer_location = self.env.ref('stock.stock_location_customers')
        stock_location = self.warehouse.lot_stock_id

        delivery_rule = self.env['stock.rule'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('location_src_id', '=', stock_location.id),
            ('location_dest_id', '=', customer_location.id),
            ('action', '=', 'pull')
        ], limit=1)
        delivery_rule.delay = 15

        product = self.env['product.product'].create({'name': 'SuperProduct', 'type': 'product'})
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

    def test_incoming_sm_and_lead_time_out_of_date_range(self):
        """
        Set a lead time on sam rule. Then generate an outgoing SM based on that
        rule with:
        - its date in dates range of MPS
        - its date + rule's lead time outside the dates range of MPS
        As a result, for the product mps, each incoming quantity should be zero
        """
        self.env.company.manufacturing_period = 'day'
        self.env.company.manufacturing_period_to_display = 10

        warehouse = self.warehouse
        warehouse.manufacture_steps = 'pbm_sam'
        post_production_location = warehouse.sam_loc_id
        stock_location = self.warehouse.lot_stock_id

        pull_sam = self.env['stock.rule'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('location_src_id', '=', post_production_location.id),
            ('location_dest_id', '=', stock_location.id),
            ('action', '=', 'pull')
        ], limit=1)
        pull_sam.delay = 15

        template = self.bom_wardrobe.product_tmpl_id
        template.route_ids = [(6, 0, pull_sam.route_id.ids)]
        product = template.product_variant_id

        procurement = self.env["procurement.group"].Procurement(
            product, 1, product.uom_id,
            stock_location,
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

        state = self.mps_wardrobe.get_production_schedule_view_state()[0]
        self.assertTrue(all(forecast['incoming_qty'] == 0 for forecast in state['forecast_ids']))

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
            'type': 'product',
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
