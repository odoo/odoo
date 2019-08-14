# -*- coding: utf-8 -*-

from lxml import objectify
import time

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_ingenico.controllers.main import OgoneController
from werkzeug import urls

from odoo.tools import mute_logger


class OgonePayment(PaymentAcquirerCommon):

    def setUp(self):
        super(OgonePayment, self).setUp()

        self.ogone = self.env.ref('payment.payment_acquirer_ogone')
        self.ogone.write({
            'ogone_pspid': 'dummy',
            'ogone_userid': 'dummy',
            'ogone_password': 'dummy',
            'ogone_shakey_in': 'dummy',
            'ogone_shakey_out': 'dummy',
            'state': 'test',
        })

    def test_10_ogone_form_render(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # be sure not to do stupid thing
        self.assertEqual(self.ogone.state, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering + shasign
        # ----------------------------------------

        form_values = {
            'PSPID': 'dummy',
            'ORDERID': 'test_ref0',
            'AMOUNT': '1',
            'CURRENCY': 'EUR',
            'LANGUAGE': 'en_US',
            'CN': 'Norbert Buyer',
            'EMAIL': 'norbert.buyer@example.com',
            'OWNERZIP': '1000',
            'OWNERADDRESS': 'Huge Street 2/543',
            'OWNERCTY': 'Belgium',
            'OWNERTOWN': 'Sin City',
            'OWNERTELNO': '0032 12 34 56 78',
            'SHASIGN': '815f67b8ff70d234ffcf437c13a9fa7f807044cc',
            'ACCEPTURL': urls.url_join(base_url, OgoneController._accept_url),
            'DECLINEURL': urls.url_join(base_url, OgoneController._decline_url),
            'EXCEPTIONURL': urls.url_join(base_url, OgoneController._exception_url),
            'CANCELURL': urls.url_join(base_url, OgoneController._cancel_url),
        }

        # render the button
        res = self.ogone.render(
            'test_ref0', 0.01, self.currency_euro.id,
            partner_id=None,
            partner_values=self.buyer_values)

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://secure.ogone.com/ncol/test/orderstandard.asp', 'ogone: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'ogone: wrong value for input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

        # ----------------------------------------
        # Test2: button using tx + validation
        # ----------------------------------------

        # create a new draft tx
        tx = self.env['payment.transaction'].create({
            'amount': 0.01,
            'acquirer_id': self.ogone.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref0',
            'partner_id': self.buyer_id})
        # render the button
        res = self.ogone.render(
            'should_be_erased', 0.01, self.currency_euro,
            tx_id=tx.id,
            partner_id=None,
            partner_values=self.buyer_values)

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://secure.ogone.com/ncol/test/orderstandard.asp', 'ogone: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'ingenico: wrong value for form input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    @mute_logger('odoo.addons.payment_ingenico.models.payment', 'ValidationError')
    def test_20_ogone_form_management(self):
        # be sure not to do stupid thing
        self.assertEqual(self.ogone.state, 'test', 'test without test environment')

        # typical data posted by ogone after client has successfully paid
        ogone_post_data = {
            'orderID': u'test_ref_2',
            'STATUS': u'9',
            'CARDNO': u'XXXXXXXXXXXX0002',
            'PAYID': u'25381582',
            'CN': u'Norbert Buyer',
            'NCERROR': u'0',
            'TRXDATE': u'11/15/13',
            'IP': u'85.201.233.72',
            'BRAND': u'VISA',
            'ACCEPTANCE': u'test123',
            'currency': u'EUR',
            'amount': u'1.95',
            'SHASIGN': u'7B7B0ED9CBC4A85543A9073374589033A62A05A5',
            'ED': u'0315',
            'PM': u'CreditCard'
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction'].form_feedback(ogone_post_data)

        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.ogone.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_2-1',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})
        # validate it
        tx.form_feedback(ogone_post_data)
        # check state
        self.assertEqual(tx.state, 'done', 'ogone: validation did not put tx into done state')
        self.assertEqual(tx.ogone_payid, ogone_post_data.get('PAYID'), 'ogone: validation did not update tx payid')

        # reset tx
        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.ogone.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_2-2',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # now ogone post is ok: try to modify the SHASIGN
        ogone_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        with self.assertRaises(ValidationError):
            tx.form_feedback(ogone_post_data)

        # simulate an error
        ogone_post_data['STATUS'] = 2
        ogone_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        tx.form_feedback(ogone_post_data)
        # check state
        self.assertEqual(tx.state, 'cancel', 'ogone: erroneous validation did not put tx into error state')

    def test_30_ogone_s2s(self):
        test_ref = 'test_ref_%.15f' % time.time()
        # be sure not to do stupid thing
        self.assertEqual(self.ogone.state, 'test', 'test without test environment')

        # create a new draft tx
        tx = self.env['payment.transaction'].create({
            'amount': 0.01,
            'acquirer_id': self.ogone.id,
            'currency_id': self.currency_euro.id,
            'reference': test_ref,
            'partner_id': self.buyer_id,
            'type': 'server2server',
        })

        # create an alias
        res = tx.ogone_s2s_create_alias({
            'expiry_date_mm': '01',
            'expiry_date_yy': '2015',
            'holder_name': 'Norbert Poilu',
            'number': '4000000000000002',
            'brand': 'VISA'})

        res = tx.ogone_s2s_execute({})
