# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('moneris', "Moneris")], ondelete={'moneris': 'set default'})
    store_id = fields.Char(
        string="Store ID", help="The store solely used to identify the account with Moneris",
        required_if_provider='moneris')
    api_token = fields.Char(
        string="API Token", required_if_provider='moneris', groups='base.group_system')
    checkout_id = fields.Char(
        string="Checkout ID", required_if_provider='moneris', groups='base.group_system')

    # #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'moneris').update({
            'support_tokenization': True,
            'support_manual_capture': 'full_only',
        })

    def _moneris_get_api_url(self):
        """ Moneris Checkout URL for Sending Preload Request """
        req_url, environment = 'https://gatewayt.moneris.com/chktv2/request/request.php', 'qa'
        if self.state == 'enabled':
            req_url, environment = 'https://gateway.moneris.com/chktv2/request/request.php', 'prod'
        return req_url, environment

    def _get_moneris_urls(self, environment):
        """ Moneris Host URL for Sending a Requests """
        if environment == 'prod':
            return {'moneris_request_url': 'https://www3.moneris.com/gateway2/servlet/MpgRequest'}
        else:
            return {'moneris_request_url': 'https://esqa.moneris.com/gateway2/servlet/MpgRequest'}
