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

from openerp.addons.payment_acquirer.tests.common import PaymentAcquirerCommon
from openerp.osv.orm import except_orm

from lxml import objectify
# import requests
# import urlparse


class BasicPayment(PaymentAcquirerCommon):

    def test_10_paypal_basic(self):
        pass

    def test_11_paypal_form(self):
        cr, uid = self.cr, self.uid
        context = {}
        base_url = self.registry('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        # ogone_url = self.payment_acquirer._get_ogone_urls(cr, uid, [ogone_id], None, None)[ogone_id]['ogone_standard_order_url']

        model, paypal_view_id = self.registry('ir.model.data').get_object_reference(cr, uid, 'payment_acquirer_paypal', 'paypal_acquirer_button')

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
                'paypal_email_id': 'dummy',
                'paypal_username': 'dummy',
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
        # print res

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

# {
#     'protection_eligibility': u'Ineligible',
#     'last_name': u'Poilu',
#     'txn_id': u'08D73520KX778924N',
#     'receiver_email': u'tde+paypal-facilitator@openerp.com',
#     'payment_status': u'Pending',
#     'payment_gross': u'',
#     'tax': u'0.00',
#     'residence_country': u'FR',
#     'address_state': u'Alsace',
#     'payer_status': u'verified',
#     'txn_type': u'web_accept',
#     'address_street': u'Av. de la Pelouse, 87648672 Mayet',
#     'handling_amount': u'0.00',
#     'payment_date': u'03:21:19 Nov 18, 2013 PST',
#     'first_name': u'Norbert',
#     'item_name': u'test_ref_0',
#     'address_country': u'France',
#     'charset': u'windows-1252',
#     'custom': u'',
#     'notify_version': u'3.7',
#     'address_name': u'Norbert Poilu',
#     'pending_reason': u'multi_currency',
#     'item_number': u'test_ref_0',
#     'receiver_id': u'DEG7Z7MYGT6QA',
#     'transaction_subject': u'',
#     'business': u'tde+paypal-facilitator@openerp.com',
#     'test_ipn': u'1',
#     'payer_id': u'VTDKRZQSAHYPS',
#     'verify_sign': u'An5ns1Kso7MWUdW4ErQKJJJ4qi4-AVoiUf-3478q3vrSmqh08IouiYpM',
#     'address_zip': u'75002',
#     'address_country_code': u'FR',
#     'address_city': u'Paris',
#     'address_status': u'unconfirmed',
#     'mc_currency': u'EUR',
#     'shipping': u'0.00',
#     'payer_email': u'tde+buyer@openerp.com',
#     'payment_type': u'instant',
#     'mc_gross': u'1.95',
#     'ipn_track_id': u'866df2ccd444b',
#     'quantity': u'1'
# }
