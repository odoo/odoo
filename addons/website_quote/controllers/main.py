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

from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
import werkzeug
import datetime
import time

from openerp.tools.translate import _

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
                self.__message_post(body, order_id, type='comment')
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
            'need_payment': not tx_id and order.state == 'manual'
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
                    partner_id=order.partner_id.id,
                    tx_values={
                        'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                        'type': 'form',
                        'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.')
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
        attachments=sign and [('signature.png', sign.decode('base64'))] or []
        order_obj.action_button_confirm(request.cr, SUPERUSER_ID, [order_id], context=request.context)
        message = _('Order signed by %s') % (signer,)
        self.__message_post(message, order_id, type='comment', subtype='mt_comment', attachments=attachments)
        return True

    @http.route(['/quote/<int:order_id>/<token>/decline'], type='http', auth="public", website=True)
    def decline(self, order_id, token, **post):
        order_obj = request.registry.get('sale.order')
        order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
        if token != order.access_token:
            return request.website.render('website.404')
        request.registry.get('sale.order').action_cancel(request.cr, SUPERUSER_ID, [order_id])
        message = post.get('decline_message')
        if message:
            self.__message_post(message, order_id, type='comment', subtype='mt_comment')
        return werkzeug.utils.redirect("/quote/%s/%s?message=2" % (order_id, token))

    @http.route(['/quote/<int:order_id>/<token>/post'], type='http', auth="public", website=True)
    def post(self, order_id, token, **post):
        # use SUPERUSER_ID allow to access/view order for public user
        order_obj = request.registry.get('sale.order')
        order = order_obj.browse(request.cr, SUPERUSER_ID, order_id)
        message = post.get('comment')
        if token != order.access_token:
            return request.website.render('website.404')
        if message:
            self.__message_post(message, order_id, type='comment', subtype='mt_comment')
        return werkzeug.utils.redirect("/quote/%s/%s?message=1" % (order_id, token))

    def __message_post(self, message, order_id, type='comment', subtype=False, attachments=[]):
        request.session.body =  message
        cr, uid, context = request.cr, request.uid, request.context
        user = request.registry['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        if 'body' in request.session and request.session.body:
            request.registry.get('sale.order').message_post(cr, SUPERUSER_ID, order_id,
                    body=request.session.body,
                    type=type,
                    subtype=subtype,
                    author_id=user.partner_id.id,
                    context=context,
                    attachments=attachments
                )
            request.session.body = False
        return True

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

        res = request.registry.get('sale.order.line').product_id_change(request.cr, SUPERUSER_ID, order_id,
            False, option.product_id.id, option.quantity, option.uom_id.id, option.quantity, option.uom_id.id,
            option.name, order.partner_id.id, False, True, time.strftime('%Y-%m-%d'),
            False, order.fiscal_position.id, True, request.context)
        vals = res.get('value', {})
        if 'tax_id' in vals:
            vals['tax_id'] = [(6, 0, vals['tax_id'])]

        vals.update({
            'price_unit': option.price_unit,
            'website_description': option.website_description,
            'name': option.name,
            'order_id': order.id,
            'product_id' : option.product_id.id,
            'product_uos_qty': option.quantity,
            'product_uos': option.uom_id.id,
            'product_uom_qty': option.quantity,
            'product_uom': option.uom_id.id,
            'discount': option.discount,
        })
        line = request.registry.get('sale.order.line').create(request.cr, SUPERUSER_ID, vals, context=request.context)
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
                'partner_country_id': order.partner_id.country_id.id,
                'reference': order.name,
                'sale_order_id': order.id,
                's2s_cb_eval': "self.env['sale.order']._confirm_online_quote(self.sale_order_id.id, self)"
            }, context=context)
            tx = transaction_obj.browse(cr, SUPERUSER_ID, tx_id, context=context)

        # confirm the quotation
        if tx.acquirer_id.auto_confirm == 'at_pay_now':
            request.registry['sale.order'].action_button_confirm(cr, SUPERUSER_ID, [order.id], context=request.context)

        return tx_id
