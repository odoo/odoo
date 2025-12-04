# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import product
from psycopg2.errors import UniqueViolation

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import mute_logger


class TestDiscussChannelAccess(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        channel_cases = {
            *product(
                ["portal", "public", "user"],
                ["public", "internal", "invite_only"],
                ["member", "outside"],
                ["write", "read", "unlink"],
            ),
            *product(
                ["public", "portal", "user"],
                ["public", "internal", "invite_only"],
                ["outside"],
                ["create"],
            ),
        }
        channel_allowed = {
            # user, access_type, membership, operation
            *product(["portal", "public"], ["public"], ["member", "outside"], ["read"]),
            *product(["user"], ["internal", "public"], ["member", "outside"], ["read", "write"]),
            *product(["user"], ["invite_only"], ["member"], ["read", "write"]),
            *product(["user"], ["public", "internal", "invite_only"], ["outside"], ["create"]),
        }
        cls._channel_type_channel_access_cases = [
            (*case, case in channel_allowed) for case in channel_cases
        ]
        member_cases = {
            *product(
                ["portal", "public", "user"],
                ["public", "internal", "invite_only"],
                ["member"],
                ["other", "self"],
                ["create", "read", "unlink", "write"],
            ),
            *product(
                ["portal", "public", "user"],
                ["public", "internal", "invite_only"],
                ["outside"],
                ["other"],
                ["create", "read", "unlink", "write"],
            ),
        }
        member_allowed = {
            # user, access_type, membership, target, operation
            *product(["public", "portal"], ["public"], ["member", "outside"], ["other"], ["read"]),
            *product(["public", "portal"], ["public"], ["outside"], ["self"], ["create"]),
            *product(
                ["public", "portal"], ["public"], ["member"], ["self"], ["read", "unlink", "write"]
            ),
            *product(
                ["user"],
                ["public", "internal"],
                ["member", "outside"],
                ["other"],
                ["create", "read"],
            ),
            *product(["user"], ["public", "internal"], ["outside"], ["self"], ["create"]),
            ("user", "invite_only", "member", "other", "create"),
            *product(
                ["user"], ["public", "internal"], ["member"], ["self"], ["read", "unlink", "write"]
            ),
            *product(["user"], ["invite_only"], ["member"], ["self", "other"], ["read"]),
            *product(["user"], ["invite_only"], ["member"], ["self"], ["unlink", "write"]),
        }
        cls._channel_type_channel_member_access_cases = [
            (*case, case in member_allowed) for case in member_cases
        ]
        cls._group_type_channel_access_cases = [
            ("public", "group", "member", "read", True),
            ("public", "group", "member", "write", False),
            ("public", "group", "member", "unlink", False),
            ("public", "group", "outside", "create", False),
            ("public", "group", "outside", "read", False),
            ("public", "group", "outside", "write", False),
            ("public", "group", "outside", "unlink", False),
            ("portal", "group", "member", "read", True),
            ("portal", "group", "member", "write", False),
            ("portal", "group", "member", "unlink", False),
            ("portal", "group", "outside", "create", False),
            ("portal", "group", "outside", "read", False),
            ("portal", "group", "outside", "write", False),
            ("portal", "group", "outside", "unlink", False),
            ("user", "group", "member", "read", True),
            ("user", "group", "member", "write", True),
            ("user", "group", "member", "unlink", False),
            ("user", "group", "outside", "create", True),
            ("user", "group", "outside", "read", False),
            ("user", "group", "outside", "write", False),
            ("user", "group", "outside", "unlink", False),
        ]
        cls._group_type_channel_member_access_cases = [
            ("public", "group", "member", "self", "create", False),
            ("public", "group", "member", "self", "read", True),
            ("public", "group", "member", "self", "write", True),
            ("public", "group", "member", "self", "unlink", True),
            ("public", "group", "member", "other", "create", False),
            ("public", "group", "member", "other", "read", True),
            ("public", "group", "member", "other", "write", False),
            ("public", "group", "member", "other", "unlink", False),
            ("public", "group", "outside", "self", "create", False),
            ("public", "group", "outside", "other", "create", False),
            ("public", "group", "outside", "other", "read", False),
            ("public", "group", "outside", "other", "write", False),
            ("public", "group", "outside", "other", "unlink", False),
            ("portal", "group", "member", "self", "create", False),
            ("portal", "group", "member", "self", "read", True),
            ("portal", "group", "member", "self", "write", True),
            ("portal", "group", "member", "self", "unlink", True),
            ("portal", "group", "member", "other", "create", False),
            ("portal", "group", "member", "other", "read", True),
            ("portal", "group", "member", "other", "write", False),
            ("portal", "group", "member", "other", "unlink", False),
            ("portal", "group", "outside", "self", "create", False),
            ("portal", "group", "outside", "other", "create", False),
            ("portal", "group", "outside", "other", "read", False),
            ("portal", "group", "outside", "other", "write", False),
            ("portal", "group", "outside", "other", "unlink", False),
            ("user", "group", "member", "self", "create", False),
            ("user", "group", "member", "self", "read", True),
            ("user", "group", "member", "self", "write", True),
            ("user", "group", "member", "self", "unlink", True),
            ("user", "group", "member", "other", "create", True),
            ("user", "group", "member", "other", "read", True),
            ("user", "group", "member", "other", "write", False),
            ("user", "group", "member", "other", "unlink", False),
            ("user", "group", "outside", "self", "create", False),
            ("user", "group", "outside", "other", "create", False),
            ("user", "group", "outside", "other", "read", False),
            ("user", "group", "outside", "other", "write", False),
            ("user", "group", "outside", "other", "unlink", False),
        ]
        cls.guest = cls.env["mail.guest"].create({"name": "A Guest"}).sudo(False)
        cls.users = {
            "public": mail_new_test_user(
                cls.env,
                login="public1",
                name="A Public User",
                groups="base.group_public",
            ),
            "portal": mail_new_test_user(
                cls.env,
                login="portal1",
                name="A Portal User",
                groups="base.group_portal",
            ),
            "user": mail_new_test_user(
                cls.env,
                login="user1",
                name="An Internal User",
                groups="base.group_user",
            ),
        }
        cls.other_user = mail_new_test_user(
            cls.env,
            login="other1",
            name="Another User 1",
            groups="base.group_user",
        )
        cls.other_user_2 = mail_new_test_user(
            cls.env,
            login="other2",
            name="Another User 2",
            groups="base.group_user",
        )

    def _test_discuss_channel_access(self, cases, for_sub_channel):
        """
        Executes a list of operations on channels in various setups and checks whether the outcomes
        match the expected results.

        :param cases: A list of test cases, where each tuple contains:

            - user_key (``"portal"`` | ``"public"`` | ``"user"``): The user performing the operation.
            - access_type (``"chat"`` | ``"group"`` | ``"internal"`` | ``"invite_only"`` | ``"public"``):
            The access specification to use. ``chat`` and ``group`` define the channel type, while the
            others configure access setups for the channels.
            - membership (``"member"`` | ``"outside"``): Whether the user is a member of the channel.
            - operation (``"create"`` | ``"read"`` | ``"write"`` | ``"unlink"``): The action being tested.
            - expected_result (bool): Whether the action is expected to be allowed (``True``) or denied
            (``False``).
        :type cases: List[Tuple[str, str, str, str, bool]]
        :param for_sub_channel: Whether the operation is being tested on a sub-channel. In this case, the
            ``cases`` parameter is used to configure the parent channel.
        """
        for user_key, access_type, membership, operation, result in cases:
            if result:
                try:
                    self._execute_action_channel(
                        user_key, access_type, membership, operation, result, for_sub_channel
                    )
                except Exception as e:  # noqa: BLE001 - re-raising, just with a more contextual message
                    raise AssertionError(
                        f"{user_key, access_type, membership, operation} should not raise"
                    ) from e
            else:
                try:
                    with self.assertRaises(AccessError), mute_logger("odoo.sql_db"), mute_logger(
                        "odoo.addons.base.models.ir_model"
                    ), mute_logger("odoo.addons.base.models.ir_rule"), mute_logger(
                        "odoo.models.unlink"
                    ):
                        self._execute_action_channel(
                            user_key, access_type, membership, operation, result, for_sub_channel
                        )
                except AssertionError as e:
                    raise AssertionError(
                        f"{user_key, access_type, membership, operation} should raise"
                    ) from e

    def test_01_discuss_channel_access(self):
        cases = [
            *self._channel_type_channel_access_cases,
            *self._group_type_channel_access_cases,
            ("public", "chat", "outside", "create", False),
            ("public", "chat", "outside", "read", False),
            ("public", "chat", "outside", "write", False),
            ("public", "chat", "outside", "unlink", False),
            ("portal", "chat", "member", "read", True),
            ("portal", "chat", "member", "write", False),
            ("portal", "chat", "member", "unlink", False),
            ("portal", "chat", "outside", "create", False),
            ("portal", "chat", "outside", "read", False),
            ("portal", "chat", "outside", "write", False),
            ("portal", "chat", "outside", "unlink", False),
            ("user", "chat", "member", "read", True),
            ("user", "chat", "member", "write", True),
            ("user", "chat", "member", "unlink", False),
            ("user", "chat", "outside", "create", True),
            ("user", "chat", "outside", "read", False),
            ("user", "chat", "outside", "write", False),
            ("user", "chat", "outside", "unlink", False),
        ]
        self._test_discuss_channel_access(cases, for_sub_channel=False)

    def test_02_discuss_sub_channel_access(self):
        cases = [
            *self._channel_type_channel_access_cases,
            ("user", "invite_only", "member_of_parent", "read", True),
            ("user", "invite_only", "member_of_parent", "write", True),
            ("user", "invite_only", "member_of_parent", "unlink", False),
            *self._group_type_channel_access_cases,
        ]
        self._test_discuss_channel_access(cases, for_sub_channel=True)

    def _test_discuss_channel_member_access(self, cases, for_sub_channel):
        """
        Executes a list of operations on channel members in various setups and checks whether the
        outcomes match the expected results.

        :param cases: A list of test cases, where each tuple contains:
            - user_key (``"portal"`` | ``"public"`` | ``"user"``):
                The user performing the operation.
            - access_type (``"chat"`` | ``"group"`` | ``"internal"`` | ``"invite_only"`` |
            ``"public"``):
                The group specification to use. ``chat`` and ``group`` define the channel type, while the
                others configure group setups for the channels.
            - membership (``"member"`` | ``"outside"`` | ``"member_of_parent"``):
                Whether the user is a member of the channel. ``member_of_parent`` means ``outside`` of the
                sub-channel, but ``member`` of the parent channel.
            - target (``"self"`` | ``"other"``):
                Whether the operation is executed on the self-member or another member.
            - operation (``"create"`` | ``"read"`` | ``"write"`` | ``"unlink"``):
                The action being tested.
            - expected_result (bool):
                Whether the action is expected to be allowed (``True``) or denied (``False``).
        :type cases: List[Tuple[str, str, str, str, str, bool]]
        :param for_sub_channel: Whether the operation is being tested on a sub-channel. In this case, the
            ``cases`` parameter is used to configure the parent channel's member.
        """
        for user_key, access_type, membership, target, operation, result in cases:
            channel_id = self._get_channel_id(user_key, access_type, membership, for_sub_channel)
            if result:
                try:
                    self._execute_action_member(channel_id, user_key, target, operation, result)
                except Exception as e:  # noqa: BLE001 - re-raising, just with a more contextual message
                    raise AssertionError(
                        f"{user_key, access_type, membership, target, operation} should not raise"
                    ) from e
            else:
                try:
                    with self.assertRaises(AccessError), mute_logger("odoo.sql_db"), mute_logger(
                        "odoo.addons.base.models.ir_model"
                    ), mute_logger("odoo.addons.base.models.ir_rule"), mute_logger(
                        "odoo.models.unlink"
                    ):
                        try:
                            self._execute_action_member(
                                channel_id, user_key, target, operation, result
                            )
                        except (UniqueViolation, UserError) as e:
                            raise AccessError("expected errors as access error") from e
                except AssertionError as e:
                    raise AssertionError(
                        f"{user_key, access_type, membership, target, operation} should raise access error"
                    ) from e

    def test_10_discuss_channel_member_access(self):
        cases = [
            *self._channel_type_channel_member_access_cases,
            *self._group_type_channel_member_access_cases,
            ("public", "chat", "outside", "self", "create", False),
            ("public", "chat", "outside", "other", "create", False),
            ("public", "chat", "outside", "other", "read", False),
            ("public", "chat", "outside", "other", "write", False),
            ("public", "chat", "outside", "other", "unlink", False),
            ("portal", "chat", "member", "self", "create", False),
            ("portal", "chat", "member", "self", "read", True),
            ("portal", "chat", "member", "self", "write", True),
            ("portal", "chat", "member", "self", "unlink", True),
            ("portal", "chat", "member", "other", "create", False),
            ("portal", "chat", "member", "other", "read", True),
            ("portal", "chat", "member", "other", "write", False),
            ("portal", "chat", "member", "other", "unlink", False),
            ("portal", "chat", "outside", "self", "create", False),
            ("portal", "chat", "outside", "other", "create", False),
            ("portal", "chat", "outside", "other", "read", False),
            ("portal", "chat", "outside", "other", "write", False),
            ("portal", "chat", "outside", "other", "unlink", False),
            ("user", "chat", "member", "self", "create", False),
            ("user", "chat", "member", "self", "read", True),
            ("user", "chat", "member", "self", "write", True),
            ("user", "chat", "member", "self", "unlink", True),
            ("user", "chat", "member", "other", "create", False),
            ("user", "chat", "member", "other", "read", True),
            ("user", "chat", "member", "other", "write", False),
            ("user", "chat", "member", "other", "unlink", False),
            ("user", "chat", "outside", "self", "create", False),
            ("user", "chat", "outside", "other", "create", False),
            ("user", "chat", "outside", "other", "read", False),
            ("user", "chat", "outside", "other", "write", False),
            ("user", "chat", "outside", "other", "unlink", False),
        ]
        self._test_discuss_channel_member_access(cases, for_sub_channel=False)

    def test_11_discuss_sub_channel_member_access(self):
        cases = [
            *self._channel_type_channel_member_access_cases,
            *self._group_type_channel_member_access_cases,
            ("user", "invite_only", "member_of_parent", "read", "other", True),
        ]
        self._test_discuss_channel_member_access(cases, for_sub_channel=True)

    def _get_channel_id(self, user_key, access_type, membership, sub_channel):
        user = self.env["res.users"] if user_key == "public" else self.users[user_key]
        partner = user.partner_id
        guest = self.guest if user_key == "public" else self.env["mail.guest"]
        partners = self.other_user.partner_id
        if membership == "member":
            partners += partner
        DiscussChannel = self.env["discuss.channel"].with_user(self.other_user)
        if access_type == "group":
            channel = DiscussChannel._create_group(partners.ids)
            if membership == "member":
                channel._add_members(users=user, guests=guest)
        elif access_type == "chat":
            channel = DiscussChannel._get_or_create_chat(partners.ids)
        else:
            channel = DiscussChannel._create_channel(access_type=access_type, name="Channel")
            if membership == "member":
                channel.sudo()._add_members(users=user, guests=guest)
        if sub_channel:
            channel.sudo()._create_sub_channel()
            channel = channel.sub_channel_ids[0]
            if membership == "member":
                channel.sudo()._add_members(users=user, guests=guest)
            elif membership == "member_of_parent":
                channel.parent_channel_id.sudo()._add_members(users=user, guests=guest)
        return channel.id

    def _execute_action_channel(self, user_key, access_type, membership, operation, result, for_sub_channel):
        current_user = self.users[user_key]
        guest = self.guest if user_key == "public" else self.env["mail.guest"]
        ChannelAsUser = self.env["discuss.channel"].with_user(current_user).with_context(guest=guest)
        if operation == "create":
            data = {
                "access_type": access_type if access_type in ("internal", "invite_only", "public") else None,
                "name": "Test Channel",
                "channel_type": access_type if access_type in ("group", "chat") else "channel",
            }
            ChannelAsUser.create(data)
        else:
            channel = ChannelAsUser.browse(
                self._get_channel_id(user_key, access_type, membership, for_sub_channel)
            )
            self.assertEqual(len(channel), 1, "should find the channel")
            if operation == "read":
                self.assertEqual(len(ChannelAsUser.search([("id", "=", channel.id)])), 1 if result else 0)
                channel.read(["name"])
            elif operation == "write":
                channel.write({"name": "new name"})
            elif operation == "unlink":
                channel.unlink()

    def _execute_action_member(self, channel_id, user_key, target, operation, result):
        current_user = self.users[user_key]
        partner = self.env["res.partner"] if user_key == "public" else current_user.partner_id
        guest = self.guest if user_key == "public" else self.env["mail.guest"]
        ChannelMemberAsUser = self.env["discuss.channel.member"].with_user(current_user).with_context(guest=guest)
        if operation == "create":
            create_data = {"channel_id": channel_id}
            if target == "self":
                if guest:
                    create_data["guest_id"] = guest.id
                else:
                    create_data["partner_id"] = partner.id
            else:
                create_data["partner_id"] = self.other_user_2.partner_id.id
            ChannelMemberAsUser.create(create_data)
        else:
            domain = [("channel_id", "=", channel_id)]
            if target == "self":
                if guest:
                    domain.append(("guest_id", "=", guest.id))
                else:
                    domain.append(("partner_id", "=", partner.id))
            else:
                domain.append(("partner_id", "=", self.other_user.partner_id.id))
            member = ChannelMemberAsUser.sudo().search(domain).sudo(False)
            self.assertEqual(len(member), 1, "should find the target member")
            if operation == "read":
                self.assertEqual(len(ChannelMemberAsUser.search(domain)), 1 if result else 0)
                member.read(["custom_channel_name"])
            elif operation == "write":
                member.write({"custom_channel_name": "new name"})
            elif operation == "unlink":
                member.unlink()
