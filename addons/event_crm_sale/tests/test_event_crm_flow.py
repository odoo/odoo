from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.tests import tagged
from odoo import Command, fields

from datetime import timedelta


@tagged('post_install', '-at_install')
class TestEventCrmFlow(TestEventCrmCommon):

    def test_lead_generation_double_event_match(self):
        self.test_rule_order.event_id = False
        self.test_rule_order.event_registration_filter = False
        event_1 = self.env['event.event'].create({
            'name': 'TestEvent 1',
            'date_begin': fields.Datetime.to_string(fields.Datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(fields.Datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
        })
        event_product = self.env['product.product'].create({
            'name': 'Test Registration Product',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'standard_price': 30.0,
            'type': 'service',
            'service_tracking': 'event',
        })
        ticket_0, ticket_1 = [self.env['event.event.ticket'].create({
            'name': 'First Ticket',
            'product_id': event_product.id,
            'seats_max': 30,
            'event_id': event.id,
        }) for event in [self.event_0, event_1]]
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [Command.create({
                'product_id': event_product.id,
                'price_unit': 190.50,
                'event_id': ticket.event_id.id,
                'event_ticket_id': ticket.id,
            }) for ticket in [ticket_0, ticket_0, ticket_1]]
        })
        sale_order.action_confirm()
        created_leads = self.env['crm.lead'].search([('event_id', '!=', False)], order="id")
        self.assertRecordValues(created_leads, [{'event_id': self.event_0.id}, {'event_id': event_1.id}])
