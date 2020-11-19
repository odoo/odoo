# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _accept_url = '/payment/ogone/test/accept'
    _decline_url = '/payment/test/ogonedecline'
    _exception_url = '/payment/test/ogone/exception'
    _cancel_url = '/payment/ogone/test/cancel'
    _fleckcheckout_url = '/payment/ogone/flexchekout/feedback'

    @http.route('/payment/ogone/payment_setup', type='json', auth='public')
    def payment_setup(
            self, acquirer_id, amount=None, currency_id=None, partner_id=None, **data
    ):
        """
            Setup the Ogone iframe used with the FlexCheckout API.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param float|None amount: The transaction amount
        :param int|None currency_id: The transaction currency, as a `res.currency` id
        :param int|None partner_id: The partner making the transaction, as a `res.partner` id
        :param
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id)
        currency = request.env['res.currency'].browse(currency_id)
        partner_sudo = partner_id and request.env['res.partner'].browse(partner_id).sudo()
        partner_country_code = partner_sudo and partner_sudo.country_id.code
        lang_code = request.context.get('lang', 'en-US')
        shopper_reference = partner_sudo and f'ODOO_PARTNER_{partner_sudo.id}'
        form_data = {
            'amount': amount,
            'currency': currency,
            'countryCode': partner_country_code,
            'partner_lang': lang_code,  # IETF language tag (e.g.: 'fr-BE')
            'partner_name': partner_sudo.name,
            'reference': shopper_reference,
            'partner_id': partner_sudo.id,
            'currency_id': currency_id,
            'param_plus': data
        }
        return {'ogone_iframe_url': acquirer_sudo._ogone_setup_iframe(form_data), 'acquirer_id': acquirer_id}

    @http.route(['/payment/ogone/flexchekout/feedback', '/payment/ogone/flexchekout/final'],
                type='http', auth='public', csrf=False, method=['GET', 'POST'],
                website=True)
    def ogone_iframe_feedback(self, **kwargs):
        """
            Handle both redirection from Ingenico in the iframe
                First after the FlexcheckoutAPI has created the Alias
                Secondly Once the send_payment_request has had the 3DS verification.
        """

        _logger.info('Ogone: entering form_feedback with post data %s', pprint.pformat(kwargs))  # debug
        return request.render("payment_ogone.ogone_feedback", kwargs)

    @http.route(['/payment/ogone/payments'], type='json', auth='public', csrf=False)
    def ogone_process_payments(self, **kwargs):
        """ Make a payment request and handle the response.
        :return: The JSON-formatted content of the response
        :rtype: dict
        """

        # fixme this in _get_tx_from_feedback_data
        acquirer_id = kwargs.get('acquirer_id')
        reference = kwargs.get('reference')
        ogone_values = kwargs.get('ogone_values')
        partner_id = kwargs.get('partner_id')
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id)
        print(kwargs)
        kwargs['ogone_values']['acquirer_id'] = acquirer_id
        kwargs['ogone_values']['partner_id'] = partner_id
        kwargs['ogone_values']['BROWSERACCEPTHEADER'] = request.httprequest.headers.environ['HTTP_ACCEPT']
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data('ogone', kwargs)
        token_id = tx_sudo.token_id
        if token_id:
            tx_sudo._send_payment_request()
            return {'tx_status': tx_sudo.state, 'html_3ds': tx_sudo.ogone_html_3ds,
                    'ogone_user_error': tx_sudo.ogone_user_error}
        else:
            return {'status': _("The transaction could not be performed")}

    # ARJ FIXME: REMOVE LATER
    @http.route('/payment/ogone/test/<state>/<int:debug>', type='http', auth='public', website=True)
    def ogone_test(self, state, debug):
        import random
        import string
        if state == 'success':
            amount = random.randint(1, 1000)
        elif state == 'uncertain':
            amount = 9999
        elif state == 'fail':
            amount = random.randint(9001, 15000)
        letters = string.ascii_lowercase
        reference = 'ARJ' + ''.join(random.choice(letters) for letter in range(10))
        currency_id = 7
        debug_str = '' if not debug else "&debug=assets"
        return werkzeug.utils.redirect(
            f"/website_payment/pay?amount={amount}&currency_id={currency_id}&reference={reference}{debug_str}")

    @http.route([
        '/payment/ogone/accept', '/payment/ogone/test/accept',
        '/payment/ogone/decline', '/payment/ogone/test/decline',
        '/payment/ogone/exception', '/payment/ogone/test/exception',
        '/payment/ogone/cancel', '/payment/ogone/test/cancel',
    ], type='http', auth='public', csrf=False, method=['GET', 'POST'])
    def ogone_transaction_feedback(self, **post):
        """ Handle redirection from Ingenico (GET) and s2s notification (POST/GET) """
        # arj fixme: We could avoid this redirect and hanle everything here with our template
        # arj fixme: by adding a route to /payment/ogone/flexchekout/feedback
        _logger.info('Ogone: entering s2s feedback with post data %s', pprint.pformat(post))
        request.env['payment.transaction'].sudo()._handle_feedback_data('ogone', post)
        return werkzeug.utils.redirect("/payment/ogone/flexchekout/final")
