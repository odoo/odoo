# -*- coding: utf-8 -*-

from openerp.tests import common


class PaymentAcquirerCommon(common.TransactionCase):

    def setUp(self):
        super(PaymentAcquirerCommon, self).setUp()
        self.payment_acquirer = self.registry('payment.acquirer')
        self.payment_transaction = self.registry('payment.transaction')

        self.currency_euro_id = self.registry('res.currency').search(
            self.cr, self.uid, [('name', '=', 'EUR')], limit=1)[0]
        self.currency_euro = self.registry('res.currency').browse(
            self.cr, self.uid, self.currency_euro_id)
        self.country_belgium_id = self.registry('res.country').search(
            self.cr, self.uid, [('code', 'like', 'BE')], limit=1)[0]
        self.country_france_id = self.registry('res.country').search(
            self.cr, self.uid, [('code', 'like', 'FR')], limit=1)[0]

        # dict partner values
        self.buyer_values = {
            'name': 'Norbert Buyer',
            'lang': 'en_US',
            'email': 'norbert.buyer@example.com',
            'street': 'Huge Street',
            'street2': '2/543',
            'phone': '0032 12 34 56 78',
            'city': 'Sin City',
            'zip': '1000',
            'country_id': self.country_belgium_id,
            'country_name': 'Belgium',
        }

        # test partner
        self.buyer_id = self.registry('res.partner').create(
            self.cr, self.uid, {
                'name': 'Norbert Buyer',
                'lang': 'en_US',
                'email': 'norbert.buyer@example.com',
                'street': 'Huge Street',
                'street2': '2/543',
                'phone': '0032 12 34 56 78',
                'city': 'Sin City',
                'zip': '1000',
                'country_id': self.country_belgium_id,
            }
        )
