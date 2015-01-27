# -*- coding: utf-8 -*-

from lxml import objectify
import urlparse

import openerp
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment.tests.common import PaymentAcquirerCommon
from openerp.addons.payment_payumoney.controllers.main import PayuMoneyController
from openerp.tools import mute_logger


@openerp.tests.common.at_install(True)
@openerp.tests.common.post_install(True)
class PayuMoneyCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(PayuMoneyCommon, self).setUp()
        self.base_url = self.env[
            'ir.config_parameter'].get_param('web.base.url')
        # get the payumoney account
        self.payumoney = self.env.ref('payment_payumoney.payment_acquirer_payu')


@openerp.tests.common.at_install(True)
@openerp.tests.common.post_install(True)
class PayuMoneyForm(PayuMoneyCommon):

    def test_10_payumoney_form_render(self):
        self.assertEqual(
            self.payumoney.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        form_values = {
            'key': self.payumoney.merchant_id,
            'txnid': 'SO004',
            'amount': '2240.0',
            'productinfo': 'SO004',
            'firstname': 'Buyer',
            'email': 'norbert.buyer@example.com',
            'phone': '0032 12 34 56 78',
            'service_provider': 'payu_paisa',
            'udf1': None,
            'surl': '%s' % urlparse.urljoin(self.base_url, PayuMoneyController._return_url),
            'furl': '%s' % urlparse.urljoin(self.base_url, PayuMoneyController._exception_url),
            'curl': '%s' % urlparse.urljoin(self.base_url, PayuMoneyController._cancel_url),
        }

        form_values['hash'] = self.env['payment.acquirer']._payu_generate_sign(
            self.payumoney, 'in', form_values)

        # render the button
        res = self.payumoney.render(
            'SO004', 2240.0, self.currency_euro_id, partner_id=None, partner_values=self.buyer_values)

        # check form result
        tree = objectify.fromstring(res[0])
        self.assertEqual(
            tree.get('action'), 'https://test.payu.in/_payment', 'PayuMoney: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'PayuMoney: wrong value for input %s: received %s instead of %s' % (
                    form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    @mute_logger('openerp.addons.payment_payumoney.models.payumoney', 'ValidationError')
    def test_20_payumoney_form_management(self):
        self.assertEqual(
            self.payumoney.environment, 'test', 'test without test environment')

        # typical data posted by payumoney after client has successfully paid
        payumoney_post_data = {
            'key': u'JBZaLc',
            'firstname': u'Buyer',
            'productinfo': u'SO004',
            'txnid': u'SO004',
            'amount': u'2240.0',
            'email': u'norbert.buyer@example.com',
            'hash': u'7f107b66ade6ee1d0c148060feddd4e07487817cf0f652fac983847bfd2d43638820485fcb9e685a4a596bf4eec98fbc4f15abea5004bae36ab8475ff030a17f',
            'mihpayid': u'403993715511008414',
            'udf1': u'',
            'status': u'success',
            'payuMoneyId': u'110024086',
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(
                payumoney_post_data, 'payumoney')

        tx = self.env['payment.transaction'].create(
            {
                'amount': 2240.0,
                'acquirer_id': self.payumoney.id,
                'currency_id': self.currency_euro_id,
                'reference': 'SO004',
                'partner_name': 'Norbert Buyer',
                'partner_country_id': self.country_france_id,
            })
        # validate it
        self.env['payment.transaction'].form_feedback(
            payumoney_post_data, 'payumoney')
        # check state
        self.assertEqual(
            tx.state, 'done', 'PayuMoney: validation did not put tx into done state')
        self.assertEqual(tx.payumoney_txnid, payumoney_post_data.get(
            'mihpayid'), 'PayuMoney: validation did not update tx payid')
        self.assertEqual(tx.payumoney_id, payumoney_post_data.get(
            'payuMoneyId'), 'PayuMoney: validation did not update unique payment id')
        # reset tx
        tx.write(
            {'state': 'draft', 'date_validate': False, 'payumoney_txnid': False})

        # now payumoney post is ok: try to modify the Hash
        payumoney_post_data['hash'] = '51fbd1f0b8cff2f0342bd88e8aa199fbd144f94ed0c55653b50f76b8051def415261f381625838303e1df11cf75866dd35079c7aa2001e7d459bf4ffd'
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(
                payumoney_post_data, 'payumoney')

        # simulate an error
        payumoney_post_data['status'] = u'pending'
        payumoney_post_data['hash'] = u'877728be77b25e0f7d82141d4fff1b22135f5fd251b084ee277f6e6275650bf54df7802679aa30fa5fc9b6ca55394dccfbc3459144b8a840d27fc6ed8f7cd605'
        self.env['payment.transaction'].form_feedback(payumoney_post_data, 'payumoney')
        # check state
        self.assertEqual(tx.state, 'pending', 'PayuMoney: erroneous validation did not put tx into pending state')
