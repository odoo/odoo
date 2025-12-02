# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates
import logging

from datetime import datetime, timedelta

from odoo import _, models
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.tools.misc import babel_locale_parse, hmac

from odoo.addons.auth_totp.models.totp import hotp, TOTP

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        res = super().write(vals)

        if 'totp_secret' in vals:
            if vals.get('totp_secret'):
                self._notify_security_setting_update(
                    _("Security Update: 2FA Activated"),
                    _("Two-factor authentication has been activated on your account"),
                    suggest_2fa=False,
                )
            else:
                self._notify_security_setting_update(
                    _("Security Update: 2FA Deactivated"),
                    _("Two-factor authentication has been deactivated on your account"),
                    suggest_2fa=False,
                )

        return res

    def authenticate(self, credential, user_agent_env):
        """Send an alert on new connection.

        - 2FA enabled -> only for new device
        - Not enabled -> no alert
        """
        auth_info = super().authenticate(credential, user_agent_env)
        self._notify_security_new_connection(auth_info)
        return auth_info

    def _notify_security_new_connection(self, auth_info):
        user = self.env(user=auth_info['uid']).user

        if request and user.email and user._mfa_type():
            # Check the `request` object to ensure that we will be able to get the
            # user information (like IP, user-agent, etc) and the cookie `td_id`.
            # (Can be unbounded if executed from a server action or a unit test.)

            key = request.cookies.get('td_id')
            if not key or not request.env['auth_totp.device']._check_credentials_for_uid(
                    scope="browser", key=key, uid=user.id):
                # 2FA enabled but not a trusted device
                user._notify_security_setting_update(
                    subject=_('New Connection to your Account'),
                    content=_('A new device was used to sign in to your account.'),
                )
                _logger.info("New device alert email sent for user <%s> to <%s>", user.login, user.email)

    def _notify_security_setting_update_prepare_values(self, content, *, suggest_2fa=True, **kwargs):
        """" Prepare rendering values for the 'mail.account_security_alert' qweb template

          :param bool suggest_2fa:
            Whether or not to suggest the end-user to turn on 2FA authentication in the email sent.
            It will only suggest to turn on 2FA if not already turned on on the user's account. """

        values = super()._notify_security_setting_update_prepare_values(content, **kwargs)
        values['suggest_2fa'] = suggest_2fa and not self.totp_enabled
        return values

    def action_open_my_account_settings(self):
        action = {
            "name": _("Security"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "views": [[self.env.ref('auth_totp_mail.res_users_view_form').id, "form"]],
            "res_id": self.id,
        }
        return action

    def get_totp_invite_url(self):
        return '/odoo/action-auth_totp_mail.action_activate_two_factor_authentication'

    def action_totp_invite(self):
        invite_template = self.env.ref('auth_totp_mail.mail_template_totp_invite')
        users_to_invite = self.sudo().filtered(lambda user: not user.totp_secret)
        for user in users_to_invite:
            email_values = {
                'email_from': self.env.user.email_formatted,
                'author_id': self.env.user.partner_id.id,
            }
            invite_template.send_mail(user.id, force_send=True, email_values=email_values,
                                      email_layout_xmlid='mail.mail_notification_light')

        # Display a confirmation toaster
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("Invitation to use two-factor authentication sent for the following user(s): %s",
                             ', '.join(users_to_invite.mapped('name'))),
            }
        }

    def _mfa_type(self):
        r = super()._mfa_type()
        if r is not None:
            return r
        ICP = self.env['ir.config_parameter'].sudo()
        otp_required = False
        if ICP.get_param('auth_totp.policy') == 'all_required' or \
                (ICP.get_param('auth_totp.policy') == 'employee_required' and self._is_internal()):
            otp_required = True
        if otp_required:
            return 'totp_mail'

    def _mfa_url(self):
        r = super()._mfa_url()
        if r is not None:
            return r
        if self._mfa_type() == 'totp_mail':
            return '/web/login/totp'

    def _rpc_api_keys_only(self):
        return self._mfa_type() == 'totp_mail' or super()._rpc_api_keys_only()

    def _check_credentials(self, credentials, env):
        if credentials['type'] == 'totp_mail':
            self._totp_rate_limit('code_check')
            user = self.sudo()
            key = user._get_totp_mail_key()
            match = TOTP(key).match(credentials['token'], window=3600, timestep=3600)
            if match is None:
                _logger.info("2FA check (mail): FAIL for %s %r", user, user.login)
                raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
            _logger.info("2FA check(mail): SUCCESS for %s %r", user, user.login)
            self._totp_rate_limit_purge('code_check')
            self._totp_rate_limit_purge('send_email')
            return {
                'uid': self.env.user.id,
                'auth_method': 'totp_mail',
                'mfa': 'default',
            }
        else:
            return super()._check_credentials(credentials, env)

    def _get_totp_mail_key(self):
        self.ensure_one()
        return hmac(self.env(su=True), 'auth_totp_mail-code', (self.id, self.login, self.login_date)).encode()

    def _get_totp_mail_code(self):
        self.ensure_one()

        key = self._get_totp_mail_key()

        now = datetime.now()
        counter = int(datetime.timestamp(now) / 3600)

        code = hotp(key, counter)
        expiration = timedelta(seconds=3600)
        lang = babel_locale_parse(self.env.context.get('lang') or self.lang)
        expiration = babel.dates.format_timedelta(expiration, locale=lang)

        return str(code).zfill(6), expiration

    def _send_totp_mail_code(self):
        self.ensure_one()
        self._totp_rate_limit('send_email')

        if not self.email:
            raise UserError(_("Cannot send email: user %s has no email address.", self.name))

        template = self.env.ref('auth_totp_mail.mail_template_totp_mail_code').sudo()
        context = {}
        if request:
            device = request.httprequest.user_agent.platform
            browser = request.httprequest.user_agent.browser
            context.update({
                'location': None,
                'device': device and device.capitalize() or None,
                'browser': browser and browser.capitalize() or None,
                'ip': request.httprequest.environ['REMOTE_ADDR'],
            })
            if request.geoip.city.name:
                context['location'] = f"{request.geoip.city.name}, {request.geoip.country_name}"

        email_values = {
            'email_to': self.email,
            'email_cc': False,
            'auto_delete': True,
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }
        template.with_context(**context).send_mail(
            self.id, force_send=True, raise_exception=True,
            email_values=email_values,
            email_layout_xmlid='mail.mail_notification_light'
        )
