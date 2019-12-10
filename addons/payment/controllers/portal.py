# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import logging
from unicodedata import normalize
import psycopg2
import werkzeug

from odoo import http, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, consteq, ustr
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)

class PaymentProcessing(http.Controller):

    @staticmethod
    def remove_payment_transaction(transactions):
        tx_ids_list = request.session.get("__payment_tx_ids__", [])
        if transactions:
            for tx in transactions:
                if tx.id in tx_ids_list:
                    tx_ids_list.remove(tx.id)
        else:
            return False
        request.session["__payment_tx_ids__"] = tx_ids_list
        return True

    @staticmethod
    def add_payment_transaction(transactions):
        if not transactions:
            return False
        tx_ids_list = set(request.session.get("__payment_tx_ids__", [])) | set(transactions.ids)
        request.session["__payment_tx_ids__"] = list(tx_ids_list)
        return True

    @staticmethod
    def get_payment_transaction_ids():
        # return the ids and not the recordset, since we might need to
        # sudo the browse to access all the record
        # I prefer to let the controller chose when to access to payment.transaction using sudo
        return request.session.get("__payment_tx_ids__", [])

    @http.route(['/payment/process'], type="http", auth="public", website=True, sitemap=False)
    def payment_status_page(self, **kwargs):
        # When the customer is redirect to this website page,
        # we retrieve the payment transaction list from his session
        tx_ids_list = self.get_payment_transaction_ids()
        payment_transaction_ids = request.env['payment.transaction'].sudo().browse(tx_ids_list).exists()

        render_ctx = {
            'payment_tx_ids': payment_transaction_ids.ids,
        }
        return request.render("payment.payment_process_page", render_ctx)

    @http.route(['/payment/process/poll'], type="json", auth="public")
    def payment_status_poll(self):
        # retrieve the transactions
        tx_ids_list = self.get_payment_transaction_ids()

        payment_transaction_ids = request.env['payment.transaction'].sudo().search([
            ('id', 'in', list(tx_ids_list)),
            ('date', '>=', (datetime.now() - timedelta(days=1)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
        ])
        if not payment_transaction_ids:
            return {
                'success': False,
                'error': 'no_tx_found',
            }

        processed_tx = payment_transaction_ids.filtered('is_processed')
        self.remove_payment_transaction(processed_tx)

        # create the returned dictionnary
        result = {
            'success': True,
            'transactions': [],
        }
        # populate the returned dictionnary with the transactions data
        for tx in payment_transaction_ids:
            message_to_display = tx.acquirer_id[tx.state + '_msg'] if tx.state in ['done', 'pending', 'cancel'] else None
            tx_info = {
                'reference': tx.reference,
                'state': tx.state,
                'return_url': tx.return_url,
                'is_processed': tx.is_processed,
                'state_message': tx.state_message,
                'message_to_display': message_to_display,
                'amount': tx.amount,
                'currency': tx.currency_id.name,
                'acquirer_provider': tx.acquirer_id.provider,
            }
            tx_info.update(tx._get_processing_info())
            result['transactions'].append(tx_info)

        tx_to_process = payment_transaction_ids.filtered(lambda x: x.state == 'done' and x.is_processed is False)
        try:
            tx_to_process._post_process_after_done()
        except psycopg2.OperationalError as e:
            request.env.cr.rollback()
            result['success'] = False
            result['error'] = "tx_process_retry"
        except Exception as e:
            request.env.cr.rollback()
            result['success'] = False
            result['error'] = str(e)
            _logger.exception("Error while processing transaction(s) %s, exception \"%s\"", tx_to_process.ids, str(e))

        return result

class WebsitePayment(http.Controller):
    @http.route(['/my/payment_method'], type='http', auth="user", website=True)
    def payment_method(self, **kwargs):
        acquirers = list(request.env['payment.acquirer'].search([
            ('state', 'in', ['enabled', 'test']), ('registration_view_template_id', '!=', False),
            ('payment_flow', '=', 's2s'), ('company_id', '=', request.env.company.id)
        ]))
        partner = request.env.user.partner_id
        payment_tokens = partner.payment_token_ids
        payment_tokens |= partner.commercial_partner_id.sudo().payment_token_ids
        return_url = request.params.get('redirect', '/my/payment_method')
        values = {
            'pms': payment_tokens,
            'acquirers': acquirers,
            'error_message': [kwargs['error']] if kwargs.get('error') else False,
            'return_url': return_url,
            'bootstrap_formatting': True,
            'partner_id': partner.id
        }
        return request.render("payment.pay_methods", values)

    @http.route(['/website_payment/pay'], type='http', auth='public', website=True, sitemap=False)
    def pay(self, reference='', order_id=None, amount=False, currency_id=None, acquirer_id=None, partner_id=False, access_token=None, **kw):
        """
        Generic payment page allowing public and logged in users to pay an arbitrary amount.

        In the case of a public user access, we need to ensure that the payment is made anonymously - e.g. it should not be
        possible to pay for a specific partner simply by setting the partner_id GET param to a random id. In the case where
        a partner_id is set, we do an access_token check based on the payment.link.wizard model (since links for specific
        partners should be created from there and there only). Also noteworthy is the filtering of s2s payment methods -
        we don't want to create payment tokens for public users.

        In the case of a logged in user, then we let access rights and security rules do their job.
        """
        env = request.env
        user = env.user.sudo()
        reference = normalize('NFKD', reference).encode('ascii','ignore').decode('utf-8')
        if partner_id and not access_token:
            raise werkzeug.exceptions.NotFound
        if partner_id and access_token:
            token_ok = request.env['payment.link.wizard'].check_token(access_token, int(partner_id), float(amount), int(currency_id))
            if not token_ok:
                raise werkzeug.exceptions.NotFound

        # Default values
        values = {
            'amount': 0.0,
            'currency': user.company_id.currency_id,
        }

        # Check sale order
        if order_id:
            try:
                order_id = int(order_id)
                order = env['sale.order'].browse(order_id)
                values.update({
                    'currency': order.currency_id,
                    'amount': order.amount_total,
                    'order_id': order_id
                })
            except:
                order_id = None

        # Check currency
        if currency_id:
            try:
                currency_id = int(currency_id)
                values['currency'] = env['res.currency'].browse(currency_id)
            except:
                pass

        # Check amount
        if amount:
            try:
                amount = float(amount)
                values['amount'] = amount
            except:
                pass

        # Check reference
        reference_values = order_id and {'sale_order_ids': [(4, order_id)]} or {}
        values['reference'] = env['payment.transaction']._compute_reference(values=reference_values, prefix=reference)

        # Check acquirer
        acquirers = None
        if acquirer_id:
            acquirers = env['payment.acquirer'].browse(int(acquirer_id))
        if not acquirers:
            acquirers = env['payment.acquirer'].search([('state', 'in', ['enabled', 'test']), ('company_id', '=', user.company_id.id)])

        # Check partner
        if not user._is_public():
            # NOTE: this means that if the partner was set in the GET param, it gets overwritten here
            # This is something we want, since security rules are based on the partner - assuming the
            # access_token checked out at the start, this should have no impact on the payment itself
            # existing besides making reconciliation possibly more difficult (if the payment partner is
            # not the same as the invoice partner, for example)
            partner_id = user.partner_id.id
        elif partner_id:
            partner_id = int(partner_id)

        values.update({
            'partner_id': partner_id,
            'bootstrap_formatting': True,
            'error_msg': kw.get('error_msg')
        })

        # s2s mode will always generate a token, which we don't want for public users
        valid_flows = ['form', 's2s'] if not user._is_public() else ['form']
        values['acquirers'] = [acq for acq in acquirers if acq.payment_flow in valid_flows]
        values['pms'] = request.env['payment.token'].search([('acquirer_id', 'in', acquirers.ids)])

        return request.render('payment.pay', values)

    @http.route(['/website_payment/transaction/<string:reference>/<string:amount>/<string:currency_id>',
                '/website_payment/transaction/v2/<string:amount>/<string:currency_id>/<path:reference>',
                '/website_payment/transaction/v2/<string:amount>/<string:currency_id>/<path:reference>/<int:partner_id>'], type='json', auth='public')
    def transaction(self, acquirer_id, reference, amount, currency_id, partner_id=False, **kwargs):
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        order_id = kwargs.get('order_id')

        reference_values = order_id and {'sale_order_ids': [(4, order_id)]} or {}
        reference = request.env['payment.transaction']._compute_reference(values=reference_values, prefix=reference)

        values = {
            'acquirer_id': int(acquirer_id),
            'reference': reference,
            'amount': float(amount),
            'currency_id': int(currency_id),
            'partner_id': partner_id,
            'type': 'form_save' if acquirer.save_token != 'none' and partner_id else 'form',
        }

        if order_id:
            values['sale_order_ids'] = [(6, 0, [order_id])]

        reference_values = order_id and {'sale_order_ids': [(4, order_id)]} or {}
        reference_values.update(acquirer_id=int(acquirer_id))
        values['reference'] = request.env['payment.transaction']._compute_reference(values=reference_values, prefix=reference)
        tx = request.env['payment.transaction'].sudo().with_context(lang=None).create(values)
        secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
        token_str = '%s%s%s' % (tx.id, tx.reference, tx.amount)
        token = hmac.new(secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256).hexdigest()
        tx.return_url = '/website_payment/confirm?tx_id=%d&access_token=%s' % (tx.id, token)

        PaymentProcessing.add_payment_transaction(tx)

        render_values = {
            'partner_id': partner_id,
        }

        return acquirer.sudo().render(tx.reference, float(amount), int(currency_id), values=render_values)

    @http.route(['/website_payment/token/<string:reference>/<string:amount>/<string:currency_id>',
                '/website_payment/token/v2/<string:amount>/<string:currency_id>/<path:reference>',
                '/website_payment/token/v2/<string:amount>/<string:currency_id>/<path:reference>/<int:partner_id>'], type='http', auth='public', website=True)
    def payment_token(self, pm_id, reference, amount, currency_id, partner_id=False, return_url=None, **kwargs):
        token = request.env['payment.token'].browse(int(pm_id))
        order_id = kwargs.get('order_id')

        if not token:
            return request.redirect('/website_payment/pay?error_msg=%s' % _('Cannot setup the payment.'))

        values = {
            'acquirer_id': token.acquirer_id.id,
            'reference': reference,
            'amount': float(amount),
            'currency_id': int(currency_id),
            'partner_id': int(partner_id),
            'payment_token_id': int(pm_id),
            'type': 'server2server',
            'return_url': return_url,
        }

        if order_id:
            values['sale_order_ids'] = [(6, 0, [int(order_id)])]

        tx = request.env['payment.transaction'].sudo().with_context(lang=None).create(values)
        PaymentProcessing.add_payment_transaction(tx)

        try:
            tx.s2s_do_transaction()
            secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
            token_str = '%s%s%s' % (tx.id, tx.reference, tx.amount)
            token = hmac.new(secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256).hexdigest()
            tx.return_url = return_url or '/website_payment/confirm?tx_id=%d&access_token=%s' % (tx.id, token)
        except Exception as e:
            _logger.exception(e)
        return request.redirect('/payment/process')

    @http.route(['/website_payment/confirm'], type='http', auth='public', website=True, sitemap=False)
    def confirm(self, **kw):
        tx_id = int(kw.get('tx_id', 0))
        access_token = kw.get('access_token')
        if tx_id:
            if access_token:
                tx = request.env['payment.transaction'].sudo().browse(tx_id)
                secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
                valid_token_str = '%s%s%s' % (tx.id, tx.reference, tx.amount)
                valid_token = hmac.new(secret.encode('utf-8'), valid_token_str.encode('utf-8'), hashlib.sha256).hexdigest()
                if not consteq(ustr(valid_token), access_token):
                    raise werkzeug.exceptions.NotFound
            else:
                tx = request.env['payment.transaction'].browse(tx_id)
            if tx.state in ['done', 'authorized']:
                status = 'success'
                message = tx.acquirer_id.done_msg
            elif tx.state == 'pending':
                status = 'warning'
                message = tx.acquirer_id.pending_msg
            PaymentProcessing.remove_payment_transaction(tx)
            return request.render('payment.confirm', {'tx': tx, 'status': status, 'message': message})
        else:
            return request.redirect('/my/home')
