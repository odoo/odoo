# -*- coding: utf-8 -*-

from openerp.addons.payment_acquirer.models.payment_acquirer import ValidationError
from openerp.addons.payment_acquirer.tests.common import PaymentAcquirerCommon
from openerp.addons.payment_acquirer_paypal.controllers.main import PaypalController
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger

from lxml import objectify
# import requests
# import urlparse
import urllib
import urllib2
import urlparse


class PaypalCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(PaypalCommon, self).setUp()
        cr, uid = self.cr, self.uid

        self.base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        model, self.paypal_view_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_acquirer_paypal', 'paypal_acquirer_button')

        # create a new ogone account
        self.paypal_id = self.payment_acquirer.create(
            cr, uid, {
                'name': 'paypal',
                'env': 'test',
                'view_template_id': self.paypal_view_id,
                'paypal_email_id': 'tde+paypal-facilitator@openerp.com',
                'paypal_username': 'tde+paypal-facilitator_api1.openerp.com',
                'paypal_api_enabled': True,
                'paypal_api_username': 'AYf_uBATwly1C72DqE2njwDHmZI25UHcZMwvgvgICLkeQEgutvrhrg6y3KhZ',
                'paypal_api_password': 'EJSDgxC_LuZ9oeG-Ud_oozfiDqqN3mUVLMmzPK71IZA3TM4taicUY2uaJYU1',
            })
        # tde+seller@openerp.com - tde+buyer@openerp.com - tde+buyer-it@openerp.com


class PaypalServer2Server(PaypalCommon):

    def test_00(self):
        cr, uid, context = self.cr, self.uid, {}

        res = self.payment_acquirer._paypal_s2s_get_access_token(cr, uid, [self.paypal_id], context=context)
        print res, res.get('access_token')

        res = self.payment_transaction.paypal_s2s_create(
            cr, uid, {
                'amount': 0.01,
                'acquirer_id': self.paypal_id,
                'currency_id': self.currency_euro_id,
                'reference': 'test_reference',
                'paypal_txn_id': '61E67681CH3238416',
            }, context=context
        )
        print res


class PaypalForm(PaypalCommon):

    def test_00_paypal_acquirer(self):
        cr, uid, context = self.cr, self.uid, {}
        # forgot some mandatory fields: should crash
        with self.assertRaises(except_orm):
            self.payment_acquirer.create(
                cr, uid, {
                    'name': 'paypal',
                    'env': 'test',
                    'view_template_id': self.paypal_view_id,
                    'paypal_email_id': 'tde+paypal-facilitator@openerp.com',
                }, context=context)

        paypal = self.payment_acquirer.browse(self.cr, self.uid, self.paypal_id, None)
        self.assertEqual(paypal.env, 'test', 'test without test env')

    def test_10_paypal_form_render(self):
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
            'return': '%s' % urlparse.urljoin(self.base_url, PaypalController._return_url),
            'notify_url': '%s' % urlparse.urljoin(self.base_url, PaypalController._notify_url),
            'cancel_return': '%s' % urlparse.urljoin(self.base_url, PaypalController._cancel_url),
        }

        # render the button
        res = self.payment_acquirer.render(
            cr, uid, self.paypal_id,
            'test_ref0', 0.01, self.currency_euro,
            partner_id=None,
            partner_values=self.buyer_values,
            context=context)

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
