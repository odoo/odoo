# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import logging

from odoo import fields, models


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('aps', "Amazon Payment Services")], ondelete={'aps': 'set default'}
    )
    aps_merchant_identifier = fields.Char(
        string="APS Merchant Identifier",
        help="The code of the merchant account to use with this provider.",
        required_if_provider='aps',
    )
    aps_access_code = fields.Char(
        string="APS Access Code",
        help="The access code associated with the merchant account.",
        required_if_provider='aps',
        groups='base.group_system',
    )
    aps_sha_request = fields.Char(
        string="APS SHA Request Phrase",
        required_if_provider='aps',
        groups='base.group_system',
    )
    aps_sha_response = fields.Char(
        string="APS SHA Response Phrase",
        required_if_provider='aps',
        groups='base.group_system',
    )

    #=== BUSINESS METHODS ===#

    def _aps_get_api_url(self):
        if self.state == 'enabled':
            return 'https://checkout.payfort.com/FortAPI/paymentPage'
        else:  # 'test'
            return 'https://sbcheckout.payfort.com/FortAPI/paymentPage'

    def _aps_calculate_signature(self, data, incoming=True):
        """ Compute the signature for the provided data according to the APS documentation.

        :param dict data: The data to sign.
        :param bool incoming: Whether the signature must be generated for an incoming (APS to Odoo)
                              or outgoing (Odoo to APS) communication.
        :return: The calculated signature.
        :rtype: str
        """
        sign_data = ''.join([f'{k}={v}' for k, v in sorted(data.items()) if k != 'signature'])
        key = self.aps_sha_response if incoming else self.aps_sha_request
        signing_string = ''.join([key, sign_data, key])
        return hashlib.sha256(signing_string.encode()).hexdigest()

    def _neutralize(self):
        super()._neutralize()
        self._neutralize_fields('aps', [
            'aps_merchant_identifier',
            'aps_access_code',
            'aps_sha_request',
            'aps_sha_response',
        ])
