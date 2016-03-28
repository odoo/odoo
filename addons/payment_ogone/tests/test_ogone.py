# -*- coding: utf-8 -*-

import time
import urlparse
from lxml import objectify

from odoo.tests.common import at_install, post_install
from odoo.tools import mute_logger

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.addons.payment_ogone.controllers.main import OgoneController


@at_install(False)
@post_install(False)
class OgonePayment(PaymentAcquirerCommon):

    def setUp(self):
        super(OgonePayment, self).setUp()
        self.base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        # get the ogone account
        self.ogone = self.env.ref('payment.payment_acquirer_ogone')
        self.Transaction = self.env['payment.transaction']

        self.ogone.write({
            'ogone_pspid': 'odoosell',
            'ogone_userid': 'odoosell',
            'ogone_password': 'odoo123sdu',
            'ogone_shakey_in': '12345678910Aa!@#',
            'ogone_shakey_out': '12345678910Aa!@#',
        })

    def test_10_ogone_form_render(self):
        # be sure not to do stupid thing
        self.assertEqual(self.ogone.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering + shasign
        # ----------------------------------------

        form_values = {
            'PSPID': 'odoosell',
            'ORDERID': 'test_ref0',
            'AMOUNT': '1',
            'CURRENCY': 'EUR',
            'LANGUAGE': 'en_US',
            'CN': 'Norbert Buyer',
            'EMAIL': 'norbert.buyer@example.com',
            'OWNERZIP': '1000',
            'OWNERADDRESS': 'Huge Street 2/543',
            'OWNERCTY': 'BE',
            'OWNERTOWN': 'Sin City',
            'OWNERTELNO': '0032 12 34 56 78',
            'SHASIGN': 'dbe2a1d7527443b62befa74a0d45d0720ce8d2b7',
            'ACCEPTURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._accept_url),
            'DECLINEURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._decline_url),
            'EXCEPTIONURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._exception_url),
            'CANCELURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._cancel_url),
        }

        # render the button
        [res] = self.ogone.render(
            'test_ref0', 0.01, self.currency_euro_id,
            values=self.buyer_values,)

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://secure.ogone.com/ncol/test/orderstandard_utf8.asp', 'ogone: wrong form POST url')
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

        # create a new draft transaction
        self.Transaction.create(
            {
                'amount': 0.01,
                'acquirer_id': self.ogone.id,
                'currency_id': self.currency_euro_id,
                'reference': 'test_ref0',
                'partner_id': self.buyer_id,
            })
        # render the button
        [res] = self.ogone.render(
            'should_be_erased', 0.01, self.currency_euro_id,
            partner_id=None,
            values=self.buyer_values,
        )

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://secure.ogone.com/ncol/test/orderstandard_utf8.asp', 'ogone: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'ogone: wrong value for form input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    @mute_logger('openerp.addons.payment_ogone.models.ogone', 'ValidationError')
    def test_20_ogone_form_management(self):
        # be sure not to do stupid thing
        self.assertEqual(self.ogone.environment, 'test', 'test without test environment')

        # typical data posted by ogone after client has successfully paid
        ogone_post_data = {
            'STATUS': u'5',
            'orderID': u'SORDER014',
            'PAYID': u'52329271',
            'CN': u'Norbert Buyer',
            'NCERROR': u'0',
            'TRXDATE': u'11/20/15',
            'IP': u'180.211.100.3',
            'BRAND': u'VISA',
            'ACCEPTANCE': u'test123',
            'currency': u'USD',
            'amount': u'247',
            'ED': u'0220',
            'SHASIGN': u'0CBB4EBAAB2A741645A4B75DA95A5481D1598C2D',
            'CARDNO': u'XXXXXXXXXXXX1111',
            'return_url': u'/shop/payment/validate',
            'PM': u'CreditCard'
        }

        # should raise error about unknown transaction
        with self.assertRaises(ValidationError):
            self.Transaction.form_feedback(ogone_post_data, 'ogone')

        # create transaction
        transaction = self.Transaction.create({
            'amount': 247,
            'acquirer_id': self.ogone.id,
            'currency_id': self.env['res.currency'].search([('name', '=', 'USD')], limit=1).id,
            'reference': 'SORDER014',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france_id})

        # validate it
        self.env['payment.transaction'].form_feedback(ogone_post_data, 'ogone')

        # check state
        self.assertEqual(transaction.state, 'done', 'ogone: validation did not put transaction into done state')
        self.assertEqual(transaction.acquirer_reference, ogone_post_data.get('PAYID'), 'ogone: validation did not update tx payid')

        # reset transaction
        transaction.write({'state': 'draft', 'date_validate': False, 'acquirer_reference': False})

        # now ogone post is ok: try to modify the SHASIGN
        ogone_post_data['SHASIGN'] = 'be8e9b07ae30d409b45239e20f48f728296f86f9'
        with self.assertRaises(ValidationError):
            self.Transaction.form_feedback(ogone_post_data, 'ogone')

        # simulate an error
        ogone_post_data['STATUS'] = 2
        ogone_post_data['SHASIGN'] = '288dd1325f083915a3d16de54e0eb9227e46f728'
        self.Transaction.form_feedback(ogone_post_data, 'ogone')
        # check state
        self.assertEqual(transaction.state, 'error', 'ogone: erroneous validation did not put tx into error state')

    # s2s method testcase disable because  s2s method not working

    def test_30_ogone_s2s(self):
        test_ref = 'test_ref_%.15f' % time.time()
        # be sure not to do stupid thing
        self.assertEqual(self.ogone.environment, 'test', 'test without test environment')
        #create payment meethod
        payment_method = self.env['payment.method'].create({
            'acquirer_id': self.ogone.id,
            'partner_id': self.buyer_id,
            'cc_number': '4111 1111 1111 1111',
            'cc_expiry': '02 / 26',
            'cc_brand': 'visa',
            'cc_cvc': '111',
            'cc_holder_name': 'test',
        })

        # create a new draft transaction
        transaction = self.Transaction.create(
            {
                'amount': 0.01,
                'acquirer_id': self.ogone.id,
                'currency_id': self.currency_usd.id,
                'reference': test_ref,
                'partner_id': self.buyer_id,
                'type': 'server2server',
                'payment_method_id': payment_method.id,
            })

        transaction.ogone_s2s_execute(transaction)
        # check an alias is set, containing at least ODOO
        self.assertEqual(transaction.state, 'done', 'Ogone: Transcation has been discarded.')
