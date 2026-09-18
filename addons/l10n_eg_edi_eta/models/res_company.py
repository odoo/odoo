import json
from datetime import datetime, timedelta

from odoo import models, fields
from odoo.addons.l10n_eg_edi_eta.lib.eta_client import ETAClient

ETA_TOKEN_DEFAULT_LIFETIME = 3600
ETA_TOKEN_EXPIRY_MARGIN = 300


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_eg_client_identifier = fields.Char(string="ETA Client ID", groups="base.group_erp_manager")
    l10n_eg_client_secret = fields.Char(string="ETA Client Secret", groups="base.group_erp_manager")
    l10n_eg_edi_api_mode = fields.Selection(
        selection=[('demo', "Demo"), ('preproduction', "Pre-production (Testing)"), ('production', "Production (Live)")],
        string="ETA Invoice Sending Mode",
    )
    l10n_eg_building_no = fields.Char("Building No.", compute='_compute_address', inverse='_inverse_l10n_eg_building_no')
    l10n_eg_edi_eta_access_token = fields.Char(string="ETA Access Token", groups="base.group_erp_manager", readonly=True)
    l10n_eg_edi_eta_token_expiry = fields.Datetime(string="ETA Access Token Expiry", groups="base.group_erp_manager", readonly=True)

    def _get_company_address_field_names(self):
        """Override to add EG specific address fields"""
        return super()._get_company_address_field_names() + ["l10n_eg_building_no"]

    def _inverse_l10n_eg_building_no(self):
        for company in self:
            company.partner_id.l10n_eg_building_no = company.l10n_eg_building_no

    def _get_invoicing_threshold(self):
        return self.env['ir.config_parameter'].sudo().get_float('l10n_eg_edi_eta.invoicing_threshold', default=150000.0)

    def _l10n_eg_edi_eta_get_access_token(self):
        """
        Fetches access token from the company if it is still valid, otherwise it will request a new one from ETA.
        returns: access_token, error_message
        """
        self.ensure_one()
        self_sudo = self.sudo()
        if (
            self_sudo.l10n_eg_edi_eta_access_token
            and self_sudo.l10n_eg_edi_eta_token_expiry
            and self_sudo.l10n_eg_edi_eta_token_expiry > datetime.now() + timedelta(seconds=60)
        ):
            return self_sudo.l10n_eg_edi_eta_access_token, ""
        return self_sudo._l10n_eg_eta_fetch_access_token()

    def _l10n_eg_eta_fetch_access_token(self):
        user = self.l10n_eg_client_identifier
        secret = self.l10n_eg_client_secret
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        body = {'grant_type': 'client_credentials', 'client_id': user, 'client_secret': secret}

        client = ETAClient(is_production=self.l10n_eg_edi_api_mode == 'production')

        content = client.get_access_token(
            body=body,
            headers=headers,
        )

        data = json.loads(content)
        breakpoint()
        if error := data.get('error'):
            return "", data.get('error_description') or error
        try:
            expires_in = int(data['expires_in'])
        except (TypeError, ValueError):
            return "", self.env._("Invalid expires_in value received from ETA API")
        self.sudo().write({
            'l10n_eg_edi_eta_access_token': data.get('access_token'),
            'l10n_eg_edi_eta_token_expiry': fields.Datetime.add(
                fields.Datetime.now(),
                seconds=max(expires_in - ETA_TOKEN_EXPIRY_MARGIN, 0),
            ),
        })
        return data.get('access_token'), ""
