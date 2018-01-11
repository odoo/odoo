# -*- coding: utf-8 -*-

from lxml import objectify
import time
import urlparse

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment.tests.common import PaymentAcquirerCommon
from openerp.addons.payment_ogone.controllers.main import OgoneController
from openerp.tools import mute_logger


class OgonePayment(PaymentAcquirerCommon):

    def setUp(self):
        super(OgonePayment, self).setUp()
        cr, uid = self.cr, self.uid
        self.base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')

        # get the adyen account
        model, self.ogone_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_ogone', 'payment_acquirer_ogone')

    def test_10_ogone_form_render(self):
        cr, uid, context = self.cr, self.uid, {}
        # be sure not to do stupid thing
        ogone = self.payment_acquirer.browse(self.cr, self.uid, self.ogone_id, None)
        self.assertEqual(ogone.environment, 'test', 'test without test environment')

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
            'ACCEPTURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._accept_url),
            'DECLINEURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._decline_url),
            'EXCEPTIONURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._exception_url),
            'CANCELURL': '%s' % urlparse.urljoin(self.base_url, OgoneController._cancel_url),
        }

        # render the button
        res = self.payment_acquirer.render(
            cr, uid, self.ogone_id,
            'test_ref0', 0.01, self.currency_euro_id,
            partner_id=None,
            partner_values=self.buyer_values,
            context=context)

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
        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 0.01,
                'acquirer_id': self.ogone_id,
                'currency_id': self.currency_euro_id,
                'reference': 'test_ref0',
                'partner_id': self.buyer_id,
            }, context=context
        )
        # render the button
        res = self.payment_acquirer.render(
            cr, uid, self.ogone_id,
            'should_be_erased', 0.01, self.currency_euro,
            tx_id=tx_id,
            partner_id=None,
            partner_values=self.buyer_values,
            context=context)

        # check form result
        tree = objectify.fromstring(res)
        self.assertEqual(tree.get('action'), 'https://secure.ogone.com/ncol/test/orderstandard.asp', 'ogone: wrong form POST url')
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
        cr, uid, context = self.cr, self.uid, {}
        # be sure not to do stupid thing
        ogone = self.payment_acquirer.browse(self.cr, self.uid, self.ogone_id, None)
        self.assertEqual(ogone.environment, 'test', 'test without test environment')

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
            self.payment_transaction.ogone_form_feedback(cr, uid, ogone_post_data, context=context)

        # create tx
        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 1.95,
                'acquirer_id': self.ogone_id,
                'currency_id': self.currency_euro_id,
                'reference': 'test_ref_2',
                'partner_name': 'Norbert Buyer',
                'partner_country_id': self.country_france_id,
            }, context=context
        )
        # validate it
        self.payment_transaction.ogone_form_feedback(cr, uid, ogone_post_data, context=context)
        # check state
        tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        self.assertEqual(tx.state, 'done', 'ogone: validation did not put tx into done state')
        self.assertEqual(tx.ogone_payid, ogone_post_data.get('PAYID'), 'ogone: validation did not update tx payid')

        # reset tx
        tx.write({'state': 'draft', 'date_validate': False, 'ogone_payid': False})

        # now ogone post is ok: try to modify the SHASIGN
        ogone_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        with self.assertRaises(ValidationError):
            self.payment_transaction.ogone_form_feedback(cr, uid, ogone_post_data, context=context)

        # simulate an error
        ogone_post_data['STATUS'] = 2
        ogone_post_data['SHASIGN'] = 'a4c16bae286317b82edb49188d3399249a784691'
        self.payment_transaction.ogone_form_feedback(cr, uid, ogone_post_data, context=context)
        # check state
        tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        self.assertEqual(tx.state, 'error', 'ogone: erroneous validation did not put tx into error state')

    def test_30_ogone_s2s(self):
        test_ref = 'test_ref_%.15f' % time.time()
        cr, uid, context = self.cr, self.uid, {}
        # be sure not to do stupid thing
        ogone = self.payment_acquirer.browse(self.cr, self.uid, self.ogone_id, None)
        self.assertEqual(ogone.environment, 'test', 'test without test environment')

        # create a new draft tx
        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 0.01,
                'acquirer_id': self.ogone_id,
                'currency_id': self.currency_euro_id,
                'reference': test_ref,
                'partner_id': self.buyer_id,
                'type': 'server2server',
            }, context=context
        )

        # create an alias
        res = self.payment_transaction.ogone_s2s_create_alias(
            cr, uid, tx_id, {
                'expiry_date_mm': '01',
                'expiry_date_yy': '2015',
                'holder_name': 'Norbert Poilu',
                'number': '4000000000000002',
                'brand': 'VISA',
            }, context=context)

        # check an alias is set, containing at least OPENERP
        tx = self.payment_transaction.browse(cr, uid, tx_id, context=context)
        self.assertIn('OPENERP', tx.partner_reference, 'ogone: wrong partner reference after creating an alias')

        res = self.payment_transaction.ogone_s2s_execute(cr, uid, tx_id, {}, context=context)
        # print res


# {
#     'orderID': u'reference',
#     'STATUS': u'9',
#     'CARDNO': u'XXXXXXXXXXXX0002',
#     'PAYID': u'24998692',
#     'CN': u'Norbert Poilu',
#     'NCERROR': u'0',
#     'TRXDATE': u'11/05/13',
#     'IP': u'85.201.233.72',
#     'BRAND': u'VISA',
#     'ACCEPTANCE': u'test123',
#     'currency': u'EUR',
#     'amount': u'1.95',
#     'SHASIGN': u'EFDC56879EF7DE72CCF4B397076B5C9A844CB0FA',
#     'ED': u'0314',
#     'PM': u'CreditCard'
# }
