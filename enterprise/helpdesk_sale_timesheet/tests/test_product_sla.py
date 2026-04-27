# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests.common import HelpdeskCommon


class TestHelpdeskSaleTimesheetSLA(HelpdeskCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_team.use_sla = True
        cls.product_template = cls.env['product.template'].create({
            'name': 'Service',
            'type': 'service',
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Partner',
        })

        cls.sla_with_product, cls.sla_with_partner, cls.sla_with_both = cls.env['helpdesk.sla'].create([
            {
                'name': 'SLA with product',
                'team_id': cls.test_team.id,
                'stage_id': cls.stage_new.id,
                'product_ids': [cls.product_template.id],
            }, {
                'name': 'SLA with partner',
                'team_id': cls.test_team.id,
                'stage_id': cls.stage_new.id,
                'partner_ids': [cls.partner.id],
            }, {
                'name': 'SLA with both',
                'team_id': cls.test_team.id,
                'stage_id': cls.stage_new.id,
                'product_ids': [cls.product_template.id],
                'partner_ids': [cls.partner.id],
            }
        ])

        cls.product = cls.env['product.product'].search([('product_tmpl_id', '=', cls.product_template.id)])

        sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })
        cls.product_sol = cls.env['sale.order.line'].create({
            'product_id': cls.product.id,
            'price_unit': 1.0,
            'order_id': sale_order.id,
        })

    def test_sla_on_ticket_product(self):
        product_ticket = self.env['helpdesk.ticket'].create({
            'name': 'product ticket',
            'team_id': self.test_team.id,
            'sale_line_id': self.product_sol.id,
        })

        self.assertEqual(sorted(product_ticket.sla_status_ids.sla_id.ids), [self.sla_with_product.id, self.sla_with_both.id])

    def test_sla_on_ticket_partner(self):
        product_ticket = self.env['helpdesk.ticket'].create({
            'name': 'product ticket',
            'team_id': self.test_team.id,
            'partner_id': self.partner.id,
        })

        self.assertEqual(sorted(product_ticket.sla_status_ids.sla_id.ids), [self.sla_with_partner.id, self.sla_with_both.id])

    def test_sla_on_ticket_both(self):
        product_ticket = self.env['helpdesk.ticket'].create({
            'name': 'product ticket',
            'team_id': self.test_team.id,
            'sale_line_id': self.product_sol.id,
            'partner_id': self.partner.id,
        })

        self.assertListEqual(sorted(product_ticket.sla_status_ids.sla_id.ids), [self.sla_with_product.id, self.sla_with_partner.id, self.sla_with_both.id])
