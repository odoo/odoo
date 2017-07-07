# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound, Forbidden

from odoo import fields, http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


def _special_access_object(res_model, res_id, token='', token_field=''):
    record = request.env[res_model].browse(res_id).sudo()
    if token and record and getattr(record, token_field, None) and consteq(getattr(record, token_field), token):
        return True
    return False


def _message_post_helper(res_model='', res_id=None, message='', token='', token_field='token', nosubscribe=True, **kw):
    """ Generic chatter function, allowing to write on *any* object that inherits mail.thread.
        If a token is specified, all logged in users will be able to write a message regardless
        of access rights; if the user is the public user, the message will be posted under the name
        of the partner_id of the object (or the public user if there is no partner_id on the object).

        :param string res_model: model name of the object
        :param int res_id: id of the object
        :param string message: content of the message

        optional keywords arguments:
        :param string token: access token if the object's model uses some kind of public access
                             using tokens (usually a uuid4) to bypass access rules
        :param string token_field: name of the field that contains the token on the object (defaults to 'token')
        :param bool nosubscribe: set False if you want the partner to be set as follower of the object when posting (default to True)

        The rest of the kwargs are passed on to message_post()
    """
    record = request.env[res_model].browse(res_id)
    author_id = request.env.user.partner_id.id if request.env.user.partner_id else False
    if token_field and token:
        access_as_sudo = _special_access_object(res_model, res_id, token=token, token_field=token_field)
        if access_as_sudo:
            record = record.sudo()
            if request.env.user == request.env.ref('base.public_user'):
                author_id = record.partner_id.id if hasattr(record, 'partner_id') else author_id
            else:
                if not author_id:
                    raise NotFound()
        else:
            raise Forbidden()
    kw.pop('csrf_token', None)
    return record.with_context(mail_create_nosubscribe=nosubscribe).message_post(
        body=message,
        message_type=kw.pop('message_type', "comment"),
        subtype=kw.pop('subtype', "mt_comment"),
        author_id=author_id,
        **kw)


class Payment(http.Controller):

    def _get_invoice_payment_request(self, payment_request_id, token=None):
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

    @http.route("/invoice/report/html", type='json', auth="public", website=True)
    def html_report(self, payment_request_id=None, token=None, **kwargs):
        # the real invoice report (displayed in HTML format)
        access_token = token if token != payment_request_id else None
        payment_request = self._get_invoice_payment_request(payment_request_id, access_token)
        return request.env.ref('account.account_invoices').sudo().render_qweb_html([payment_request.invoice_id.id])[0]

    @http.route(['/payment/<int:payment_request_id>'], type='http', auth="user", website=True)
    def pay_user(self, *args, **kwargs):
        return self.pay(*args, **kwargs)

    @http.route(['/payment/<token>'], type='http', auth='public', website=True)
    def pay(self, payment_request_id=None, token=None, pdf=None, **kwargs):
        payment_request = self._get_invoice_payment_request(payment_request_id, token)
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

        # Log only once a day
        now = fields.Date.today()
        if payment_request and request.session.get('view_invoice') != now and request.env.user.share:
            request.session['view_invoice'] = now
            invoice = payment_request.invoice_id
            body = _('Invoice viewed by customer')
            _message_post_helper(
                res_model='account.invoice',
                res_id=invoice.id,
                message=body,
                token=token,
                token_field="access_token",
                message_type='notification',
                subtype="mail.mt_note",
                partner_ids=invoice.user_id.sudo().partner_id.ids)

        values = {
            'payment_request': payment_request,
            'token': token,
            'sign_modal_for_invoice': True,
            'call_url': '/payment/%s/transaction' % payment_request.id
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

    @http.route("/payment/<int:payment_request_id>/transaction/<int:acquirer_id>", type='json', auth="public", website=True)
    def payment_transaction(self, payment_request_id, acquirer_id, tx_type='form', token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.
        :param int acquirer_id: id of a payment.acquirer record. If not set the
            user is redirected to the checkout page
        """

        # In case the route is called directly from the JS (as done in Stripe payment method)
        access_token = kwargs.get('access_token')
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
            payment_request.invoice_id.currency_id.id,
            values={
                'return_url': '/payment/%s' % access_token if access_token else '/payment/%s' % payment_request.id,
                'partner_id': payment_request.partner_id.id,
                'billing_partner_id': payment_request.partner_id.id,
            },
        )
