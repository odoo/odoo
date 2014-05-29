# -*- coding: utf-8 -*-

from lxml import objectify
import urlparse

import openerp
from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment.tests.common import PaymentAcquirerCommon
from openerp.addons.payment_buckaroo.controllers.main import BuckarooController
from openerp.tools import mute_logger


@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(False)
class BuckarooCommon(PaymentAcquirerCommon):

    def setUp(self):
        super(BuckarooCommon, self).setUp()
        cr, uid = self.cr, self.uid
        self.base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')

        # get the buckaroo account
        model, self.buckaroo_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_buckaroo', 'payment_acquirer_buckaroo')


@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(False)
class BuckarooForm(BuckarooCommon):

    def test_10_Buckaroo_form_render(self):
        cr, uid, context = self.cr, self.uid, {}
        # be sure not to do stupid things
        buckaroo = self.payment_acquirer.browse(self.cr, self.uid, self.buckaroo_id, None)
        self.assertEqual(buckaroo.environment, 'test', 'test without test environment')

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        form_values = {
            'add_returndata': None,
            'Brq_websitekey': buckaroo.brq_websitekey,
            'Brq_amount': '2240.0',
            'Brq_currency': 'EUR',
            'Brq_invoicenumber': 'SO004',
            'Brq_signature': '1b8c10074c622d965272a91a9e88b5b3777d2474',  # update me
            'brq_test': 'True',
            'Brq_return': '%s' % urlparse.urljoin(self.base_url, BuckarooController._return_url),
            'Brq_returncancel': '%s' % urlparse.urljoin(self.base_url, BuckarooController._cancel_url),
            'Brq_returnerror': '%s' % urlparse.urljoin(self.base_url, BuckarooController._exception_url),
            'Brq_returnreject': '%s' % urlparse.urljoin(self.base_url, BuckarooController._reject_url),
            'Brq_culture': 'en-US',
        }

        # render the button
        res = self.payment_acquirer.render(
            cr, uid, self.buckaroo_id,
            'SO004', 2240.0, self.currency_euro_id,
            partner_id=None,
            partner_values=self.buyer_values,
            context=context)

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://testcheckout.buckaroo.nl/html/', 'Buckaroo: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'Buckaroo: wrong value for input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

        # ----------------------------------------
        # Test2: button using tx + validation
        # ----------------------------------------

        # create a new draft tx
        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 2240.0,
                'acquirer_id': self.buckaroo_id,
                'currency_id': self.currency_euro_id,
                'reference': 'SO004',
                'partner_id': self.buyer_id,
            }, context=context
        )

        # render the button
        res = self.payment_acquirer.render(
            cr, uid, self.buckaroo_id,
            'should_be_erased', 2240.0, self.currency_euro,
            tx_id=tx_id,
            partner_id=None,
            partner_values=self.buyer_values,
            context=context)

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://testcheckout.buckaroo.nl/html/', 'Buckaroo: wrong form POST url')
        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue
            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'Buckaroo: wrong value for form input %s: received %s instead of %s' % (form_input.get('name'), form_input.get('value'), form_values[form_input.get('name')])
            )

    @mute_logger('openerp.addons.payment_buckaroo.models.buckaroo', 'ValidationError')
    def test_20_buckaroo_form_management(self):
        cr, uid, context = self.cr, self.uid, {}
        # be sure not to do stupid thing
        buckaroo = self.payment_acquirer.browse(self.cr, self.uid, self.buckaroo_id, None)
        self.assertEqual(buckaroo.environment, 'test', 'test without test environment')

        # typical data posted by buckaroo after client has successfully paid
        buckaroo_post_data = {
            'BRQ_RETURNDATA': u'',
            'BRQ_AMOUNT': u'2240.00',
            'BRQ_CURRENCY': u'EUR',
            'BRQ_CUSTOMER_NAME': u'Jan de Tester',
            'BRQ_INVOICENUMBER': u'SO004',
            'BRQ_PAYMENT': u'573311D081B04069BD6336001611DBD4',
            'BRQ_PAYMENT_METHOD': u'paypal',
            'BRQ_SERVICE_PAYPAL_PAYERCOUNTRY': u'NL',
            'BRQ_SERVICE_PAYPAL_PAYEREMAIL': u'fhe@openerp.com',
            'BRQ_SERVICE_PAYPAL_PAYERFIRSTNAME': u'Jan',
            'BRQ_SERVICE_PAYPAL_PAYERLASTNAME': u'Tester',
            'BRQ_SERVICE_PAYPAL_PAYERMIDDLENAME': u'de',
            'BRQ_SERVICE_PAYPAL_PAYERSTATUS': u'verified',
            'BRQ_SIGNATURE': u'175d82dd53a02bad393fee32cb1eafa3b6fbbd91',
            'BRQ_STATUSCODE': u'190',
            'BRQ_STATUSCODE_DETAIL': u'S001',
            'BRQ_STATUSMESSAGE': u'Transaction successfully processed',
            'BRQ_TEST': u'true',
            'BRQ_TIMESTAMP': u'2014-05-08 12:41:21',
            'BRQ_TRANSACTIONS': u'D6106678E1D54EEB8093F5B3AC42EA7B',
            'BRQ_WEBSITEKEY': u'5xTGyGyPyl',
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.payment_transaction.form_feedback(cr, uid, buckaroo_post_data, 'buckaroo', context=context)

        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 2240.0,
                'acquirer_id': self.buckaroo_id,
                'currency_id': self.currency_euro_id,
                'reference': 'SO004',
                'partner_name': 'Norbert Buyer',
                'partner_country_id': self.country_france_id,
            }, context=context
        )
        # validate it
        self.payment_transaction.form_feedback(cr, uid, buckaroo_post_data, 'buckaroo', context=context)
        # check state
        tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        self.assertEqual(tx.state, 'done', 'Buckaroo: validation did not put tx into done state')
        self.assertEqual(tx.buckaroo_txnid, buckaroo_post_data.get('BRQ_TRANSACTIONS'), 'Buckaroo: validation did not update tx payid')

        # reset tx
        tx.write({'state': 'draft', 'date_validate': False, 'buckaroo_txnid': False})

        # now buckaroo post is ok: try to modify the SHASIGN
        buckaroo_post_data['BRQ_SIGNATURE'] = '54d928810e343acf5fb0c3ee75fd747ff159ef7a'
        with self.assertRaises(ValidationError):
            self.payment_transaction.form_feedback(cr, uid, buckaroo_post_data, 'buckaroo', context=context)

        # simulate an error
        buckaroo_post_data['BRQ_STATUSCODE'] = 2
        buckaroo_post_data['BRQ_SIGNATURE'] = '4164b52adb1e6a2221d3d8a39d8c3e18a9ecb90b'
        self.payment_transaction.form_feedback(cr, uid, buckaroo_post_data, 'buckaroo', context=context)
        # check state
        tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        self.assertEqual(tx.state, 'error', 'Buckaroo: erroneous validation did not put tx into error state')
