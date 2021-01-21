# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_paytm.controllers.main import PaytmController

from odoo.tests import tagged

from lxml import objectify


class PaytmCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(PaytmCommon, self).setUp()

        self.paytm = self.env.ref('payment.payment_acquirer_paytm')
        self.paytm.write({'paytm_merchant_id': 'ovHiLo68583917222411', 'paytm_merchant_key': '05GT2Ju4QFLIM%VX'})

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


@tagged('post_install', '-at_install', 'external', '-standard')
class PaytmForm(PaytmCommon):

    def test_10_paytm_form_render(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # be sure not to do stupid things
        self.assertEqual(self.paytm.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------
        # render the button
        res = self.paytm.render(
            'test_ref0', 0.01, self.currency_india.id,
            values=self.buyer_values)

        form_values = {
            'MID': 'ovHiLo68583917222411',
            'ORDER_ID': 'test_ref0',
            'CUST_ID': self.buyer.id,
            'TXN_AMOUNT': '0.01',
            'CHANNEL_ID': 'WEB',
            'WEBSITE': 'WEBSTAGING',
            'MOBILE_NO': '0032 12 34 56 78',
            'EMAIL': 'norbert.buyer@example.com',
            'INDUSTRY_TYPE_ID': 'Retail',
            'CALLBACK_URL': urls.url_join(base_url, PaytmController._callback_url),
            'CHECKSUMHASH': b'RbOYJp+5Am9383jMMWPuddpo8UN9n6ev6BLaUT2DJBkXzkaYHqcL3+4OWqro'
                            b'JO8bsiK3TBHysMrMO87cHqisXvnfAsKJI5geuuFh8Lsf/iw=',
        }

        # check form result
        tree = objectify.fromstring(res)

        data_set = tree.xpath("//input[@name='data_set']")
        self.assertEqual(len(data_set), 1, 'paytm: Found %d "data_set" input instead of 1' % len(data_set))
        self.assertEqual(data_set[0].get('data-action-url'), 'https://securegw-stage.paytm.in/theia/processTransaction', 'paytm: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit', 'data_set', 'CUST_ID', 'CHECKSUMHASH']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'paytm: wrong value for input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    def test_20_paytm_form_management(self):
        # be sure not to do stupid things
        self.assertEqual(self.paytm.environment, 'test', 'test without test environment')

        # typical data posted by paytm after client has successfully paid
        paytm_post_data = {
            'BANKNAME': 'JPMORGAN CHASE BANK',
            'BANKTXNID': '4036217121962950',
            'CHECKSUMHASH': 'sImM2lxoByrJdIPtAh5J8XlpawNOLRBLux7b8LlzQBo6Xb8IPwjbn/OPiAQKEEVgsExpgT1orMKd0dev10gf9K9vPLWBhnTYVIwJxwX3qZ4=',
            'CURRENCY': 'INR',
            'GATEWAYNAME': 'HDFC',
            'MID': 'ovHiLo68583917222411',
            'ORDERID': 'test_ref0',
            'PAYMENTMODE': 'DC',
            'RESPCODE': '01',
            'RESPMSG': 'Txn Success',
            'STATUS': 'TXN_SUCCESS',
            'TXNAMOUNT': '14.07',
            'TXNDATE': '2019-01-01 12:07:18.0',
            'TXNID': '20190101111212800110168531000127632',
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(paytm_post_data, 'paytm')

        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 14.07,
            'acquirer_id': self.paytm.id,
            'currency_id': self.currency_india.id,
            'reference': 'test_ref0',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_india.id,
            'partner_id': self.buyer.id})

        # validate it
        tx.form_feedback(paytm_post_data, 'paytm')

        # check
        self.assertEqual(tx.state, 'done', 'paytm: wrong state after receiving a valid payment success notification')
        self.assertEqual(tx.acquirer_reference, '20190101111212800110168531000127632', 'paytm: wrong txn_id after receiving a valid payment success notification')
