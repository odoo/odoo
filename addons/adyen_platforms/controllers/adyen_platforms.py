# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from pprint import pformat

from odoo import http
from odoo.http import request

from odoo.addons.adyen_platforms.util import odoo_payments_proxy_control

_logger = logging.getLogger(__name__)


class AdyenPlatformsController(http.Controller):

    @http.route('/adyen_platforms/create_account', type='http', auth='user', website=True)
    def adyen_platforms_create_account(self, creation_token):
        request.session['adyen_creation_token'] = creation_token
        return request.redirect('/web?#action=adyen_platforms.adyen_account_action_create')

    @odoo_payments_proxy_control
    @http.route('/adyen_platforms/account_notification', type='json', auth='public', csrf=False)
    def adyen_platforms_notification(self):
        data = request.jsonrequest
        _logger.debug('Account notification received: %s', pformat(data))

        account = request.env['adyen.account'].sudo().search([('adyen_uuid', '=', data['adyen_uuid'])])
        if not account:
            _logger.error('Received notification for non-existing account: %s', data['adyen_uuid'])
            return

        account.with_context(update_from_adyen=True)._handle_notification(data)

    @odoo_payments_proxy_control
    @http.route('/adyen_platforms/transaction_notification', type='json', auth='public', csrf=False)
    def adyen_transaction_notification(self):
        data = request.jsonrequest
        _logger.debug('Transaction notification received: %s', pformat(data))

        account = request.env['adyen.account'].sudo().search([('adyen_uuid', '=', data['adyen_uuid'])])
        if not account:
            _logger.error('Received notification for non-existing account: %s', data['adyen_uuid'])
            return

        request.env['adyen.transaction'].sudo()._handle_notification(data)
