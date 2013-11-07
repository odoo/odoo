# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012-TODAY OpenERP S.A. <http://openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.payment_acquirer.controllers.main import OgoneController
from openerp.addons.payment_acquirer.tests.common import TestPaymentAcquirer
from openerp.osv.orm import except_orm

from lxml import objectify
# import requests
# import urlparse


class BasicPayment(TestPaymentAcquirer):

    def test_10_paypal_basic(self):
        pass

    def test_11_paypal_form(self):
        cr, uid = self.cr, self.uid
        context = {}
        base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        # ogone_url = self.payment_acquirer._get_ogone_urls(cr, uid, [ogone_id], None, None)[ogone_id]['ogone_standard_order_url']

        model, paypal_view_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_acquirer', 'paypal_acquirer_button')

        # forgot some mandatory fields: should crash
        with self.assertRaises(except_orm):
            paypal_id = self.payment_acquirer.create(
                cr, uid, {
                    'name': 'paypal',
                    'env': 'test',
                    'view_template_id': paypal_view_id,
                    'paypal_email_id': 'tde+paypal-facilitator@openerp.com',
                }, context=context
            )
        # tde+buyer@openerp.com

        # create a new paypal account
        paypal_id = self.payment_acquirer.create(
            cr, uid, {
                'name': 'paypal',
                'env': 'test',
                'view_template_id': paypal_view_id,
                'paypal_email_id': 'tde+paypal-facilitator@openerp.com',
                'paypal_username': 'tde+paypal-facilitator_api1.openerp.com',
            }, context=context
        )
        # verify acquirer data
        paypal = self.payment_acquirer.browse(cr, uid, paypal_id, context)
        self.assertEqual(paypal.env, 'test', 'test without test env')

        # render the button
        res = self.payment_acquirer.render(
            cr, uid, paypal_id,
            'test_ref0', 0.01, self.currency_euro,
            partner_id=None,
            partner_values=self.buyer_values,
            context=context)
        print res

    #     # check some basic paypal methods
    #     res = self.payment_transaction.validate_paypal_notification(
    #         cr, uid,
    #         'http://localhost/payment?mc_gross=19.95&protection_eligibility=Eligible&address_status=confirmed&payer_id=LPLWNMTBWMFAY&tax=0.00&address_street=1+Main+St&payment_date=20%3A12%3A59+Jan+13%2C+2009+PST&payment_status=Completed&charset=windows-1252&address_zip=95131&first_name=Test&mc_fee=0.88&address_country_code=US&address_name=Test+User&notify_version=2.6&custom=&payer_status=verified&address_country=United+States&address_city=San+Jose&quantity=1&verify_sign=AtkOfCXbDm2hu0ZELryHFjY-Vb7PAUvS6nMXgysbElEn9v-1XcmSoGtf&payer_email=gpmac_1231902590_per%40paypal.com&txn_id=61E67681CH3238416&payment_type=instant&last_name=User&address_state=CA&receiver_email=gpmac_1231902686_biz%40paypal.com&payment_fee=0.88&receiver_id=S8XGHLYDW9T3S&txn_type=express_checkout&item_name=&mc_currency=USD&item_number=&residence_country=US&test_ipn=1&handling_amount=0.00&transaction_subject=&payment_gross=19.95&shipping=0.00')
    #     self.assertEqual(res, False, 'payment: paypal validation on a txn_id that does not exists should return False')

    #     txn_id = self.payment_transaction.create(
    #         cr, uid, {
    #             'amount': 0.01,
    #             'acquirer_id': paypal_id,
    #             'currency_id': currency_id,
    #             'reference': 'test_reference',
    #             'paypal_txn_id': '61E67681CH3238416',
    #         }, context=context
    #     )
    #     res = self.payment_transaction.validate_paypal_notification(
    #         cr, uid,
    #         'http://localhost/payment?mc_gross=19.95&protection_eligibility=Eligible&address_status=confirmed&payer_id=LPLWNMTBWMFAY&tax=0.00&address_street=1+Main+St&payment_date=20%3A12%3A59+Jan+13%2C+2009+PST&payment_status=Completed&charset=windows-1252&address_zip=95131&first_name=Test&mc_fee=0.88&address_country_code=US&address_name=Test+User&notify_version=2.6&custom=&payer_status=verified&address_country=United+States&address_city=San+Jose&quantity=1&verify_sign=AtkOfCXbDm2hu0ZELryHFjY-Vb7PAUvS6nMXgysbElEn9v-1XcmSoGtf&payer_email=gpmac_1231902590_per%40paypal.com&txn_id=61E67681CH3238416&payment_type=instant&last_name=User&address_state=CA&receiver_email=gpmac_1231902686_biz%40paypal.com&payment_fee=0.88&receiver_id=S8XGHLYDW9T3S&txn_type=express_checkout&item_name=&mc_currency=USD&item_number=&residence_country=US&test_ipn=1&handling_amount=0.00&transaction_subject=&payment_gross=19.95&shipping=0.00')
    #     print res

        # # user pays using Paypal
        # resp = self.payment_transaction.create_paypal_command(
        #     cr, uid, cmd='_xclick', parameters={
        #         'business': 'tdelavallee-facilitator@gmail.com',
        #         'amount': 50,
        #         'item_name': 'test_item',
        #         'quantity': 1,
        #         'currency_code': 'USD',
        #         'return': 'http://www.example.com',
        #     })
        # print resp
        # print resp.url
        # print resp.text

        # self.payment_transaction.validate(cr, uid, [tx_id], context=context)

    def test_20_ogone_form(self):
        cr, uid = self.cr, self.uid
        context = {}
        base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        # ogone_url = self.payment_acquirer._get_ogone_urls(cr, uid, [ogone_id], None, None)[ogone_id]['ogone_standard_order_url']

        model, ogone_view_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_acquirer', 'ogone_acquirer_button')

        # create a new ogone account
        ogone_id = self.payment_acquirer.create(
            cr, uid, {
                'name': 'ogone',
                'env': 'test',
                'view_template_id': ogone_view_id,
                'ogone_pspid': 'pinky',
                'ogone_userid': 'OOAPI',
                'ogone_password': 'R!ci/6Nu8a',
                'ogone_shakey_in': 'tINY4Yv14789gUix1130',
                'ogone_shakey_out': 'tINYj885Tfvd4P471464',
            }, context=context
        )
        # verify acquirer data
        ogone = self.payment_acquirer.browse(cr, uid, ogone_id, context)
        self.assertEqual(ogone.env, 'test', 'test without test env')

        form_values = {
            'PSPID': 'pinky',
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
            'SHASIGN': 'ea74bb42d4f25746279cdd44a737aaddc71e7f9f',
            'ACCEPTURL': '%s/%s' % (base_url, OgoneController._accept_url),
            'DECLINEURL': '%s/%s' % (base_url, OgoneController._decline_url),
            'EXCEPTIONURL': '%s/%s' % (base_url, OgoneController._exception_url),
            'CANCELURL': '%s/%s' % (base_url, OgoneController._cancel_url),
        }

        # render the button
        res = self.payment_acquirer.render(
            cr, uid, ogone_id,
            'test_ref0', 0.01, self.currency_euro,
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
                'ogone: wrong value for form: received %s instead of %s' % (form_input.get('value'), form_values[form_input.get('name')])
            )
        # resp = requests.post(tree.get('action'), data=form_values)

        # create a new draft tx
        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 0.01,
                'acquirer_id': ogone_id,
                'currency_id': self.currency_euro_id,
                'reference': 'test_ref0',
                'partner_id': self.buyer_id,
            }, context=context
        )
        # render the button
        res = self.payment_acquirer.render(
            cr, uid, ogone_id,
            'test_ref0', 0.01, self.currency_euro,
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

    def test_21_ogone_s2s(self):
        cr, uid = self.cr, self.uid
        context = {}

        model, ogone_view_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_acquirer', 'ogone_acquirer_button')

        # create a new ogone account
        ogone_id = self.payment_acquirer.create(
            cr, uid, {
                'name': 'ogone',
                'env': 'test',
                'view_template_id': ogone_view_id,
                'ogone_pspid': 'pinky',
                'ogone_userid': 'OOAPI',
                'ogone_password': 'R!ci/6Nu8a',
                'ogone_shakey_in': 'tINY4Yv14789gUix1130',
                'ogone_shakey_out': 'tINYj885Tfvd4P471464',
            }, context=context
        )

        # create a new draft tx
        tx_id = self.payment_transaction.create(
            cr, uid, {
                'amount': 0.01,
                'acquirer_id': ogone_id,
                'currency_id': self.currency_euro_id,
                'reference': 'test_ogone_0',
                'partner_id': self.buyer_id,
                'type': 'server2server',
            }, context=context
        )

        res = self.payment_transaction.ogone_s2s_create_alias(
            cr, uid, tx_id, {
                'expiry_date_mm': '01',
                'expiry_date_yy': '2015',
                'holder_name': 'Norbert Poilu',
                'number': '4000000000000002',
                'brand': 'VISA',
            }, context=context)
        print res

        res = self.payment_transaction.ogone_s2s_execute(cr, uid, tx_id, {}, context=context)
        print res


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
