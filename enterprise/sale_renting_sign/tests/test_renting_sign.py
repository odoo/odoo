# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.addons.sale_renting.tests.test_rental import TestRentalCommon
from odoo.addons.sign.tests.sign_request_common import SignRequestCommon


class TestRentalSign(TestRentalCommon, SignRequestCommon):

    def test_linked_record(self):
        partner = self.env['res.partner'].create({'name': 'A partner', 'email': "hello@plop.com"})
        reservation_begin = fields.Datetime.now()
        pickup_date = reservation_begin + relativedelta(days=1)
        return_date = pickup_date + relativedelta(hours=1)
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'rental_start_date': pickup_date,
            'rental_return_date': return_date,
            'order_line': [
                Command.create({
                    'product_id': self.product_id.id,
                    'reservation_begin': reservation_begin,
                }),
            ]
        })
        sr = self.create_sign_request_1_role(partner, self.env['res.partner'])
        # Sign.Request is not linked to record
        values = sr.get_close_values()
        action = values["action"]
        self.assertEqual(action["xml_id"], "sign.sign_request_action", "Generic action because the sr is not linked to any record")
        self.assertEqual(values["label"], "Close", "static button label to go back to the sign requests")
        self.assertFalse(values["custom_action"], "We get a custom action because the sr is linked to a record")

        # Sign.Request is linked to a generic SO
        sr.reference_doc = f"sale.order,{order.id}"
        self.assertTrue(order.order_line.is_product_rentable, "This is a rental line")
        self.assertFalse(order.is_rental_order, "Normal SO because the sol is not 'is_rental'")

        values = sr.get_close_values()
        action = values["action"]
        self.assertNotEqual(action["xml_id"], "sale_renting.rental_order_action", "Generic action of sale order")
        self.assertEqual(values["label"], "Back to Sales Order", "dynamic button label")
        self.assertTrue(values["custom_action"], "We get a custom action because the sr is linked to a record")

        # Sign.Request is linked to a rental SO
        order.order_line.is_rental = True
        values = sr.get_close_values()
        action = values["action"]
        self.assertTrue(order.is_rental_order, "This is a rental order")
        self.assertEqual(action["xml_id"], "sale_renting.rental_order_action", "Rental action")
