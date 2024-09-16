# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errors import UniqueViolation

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestDiscussChannelAccess(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._channel_type_channel_access_cases = [
            ("public", "no_group", "member", "read", True),
            ("public", "no_group", "member", "write", False),
            ("public", "no_group", "member", "unlink", False),
            ("public", "no_group", "outside", "create", False),
            ("public", "no_group", "outside", "read", True),
            ("public", "no_group", "outside", "write", False),
            ("public", "no_group", "outside", "unlink", False),
            ("public", "group_matching", "member", "read", True),
            ("public", "group_matching", "member", "write", False),
            ("public", "group_matching", "member", "unlink", False),
            ("public", "group_matching", "outside", "create", False),
            ("public", "group_matching", "outside", "read", True),
            ("public", "group_matching", "outside", "write", False),
            ("public", "group_matching", "outside", "unlink", False),
            ("public", "group_failing", "member", "read", False),
            ("public", "group_failing", "member", "write", False),
            ("public", "group_failing", "member", "unlink", False),
            ("public", "group_failing", "outside", "create", False),
            ("public", "group_failing", "outside", "read", False),
            ("public", "group_failing", "outside", "write", False),
            ("public", "group_failing", "outside", "unlink", False),
            ("portal", "no_group", "member", "read", True),
            ("portal", "no_group", "member", "write", False),
            ("portal", "no_group", "member", "unlink", False),
            ("portal", "no_group", "outside", "create", False),
            ("portal", "no_group", "outside", "read", True),
            ("portal", "no_group", "outside", "write", False),
            ("portal", "no_group", "outside", "unlink", False),
            ("portal", "group_matching", "member", "read", True),
            ("portal", "group_matching", "member", "write", False),
            ("portal", "group_matching", "member", "unlink", False),
            ("portal", "group_matching", "outside", "create", False),
            ("portal", "group_matching", "outside", "read", True),
            ("portal", "group_matching", "outside", "write", False),
            ("portal", "group_matching", "outside", "unlink", False),
            ("portal", "group_failing", "member", "read", False),
            ("portal", "group_failing", "member", "write", False),
            ("portal", "group_failing", "member", "unlink", False),
            ("portal", "group_failing", "outside", "create", False),
            ("portal", "group_failing", "outside", "read", False),
            ("portal", "group_failing", "outside", "write", False),
            ("portal", "group_failing", "outside", "unlink", False),
            ("user", "no_group", "member", "read", True),
            ("user", "no_group", "member", "write", True),
            ("user", "no_group", "member", "unlink", False),
            ("user", "no_group", "outside", "create", True),
            ("user", "no_group", "outside", "read", True),
            ("user", "no_group", "outside", "write", True),
            ("user", "no_group", "outside", "unlink", False),
            ("user", "group_matching", "member", "read", True),
            ("user", "group_matching", "member", "write", True),
            ("user", "group_matching", "member", "unlink", False),
            ("user", "group_matching", "outside", "create", True),
            ("user", "group_matching", "outside", "read", True),
            ("user", "group_matching", "outside", "write", True),
            ("user", "group_matching", "outside", "unlink", False),
            ("user", "group_failing", "member", "read", False),
            ("user", "group_failing", "member", "write", False),
            ("user", "group_failing", "member", "unlink", False),
            ("user", "group_failing", "outside", "create", False),
            ("user", "group_failing", "outside", "read", False),
            ("user", "group_failing", "outside", "write", False),
            ("user", "group_failing", "outside", "unlink", False),
        ]
        cls._channel_type_channel_member_access_cases = [
            ("public", "no_group", "member", "self", "create", False),
            ("public", "no_group", "member", "self", "read", True),
            ("public", "no_group", "member", "self", "write", True),
            ("public", "no_group", "member", "self", "unlink", True),
            ("public", "no_group", "member", "other", "create", False),
            ("public", "no_group", "member", "other", "read", False),
            ("public", "no_group", "member", "other", "write", False),
            ("public", "no_group", "member", "other", "unlink", False),
            ("public", "no_group", "outside", "self", "create", True),
            ("public", "no_group", "outside", "other", "create", False),
            ("public", "no_group", "outside", "other", "read", False),
            ("public", "no_group", "outside", "other", "write", False),
            ("public", "no_group", "outside", "other", "unlink", False),
            ("public", "group_matching", "member", "self", "create", False),
            ("public", "group_matching", "member", "self", "read", True),
            ("public", "group_matching", "member", "self", "write", True),
            ("public", "group_matching", "member", "self", "unlink", True),
            ("public", "group_matching", "member", "other", "create", False),
            ("public", "group_matching", "member", "other", "read", False),
            ("public", "group_matching", "member", "other", "write", False),
            ("public", "group_matching", "member", "other", "unlink", False),
            ("public", "group_matching", "outside", "self", "create", True),
            ("public", "group_matching", "outside", "other", "create", False),
            ("public", "group_matching", "outside", "other", "read", False),
            ("public", "group_matching", "outside", "other", "write", False),
            ("public", "group_matching", "outside", "other", "unlink", False),
            ("public", "group_failing", "member", "self", "create", False),
            ("public", "group_failing", "member", "self", "read", False),
            ("public", "group_failing", "member", "self", "write", False),
            ("public", "group_failing", "member", "self", "unlink", False),
            ("public", "group_failing", "member", "other", "create", False),
            ("public", "group_failing", "member", "other", "read", False),
            ("public", "group_failing", "member", "other", "write", False),
            ("public", "group_failing", "member", "other", "unlink", False),
            ("public", "group_failing", "outside", "self", "create", False),
            ("public", "group_failing", "outside", "other", "create", False),
            ("public", "group_failing", "outside", "other", "read", False),
            ("public", "group_failing", "outside", "other", "write", False),
            ("public", "group_failing", "outside", "other", "unlink", False),
            ("portal", "no_group", "member", "self", "create", False),
            ("portal", "no_group", "member", "self", "read", True),
            ("portal", "no_group", "member", "self", "write", True),
            ("portal", "no_group", "member", "self", "unlink", True),
            ("portal", "no_group", "member", "other", "create", False),
            ("portal", "no_group", "member", "other", "read", False),
            ("portal", "no_group", "member", "other", "write", False),
            ("portal", "no_group", "member", "other", "unlink", False),
            ("portal", "no_group", "outside", "self", "create", True),
            ("portal", "no_group", "outside", "other", "create", False),
            ("portal", "no_group", "outside", "other", "read", False),
            ("portal", "no_group", "outside", "other", "write", False),
            ("portal", "no_group", "outside", "other", "unlink", False),
            ("portal", "group_matching", "member", "self", "create", False),
            ("portal", "group_matching", "member", "self", "read", True),
            ("portal", "group_matching", "member", "self", "write", True),
            ("portal", "group_matching", "member", "self", "unlink", True),
            ("portal", "group_matching", "member", "other", "create", False),
            ("portal", "group_matching", "member", "other", "read", False),
            ("portal", "group_matching", "member", "other", "write", False),
            ("portal", "group_matching", "member", "other", "unlink", False),
            ("portal", "group_matching", "outside", "self", "create", True),
            ("portal", "group_matching", "outside", "other", "create", False),
            ("portal", "group_matching", "outside", "other", "read", False),
            ("portal", "group_matching", "outside", "other", "write", False),
            ("portal", "group_matching", "outside", "other", "unlink", False),
            ("portal", "group_failing", "member", "self", "create", False),
            ("portal", "group_failing", "member", "self", "read", False),
            ("portal", "group_failing", "member", "self", "write", False),
            ("portal", "group_failing", "member", "self", "unlink", False),
            ("portal", "group_failing", "member", "other", "create", False),
            ("portal", "group_failing", "member", "other", "read", False),
            ("portal", "group_failing", "member", "other", "write", False),
            ("portal", "group_failing", "member", "other", "unlink", False),
            ("portal", "group_failing", "outside", "self", "create", False),
            ("portal", "group_failing", "outside", "other", "create", False),
            ("portal", "group_failing", "outside", "other", "read", False),
            ("portal", "group_failing", "outside", "other", "write", False),
            ("portal", "group_failing", "outside", "other", "unlink", False),
            ("user", "no_group", "member", "self", "create", False),
            ("user", "no_group", "member", "self", "read", True),
            ("user", "no_group", "member", "self", "write", True),
            ("user", "no_group", "member", "self", "unlink", True),
            ("user", "no_group", "member", "other", "create", True),
            ("user", "no_group", "member", "other", "read", False),
            ("user", "no_group", "member", "other", "write", False),
            ("user", "no_group", "member", "other", "unlink", False),
            ("user", "no_group", "outside", "self", "create", True),
            ("user", "no_group", "outside", "other", "create", True),
            ("user", "no_group", "outside", "other", "read", False),
            ("user", "no_group", "outside", "other", "write", False),
            ("user", "no_group", "outside", "other", "unlink", False),
            ("user", "group_matching", "member", "self", "create", False),
            ("user", "group_matching", "member", "self", "read", True),
            ("user", "group_matching", "member", "self", "write", True),
            ("user", "group_matching", "member", "self", "unlink", True),
            ("user", "group_matching", "member", "other", "create", True),
            ("user", "group_matching", "member", "other", "read", False),
            ("user", "group_matching", "member", "other", "write", False),
            ("user", "group_matching", "member", "other", "unlink", False),
            ("user", "group_matching", "outside", "self", "create", True),
            ("user", "group_matching", "outside", "other", "create", True),
            ("user", "group_matching", "outside", "other", "read", False),
            ("user", "group_matching", "outside", "other", "write", False),
            ("user", "group_matching", "outside", "other", "unlink", False),
            ("user", "group_failing", "member", "self", "create", False),
            ("user", "group_failing", "member", "self", "read", False),
            ("user", "group_failing", "member", "self", "write", False),
            ("user", "group_failing", "member", "self", "unlink", False),
            ("user", "group_failing", "member", "other", "create", False),
            ("user", "group_failing", "member", "other", "read", False),
            ("user", "group_failing", "member", "other", "write", False),
            ("user", "group_failing", "member", "other", "unlink", False),
            ("user", "group_failing", "outside", "self", "create", False),
            ("user", "group_failing", "outside", "other", "create", False),
            ("user", "group_failing", "outside", "other", "read", False),
            ("user", "group_failing", "outside", "other", "write", False),
            ("user", "group_failing", "outside", "other", "unlink", False),
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
                groups="base.group_public,mail.secret_group",
            ),
            "portal": mail_new_test_user(
                cls.env,
                login="portal1",
                name="A Portal User",
                groups="base.group_portal,mail.secret_group",
            ),
            "user": mail_new_test_user(
                cls.env,
                login="user1",
                name="An Internal User",
                groups="base.group_user,mail.secret_group",
            ),
        }
        cls.other_user = mail_new_test_user(
            cls.env,
            login="other1",
            name="Another User 1",
            groups="base.group_user,mail.secret_group",
        )
        cls.other_user_2 = mail_new_test_user(
            cls.env,
            login="other2",
            name="Another User 2",
            groups="base.group_user,mail.secret_group",
        )

    def _test_discuss_channel_access(self, cases):
        """
        Executes a list of operations on channels in various setups and checks whether the outcomes
        match the expected results.

        :param cases: A list of test cases, where each tuple contains:

            - user_key (``"portal"`` | ``"public"`` | ``"user"``): The user performing the operation.
            - group_key (``"chat"`` | ``"group"`` | ``"no_group"`` | ``"group_matching"`` |
            ``"group_failing"``): The group specification to use. ``chat`` and ``group`` define the
            channel type, while the others configure group setups for the channels.
            - membership (``"member"`` | ``"outside"``): Whether the user is a member of the channel.
            - operation (``"create"`` | ``"read"`` | ``"write"`` | ``"unlink"``): The action being tested.
            - expected_result (bool): Whether the action is expected to be allowed (``True``) or denied
            (``False``).
        :type cases: List[Tuple[str, str, str, str, bool]]
        """
        for user_key, channel_key, membership, operation, result in cases:
            if result:
                try:
                    self._execute_action_channel(
                        user_key, channel_key, membership, operation, result
                    )
                except Exception as e:  # noqa: BLE001 - re-raising, just with a more contextual message
                    raise AssertionError(
                        f"{user_key, channel_key, membership, operation} should not raise"
                    ) from e
            else:
                try:
                    with self.assertRaises(AccessError), mute_logger("odoo.sql_db"), mute_logger(
                        "odoo.addons.base.models.ir_model"
                    ), mute_logger("odoo.addons.base.models.ir_rule"), mute_logger(
                        "odoo.models.unlink"
                    ):
                        self._execute_action_channel(
                            user_key, channel_key, membership, operation, result
                        )
                except AssertionError as e:
                    raise AssertionError(
                        f"{user_key, channel_key, membership, operation} should raise"
                    ) from e

    def test_01_discuss_channel_access(self):
        cases = [
            *self._channel_type_channel_access_cases,
            ("public", "group", "member", "read", True),
            ("public", "group", "member", "write", False),
            ("public", "group", "member", "unlink", False),
            ("public", "group", "outside", "create", False),
            ("public", "group", "outside", "read", False),
            ("public", "group", "outside", "write", False),
            ("public", "group", "outside", "unlink", False),
            ("public", "chat", "outside", "create", False),
            ("public", "chat", "outside", "read", False),
            ("public", "chat", "outside", "write", False),
            ("public", "chat", "outside", "unlink", False),
            ("portal", "group", "member", "read", True),
            ("portal", "group", "member", "write", False),
            ("portal", "group", "member", "unlink", False),
            ("portal", "group", "outside", "create", False),
            ("portal", "group", "outside", "read", False),
            ("portal", "group", "outside", "write", False),
            ("portal", "group", "outside", "unlink", False),
            ("portal", "chat", "member", "read", True),
            ("portal", "chat", "member", "write", False),
            ("portal", "chat", "member", "unlink", False),
            ("portal", "chat", "outside", "create", False),
            ("portal", "chat", "outside", "read", False),
            ("portal", "chat", "outside", "write", False),
            ("portal", "chat", "outside", "unlink", False),
            ("user", "group", "member", "read", True),
            ("user", "group", "member", "write", True),
            ("user", "group", "member", "unlink", False),
            ("user", "group", "outside", "create", True),
            ("user", "group", "outside", "read", False),
            ("user", "group", "outside", "write", False),
            ("user", "group", "outside", "unlink", False),
            ("user", "chat", "member", "read", True),
            ("user", "chat", "member", "write", True),
            ("user", "chat", "member", "unlink", False),
            ("user", "chat", "outside", "create", True),
            ("user", "chat", "outside", "read", False),
            ("user", "chat", "outside", "write", False),
            ("user", "chat", "outside", "unlink", False),
        ]
        self._test_discuss_channel_access(cases)

    def _test_discuss_channel_member_access(self, cases):
        """
        Executes a list of operations on channel members in various setups and checks whether the
        outcomes match the expected results.

        :param cases: A list of test cases, where each tuple contains:
            - user_key (``"portal"`` | ``"public"`` | ``"user"``):
                The user performing the operation.
            - group_key (``"chat"`` | ``"group"`` | ``"no_group"`` | ``"group_matching"`` |
            ``"group_failing"``):
                The group specification to use. ``chat`` and ``group`` define the channel type, while the
                others configure group setups for the channels.
            - membership (``"member"`` | ``"outside"``):
                Whether the user is a member of the channel.
            - target (``"self"`` | ``"other"``):
                Whether the operation is executed on the self-member or another member.
            - operation (``"create"`` | ``"read"`` | ``"write"`` | ``"unlink"``):
                The action being tested.
            - expected_result (bool):
                Whether the action is expected to be allowed (``True``) or denied (``False``).
        :type cases: List[Tuple[str, str, str, str, str, bool]]
        """
        for user_key, channel_key, membership, target, operation, result in cases:
            channel_id = self._get_channel_id(user_key, channel_key, membership)
            if result:
                try:
                    self._execute_action_member(channel_id, user_key, target, operation, result)
                except Exception as e:  # noqa: BLE001 - re-raising, just with a more contextual message
                    raise AssertionError(
                        f"{user_key, channel_key, membership, target, operation} should not raise"
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
                        f"{user_key, channel_key, membership, target, operation} should raise access error"
                    ) from e

    def test_10_discuss_channel_member_access(self):
        cases = [
            *self._channel_type_channel_member_access_cases,
            ("public", "group", "member", "self", "create", False),
            ("public", "group", "member", "self", "read", True),
            ("public", "group", "member", "self", "write", True),
            ("public", "group", "member", "self", "unlink", True),
            ("public", "group", "member", "other", "create", False),
            ("public", "group", "member", "other", "read", False),
            ("public", "group", "member", "other", "write", False),
            ("public", "group", "member", "other", "unlink", False),
            ("public", "group", "outside", "self", "create", False),
            ("public", "group", "outside", "other", "create", False),
            ("public", "group", "outside", "other", "read", False),
            ("public", "group", "outside", "other", "write", False),
            ("public", "group", "outside", "other", "unlink", False),
            ("public", "chat", "outside", "self", "create", False),
            ("public", "chat", "outside", "other", "create", False),
            ("public", "chat", "outside", "other", "read", False),
            ("public", "chat", "outside", "other", "write", False),
            ("public", "chat", "outside", "other", "unlink", False),
            ("portal", "group", "member", "self", "create", False),
            ("portal", "group", "member", "self", "read", True),
            ("portal", "group", "member", "self", "write", True),
            ("portal", "group", "member", "self", "unlink", True),
            ("portal", "group", "member", "other", "create", False),
            ("portal", "group", "member", "other", "read", False),
            ("portal", "group", "member", "other", "write", False),
            ("portal", "group", "member", "other", "unlink", False),
            ("portal", "group", "outside", "self", "create", False),
            ("portal", "group", "outside", "other", "create", False),
            ("portal", "group", "outside", "other", "read", False),
            ("portal", "group", "outside", "other", "write", False),
            ("portal", "group", "outside", "other", "unlink", False),
            ("portal", "chat", "member", "self", "create", False),
            ("portal", "chat", "member", "self", "read", True),
            ("portal", "chat", "member", "self", "write", True),
            ("portal", "chat", "member", "self", "unlink", True),
            ("portal", "chat", "member", "other", "create", False),
            ("portal", "chat", "member", "other", "read", False),
            ("portal", "chat", "member", "other", "write", False),
            ("portal", "chat", "member", "other", "unlink", False),
            ("portal", "chat", "outside", "self", "create", False),
            ("portal", "chat", "outside", "other", "create", False),
            ("portal", "chat", "outside", "other", "read", False),
            ("portal", "chat", "outside", "other", "write", False),
            ("portal", "chat", "outside", "other", "unlink", False),
            ("user", "group", "member", "self", "create", False),
            ("user", "group", "member", "self", "read", True),
            ("user", "group", "member", "self", "write", True),
            ("user", "group", "member", "self", "unlink", True),
            ("user", "group", "member", "other", "create", True),
            ("user", "group", "member", "other", "read", False),
            ("user", "group", "member", "other", "write", False),
            ("user", "group", "member", "other", "unlink", False),
            ("user", "group", "outside", "self", "create", False),
            ("user", "group", "outside", "other", "create", False),
            ("user", "group", "outside", "other", "read", False),
            ("user", "group", "outside", "other", "write", False),
            ("user", "group", "outside", "other", "unlink", False),
            ("user", "chat", "member", "self", "create", False),
            ("user", "chat", "member", "self", "read", True),
            ("user", "chat", "member", "self", "write", True),
            ("user", "chat", "member", "self", "unlink", True),
            ("user", "chat", "member", "other", "create", False),
            ("user", "chat", "member", "other", "read", False),
            ("user", "chat", "member", "other", "write", False),
            ("user", "chat", "member", "other", "unlink", False),
            ("user", "chat", "outside", "self", "create", False),
            ("user", "chat", "outside", "other", "create", False),
            ("user", "chat", "outside", "other", "read", False),
            ("user", "chat", "outside", "other", "write", False),
            ("user", "chat", "outside", "other", "unlink", False),
        ]
        self._test_discuss_channel_member_access(cases)

    def _get_channel_id(self, user_key, channel_key, membership):
        partner = self.env["res.partner"] if user_key == "public" else self.users[user_key].partner_id
        guest = self.guest if user_key == "public" else self.env["mail.guest"]
        partners = self.other_user.partner_id
        if membership == "member":
            partners += partner
        DiscussChannel = self.env["discuss.channel"].with_user(self.other_user)
        if channel_key == "group":
            channel = DiscussChannel.create_group(partners.ids)
            if membership == "member":
                channel.add_members(partner_ids=partner.ids, guest_ids=guest.ids)
        elif channel_key == "chat":
            channel = DiscussChannel.channel_get(partners.ids)
        else:
            channel = DiscussChannel.channel_create("Channel", group_id=None)
            if membership == "member":
                channel.add_members(partner_ids=partner.ids, guest_ids=guest.ids)
        if channel_key == "no_group":
            channel.group_public_id = None
        elif channel_key == "group_matching":
            channel.group_public_id = self.secret_group
        elif channel_key == "group_failing":
            channel.group_public_id = self.env.ref("base.group_system")
        return channel.id

    def _execute_action_channel(self, user_key, channel_key, membership, operation, result):
        current_user = self.users[user_key]
        guest = self.guest if user_key == "public" else self.env["mail.guest"]
        ChannelAsUser = self.env["discuss.channel"].with_user(current_user).with_context(guest=guest)
        if operation == "create":
            group_public_id = None
            if channel_key == "group_matching":
                group_public_id = self.secret_group.id
            elif channel_key == "group_failing":
                group_public_id = self.env.ref("base.group_system").id
            data = {
                "name": "Test Channel",
                "channel_type": channel_key if channel_key in ("group", "chat") else "channel",
                "group_public_id": group_public_id,
            }
            ChannelAsUser.create(data)
        else:
            channel = ChannelAsUser.browse(self._get_channel_id(user_key, channel_key, membership))
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
