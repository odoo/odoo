# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_sale.tests.common import TestEventSaleCommon
from odoo.tests import tagged
from odoo.tests.common import users


@tagged('event_flow')
class TestEventSale(TestEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventSale, cls).setUpClass()

        cls.event_0.write({
            'event_ticket_ids': [
                (5, 0),
                (0, 0, {
                    'name': 'First Ticket',
                    'product_id': cls.event_product.id,
                    'seats_max': 30,
                }), (0, 0, {
                    'name': 'Second Ticket',
                    'product_id': cls.event_product.id,
                })
            ],
        })

        # make a SO for a customer, selling some tickets
        cls.customer_so = cls.env['sale.order'].with_user(cls.user_sales_salesman).create({
            'partner_id': cls.event_customer.id,
        })

    @users('user_sales_salesman')
    def test_event_crm_sale(self):
        TICKET1_COUNT, TICKET2_COUNT = 3, 1
        customer_so = self.customer_so.with_user(self.env.user)
        ticket1 = self.event_0.event_ticket_ids[0]
        ticket2 = self.event_0.event_ticket_ids[1]

        # PREPARE SO DATA
        # ------------------------------------------------------------

        # adding some tickets to SO
        customer_so.write({
            'order_line': [
                (0, 0, {
                    'event_id': self.event_0.id,
                    'event_ticket_id': ticket1.id,
                    'product_id': ticket1.product_id.id,
                    'product_uom_qty': TICKET1_COUNT,
                    'price_unit': 10,
                }), (0, 0, {
                    'event_id': self.event_0.id,
                    'event_ticket_id': ticket2.id,
                    'product_id': ticket2.product_id.id,
                    'product_uom_qty': TICKET2_COUNT,
                    'price_unit': 50,
                })
            ]
        })
        ticket1_line = customer_so.order_line.filtered(lambda line: line.event_ticket_id == ticket1)
        ticket2_line = customer_so.order_line.filtered(lambda line: line.event_ticket_id == ticket2)
        self.assertEqual(customer_so.amount_untaxed, TICKET1_COUNT * 10 + TICKET2_COUNT * 50)

        # one existing registration for first ticket
        ticket1_reg1 = self.env['event.registration'].create({
            'event_id': self.event_0.id,
            'event_ticket_id': ticket1.id,
            'partner_id': self.event_customer2.id,
            'sale_order_id': customer_so.id,
            'sale_order_line_id': ticket1_line.id,
        })
        self.assertEqual(ticket1_reg1.partner_id, self.event_customer)
        for field in ['name', 'email', 'phone', 'mobile']:
            self.assertEqual(ticket1_reg1[field], self.event_customer[field])

        # EVENT REGISTRATION EDITOR
        # ------------------------------------------------------------

        # use event registration editor to create missing lines and update details
        editor = self.env['registration.editor'].with_context({
            'default_sale_order_id': customer_so.id
        }).create({})
        self.assertEqual(len(editor.event_registration_ids), TICKET1_COUNT + TICKET2_COUNT)
        self.assertEqual(editor.sale_order_id, customer_so)
        self.assertEqual(editor.event_registration_ids.sale_order_line_id, ticket1_line | ticket2_line)

        # check line linked to existing registration (ticket1_reg1)
        ticket1_editor_reg1 = editor.event_registration_ids.filtered(lambda line: line.registration_id)
        for field in ['name', 'email', 'phone', 'mobile']:
            self.assertEqual(ticket1_editor_reg1[field], ticket1_reg1[field])

        # check new lines
        ticket1_editor_other = editor.event_registration_ids.filtered(lambda line: not line.registration_id and line.event_ticket_id == ticket1)
        self.assertEqual(len(ticket1_editor_other), 2)
        ticket2_editor_other = editor.event_registration_ids.filtered(lambda line: not line.registration_id and line.event_ticket_id == ticket2)
        self.assertEqual(len(ticket2_editor_other), 1)

        # update lines in editor and save them
        ticket1_editor_other[0].write({
            'name': 'ManualEntry1',
            'email': 'manual.email.1@test.example.com',
            'phone': '+32456111111',
        })
        ticket1_editor_other[1].write({
            'name': 'ManualEntry2',
            'email': 'manual.email.2@test.example.com',
            'mobile': '+32456222222',
        })
        editor.action_make_registration()

        # check editor correctly created new registrations with information coming from it or SO as fallback
        self.assertEqual(len(self.event_0.registration_ids), TICKET1_COUNT + TICKET2_COUNT)
        new_registrations = self.event_0.registration_ids - ticket1_reg1
        self.assertEqual(new_registrations.sale_order_id, customer_so)
        ticket1_new_reg = new_registrations.filtered(lambda reg: reg.event_ticket_id == ticket1)
        ticket2_new_reg = new_registrations.filtered(lambda reg: reg.event_ticket_id == ticket2)
        self.assertEqual(len(ticket1_new_reg), 2)
        self.assertEqual(len(ticket2_new_reg), 1)
        self.assertEqual(
            set(ticket1_new_reg.mapped('name')),
            set(['ManualEntry1', 'ManualEntry2'])
        )
        self.assertEqual(
            set(ticket1_new_reg.mapped('email')),
            set(['manual.email.1@test.example.com', 'manual.email.2@test.example.com'])
        )
        self.assertEqual(
            set(ticket1_new_reg.mapped('phone')),
            set(['+32456111111', self.event_customer.phone])
        )
        self.assertEqual(
            set(ticket1_new_reg.mapped('mobile')),
            set(['+32456222222', self.event_customer.mobile])
        )
        for field in ['name', 'email', 'phone', 'mobile']:
            self.assertEqual(ticket2_new_reg[field], self.event_customer[field])

        # ADDING MANUAL LINES ON SO
        # ------------------------------------------------------------

        ticket2_line.write({'product_uom_qty': 3})
        editor_action = customer_so.action_confirm()
        self.assertEqual(customer_so.state, 'sale')
        self.assertEqual(customer_so.amount_untaxed, TICKET1_COUNT * 10 + (TICKET2_COUNT + 2) * 50)

        # check confirm of SO correctly created new registrations with information coming from SO
        self.assertEqual(len(self.event_0.registration_ids), 6)  # 3 for each ticket now
        new_registrations = self.event_0.registration_ids - (ticket1_reg1 | ticket1_new_reg | ticket2_new_reg)
        self.assertEqual(new_registrations.event_ticket_id, ticket2)
        self.assertEqual(new_registrations.partner_id, self.customer_so.partner_id)

        self.assertEqual(editor_action['type'], 'ir.actions.act_window')
        self.assertEqual(editor_action['res_model'], 'registration.editor')

    def test_ticket_price_with_pricelist_and_tax(self):
        self.env.user.partner_id.country_id = False
        pricelist = self.env['product.pricelist'].search([], limit=1)

        tax = self.env['account.tax'].create({
            'name': "Tax 10",
            'amount': 10,
        })

        event_product = self.env['product.template'].create({
            'name': 'Event Product',
            'list_price': 10.0,
        })

        event_product.taxes_id = tax

        event = self.env['event.event'].create({
            'name': 'New Event',
            'date_begin': '2020-02-02',
            'date_end': '2020-04-04',
        })
        event_ticket = self.env['event.event.ticket'].create({
            'name': 'VIP',
            'price': 1000.0,
            'event_id': event.id,
            'product_id': event_product.product_variant_id.id,
        })

        pricelist.item_ids = self.env['product.pricelist.item'].create({
            'applied_on': "1_product",
            'base': "list_price",
            'compute_price': "fixed",
            'fixed_price': 6.0,
            'product_tmpl_id': event_product.id,
        })

        pricelist.discount_policy = 'without_discount'

        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'pricelist_id': pricelist.id,
        })
        sol = self.env['sale.order.line'].create({
            'name': event.name,
            'product_id': event_product.product_variant_id.id,
            'product_uom_qty': 1,
            'product_uom': event_product.uom_id.id,
            'price_unit': event_product.list_price,
            'order_id': so.id,
            'event_id': event.id,
            'event_ticket_id': event_ticket.id,
        })
        sol.product_id_change()
        self.assertEqual(so.amount_total, 660.0, "Ticket is $1000 but the event product is on a pricelist 10 -> 6. So, $600 + a 10% tax.")
