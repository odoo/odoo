# -*- coding: utf-8 -*-

from odoo.tests import common


class EventSaleTest(common.TransactionCase):

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
        event = self.env['event.event'].create({
            'name': 'test_event',
            'event_type_id': 1,
            'date_end': '2012-01-01 19:05:15',
            'date_begin': '2012-01-01 18:05:15'
        })

        # I create a sales order
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'note': 'Invoice after delivery',
            'payment_term_id': self.env.ref('account.account_payment_term').id
        })

        # In the sales order I add some sales order lines. i choose event product
        self.env['sale.order.line'].create({
            'product_id': product.id,
            'price_unit': 190.50,
            'product_uom': self.env.ref('product.product_uom_unit').id,
            'product_uom_qty': 8.0,
            'order_id': self.sale_order.id,
            'name': 'sales order line',
            'event_id': event.id
        })

        # In the event registration I add some attendee detail lines. i choose event product
        self.register_person = self.env['registration.editor'].create({
            'sale_order_id': self.sale_order.id,
            'event_registration_ids': [(0, 0, {
                'event_id': event.id,
                'name': 'Administrator',
                'email': 'abc@example.com'
            })],
        })

    def test_00_create_event_product(self):
        # I click apply to create attendees
        self.register_person.action_make_registration()
        # I check if a registration is created
        registrations = self.EventRegistration.search([('origin', '=', self.sale_order.name)])
        self.assertTrue(registrations, "The registration is not created.")
