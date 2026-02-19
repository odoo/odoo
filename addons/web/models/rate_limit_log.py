# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import _, models, fields
from odoo.exceptions import AccessDenied


class RateLimitLog(models.TransientModel):
    _name = 'rate.limit.log'
    _description = 'Rate limit logs'

    _scope_identity_key_ip_create_date_idx = models.Index(
        "(scope, identity_key, ip, create_date)"
    )

    ip = fields.Char(readonly=True)
    scope = fields.Char(required=True, readonly=True)
    identity_key = fields.Char(readonly=True)

    def _rate_limit_check(self, scope, ip, identity_key=False):
        """Check rate limit for the given scope and log the attempt.

        Raises AccessDenied if the rate limit has been exceeded.

        :param str scope: the rate limit scope (e.g. 'totp_code_check')
        :param str ip: the IP address of the request
        :param str identity_key: optional identity to rate limit on instead
            of IP alone (e.g. user id, email address)
        """
        limit, interval = self._rate_limit_get_config(scope)
        domain = self._rate_limit_build_domain(scope, ip, identity_key, interval)
        if self.sudo().search_count(domain) >= limit:
            raise AccessDenied(self._rate_limit_get_error_message(scope))
        self.sudo().create(self._rate_limit_prepare_log_values(scope, ip, identity_key))

    def _rate_limit_purge(self, scope, identity_key=False):
        """Clear rate limit logs for the given scope after a successful action.

        :param str scope: the rate limit scope
        :param str identity_key: if provided, only purge logs matching this key
        """
        domain = [('scope', '=', scope)]
        if identity_key:
            domain.append(('identity_key', '=', identity_key))
        self.sudo().search(domain).unlink()

    # --------------------------------------------------
    # Overridable hooks
    # --------------------------------------------------

    def _rate_limit_get_config(self, scope):
        """Return (max_attempts, interval_in_seconds) for the given scope.

        Override this method via ``_inherit`` to register your own scopes.

        :param str scope: the rate limit scope
        :return: tuple (limit, interval)
        :raises ValueError: if the scope is unknown
        """
        raise ValueError("Unknown rate limit scope: %s" % scope)

    def _rate_limit_get_error_message(self, scope):
        """Return the user-facing error message when the limit is exceeded.

        Override this method via ``_inherit`` to provide scope-specific
        messages.

        :param str scope: the rate limit scope
        :return: str
        """
        return _("Too many attempts, please try again later.")

    def _rate_limit_build_domain(self, scope, ip, identity_key, interval):
        """Build the search domain used to count recent attempts.

        When an ``identity_key`` is provided the limit is enforced per
        identity (e.g. per user or per email).  Otherwise it falls back to
        per-IP limiting.

        Override this method if you need a different strategy (e.g. limit
        by both IP and identity simultaneously).

        :param str scope: the rate limit scope
        :param str ip: the IP address
        :param str identity_key: optional identity value
        :param int interval: the time window in seconds
        :return: list of domain tuples
        """
        domain = [
            ('scope', '=', scope),
            ('create_date', '>=', datetime.now() - timedelta(seconds=interval)),
        ]
        if identity_key:
            domain.append(('identity_key', '=', identity_key))
        else:
            domain.append(('ip', '=', ip))
        return domain

    def _rate_limit_prepare_log_values(self, scope, ip, identity_key):
        """Prepare the values dict for creating a rate limit log entry.

        Override to add extra data to the log record.

        :param str scope: the rate limit scope
        :param str ip: the IP address
        :param str identity_key: optional identity value
        :return: dict
        """
        return {
            'scope': scope,
            'ip': ip,
            'identity_key': identity_key or False,
        }
