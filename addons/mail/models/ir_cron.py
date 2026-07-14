# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, SUPERUSER_ID


class IrCron(models.AbstractModel):
    _inherit = 'ir.cron'

    def _notify_admin(self, message):
        """ Send a notification to the admin users. """
        channel_admin = self.env.ref("mail.channel_admin", raise_if_not_found=False)
        if channel_admin:
            channel_admin.with_user(SUPERUSER_ID).message_post(body=message)
        super()._notify_admin(message)
