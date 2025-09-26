# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .dpo_request import execute_dpo_api_request, refresh_dpo_token


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    dpo_tid = fields.Char(string='DPO Terminal ID', help='Enter the unique Terminal ID (TID) of your DPO POS terminal (e.g., XXXXXXXX).')
    dpo_mid = fields.Char(string='DPO Merchant ID', help='Enter the Merchant ID assigned by DPO (e.g., 123456789012).')
    dpo_client_id = fields.Char(string='DPO API Client ID', help='The Client ID provided by DPO for authenticating API requests.')
    dpo_client_secret = fields.Char(string='DPO API Client Secret', help='The Client Secret provided by DPO for secure API access. Keep it confidential.')
    dpo_test_mode = fields.Boolean(string='Enable Test Mode', help='Check this to use DPO’s sandbox environment for testing purposes.')
    dpo_bearer_token = fields.Char(default='Token', help='Bearer token used for authenticating API requests. Automatically refreshed when expired.')
    dpo_allowed_payment_modes = fields.Selection(
        selection=[('card', 'Card'), ('momo', 'Mobile Money')],
        default='card',
        help='Choose allowed payment mode:\nCard - regular card payments\nMobile Money - M-Pesa / Airtel Mobile Money',
    )

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('dpo', 'DPO')]

    # TODO:remove modes
    def _is_write_forbidden(self, fields):
        # Allow the modification of these fields even if a pos_session is open
        whitelisted_fields = {'dpo_bearer_token', 'dpo_allowed_payment_modes'}
        return super()._is_write_forbidden(fields - whitelisted_fields)

    @api.constrains('use_payment_terminal')
    def _validate_dpo_terminal(self):
        # TODO: remove when production api is available
        if any(record.use_payment_terminal == 'dpo' and not record.dpo_test_mode for record in self):
            raise UserError(_('Production mode not implemented yet.'))
        if any(record.use_payment_terminal == 'dpo' and record.company_id.currency_id.name != 'KES' for record in self):
            raise UserError(_('This Payment Terminal is only valid for KES Currency'))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.use_payment_terminal == 'dpo':
                record._validate_dpo_credentials()
        return records

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.use_payment_terminal == 'dpo' and any(k in vals for k in ['dpo_client_id', 'dpo_client_secret', 'dpo_tid', 'dpo_mid']):
                record._validate_dpo_credentials()
        return res

    def _validate_dpo_credentials(self):
        refresh_dpo_token(self)
        response = self.send_dpo_request({}, 'pos-status', 'GET')
        if response.get('errorMessage'):
            raise UserError(_(
                'Invalid Merchant ID & Terminal ID.'
                'Also ensure that the POS terminal device is connected to the internet.',
            ))

    def send_dpo_request(self, data, endpoint, action='POST'):
        if endpoint == 'start-transaction':
            data['transactionType'] = self._get_transaction_type()

        return execute_dpo_api_request(self, data, endpoint, action)

    def _get_transaction_type(self):
        if self.dpo_allowed_payment_modes == 'momo':
            return 'pushPaymentDpoMomoSale'
        return 'pushPaymentSale'
