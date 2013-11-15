# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website


class WebsitePayment(http.Controller):

    @website.route([
        '/payment/paypal/test',
    ], type='http', auth="public")
    def paypal_test(self, **post):
        """ TODO
        """
        cr, uid, context = request.cr, request.uid, request.context
        acquirer_obj = request.registry['payment.acquirer']
        payment_obj = request.registry['payment.transaction']
        currency_obj = request.registry['res.currency']

        paypal_id = acquirer_obj.search(cr, uid, [('name', '=', 'paypal')], limit=1, context=context)[0]

        currency_id = currency_obj.search(cr, uid, [('name', '=', 'EUR')], limit=1, context=context)[0]
        currency = currency_obj.browse(cr, uid, currency_id, context=context)

        paypal_form = acquirer_obj.render(cr, uid, paypal_id, 'reference', 0.01, currency, context=context)
        paypal = acquirer_obj.browse(cr, uid, paypal_id, context=context)

        values = {
            'acquirer': paypal,
            'acquirer_form': paypal_form,
        }
        return request.website.render("website_payment.index_paypal", values)

    @website.route([
        '/payment/ogone/test',
    ], type='http', auth="public")
    def ogone_test(self, **post):
        """ TODO
        """
        cr, uid, context = request.cr, request.uid, request.context
        acquirer_obj = request.registry['payment.acquirer']
        payment_obj = request.registry['payment.transaction']
        currency_obj = request.registry['res.currency']

        ogone_id = acquirer_obj.search(cr, uid, [('name', '=', 'ogone')], limit=1, context=context)[0]
        currency_id = currency_obj.search(cr, uid, [('name', '=', 'EUR')], limit=1, context=context)[0]

        nbr_tx = payment_obj.search(cr, uid, [], count=True, context=context)
        tx_id = payment_obj.create(cr, uid, {
            'reference': 'test_ref_%s' % (nbr_tx),
            'amount': 1.95,
            'currency_id': currency_id,
            'acquirer_id': ogone_id,
            'partner_name': 'Norbert Buyer',
            'partner_email': 'norbert.buyer@example.com',
            'partner_lang': 'fr_FR',
        }, context=context)

        ogone_form = acquirer_obj.render(cr, uid, ogone_id, None, None, None, tx_id=tx_id, context=context)
        ogone = acquirer_obj.browse(cr, uid, ogone_id, context=context)

        values = {
            'acquirer': ogone,
            'acquirer_form': ogone_form,
        }
        return request.website.render("website_payment.index_ogone", values)
