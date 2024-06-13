# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT

class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    # Google Calendar tokens and synchronization information.
    google_calendar_rtoken = fields.Char('Refresh Token', copy=False, groups='base.group_system')
    google_calendar_token = fields.Char('User token', copy=False, groups='base.group_system')
    google_calendar_token_validity = fields.Datetime('Token Validity', copy=False, groups='base.group_system')
    google_calendar_sync_token = fields.Char('Next Sync Token', copy=False, groups='base.group_system')
    google_calendar_cal_id = fields.Char('Calendar ID', copy=False, groups='base.group_system',
        help='Last Calendar ID who has been synchronized. If it is changed, we remove all links between GoogleID and Odoo Google Internal ID')
    google_synchronization_stopped = fields.Boolean('Google Synchronization stopped', copy=False, groups='base.group_system')

    @api.model
    def _get_fields_blacklist(self):
        """ Get list of google fields that won't be formatted in session_info. """
        google_fields_blacklist = [
            'google_calendar_rtoken',
            'google_calendar_token',
            'google_calendar_token_validity',
            'google_calendar_sync_token',
            'google_calendar_cal_id',
            'google_synchronization_stopped'
        ]
        return super()._get_fields_blacklist() + google_fields_blacklist

    def _set_google_auth_tokens(self, access_token, refresh_token, ttl):
        self.sudo().write({
            'google_calendar_rtoken': refresh_token,
            'google_calendar_token': access_token,
            'google_calendar_token_validity': fields.Datetime.now() + timedelta(seconds=ttl) if ttl else False,
        })

    def _google_calendar_authenticated(self):
        self.ensure_one()
        return bool(self.sudo().google_calendar_rtoken)

    def _is_google_calendar_valid(self):
        self.ensure_one()
        return self.sudo().google_calendar_token_validity and self.sudo().google_calendar_token_validity >= (fields.Datetime.now() + timedelta(minutes=1))

    def _refresh_google_calendar_token(self):
        self.ensure_one()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('google_calendar_client_id')
        client_secret = get_param('google_calendar_client_secret')

        if not client_id or not client_secret:
            raise UserError(_("The account for the Google Calendar service is not configured."))

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': self.sudo().google_calendar_rtoken,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
        }

        try:
            _dummy, response, _dummy = self.env['google.service']._do_request(GOOGLE_TOKEN_ENDPOINT, params=data, headers=headers, method='POST', preuri='')
            ttl = response.get('expires_in')
            self.sudo().write({
                'google_calendar_token': response.get('access_token'),
                'google_calendar_token_validity': fields.Datetime.now() + timedelta(seconds=ttl),
            })
        except requests.HTTPError as error:
            if error.response.status_code in (400, 401):  # invalid grant or invalid client
                # Delete refresh token and make sure it's commited
                self.env.cr.rollback()
                self.sudo()._set_google_auth_tokens(False, False, 0)
                self.env.cr.commit()
            error_key = error.response.json().get("error", "nc")
            error_msg = _("An error occurred while generating the token. Your authorization code may be invalid or has already expired [%s]. "
                          "You should check your Client ID and secret on the Google APIs plateform or try to stop and restart your calendar synchronization.",
                          error_key)
            raise UserError(error_msg)
