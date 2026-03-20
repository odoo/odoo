# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from datetime import datetime, timedelta
from odoo.addons.l10n_vn_edi_viettel.models.account_move import _l10n_vn_edi_send_request


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_vn_edi_username = fields.Char(
        string='SInvoice Username',
        groups='base.group_system',
    )
    l10n_vn_edi_password = fields.Char(
        string='SInvoice Password',
        groups='base.group_system',
    )
    l10n_vn_edi_token = fields.Char(
        string='SInvoice Access Token',
        groups='base.group_system',
        readonly=True,
    )
    l10n_vn_edi_token_expiry = fields.Datetime(
        string='SInvoice Access Token Expiration Date',
        groups='base.group_system',
        readonly=True,
    )
    l10n_vn_edi_symbol_id = fields.Many2one(
        comodel_name='l10n_vn_edi_viettel.sinvoice.symbol',
        string='Default Symbol',
        help='If set, this symbol will be used as the default symbol for all invoices of this company.',
    )

    def _l10n_vn_edi_get_credentials_company(self):
        """ The company holding the credentials could be one of the parent companies.
        We need to ensure that:
            - We use the credentials of the parent company, if no credentials are set on the child one.
            - We store the access token on the appropriate company, based on which holds the credentials.
        """
        if self.l10n_vn_edi_username and self.l10n_vn_edi_password:
            return self

        return self.sudo().parent_ids.filtered(
            lambda c: c.l10n_vn_edi_username and c.l10n_vn_edi_password
        )[-1:]

    def _l10n_vn_edi_get_access_token(self):
        """ Return an access token to be used to contact the API. Either take a valid stored one or get a new one. """
        self.ensure_one()
        credentials_company = self._l10n_vn_edi_get_credentials_company()
        # First, check if we have a token stored and if it is still valid.
        if credentials_company.l10n_vn_edi_token and credentials_company.l10n_vn_edi_token_expiry > datetime.now():
            return credentials_company.l10n_vn_edi_token, ""

        data = {'username': credentials_company.l10n_vn_edi_username, 'password': credentials_company.l10n_vn_edi_password}
        request_response, error_message = _l10n_vn_edi_send_request(
            method='POST',
            url='https://api-vinvoice.viettel.vn/auth/login',  # This one is special and uses another base address.
            json_data=data
        )
        if error_message:
            return "", error_message
        if 'access_token' not in request_response:  # Just in case something else go wrong and it's missing the token
            return "", _('Connection to the API failed, please try again later.')

        access_token = request_response['access_token']

        try:
            access_token_expiry = datetime.now() + timedelta(seconds=int(request_response['expires_in']))
        except ValueError:  # Simple security measure in case we don't get the expected format in the response.
            return "", _('Error while parsing API answer. Please try again later.')

        # Tokens are valid for 5 minutes. Storing it helps reduce api calls and speed up things a little bit.
        credentials_company.write({
            'l10n_vn_edi_token': access_token,
            'l10n_vn_edi_token_expiry': access_token_expiry,
        })

        return request_response['access_token'], ""
