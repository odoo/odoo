# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment.models.payment_acquirer import ValidationError

from odoo.tests import tagged


class RazorpayCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(RazorpayCommon, self).setUp()

        self.razorpay = self.env.ref('payment.payment_acquirer_razorpay')
        self.razorpay.write({'razorpay_key_id': 'rzp_test_2hDe6P3Lim1ZEu', 'razorpay_key_secret': 'Y63AyP9eL91Zw3XL5tgzujIu', 'fees_active': False})

        self.country_india = self.env['res.country'].search([('code', 'like', 'IN')], limit=1)
        self.currency_india = self.env.ref('base.INR')

        # test partner
        self.buyer.update({
            'country_id': self.country_india.id
        })

        # dict partner values
        self.buyer_values.update({
            'partner': self.buyer,
            'partner_country': self.country_india.id,
            'partner_country_id': self.country_india.id,
        })


@tagged('post_install', '-at_install', '-standard', 'external')
class RazorpayTest(RazorpayCommon):

    def test_10_razorpay_form_render(self):
        self.assertEqual(self.razorpay.environment, 'test', 'test without test environment')
        res = self.razorpay.render('test_ref0', 14.07, self.currency_india.id, values=self.buyer_values).decode('utf-8')
        popup_script_src = 'script src="https://checkout.razorpay.com/v1/checkout.js"'
        # check form result
        self.assertIn(popup_script_src, res, "Razorpay: popup script not found in template render")
        # Generated and received
        self.assertIn(self.buyer_values.get('email'), res, 'Razorpay: email input not found in rendered template')

    def test_20_razorpay_form_management(self):
        self.assertEqual(self.razorpay.environment, 'test', 'test without test environment')

        razorpay_post_data = {
            'amount': 1407,
            'amount_refunded': 0,
            'bank': 'UTIB',
            'captured': True,
            'card_id': None,
            'contact': '+15555555555',
            'created_at': 1547120621,
            'currency': 'INR',
            'description': None,
            'email': 'admin@yourcompany.example.com',
            'entity': 'payment',
            'error_code': None,
            'error_description': None,
            'fee': 2538,
            'id': 'pay_BiKFM49mcKCwvd',
            'international': False,
            'invoice_id': None,
            'method': 'netbanking',
            'notes': {'order_id': 'test_ref0'},
            'order_id': None,
            'refund_status': None,
            'status': 'captured',
            'tax': 388,
            'vpa': None,
            'wallet': None
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(razorpay_post_data, 'razorpay')

        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': razorpay_post_data.get('amount') / 100,
            'acquirer_id': self.razorpay.id,
            'currency_id': self.currency_india.id,
            'reference': razorpay_post_data.get('notes').get('order_id'),
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_india.id,
            'partner_id': self.buyer.id})

        # validate it
        tx.form_feedback(razorpay_post_data, 'razorpay')

        # check
        self.assertEqual(tx.state, 'done', 'razorpay: wrong state after receiving a valid payment success notification')
