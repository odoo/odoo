# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_event_full.tests.common import TestEventFullCommon
from odoo.tests import tagged, users


@tagged("event_crm")
class TestEventCrm(TestEventFullCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrm, cls).setUpClass()

        cls.TICKET1_COUNT, cls.TICKET2_COUNT = 3, 1
        ticket1 = cls.test_event.event_ticket_ids[0]
        ticket2 = cls.test_event.event_ticket_ids[1]

        (cls.test_rule_attendee + cls.test_rule_order).write({'event_id': cls.test_event.id})

        # PREPARE SO DATA
        # ------------------------------------------------------------

        # adding some tickets to SO
        cls.customer_so.write({
            'order_line': [
                (0, 0, {
                    'event_id': cls.test_event.id,
                    'event_ticket_id': ticket1.id,
                    'product_id': ticket1.product_id.id,
                    'product_uom_qty': cls.TICKET1_COUNT,
                }), (0, 0, {
                    'event_id': cls.test_event.id,
                    'event_ticket_id': ticket2.id,
                    'product_id': ticket2.product_id.id,
                    'product_uom_qty': cls.TICKET2_COUNT,
                    'price_unit': 50,
                })
            ]
        })

    @users('user_sales_salesman')
    def test_event_crm_sale_customer(self):
        """ Test a SO with a real customer set on it, check partner propagation
        as well as group-based lead update. """
        customer_so = self.env['sale.order'].browse(self.customer_so.id)

        # adding some tickets to SO
        t1_reg_vals = [
            dict(customer_data,
                 partner_id=customer_so.partner_id.id,
                 sale_order_line_id=customer_so.order_line[0].id)
            for customer_data in self.website_customer_data[:self.TICKET1_COUNT]
        ]
        t1_registrations = self.env['event.registration'].create(t1_reg_vals)

        # check effect: registrations, leads
        self.assertEqual(self.test_event.registration_ids, t1_registrations)
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)
        self.assertEqual(self.test_rule_order_done.lead_ids, self.env['crm.lead'])
        # check lead converted based on registrations
        self.assertLeadConvertion(self.test_rule_order, t1_registrations, partner=customer_so.partner_id)

        # SO is confirmed -> missing registrations should be automatically added
        # and added to the lead as part of the same group
        customer_so.action_confirm()
        self.assertEqual(customer_so.state, 'sale')
        self.assertEqual(len(self.test_event.registration_ids), self.TICKET1_COUNT + self.TICKET2_COUNT)
        self.assertEqual(len(self.test_rule_order.lead_ids), 1)  # no new lead created
        self.assertEqual(self.test_rule_order_done.lead_ids, self.env['crm.lead'])  # this one still not triggered

        # check existing lead has been updated with new registrations
        self.assertLeadConvertion(self.test_rule_order, self.test_event.registration_ids, partner=customer_so.partner_id)

        # Confirm registrations -> trigger the "DONE" rule, one new lead linked to all
        # event registrations created in this test as all belong to the same SO
        self.test_event.registration_ids.write({'state': 'done'})
        self.assertLeadConvertion(self.test_rule_order_done, self.test_event.registration_ids, partner=customer_so.partner_id)

    @users('user_sales_salesman')
    def test_event_crm_sale_mixed_group(self):
        """ Test a mixed sale order line creation. This should not happen in a customer
        use case but should be supported by the code. """
        public_partner = self.env.ref('base.public_partner')
        public_so = self.env['sale.order'].create({
            'partner_id': public_partner.id,
            'order_line': [
                (0, 0, {
                    'event_id': self.test_event.id,
                    'event_ticket_id': self.test_event.event_ticket_ids[0].id,
                    'product_id': self.test_event.event_ticket_ids[0].product_id.id,
                    'product_uom_qty': 2,
                })
            ]
        })
        customer_so = self.env['sale.order'].browse(self.customer_so.id)

        # make a multi-SO create
        mixed_reg_vals = [
            dict(self.website_customer_data[0],
                 partner_id=customer_so.partner_id.id,
                 sale_order_line_id=customer_so.order_line[0].id),
            dict(self.website_customer_data[1],
                 partner_id=customer_so.partner_id.id,
                 sale_order_line_id=customer_so.order_line[0].id),
            dict(self.website_customer_data[2],
                 partner_id=public_so.partner_id.id,
                 sale_order_line_id=public_so.order_line[0].id),
            dict(self.website_customer_data[3],
                 partner_id=public_so.partner_id.id,
                 sale_order_line_id=public_so.order_line[0].id),
        ]
        self.env['event.registration'].create(mixed_reg_vals)

        public_regs = self.test_event.registration_ids.filtered(lambda reg: reg.sale_order_id == public_so)
        self.assertEqual(len(public_regs), 2)
        customer_regs = self.test_event.registration_ids.filtered(lambda reg: reg.sale_order_id == customer_so)
        self.assertEqual(len(customer_regs), 2)
        self.assertLeadConvertion(self.test_rule_order, public_regs, partner=None)
        self.assertLeadConvertion(self.test_rule_order, customer_regs, partner=customer_so.partner_id)

    @users('user_sales_salesman')
    def test_event_crm_sale_public(self):
        """ Test a SO with a public partner on it, then updated when SO is confirmed.
        This somehow simulates a simplified website_event_sale flow. """
        public_partner = self.env.ref('base.public_partner')
        customer_so = self.env['sale.order'].browse(self.customer_so.id)
        customer_so.write({
            'partner_id': public_partner.id,
        })

        # adding some tickets to SO
        t1_reg_vals = [
            dict(customer_data,
                 partner_id=public_partner.id,
                 sale_order_line_id=customer_so.order_line[0].id)
            for customer_data in self.website_customer_data[:self.TICKET1_COUNT]
        ]
        t1_registrations = self.env['event.registration'].create(t1_reg_vals)
        self.assertEqual(self.test_event.registration_ids, t1_registrations)

        # check lead converted based on registrations
        self.assertLeadConvertion(self.test_rule_order, t1_registrations, partner=None)

        # SO is confirmed -> missing registrations should be automatically added
        # BUT as public user -> no email -> not taken into account by rule
        customer_so.action_confirm()
        self.assertEqual(customer_so.state, 'sale')
        self.assertEqual(len(self.test_event.registration_ids), self.TICKET1_COUNT + self.TICKET2_COUNT)
        self.assertLeadConvertion(self.test_rule_order, t1_registrations, partner=None)

        # SO has a customer set -> main contact of lead is updated accordingly
        customer_so.write({'partner_id': self.event_customer.id})
        self.assertLeadConvertion(self.test_rule_order, t1_registrations, partner=self.event_customer)

    def test_event_update_lead(self):
        """Make sure that we update leads without issues when question's answer is added to an event attendee."""
        self.env['event.lead.rule'].search([]).write({'active': False})
        self.env['event.lead.rule'].create({
            'name': 'test_event_lead_rule',
            'lead_creation_basis': 'attendee',
            'lead_creation_trigger': 'create',
            'event_registration_filter': [['partner_id', '!=', False]],
            'lead_type': 'lead',
        })
        event_registration = self.env['event.registration'].create({
                    'name': 'Event Registration without answers added at first',
                    'event_id': self.test_event.id,
                    'partner_id': self.event_customer.id,
        })
        event_registration.write({
            'registration_answer_ids': [(0, 0, {
                'question_id': self.test_event.question_ids[1].id,
                'value_answer_id': self.test_event.question_ids[1].answer_ids[0].id,
            })]
        })
        self.assertIn(self.test_event.question_ids[1].answer_ids[0].name, event_registration.lead_ids[0].description,
            "lead description not updated with the answer to the question")
