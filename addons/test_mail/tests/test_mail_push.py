import json
import socket
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import requests
from markupsafe import Markup
from requests.adapters import HTTPAdapter

import odoo
from odoo.exceptions import UserError
from odoo.libs.guarded_http import GuardedAdapter
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tests.transaction_case import _super_send
from odoo.tools.misc import mute_logger

from odoo.addons.mail.models.mail_push import (
    PUSH_ENDPOINT_RETRY_DAYS,
    PUSH_ENDPOINT_RETRY_DELAY,
)
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tools.jwt import InvalidVapidError
from odoo.addons.mail.tools.web_push import (
    ENCRYPTION_BLOCK_OVERHEAD,
    ENCRYPTION_HEADER_SIZE,
)
from odoo.addons.sms.tests.common import SMSCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE


@tagged("mail_push")
class TestWebPushPayloadBudget(TransactionCase):
    """The payload budget, without a browser.

    `TestWebPushNotification` needs a running HTTP server and is skipped under
    `--no-http`; `_web_push_truncate_payload` is a pure function over a dict and
    has no business paying for one.
    """

    def _truncated(self, title, body, icon="/i.png"):
        payload = {
            "title": title,
            "options": {
                "body": body,
                "icon": icon,
                "data": {"model": "mail.test.simple", "res_id": 1},
            },
        }
        out = self.env["mixin.mail.thread"]._web_push_truncate_payload(payload)
        return out, len(json.dumps(out).encode())

    def test_a_payload_oversized_by_its_title_still_fits(self):
        """The overflow must come out of whatever is long, not always the body.

        `record_name` is a record's `display_name`, which nothing bounds, and the
        title is `"<author>: <record_name>"`. A payload made oversized by that
        title used to have the *whole* overflow taken out of the body -- so the
        body came back empty and the payload was **still over budget**, which the
        endpoint then rejected. Both halves of that were wrong: the content was
        destroyed and the notification did not arrive either way.
        """
        budget = self.env[
            "mixin.mail.thread"
        ]._truncate_payload_get_max_payload_length()
        payload, size = self._truncated("T" * 6000, "the message")
        self.assertLessEqual(size, budget, "a trimmed payload must fit its budget")
        self.assertEqual(
            payload["options"]["body"],
            "the message",
            "a short body is not worth emptying when the title is what is long",
        )
        self.assertTrue(payload["title"], "and the title is trimmed, not dropped")

    def test_a_payload_oversized_by_its_body_still_trims_the_body(self):
        """The case that already worked, pinned so the rule above cannot silently
        invert it: a long body against a short title still gives up the body, and
        the title survives whole."""
        budget = self.env[
            "mixin.mail.thread"
        ]._truncate_payload_get_max_payload_length()
        payload, size = self._truncated("Ernest: Ticket", "B" * 6000)
        self.assertLessEqual(size, budget)
        self.assertEqual(payload["title"], "Ernest: Ticket")
        self.assertLess(len(payload["options"]["body"]), 6000)
        self.assertTrue(payload["options"]["body"], "trimmed, not emptied")

    def test_a_cut_inside_a_surrogate_pair_leaves_no_half_character(self):
        """The budget counts escaped characters; a non-BMP char escapes as TWO.

        `json.dumps("\N{GRINNING FACE}")` is `\\ud83d\\ude00` -- twelve escaped
        characters for one real one -- so trimming to an escaped-length budget
        can cut between the halves. What survives is a code unit, not a
        character. Nothing raises: the JSON is ASCII-escaped, so it re-encodes
        and ships, and the browser is the first thing to see it, as U+FFFD.

        Asserted on `_web_push_truncate_json_string` rather than on a whole
        payload because where a payload-level cut lands depends on every other
        field's length -- a payload test passes or fails by accident of the
        icon path, which is how the first version of this test proved nothing.
        """
        thread = self.env["mixin.mail.thread"]
        emoji = "\N{GRINNING FACE}"
        self.assertEqual(len(json.dumps(emoji)[1:-1]), 12, "one char, two escapes")
        for max_chars in (6, 9, 18):
            with self.subTest(max_chars=max_chars):
                out = thread._web_push_truncate_json_string(emoji * 3, max_chars)
                self.assertFalse(
                    [char for char in out if "\ud800" <= char <= "\udfff"],
                    f"cutting at {max_chars} escaped chars kept half a character: "
                    f"{out!r}",
                )

    def test_truncating_on_a_pair_boundary_keeps_whole_characters(self):
        """The complement: a cut that lands cleanly must not lose the character."""
        thread = self.env["mixin.mail.thread"]
        emoji = "\N{GRINNING FACE}"
        self.assertEqual(thread._web_push_truncate_json_string(emoji * 3, 12), emoji)


@tagged("post_install", "-at_install", "mail_push")
@tagged("mail_push")
class TestWebPushRecipientLanguage(TransactionCase):
    """A push notification is rendered in the recipient's language, not the sender's.

    `_notify_thread_by_web_push` built ONE payload and handed the same bytes to
    every device. The email path for the same message already groups recipients
    per language (`_notify_get_classified_recipients_iterator`), and
    `discuss_channel_member.py` already supplied `payload_by_lang` to
    `_web_push_send_notification` -- the parameter existed with exactly one
    caller. The thread path did neither.

    What is actually translatable in a push payload is narrow, and the tests
    below say so rather than implying the whole body is: a message whose body is
    empty falls back to its attachment names joined by a *translated* connector
    ("%(file1)s and %(file2)s", plus the "Voice Message" label), and that string
    is what a French recipient used to receive in English. A plain comment
    carries the author's own HTML and has nothing to translate, so it is
    unaffected either way -- asserted here so the fix's scope is pinned and not
    overstated later.

    A `TransactionCase`, not `TestWebPushNotification`'s base: that class skips
    itself when its environment is unavailable, and language selection is decided
    long before any endpoint is contacted.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.env["mail.push.device"].get_or_create_web_push_vapid_public_key()
        cls.record = cls.env["mail.test.simple"].create({"name": "Pushed"})
        cls.user_en = cls._push_user("push_en", "en_US")
        cls.user_fr = cls._push_user("push_fr", "fr_FR")
        cls.record.message_subscribe((cls.user_en + cls.user_fr).partner_id.ids)

    @classmethod
    def _push_user(cls, login, lang):
        user = mail_new_test_user(
            cls.env, login=login, groups="base.group_user", name=login.upper()
        )
        user.partner_id.lang = lang
        user.notification_type = "inbox"
        cls.env["mail.push.device"].sudo().create(
            {
                "endpoint": f"https://test.odoo.com/webpush/{login}",
                "expiration_time": None,
                "keys": json.dumps({"p256dh": "k", "auth": "a"}),
                "partner_id": user.partner_id.id,
            }
        )
        return user

    def _bodies_pushed_by(self, post):
        """Run `post`, return {login: push body actually delivered to that device}."""
        delivered = {}

        def _capture(*args, **kwargs):
            login = kwargs["device"]["endpoint"].rsplit("/", 1)[-1]
            delivered[login] = json.loads(kwargs["payload"])["options"]["body"]

        with patch.object(
            odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point", _capture
        ):
            post()
            self.env.flush_all()
        return delivered

    def _post_with_attachments(self):
        attachments = self.env["ir.attachment"].create(
            [
                {"name": "alpha.txt", "datas": "MQ=="},
                {"name": "beta.txt", "datas": "MQ=="},
            ]
        )
        self.record.message_post(
            body="",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            attachment_ids=attachments.ids,
            partner_ids=(self.user_en + self.user_fr).partner_id.ids,
        )

    def test_attachment_fallback_reaches_each_device_in_its_own_language(self):
        """The user-visible symptom: a French device received the English join."""
        bodies = self._bodies_pushed_by(self._post_with_attachments)
        self.assertEqual(set(bodies), {"push_en", "push_fr"}, "both devices pushed")
        self.assertNotEqual(
            bodies["push_en"],
            bodies["push_fr"],
            "the attachment-name fallback is a translated string, so the two "
            f"recipients must not receive the same bytes (got {bodies!r})",
        )
        for login, body in bodies.items():
            self.assertIn("alpha.txt", body, f"{login} still names the attachments")
            self.assertIn("beta.txt", body, f"{login} still names the attachments")

    def test_a_plain_comment_is_not_translated_and_must_not_change(self):
        """Scope guard: the author's own HTML is not the mixin's to translate."""
        bodies = self._bodies_pushed_by(
            lambda: self.record.message_post(
                body=Markup("<p>Hello</p>"),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                partner_ids=(self.user_en + self.user_fr).partner_id.ids,
            )
        )
        self.assertEqual(set(bodies), {"push_en", "push_fr"})
        self.assertEqual(
            bodies["push_en"],
            bodies["push_fr"],
            "a body with no translatable content must reach both devices alike",
        )

    def test_one_payload_is_built_per_language_not_per_device(self):
        """Per-language must not silently become per-device."""
        other_en = self._push_user("push_en2", "en_US")
        self.record.message_subscribe(other_en.partner_id.ids)
        rendered_langs = []
        thread_model = type(self.env["mixin.mail.thread"])
        original = thread_model._notify_by_web_push_prepare_payload

        def _record_lang(records, message, **kwargs):
            rendered_langs.append(records.env.lang)
            return original(records, message, **kwargs)

        with patch.object(
            thread_model, "_notify_by_web_push_prepare_payload", _record_lang
        ):
            self._bodies_pushed_by(self._post_with_attachments)
        self.assertEqual(
            sorted(rendered_langs),
            ["en_US", "fr_FR"],
            "three devices across two languages must cost two payload renders",
        )


@tagged("mail_push")
class TestWebPushAuthorSuppression(TransactionCase):
    """Push must suppress the same author the inbox/email path suppressed.

    `_notify_get_recipients` has already applied the author policy -- including
    the `notify_author` / `notify_author_mention` flags -- before
    `_notify_thread_by_web_push` ever sees `recipients_data`. The push path then
    subtracted an author *again*, and resolved it differently: the inbox/email
    side skips the REAL author (`_message_compute_real_author`, i.e. whoever is
    acting), while the push side subtracted the DECLARED `msg_vals["author_id"]`.

    Those coincide for an ordinary post and diverge exactly when a message is
    posted on someone else's behalf -- out-of-office auto-replies, gateway-created
    messages, `_track_set_author`. There the declared author is a legitimate
    recipient: they were notified, and their device was silently skipped.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["mail.push.device"].get_or_create_web_push_vapid_public_key()
        cls.actor = cls._device_user("actor")
        cls.declared = cls._device_user("declared")
        cls.record = cls.env["mail.test.simple"].create({"name": "OnBehalf"})

    @classmethod
    def _device_user(cls, login):
        user = mail_new_test_user(
            cls.env, login=login, groups="base.group_user", name=login.upper()
        )
        user.notification_type = "inbox"
        cls.env["mail.push.device"].sudo().create(
            {
                "endpoint": f"https://test.odoo.com/webpush/{login}",
                "expiration_time": None,
                "keys": json.dumps({"p256dh": "k", "auth": "a"}),
                "partner_id": user.partner_id.id,
            }
        )
        return user

    def _post_on_behalf(self):
        pushed = []

        def _capture(*args, **kwargs):
            pushed.append(kwargs["device"]["endpoint"].rsplit("/", 1)[-1])

        with patch.object(
            odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point", _capture
        ):
            message = self.record.with_user(self.actor).message_post(
                body=Markup("<p>on behalf</p>"),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=self.declared.partner_id.id,
                partner_ids=(self.actor + self.declared).partner_id.ids,
            )
            self.env.flush_all()
        return message, pushed

    def test_a_recipient_notified_on_behalf_is_also_pushed(self):
        message, pushed = self._post_on_behalf()
        notified = self.env["mail.notification"].search(
            [("mail_message_id", "=", message.id)]
        )
        self.assertIn(
            self.declared.partner_id,
            notified.res_partner_id,
            "precondition: the declared author is a genuine recipient here",
        )
        self.assertIn(
            "declared",
            pushed,
            "a partner the inbox path notified must not have their device skipped "
            "because they are named as the message's author",
        )

    def test_the_acting_author_is_still_not_pushed(self):
        """Removing the second filter must not start notifying the actor."""
        message, pushed = self._post_on_behalf()
        notified = self.env["mail.notification"].search(
            [("mail_message_id", "=", message.id)]
        )
        self.assertNotIn(
            self.actor.partner_id,
            notified.res_partner_id,
            "precondition: the acting author is suppressed by _notify_get_recipients",
        )
        self.assertNotIn(
            "actor", pushed, "and is therefore not pushed either -- one policy, not two"
        )


class TestWebPushMessageTypes(TransactionCase):
    """Which recipients a push reaches is decided by the message type through
    two hooks, so a module adding a type (`whatsapp`) extends a set instead of
    core naming it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.simple"].create({"name": "Types"})
        cls.message = cls.record.message_post(body="x", message_type="comment")

    def _recipients(self, message_type):
        data = [
            {"id": 11, "active": True, "notif": "inbox", "email_normalized": "a@x"},
            {"id": 12, "active": True, "notif": "email", "email_normalized": "b@x"},
        ]
        return self.record._notify_get_recipients_for_extra_notifications(
            self.message, data, msg_vals={"message_type": message_type}
        )

    def test_a_comment_pushes_every_recipient(self):
        self.assertEqual(self._recipients("comment"), {11, 12})

    def test_a_notification_pushes_only_inbox_recipients(self):
        for message_type in ("notification", "user_notification", "email"):
            self.assertEqual(self._recipients(message_type), {11}, message_type)

    def test_an_unknown_type_pushes_nobody(self):
        self.assertEqual(self._recipients("email_outgoing"), set())
        Thread = self.env.registry["mixin.mail.thread"]
        with patch.object(
            Thread,
            "_web_push_all_recipients_message_types",
            lambda model: frozenset({"comment", "email_outgoing"}),
        ):
            self.assertEqual(self._recipients("email_outgoing"), {11, 12})


# `SMSCommon.tearDown` calls `self.env["sms.sms"]`, and `sms` is `auto_install` on
# top of `mail` -- so at_install, where these would otherwise run, is before `sms`
# is in the registry and every test dies in teardown with KeyError: 'sms.sms'
# having already passed its body.
@tagged("-at_install", "post_install", "mail_push")
class TestWebPushNotification(SMSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_email = cls.user_employee
        cls.user_email.notification_type = "email"

        cls.user_inbox = mail_new_test_user(
            cls.env,
            login="user_inbox",
            groups="base.group_user",
            name="User Inbox",
            notification_type="inbox",
        )

        cls.record_simple = (
            cls.env["mail.test.simple"]
            .with_context(cls._test_context)
            .create({"name": "Test", "email_from": "ignasse@example.com"})
        )
        cls.record_simple.message_subscribe(
            partner_ids=[
                cls.user_email.partner_id.id,
                cls.user_inbox.partner_id.id,
            ]
        )
        cls.alias_gateway = cls.env["mail.alias"].create(
            {
                "alias_contact": "everyone",
                "alias_domain": cls.mail_alias_domain.id,
                "alias_model_id": cls.env["ir.model"]._get_id(
                    "mail.test.gateway.company"
                ),
                "alias_name": "alias.gateway",
            }
        )

        # generate keys and devices
        cls.vapid_public_key = cls.env[
            "mail.push.device"
        ].get_or_create_web_push_vapid_public_key()
        cls.env["mail.push.device"].sudo().create(
            [
                {
                    "endpoint": f"https://test.odoo.com/webpush/user{(idx + 1)}",
                    "expiration_time": None,
                    "keys": json.dumps(
                        {
                            "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                            "auth": "DJFdtAgZwrT6yYkUMgUqow",
                        }
                    ),
                    "partner_id": user.partner_id.id,
                }
                for idx, user in enumerate(cls.user_email + cls.user_inbox)
            ]
        )

    def _trigger_cron_job(self):
        self.env.ref("mail.ir_cron_web_push_notification").method_direct_trigger()

    def _assert_notification_count_for_cron(self, number_of_notification):
        notification_count = self.env["mail.push"].search_count([])
        self.assertEqual(notification_count, number_of_notification)

    @patch.object(odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point")
    def test_notify_by_push(self, push_to_end_point):
        """When posting a comment, notify both inbox and people outside of Odoo
        aka email"""
        self.record_simple.with_user(self.user_admin).message_post(
            body=Markup("<p>Hello</p>"),
            message_type="comment",
            partner_ids=(self.user_email + self.user_inbox).partner_id.ids,
            subtype_xmlid="mail.mt_comment",
        )
        # not using cron, as max 1 push notif -> direct send
        self._assert_notification_count_for_cron(0)
        # two recipients, comment notifies both inbox and email people
        self.assertEqual(push_to_end_point.call_count, 2)

    @patch.object(odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point")
    def test_notify_by_push_channel(self, push_to_end_point):
        """Test various use case with discuss.channel. Chat and group channels
        sends push notifications, channel not."""
        chat_channel, channel_channel, group_channel = (
            self.env["discuss.channel"]
            .with_user(self.user_email)
            .create(
                [
                    {
                        "channel_partner_ids": [
                            (4, self.user_email.partner_id.id),
                            (4, self.user_inbox.partner_id.id),
                        ],
                        "channel_type": channel_type,
                        "name": f"{channel_type} Message"
                        if channel_type != "group"
                        else "",
                    }
                    for channel_type in ["chat", "channel", "group"]
                ]
            )
        )
        group_channel._add_members(guests=self.guest)

        for channel, sender, notification_count in zip(
            (chat_channel + channel_channel + group_channel + group_channel),
            (self.user_email, self.user_email, self.user_email, self.guest),
            (1, 0, 1, 2),
            strict=True,
        ):
            with self.subTest(channel_type=channel.channel_type):
                if sender == self.guest:
                    channel_as_sender = channel.with_user(
                        self.env.ref("base.public_user")
                    ).with_context(guest=sender)
                else:
                    channel_as_sender = channel.with_user(self.user_email)
                # sudo: discuss.channel - guest can post as sudo in a test (simulating RPC without using network)
                channel_as_sender.sudo().message_post(
                    body="Test Push",
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
                self.assertEqual(push_to_end_point.call_count, notification_count)
                if notification_count > 0:
                    payload_value = json.loads(
                        push_to_end_point.call_args.kwargs["payload"]
                    )
                    if channel.channel_type == "chat":
                        self.assertEqual(
                            payload_value["title"], f"{self.user_email.name}"
                        )
                    elif channel.channel_type == "group":
                        self.assertIn(self.user_email.name, payload_value["title"])
                        self.assertIn(self.user_inbox.name, payload_value["title"])
                        self.assertIn(self.guest.name, payload_value["title"])
                        self.assertNotIn("False", payload_value["title"])
                    else:
                        self.assertEqual(payload_value["title"], f"#{channel.name}")
                    icon = (
                        "/web/static/img/odoo-icon-192x192.png"
                        if sender == self.guest
                        else f"/web/image/res.partner/{self.user_email.partner_id.id}/avatar_128"
                    )
                    self.assertEqual(payload_value["options"]["icon"], icon)
                    self.assertEqual(payload_value["options"]["body"], "Test Push")
                    self.assertEqual(
                        payload_value["options"]["data"]["res_id"], channel.id
                    )
                    self.assertEqual(
                        payload_value["options"]["data"]["model"], channel._name
                    )
                    self.assertEqual(
                        push_to_end_point.call_args.kwargs["device"]["endpoint"],
                        "https://test.odoo.com/webpush/user2",
                    )
                push_to_end_point.reset_mock()

        # Test Direct Message with channel muted -> should skip push notif
        now = datetime.now()
        self.env["discuss.channel.member"].search(
            [
                (
                    "partner_id",
                    "in",
                    (self.user_email.partner_id + self.user_inbox.partner_id).ids,
                ),
                (
                    "channel_id",
                    "in",
                    (chat_channel + channel_channel + group_channel).ids,
                ),
            ]
        ).write({"mute_until_dt": now + timedelta(days=5)})
        chat_channel.with_user(self.user_email).message_post(
            body="Test",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_not_called()
        push_to_end_point.reset_mock()

        self.env["discuss.channel.member"].search(
            [
                (
                    "partner_id",
                    "in",
                    (self.user_email.partner_id + self.user_inbox.partner_id).ids,
                ),
                (
                    "channel_id",
                    "in",
                    (chat_channel + channel_channel + group_channel).ids,
                ),
            ]
        ).write(
            {
                "mute_until_dt": False,
            }
        )

        # Test Channel Message
        group_channel.with_user(self.user_email).message_post(
            body="Test",
            partner_ids=self.user_inbox.partner_id.ids,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_called_once()

    @patch.object(odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point")
    def test_notify_by_push_channel_with_incoming_envelope(self, push_to_end_point):
        """A channel post that carries an incoming envelope must still push.

        `_notify_get_recipients_for_extra_notifications` -- the method that
        turns a recipients-data list into push targets -- compares every active
        recipient's `email_normalized` against the envelope, and only builds
        that envelope when `incoming_email_to`/`incoming_email_cc` is set. The
        channel members `DiscussChannel._notify_get_recipients` appends carried
        neither `email_normalized` nor `name`, so the comparison raised
        `KeyError: 'email_normalized'` and the whole `message_post` blew up --
        every other push test posts without an envelope and so never reached
        the read. The payload a recipients-data entry must carry is defined
        once, by `mail.followers._get_recipient_data`; a hand-built entry that
        omits a key of it is not a lighter entry, it is a broken one.
        """
        group_channel = (
            self.env["discuss.channel"]
            .with_user(self.user_email)
            .create(
                {
                    "channel_partner_ids": [
                        (4, self.user_email.partner_id.id),
                        (4, self.user_inbox.partner_id.id),
                    ],
                    "channel_type": "group",
                    "name": "",
                }
            )
        )
        # The post comes first on purpose: it is the regression. Asserting the
        # payload shape first would make this test fail on the assertion and
        # never execute the call that actually raised.
        message = group_channel.with_user(self.user_email).message_post(
            body="Test Push",
            incoming_email_to="an.outsider@test.example.com",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        self.assertTrue(message.id, "the post survives an incoming envelope")
        push_to_end_point.assert_called_once()

        recipients_data = group_channel._notify_get_recipients(
            message, {"message_type": "comment", "partner_ids": []}
        )
        self.assertTrue(recipients_data, "precondition: the member is a recipient")
        for recipient in recipients_data:
            self.assertEqual(
                set(recipient),
                {
                    "active",
                    "email_normalized",
                    "groups",
                    "id",
                    "is_follower",
                    "lang",
                    "name",
                    "notif",
                    "share",
                    "type",
                    "uid",
                    "ushare",
                },
                "a recipients-data entry carries the whole payload, not a subset",
            )
        # the envelope address is not a member, so nobody is filtered out of the
        # push by it -- the read that used to raise is nonetheless performed
        self.assertEqual(
            [r["id"] for r in recipients_data],
            [self.user_inbox.partner_id.id],
        )

    @patch.object(odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point")
    def test_notify_by_push_channel_with_channel_notifications_settings(
        self, push_to_end_point
    ):
        """Test various use case with the channel notification settings."""
        all_test_user = mail_new_test_user(
            self.env,
            login="all",
            name="all",
            email="all@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        mentions_test_user = mail_new_test_user(
            self.env,
            login="mentions",
            name="mentions",
            email="mentions@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        nothing_test_user = mail_new_test_user(
            self.env,
            login="nothing",
            name="nothing",
            email="nothing@example.com",
            notification_type="inbox",
            groups="base.group_user",
        )
        all_test_user.res_users_settings_ids.write({"channel_notifications": "all"})
        nothing_test_user.res_users_settings_ids.write(
            {"channel_notifications": "no_notif"}
        )

        # generate devices
        self.env["mail.push.device"].sudo().create(
            [
                {
                    "endpoint": f"https://test.odoo.com/webpush/user{(idx + 20)}",
                    "expiration_time": None,
                    "keys": json.dumps(
                        {
                            "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                            "auth": "DJFdtAgZwrT6yYkUMgUqow",
                        }
                    ),
                    "partner_id": user.partner_id.id,
                }
                for idx, user in enumerate(
                    all_test_user + mentions_test_user + nothing_test_user
                )
            ]
        )

        channel_channel = (
            self.env["discuss.channel"]
            .with_user(self.user_email)
            .create(
                [
                    {
                        "channel_partner_ids": [
                            (4, self.user_email.partner_id.id),
                            (4, all_test_user.partner_id.id),
                            (4, mentions_test_user.partner_id.id),
                            (4, nothing_test_user.partner_id.id),
                        ],
                        "channel_type": "channel",
                        "name": "channel",
                    }
                ]
            )
        )
        # normal messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_called_once()
        # all_test_user should be notified
        self.assertEqual(
            push_to_end_point.call_args.kwargs["device"]["endpoint"],
            "https://test.odoo.com/webpush/user20",
        )
        push_to_end_point.reset_mock()

        # mention messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push @mentions",
            message_type="comment",
            partner_ids=(
                all_test_user + mentions_test_user + nothing_test_user
            ).partner_id.ids,
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(push_to_end_point.call_count, 2)
        # all_test_user and mentions_test_user should be notified
        self.assertEqual(
            push_to_end_point.call_args_list[0].kwargs["device"]["endpoint"],
            "https://test.odoo.com/webpush/user20",
        )
        self.assertEqual(
            push_to_end_point.call_args_list[1].kwargs["device"]["endpoint"],
            "https://test.odoo.com/webpush/user21",
        )
        push_to_end_point.reset_mock()

        # muted channel
        now = datetime.now()
        self.env["discuss.channel.member"].search(
            [
                (
                    "partner_id",
                    "in",
                    (
                        all_test_user.partner_id
                        + mentions_test_user.partner_id
                        + nothing_test_user.partner_id
                    ).ids,
                ),
            ]
        ).write(
            {
                "mute_until_dt": now + timedelta(days=5),
            }
        )
        # normal messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_not_called()
        # mention messages in channel
        channel_channel.with_user(self.user_email).message_post(
            body="Test Push",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        push_to_end_point.assert_not_called()

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
    )
    def test_notify_by_push_mail_gateway(self):
        """Check mail gateway push notifications"""
        with self.mock_mail_gateway():
            test_record = self.format_and_process(
                MAIL_TEMPLATE,
                self.user_email.email_formatted,
                f"{self.alias_gateway.display_name}, {self.user_inbox.email_formatted}",
                subject="Test Record Creation",
                target_model="mail.test.gateway.company",
            )
        self.assertEqual(len(test_record.message_ids), 1)
        self.assertEqual(test_record.message_partner_ids, self.user_email.partner_id)
        test_record.message_subscribe(partner_ids=[self.user_inbox.partner_id.id])

        for include_as_external, has_notif in ((False, True), (True, False)):
            with self.mock_mail_gateway():
                to = f"{self.alias_gateway.display_name}"
                if include_as_external:
                    to += f", {self.user_inbox.email_formatted}"
                self.format_and_process(
                    MAIL_TEMPLATE,
                    self.user_email.email_formatted,
                    to,
                    subject="Repy By Email",
                    extra=f"In-Reply-To:\r\n\t{test_record.message_ids[-1].message_id}\n",
                )
            if has_notif:
                # user_inbox is notified by Odoo, hence receives a push notification
                self.assertPushNotification(
                    mail_push_count=0,
                    title_content=self.user_email.name,
                    body_content="Please call me as soon as possible this afternoon!\n\n--\nSylvie",
                )
            else:
                self.assertNoPushNotification()

    def test_notify_by_push_message_notify(self):
        """In case of notification, only inbox users are notified"""
        for recipient, has_notification in [
            (self.user_email, False),
            (self.user_inbox, True),
        ]:
            with self.subTest(recipient=recipient):
                with self.mock_mail_gateway():
                    self.record_simple.with_user(self.user_admin).message_notify(
                        body="Test Push Body",
                        partner_ids=recipient.partner_id.ids,
                        subject="Test Push Notification",
                    )
                # not using cron, as max 1 push notif -> direct send
                self._assert_notification_count_for_cron(0)
                if has_notification:
                    self.assertPushNotification(
                        mail_push_count=0,
                        endpoint="https://test.odoo.com/webpush/user2",
                        keys=("vapid_private_key", "vapid_public_key"),
                        title=f"{self.user_admin.name}: {self.record_simple.display_name}",
                        body_content="Test Push Body",
                        options={
                            "data": {
                                "model": self.record_simple._name,
                                "res_id": self.record_simple.id,
                            },
                        },
                    )
                else:
                    self.assertNoPushNotification()

    @patch.object(odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point")
    def test_notify_call_invitation(self, push_to_end_point):
        inviting_user = (
            self.env["res.users"].sudo().create({"name": "Test User", "login": "test"})
        )
        channel = (
            self.env["discuss.channel"]
            .with_user(inviting_user)
            ._get_or_create_chat(partners_to=[self.user_email.partner_id.id])
        )
        inviting_channel_member = channel.sudo().channel_member_ids.filtered(
            lambda channel_member: channel_member.partner_id == inviting_user.partner_id
        )

        inviting_channel_member._rtc_join_call()
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs["payload"])
        self.assertEqual(
            payload_value["title"],
            "Incoming call",
        )
        options = payload_value["options"]
        self.assertTrue(options["requireInteraction"])
        self.assertEqual(options["body"], f"Conference: {channel.name}")
        self.assertEqual(
            options["actions"],
            [
                {
                    "action": "DECLINE",
                    "type": "button",
                    "title": "Decline",
                },
                {
                    "action": "ACCEPT",
                    "type": "button",
                    "title": "Accept",
                },
            ],
        )
        data = options["data"]
        self.assertEqual(data["type"], "CALL")
        self.assertEqual(data["res_id"], channel.id)
        self.assertEqual(data["model"], "discuss.channel")
        push_to_end_point.reset_mock()

        inviting_channel_member._rtc_leave_call()
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs["payload"])
        self.assertEqual(payload_value["options"]["data"]["type"], "CANCEL")
        push_to_end_point.reset_mock()

    @patch.object(odoo.addons.mail.models.mixin_mail_thread, "push_to_end_point")
    def test_notify_by_push_tracking(self, push_to_end_point):
        """Test tracking message included in push notifications"""
        container_update_subtype = self.env.ref(
            "test_mail.st_mail_test_ticket_container_upd"
        )
        ticket = (
            self.env["mail.test.ticket"]
            .with_user(self.user_email)
            .create(
                {
                    "name": "Test",
                }
            )
        )
        ticket.message_subscribe(
            partner_ids=[self.user_email.partner_id.id],
            subtype_ids=[container_update_subtype.id],
        )

        container = self.env["mail.test.container"].create({"name": "Container"})
        ticket.write(
            {
                "name": "Test2",
                "email_from": "noone@example.com",
                "container_id": container.id,
            }
        )
        self.flush_tracking()
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_not_called()

        container2 = self.env["mail.test.container"].create({"name": "Container Two"})
        ticket.message_subscribe(
            partner_ids=[self.user_inbox.partner_id.id],
            subtype_ids=[container_update_subtype.id],
        )
        ticket.write(
            {
                "name": "Test3",
                "email_from": "noone@example.com",
                "container_id": container2.id,
            }
        )
        self.flush_tracking()
        self._assert_notification_count_for_cron(0)
        push_to_end_point.assert_called_once()
        payload_value = json.loads(push_to_end_point.call_args.kwargs["payload"])
        self.assertIn(
            f"{container_update_subtype.description}\nContainer: {container.name} → {container2.name}",
            payload_value["options"]["body"],
            "Tracking changes should be included in push notif payload",
        )

    def test_tracking_message_non_char_field(self):
        """Regression: a push tracking message must render float / monetary /
        date changes with their real value. They live in *_value_float /
        *_value_datetime, so reading only *_value_char / *_value_integer used to
        render every such change as '0' (e.g. a 10.5 -> 20.0 price -> 'Revenue: 0').
        """
        record = self.env["mail.test.track.monetary"].create({})
        field = self.env["ir.model.fields"]._get("mail.test.track.monetary", "revenue")
        message = self.env["mail.message"].create(
            {
                "model": "mail.test.track.monetary",
                "res_id": record.id,
                "message_type": "notification",
                "subtype_id": self.env.ref("mail.mt_note").id,
            }
        )
        self.env["mail.tracking.value"].create(
            {
                "mail_message_id": message.id,
                "field_id": field.id,
                "old_value_float": 10.5,
                "new_value_float": 20.0,
            }
        )
        message.invalidate_recordset(["tracking_value_ids"])
        body = self.env["mixin.mail.thread"]._generate_tracking_message(message)
        self.assertIn("Revenue: 10.5 → 20.0", body)
        self.assertNotIn("Revenue: 0", body)

    @patch.object(odoo.addons.mail.models.mail_push, "push_to_end_point")
    def test_push_notifications_cron(self, push_to_end_point):
        # Add 4 more devices to force sending via cron queue
        for index in range(10, 14):
            self.env["mail.push.device"].sudo().create(
                [
                    {
                        "endpoint": "https://test.odoo.com/webpush/user%d" % index,
                        "expiration_time": None,
                        "keys": json.dumps(
                            {
                                "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                                "auth": "DJFdtAgZwrT6yYkUMgUqow",
                            }
                        ),
                        "partner_id": self.user_inbox.partner_id.id,
                    }
                ]
            )

        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body="Test message send via Web Push",
            subject="Test Activity",
        )

        self._assert_notification_count_for_cron(5)
        # Force the execution of the cron
        self._trigger_cron_job()
        self.assertEqual(push_to_end_point.call_count, 5)

    def test_push_notifications_cron_under_mock_mail_gateway(self):
        with (
            patch.object(
                odoo.addons.mail.models.mixin_mail_thread, "MAX_DIRECT_PUSH", 1
            ),
            patch.object(requests.Session, "post") as post,
            self.mock_mail_gateway(),
        ):
            self.record_simple.with_user(self.user_email).message_notify(
                partner_ids=self.user_inbox.partner_id.ids,
                body="Test message send via Web Push",
                subject="Test Activity",
            )
            self._assert_notification_count_for_cron(1)
            self.push_to_end_point_mocked.assert_not_called()
            self._trigger_cron_job()
            self.push_to_end_point_mocked.assert_called_once()
            self.assertEqual(
                self.push_to_end_point_mocked.call_args.kwargs["device"]["endpoint"],
                "https://test.odoo.com/webpush/user2",
            )
        post.assert_not_called()
        self._assert_notification_count_for_cron(0)

    @patch.object(
        requests.Session,
        "post",
        return_value=SimpleNamespace(status_code=404, text="Device Unreachable"),
    )
    def test_push_notifications_error_device_unreachable(self, post):
        with mute_logger("odoo.addons.mail.tools.web_push"):
            self.record_simple.with_user(self.user_email).message_notify(
                partner_ids=self.user_inbox.partner_id.ids,
                body="Test message send via Web Push",
                subject="Test Activity",
            )

        self._assert_notification_count_for_cron(0)
        post.assert_called_once()
        # Test that the unreachable device is deleted from the DB
        notification_count = self.env["mail.push.device"].search_count(
            [("endpoint", "=", "https://test.odoo.com/webpush/user2")]
        )
        self.assertEqual(notification_count, 0)

    @patch.object(
        requests.Session,
        "post",
        return_value=SimpleNamespace(status_code=201, text="Ok"),
    )
    def test_push_notifications_error_encryption_simple(self, post):
        """Test to see if all parameters sent to the endpoint are present.
        This test doesn't test if the cryptographic values are correct."""
        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body="Test message send via Web Push",
            subject="Test Activity",
        )

        self._assert_notification_count_for_cron(0)
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], "https://test.odoo.com/webpush/user2")
        self.assertIn("headers", post.call_args.kwargs)
        self.assertIn("vapid", post.call_args.kwargs["headers"]["Authorization"])
        self.assertIn("t=", post.call_args.kwargs["headers"]["Authorization"])
        self.assertIn("k=", post.call_args.kwargs["headers"]["Authorization"])
        self.assertEqual(
            "aes128gcm", post.call_args.kwargs["headers"]["Content-Encoding"]
        )
        self.assertEqual("60", post.call_args.kwargs["headers"]["TTL"])
        self.assertIn("data", post.call_args.kwargs)
        self.assertIn("timeout", post.call_args.kwargs)

    @patch.object(
        requests.Session,
        "post",
        return_value=SimpleNamespace(status_code=201, text="Ok"),
    )
    def test_push_notifications_device_invalid_tld_domain(self, post):
        self.env["mail.push.device"].sudo().create(
            [
                {
                    "endpoint": "https://test.odoo.invalid/webpush/user",
                    "expiration_time": None,
                    "keys": json.dumps(
                        {
                            "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                            "auth": "DJFdtAgZwrT6yYkUMgUqow",
                        }
                    ),
                    "partner_id": self.user_inbox.partner_id.id,
                }
            ]
        )

        device_count = self.env["mail.push.device"].search_count(
            [("endpoint", "=", "https://test.odoo.invalid/webpush/user")]
        )
        self.assertEqual(device_count, 1)

        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body="Test message send via Web Push",
            subject="Test Activity",
        )

        self._assert_notification_count_for_cron(0)
        post.assert_called_once()
        # Test that the device with the invalid TLD is deleted from the DB
        device_count = self.env["mail.push.device"].search_count(
            [("endpoint", "=", "https://test.odoo.invalid/webpush/user")]
        )
        self.assertEqual(device_count, 0)

    @patch.object(
        requests.Session,
        "post",
        side_effect=ConnectionError("Oops, network error"),
    )
    def test_push_notifications_device_raise_exception(self, post):
        # Add 4 more devices to force sending via cron queue
        for index in range(10, 14):
            self.env["mail.push.device"].sudo().create(
                [
                    {
                        "endpoint": "https://test.odoo.com/webpush/user%d" % index,
                        "expiration_time": None,
                        "keys": json.dumps(
                            {
                                "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                                "auth": "DJFdtAgZwrT6yYkUMgUqow",
                            }
                        ),
                        "partner_id": self.user_inbox.partner_id.id,
                    }
                ]
            )

        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body="Test message send via Web Push",
            subject="Test Activity",
        )

        with self.assertLogs(
            "odoo.addons.mail.models.mail_push", level="ERROR"
        ) as capture:
            self._assert_notification_count_for_cron(5)
            self._trigger_cron_job()
            self.assertEqual(
                capture.output,
                [
                    "ERROR:odoo.addons.mail.models.mail_push:An error occurred while trying to send web push: Oops, network error",
                ]
                * 5,
            )

    def test_push_notification_regenerate_vapid_keys(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=", "mail.web_push_vapid_public_key")]
        ).unlink()
        new_vapid_public_key = self.env[
            "mail.push.device"
        ].get_or_create_web_push_vapid_public_key()
        self.assertNotEqual(self.vapid_public_key, new_vapid_public_key)
        with self.assertRaises(InvalidVapidError):
            self.env["mail.push.device"].register_devices(
                endpoint="https://test.odoo.com/webpush/user1",
                expiration_time=None,
                keys=json.dumps(
                    {
                        "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                        "auth": "DJFdtAgZwrT6yYkUMgUqow",
                    }
                ),
                partner_id=self.user_email.partner_id.id,
                vapid_public_key=self.vapid_public_key,
            )

    def test_the_vapid_private_key_is_a_system_secret(self):
        Credential = self.env["credential.credential"]

        self.assertTrue(
            Credential._get_system_secret("mail.web_push_vapid_private_key")
        )
        self.assertFalse(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail.web_push_vapid_private_key")
        )

    def test_a_lost_vapid_private_key_regenerates_the_pair(self):
        self.env["credential.credential"]._set_system_secret(
            "mail.web_push_vapid_private_key", False
        )

        new_vapid_public_key = self.env[
            "mail.push.device"
        ].get_or_create_web_push_vapid_public_key()

        self.assertNotEqual(self.vapid_public_key, new_vapid_public_key)
        self.assertFalse(self.env["mail.push.device"].sudo().search_count([]))

    def test_without_an_encryption_key_no_vapid_keys_are_made(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=", "mail.web_push_vapid_public_key")]
        ).unlink()
        Credential = type(self.env["credential.credential"])

        with (
            patch.object(
                Credential, "_is_encryption_key_configured", return_value=False
            ),
            mute_logger("odoo.addons.mail.models.mail_push_device"),
        ):
            public_key = self.env[
                "mail.push.device"
            ].get_or_create_web_push_vapid_public_key()

        self.assertFalse(public_key)
        self.assertFalse(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail.web_push_vapid_public_key")
        )
        self.assertTrue(self.env["mail.push.device"].sudo().search_count([]))

    def test_register_devices_endpoint_rotation(self):
        """A push subscription endpoint rotation must update the existing
        device row in place rather than orphan it and create a duplicate. The
        web client signals the rotation via a snake_case ``previous_endpoint``
        kwarg (the service worker uses camelCase ``previousEndpoint``); both
        must be honored."""
        Device = self.env["mail.push.device"]
        keys = {
            "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
            "auth": "DJFdtAgZwrT6yYkUMgUqow",
        }
        old_endpoint = "https://test.odoo.com/webpush/rotate-old"
        new_endpoint = "https://test.odoo.com/webpush/rotate-new"
        for hint in ("previous_endpoint", "previousEndpoint"):
            with self.subTest(hint=hint):
                Device.sudo().search(
                    [("endpoint", "in", [old_endpoint, new_endpoint])]
                ).unlink()
                Device.with_user(self.user_email).register_devices(
                    endpoint=old_endpoint,
                    expirationTime=None,
                    keys=keys,
                    vapid_public_key=self.vapid_public_key,
                )
                original = Device.sudo().search([("endpoint", "=", old_endpoint)])
                self.assertEqual(len(original), 1)
                # rotation: same subscription, new endpoint, old one passed as hint
                Device.with_user(self.user_email).register_devices(
                    endpoint=new_endpoint,
                    expirationTime=None,
                    keys=keys,
                    vapid_public_key=self.vapid_public_key,
                    **{hint: old_endpoint},
                )
                self.assertFalse(
                    Device.sudo().search([("endpoint", "=", old_endpoint)]),
                    "old endpoint row must be updated in place, not orphaned",
                )
                rotated = Device.sudo().search([("endpoint", "=", new_endpoint)])
                self.assertEqual(
                    rotated, original, "same row, endpoint rotated in place"
                )

    def test_register_devices_coerces_the_expiration_and_validates_the_keys(self):
        Device = self.env["mail.push.device"].with_user(self.user_email)
        endpoint = "https://test.odoo.com/webpush/expiring"
        Device.register_devices(
            endpoint=endpoint,
            expirationTime=1_700_000_000_000,
            keys=self._valid_browser_keys(),
            vapid_public_key=self.vapid_public_key,
        )
        device = Device.sudo().search([("endpoint", "=", endpoint)])
        self.assertEqual(
            device.expiration_time,
            datetime(2023, 11, 14, 22, 13, 20),
            "the Push API sends milliseconds since the epoch",
        )
        Device.register_devices(
            endpoint=endpoint,
            expirationTime=None,
            keys=self._valid_browser_keys(),
            vapid_public_key=self.vapid_public_key,
        )
        self.assertFalse(device.expiration_time)

        bad_endpoint = "https://test.odoo.com/webpush/bad-keys"
        for bad_keys in (
            "not a mapping",
            {"p256dh": "AAAA", "auth": "DJFdtAgZwrT6yYkUMgUqow"},
            {**self._valid_browser_keys(), "auth": "short"},
            {"p256dh": None, "auth": None},
            {"auth": "DJFdtAgZwrT6yYkUMgUqow"},
        ):
            with self.subTest(keys=bad_keys), self.assertRaises(UserError):
                Device.register_devices(
                    endpoint=bad_endpoint,
                    expirationTime=None,
                    keys=bad_keys,
                    vapid_public_key=self.vapid_public_key,
                )
        self.assertFalse(Device.sudo().search([("endpoint", "=", bad_endpoint)]))

    @patch.object(
        requests.Session,
        "post",
        return_value=SimpleNamespace(status_code=201, text="Ok"),
    )
    def test_cron_unlinks_a_device_whose_keys_cannot_be_used(self, post):
        device = (
            self.env["mail.push.device"]
            .sudo()
            .create(
                {
                    "endpoint": "https://test.odoo.com/webpush/undecodable",
                    "keys": json.dumps(
                        {"p256dh": "AAAA", "auth": "DJFdtAgZwrT6yYkUMgUqow"}
                    ),
                    "partner_id": self.user_inbox.partner_id.id,
                }
            )
        )
        notification = (
            self.env["mail.push"]
            .sudo()
            .create(
                {
                    "mail_push_device_id": device.id,
                    "payload": json.dumps({"title": "t"}),
                }
            )
        )
        self._trigger_cron_job()
        self.assertFalse(device.exists(), "keys that never decrypt are a dead device")
        self.assertFalse(notification.exists())
        post.assert_not_called()

    def test_cron_retries_a_notification_the_endpoint_could_not_take(self):
        device = (
            self.env["mail.push.device"]
            .sudo()
            .search([("partner_id", "=", self.user_inbox.partner_id.id)], limit=1)
        )
        notification = (
            self.env["mail.push"]
            .sudo()
            .create(
                {
                    "mail_push_device_id": device.id,
                    "payload": json.dumps({"title": "t"}),
                }
            )
        )
        for status_code, headers, expected_delay in (
            (429, {"Retry-After": "120"}, timedelta(seconds=120)),
            (503, {}, PUSH_ENDPOINT_RETRY_DELAY),
            (500, {"Retry-After": "not a date"}, PUSH_ENDPOINT_RETRY_DELAY),
            (
                429,
                {"Retry-After": "99999999"},
                timedelta(days=PUSH_ENDPOINT_RETRY_DAYS),
            ),
        ):
            with (
                self.subTest(status_code=status_code, headers=headers),
                patch.object(
                    requests.Session,
                    "post",
                    return_value=SimpleNamespace(
                        status_code=status_code, text="later", headers=headers
                    ),
                ) as post,
                mute_logger("odoo.addons.mail.tools.web_push"),
            ):
                notification.retry_after = False
                before = datetime.now()
                self._trigger_cron_job()
                post.assert_called_once()
                self.assertTrue(notification.exists(), "kept for a later attempt")
                self.assertTrue(device.exists(), "the device is not at fault")
                self.assertAlmostEqual(
                    notification.retry_after,
                    before + expected_delay,
                    delta=timedelta(seconds=10),
                )

        with patch.object(requests.Session, "post") as post:
            self._trigger_cron_job()
        post.assert_not_called()

    def test_cron_posts_through_the_guarded_session(self):
        sessions = []

        def post(session, url, **kwargs):
            sessions.append(session.get_adapter(url))
            return SimpleNamespace(status_code=201, text="Ok")

        self.env["mail.push"].sudo().create(
            {
                "mail_push_device_id": self.env["mail.push.device"]
                .sudo()
                .search([], limit=1)
                .id,
                "payload": json.dumps({"title": "t"}),
            }
        )
        with patch.object(requests.Session, "post", autospec=True, side_effect=post):
            self._trigger_cron_job()
        self.assertTrue(sessions)
        for adapter in sessions:
            self.assertIsInstance(adapter, GuardedAdapter)

    @staticmethod
    def _valid_browser_keys():
        return {
            "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
            "auth": "DJFdtAgZwrT6yYkUMgUqow",
        }

    def _push_resolving(self, getaddrinfo):
        device = (
            self.env["mail.push.device"]
            .sudo()
            .search([("partner_id", "=", self.user_email.partner_id.id)], limit=1)
        )
        private_key = self.env["credential.credential"]._get_system_secret(
            "mail.web_push_vapid_private_key"
        )
        with (
            patch("socket.getaddrinfo", **getaddrinfo),
            patch.object(requests.Session, "send", _super_send),
            patch.object(HTTPAdapter, "send") as send,
            mute_logger("odoo.addons.mail.models.mixin_mail_thread"),
        ):
            self.record_simple._web_push_send_notification(
                device, private_key, self.vapid_public_key, payload={"title": "t"}
            )
        send.assert_not_called()
        return device

    def test_web_push_transient_failure_keeps_device(self):
        """A resolution failure is transient and keeps the device; an endpoint
        resolving to a non-public address is a bogus subscription and is deleted."""
        device = self._push_resolving({"side_effect": socket.gaierror})
        self.assertTrue(
            device.exists(), "transient resolution failure must keep the device"
        )
        device = self._push_resolving(
            {"return_value": [(2, 1, 6, "", ("10.0.0.1", 443))]}
        )
        self.assertFalse(
            device.exists(), "endpoint resolving to a non-public address is deleted"
        )

    @patch.object(
        requests.Session,
        "post",
        return_value=SimpleNamespace(status_code=201, text="Ok"),
    )
    @patch.object(
        odoo.addons.mail.models.mixin_mail_thread,
        "push_to_end_point",
        wraps=odoo.addons.mail.tools.web_push.push_to_end_point,
    )
    def test_push_notifications_truncate_payload(
        self, thread_push_mock, session_post_mock
    ):
        """Ensure that when we send large bodies with various character types,
        the final encrypted data (post-encryption) never exceeds 4096 bytes.

        This test checks the behavior for the current size limits and encryption overhead.
        See below test for a more illustrative example.
        See MixinMailThread._truncate_payload for a more thorough explanation.

        Test scenarios include:
        - ASCII characters (X)
        - UTF-8 characters (Ø), at various offsets
        """
        # compute the size of an empty notification with these parameters
        # this could change based on the id of record_simple for example
        # but is otherwise constant for any notification sent with the same parameters
        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body="",
            subject="Test Payload",
        )
        base_payload_size = len(thread_push_mock.call_args.kwargs["payload"].encode())
        effective_payload_size_limit = self.env[
            "mixin.mail.thread"
        ]._truncate_payload_get_max_payload_length()
        # this is just a sanity check that the value makes sense, feel free to update as needed
        self.assertEqual(
            effective_payload_size_limit, 3993, "Payload limit should come out to 3990."
        )
        body_size_limit = effective_payload_size_limit - base_payload_size
        encryption_overhead = ENCRYPTION_HEADER_SIZE + ENCRYPTION_BLOCK_OVERHEAD

        test_cases = (
            [
                # (description, body)
                ("empty string", "", 0, 0),
                (
                    "1-byte ASCII characters (below limit)",
                    "X" * (body_size_limit - 1),
                    body_size_limit - 1,
                    body_size_limit - 1,
                ),
                (
                    "1-byte ASCII characters (at limit)",
                    "X" * body_size_limit,
                    body_size_limit,
                    body_size_limit,
                ),
                (
                    "1-byte ASCII characters (past limit)",
                    "X" * (body_size_limit + 1),
                    body_size_limit,
                    body_size_limit,
                ),
                (
                    "1-byte ASCII characters (way past limit)",
                    "X" * 5000,
                    body_size_limit,
                    body_size_limit,
                ),
            ]
            + [  # \u00d8 check that it can be cut anywhere by offsetting the string by 1 byte each time
                (
                    f"2-bytes UTF-8 characters (near limit + {offset}-byte offset)",
                    ("+" * offset) + ("Ø" * (body_size_limit // 6)),
                    offset
                    + (
                        (body_size_limit - offset) // 6
                    ),  # length truncated to nearest full character (\u00f8)
                    offset * 1 + ((body_size_limit - offset) // 6) * 6,
                )
                for offset in range(8)
            ]
        )

        for description, body, expected_body_length, expected_body_size in test_cases:
            with self.subTest(description):
                self.record_simple.with_user(self.user_email).message_notify(
                    partner_ids=self.user_inbox.partner_id.ids,
                    body=body,
                    subject="Test Payload",
                )

                encrypted_payload = session_post_mock.call_args.kwargs["data"]
                payload_before_encryption = thread_push_mock.call_args.kwargs["payload"]
                self.assertLessEqual(
                    len(encrypted_payload),
                    4096,
                    "Final encrypted payload should not exceed 4096 bytes",
                )
                self.assertEqual(
                    len(json.loads(payload_before_encryption)["options"]["body"]),
                    expected_body_length,
                )
                self.assertEqual(
                    len(encrypted_payload),
                    base_payload_size + expected_body_size + encryption_overhead,
                    "Encrypted size should be exactly the base payload size + body size + encryption overhead.",
                )

    @patch.object(
        requests.Session,
        "post",
        return_value=SimpleNamespace(status_code=201, text="Ok"),
    )
    @patch.object(
        odoo.addons.mail.models.mixin_mail_thread,
        "push_to_end_point",
        wraps=odoo.addons.mail.tools.web_push.push_to_end_point,
    )
    @patch.object(
        odoo.addons.mail.tools.web_push,
        "_encrypt_payload",
        wraps=odoo.addons.mail.tools.web_push._encrypt_payload,
    )
    def test_push_notifications_truncate_payload_mocked_size_limit(
        self, web_push_encrypt_payload_mock, thread_push_mock, session_post_mock
    ):
        """Illustrative test for text contents truncation.

        We want to ensure we truncate utf-8 values properly based on maximum payload size.
        Here max payload size is mocked, so that we can test on the same body each time to ease reading.

        See MixinMailThread._truncate_payload for a more thorough explanation.
        """
        self.record_simple.with_user(self.user_email).message_notify(
            partner_ids=self.user_inbox.partner_id.ids,
            body="",
            subject="Test Payload",
        )
        base_payload = thread_push_mock.call_args.kwargs["payload"].encode()
        base_payload_size = len(base_payload)
        encryption_overhead = ENCRYPTION_HEADER_SIZE + ENCRYPTION_BLOCK_OVERHEAD

        # The overflow is taken out of the LONGEST field, so the body has to be
        # the longest one for this to exercise UTF-8 truncation at all. A
        # realistic title ("<author>: <record name>") escapes to more characters
        # than "BØDY" alone, and would be the field trimmed instead -- which is
        # correct behaviour (see TestWebPushPayloadBudget) but says nothing
        # about multi-byte boundaries. The padding buys that, and nothing else.
        pad = "X" * 40
        body = pad + "BØDY"
        body_json = json.dumps(body)[1:-1]
        for size_limit, expected_body in (
            [
                (base_payload_size + len(body_json), pad + "BØDY"),
                (base_payload_size + len(body_json) - 1, pad + "BØD"),
                (base_payload_size + len(body_json) - 2, pad + "BØ"),
            ]
            + [  # truncating anywhere in \u00d8 (Ø) should truncate to the nearest full character (B)
                (base_payload_size + len(body_json) - n, pad + "B") for n in range(3, 9)
            ]
            + [
                (base_payload_size + len(body_json) - 9, pad),
                (
                    base_payload_size + len(body_json) - 10,
                    pad[:-1],
                ),  # the body keeps giving once the multi-byte tail is gone
            ]
        ):
            with (
                self.subTest(size_limit=size_limit),
                patch.object(
                    odoo.addons.mail.models.mixin_mail_thread.MixinMailThread,
                    "_truncate_payload_get_max_payload_length",
                    return_value=size_limit,
                ),
            ):
                self.record_simple.with_user(self.user_email).message_notify(
                    partner_ids=self.user_inbox.partner_id.ids,
                    body=body,
                    subject="Test Payload",
                )
                payload_at_push = thread_push_mock.call_args.kwargs["payload"]
                payload_before_encrypt = web_push_encrypt_payload_mock.call_args.args[0]
                encrypted_payload = session_post_mock.call_args.kwargs["data"]
                self.assertEqual(
                    payload_before_encrypt.decode(),
                    payload_at_push,
                    "Payload should not change between encryption and push call.",
                )
                self.assertEqual(
                    len(payload_before_encrypt),
                    len(payload_at_push),
                    "Encoded body should be same size as decoded.",
                )
                self.assertEqual(
                    len(encrypted_payload),
                    len(payload_before_encrypt) + encryption_overhead,
                    "Final encrypted payload should just be the size of the unencrypted payload + the size of encryption overhead.",
                )
                self.assertEqual(
                    json.loads(payload_at_push)["options"]["body"], expected_body
                )
                self.assertLessEqual(
                    len(payload_before_encrypt),
                    size_limit,
                    "a trimmed payload must fit the budget it was trimmed for",
                )
                self.assertEqual(
                    json.loads(payload_at_push)["title"],
                    json.loads(base_payload.decode())["title"],
                    "the body is the longest field here, so the title is untouched",
                )
