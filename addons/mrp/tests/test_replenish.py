# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

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
