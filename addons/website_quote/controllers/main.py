# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
import werkzeug
import datetime
import time

from openerp.tools.translate import _
from openerp.addons.website_mail.controllers.main import _message_post_helper


class sale_quote(http.Controller):
    @http.route([
        "/quote/<int:order_id>",
        "/quote/<int:order_id>/<token>"
    ], type='http', auth="public", website=True)
    def view(self, order_id, pdf=None, token=None, message=False, **post):
        # use SUPERUSER_ID allow to access/view order for public user
        # only if he knows the private token
        order = request.registry.get('sale.order').browse(request.cr, token and SUPERUSER_ID or request.uid, order_id, request.context)
        now = time.strftime('%Y-%m-%d')
        dummy, action = request.registry.get('ir.model.data').get_object_reference(request.cr, request.uid, 'sale', 'action_quotations')
        if token:
            if token != order.access_token:
                return request.website.render('website.404')
            # Log only once a day
            if request.session.get('view_quote',False)!=now:
                request.session['view_quote'] = now
                body=_('Quotation viewed by customer')
                _message_post_helper(res_model='sale.order', res_id=order.id, message=body, token=token, token_field="access_token", message_type='notification')
        days = 0
        if order.validity_date:
            days = (datetime.datetime.strptime(order.validity_date, '%Y-%m-%d') - datetime.datetime.now()).days + 1
        if pdf:
            report_obj = request.registry['report']
            pdf = report_obj.get_pdf(request.cr, SUPERUSER_ID, [order_id], 'website_quote.report_quote', data=None, context=dict(request.context, set_viewport_size=True))
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        user = request.registry['res.users'].browse(request.cr, SUPERUSER_ID, request.uid, context=request.context)
        tx_id = request.registry['payment.transaction'].search(request.cr, SUPERUSER_ID, [('reference', '=', order.name)], context=request.context)
        tx = request.registry['payment.transaction'].browse(request.cr, SUPERUSER_ID, tx_id, context=request.context) if tx_id else False
        values = {
            'quotation': order,
            'message': message and int(message) or False,
            'option': bool(filter(lambda x: not x.line_id, order.options)),
            'order_valid': (not order.validity_date) or (now <= order.validity_date),
            'days_valid': days,
            'action': action,
            'breadcrumb': user.partner_id == order.partner_id,
            'tx_id': tx_id,
            'tx_state': tx.state if tx else False,
            'tx_post_msg': tx.acquirer_id.post_msg if tx else False,
            'need_payment': not tx_id and order.state == 'manual',
            'token': token,
        }

        if order.require_payment or (not tx_id and order.state == 'manual'):
            payment_obj = request.registry.get('payment.acquirer')
            acquirer_ids = payment_obj.search(request.cr, SUPERUSER_ID, [('website_published', '=', True), ('company_id', '=', order.company_id.id)], context=request.context)
            values['acquirers'] = list(payment_obj.browse(request.cr, token and SUPERUSER_ID or request.uid, acquirer_ids, context=request.context))
            render_ctx = dict(request.context, submit_class='btn btn-primary', submit_txt=_('Pay & Confirm'))
            for acquirer in values['acquirers']:
                acquirer.button = payment_obj.render(
                    request.cr, SUPERUSER_ID, acquirer.id,
                    order.name,
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    values={
                        'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                        'type': 'form',
                        'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                        'partner_id': order.partner_id.id,
                    },
                    context=render_ctx)
        return request.website.render('website_quote.so_quotation', values)

    @http.route(['/quote/accept'], type='json', auth="public", website=True)
    def accept(self, order_id, token=None, signer=None, sign=None, **post):
        order_obj = request.registry.get('sale.order')
        order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
        if token != order.access_token:
            return request.website.render('website.404')
        if order.require_payment:
            return request.website.render('website.404')
        if order.state != 'sent':
            return False
        attachments=sign and [('signature.png', sign.decode('base64'))] or []
        order_obj.action_confirm(request.cr, SUPERUSER_ID, [order_id], context=request.context)
        message = _('Order signed by %s') % (signer,)
        _message_post_helper(message=message, res_id=order_id, res_model='sale.order', attachments=attachments, **({'token': token, 'token_field': 'access_token'} if token else {}))
        return True

    @http.route(['/quote/<int:order_id>/<token>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, token, **post):
        order_obj = request.registry.get('sale.order')
        order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
        if token != order.access_token:
            return request.website.render('website.404')
        if order.state != 'sent':
            return werkzeug.utils.redirect("/quote/%s/%s?message=4" % (order_id, token))
        request.registry.get('sale.order').action_cancel(request.cr, SUPERUSER_ID, [order_id])
        message = post.get('decline_message')
        if message:
            _message_post_helper(message=message, res_id=order_id, res_model='sale.order', **{'token': token, 'token_field': 'access_token'} if token else {})
        return werkzeug.utils.redirect("/quote/%s/%s?message=2" % (order_id, token))

    @http.route(['/quote/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, token=None, **post):
        order = request.registry.get('sale.order').browse(request.cr, SUPERUSER_ID, int(order_id))
        if token != order.access_token:
            return request.website.render('website.404')
        if order.state not in ('draft','sent'):
            return False
        line_id=int(line_id)
        if unlink:
            request.registry.get('sale.order.line').unlink(request.cr, SUPERUSER_ID, [line_id], context=request.context)
            return False
        number=(remove and -1 or 1)

        order_line_obj = request.registry.get('sale.order.line')
        order_line_val = order_line_obj.read(request.cr, SUPERUSER_ID, [line_id], [], context=request.context)[0]
        quantity = order_line_val['product_uom_qty'] + number
        order_line_obj.write(request.cr, SUPERUSER_ID, [line_id], {'product_uom_qty': (quantity)}, context=request.context)
        return [str(quantity), str(order.amount_total)]

    @http.route(["/quote/template/<model('sale.quote.template'):quote>"], type='http', auth="user", website=True)
    def template_view(self, quote, **post):
        values = { 'template': quote }
        return request.website.render('website_quote.so_template', values)

    @http.route(["/quote/add_line/<int:option_id>/<int:order_id>/<token>"], type='http', auth="public", website=True)
    def add(self, option_id, order_id, token, **post):
        vals = {}
        order = request.registry.get('sale.order').browse(request.cr, SUPERUSER_ID, order_id)
        if token != order.access_token:
            return request.website.render('website.404')
        if order.state not in ['draft', 'sent']:
            return request.website.render('website.http_error', {'status_code': 'Forbidden', 'status_message': _('You cannot add options to a confirmed order.')})
        option_obj = request.registry.get('sale.order.option')
        option = option_obj.browse(request.cr, SUPERUSER_ID, option_id)

        vals = {
            'price_unit': option.price_unit,
            'website_description': option.website_description,
            'name': option.name,
            'order_id': order.id,
            'product_id': option.product_id.id,
            'product_uom_qty': option.quantity,
            'product_uom': option.uom_id.id,
            'discount': option.discount,
        }
        line = request.registry.get('sale.order.line').create(request.cr, SUPERUSER_ID, vals, context=request.context)
        request.registry.get('sale.order.line')._compute_tax_id(request.cr, SUPERUSER_ID, [line], context=request.context)
        option_obj.write(request.cr, SUPERUSER_ID, [option.id], {'line_id': line}, context=request.context)
        return werkzeug.utils.redirect("/quote/%s/%s#pricing" % (order.id, token))

    # note dbo: website_sale code
    @http.route(['/quote/<int:order_id>/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id, order_id):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        cr, uid, context = request.cr, request.uid, request.context
        transaction_obj = request.registry.get('payment.transaction')
        order = request.registry.get('sale.order').browse(cr, SUPERUSER_ID, order_id, context=context)

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/quote/" + str(order_id))

        # find an already existing transaction
        tx_id = transaction_obj.search(cr, SUPERUSER_ID, [('reference', '=', order.name)], context=context)
        tx = transaction_obj.browse(cr, SUPERUSER_ID, tx_id, context=context)
        if tx:
            if tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.write({
                    'acquirer_id': acquirer_id,
                })
            tx_id = tx.id
        else:
            tx_id = transaction_obj.create(cr, SUPERUSER_ID, {
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'reference': order.name,
                'sale_order_id': order.id,
                'callback_eval': "self.env['sale.order']._confirm_online_quote(self.sale_order_id.id, self)"
            }, context=context)
            tx = transaction_obj.browse(cr, SUPERUSER_ID, tx_id, context=context)
            # update quotation
            request.registry['sale.order'].write(
                cr, SUPERUSER_ID, [order.id], {
                    'payment_acquirer_id': acquirer_id,
                    'payment_tx_id': tx_id
                }, context=context)

        # confirm the quotation
        if tx.acquirer_id.auto_confirm == 'at_pay_now':
            request.registry['sale.order'].action_confirm(cr, SUPERUSER_ID, [order.id], context=request.context)

        return tx_id
