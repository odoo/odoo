from datetime import timedelta

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import HttpCase


class TestNotification(MailCommon, HttpCase):
    def test_missed_message(self):
        self.env["mail.notification"].search([('notification_type', "=", "inbox")]).unlink()
        user = mail_new_test_user(
            self.env,
            login="all",
            name="all",
            email="all@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        user.presence_ids._update_presence(user)
        user.presence_ids.write({
            "last_poll": fields.Datetime.now() - timedelta(hours=13),
            "status": "offline",
        })
        channel = self.env["discuss.channel"]._create_channel(name="Channel", group_id=None)
        channel._add_members(users=user)

        with self.with_user("employee"), self.mock_mail_gateway():
            channel_msg = channel.message_post(
                body="@all Test",
                partner_ids=[user.partner_id.id],
                message_type="comment",
                subtype_xmlid="mail.mt_comment"
            )
            self.env["mail.notification"].search([
                ("mail_message_id", "=", channel_msg.id),
            ])
            channel_msg = channel.message_post(
                body="@all Test",
                partner_ids=[user.partner_id.id],
                message_type="comment",
                subtype_xmlid="mail.mt_comment"
            )
            odoobot = self.env.ref('base.partner_root')
            self.assertSentEmail(
                odoobot.email_formatted,
                [user.partner_id.email],
                subject="WOLOLO",
            )
