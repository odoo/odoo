# -*- coding: utf-8 -*-

import datetime
from odoo.tests.common import TransactionCase, users
from odoo.fields import Datetime
from unittest.mock import patch

from odoo.addons.test_mail.tests.common import mail_new_test_user

class EventSaleTest(TransactionCase):

    def setUp(self):
        super(EventSaleTest, self).setUp()

        self.EventRegistration = self.env['event.registration']

        # First I create an event product
        product = self.env['product.product'].create({
            'name': 'test_formation',
            'type': 'service',
            'event_ok': True,
        })

        # I create an event from the same type than my product
        self.event = self.env['event.event'].create({
            'name': 'test_event',
            'event_type_id': 1,
            'date_end': '2012-01-01 19:05:15',
            'date_begin': '2012-01-01 18:05:15'
        })

        ticket = self.env['event.event.ticket'].create({
            'name': 'test_ticket',
            'product_id': product.id,
            'event_id': self.event.id,
        })

        self.user_salesperson = mail_new_test_user(self.env, login='user_salesman', groups='sales_team.group_sale_salesman')

        # I create a sales order
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'note': 'Invoice after delivery',
            'payment_term_id': self.env.ref('account.account_payment_term_end_following_month').id
        })

        # In the sales order I add some sales order lines. i choose event product
        self.env['sale.order.line'].create({
            'product_id': product.id,
            'price_unit': 190.50,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'product_uom_qty': 8.0,
            'order_id': self.sale_order.id,
            'name': 'sales order line',
            'event_id': self.event.id,
            'event_ticket_id': ticket.id,
        })

        # In the event registration I add some attendee detail lines. i choose event product
        self.register_person = self.env['registration.editor'].create({
            'sale_order_id': self.sale_order.id,
            'event_registration_ids': [(0, 0, {
                'event_id': self.event.id,
                'name': 'Administrator',
                'email': 'abc@example.com',
                'sale_order_line_id': self.sale_order.order_line.id,
            })],
        })

    def test_00_create_event_product(self):
        # I click apply to create attendees
        self.register_person.action_make_registration()
        # I check if a registration is created
        registrations = self.EventRegistration.search([('origin', '=', self.sale_order.name)])
        self.assertTrue(registrations, "The registration is not created.")

    def test_event_is_registrable(self):
        self.patcher = patch('odoo.addons.event.models.event.fields.Datetime', wraps=Datetime)
        self.mock_datetime = self.patcher.start()

        test_event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': datetime.datetime(2019, 6, 8, 12, 0),
            'date_end': datetime.datetime(2019, 6, 12, 12, 0),
        })

        self.mock_datetime.now.return_value = datetime.datetime(2019, 6, 9, 12, 0)
        self.assertEqual(test_event._is_event_registrable(), True)

        self.mock_datetime.now.return_value = datetime.datetime(2019, 6, 13, 12, 0)
        self.assertEqual(test_event._is_event_registrable(), False)

        self.mock_datetime.now.return_value = datetime.datetime(2019, 6, 10, 12, 0)
        test_event.write({'event_ticket_ids': [(6, 0, [])]})
        self.assertEqual(test_event._is_event_registrable(), True)

        test_event_ticket = self.env['event.event.ticket'].create({
            'name': 'TestTicket',
            'event_id': test_event.id,
            'product_id': 1,
        })
        test_event_ticket.copy()
        test_event_ticket.product_id.active = False
        self.assertEqual(test_event._is_event_registrable(), False)

        self.patcher.stop()

    def test_01_ticket_price_with_pricelist_and_tax(self):
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

    @users('user_salesman')
    def test_unlink_so(self):
        """ This test ensures that when deleting a sale order, if the latter is linked to an event registration,
        the number of expected seats will be correctly updated """
        event = self.env['event.event'].browse(self.event.ids)
        self.register_person.action_make_registration()
        self.assertEqual(event.seats_expected, 1)
        self.sale_order.unlink()
        self.assertEqual(event.seats_expected, 0)

    @users('user_salesman')
    def test_unlink_soline(self):
        """ This test ensures that when deleting a sale order line, if the latter is linked to an event registration,
        the number of expected seats will be correctly updated """
        event = self.env['event.event'].browse(self.event.ids)
        self.register_person.action_make_registration()
        self.assertEqual(event.seats_expected, 1)
        self.sale_order.order_line.unlink()
        self.assertEqual(event.seats_expected, 0)
        
    @users('user_salesman')
    def test_cancel_so(self):
        """ This test ensures that when canceling a sale order, if the latter is linked to an event registration,
        the number of expected seats will be correctly updated """
        event = self.env['event.event'].browse(self.event.ids)
        self.register_person.action_make_registration()
        self.assertEqual(event.seats_expected, 1)
        self.sale_order.action_cancel()
        self.assertEqual(event.seats_expected, 0)
