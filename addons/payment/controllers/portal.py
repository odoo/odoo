# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2

from odoo import http, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
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
            message_to_display = tx.acquirer_id[tx.state + '_msg'] if tx.state in ['done', 'pending', 'cancel', 'error'] else None
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
            ('website_published', '=', True), ('registration_view_template_id', '!=', False),
            ('payment_flow', '=', 's2s'), ('company_id', '=', request.env.user.company_id.id)
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
    def pay(self, reference='', order_id=None, amount=False, currency_id=None, acquirer_id=None, **kw):
        env = request.env
        user = env.user.sudo()

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
            acquirers = env['payment.acquirer'].search([('website_published', '=', True), ('company_id', '=', user.company_id.id)])

        # Check partner
        partner_id = user.partner_id.id if not user._is_public() else False

        values.update({
            'partner_id': partner_id,
            'bootstrap_formatting': True,
            'error_msg': kw.get('error_msg')
        })

        values['acquirers'] = [acq for acq in acquirers if acq.payment_flow in ['form', 's2s']]
        values['pms'] = request.env['payment.token'].search([('acquirer_id', 'in', acquirers.filtered(lambda x: x.payment_flow == 's2s').ids)])

        return request.render('payment.pay', values)

    @http.route(['/website_payment/transaction/<string:reference>/<string:amount>/<string:currency_id>',
                '/website_payment/transaction/v2/<string:amount>/<string:currency_id>/<path:reference>',], type='json', auth='public')
    def transaction(self, acquirer_id, reference, amount, currency_id, **kwargs):
        partner_id = request.env.user.partner_id.id if not request.env.user._is_public() else False
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
        tx.return_url = '/website_payment/confirm?tx_id=%d' % tx.id

        PaymentProcessing.add_payment_transaction(tx)

        render_values = {
            'partner_id': partner_id,
        }

        return acquirer.sudo().render(tx.reference, float(amount), int(currency_id), values=render_values)

    @http.route(['/website_payment/token/<string:reference>/<string:amount>/<string:currency_id>',
                '/website_payment/token/v2/<string:amount>/<string:currency_id>/<path:reference>'], type='http', auth='public', website=True)
    def payment_token(self, pm_id, reference, amount, currency_id, return_url=None, **kwargs):
        token = request.env['payment.token'].browse(int(pm_id))
        order_id = kwargs.get('order_id')

        if not token:
            return request.redirect('/website_payment/pay?error_msg=%s' % _('Cannot setup the payment.'))

        partner_id = request.env.user.partner_id.id if not request.env.user._is_public() else False

        values = {
            'acquirer_id': token.acquirer_id.id,
            'reference': reference,
            'amount': float(amount),
            'currency_id': int(currency_id),
            'partner_id': partner_id,
            'payment_token_id': pm_id,
            'type': 'form_save' if token.acquirer_id.save_token != 'none' and partner_id else 'form',
            'return_url': return_url,
        }

        if order_id:
            values['sale_order_ids'] = [(6, 0, [order_id])]

        tx = request.env['payment.transaction'].sudo().with_context(lang=None).create(values)
        PaymentProcessing.add_payment_transaction(tx)

        try:
            res = tx.s2s_do_transaction()
            tx.return_url = return_url or '/website_payment/confirm?tx_id=%d' % tx.id
            return request.redirect('/payment/process')
        except Exception as e:
            return request.redirect('/payment/process')

    @http.route(['/website_payment/confirm'], type='http', auth='public', website=True, sitemap=False)
    def confirm(self, **kw):
        tx_id = int(kw.get('tx_id', 0))
        if tx_id:
            tx = request.env['payment.transaction'].browse(tx_id)
            if tx.state in ['done', 'authorized']:
                status = 'success'
                message = tx.acquirer_id.done_msg
            elif tx.state == 'pending':
                status = 'warning'
                message = tx.acquirer_id.pending_msg
            else:
                status = 'danger'
                message = tx.acquirer_id.error_msg
            PaymentProcessing.remove_payment_transaction(tx)
            return request.render('payment.confirm', {'tx': tx, 'status': status, 'message': message})
        else:
            return request.redirect('/my/home')
