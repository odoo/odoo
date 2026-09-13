# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCase
from odoo.addons.mail.tests.common import MailCommon


@odoo.tests.tagged("mail_controller", "post_install", "-at_install")
class TestMoveMessages(HttpCase, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.user_employee.partner_id
        Channel = cls.env["discuss.channel"]
        cls.source = Channel.create({"name": "Source", "channel_type": "channel"})
        cls.target = Channel.create({"name": "Target", "channel_type": "channel"})
        cls.source._add_members(partners=cls.partner)
        cls.target._add_members(partners=cls.partner)
        cls.messages = cls.env["mail.message"]
        for idx in range(4):
            cls.messages |= cls.source.message_post(
                body=f"msg {idx}",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=cls.partner.id,
            )

    def _move(self, message_ids, target_channel_id, **kwargs):
        """Call the /discuss/messages/move route as the employee user."""
        self.authenticate("employee", "employee")
        res = self.url_open(
            url="/discuss/messages/move",
            data=json.dumps(
                {
                    "params": {
                        "message_ids": message_ids,
                        "target_channel_id": target_channel_id,
                        **kwargs,
                    },
                },
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        return res.json()

    def _source_comments(self, channel):
        return self.env["mail.message"].search(
            [
                ("model", "=", "discuss.channel"),
                ("res_id", "=", channel.id),
                ("message_type", "=", "comment"),
            ]
        )

    def test_move_only(self):
        anchor = self.messages[1]
        self._move([anchor.id], self.target.id, scope="only", notify_new=False)
        self.assertEqual(anchor.res_id, self.target.id)
        remaining = self._source_comments(self.source)
        self.assertEqual(len(remaining), 3)
        self.assertNotIn(anchor, remaining)

    def test_move_following(self):
        anchor = self.messages[1]
        self._move([anchor.id], self.target.id, scope="following", notify_new=False)
        moved = self._source_comments(self.target)
        self.assertEqual(set(moved.ids), set(self.messages[1:].ids))
        remaining = self._source_comments(self.source)
        self.assertEqual(set(remaining.ids), set(self.messages[:1].ids))

    def test_move_all(self):
        anchor = self.messages[2]
        self._move([anchor.id], self.target.id, scope="all", notify_new=False)
        moved = self._source_comments(self.target)
        self.assertEqual(set(moved.ids), set(self.messages.ids))
        self.assertFalse(self._source_comments(self.source))

    def test_move_to_new_topic(self):
        anchor = self.messages[0]
        self._move(
            [anchor.id],
            self.target.id,
            scope="only",
            new_topic_name="My Topic",
            notify_new=False,
        )
        sub_channel = self.env["discuss.channel"].search(
            [
                ("parent_channel_id", "=", self.target.id),
                ("name", "=", "My Topic"),
            ]
        )
        self.assertTrue(sub_channel)
        self.assertEqual(anchor.res_id, sub_channel.id)

    def test_notify_new_and_old(self):
        anchor = self.messages[0]
        before_source = len(self._source_comments(self.source))
        self._move(
            [anchor.id],
            self.target.id,
            scope="only",
            notify_new=True,
            notify_old=True,
        )
        source_notices = self.env["mail.message"].search(
            [
                ("model", "=", "discuss.channel"),
                ("res_id", "=", self.source.id),
                ("message_type", "=", "notification"),
            ]
        )
        self.assertTrue(source_notices)
        target_notices = self.env["mail.message"].search(
            [
                ("model", "=", "discuss.channel"),
                ("res_id", "=", self.target.id),
                ("message_type", "=", "notification"),
            ]
        )
        self.assertTrue(target_notices)
        self.assertEqual(len(self._source_comments(self.source)), before_source - 1)

    def test_parent_id_cleanup(self):
        parent = self.messages[0]
        child = self.source.message_post(
            body="child",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=self.partner.id,
            parent_id=parent.id,
        )
        self._move([child.id], self.target.id, scope="only", notify_new=False)
        self.assertEqual(child.res_id, self.target.id)
        # Parent stayed behind, so the reference is cleared.
        self.assertFalse(child.parent_id)

    @mute_logger("odoo.http")
    def test_same_destination_raises(self):
        anchor = self.messages[0]
        res = self._move([anchor.id], self.source.id, scope="only")
        self.assertIn("error", res)
        # The message did not move.
        self.assertEqual(anchor.res_id, self.source.id)

    @mute_logger("odoo.http")
    def test_move_to_non_editable_channel(self):
        # A group channel requires membership to be editable. The employee is
        # not a member, so it is not editable for them.
        other = self.env["discuss.channel"].create(
            {"name": "Other", "channel_type": "group"}
        )
        anchor = self.messages[0]
        res = self._move([anchor.id], other.id, scope="only")
        self.assertIn("error", res)
        self.assertEqual(anchor.res_id, self.source.id)

    @mute_logger("odoo.http")
    def test_new_topic_under_thread_raises(self):
        sub_channel = self.target._create_sub_channel(name="Existing Thread")
        anchor = self.messages[0]
        res = self._move(
            [anchor.id],
            sub_channel.id,
            scope="only",
            new_topic_name="Nested",
        )
        self.assertIn("error", res)
        self.assertEqual(anchor.res_id, self.source.id)
