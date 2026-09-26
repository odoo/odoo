# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.pos_event.tests.test_frontend import TestUi
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestPoSEventSale(TestUi):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_user.group_ids += cls.quick_ref('sales_team.group_sale_salesman_all_leads')

    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref('sales_team.group_sale_salesman_all_leads')

    def _create_event_sale_order(self):
        event = self.test_event_registration_not_mandatory
        return self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_event.id,
                    'product_uom_qty': 2,
                    'event_id': event.id,
                    'event_ticket_id': event.event_ticket_ids[0].id,
                }),
            ],
        })

    def test_settle_event_quotation(self):
        """ A quotation has no attendee yet, so the PoS registers them on settlement and they are
        confirmed by the payment, as when the tickets are sold from the PoS. """
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        sale_order = self._create_event_sale_order()
        self.assertFalse(sale_order.order_line.registration_ids)

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SettleEventQuotation')

        pos_order = self.main_pos_config.current_session_id.order_ids
        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(sale_order.state, 'sale')

        # Confirming the sale order must not register the same attendees a second time
        registrations = sale_order.order_line.registration_ids
        self.assertEqual(len(registrations), 2)
        self.assertEqual(registrations.pos_order_line_id, pos_order.lines)
        self.assertEqual(set(registrations.mapped('state')), {'open'})
        self.assertEqual(set(registrations.mapped('sale_status')), {'sold'})
        self.assertEqual(sorted(registrations.mapped('name')), ['Attendee 1', 'Attendee 2'])
        self.assertEqual(
            sorted(registrations.mapped('email')),
            ['attendee1@test.com', 'attendee2@test.com'],
        )

    def test_settle_registered_event_sale_order(self):
        """ A confirmed sale order already registered its attendees: the PoS leaves them alone. """
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        sale_order = self._create_event_sale_order()
        sale_order.action_confirm()
        registrations = sale_order.order_line.registration_ids
        self.assertEqual(len(registrations), 2)

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SettleRegisteredEventSaleOrder')

        self.assertEqual(self.main_pos_config.current_session_id.order_ids.state, 'paid')
        self.assertEqual(sale_order.order_line.registration_ids, registrations)
        self.assertFalse(registrations.pos_order_line_id)
        self.assertEqual(set(registrations.mapped('state')), {'draft'})

    def test_sale_status_event_in_pos(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('event.group_event_user').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()

        order_data = {
            "amount_paid": 100,
            "amount_tax": 0,
            "amount_return": 0,
            "amount_total": 100,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "lines": [
                Command.create({
                    "discount": 0,
                    "price_unit": 100.0,
                    "product_id": self.product_event.id,
                    "price_subtotal": 100.0,
                    "price_subtotal_incl": 100.0,
                    "tax_ids": [],
                    "qty": 1,
                    "event_ticket_id": self.test_event.event_ticket_ids[0].id,
                    "event_registration_ids": [
                        (0, 0, {
                            "event_id": self.test_event.id,
                            "event_ticket_id": self.test_event.event_ticket_ids[0].id,
                            "name": "Test Name",
                            "email": "Test Email",
                            "phone": "047123123198",
                        }),
                    ],
                }),
            ],
            "name": "Order 12345-123-1234",
            "partner_id": self.partner_a.id,
            "session_id": self.main_pos_config.current_session_id.id,
            "sequence_number": 2,
            "payment_ids": [
                    Command.create({
                        "amount": 100,
                        "name": fields.Datetime.now(),
                        "payment_method_id": self.bank_payment_method.id,
                    }),
            ],
            "uuid": "12345-123-1234",
            "user_id": self.env.uid,
            "to_invoice": False,
        }

        order_data_2 = {
            "amount_paid": 100,
            "amount_tax": 0,
            "amount_return": 0,
            "amount_total": 100,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "lines": [
                Command.create({
                    "discount": 0,
                    "price_unit": 100.0,
                    "product_id": self.product_event.id,
                    "price_subtotal": 100.0,
                    "price_subtotal_incl": 100.0,
                    "tax_ids": [],
                    "qty": 1,
                    "event_ticket_id": self.test_event.event_ticket_ids[0].id,
                    "event_registration_ids": [
                        (0, 0, {
                            "event_id": self.test_event.id,
                            "event_ticket_id": self.test_event.event_ticket_ids[0].id,
                            "name": "Test Name",
                            "email": "Test Email",
                            "phone": "047123123198",
                        }),
                    ],
                }),
            ],
            "name": "Order 12345-123-1234",
            "access_token": "12345-123-1234",
            "partner_id": self.partner_a.id,
            "session_id": self.main_pos_config.current_session_id.id,
            "sequence_number": 2,
            "payment_ids": [],
            "uuid": "12345-123-4331",
            "user_id": self.env.uid,
            "to_invoice": False,
            "state": "draft",
        }
        self.env['pos.order'].sync_from_ui([order_data, order_data_2])
        sale_status = self.env['event.registration'].search([]).mapped("sale_status")
        self.assertEqual(len(sale_status), 2)
        self.assertIn('sold', sale_status)
        self.assertIn('to_pay', sale_status)
