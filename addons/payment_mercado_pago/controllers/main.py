# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial
import logging
import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import float_round

from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.payment_mercado_pago.const import INTEGER_ONLY_CURRENCIES


_logger = logging.getLogger(__name__)


class MercadoPagoController(PaymentPortal):
    _return_url = '/payment/mercado_pago/return'
    _webhook_url = '/payment/mercado_pago/webhook'

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def mercado_pago_return_from_checkout(self, **data):
        """ Process the notification data sent by Mercado Pago after redirection from checkout.

        :param dict data: The notification data.
        """
        # Handle the notification data.
        _logger.info("Handling redirection from Mercado Pago with data:\n%s", pprint.pformat(data))
        if data.get('payment_id') != 'null':
            request.env['payment.transaction'].sudo()._handle_notification_data(
                'mercado_pago', data
            )
        else:  # The customer cancelled the payment by clicking on the return button.
            pass  # Don't try to process this case because the payment id was not provided.

        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(
        f'{_webhook_url}/<reference>', type='http', auth='public', methods=['POST'], csrf=False
    )
    def mercado_pago_webhook(self, reference, **_kwargs):
        """ Process the notification data sent by Mercado Pago to the webhook.

        :param str reference: The transaction reference embedded in the webhook URL.
        :param dict _kwargs: The extra query parameters.
        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Notification received from Mercado Pago with data:\n%s", pprint.pformat(data))

        # Mercado Pago sends two types of asynchronous notifications: webhook notifications and
        # IPNs which are very similar to webhook notifications but are sent later and contain less
        # information. Therefore, we filter the notifications we receive based on the 'action'
        # (type of event) key as it is not populated for IPNs, and we don't want to process the
        # other types of events.
        if data.get('action') in ('payment.created', 'payment.updated'):
            # Handle the notification data.
            try:
                payment_id = data.get('data', {}).get('id')
                request.env['payment.transaction'].sudo()._handle_notification_data(
                    'mercado_pago', {'external_reference': reference, 'payment_id': payment_id}
                )  # Use 'external_reference' as the reference key like in the redirect data.
            except ValidationError:  # Acknowledge the notification to avoid getting spammed.
                _logger.exception("Unable to handle the notification data; skipping to acknowledge")
        return ''  # Acknowledge the notification.

    def _create_transaction(self, amount, currency_id, provider_id, **kwargs):
        """
        Round amounts to integers when paying with Mercado Pago using one of
        the currencies where they deviate from the ISO 4217 standard.
        """
        currency_sudo = request.env['res.currency'].sudo().browse(currency_id)
        if (
            currency_sudo.name not in INTEGER_ONLY_CURRENCIES
            or amount.is_integer()
            or request.env['payment.provider'].sudo().browse(provider_id).code != 'mercado_pago'
        ):
            return super()._create_transaction(
                amount=amount,
                currency_id=currency_id,
                provider_id=provider_id,
                **kwargs,
            )

        # Step 1: decide on a rounding method
        rounding_method = 'HALF-UP'
        if request.env['ir.module.module']._get('account').state == 'installed':
            rounding_sudo = request.env['account.cash.rounding'].sudo().search([
                ('rounding', '=', 1.0),
                ('company_id', '=', request.env.company.id),
            ])
            if len(rounding_sudo) > 1:  # in case of multiple, prefer one referencing Mercado Pago
                mp_rounding = rounding_sudo.filtered_domain([('name', 'ilike', 'Mercado%Pago')])
                rounding_sudo = next(iter(mp_rounding or rounding_sudo))
            rounding_method = rounding_sudo.rounding_method or rounding_method

        float2int = partial(float_round, precision_rounding=1.0, rounding_method=rounding_method)
        document_amounts = {}
        custom_create_values = kwargs.get('custom_create_values', {})

        # Step 2: go over sale orders
        for sale_order_id in (cmd[-1] for cmd in custom_create_values.get('sale_order_ids', [])):
            order_sudo = request.env['sale.order'].sudo().browse(sale_order_id)
            document_amounts[order_sudo] = order_sudo.amount_total
            if order_sudo.amount_total.is_integer():
                continue  # no changes needed
            diff_balance = float2int(order_sudo.amount_total) - order_sudo.amount_total
            biggest_tax_line = max(
                order_sudo.order_line,
                key=lambda sol: (sol.price_tax, sol.price_subtotal)
            )
            if biggest_tax_line.price_tax:
                biggest_tax_line.price_tax += diff_balance
            else:
                biggest_tax_line.price_subtotal += diff_balance

        # Step 3: go over invoices
        for invoice_id in (cmd[-1] for cmd in custom_create_values.get('invoice_ids', [])):
            invoice_sudo = request.env['account.move'].sudo().browse(invoice_id)
            document_amounts[invoice_sudo] = invoice_sudo.amount_total
            if invoice_sudo.amount_total.is_integer():
                continue  # no changes needed
            # create cash rounding if necessary
            if not rounding_sudo:
                rounding_sudo = rounding_sudo.create({
                    'name': f"Mercado Pago: {currency_sudo.name}",
                    'rounding': 1.0,
                    'strategy': 'biggest_tax',
                    'rounding_method': rounding_method,
                    'company_id': request.env.company.id,
                })
            # apply cash rounding to invoice
            invoice_sudo.invoice_cash_rounding_id = rounding_sudo
            invoice_sudo._recompute_cash_rounding_lines()

        # Step 4: decide on new amount
        if currency_sudo.compare_amounts(amount, sum(document_amounts.values())) == 0:
            # if original amount was sum of all totals, new amount should be too
            new_amount = sum(doc.amount_total for doc in document_amounts)
        else:
            new_amount = float2int(amount)

        # Step 5: continue transaction
        return super()._create_transaction(
            amount=round(new_amount, 0),  # sanity round in case of tiny floating point errors
            currency_id=currency_id,
            provider_id=provider_id,
            **kwargs,
        )
