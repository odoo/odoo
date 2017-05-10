# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request


_logger = logging.getLogger(__name__)


class Payment(http.Controller):

    def _get_invoice_payment_request(self, payment_request_id, token=None, **kw):
        # find payment request for invoice
        env = request.env
        if token:
            return env['account.payment.request'].sudo().search([('access_token', '=', token)], limit=1)
        else:
            return env['account.payment.request'].search([('id', '=', payment_request_id)], limit=1)

    def _print_invoice_pdf(self, id, xml_id):
        # print report as sudo, since it require access to taxes, payment term, ... and portal
        # does not have those access rights.
        pdf = request.env.ref(xml_id).sudo().with_context(set_viewport_size=True).render_qweb_pdf([id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    def _update_payment_status(self, transaction, payment_request, token=None):
        if transaction.state == 'pending':
            payment_request_status = 'pending'
            status = 'warning'
            message = transaction.acquirer_id.pending_msg
        elif transaction.state == 'done':
            payment_request_status = 'paid'
            status = 'success'
            message = transaction.acquirer_id.done_msg
        else:
            payment_request_status = 'open'
            message = None
            status = None
        if payment_request_status != payment_request.state:
            payment_request.write({'state': payment_request_status})
        return {'message': message, 'status': status}

    @http.route(['/payment/<int:payment_request_id>'], type='http', auth="user", website=True)
    def pay_user(self, *args, **kwargs):
        return self.pay(*args, **kwargs)

    @http.route(['/payment/<token>'], type='http', auth='public', website=True)
    def pay(self, payment_request_id=None, token=None, pdf=None, **kwargs):
        payment_request = self._get_invoice_payment_request(payment_request_id, token, **kwargs)
        if not token:
            try:
                payment_request.invoice_id.check_access_rights('read')
                payment_request.invoice_id.check_access_rule('read')
            except AccessError:
                return request.render("payment.403")

        if not payment_request:
            return request.render("payment.403")

        if pdf:
            return self._print_invoice_pdf(payment_request.invoice_id.id, 'account.account_invoices')

        values = {
            'payment_request': payment_request,
            'invoice_pay': True,
        }
        transaction = payment_request.payment_tx_id if payment_request.payment_tx_id else None
        if transaction:
            result = self._update_payment_status(transaction, payment_request, token)
            values.update(result)

        render_values = {
            'return_url': '/payment/%s' % token if token else '/payment/%s' % payment_request_id,
            'partner_id': payment_request.partner_id.id,
            'billing_partner_id': payment_request.partner_id.id,
        }
        values.update(payment_request.with_context(submit_class="btn btn-primary", submit_txt=_('Pay'))._prepare_payment_acquirer(values=render_values))

        return request.render('payment.invoice_pay', values)

    @http.route("/payment/transaction/<int:acquirer_id>", type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id, tx_type='form', token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.
        :param int acquirer_id: id of a payment.acquirer record. If not set the
            user is redirected to the checkout page
        """

        # In case the route is called directly from the JS (as done in Stripe payment method)
        payment_request_id = kwargs.get('payment_request_id')
        access_token = kwargs.get('access_token') if kwargs.get('access_token') != kwargs.get('payment_request_id') else None
        payment_request = self._get_invoice_payment_request(payment_request_id, access_token)

        if not payment_request or acquirer_id is None:
            return request.redirect("/payment/%s" % access_token if access_token else '/payment/%s' % payment_request.id)

        # find an already existing transaction
        transaction = request.env['payment.transaction'].sudo().search([
            ('reference', '=', payment_request.reference),
            ('payment_request_id', '=', payment_request.id)
        ])
        transaction = payment_request._prepare_payment_transaction(acquirer_id, tx_type=tx_type, transaction=transaction, token=token)
        request.session['invoice_tx_id'] = transaction.id

        if token:
            return request.env.ref('payment.payment_token_form').render(dict(tx=transaction), engine='ir.qweb')

        return transaction.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=_('Pay')).sudo().render(
            transaction.reference,
            payment_request.amount_total,
            payment_request.currency_id.id,
            values={
                'return_url': '/payment/%s' % access_token if access_token else '/payment/%s' % payment_request.id,
                'partner_id': payment_request.partner_id.id,
                'billing_partner_id': payment_request.partner_id.id,
            },
        )
