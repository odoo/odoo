# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_crm_sale.tests.common import TestEventCrmSaleCommon
from odoo.tests import users
from odoo.tools import mute_logger


class TestEventSaleCrm(TestEventCrmSaleCommon):

    @users('user_sales_salesman')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_crm_sale(self):
        self.assertEqual(self.test_rule_order.lead_ids, self.env['crm.lead'])

        # make a SO for a customer, selling some tickets
        customer_so = self.env['sale.order'].create({
            'partner_id': self.test_customer.id,
        })
        customer_so.write({
            'order_line': [(0, 0, {
                'event_id': self.event_0.id,
                'event_ticket_id': self.event_0.event_ticket_ids[0].id,
                'product_id': self.event_0.event_ticket_ids[0].product_id.id,
                'product_uom_qty': 4,
            })]
        })
        self.assertEqual(customer_so.amount_untaxed, 4 * self.event_0.event_ticket_ids[0].product_id.list_price)

        registration_vals = [
            dict(customer_data,
                 event_id=self.event_0.id,
                 sale_order_id=customer_so.id,
                 sale_order_line_id=customer_so.order_line[0].id)
            for customer_data in self.batch_customer_data
        ]
        self.env['event.registration'].create(registration_vals)

        self.assertEqual(len(self.test_rule_order.lead_ids), len(registration_vals))

    # @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    # def test_event_crm_flow_per_order(self):
    #     lead = self.env['crm.lead'].search([
    #         ('event_id', '=', self.test_event.id),
    #         ('event_lead_rule_id', '=', self.test_rule_order.id)
    #     ])

    #     self.assertEqual(len(lead), 1,
    #         "Event CRM: one lead sould be created for the set of attendees")

    #     self.assertEqual(lead.registration_count, 3,
    #         "Event CRM: registration which does not check the rule should not be linked to the lead")

    #     self.assertEqual(len(lead.event_id.registration_ids), 4,
    #         "Event CRM: four registrations should have been created for the event")

    # @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    # def test_event_crm_multi_rules(self):
    #     leads = self.env['crm.lead'].search([
    #         ('event_id', '=', self.test_event.id),
    #         ('event_lead_rule_id', 'in', [self.test_rule_attendee.id, self.test_rule_order.id])
    #     ])

    #     self.assertEqual(len(leads), 4,
    #         "Event CRM: four leads sould be created for the set of attendees")

    #     self.assertEqual(len(leads.event_id.registration_ids), 4,
    #         "Event CRM: four registrations should have been created for the event")
