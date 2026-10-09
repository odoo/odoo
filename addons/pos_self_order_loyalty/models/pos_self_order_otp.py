# Part of Odoo. See LICENSE file for full copyright and licensing details.

import secrets
import string
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import consteq, hmac

CODE_LENGTH = 6
VALIDITY = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5  # per code
# per email: a new code doesn't give new chances, or guessing would only be slowed down
MAX_FAILURES = 15
FAILURES_WINDOW = timedelta(hours=24)
OTP_SCOPE = 'self-loyalty-auth'


class PosSelfOrderOtp(models.Model):
    """One-time code proving that a self-order customer owns an email address.

    Keyed on the email rather than on a partner: the customer is only created once the
    code is validated, so nobody can create customers, or an account in someone else's
    name, without access to the mailbox.

    The record outlives its code (used up or expired) as long as it counts wrong codes for
    the email, see MAX_FAILURES.
    """
    _name = 'pos_self_order_loyalty.otp'
    _description = "Self-Order Identification Code"

    email = fields.Char(required=True, index=True)  # normalized
    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    lang = fields.Char()
    code_hash = fields.Char()  # empty once the code can't be used anymore
    sent_at = fields.Datetime(required=True)
    expires_at = fields.Datetime(required=True)
    attempts = fields.Integer(default=0)  # on the current code
    failures = fields.Integer(default=0)  # on the email, since failures_since
    failures_since = fields.Datetime()

    _email_company_unique = models.Constraint(
        'UNIQUE(email, company_id)', "Only one pending code per email and company.",
    )

    @api.model
    def _hash(self, email, code):
        return hmac(self.env(su=True), OTP_SCOPE, (email, code))

    @api.model
    def _get(self, email, company):
        return self.sudo().search([('email', '=', email), ('company_id', '=', company.id)])

    @api.model
    def _is_email_blocked(self, email, company):
        """Whether `email` made too many wrong attempts. It doesn't depend on whether a customer
        has this email, so it can't be used to find out who the customers are."""
        otp = self._get(email, company)
        return bool(otp) and otp._is_blocked()

    def _is_blocked(self):
        self.ensure_one()
        return self.failures >= MAX_FAILURES and self.failures_since > fields.Datetime.now() - FAILURES_WINDOW

    def _register_failure(self):
        self.ensure_one()
        now = fields.Datetime.now()
        if not self.failures_since or self.failures_since <= now - FAILURES_WINDOW:
            self.write({'failures': 1, 'failures_since': now})
        else:
            self.failures += 1

    @api.model
    def _send_code(self, email, company):
        """Email a new code to `email`. Does nothing during the resend cooldown, or while the
        email is blocked (see MAX_FAILURES)."""
        Otp = self.sudo()
        now = fields.Datetime.now()
        otp = self._get(email, company)
        if otp and (otp.sent_at > now - RESEND_COOLDOWN or otp._is_blocked()):
            return
        code = ''.join(secrets.choice(string.digits) for _ in range(CODE_LENGTH))
        values = {
            'code_hash': self._hash(email, code),
            'sent_at': now,
            'expires_at': now + VALIDITY,
            'attempts': 0,
            'lang': self.env.lang,
        }
        if otp:
            otp.write(values)
        else:
            otp = Otp.create({**values, 'email': email, 'company_id': company.id})
        self.env.ref('pos_self_order_loyalty.mail_template_self_otp').sudo().with_context(
            otp_code=code,
            validity_minutes=int(VALIDITY.total_seconds() // 60),
        ).send_mail(otp.id, force_send=True, email_layout_xmlid='mail.mail_notification_light')

    @api.model
    def _check_code(self, email, company, code):
        """Whether `code` is the valid code sent to `email`. A valid code can only be used once,
        and validating it forgets the wrong attempts made on the email."""
        if not isinstance(code, str) or len(code) != CODE_LENGTH or not code.isdigit():
            return False
        otp = self._get(email, company)
        if not otp or not otp.code_hash:
            return False
        # Concurrent attempts can't bypass the attempt limits
        otp.lock_for_update()
        if otp._is_blocked():
            return False
        if otp.attempts >= MAX_ATTEMPTS or otp.expires_at < fields.Datetime.now():
            otp.code_hash = False
            return False
        otp.attempts += 1
        if not consteq(otp.code_hash, self._hash(email, code)):
            otp._register_failure()
            return False
        otp.unlink()
        return True

    @api.autovacuum
    def _gc_expired_codes(self):
        now = fields.Datetime.now()
        self.sudo().search([
            ('expires_at', '<', now),
            '|', ('failures_since', '=', False), ('failures_since', '<=', now - FAILURES_WINDOW),
        ]).unlink()
