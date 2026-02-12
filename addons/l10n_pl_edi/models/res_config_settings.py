import base64
import stdnum.pl.nip

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService
from odoo.addons.l10n_pl_edi.tools.xades_signer import XadesSigner


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pl_edi_certificate = fields.Many2one(
        'certificate.certificate',
        "KSeF Certificate",
        compute='_compute_l10n_pl_edi_certificate',
        inverse='_set_l10n_pl_edi_certificate',
        readonly=False,
    )
    l10n_pl_edi_access_token = fields.Char(
        "KSeF Access Token",
        related='company_id.l10n_pl_edi_access_token',
        readonly=True,
    )
    l10n_pl_edi_register = fields.Boolean(
        "Allow KSeF integration",
        related='company_id.l10n_pl_edi_register',
        readonly=False,
    )

    @api.depends('company_id')
    def _compute_l10n_pl_edi_certificate(self):
        for config in self:
            config.l10n_pl_edi_certificate = config.company_id.l10n_pl_edi_certificate

    @api.onchange('l10n_pl_edi_register')
    def _l10n_pl_edi_reset(self):
        # UI-only feedback; do not write to company here
        for config in self:
            if not config.l10n_pl_edi_register:
                config.l10n_pl_edi_certificate = False

    def _set_l10n_pl_edi_certificate(self):
        for config in self:
            company = config.company_id.sudo()
            if config.l10n_pl_edi_certificate:
                config._l10n_pl_edi_ksef_authenticate()
                company.l10n_pl_edi_register = True
                company.l10n_pl_edi_certificate = config.l10n_pl_edi_certificate
            else:
                # Persisted reset happens only on save
                company.write(dict.fromkeys([
                    'l10n_pl_edi_certificate',
                    'l10n_pl_edi_access_token',
                    'l10n_pl_edi_refresh_token',
                    'l10n_pl_edi_register',
                    'l10n_pl_edi_session_id',
                    'l10n_pl_edi_session_key',
                    'l10n_pl_edi_session_iv',
                ], False))

    def _l10n_pl_edi_ksef_authenticate(self):
        """
            Orchestrates the entire authentication flow using the service.
        """
        self.ensure_one()

        vat = self.company_id.vat
        if not vat or not vat.startswith('PL'):
            raise ValidationError(self.env._("A polish VAT number must be set on your company."))
        if not self.l10n_pl_edi_certificate:
            raise ValidationError(self.env._("Please set up a valid KSeF Certificate, with its Private Key set"))

        nip = stdnum.pl.nip.compact(vat)

        ksef_service = KsefApiService(self.company_id)
        temp_token, ref_number = None, None

        if not self.l10n_pl_edi_certificate.private_key_id:
            raise ValidationError(self.env._(
                "The selected certificate record (%(name)s) is missing a private key.",
                name=self.l10n_pl_edi_certificate.display_name
            ))

        key_bytes = base64.b64decode(self.l10n_pl_edi_certificate.private_key_id.pem_key)
        cert_bytes = base64.b64decode(self.l10n_pl_edi_certificate.pem_certificate)
        private_key_password = (self.l10n_pl_edi_certificate.private_key_id.password or "").encode("utf-8") or None
        if key_bytes and cert_bytes:
            signer = XadesSigner(key_bytes, cert_bytes, private_key_password)
        else:
            raise UserError(self.env._("KSeF certificate and private key are not set."))

        challenge_data = ksef_service.get_challenge()
        challenge_code = challenge_data.get('challenge')

        signed_xml = signer.sign_authentication_challenge(challenge_code, nip)
        token_data = ksef_service.authenticate_xades(signed_xml)

        temp_token = token_data.get('authenticationToken', {}).get('token')
        ref_number = token_data.get('referenceNumber')
        if not temp_token or not ref_number:
            raise ValidationError(self.env._("Failed to initiate KSeF authentication."))

        status_data = ksef_service.check_auth_status(ref_number, temp_token)
        if status_data.get('status', {}).get('code') != 200:
            raise ValidationError(self.env._("Authentication with KSeF failed."))

        token_data = ksef_service.redeem_token(temp_token)
        access_token = token_data.get('accessToken', {}).get('token')
        refresh_token = token_data.get('refreshToken', {}).get('token')
        if not access_token or not refresh_token:
            raise ValidationError(self.env._("Failed to retrieve access or refresh tokens."))

        self.company_id.sudo().write({
            'l10n_pl_edi_access_token': access_token,
            'l10n_pl_edi_refresh_token': refresh_token,
        })
