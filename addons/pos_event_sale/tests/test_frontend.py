# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.pos_event.tests.test_frontend import TestUi
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestPoSEventSale(TestUi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_sale_status_event_in_pos(self):
        self.pos_user.write({
            'groups_id': [
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
                    "pack_lot_ids": [],
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
            "last_order_preparation_change": "{}",
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
                    "pack_lot_ids": [],
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
            "last_order_preparation_change": "{}",
            "user_id": self.env.uid,
            "to_invoice": False,
            "state": "draft",
        }
        self.env['pos.order'].sync_from_ui([order_data, order_data_2])
        sale_status = self.env['event.registration'].search([]).mapped("sale_status")
        self.assertEqual(len(sale_status), 2)
        self.assertIn('sold', sale_status)
        self.assertIn('to_pay', sale_status)
