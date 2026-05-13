from datetime import datetime, timedelta

from odoo import _, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_eg_edi_pos_enable = fields.Boolean(string="Submit POS receipts to ETA")
    l10n_eg_edi_pos_client_id = fields.Char(groups='base.group_system')
    l10n_eg_edi_pos_client_secret = fields.Char(groups='base.group_system')
    l10n_eg_edi_pos_serial_number = fields.Char(groups='base.group_system')
    l10n_eg_edi_pos_preprod = fields.Boolean(string="Use Pre-production Environment")
    l10n_eg_edi_pos_access_token = fields.Char(groups='base.group_system', readonly=True)
    l10n_eg_edi_pos_token_expiry = fields.Datetime(groups='base.group_system', readonly=True)
    l10n_eg_edi_pos_last_uuid = fields.Char(groups='base.group_system', readonly=True)

    def _l10n_eg_edi_pos_get_token(self):
        """
            returns valid_access_token, error_message
        """
        self.ensure_one()
        self_sudo = self.sudo()
        if (
            self_sudo.l10n_eg_edi_pos_access_token
            and self_sudo.l10n_eg_edi_pos_token_expiry
            and self_sudo.l10n_eg_edi_pos_token_expiry > datetime.now() + timedelta(seconds=60)
        ):
            return self_sudo.l10n_eg_edi_pos_access_token, ""
        return self._l10n_eg_edi_pos_authenticate()

    def _l10n_eg_edi_pos_build_auth_request(self):
        """
            returns {
                'body': {...},
                'header': {...},
            }
        """
        self.ensure_one()
        self_sudo = self.sudo()
        return {
            'body': {
                'grant_type': 'client_credentials',
                'client_id': self_sudo.l10n_eg_edi_pos_client_id,
                'client_secret': self_sudo.l10n_eg_edi_pos_client_secret,
            },
            'header': {
                'posserial': self_sudo.l10n_eg_edi_pos_serial_number,
                'pososversion': 'os',
                'posmodelframework': '1',
                'presharedkey': self_sudo.l10n_eg_edi_pos_client_id,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        }

    def _l10n_eg_edi_pos_authenticate(self):
        """
            returns access_token, authentication_error
        """
        self.ensure_one()
        request_data = self._l10n_eg_edi_pos_build_auth_request()
        response = self.env['account.edi.format']._l10n_eg_eta_connect_to_server(
            request_data,
            '/connect/token',
            'POST',
            is_access_token_req=True,
            production_enviroment=not self.l10n_eg_edi_pos_preprod,
        )

        data = response.get('data') or {}
        if (error := response.get('error')) or 'access_token' not in data:
            return "", error or _("ETA authentication response is missing the access token.")

        try:
            expiry = datetime.now() + timedelta(seconds=int(data['expires_in']))
        except (KeyError, ValueError, TypeError):
            return "", _("ETA authentication response is missing a valid expires_in.")

        self.sudo().write({
            'l10n_eg_edi_pos_access_token': data['access_token'],
            'l10n_eg_edi_pos_token_expiry': expiry,
        })

        return data['access_token'], ""

    def _l10n_eg_edi_pos_check_credentials(self):
        """
            returns an error string based on the missing credential values.
        """
        self.ensure_one()
        self_sudo = self.sudo()
        errors = []
        if not self_sudo.l10n_eg_edi_pos_client_id:
            errors.append(_("ETA Client ID is missing."))
        if not self_sudo.l10n_eg_edi_pos_client_secret:
            errors.append(_("ETA Client Secret is missing."))
        if not self_sudo.l10n_eg_edi_pos_serial_number:
            errors.append(_("POS Serial Number is missing."))
        return errors
