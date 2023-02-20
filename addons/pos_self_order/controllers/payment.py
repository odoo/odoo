# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import urllib.parse
import werkzeug

from odoo import _, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal

from odoo import fields

# TODO: where is the best place to put this function?
def find_amount_to_pay(order_to_pay_sudo):
    if not order_to_pay_sudo:
        # TODO: refactor using odoo logger ??
        print(f"ERROR: order not found")
        # FIXME: this redirect is not working
        return request.redirect(f"pos-self-order")
    order_to_pay_amount = order_to_pay_sudo.read(['amount_total', 'amount_paid'])[0]
    amount_to_pay = order_to_pay_amount.get('amount_total') - order_to_pay_amount.get('amount_paid')
    if amount_to_pay <= 0:
        # TODO: create this page
        return request.redirect(f"pos-self-order")
    return amount_to_pay
    



class PaymentPortal(payment_portal.PaymentPortal):
    @http.route('/pos-self-order/pay/', type='http', methods=['GET', 'POST'], auth='public', website=True, sitemap=False)
    def pos_self_order_pay(self, pos_order_id=None, access_token=None):
        """ Behaves like PaymentPortal.payment_pay but for POS Self Order.

        :param dict kwargs: As the parameters of in payment_pay, with the additional:
            - str pos_order_id: the id of the order to pay
        :return: The rendered payment form
        :rtype: str
        """
        
                
        # TODO: we want the user to not have to login to pay for the order
        # if request.env.user._is_public():
        #     kwargs['partner_id'] = request.env.user.partner_id.id
        #     kwargs['access_token'] = payment_utils.generate_access_token(kwargs['partner_id'], kwargs['amount'], kwargs['currency_id'])
        order_to_pay_sudo = request.env['pos.order'].sudo().search([('pos_reference', '=' , pos_order_id)], limit=1)
        if order_to_pay_sudo.read(['access_token'])[0].get('access_token') != access_token:
            return request.redirect(f"pos-self-order/start")
        # FIXME: when you start the payment process, the payment.transaction record
        # is created before the payment is validated, so it is possible to have a payment.transaction
        # record that is not paid.
        # The problem is when you try to pay again for the same order, the payment.transaction record
        # will have a reference of type concat(initial_reference, '-1') and the logic
        # that checks if the order was correctly paid will fail. (because the reference is not the same)
        kwargs = {
            # 'pos_order_id': pos_order_id,
            'amount': find_amount_to_pay(order_to_pay_sudo),
            'reference': pos_order_id,
            'currency_id': request.env.company.currency_id.id,
        }
        print("paying for order with id: \n", pos_order_id, "\nsum to be paid: ", kwargs['amount'])
        return self.payment_pay(**kwargs)
    
    def _get_payment_page_template_xmlid(self, **kwargs):
        return 'pos_self_order.pay'


    @http.route('/payment/confirmation', type='http', methods=['GET'], auth='public', website=True)
    def payment_confirm(self, tx_id, access_token, **kwargs):
        """ Display the payment confirmation page to the user.

        :param str tx_id: The transaction to confirm, as a `payment.transaction` id
        :param str access_token: The access token used to verify the user
        :param dict kwargs: Optional data. This parameter is not used here
        :raise: werkzeug.exceptions.NotFound if the access token is invalid
        """
        tx_id = self._cast_as_int(tx_id)
        if tx_id:
            tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)
            # Raise an HTTP 404 if the access token is invalid
            if not payment_utils.check_access_token(
                access_token, tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id
            ):
                # Don't leak information about ids.
                raise werkzeug.exceptions.NotFound()
            
            # Stop monitoring the transaction now that it reached a final state.
            PaymentPostProcessing.remove_transactions(tx_sudo)
        
            order_to_pay_sudo = request.env['pos.order'].sudo().search([('pos_reference', '=', tx_sudo.reference)], limit=1)
            
            error_url = f"pos-self-order?pos_id={order_to_pay_sudo.session_id.config_id.id}&table_id={order_to_pay_sudo.table_id.id}&message_to_display=pay_error"
            if tx_sudo.amount < find_amount_to_pay(order_to_pay_sudo):
                return request.redirect(error_url)

            # now that the payment is done, we have to 
            # EDIT THE ORDER TO SET THE STATE TO PAID

            # we have to specify that the order was done using the "Online Payment" payment method
            # for this we will have to see what is the id of the payment method with the name "Online Payment"
            payment_method_sudo = request.env['pos.payment.method'].sudo().search([('name', '=', 'Online Payment')], limit=1) 
            if not payment_method_sudo:
                print("ERROR: You need to create a payment method with the name 'Online Payment' to use this module")
                return request.redirect(error_url)
            payment_method_id = payment_method_sudo[0].id

            order_to_pay_sudo.add_payment({'amount': tx_sudo.amount, 
                                            'payment_date': fields.Datetime.now(), 
                                            'payment_method_id': payment_method_id, 
                                            'card_type': '', 
                                            'cardholder_name': '', 
                                            'transaction_id': tx_sudo.payment_id.name, 
                                            'payment_status': '', 
                                            'ticket': '', 
                                            'pos_order_id': order_to_pay_sudo.id,
                                            'name': False,
                                            })
            order_to_pay_sudo.action_pos_order_paid()
            # now that the order is paid, we have to redirect the user back to the pos self order page
            return request.redirect(f"/pos-self-order?pos_id={order_to_pay_sudo.session_id.config_id.id}&table_id={order_to_pay_sudo.table_id.id}&message_to_display=pay_success")
