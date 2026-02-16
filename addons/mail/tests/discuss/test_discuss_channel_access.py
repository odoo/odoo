# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import product
from psycopg2.errors import UniqueViolation

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError
from odoo.tools import mute_logger


class TestDiscussChannelAccess(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # user, visibility_policy, membership, operation
        all_channel_cases = [
            case
            for case in product(
                ["portal", "public", "user"],
                [
                    "group_failing",
                    "group_matching",
                    "internal",
                    "member_and_group_failing",
                    "member_and_group_matching",
                    "public",
                ],
                ["member", "outside"],
                ["create", "read", "unlink", "write"],
            )
            # member+create: doesn't make sense, the channel already exists.
            if case[2] != "member" or case[3] != "create"
        ]
        ok_channel_cases = {
            *product(
                ["portal", "public"],
                ["group_matching", "public"],
                ["member", "outside"],
                ["read"],
            ),
            *product(
                ["portal", "public"],
                ["member", "member_and_group_matching"],
                ["member"],
                ["read"],
            ),
            *product(
                ["user"],
                [
                    "group_matching",
                    "internal",
                    "member",
                    "member_and_group_matching",
                    "public",
                ],
                ["outside"],
                ["create"],
            ),
            *product(
                ["user"],
                ["group_matching", "internal", "public"],
                ["member", "outside"],
                ["read", "write"],
            ),
            *product(
                ["user"],
                ["member", "member_and_group_matching"],
                ["member"],
                ["read", "write"],
            ),
        }
        cls._channel_access_cases = [
            # Membership policy is irrelevant to channel access, ignore it.
            (*case[:2], None, *case[2:], case in ok_channel_cases) for case in all_channel_cases
        ]
        all_channel_member_access_cases = [
            case
            for case in product(
                ["portal", "public", "user"],
                [
                    "group_failing",
                    "group_matching",
                    "internal",
                    "member",
                    "member_and_group_failing",
                    "member_and_group_matching",
                    "public",
                ],
                ["open", "invite", "blocked"],
                ["member", "outside"],
                ["self", "other"],
                ["create", "write", "unlink", "read"],
            )
            if not (
                # self+outside: only create makes sense as the member doesn't exist.
                (case[3] == "outside" and case[4] == "self" and case[5] != "create")
                # self+member+create: doesn't make sense, the member already exists.
                or (case[3] == "member" and case[4] == "self" and case[5] == "create")
            )
        ]
        ok_channel_member_access_cases = {
            # Everyone can read/write/unlink self on accessible channels.
            *product(
                ["portal", "public", "user"],
                [
                    "group_matching",
                    "member",
                    "member_and_group_matching",
                    "public",
                ],
                ["open", "invite", "blocked"],
                ["member"],
                ["self"],
                ["read", "write", "unlink"],
            ),
            *product(
                ["user"],
                ["internal"],
                ["open", "invite", "blocked"],
                ["member"],
                ["self"],
                ["read", "write", "unlink"],
            ),
            # Everyone can read others on accessible channels.
            *product(
                ["portal", "public", "user"],
                ["group_matching", "public"],
                ["open", "invite", "blocked"],
                ["member", "outside"],
                ["other"],
                ["read"],
            ),
            *product(
                ["portal", "public", "user"],
                ["member", "member_and_group_matching"],
                ["open", "invite", "blocked"],
                ["member"],
                ["other"],
                ["read"],
            ),
            *product(
                ["user"],
                ["internal"],
                ["open", "invite", "blocked"],
                ["member", "outside"],
                ["other"],
                ["read"],
            ),
            # Everyone can self-join opened, accessible channels.
            *product(
                ["portal", "public", "user"],
                ["group_matching", "public"],
                ["open"],
                ["outside"],
                ["self"],
                ["create"],
            ),
            ("user", "internal", "open", "outside", "self", "create"),
            # Internal users can create others on accessible channels
            # (according to membership policy).
            *product(
                ["user"],
                ["group_matching", "internal", "public"],
                ["open"],
                ["outside"],
                ["other"],
                ["create"],
            ),
            *product(
                ["user"],
                [
                    "group_matching",
                    "internal",
                    "member",
                    "member_and_group_matching",
                    "public",
                ],
                ["open", "invite"],
                ["member"],
                ["other"],
                ["create"],
            ),
        }
        cls._channel_member_access_cases = [
            (*case, case in ok_channel_member_access_cases) for case in all_channel_member_access_cases
        ]
        cls.secret_group = cls.env["res.groups"].create({"name": "Secret User Group"})
        cls.env["ir.model.data"].create(
            {
                "name": "secret_group",
                "module": "mail",
                "model": cls.secret_group._name,
                "res_id": cls.secret_group.id,
            }
        )
        cls.guest = cls.env["mail.guest"].create({"name": "A Guest"}).sudo(False)
        cls.users = {
            "public": mail_new_test_user(
                cls.env,
                login="public1",
                name="A Public User",
                groups="base.group_everyone,base.group_public,mail.secret_group",
            ),
            "portal": mail_new_test_user(
                cls.env,
                login="portal1",
                name="A Portal User",
                groups="base.group_everyone,base.group_portal,mail.secret_group",
            ),
            "user": mail_new_test_user(
                cls.env,
                login="user1",
                name="An Internal User",
                groups="base.group_everyone,base.group_user,mail.secret_group",
            ),
        }
        cls.other_user = mail_new_test_user(
            cls.env,
            login="other1",
            name="Another User 1",
            groups="base.group_everyone,base.group_user,mail.secret_group",
        )
        cls.other_user_2 = mail_new_test_user(
            cls.env,
            login="other2",
            name="Another User 2",
            groups="base.group_everyone,base.group_user,mail.secret_group",
        )

    def _test_discuss_channel_access(self, cases, for_sub_channel=False):
        """
        Executes a list of operations on channels in various setups and checks whether the outcomes
        match the expected results.

        :param cases: A list of test cases, where each tuple contains:

            - user_key (``"portal"`` | ``"public"`` | ``"user"``): The user performing the operation.
            - visibility_policy (``"internal"`` | ``"public"`` | ``"member_and_group_failing"`` |
                ``"member_and_group_matching"`` | ``"group_failing"`` | ``"group_matching"``
                | ``None``): The visibility policy of the channel.
                ``None`` uses the default policy for the channel type. ``"_matching/_failing"`` policies is used
                to set up channels with groups that either match or do not match the user's groups.
            - membership_policy (``"blocked"`` | ``"open"`` | ``"private"`` | ``None``): The membership policy of
                the channel. ``None`` uses the default policy for the channel type.
            - membership (``"member"`` | ``"outside"``): Whether the user is a member of the channel.
            - operation (``"create"`` | ``"read"`` | ``"write"`` | ``"unlink"``): The action being tested.
            - expected_result (bool): Whether the action is expected to be allowed (``True``) or denied
            (``False``).
        :type cases: List[Tuple[str, str, str, str, bool]]
        :param for_sub_channel: Whether the operation is being tested on a sub-channel. In this case, the
            ``cases`` parameter is used to configure the parent channel.
        """
        for user_key, visibility_policy, membership_policy, membership, operation, result in cases:
            err_msg = (
                f"(user={user_key}, visibility_policy={visibility_policy}, membership_policy={membership_policy}"
                f", membership={membership}, operation={operation}) " + ("should not raise" if result else "should raise")
            )
            if result:
                try:
                    self._execute_action_channel(
                        user_key, visibility_policy, membership_policy, membership, operation, result, for_sub_channel
                    )
                except Exception as e:  # noqa: BLE001 - re-raising, just with a more contextual message
                    raise AssertionError(err_msg) from e
            else:
                try:
                    with self.assertRaises(AccessError), mute_logger("odoo.sql_db"), mute_logger(
                        "odoo.addons.base.models.ir_model"
                    ), mute_logger("odoo.addons.base.models.ir_rule"), mute_logger(
                        "odoo.models.unlink"
                    ):
                        self._execute_action_channel(
                            user_key, visibility_policy, membership_policy, membership, operation, result, for_sub_channel
                        )
                except AssertionError as e:
                    raise AssertionError(err_msg) from e

    def test_01_discuss_channel_access(self):
        self._test_discuss_channel_access(self._channel_access_cases)

    def test_02_discuss_sub_channel_access(self):
        self._test_discuss_channel_access(
            self._channel_access_cases,
            for_sub_channel=True,
        )

    def _test_discuss_channel_member_access(self, cases, for_sub_channel=False):
        """
        Executes a list of operations on channel members in various setups and checks whether the
        outcomes match the expected results.

        :param cases: A list of test cases, where each tuple contains:
            - user_key (``"portal"`` | ``"public"`` | ``"user"``):
                The user performing the operation.
            - channel_type (``"channel"`` | ``"chat"`` | ``"group"``): The type of the channel.
            - visibility_policy (``"internal"`` | ``"public"`` | ``"member_and_group_failing"`` |
                ``"member_and_group_matching"`` | ``"group_failing"`` | ``"group_matching"``
                | ``None``): The visibility policy of the channel.
                ``None`` uses the default policy for the channel type. ``"_matching/_failing"`` policies is used
                to set up channels with groups that either match or do not match the user's groups.
            - membership_policy (``"blocked"`` | ``"open"`` | ``"private"`` | ``None``): The membership policy of
                the channel. ``None`` uses the default policy for the channel type.
            - membership (``"member"`` | ``"outside"``):
                Whether the user is a member of the channel.
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
        for user_key, visibility_key, membership_policy, membership, target, operation, result in cases:
            group_config = None
            visibility_policy = visibility_key
            if visibility_key:
                parts = visibility_key.split("_")
                if parts[-1] in {"matching", "failing"}:
                    group_config = parts[-1]
                    visibility_policy = "_".join(parts[:-1])
            err_msg = (
                f"(user={user_key}, visibility_policy={visibility_policy}, group_config={group_config}"
                f", membership_policy={membership_policy}, membership={membership}, target={target}"
                f", operation={operation})  " + ("should not raise" if result else "should raise")
            )
            channel_id = self._get_channel_id(user_key, visibility_policy, membership_policy, group_config, membership, for_sub_channel)
            if result:
                try:
                    self._execute_action_member(channel_id, user_key, target, operation, result)
                except Exception as e:  # noqa: BLE001 - re-raising, just with a more contextual message
                    raise AssertionError(err_msg) from e
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
                    raise AssertionError(err_msg) from e

    def test_10_discuss_channel_member_access(self):
        self._test_discuss_channel_member_access(self._channel_member_access_cases)

    def test_11_discuss_sub_channel_member_access(self):
        self._test_discuss_channel_member_access(
            self._channel_member_access_cases,
            for_sub_channel=True,
        )

    def _get_channel_id(self, user_key, visibility_policy, membership_policy, group_config, membership, sub_channel):
        user = self.env["res.users"] if user_key == "public" else self.users[user_key]
        partner = user.partner_id
        guest = self.guest if user_key == "public" else self.env["mail.guest"]
        partners = self.other_user.partner_id
        if membership == "member":
            partners += partner
        DiscussChannel = self.env["discuss.channel"].with_user(self.other_user)
        channel = DiscussChannel.create(
            {
                "channel_type": "channel",
                "name": f"channel_visibility_{visibility_policy}_membership_{membership_policy}",
            },
        )
        if membership == "member":
            channel.sudo()._add_members(users=user, guests=guest)
        if membership_policy:
            channel.membership_policy = membership_policy
        if visibility_policy:
            channel.visibility_policy = visibility_policy
        if group_config == "matching":
            channel.group_public_id = self.secret_group
        elif group_config == "failing":
            channel.group_public_id = self.env.ref("base.group_system")
        if sub_channel:
            channel.sudo()._create_sub_channel()
            channel = channel.sub_channel_ids[0]
            if membership == "member":
                channel.sudo()._add_members(users=user, guests=guest)
        return channel.id

    def _execute_action_channel(self, user_key, visibility_key, membership_policy, membership, operation, result, for_sub_channel=False):
        current_user = self.users[user_key]
        guest = self.guest if user_key == "public" else self.env["mail.guest"]
        ChannelAsUser = self.env["discuss.channel"].with_user(current_user).with_context(guest=guest)
        group_config = None
        visibility_policy = visibility_key
        if visibility_key:
            parts = visibility_key.split("_")
            if parts[-1] in {"matching", "failing"}:
                group_config = parts[-1]
                visibility_policy = "_".join(parts[:-1])
        group_public_id = None
        if operation == "create":
            group_public_id = None
            if group_config == "matching":
                group_public_id = self.secret_group.id
            elif group_config == "failing":
                group_public_id = self.env.ref("base.group_system").id
            data = {"name": "Test Channel", "channel_type": "channel", "group_public_id": group_public_id}
            if visibility_policy:
                data["visibility_policy"] = visibility_policy
            if membership_policy:
                data["membership_policy"] = membership_policy
            ChannelAsUser.create(data)
        else:
            channel = ChannelAsUser.browse(
                self._get_channel_id(user_key, visibility_policy, membership_policy, group_config, membership, for_sub_channel)
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
                member.read(["custom_notifications"])
            elif operation == "write":
                member.write({"custom_notifications": "mentions"})
            elif operation == "unlink":
                member.unlink()

    def test_channel_type_default_policies(self):
        chat = self.env["discuss.channel"].create({"channel_type": "chat", "name": "Chat"})
        self.assertEqual(chat.visibility_policy, "member")
        self.assertEqual(chat.membership_policy, "blocked")
        channel = self.env["discuss.channel"].create({"channel_type": "channel", "name": "Channel"})
        self.assertEqual(channel.visibility_policy, "member")
        self.assertEqual(channel.membership_policy, "invite")
        group = self.env["discuss.channel"].create({"channel_type": "group", "name": "Group"})
        self.assertEqual(group.visibility_policy, "member")
        self.assertEqual(group.membership_policy, "invite")
