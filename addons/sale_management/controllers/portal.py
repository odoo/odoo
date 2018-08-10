# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.mail import _message_post_helper


class CustomerPortal(CustomerPortal):

    def _portal_quote_user_can_accept(self, order):
        if order.sale_order_template_id:
            return order.require_signature
        else:
            return order.company_id.portal_confirmation_sign or order.company_id.portal_confirmation_pay

    @http.route(['/my/quotes/accept'], type='json', auth="public", website=True)
    def portal_quote_accept(self, res_id, access_token=None, partner_name=None, signature=None):
        try:
            order_sudo = self._document_check_access('sale.order', res_id, access_token=access_token)
        except AccessError:
            return {'error': _('Invalid order')}
        if order_sudo.state != 'sent':
            return {'error': _('Order is not in a state requiring customer validation.')}

        if not self._portal_quote_user_can_accept(order_sudo):
            return {'error': _('Operation not allowed')}
        if not signature:
            return {'error': _('Signature is missing.')}

        success_message = _('Your order has been signed but still needs to be paid to be confirmed.')

        if not order_sudo.has_to_be_paid():
            order_sudo.action_confirm()
            success_message = _('Your order has been confirmed.')

        order_sudo.signature = signature
        order_sudo.signed_by = partner_name

        pdf = request.env.ref('sale.action_report_saleorder').sudo().render_qweb_pdf([order_sudo.id])[0]
        _message_post_helper(
            res_model='sale.order',
            res_id=order_sudo.id,
            message=_('Order signed by %s') % (partner_name,),
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            **({'token': access_token} if access_token else {}))

        return {
            'success': success_message,
            'redirect_url': order_sudo.get_portal_url(),
        }

    @http.route(['/my/orders/<int:order_id>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, access_token=None, **post):
        try:
            self._document_check_access('sale.order', order_id, access_token=access_token)
        except AccessError:
            return request.redirect('/my')

        Order = request.env['sale.order'].sudo().browse(order_id)
        if Order.state != 'sent':
            return request.redirect(Order.get_portal_url() + "&message=4")
        Order.action_cancel()
        message = post.get('decline_message')
        if message:
            _message_post_helper(message=message, res_id=order_id, res_model='sale.order', **{'token': access_token} if access_token else {})
        return request.redirect(Order.get_portal_url())

    @http.route(['/my/orders/<int:order_id>/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, token=None, **post):
        try:
            self._document_check_access('sale.order', order_id, access_token=token)
        except AccessError:
            return request.redirect('/my')

        # todo seb make sure line belongs to order
        Order = request.env['sale.order'].sudo().browse(int(order_id))
        if Order.state not in ('draft', 'sent'):
            return False
        OrderLine = request.env['sale.order.line'].sudo().browse(int(line_id))
        if unlink:
            OrderLine.unlink()
            return False
        number = -1 if remove else 1
        quantity = OrderLine.product_uom_qty + number
        OrderLine.write({'product_uom_qty': quantity})
        return [str(quantity), str(Order.amount_total)]

    @http.route(["/my/orders/<int:order_id>/add_option/<int:option_id>"], type='http', auth="public", website=True)
    def add(self, order_id, option_id, access_token=None, **post):
        try:
            self._document_check_access('sale.order', order_id, access_token=access_token)
        except AccessError:
            return request.redirect('/my')

        option_sudo = self.env['sale.order.option'].sudo().browse(option_id)

        if order_id != option_sudo.order_id:
            return request.redirect(option_sudo.order_id.get_portal_url())

        option_sudo.add_option_to_order()

        return request.redirect(option_sudo.order_id.get_portal_url() + "#details")

    # note dbo: website_sale code
    @http.route(['/my/orders/<int:order_id>/transaction/'], type='json', auth="public", website=True)
    def payment_transaction_token(self, acquirer_id, order_id, save_token=False, access_token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return False

        try:
            acquirer_id = int(acquirer_id)
        except:
            return False

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order or not order.order_line:
            return False

        # Create transaction
        vals = {
            'acquirer_id': acquirer_id,
            'type': order._get_payment_type(),
        }

        transaction = order._create_payment_transaction(vals)

        return transaction.render_sale_button(
            order,
            order.get_portal_url(),
            submit_txt=_('Pay & Confirm'),
            render_values={
                'type': order._get_payment_type(),
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
            }
        )

    @http.route('/my/orders/<int:order_id>/transaction/token', type='http', auth='public', website=True)
    def payment_token(self, order_id, pm_id=None, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order:
            return request.redirect("/my/orders")
        if not order.order_line or pm_id is None:
            return request.redirect(order.get_portal_url())

        # try to convert pm_id into an integer, if it doesn't work redirect the user to the quote
        try:
            pm_id = int(pm_id)
        except ValueError:
            return request.redirect(order.get_portal_url())

        # Create transaction
        vals = {
            'payment_token_id': pm_id,
            'type': 'server2server',
        }

        order._create_payment_transaction(vals)

        return request.redirect(order.get_portal_url())
