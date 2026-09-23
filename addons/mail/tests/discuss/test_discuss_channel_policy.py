from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.tools import format_list

from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestDiscussChannelTypePolicy(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Channel = cls.env["discuss.channel"]

    def _channel_of_type(self, channel_type):
        if channel_type == "chat":
            return self.Channel._get_or_create_chat([self.partner_employee.id])
        if channel_type == "group":
            return self.Channel._create_group([self.partner_employee.id])
        return self.Channel.create({"name": "C", "channel_type": channel_type})

    def test_the_matrix_covers_every_declared_channel_type(self):
        declared = {
            code for code, _label in self.Channel._fields["channel_type"].selection
        }
        self.assertEqual(
            declared,
            set(self.Channel._channel_type_policies()),
            "A channel_type was declared without a policy row. The module that "
            "adds the type decides each policy for it, in its own "
            "_channel_type_policies override.",
        )

    def test_the_three_native_rows_are_pinned(self):
        policies = self.Channel._channel_type_policies()
        self.assertTrue(policies["chat"].push_icon_is_sender)
        self.assertEqual(policies["chat"].max_members, 2)
        self.assertEqual(policies["channel"].email_invite, "public_only")
        self.assertTrue(policies["channel"].supports_sub_channels)
        self.assertTrue(policies["group"].member_based_naming)
        self.assertFalse(policies["group"].supports_group_authorization)

    def test_narrating_membership_changes_is_every_type_but_channel(self):
        expected = {"chat": True, "channel": False, "group": True}
        for channel_type, narrates in expected.items():
            with self.subTest(channel_type=channel_type):
                channel = self._channel_of_type(channel_type)
                self.assertEqual(channel._narrates_membership_changes(), narrates)

    def test_notify_opted_in_only_is_channel_only(self):
        opt_in = self.Channel._types_with("notify_opted_in_only")
        self.assertEqual(opt_in, ["channel"])

    def test_auto_inviting_to_call_is_every_type_but_channel(self):
        expected = {"chat": True, "channel": False, "group": True}
        for channel_type, invites in expected.items():
            with self.subTest(channel_type=channel_type):
                channel = self._channel_of_type(channel_type)
                self.assertEqual(channel._auto_invites_members_to_call(), invites)

    def test_group_authorization_is_channel_only(self):
        supported = self.Channel._types_supporting_group_authorization()
        self.assertIn("channel", supported)
        self.assertNotIn("chat", supported)
        self.assertNotIn("group", supported)

    def test_the_sql_check_is_built_from_the_policy(self):
        self.env.cr.execute(
            """
            SELECT pg_get_constraintdef(oid)
              FROM pg_constraint
             WHERE conrelid = 'discuss_channel'::regclass
               AND conname = 'discuss_channel_group_public_id_check'
            """
        )
        [(definition,)] = self.env.cr.fetchall()
        for channel_type in self.Channel._types_supporting_group_authorization():
            self.assertIn(channel_type, definition)

    def test_group_authorization_is_refused_for_other_types(self):
        for channel_type in ("chat", "group"):
            with (
                self.subTest(channel_type=channel_type),
                self.assertRaises(ValidationError),
            ):
                self._channel_of_type(channel_type).write(
                    {"group_public_id": self.env.ref("base.group_user").id}
                )


@tagged("post_install", "-at_install")
class TestDiscussChannelPolicyRegressions(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Channel = cls.env["discuss.channel"]

    def test_searching_partners_negatively_means_has_no_such_member(self):
        other = self.env["res.partner"].create({"name": "Outside"})
        channel = self.Channel.create(
            {
                "name": "C",
                "channel_type": "channel",
                "channel_partner_ids": [
                    (4, self.partner_employee.id),
                    (4, self.partner_admin.id),
                ],
            }
        )
        scope = [("id", "=", channel.id)]
        self.assertTrue(
            self.Channel.search(
                scope + [("channel_partner_ids", "in", [self.partner_employee.id])]
            )
        )
        self.assertFalse(
            self.Channel.search(
                scope + [("channel_partner_ids", "not in", [self.partner_employee.id])],
            ),
            "the partner IS a member, so the channel must not match 'not in'",
        )
        self.assertFalse(
            self.Channel.search(
                scope + [("channel_partner_ids", "!=", self.partner_employee.id)]
            )
        )
        self.assertTrue(
            self.Channel.search(
                scope + [("channel_partner_ids", "not in", [other.id])]
            ),
            "a non-member must still match 'not in'",
        )

    def test_receiving_a_bounce_honours_the_multi_record_contract(self):
        channels = self.Channel.create(
            [
                {"name": "A", "channel_type": "channel"},
                {"name": "B", "channel_type": "channel"},
            ]
        )
        partner = self.env["res.partner"].create(
            {"name": "Bouncy", "email": "bouncy@example.com"}
        )
        partner.message_bounce = self.Channel.MAX_BOUNCE_LIMIT + 1
        channels._message_receive_bounce("bouncy@example.com", partner)

    def test_a_member_with_a_blank_name_is_omitted_not_rendered_as_False(self):
        blank = self.env["res.partner"].create({"name": ""})
        named = self.env["res.partner"].create({"name": "Ana"})
        group = self.Channel._create_group([named.id, blank.id])
        self.assertNotIn("False", group.display_name)
        self.assertIn("Ana", group.display_name)

    def test_creating_with_a_falsy_x2many_is_accepted_as_everywhere_else(self):
        channel = self.Channel.create(
            {"name": "C", "channel_type": "channel", "channel_member_ids": False}
        )
        self.assertTrue(channel)

    def test_inviting_by_email_refuses_a_multi_record_set_at_the_boundary(self):
        channels = self.Channel.create(
            [
                {"name": "A", "channel_type": "group"},
                {"name": "B", "channel_type": "group"},
            ]
        )
        with self.assertRaises(ValueError):
            channels.invite_by_email(["someone@example.com"])

    def test_the_push_title_is_the_display_name_not_a_second_rendering(self):
        partners = self.env["res.partner"].create(
            [{"name": name} for name in ("Ana", "Bo", "Cy", "Di")]
        )
        group = self.Channel._create_group(partners.ids)
        message = group.message_post(
            body="hi", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        payload = group._notify_by_web_push_prepare_payload(message)
        self.assertEqual(
            payload["title"], f"{group.display_name} - {message.author_id.name}"
        )
        self.assertIn(
            "other",
            group.display_name,
            "display_name caps the list, so the push title inherits the cap",
        )

    def test_the_member_link_list_is_rendered_once_by_one_helper(self):
        group = self.Channel._create_group([self.partner_employee.id])
        members = group.channel_member_ids
        rendered = members._format_html_link_list()
        for member in members:
            self.assertIn(member._get_persona_name(), rendered)
        self.assertEqual(
            self.env["discuss.channel.member"]._format_html_link_list(),
            "",
            "an empty recordset renders as nothing, not as a stray separator",
        )
        with_trailer = members._format_html_link_list((self.env._("you"),))
        self.assertIn("you", with_trailer)
        self.assertEqual(
            with_trailer.count("<a"),
            len(members),
            "the trailer is a plain item, never a link",
        )

    def test_the_persona_name_never_leaks_a_recordset_falsy(self):
        blank = self.env["res.partner"].create({"name": ""})
        group = self.Channel._create_group([blank.id])
        member = group.channel_member_ids.filtered(lambda m: m.partner_id == blank)
        self.assertEqual(member._get_persona_name(), "")
        self.assertEqual(
            format_list(self.env, [member._get_persona_name()]),
            "",
            "an empty name must not become the string 'False'",
        )


@tagged("post_install", "-at_install")
class TestDiscussChannelInviteLookup(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Channel = cls.env["discuss.channel"]

    def test_an_address_is_data_not_a_like_pattern(self):
        member = self.env["res.partner"].create({"name": "M", "email": "a-b@x.com"})
        group = self.Channel._create_group([member.id])
        self.assertEqual(
            list(group._get_uninvited_emails(["a_b@x.com"])),
            ["a_b@x.com"],
            "'a_b@x.com' is a different address from the member's 'a-b@x.com'",
        )

    def test_the_member_own_address_is_still_excluded(self):
        member = self.env["res.partner"].create({"name": "M", "email": "a-b@x.com"})
        group = self.Channel._create_group([member.id])
        self.assertEqual(list(group._get_uninvited_emails(["a-b@x.com"])), [])

    def test_the_lookup_stays_case_insensitive(self):
        member = self.env["res.partner"].create({"name": "M", "email": "a-b@x.com"})
        group = self.Channel._create_group([member.id])
        self.assertEqual(list(group._get_uninvited_emails(["A-B@X.com"])), [])

    def test_joined_notification_lives_on_the_member_model(self):
        self.assertTrue(hasattr(self.env["discuss.channel.member"], "_notify_joined"))
        self.assertFalse(hasattr(self.Channel, "_notify_members_joined"))
        member = self.env["res.partner"].create({"name": "M"})
        channels = self.Channel.create(
            [
                {"name": "c1", "channel_type": "channel"},
                {"name": "c2", "channel_type": "channel"},
            ]
        )
        self.assertEqual(len(channels._add_members(partners=member)), 2)
