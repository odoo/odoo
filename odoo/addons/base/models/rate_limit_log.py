from datetime import timedelta

from odoo import api, fields, models


class RateLimitLog(models.TransientModel):
    _name = 'rate.limit.log'
    _description = 'Rate Limit Log'

    _rate_limit_key_create_date_idx = models.Index("(rate_limit_key, create_date)")

    rate_limit_key = fields.Char(readonly=True)

    def _build_rate_limit_key(self, scope, key_vals):
        return '-'.join(map(str, [scope, *key_vals]))

    @api.model
    def _consume_rate_limit(self, rate_limit_rules):
        """
        Check rate limits for the given rules and log attempts if allowed.

        For each rule in ``rate_limit_rules``, this method computes a unique key
        from ``key_vals`` and ``scope``, then counts existing log entries
        matching that key within the configured time window.

        The sequence of values in ``key_vals`` matters, as it directly
        affects key generation. Changing the order will result in a different
        key.

        If any rule exceeds its allowed limit, the method returns ``False`` and
        no log entries are created. Otherwise, a new log entry is created for
        each rule and the method returns ``True``.

        :param list[dict] rate_limit_rules: List of rate limit rule definitions.

        Each rule dictionary must contain:

        - ``scope``: Logical scope used to differentiate contexts.
        - ``key_vals``: Ordered list of values used to build the key.
        - ``limit``: Maximum allowed count within the interval.
        - ``interval``: Time window in seconds.

        Example::

            [
                {'scope': 'send_copy_email', 'key_vals': ['127.0.0.1'], 'limit': 2, 'interval': 60},
                {'scope': 'send_copy_email', 'key_vals': ['127.0.0.1'], 'limit': 50, 'interval': 3600},
                {'scope': 'send_copy_email', 'key_vals': ['abc@xyz.com'], 'limit': 10, 'interval': 3600},
            ]

        :returns: ``True`` if all rules allow the action, ``False`` otherwise.
        :rtype: bool
        """
        seen_keys = set()
        vals_list = []
        for rate_limit_rule in rate_limit_rules:
            rate_limit_key = self._build_rate_limit_key(rate_limit_rule['scope'], rate_limit_rule['key_vals'])
            domain = [
                ('rate_limit_key', '=', rate_limit_key),
                ('create_date', '>=', fields.Datetime.now() - timedelta(seconds=rate_limit_rule['interval'])),
            ]
            if self.search_count(domain) >= rate_limit_rule['limit']:
                return False
            if rate_limit_key not in seen_keys:
                vals_list.append({'rate_limit_key': rate_limit_key})
                seen_keys.add(rate_limit_key)
        self.create(vals_list)
        return True

    @api.model
    def _reset_rate_limit(self, reset_rules):
        """
        Delete all rate limit log entries matching the given rules.

        For each rule in ``reset_rules``, a key is generated using
        ``key_vals`` and ``scope``. All matching log entries are then
        removed.

        The sequence of values in ``key_vals`` matters, as it directly
        affects key generation. Changing the order will result in a different
        key.

        This is typically used to reset rate limits after a successful action.

        :param list[dict] reset_rules: List of rule definitions used to identify
            entries to delete.

        Each rule dictionary must contain:

        - ``scope``: Logical scope used to differentiate contexts.
        - ``key_vals``: Ordered list of values used to build the key. The order
          must be identical to that used when calling ``_consume_rate_limit``.
          otherwise, the computed key will differ and matching entries will not
          be removed.

        :returns: None
        :rtype: None
        """
        keys = [
            self._build_rate_limit_key(rule['scope'], rule['key_vals'])
            for rule in reset_rules
        ]
        self.search([('rate_limit_key', 'in', keys)]).unlink()
