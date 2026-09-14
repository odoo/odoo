import logging

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import users

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user

_logger = logging.getLogger(__name__)


class TestPortalWizard(MailCommon):
    def test_contact_manager_can_grant_and_revoke_without_admin_access(self):
        operator = mail_new_test_user(
            self.env,
            "portal_contact_manager",
            groups="base.group_user,base.group_partner_manager",
        )
        self.assertFalse(operator.has_group("base.group_system"))
        line = (
            self.env["portal.wizard"]
            .with_user(operator)
            .with_context(active_ids=self.partner.ids)
            .create({})
            .user_ids
        )
        self.assertFalse(line.user_id)

        with self.mock_mail_gateway():
            line.action_grant_access()
        account = line.user_id.sudo()
        _logger.debug("Contact manager %s granted account %s", operator.id, account.id)
        self.assertTrue(line.is_portal)
        self.assertEqual(account.partner_id, self.partner)
        self.assertTrue(account.active)

        line.action_revoke_access()

        self.assertFalse(line.is_portal)
        self.assertFalse(account.active)

    def test_revoke_rechecks_a_user_promoted_to_internal(self):
        line = (
            self.env["portal.wizard"]
            .with_context(active_ids=self.portal_user.partner_id.ids)
            .create({})
            .user_ids
        )
        self.assertTrue(line.is_portal)
        self.assertFalse(line.is_internal)
        self.portal_user.group_ids = [Command.set(self.env.ref("base.group_user").ids)]

        with self.assertRaises(UserError):
            line.action_revoke_access()

        _logger.debug(
            "Revoke challenge: internal=%s active=%s",
            line.is_internal,
            self.portal_user.active,
        )
        self.assertTrue(line.is_internal)
        self.assertTrue(self.portal_user.active)

    def test_reinvite_rechecks_an_archived_account(self):
        line = (
            self.env["portal.wizard"]
            .with_context(active_ids=self.portal_user.partner_id.ids)
            .create({})
            .user_ids
        )
        self.assertTrue(line.is_portal)
        self.portal_user.active = False

        with self.mock_mail_gateway(), self.assertRaises(UserError):
            line.action_invite_again()

        _logger.debug(
            "Reinvite challenge: portal=%s active=%s",
            line.is_portal,
            self.portal_user.active,
        )
        self.assertFalse(line.is_portal)
        self.assertNotSentEmail()

    def test_grant_access_rechecks_an_account_created_after_reading(self):
        wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=self.partner.ids)
            .create({})
        )
        line = wizard.user_ids
        self.assertFalse(line.user_id)

        user = mail_new_test_user(
            self.env,
            login="portal_cache_regression",
            partner_id=self.partner.id,
            groups="base.group_portal",
        )
        with self.assertRaises(UserError):
            line.action_grant_access()
        _logger.debug(
            "Wizard line %s resolves newly created user %s", line.id, line.user_id.id
        )
        self.assertEqual(line.user_id, user)
        self.assertTrue(line.is_portal)

    def setUp(self):
        super().setUp()

        self.user_employee.write(
            {"group_ids": [(3, self.env.ref("base.group_partner_manager").id)]}
        )
        self.partner = self.env["res.partner"].create(
            {
                "name": "Testing Partner",
                "email": "testing_partner@example.com",
            }
        )

        self.public_user = mail_new_test_user(
            self.env,
            name="Public user",
            login="public_user",
            email="public_user@example.com",
            groups="base.group_public",
        )

        self.portal_user = mail_new_test_user(
            self.env,
            name="Portal user",
            login="portal_user",
            email="portal_user@example.com",
            groups="base.group_portal",
        )

        self.internal_user = mail_new_test_user(
            self.env,
            name="Internal user",
            login="internal_user",
            email="internal_user@example.com",
            groups="base.group_user",
        )

    def test_portal_wizard_acl(self):
        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[self.partner.id])
            .create({})
        )

        with self.assertRaises(
            AccessError,
            msg="Standard users should not be able to open the portal wizard",
        ):
            self.env["portal.wizard"].with_context(
                active_ids=[self.partner.id]
            ).with_user(self.user_employee).create({})

        with self.assertRaises(
            AccessError,
            msg="Standard users should not be able to open the portal wizard",
        ):
            _ = portal_wizard.with_user(self.user_employee).welcome_message

        with self.assertRaises(
            AccessError,
            msg="Standard users should not be able to open the portal wizard",
        ):
            _ = portal_wizard.user_ids.with_user(self.user_employee).email

    @users("admin")
    def test_portal_wizard_partner(self):
        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[self.partner.id])
            .create({})
        )

        self.assertEqual(len(portal_wizard.user_ids), 1)

        portal_user = portal_wizard.user_ids

        self.assertFalse(portal_user.user_id.id)
        self.assertFalse(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)

        portal_user.email = "first_email@example.com"
        with self.mock_mail_gateway():
            portal_user.action_grant_access()
        new_user = portal_user.user_id

        self.assertTrue(new_user.id, "Must create a new user")
        self.assertTrue(new_user._is_portal(), "Must add the group to the user")
        self.assertEqual(
            self.partner.email,
            "first_email@example.com",
            "Must write on the email of the partner",
        )
        self.assertEqual(
            new_user.email,
            "first_email@example.com",
            "Must create the user with the right email",
        )
        self.assertSentEmail(self.company_admin.partner_id, [self.partner])

    @users("admin")
    def test_portal_wizard_public_user(self):
        public_partner = self.public_user.partner_id
        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[public_partner.id])
            .create({})
        )

        self.assertEqual(len(portal_wizard.user_ids), 1)
        portal_user = portal_wizard.user_ids

        self.assertEqual(portal_user.user_id, self.public_user)
        self.assertFalse(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)

        portal_user.email = "new_email@example.com"
        with self.mock_mail_gateway():
            portal_user.action_grant_access()

        self.assertTrue(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)

        self.assertTrue(self.public_user._is_portal(), "Must add the group portal")
        self.assertFalse(self.public_user._is_public(), "Must remove the group public")
        self.assertEqual(
            public_partner.email,
            "new_email@example.com",
            "Must change the email of the partner",
        )
        self.assertEqual(
            self.public_user.email,
            "new_email@example.com",
            "Must change the email of the user",
        )
        self.assertSentEmail(self.company_admin.partner_id, [public_partner])

        with self.mock_mail_gateway():
            portal_user.action_revoke_access()
            portal_user.invalidate_recordset()

        self.assertEqual(
            portal_user.user_id,
            self.public_user,
            "Must keep the user even if it is archived",
        )
        self.assertFalse(portal_user.user_id.active, "Must have archived the user")
        self.assertFalse(portal_user.is_portal)
        self.assertFalse(portal_user.is_internal)
        self.assertNotSentEmail()

    @users("admin")
    def test_portal_wizard_internal_user(self):
        internal_partner = self.internal_user.partner_id
        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[internal_partner.id])
            .create({})
        )

        self.assertEqual(len(portal_wizard.user_ids), 1)
        portal_user = portal_wizard.user_ids

        self.assertTrue(portal_user.is_internal)

        with (
            self.assertRaises(
                UserError, msg="Should not be able to manage internal user"
            ),
            self.mock_mail_gateway(),
        ):
            portal_wizard.user_ids.action_grant_access()

        self.assertNotSentEmail()

        with self.assertRaises(
            UserError, msg="Should not be able to manage internal user"
        ):
            portal_wizard.user_ids.action_revoke_access()

    @users("admin")
    def test_portal_wizard_error(self):
        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[self.portal_user.partner_id.id])
            .create({})
        )

        self.assertEqual(len(portal_wizard.user_ids), 1)
        portal_user = portal_wizard.user_ids

        self.internal_user.login = "test_error@example.com"

        portal_user.email = "test_error@example.com"
        with self.assertRaises(UserError, msg="Must detect the already used email."):
            portal_user._assert_user_email_uniqueness()
        self.assertEqual(
            portal_user.email_state, "exist", msg="Must detect the already used email."
        )

        portal_user.email = "wrong email format"
        with self.assertRaises(UserError, msg="Must detect wrong email format."):
            portal_user._assert_user_email_uniqueness()
        self.assertEqual(
            portal_user.email_state, "ko", msg="Must detect wrong email format."
        )

        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[self.internal_user.partner_id.id])
            .create({})
        )
        portal_user = portal_wizard.user_ids
        with self.assertRaises(
            UserError, msg="Must not be able to change internal user group."
        ):
            portal_user.action_revoke_access()

    def test_portal_wizard_multi_company(self):
        company_1 = self.company_admin
        company_2 = self.company_2

        partner_company_2 = (
            self.env["res.partner"]
            .with_company(company_2)
            .create(
                {
                    "name": "Testing Partner",
                    "email": "testing_partner@example.com",
                    "company_id": company_2.id,
                }
            )
        )

        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[partner_company_2.id])
            .create({})
        )
        portal_user = portal_wizard.user_ids

        portal_user.with_company(company_1).action_grant_access()

        self.assertEqual(
            portal_user.user_id.company_id,
            company_2,
            "Must create the user in the same company as the partner.",
        )

    def test_portal_wizard_multiple_access_changes(self):
        portal_wizard = (
            self.env["portal.wizard"]
            .with_context(active_ids=[self.partner.id])
            .create({})
        )
        self.assertEqual(len(portal_wizard.user_ids), 1)

        portal_user = portal_wizard.user_ids[0]
        self.assertFalse(portal_user.user_id)
        self.assertFalse(portal_user.is_portal)

        for _ in range(2):
            portal_user.action_grant_access()
            self.assertTrue(portal_user.user_id.active)
            self.assertTrue(portal_user.user_id._is_portal())
            self.assertTrue(portal_user.is_portal)
            self.assertTrue(self.partner.signup_type)

            portal_user.action_revoke_access()
            self.assertFalse(portal_user.user_id.active)
            self.assertTrue(portal_user.user_id._is_portal())
            self.assertFalse(portal_user.is_portal)
            self.assertFalse(self.partner.signup_type)
