# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo import fields



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

        scrap_wizard_dict = basic_mo.button_scrap()
        scrap_form = Form(self.env[scrap_wizard_dict['res_model']].with_context(scrap_wizard_dict['context']))
        scrap_form.product_id = product_to_scrap
        scrap_form.should_replenish = True
        self.assertEqual(scrap_form.location_id, warehouse.pbm_loc_id)
        scrap_form.save().action_validate()
        self.assertNotEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])
        self.assertEqual(len(basic_mo.picking_ids), 2)
        replenish_picking = basic_mo.picking_ids.filtered(lambda x: x.state == 'assigned')
        replenish_picking.button_validate()
        self.assertEqual(basic_mo.move_raw_ids.mapped('state'), ['assigned', 'assigned'])
