"""Tests for the partner signup-token lifecycle."""

from unittest.mock import patch

from odoo import exceptions
from odoo.tests import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestSignupToken(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Signup partner", "email": "signup.partner@example.com"}
        )

    def test_token_round_trip_resolves_partner(self):
        """A prepared partner's token resolves back to the same partner."""
        self.partner.signup_prepare()
        token = self.partner._generate_signup_token()
        self.assertEqual(
            self.env["res.partner"]._get_signup_partner(token), self.partner
        )

    def test_cancel_invalidates_token(self):
        """Cancelling the signup clears the type and kills the token."""
        self.partner.signup_prepare()
        token = self.partner._generate_signup_token()
        self.partner.signup_cancel()
        self.assertFalse(self.partner.signup_type)
        with self.assertRaises(exceptions.UserError):
            self.env["res.partner"]._get_signup_partner(token)

    def test_garbage_token_rejected(self):
        """An arbitrary token never resolves (negative)."""
        with self.assertRaises(exceptions.UserError):
            self.env["res.partner"]._get_signup_partner("not-a-real-token")

    def test_retrieve_info_without_user_offers_email(self):
        """For a partner with no user, the email doubles as proposed login."""
        self.partner.signup_prepare()
        token = self.partner._generate_signup_token()
        info = self.env["res.partner"]._resolve_signup_info(token)
        self.assertEqual(info["name"], "Signup partner")
        self.assertEqual(info["login"], "signup.partner@example.com")
        self.assertEqual(info["email"], "signup.partner@example.com")

    def test_retrieve_info_with_user_exposes_login(self):
        """For a partner with a user, the existing login is returned."""
        user = mail_new_test_user(
            self.env,
            login="signup_existing",
            email="signup.existing@example.com",
            groups="base.group_user",
        )
        user.partner_id.signup_prepare()
        token = user.partner_id._generate_signup_token()
        info = self.env["res.partner"]._resolve_signup_info(token)
        self.assertEqual(info["login"], "signup_existing")


@tagged("post_install", "-at_install")
class TestSignupWithToken(TransactionCase):
    """User creation and password change through res.users.signup tokens."""

    def test_signup_token_creates_user_for_partner(self):
        """A token for a user-less partner signs up a user and burns it."""
        partner = self.env["res.partner"].create(
            {"name": "Invitee", "email": "invitee@test.example.com"}
        )
        partner.signup_prepare()
        token = partner._generate_signup_token()

        login, _password = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .signup(
                {"login": "invitee@test.example.com", "password": "SuperSecret!42"},
                token=token,
            )
        )

        self.assertEqual(login, "invitee@test.example.com")
        self.assertTrue(partner.user_ids)
        self.assertEqual(partner.user_ids.partner_id, partner)
        self.assertFalse(partner.signup_type)

    def test_signup_token_updates_existing_user(self):
        """A token for a partner WITH a user updates it, ignoring identity."""
        user = mail_new_test_user(
            self.env,
            name="Existing signup user",
            login="existing.signup@test.example.com",
            groups="base.group_portal",
        )
        user.partner_id.signup_prepare(signup_type="reset")
        token = user.partner_id._generate_signup_token()

        login, _password = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .signup(
                {
                    "login": "hijack@test.example.com",
                    "name": "Hijacker",
                    "password": "NewSecret!42",
                },
                token=token,
            )
        )

        # identity fields are ignored: same login, same name
        self.assertEqual(login, "existing.signup@test.example.com")
        self.assertEqual(user.name, "Existing signup user")
        self.assertFalse(user.partner_id.signup_type)

    def test_burnt_token_rejected_on_second_use(self):
        """A signup token is single-use: the second signup must fail."""
        partner = self.env["res.partner"].create(
            {"name": "One shot", "email": "one.shot@test.example.com"}
        )
        partner.signup_prepare()
        token = partner._generate_signup_token()
        self.env["res.users"].with_context(no_reset_password=True).signup(
            {"login": "one.shot@test.example.com", "password": "FirstUse!42"},
            token=token,
        )

        with self.assertRaises(exceptions.UserError):
            self.env["res.users"].with_context(no_reset_password=True).signup(
                {"login": "again@test.example.com", "password": "SecondUse!42"},
                token=token,
            )

    def test_web_create_users_survives_email_less_inactive_user(self):
        """A login-only inactive user must not abort the batch invite."""
        Users = self.env["res.users"]
        email_less = Users.with_context(no_reset_password=True).create(
            {"name": "No email", "login": "noemail.match@test.example.com"}
        )
        self.assertFalse(email_less.email)
        self.assertEqual(email_less.state, "new")

        Users.web_create_users(
            ["noemail.match@test.example.com", "fresh@test.example.com"]
        )

        fresh = Users.search([("login", "=", "fresh@test.example.com")])
        self.assertTrue(fresh)
        self.assertEqual(fresh.state, "new")


@tagged("post_install", "-at_install")
class TestSignupUrl(TransactionCase):
    """Signup URL building and partner auth parameters."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Url partner", "email": "url.partner@example.com"}
        )

    def test_signup_url_builds_action_fragment(self):
        """Action, view and record data land urlencoded in the redirect."""
        urls = self.partner.with_context(signup_valid=True)._get_signup_url_for_action(
            action="base.action_partner_form",
            view_type="form",
            menu_id=7,
            model="res.partner",
            res_id=self.partner.id,
        )
        url = urls[self.partner.id]
        self.assertIn("token=", url)
        self.assertIn("redirect=", url)
        self.assertIn("action%3Dbase.action_partner_form", url)
        self.assertIn("view_type%3Dform", url)
        self.assertIn(f"res_id%3D{self.partner.id}", url)
        # signup_valid prepared a token on the user-less partner
        self.assertTrue(self.partner.signup_type)

    def test_signup_url_mail_view_action(self):
        """The /mail/view action uses its own redirect base."""
        urls = self.partner.with_context(signup_valid=True)._get_signup_url_for_action(
            action="/mail/view", res_id=42
        )
        self.assertIn("redirect=%2Fmail%2Fview%3F", urls[self.partner.id])

    def test_signup_url_explicit_redirect(self):
        """An explicit url wins over any fragment building."""
        urls = self.partner.with_context(signup_valid=True)._get_signup_url_for_action(
            url="/my/custom"
        )
        self.assertIn("redirect=%2Fmy%2Fcustom", urls[self.partner.id])

    def test_auth_param_token_for_userless_partner(self):
        """In b2c a user-less partner gets a fresh signup token."""
        self.env["ir.config_parameter"].sudo().set_param(
            "auth_signup.invitation_scope", "b2c"
        )
        # website, when installed, decides the scope per website and overrides
        # the parameter; the setting an administrator changes writes both
        if "website" in self.env:
            self.env["website"].sudo().search([]).write(
                {"auth_signup_uninvited": "b2c"}
            )
        res = self.partner.signup_get_auth_param()
        self.assertTrue(res[self.partner.id]["auth_signup_token"])

    def test_auth_param_login_for_partner_with_user(self):
        """A partner already linked to a user exposes its login instead."""
        user = mail_new_test_user(
            self.env, login="linked.user@example.com", groups="base.group_user"
        )
        res = user.partner_id.signup_get_auth_param()
        self.assertEqual(
            res[user.partner_id.id]["auth_login"], "linked.user@example.com"
        )

    def test_auth_param_denied_for_non_internal(self):
        """Portal users cannot read signup auth parameters."""
        portal = mail_new_test_user(
            self.env, login="portal.signup@example.com", groups="base.group_portal"
        )
        with self.assertRaises(exceptions.AccessDenied):
            self.partner.with_user(portal).signup_get_auth_param()


@tagged("post_install", "-at_install")
class TestSignupUserLifecycle(TransactionCase):
    """Signup cancellation and re-invitation over the user lifecycle."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Lifecycle user",
                    "login": "lifecycle@example.com",
                    "email": "lifecycle@example.com",
                }
            )
        )

    def test_deactivating_user_cancels_signup(self):
        """Archiving a user drops the partner's pending signup."""
        self.user.partner_id.signup_prepare()
        self.assertTrue(self.user.partner_id.signup_type)
        self.user.active = False
        self.assertFalse(self.user.partner_id.signup_type)

    def test_unlinking_user_cancels_signup(self):
        """Deleting a user drops the partner's pending signup."""
        partner = self.user.partner_id
        partner.signup_prepare()
        self.assertTrue(partner.signup_type)
        self.user.unlink()
        self.assertFalse(partner.signup_type)

    def test_web_create_users_reinvites_inactive_with_email(self):
        """An inactive emailed user gets a fresh signup invitation."""
        self.assertEqual(self.user.state, "new")
        self.assertFalse(self.user.partner_id.signup_type)
        self.env["res.users"].web_create_users(["lifecycle@example.com"])
        # the re-invitation prepared a signup token on the partner
        self.assertEqual(self.user.partner_id.signup_type, "signup")
        self.assertTrue(self.user.partner_id.sudo()._generate_signup_token())

    def test_reminder_mails_inviting_user(self):
        """The reminder cron mails whoever invited the unregistered user."""
        creator = self.user.create_uid
        if not creator.email:
            creator.email = "creator@example.com"
        before = self.env["mail.mail"].search_count([])
        # _commit_progress calls cr.commit(), forbidden on a test cursor:
        # stub the cron bookkeeping, the behavior under test is the mailing.
        with patch.object(
            type(self.env["ir.cron"]), "_commit_progress", return_value=1.0
        ):
            self.env["res.users"].send_unregistered_user_reminder(after_days=0)
        new_mails = self.env["mail.mail"].search_count([]) - before
        self.assertGreater(new_mails, 0)
