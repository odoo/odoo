# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests.common import HelpdeskCommon


class TestHelpdeskSaleTimesheetSLA(HelpdeskCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_team.use_sla = True
        cls.sla = cls.env['helpdesk.sla'].create({
            'name': 'SLA',
            'team_id': cls.test_team.id,
            'time': 32,
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Partner',
        })

        cls.product_template = cls.env['product.template'].create({
            'name': 'Service',
            'type': 'service',
            'sla_id': cls.sla.id,
        })
        cls.product = cls.env['product.product'].search([('product_tmpl_id', '=', cls.product_template.id)])

    def test_sol_sla(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'price_unit': 1.0,
            'order_id': sale_order.id,
        })

        sale_order.action_confirm()
        self.assertIn(sol, self.sla.sale_line_ids, 'The SOL containing the service should be set on the SLA policy once the SO in confirmed.')
