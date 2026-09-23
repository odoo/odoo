from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger
from odoo.tools.mail import add_html_content

from odoo.addons.base.tests.common import converted_reach
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail_group.tests.common import TestMailListCommon


@tagged("mail_group")
class TestMailGroup(TestMailListCommon):
    def test_clean_email_body(self):
        footer = self.env["ir.qweb"]._render(
            "mail_group.mail_group_footer",
            {"group_url": "Test remove footer"},
            minimal_qcontext=True,
        )
        body = add_html_content("<div>Test email body</div>", footer, plaintext=False)

        result = self.env["mail.group"]._clean_email_body(body)
        self.assertIn(
            "Test email body", result, "Should have kept the original email body"
        )
        self.assertNotIn(
            "Test remove footer", result, "Should have removed the mailing list footer"
        )
        self.assertNotIn(
            "o_mg_message_footer", result, "Should have removed the entire HTML element"
        )

    def test_constraint_valid_email(self):
        mail_group = (
            self.env["mail.group"]
            .with_user(self.user_employee)
            .browse(self.test_group.ids)
        )
        user_without_email = mail_new_test_user(
            self.env,
            login="user_employee_nomail",
            company_id=self.company_admin.id,
            email=False,
            groups="base.group_user",
            name="User without email",
        )

        with self.assertRaises(ValidationError, msg="Moderators must have an email"):
            mail_group.moderator_ids |= user_without_email

    def test_find_group_user_for_alias(self):
        group_user_not_member = mail_new_test_user(
            self.env,
            login="group user not member",
            email="group_user_not_member@example.com",
        )

        self.assertIn(
            group_user_not_member,
            self.test_group.access_group_id.all_user_ids,
            "User, that sends e-mail, must be part of the access group (in this test scenario)",
        )
        self.assertNotIn(
            group_user_not_member.id,
            self.test_group.member_ids.ids,
            "User, that sends e-mail, shan't be a member of the mail group (in this test scenario)",
        )

        self.test_group.alias_id.alias_contact = "followers"
        self.test_group.access_mode = "groups"
        err_msg = self.test_group._alias_resolve_error(
            {}, {"email_from": group_user_not_member.email}, self.test_group.alias_id
        )
        self.assertFalse(
            err_msg,
            "Mail with sender belonging to allowed user group (not a member of the mail group) was rejected",
        )

    def test_group_access_refuses_an_address_less_sender(self):
        self.test_group.access_mode = "groups"
        for email_from in ("", False, "not an address"):
            with self.subTest(email_from=email_from):
                error = self.test_group._alias_resolve_error(
                    {}, {"email_from": email_from}, self.test_group.alias_id
                )
                self.assertTrue(error)
                self.assertEqual(error.code, "error_mail_group_members_restricted")

    def test_find_member(self):
        member_1 = self.test_group_member_1
        email = member_1.email_normalized

        partner_2 = self.user_portal.partner_id
        partner_2.email = '"Bob" <%s>' % email
        member_2 = self.env["mail.group.member"].create(
            {
                "partner_id": partner_2.id,
                "mail_group_id": self.test_group.id,
            }
        )

        partner_3 = self.partner_root
        partner_3.email = '"Bob" <%s>' % email
        member_3 = self.env["mail.group.member"].create(
            {
                "partner_id": partner_3.id,
                "mail_group_id": self.test_group.id,
            }
        )

        self.env["mail.group.member"].create(
            {
                "email": "Alice",
                "mail_group_id": self.test_group.id,
            }
        )

        member = self.test_group._find_member(email)
        self.assertEqual(
            member,
            member_1,
            "When no partner is provided, return the member without partner in priority",
        )

        member = self.test_group._find_member(email, partner_2.id)
        self.assertEqual(
            member, member_2, "Should return the member with the right partner"
        )

        member = self.test_group._find_member(email, partner_3.id)
        self.assertEqual(
            member, member_3, "Should return the member with the right partner"
        )

        member_2.unlink()
        member = self.test_group._find_member(email, partner_2.id)
        self.assertEqual(member, member_1, "Should return the member without partner")

        member_1.unlink()
        member = self.test_group._find_member(email, partner_2.id)
        self.assertFalse(
            member,
            "Should not return any member because the only one with the same email has a different partner",
        )

        member = self.test_group._find_member("", None)
        self.assertEqual(
            member, None, "When no email nor partner is provided, return nobody"
        )

    def test_find_member_for_alias(self):
        user = self.user_portal
        user2 = mail_new_test_user(self.env, login="login_2", email=user.email)

        member = self.env["mail.group.member"].create(
            {
                "partner_id": user.partner_id.id,
                "mail_group_id": self.test_group.id,
            }
        )
        self.assertEqual(member.email, user.email)

        msg_dict = {
            "author_id": user2.partner_id.id,
            "email_from": user2.email,
        }
        self.test_group.alias_id.alias_contact = "followers"
        self.assertFalse(
            self.test_group._alias_resolve_error({}, msg_dict, self.test_group.alias_id)
        )

    @users("employee")
    def test_join_group(self):
        mail_group = self.env["mail.group"].browse(self.test_group.ids)
        self.assertEqual(len(mail_group.member_ids), 4)

        mail_group._join_group('"Jack" <jack@test.com>')
        self.assertEqual(len(mail_group.member_ids), 5)
        self.assertTrue(mail_group._find_member('"Test" <jack@test.com>'))

        mail_group._join_group('"Jack the developer" <jack@test.com>')
        self.assertEqual(
            len(mail_group.member_ids), 5, "Should not have added the duplicated email"
        )

        portal_partner = self.user_portal.partner_id
        mail_group._join_group(
            '"Bob" <email_different_than_partner@test.com>', portal_partner.id
        )
        self.assertEqual(
            len(mail_group.member_ids), 6, "Should have added the new member"
        )
        member = mail_group._find_member(
            "email_different_than_partner@test.com", portal_partner.id
        )
        self.assertTrue(member)
        self.assertEqual(
            member.partner_id, portal_partner, "Should have set the partner"
        )
        self.assertEqual(
            member.email,
            portal_partner.email,
            "Should have force the email to the email of the partner",
        )
        self.assertEqual(member.email_normalized, portal_partner.email_normalized)

        portal_partner.email = "new_portal_email@example.com"
        self.assertEqual(
            member.email,
            "new_portal_email@example.com",
            "Should have change the email of the partner",
        )
        self.assertEqual(member.email_normalized, "new_portal_email@example.com")

    @mute_logger("odoo.addons.base.models.ir_access", "odoo.addons.base.models.ir_model")
    @users("employee")
    def test_mail_group_access_mode_groups(self):
        test_group = self.env.ref("base.group_partner_manager")
        mail_group = self.env["mail.group"].browse(self.test_group.ids)
        mail_group.write(
            {
                "access_group_id": test_group.id,
                "access_mode": "groups",
            }
        )

        with self.assertRaises(AccessError):
            mail_group.with_user(self.user_portal).check_access("read")

        public_user = self.env.ref("base.public_user")
        with self.assertRaises(AccessError):
            mail_group.with_user(public_user).check_access("read")

        with self.assertRaises(AccessError):
            mail_group.with_user(self.user_employee_2).check_access("read")

        self.user_employee_2.group_ids |= test_group
        mail_group.with_user(self.user_employee_2).check_access("read")
        with self.assertRaises(
            AccessError,
            msg="Only moderator / responsible and admin can write on the group",
        ):
            mail_group.with_user(self.user_employee_2).check_access("write")

        self.user_employee_2.group_ids -= test_group
        mail_group.moderator_ids |= self.user_employee_2
        mail_group.with_user(self.user_employee_2).check_access("read")
        mail_group.with_user(self.user_employee_2).check_access("write")

        mail_group.access_group_id = self.env.ref("base.group_public")
        mail_group.with_user(public_user).check_access("read")
        with self.assertRaises(AccessError):
            mail_group.with_user(public_user).check_access("write")

    @mute_logger("odoo.addons.base.models.ir_access", "odoo.addons.base.models.ir_model")
    @users("employee")
    def test_mail_group_access_mode_public(self):
        mail_group = self.env["mail.group"].browse(self.test_group.ids)
        mail_group.access_mode = "public"

        public_user = self.env.ref("base.public_user")
        mail_group.with_user(public_user).check_access("read")
        with self.assertRaises(AccessError):
            mail_group.with_user(public_user).check_access("write")

        mail_group.with_user(self.user_employee_2).check_access("read")
        with self.assertRaises(
            AccessError,
            msg="Only moderator / responsible and admin can write on the group",
        ):
            mail_group.with_user(self.user_employee_2).check_access("write")

        mail_group.moderator_ids |= self.user_employee_2
        mail_group.with_user(self.user_employee_2).check_access("write")

    @mute_logger("odoo.addons.base.models.ir_access", "odoo.addons.base.models.ir_model")
    @users("employee")
    def test_mail_group_access_mode_members(self):
        mail_group = self.env["mail.group"].browse(self.test_group.ids)
        mail_group.access_mode = "members"
        partner = self.user_employee_2.partner_id
        self.assertNotIn(partner, mail_group.member_partner_ids)

        with self.assertRaises(
            AccessError, msg="Non-member should not have access to the group"
        ):
            mail_group.with_user(self.user_employee_2).check_access("read")

        public_user = self.env.ref("base.public_user")
        with self.assertRaises(
            AccessError, msg="Non-member should not have access to the group"
        ):
            mail_group.with_user(public_user).check_access("read")

        mail_group.write(
            {
                "member_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": partner.id,
                        },
                    )
                ]
            }
        )
        self.assertIn(partner, mail_group.member_partner_ids)

        mail_group.with_user(self.user_employee_2).check_access("read")
        with self.assertRaises(
            AccessError,
            msg="Only moderator / responsible and admin can write on the group",
        ):
            mail_group.with_user(self.user_employee_2).check_access("write")

        mail_group.moderator_ids |= self.user_employee_2
        mail_group.with_user(self.user_employee_2).check_access("write")

    @mute_logger("odoo.addons.base.models.ir_access", "odoo.addons.base.models.ir_model")
    @users("employee")
    def test_mail_group_member_security(self):
        member = self.env["mail.group.member"].browse(self.test_group_member_1.ids)
        self.assertEqual(
            member.email,
            '"Member 1" <member_1@test.com>',
            msg="Moderators should have access to members",
        )

        with self.assertRaises(
            AccessError, msg="Portal should not have access to members"
        ):
            member.with_user(self.user_portal).check_access("read")

        with self.assertRaises(
            AccessError, msg="Non moderators should not have access to member"
        ):
            member.with_user(self.user_portal).check_access("read")


@tagged("mail_group")
class TestMailGroupAdministrator(TestMailListCommon):
    def test_an_administrator_manages_groups_they_do_not_moderate(self):
        administrator = mail_new_test_user(
            self.env,
            login="mail_group_administrator",
            groups="base.group_user,mail_group.group_mail_group_manager",
        )
        records = (
            self.test_group,
            self.test_group_member_1,
            self.test_group_msg_1_pending,
            self.moderation,
        )
        for record in records:
            with self.subTest(model=record._name):
                record.with_user(administrator).check_access("write")
                self.assertEqual(
                    converted_reach(self.env, record._name, administrator, "write")
                    & record,
                    record,
                )
