# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, _
from odoo.exceptions import UserError

from ..models.l10n_pl_ksef_api import KsefApiService
from ..models.l10n_pl_edi_sign import XadesSigner


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pl_edi_mode = fields.Selection(related='company_id.l10n_pl_edi_mode', readonly=False)
    l10n_pl_edi_certificate = fields.Binary(
        string="KSeF Certificate & Private Key",
        related='company_id.l10n_pl_edi_certificate',
        readonly=False,
    )
    l10n_pl_access_token = fields.Char(string="KSeF Access Token", related='company_id.l10n_pl_access_token', readonly=True, copy=False)

    def _get_ksef_api_service(self):
        return KsefApiService(self.company_id)

    def authenticate_user_for_ksef(self):
        """Orchestrates the entire authentication flow using the service."""
        self.ensure_one()
        ksef_service = self._get_ksef_api_service()
        temp_token, ref_number = None, None

        if self.company_id.l10n_pl_edi_certificate:
            # === XAdES Authentication Flow ===
            if not self.company_id.vat:
                raise UserError(_("The company's VAT number is not set."))

            nip = self.company_id.vat.replace("PL", "")
            challenge_data = ksef_service.get_challenge()
            challenge_code = challenge_data.get('challenge')

            # Use the new utility class for signing
            cert_content = base64.b64decode(self.company_id.l10n_pl_edi_certificate)
            signer = XadesSigner(cert_content)
            signed_xml = signer.sign_authentication_challenge(challenge_code, nip)

            token_data = ksef_service.authenticate_xades(signed_xml)
            temp_token = token_data.get('authenticationToken', {}).get('token')
            ref_number = token_data.get('referenceNumber')

        if not temp_token or not ref_number:
            raise UserError(_("Failed to initiate KSeF authentication."))

        status_data = ksef_service.check_auth_status(ref_number, temp_token)
        if status_data.get('status', {}).get('code') != 200:
            raise UserError(_("KSeF Authentication is still pending or failed."))

        token_data = ksef_service.redeem_token(temp_token)
        access_token = token_data.get('accessToken', {}).get('token')
        refresh_token = token_data.get('refreshToken', {}).get('token')

        if not access_token or not refresh_token:
            raise UserError(_("Failed to retrieve access or refresh tokens."))

        self.company_id.write({
            'l10n_pl_access_token': access_token,
            'l10n_pl_refresh_token': refresh_token,
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}
