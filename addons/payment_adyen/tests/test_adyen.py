# -*- coding: utf-8 -*-

from lxml import objectify

from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_adyen.controllers.main import AdyenController
from werkzeug import urls


class AdyenCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(AdyenCommon, self).setUp()

        # some CC (always use expiration date 06 / 2016, cvc 737, cid 7373 (amex))
        self.amex = (('370000000000002', '7373'))
        self.dinersclub = (('36006666333344', '737'))
        self.discover = (('6011601160116611', '737'), ('644564456445644', '737'))
        self.jcb = (('3530111333300000', '737'))
        self.mastercard = (('5555444433331111', '737'), ('5555555555554444', '737'))
        self.visa = (('4111 1111 1111 1111', '737'), ('4444333322221111', '737'))
        self.mcdebit = (('5500000000000004', '737'))
        self.visadebit = (('4400000000000008', '737'))
        self.maestro = (('6731012345678906', '737'))
        self.laser = (('630495060000000000', '737'))
        self.hipercard = (('6062828888666688', '737'))
        self.dsmastercard = (('521234567890 1234', '737', 'user', 'password'))
        self.dsvisa = (('4212345678901237', '737', 'user', 'password'))
        self.mistercash = (('6703444444444449', None, 'user', 'password'))


class AdyenForm(AdyenCommon):

    def test_10_adyen_form_render(self):
        # be sure not to do stupid things
        adyen = self.env.ref('payment.payment_acquirer_adyen')
        self.assertEqual(adyen.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        form_values = {
            'merchantAccount': 'OpenERPCOM',
            'merchantReference': 'test_ref0',
            'skinCode': 'cbqYWvVL',
            'paymentAmount': '1',
            'currencyCode': 'EUR',
            'resURL': urls.url_join(base_url, AdyenController._return_url),
        }

        # render the button
        res = adyen.render(
            'test_ref0', 0.01, self.currency_euro.id,
            partner_id=None,
            partner_values=self.buyer_values)

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://test.adyen.com/hpp/pay.shtml', 'adyen: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit', 'shipBeforeDate', 'sessionValidity', 'shopperLocale', 'merchantSig']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'adyen: wrong value for input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )
