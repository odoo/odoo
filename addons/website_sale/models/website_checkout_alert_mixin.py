# Part of Odoo. See LICENSE file for full copyright and licensing details.

import bisect
from typing import Literal

from odoo import fields, models


class WebsiteCheckoutAlertMixin(models.AbstractModel):
    _name = 'website.checkout.alert.mixin'
    _description = "Website Checkout Alert Mixin"

    alerts = fields.Json()

    def _add_info_alert(self, message: str, /, **kwargs):
        return self._add_alert('info', message, **kwargs)

    def _add_warning_alert(self, message: str, /, **kwargs):
        return self._add_alert('warning', message, **kwargs)

    def _add_danger_alert(self, message: str, /, **kwargs):
        return self._add_alert('danger', message, **kwargs)

    def _add_alert(self, level: Literal['info', 'warning', 'danger'], message: str, /, **kwargs):
        """Add an alert to the current records.

        Alerts are ordered by level of severity, `danger` to `info`.

        :param level: Severity of the alert.
        :param message: The message text to display to the customer.
        :param kwargs: Extra info added in the alert dictionary.
        """
        LEVEL_SEQUENCE_MAPPING = {'danger': 0, 'warning': 500, 'info': 1000}
        level_sequence = LEVEL_SEQUENCE_MAPPING[level]
        for record in self:
            alerts = record._get_alerts()
            idx = bisect.bisect_right(
                alerts, level_sequence, key=lambda alert: LEVEL_SEQUENCE_MAPPING[alert['level']]
            )
            alerts.insert(idx, {'level': level, 'message': message, **kwargs})
            record.alerts = alerts

    def _get_alerts(self) -> list[dict]:
        _ = self and self.ensure_one()  # At most one
        return self.alerts or []

    def _join_alert_messages(self):
        """Return the alert messages of the current records joined by `sep`."""
        return "\n\n".join(alert['message'] for record in self for alert in record._get_alerts())

    def _get_max_alert_level(self):
        """Return the highest severity level (`danger` > `warning` > `info`). Defaults to `info`."""
        self.ensure_one()
        if alerts := self._get_alerts():
            return alerts[0].get('level', 'info')  # Assumed to be ordered
        return 'info'

    def _clear_alerts(self):
        self.alerts = False
