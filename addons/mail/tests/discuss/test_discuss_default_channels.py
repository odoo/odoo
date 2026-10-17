# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tools.misc import mute_logger

from odoo.addons.mail.tests.common import MailCommon


class TestDiscussDefaultChannels(MailCommon):
    @mute_logger("odoo.addons.base.models.ir_cron")
    def test_notify_admin_posts_in_admin_channel(self):
        self.env["ir.cron"]._notify_admin("The cron failed")
        self.assertMessageFields(
            self.env.ref("mail.channel_admin").message_ids[0],
            {
                "author_id": self.partner_root,
                "body": "<p>The cron failed</p>",
            },
        )

    def test_update_notification_posts_in_general_channel(self):
        with patch.object(
            self.registry["publisher_warranty.contract"],
            "_get_sys_logs",
            return_value={"messages": ["Your database expires soon"]},
        ):
            self.env["publisher_warranty.contract"].update_notification(cron_mode=False)
        self.assertMessageFields(
            self.env.ref("mail.channel_all_employees").message_ids[0],
            {
                "body": "<p>Your database expires soon</p>",
                "subtype_id": self.env.ref("mail.mt_comment"),
            },
        )
