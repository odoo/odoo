# -*- coding: utf-8 -*-
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

TOTP_RATE_LIMITS = {
    'send_email': (10, 3600),
    'code_check': (10, 3600),
}


class Users(models.Model):
    _inherit = 'res.users'

    def _mfa_type(self):
        r = super()._mfa_type()
        if r is not None:
            return r
        ICP = self.env['ir.config_parameter'].sudo()
        otp_required = False
        if ICP.get_param('auth_totp.policy') == 'all_required':
            otp_required = True
        elif ICP.get_param('auth_totp.policy') == 'employee_required' and self._is_internal():
            otp_required = True
        if otp_required:
            return 'totp_mail'

    def _mfa_url(self):
        r = super()._mfa_url()
        if r is not None:
            return r
        if self._mfa_type() == 'totp_mail':
            return '/web/login/totp'

    def _totp_check(self, code):
        self._totp_rate_limit('code_check')
        user = self.sudo()
        if user._mfa_type() != 'totp_mail':
            return super()._totp_check(code)

        key = self._get_totp_mail_key()
        match = TOTP(key).match(code, window=3600, timestep=3600)
        if match is None:
            _logger.info("2FA check (mail): FAIL for %s %r", self, self.login)
            raise AccessDenied(_("Verification failed, please double-check the 6-digit code"))
        _logger.info("2FA check(mail): SUCCESS for %s %r", self, self.login)
        self._totp_rate_limit_purge('code_check')
        self._totp_rate_limit_purge('send_email')
        return True

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
        expiration = babel.dates.format_timedelta(expiration, lang)

        return str(code).zfill(6), expiration

    def _send_totp_mail_code(self):
        self.ensure_one()
        self._totp_rate_limit('send_email')

        if not self.email:
            raise UserError(_("Cannot send email: user %s has no email address.", self.name))

        template = self.env.ref('auth_totp_mail_enforce.mail_template_totp_mail_code').sudo()
        context = {}
        if request:
            geoip = request.geoip
            device = request.httprequest.user_agent.platform
            browser = request.httprequest.user_agent.browser
            context.update({
                'location': f"{geoip['city']}, {geoip['country_name']}" if geoip else None,
                'device': device and device.capitalize() or None,
                'browser': browser and browser.capitalize() or None,
                'ip': request.httprequest.environ['REMOTE_ADDR'],
            })
        email_values = {
            'email_to': self.email,
            'email_cc': False,
            'auto_delete': True,
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }
        with self.env.cr.savepoint():
            template.with_context(**context).send_mail(
                self.id, force_send=True, raise_exception=True, email_values=email_values, email_layout_xmlid='mail.mail_notification_light'
            )

    def _totp_rate_limit(self, limit_type):
        self.ensure_one()
        assert request, "A request is required to be able to rate limit TOTP related actions"
        limit, interval = TOTP_RATE_LIMITS.get(limit_type)
        RateLimitLog = self.env['auth.totp.rate.limit.log'].sudo()
        ip = request.httprequest.environ['REMOTE_ADDR']
        domain = [
            ('user_id', '=', self.id),
            ('create_date', '>=', datetime.now() - timedelta(seconds=interval)),
            ('limit_type', '=', limit_type),
            ('ip', '=', ip),
        ]
        count = RateLimitLog.search_count(domain)
        if count >= limit:
            descriptions = {
                'send_email': _('You reached the limit of authentication mails sent for your account'),
                'code_check': _('You reached the limit of code verifications for your account'),
            }
            description = descriptions.get(limit_type)
            raise AccessDenied(description)
        RateLimitLog.create({
            'user_id': self.id,
            'ip': ip,
            'limit_type': limit_type,
        })

    def _totp_rate_limit_purge(self, limit_type):
        self.ensure_one()
        assert request, "A request is required to be able to rate limit TOTP related actions"
        ip = request.httprequest.environ['REMOTE_ADDR']
        RateLimitLog = self.env['auth.totp.rate.limit.log'].sudo()
        RateLimitLog.search([
            ('user_id', '=', self.id),
            ('limit_type', '=', limit_type),
            ('ip', '=', ip),
        ]).unlink()
