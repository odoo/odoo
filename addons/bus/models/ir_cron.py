# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrCron(models.Model):
    _inherit = "ir.cron"

    def _notify_admin(self, message):
        """Send a notification to the admin users."""
        self.env.user._bus_send('simple_notification', {
            'type': 'warning',
            'message': message,
        })
        super()._notify_admin(message)
