# -*- coding: utf-8 -*-

from openerp.addons.payment_acquirer.models.payment_acquirer import ValidationError
from openerp.addons.payment_acquirer.tests.common import PaymentAcquirerCommon
from openerp.addons.payment_acquirer_adyen.controllers.main import AdyenController
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger

from lxml import objectify
import urlparse


class AdyenCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(AdyenCommon, self).setUp()
        cr, uid = self.cr, self.uid

        self.base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        model, self.paypal_view_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_acquirer_adyen', 'adyen_acquirer_button')

        # create a new ogone account
        self.adyen_id = self.payment_acquirer.create(
            cr, uid, {
                'name': 'adyen',
                'env': 'test',
                'view_template_id': self.paypal_view_id,
                'adyen_merchant_account': 'OpenERP',
                'adyen_skin_code': 'cbqYWvVL',
                'adyen_skin_hmac_key': 'cbqYWvVL',
            })

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


class AdyenServer2Server(AdyenCommon):

    def test_00_tx_management(self):
        cr, uid, context = self.cr, self.uid, {}

        # res = self.payment_acquirer._paypal_s2s_get_access_token(cr, uid, [self.paypal_id], context=context)
        # self.assertTrue(res[self.paypal_id] is not False, 'paypal: did not generate access token')

        # tx_id = self.payment_transaction.s2s_create(
        #     cr, uid, {
        #         'amount': 0.01,
        #         'acquirer_id': self.paypal_id,
        #         'currency_id': self.currency_euro_id,
        #         'reference': 'test_reference',
        #         'partner_id': self.buyer_id,
        #     }, {
        #         'number': self.visa[0][0],
        #         'cvc': self.visa[0][1],
        #         'brand': 'visa',
        #         'expiry_mm': 9,
        #         'expiry_yy': 2015,
        #     }, context=context
        # )

        # tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        # self.assertTrue(tx.paypal_txn_id is not False, 'paypal: txn_id should have been set after s2s request')

        # self.payment_transaction.write(cr, uid, tx_id, {'paypal_txn_id': False}, context=context)


class AdyenForm(AdyenCommon):

    def test_10_adyen_form_render(self):
        cr, uid, context = self.cr, self.uid, {}

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        form_values = {
            'cmd': '_xclick',
            'business': 'tde+paypal-facilitator@openerp.com',
            'item_name': 'test_ref0',
            'item_number': 'test_ref0',
            'first_name': 'Buyer',
            'last_name': 'Norbert',
            'amount': '0.01',
            'currency_code': 'EUR',
            'address1': 'Huge Street 2/543',
            'city': 'Sin City',
            'zip': '1000',
            'country': 'Belgium',
            'email': 'norbert.buyer@example.com',
            'return': '%s' % urlparse.urljoin(self.base_url, AdyenController._return_url),
        }

        # render the button
        res = self.payment_acquirer.render(
            cr, uid, self.adyen_id,
            'test_ref0', 0.01, self.currency_euro,
            partner_id=None,
            partner_values=self.buyer_values,
            context=context)
        print res

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://www.sandbox.paypal.com/cgi-bin/webscr', 'paypal: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'paypal: wrong value for form: received %s instead of %s' % (form_input.get('value'), form_values[form_input.get('name')])
            )

    @mute_logger('openerp.addons.payment_acquirer_paypal.models.paypal', 'ValidationError')
    def test_20_paypal_form_management(self):
        cr, uid, context = self.cr, self.uid, {}

        # typical data posted by paypal after client has successfully paid
        paypal_post_data = {
            'protection_eligibility': u'Ineligible',
            'last_name': u'Poilu',
            'txn_id': u'08D73520KX778924N',
            'receiver_email': u'tde+paypal-facilitator@openerp.com',
            'payment_status': u'Pending',
            'payment_gross': u'',
            'tax': u'0.00',
            'residence_country': u'FR',
            'address_state': u'Alsace',
            'payer_status': u'verified',
            'txn_type': u'web_accept',
            'address_street': u'Av. de la Pelouse, 87648672 Mayet',
            'handling_amount': u'0.00',
            'payment_date': u'03:21:19 Nov 18, 2013 PST',
            'first_name': u'Norbert',
            'item_name': u'test_ref_2',
            'address_country': u'France',
            'charset': u'windows-1252',
            'custom': u'',
            'notify_version': u'3.7',
            'address_name': u'Norbert Poilu',
            'pending_reason': u'multi_currency',
            'item_number': u'test_ref_2',
            'receiver_id': u'DEG7Z7MYGT6QA',
            'transaction_subject': u'',
            'business': u'tde+paypal-facilitator@openerp.com',
            'test_ipn': u'1',
            'payer_id': u'VTDKRZQSAHYPS',
            'verify_sign': u'An5ns1Kso7MWUdW4ErQKJJJ4qi4-AVoiUf-3478q3vrSmqh08IouiYpM',
            'address_zip': u'75002',
            'address_country_code': u'FR',
            'address_city': u'Paris',
            'address_status': u'unconfirmed',
            'mc_currency': u'EUR',
            'shipping': u'0.00',
            'payer_email': u'tde+buyer@openerp.com',
            'payment_type': u'instant',
            'mc_gross': u'1.95',
            'ipn_track_id': u'866df2ccd444b',
            'quantity': u'1'
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.payment_transaction.form_feedback(cr, uid, paypal_post_data, 'paypal', context=context)

        # create tx
        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 1.95,
                'acquirer_id': self.paypal_id,
                'currency_id': self.currency_euro_id,
                'reference': 'test_ref_2',
                'partner_name': 'Norbert Buyer',
            }, context=context
        )
        # validate it
        self.payment_transaction.form_feedback(cr, uid, paypal_post_data, 'paypal', context=context)
        # check
        tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        self.assertEqual(tx.state, 'pending', 'paypal: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.state_message, 'multi_currency', 'paypal: wrong state message after receiving a valid pending notification')
        self.assertEqual(tx.paypal_txn_id, '08D73520KX778924N', 'paypal: wrong txn_id after receiving a valid pending notification')
        self.assertFalse(tx.date_validate, 'paypal: validation date should not be updated whenr receiving pending notification')

        # update tx
        self.payment_transaction.write(cr, uid, [tx_id], {
            'state': 'draft',
            'paypal_txn_id': False,
        }, context=context)
        # update notification from paypal
        paypal_post_data['payment_status'] = 'Completed'
        # validate it
        self.payment_transaction.form_feedback(cr, uid, paypal_post_data, 'paypal', context=context)
        # check
        tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        self.assertEqual(tx.state, 'done', 'paypal: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.paypal_txn_id, '08D73520KX778924N', 'paypal: wrong txn_id after receiving a valid pending notification')
        self.assertEqual(tx.date_validate, '2013-11-18 03:21:19', 'paypal: wrong validation date')

# {'authResult': u'AUTHORISED',
#  'merchantReference': u'SO014',
#  'merchantReturnData': u'return_url=/shop/payment/validate',
#  'merchantSig': u'GaLRO8aMHFaQX3gQ5BVP/YETzeA=',
#  'paymentMethod': u'visa',
#  'pspReference': u'8813859935907337',
#  'shopperLocale': u'en_US',
#  'skinCode': u'cbqYWvVL'}