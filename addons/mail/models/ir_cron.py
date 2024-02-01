# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, SUPERUSER_ID


class IrCron(models.AbstractModel):
    _inherit = 'ir.cron'

    def _get_admin_channel(self):
        """ Get the admin channel.
        If it doesn't exist, creates it. """
        admin_group = self.env.ref("base.group_system", raise_if_not_found=False)
        if not admin_group:
            return

        domain = [
            ("channel_type", "=", "channel"),
            ("group_public_id", "=", admin_group.id),
            ("group_ids", "in", admin_group.id),
        ]

        admin_channel = self.env['discuss.channel'].search(domain).sorted(lambda c: "admin" not in c.name.lower())
        if admin_channel:
            return admin_channel

        return self.env['discuss.channel'].create({
            "name": "Administrators",
            "channel_type": "channel",
            "group_public_id": admin_group.id,
            "group_ids": [(6, 0, [admin_group.id])],
        })


    def _notify_admin(self, message):
        """ Send a notification to the admin users. """
        self._get_admin_channel().with_user(SUPERUSER_ID).message_post(body=message)
        super()._notify_admin(message)
