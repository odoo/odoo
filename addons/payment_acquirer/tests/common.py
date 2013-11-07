# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 20123TODAY OpenERP S.A. <http://www.openerp.com>
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

from openerp.tests import common


class TestPaymentAcquirer(common.TransactionCase):

    def setUp(self):
        super(TestPaymentAcquirer, self).setUp()
        self.payment_acquirer = self.registry('payment.acquirer')
        self.payment_transaction = self.registry('payment.transaction')

        self.currency_euro_id = self.registry('res.currency').search(
            self.cr, self.uid, [('name', '=', 'EUR')], limit=1)[0]
        self.currency_euro = self.registry('res.currency').browse(
            self.cr, self.uid, self.currency_euro_id)
        country_belgium_id = self.registry('res.country').search(
            self.cr, self.uid, [('code', 'like', 'BE')], limit=1)[0]

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
            'country_id': country_belgium_id,
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
                'country_id': country_belgium_id,
            }
        )
