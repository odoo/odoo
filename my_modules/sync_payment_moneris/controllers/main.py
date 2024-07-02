# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests
import json

from werkzeug import urls

from odoo import _, http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal

_logger = logging.getLogger(__name__)


class PaymentPortal(payment_portal.PaymentPortal):

    @http.route('/my/payment_method', type='http', methods=['GET'], auth='user', website=True)
    def payment_method(self, **kwargs):
        """ Display the form to manage payment methods.

        :param dict kwargs: Optional data. This parameter is not used here
        :return: The rendered manage form
        :rtype: str
        """
        partner_sudo = request.env.user.partner_id  # env.user is always sudoed

        # Select all the payment methods and tokens that match the payment context.
        providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            request.env.company.id,
            partner_sudo.id,
            0.,  # There is no amount to pay with validation transactions.
            force_tokenization=True,
            is_validation=True,
            **kwargs,
        )  # In sudo mode to read the fields of providers and partner (if logged out).
        #### Added Code for Remove Moneris Payment Method ####
        moneris_provider_ids = request.env['payment.provider'].sudo().search([('code', '=', 'moneris')])
        if moneris_provider_ids:
            providers_sudo -= moneris_provider_ids
        ######################################################

        payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            providers_sudo.ids,
            partner_sudo.id,
            force_tokenization=True,
        )  # In sudo mode to read the fields of providers.
        tokens_sudo = request.env['payment.token'].sudo()._get_available_tokens(
            None, partner_sudo.id, is_validation=True
        )  # In sudo mode to read the commercial partner's and providers' fields.

        access_token = payment_utils.generate_access_token(partner_sudo.id, None, None)

        payment_form_values = {
            'mode': 'validation',
            'allow_token_selection': False,
            'allow_token_deletion': True,
        }
        payment_context = {
            'reference_prefix': payment_utils.singularize_reference_prefix(prefix='V'),
            'partner_id': partner_sudo.id,
            'providers_sudo': providers_sudo,
            'payment_methods_sudo': payment_methods_sudo,
            'tokens_sudo': tokens_sudo,
            'transaction_route': '/payment/transaction',
            'landing_route': '/my/payment_method',
            'access_token': access_token,
        }
        rendering_context = {
            **payment_form_values,
            **payment_context,
            **self._get_extra_payment_form_values(**kwargs),
        }
        return request.render('payment.payment_methods', rendering_context)


class MonerisController(http.Controller):

    def create_moneris_preload_request(self, provider, model_id, tx_id=None):
        """
        """
        req_url, environment = provider._moneris_get_api_url()
        tax_amount = ((model_id.amount_tax * 100) / model_id.amount_untaxed)

        line_items = []
        if model_id._name == 'sale.order':
            for line in model_id.order_line.filtered(lambda x: x.product_id):
                # amount_including_tax = (line.price_tax / line.product_uom_qty) + line.price_unit
                # create line item
                line_items.append({
                    'url': '',
                    'description': line.product_id.name if (line.price_subtotal >= 0 and line.product_uom_qty > 0.0) else line.product_id.name + " (The product price is negative, so the amount is deducted from the Subtotal)",
                    'product_code': line.product_id.default_code,
                    'unit_cost': abs(round(line.price_unit, 2)),
                    'quantity': str(abs(int(line.product_uom_qty))),
                })
        elif model_id._name == 'account.move':
            for line in model_id.invoice_line_ids.filtered(lambda x: x.product_id):
                # create line item
                line_items.append({
                    'url': '',
                    'description': line.product_id.name if (line.price_subtotal >= 0 and line.quantity > 0.0) else line.product_id.name + " (The product price is negative, so the amount is deducted from the Subtotal)",
                    'product_code': line.product_id.default_code,
                    'unit_cost': abs(round(line.price_unit, 2)),
                    'quantity': str(abs(int(line.quantity))),
                })
        partner_id = model_id.partner_id
        partner_shipping_id = model_id.partner_shipping_id or model_id.partner_id
        partner_billing_id = model_id.partner_invoice_id if model_id._name == 'sale.order' else model_id.partner_id

        if partner_id.is_company:
            split_name = '', partner_id.name
        else:
            split_name = payment_utils.split_partner_name(partner_id.name)

        if tx_id.partner_id and tx_id.partner_id.customer_id:
            customer_id = tx_id.partner_id.customer_id
        else:
            customer_id = tx_id.partner_id._get_moneris_customer_id('CAN_')
            tx_id.partner_id.customer_id = customer_id

        data = {
            "store_id": provider.store_id,
            "api_token": provider.api_token,
            "checkout_id": provider.checkout_id,
            "txn_total": str("%.2f" % tx_id.amount) if tx_id else (model_id.amount_residual if model_id._name == 'account.move' else str("%.2f" % model_id.amount_total)),
            "environment": environment,
            "action": "preload",
            "ask_cvv": "Y",
            "order_no": tx_id.reference if tx_id and tx_id.reference else model_id.name,
            "cust_id": customer_id,
            "dynamic_descriptor": "paymoneris",
            "language": "en",
            "cart": {
                "items": line_items,
                "subtotal": str("%.2f" % model_id.amount_untaxed) or "0.00",
                    "tax": {
                    "amount": str("%.2f" % model_id.amount_tax) or "0.00",
                    "description": "Taxes",
                    "rate": str("%.3f" % tax_amount) if model_id.amount_untaxed and model_id.amount_tax and model_id.amount_tax > 0 else "0.00"
                }
            },
            "contact_details":{
                "first_name": split_name[0] or '',
                "last_name": split_name[1] or '',
                "email": partner_id.email or '',
                "phone": partner_id.phone or '',
            },
            "shipping_details":{
                "address_1": partner_shipping_id.street or '',
                "address_2": partner_shipping_id.street2 or '',
                "city": partner_shipping_id.city or '',
                "province": partner_shipping_id.state_id.code or '',
                "country": partner_shipping_id.country_id.code or '',
                "postal_code": partner_shipping_id.zip or ''
            },
            "billing_details":{
                "address_1": partner_billing_id.street or '',
                "address_2": partner_billing_id.street2 or '',
                "city": partner_billing_id.city or '',
                "province": partner_billing_id.state_id.code or '',
                "country": partner_billing_id.country_id.code or '',
                "postal_code": partner_billing_id.zip or ''
            }
        }
        req = requests.post(url=req_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        response = req.json()
        if response.get('response') and response.get('response').get('success') == 'true':
            return response.get('response')
        elif response.get('response') and response.get('response').get('success') == 'false':
            return response.get('response')
        return True

    @http.route('/payment/moneris/payment_details', type='json', auth='public')
    def moneris_payment_methods(self, code, provider_id, amount, currency_id, partner_id, reference):
        """ Query the available payment methods based on the transaction context.

        :param char code: The transaction amount
        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :param int processingValues: The transaction currency, as a `res.currency` id
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        currency = request.env['res.currency'].browse(currency_id)
        partner_sudo = partner_id and request.env['res.partner'].sudo().browse(partner_id).exists()
        lang_code = (request.context.get('lang') or 'en-US').replace('_', '-')
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)], limit=1)

        model_id = False
        model_reference = reference.rsplit('-',1)
        if 'x' in model_reference:
            model_reference = model_reference.rsplit('x',1)
        if model_reference:
            model_id = request.env['sale.order'].sudo().search([('name', '=', model_reference[0])], limit=1)
            if not model_id:
                model_id = request.env['account.move'].sudo().search([('name', '=', model_reference[0])], limit=1)

        response = self.create_moneris_preload_request(provider=provider_sudo, model_id=model_id, tx_id=tx_sudo)
        _logger.info("paymentMethods request response:\n%s", pprint.pformat(response))
        if response and isinstance(response, dict):
            if response.get('success') == 'true':
                base_url = provider_sudo.get_base_url()
                req_url, environment = provider_sudo._moneris_get_api_url()
                response.update({
                    'moneris_state': provider_sudo.state,
                    'environment': environment,
                    'redirect_uri': '/payment/moneris/return/%s' % (tx_sudo.id),
                    'page_loaded': urls.url_join(base_url, '/payment/moneris/return?tx_id=%s' % (tx_sudo.id)),
                    'cancel_transaction': urls.url_join(base_url, '/payment/moneris/return?tx_id=%s' % (tx_sudo.id)),
                    'error_event': urls.url_join(base_url, '/payment/moneris/return?tx_id=%s' % (tx_sudo.id)),
                    'payment_receipt': urls.url_join(base_url, '/payment/moneris/return?tx_id=%s' % (tx_sudo.id)),
                    'payment_complete': urls.url_join(base_url, '/payment/moneris/return?tx_id=%s' % (tx_sudo.id))
                })
                return response
            elif response.get('success') == 'false':
                error = response.get('error')
                response.update({'error_message': error})
                return response
        return {}

    @http.route(['/payment/moneris/return/<int:tx_id>'], type='json', auth='public', csrf=False)
    def moneris_payment(self, tx_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction.
        """
        _logger.info('Moneris: POST %s : %s', tx_id, pprint.pformat(post))
        if tx_id and post:
            tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)
            provider_id = tx_sudo.provider_id
            req_url, environment = provider_id._moneris_get_api_url()
            response = post.get('response') and json.loads(post.get('response'))
            data = {
                'store_id': provider_id.store_id,
                'api_token': provider_id.api_token,
                'checkout_id': provider_id.checkout_id,
                'ticket': response.get('ticket'),
                'environment': environment,
                'action': 'receipt',
            }
            receipt_req = requests.post(url=req_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
            receipt_response = receipt_req.json()
            receipt_response.update({'save_token': post.get('save_token', False)})
            _logger.info('Moneris: entering form_feedback with post receipt response data %s', pprint.pformat(receipt_response))

            # Handle the notification data
            tx_sudo._handle_notification_data('moneris', receipt_response)
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            return {'return_url': urls.url_join(base_url, "/payment/status")}

