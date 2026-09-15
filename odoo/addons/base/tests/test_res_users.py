from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from odoo import models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.http import _request_stack
from odoo.libs.password import CryptContext, pbkdf2_sha512_hash
from odoo.tests import (
    TEST_CURSOR_COOKIE_NAME,
    Form,
    HttpCase,
    TransactionCase,
    new_test_user,
    tagged,
    users,
    warmup,
)
from odoo.tools import mute_logger


class UsersCommonCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        users = cls.env["res.users"].create(
            [
                {
                    "name": "Internal",
                    "login": "user_internal",
                    "password": "password",
                    "group_ids": [cls.env.ref("base.group_user").id],
                    "tz": "UTC",
                },
                {
                    "name": "Portal 1",
                    "login": "portal_1",
                    "password": "portal_1",
                    "group_ids": [cls.env.ref("base.group_portal").id],
                },
                {
                    "name": "Portal 2",
                    "login": "portal_2",
                    "password": "portal_2",
                    "group_ids": [cls.env.ref("base.group_portal").id],
                },
            ]
        )

        cls.user_internal, cls.user_portal_1, cls.user_portal_2 = users

        users.partner_id.invalidate_recordset()
        users.invalidate_recordset()


class TestUsers(UsersCommonCase):
    def test_name_search(self):
        User = self.env["res.users"]

        test_user = User.create({"name": "Flad the Impaler", "login": "vlad"})
        like_user = User.create({"name": "Wlad the Impaler", "login": "vladi"})
        other_user = User.create(
            {"name": "Nothing similar", "login": "nothing similar"}
        )
        all_users = test_user | like_user | other_user

        res = User.name_search("vlad", operator="ilike")
        self.assertEqual(User.browse(i[0] for i in res) & all_users, test_user)

        res = User.name_search("vlad", operator="not ilike")
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search("", operator="ilike")
        self.assertEqual(User.browse(i[0] for i in res) & all_users, all_users)

        res = User.name_search("", operator="not ilike")
        self.assertEqual(User.browse(i[0] for i in res) & all_users, User)

        res = User.name_search("lad", operator="ilike")
        self.assertEqual(
            User.browse(i[0] for i in res) & all_users, test_user | like_user
        )

        res = User.name_search("lad", operator="not ilike")
        self.assertEqual(User.browse(i[0] for i in res) & all_users, other_user)

    def test_user_partner(self):

        User = self.env["res.users"]
        Partner = self.env["res.partner"]
        Company = self.env["res.company"]

        company_1 = Company.create({"name": "company_1"})
        company_2 = Company.create({"name": "company_2"})

        partner = Partner.create({"name": "Bob Partner", "company_id": company_2.id})

        test_user = User.create(
            {
                "name": "John Smith",
                "login": "jsmith",
                "company_ids": [company_1.id],
                "company_id": company_1.id,
            }
        )

        self.assertFalse(
            test_user.partner_id.company_id,
            "The partner_id linked to a user should be created without any company_id",
        )

        test_user = User.create(
            {
                "name": "Bob Smith",
                "login": "bsmith",
                "company_ids": [company_1.id],
                "company_id": company_1.id,
                "partner_id": partner.id,
            }
        )

        self.assertEqual(
            test_user.partner_id.company_id,
            company_1,
            "If the partner_id of a user has already a company, it is replaced by the user company",
        )

    def test_change_user_company(self):

        User = self.env["res.users"]
        Company = self.env["res.company"]

        test_user = User.create({"name": "John Smith", "login": "jsmith"})
        company_1 = Company.create({"name": "company_1"})
        company_2 = Company.create({"name": "company_2"})

        test_user.company_ids += company_1
        test_user.company_ids += company_2

        test_user.write({"company_id": company_1.id})

        self.assertFalse(
            test_user.partner_id.company_id,
            "On user company change, if its partner_id has no company_id,"
            "the company_id of the partner_id shall NOT be updated",
        )

        test_user.partner_id.write({"company_id": company_1.id})

        test_user.write({"company_id": company_2.id})

        self.assertEqual(
            test_user.partner_id.company_id,
            company_2,
            "On user company change, if its partner_id has already a company_id,"
            "the company_id of the partner_id shall be updated",
        )

    @mute_logger("odoo.db")
    def test_deactivate_portal_users_access(self):
        with self.assertRaises(
            UserError,
            msg="Internal users should not be able to deactivate their account",
        ):
            self.user_internal._deactivate_portal_user()

    @mute_logger("odoo.db", "odoo.addons.base.models.res_users_deletion")
    def test_deactivate_portal_users_archive_and_remove(self):
        User = self.env["res.users"]
        portal_user = User.create(
            {
                "name": "Portal",
                "login": "portal_user",
                "password": "password",
                "group_ids": [self.env.ref("base.group_portal").id],
            }
        )
        portal_partner = portal_user.partner_id

        portal_user_2 = User.create(
            {
                "name": "Portal",
                "login": "portal_user_2",
                "password": "password",
                "group_ids": [self.env.ref("base.group_portal").id],
            }
        )
        portal_partner_2 = portal_user_2.partner_id

        (portal_user | portal_user_2)._deactivate_portal_user()

        self.assertTrue(
            portal_user.exists() and not portal_user.active,
            "Should have archived the user 1",
        )

        self.assertEqual(portal_user.name, "Portal", "Should have kept the user name")
        self.assertEqual(
            portal_user.partner_id.name,
            "Portal",
            "Should have kept the partner name",
        )
        self.assertNotEqual(
            portal_user.login,
            "portal_user",
            "Should have removed the user login",
        )

        asked_deletion_1 = self.env["res.users.deletion"].search(
            [("user_id", "=", portal_user.id)]
        )
        asked_deletion_2 = self.env["res.users.deletion"].search(
            [("user_id", "=", portal_user_2.id)]
        )

        self.assertTrue(
            asked_deletion_1,
            "Should have added the user 1 in the deletion queue",
        )
        self.assertTrue(
            asked_deletion_2,
            "Should have added the user 2 in the deletion queue",
        )

        self.cron = self.env["ir.cron"].create(
            {
                "name": "Test Cron",
                "user_id": portal_user_2.id,
                "model_id": self.env.ref("base.model_res_partner").id,
            }
        )

        with self.enter_registry_test_mode():
            self.env.ref("base.ir_cron_res_users_deletion").method_direct_trigger()

        self.assertFalse(portal_user.exists(), "Should have removed the user")
        self.assertFalse(portal_partner.exists(), "Should have removed the partner")
        self.assertEqual(
            asked_deletion_1.state,
            "done",
            "Should have marked the deletion as done",
        )

        self.assertTrue(portal_user_2.exists(), "Should have kept the user")
        self.assertTrue(portal_partner_2.exists(), "Should have kept the partner")
        self.assertEqual(
            asked_deletion_2.state,
            "fail",
            "Should have marked the deletion as failed",
        )

    def test_delete_public_user(self):
        public_user = self.env.ref("base.public_user")
        public_partner = public_user.partner_id

        with self.assertRaises(UserError, msg="Public user should not be deletable"):
            public_user.unlink()

        self.assertTrue(
            public_user.exists() and not public_user.active,
            "Public user should still exist and be inactive",
        )
        self.assertTrue(
            public_partner.exists() and not public_partner.active,
            "Public partner should still exist and be inactive",
        )

    def test_user_home_action_restriction(self):
        test_user = new_test_user(self.env, "hello world")

        restricted_action = self.env["ir.actions.act_window"].search(
            [("context", "ilike", "active_id")], limit=1
        )
        with self.assertRaises(ValidationError):
            test_user.action_id = restricted_action.id

        allowed_action = self.env["ir.actions.act_window"].search(
            ["!", ("context", "ilike", "active_id")], limit=1
        )

        test_user.action_id = allowed_action.id
        self.assertEqual(test_user.action_id.id, allowed_action.id)

    def test_context_get_lang(self):
        self.env["res.lang"].with_context(active_test=False).search(
            [("code", "in", ["fr_FR", "es_ES", "de_DE", "en_US"])]
        ).write({"active": True})

        user = new_test_user(self.env, "jackoneill")
        user = user.with_user(user)
        user.lang = "fr_FR"

        company = user.company_id.partner_id.sudo()
        company.lang = "de_DE"

        request = SimpleNamespace()
        request.best_lang = "es_ES"
        request_patch = patch("odoo.addons.base.models.res_users.request", request)
        self.addCleanup(request_patch.stop)
        request_patch.start()

        self.assertEqual(user.context_get()["lang"], "fr_FR")
        self.env.registry.clear_cache()
        user.lang = False

        self.assertEqual(user.context_get()["lang"], "es_ES")
        self.env.registry.clear_cache()
        request_patch.stop()

        self.assertEqual(user.context_get()["lang"], "de_DE")
        self.env.registry.clear_cache()
        company.lang = False

        self.assertEqual(user.context_get()["lang"], "en_US")

    def test_context_get_request_lang_not_pinned(self):
        self.env["res.lang"].with_context(active_test=False).search(
            [("code", "in", ["fr_FR", "es_ES", "de_DE", "en_US"])]
        ).write({"active": True})
        self.addCleanup(self.env.registry.clear_cache)

        user = new_test_user(self.env, "ctxnopin")
        user = user.with_user(user)
        user.lang = False
        user.company_id.partner_id.sudo().lang = "de_DE"

        patch_target = "odoo.addons.base.models.res_users.request"
        with patch(patch_target, SimpleNamespace(best_lang="es_ES")):
            self.assertEqual(user.context_get()["lang"], "es_ES")
        self.assertEqual(user.context_get()["lang"], "de_DE")
        with patch(patch_target, SimpleNamespace(best_lang="fr_FR")):
            self.assertEqual(user.context_get()["lang"], "fr_FR")
        with patch(patch_target, SimpleNamespace(best_lang="nl_NL")):
            self.assertEqual(user.context_get()["lang"], "de_DE")
        user.lang = "fr_FR"
        with patch(patch_target, SimpleNamespace(best_lang="es_ES")):
            self.assertEqual(user.context_get()["lang"], "fr_FR")

    def test_user_self_update(self):
        test_user = self.env["res.users"].create(
            {"name": "John Smith", "login": "jsmith"}
        )
        self.assertFalse(test_user.phone_ids)
        phone = (
            self.env["phone.number"].with_user(test_user).create({"number": "2387478"})
        )
        test_user.with_user(test_user).write({"phone_ids": [Command.link(phone.id)]})

        self.assertEqual(
            test_user.partner_id.phone_ids.number,
            "2387478",
            "The phone of the partner_id shall be updated.",
        )

    def test_session_non_existing_user(self):
        User = self.env["res.users"]
        last_user_id = User.with_context(active_test=False).search(
            [], limit=1, order="id desc"
        )
        non_existing_user = User.browse(last_user_id.id + 1)
        self.assertFalse(non_existing_user._get_session_token("session_id"))


@tagged("post_install", "-at_install", "groups")
class TestUsers2(UsersCommonCase):
    def test_change_user_login(self):

        User = self.env["res.users"]
        with Form(User, view="base.view_users_simple_form") as UserForm:
            UserForm.name = "Test User"
            UserForm.login = "test-user1"
            self.assertFalse(UserForm.email)

            UserForm.login = "test-user1@mycompany.example.org"
            self.assertEqual(
                UserForm.email,
                "test-user1@mycompany.example.org",
                "Setting a valid email as login should update the partner's email",
            )

    def test_default_groups(self):
        default_group = self.env.ref("base.default_user_group")
        test_group = self.env["res.groups"].create({"name": "test_group"})
        default_group.implied_ids = test_group

        f = Form(self.env["res.users"], view="base.view_users_form")
        f.name = "bob"
        f.login = "bob"
        user = f.save()

        group_user = self.env.ref("base.group_user")

        self.assertIn(group_user, user.group_ids)
        self.assertEqual(default_group.implied_ids + group_user, user.group_ids)

    def test_selection_groups(self):
        app = self.env["res.groups.privilege"].create({"name": "Foo"})
        group_user, group_manager, group_visitor = self.env["res.groups"].create(
            [
                {"name": name, "privilege_id": app.id}
                for name in ("User", "Manager", "Visitor")
            ]
        )
        self.assertLess(group_user.id, group_manager.id)
        self.assertLess(group_manager.id, group_visitor.id)
        group_manager.implied_ids = group_user
        group_user.implied_ids = group_visitor
        groups = group_visitor + group_user + group_manager

        user = self.env["res.users"].create({"name": "foo", "login": "foo"})

        user.write({"group_ids": [Command.set([group_visitor.id])]})
        self.assertEqual(user.group_ids & groups, group_visitor)
        self.assertEqual(user.all_group_ids & groups, group_visitor)
        self.assertEqual(user.read(["group_ids"])[0]["group_ids"], [group_visitor.id])
        self.assertEqual(
            user.read(["all_group_ids"])[0]["all_group_ids"], [group_visitor.id]
        )

        user.write({"group_ids": [Command.unlink(group_visitor.id)]})
        self.assertEqual(user.group_ids & groups, self.env["res.groups"])

        user.write({"group_ids": [Command.set([group_manager.id])]})
        self.assertEqual(user.group_ids & groups, group_manager)
        self.assertEqual(
            user.all_group_ids & groups,
            group_visitor + group_manager + group_user,
        )
        self.assertEqual(user.read(["group_ids"])[0]["group_ids"], [group_manager.id])
        self.assertEqual(
            set(user.read(["all_group_ids"])[0]["all_group_ids"]),
            set((group_visitor + group_manager + group_user).ids),
        )

        user.write({"group_ids": [Command.link(group_user.id)]})
        self.assertEqual(user.group_ids & groups, group_manager + group_user)
        self.assertEqual(
            user.all_group_ids & groups,
            group_visitor + group_manager + group_user,
        )
        self.assertEqual(
            set(user.read(["group_ids"])[0]["group_ids"]),
            set((group_manager + group_user).ids),
        )
        self.assertEqual(
            set(user.read(["all_group_ids"])[0]["all_group_ids"]),
            set((group_visitor + group_manager + group_user).ids),
        )

        groups = self.env["res.groups"].search([("all_user_ids", "=", user.id)])
        self.assertEqual(groups, user.all_group_ids)

    def test_implied_groups_on_change(self):
        group_public = self.env.ref("base.group_public")
        group_portal = self.env.ref("base.group_portal")
        group_user = self.env.ref("base.group_user")

        app = self.env["res.groups.privilege"].create({"name": "Foo"})
        group_contain_user = self.env["res.groups"].create(
            {
                "name": "Small user group",
                "privilege_id": app.id,
                "implied_ids": [group_user.id],
            }
        )

        user_form = Form(self.env["res.users"], view="base.view_users_form")
        user_form.name = "Test"
        user_form.login = "Test"
        self.assertFalse(user_form.share)

        user_form["group_ids"] = group_portal
        self.assertTrue(
            user_form.share, "The group_ids onchange should have been triggered"
        )

        user = user_form.save()

        with self.debug_mode():
            user_form = Form(user, view="base.view_users_form")

            user_form["group_ids"] = group_user
            self.assertFalse(
                user_form.share,
                "The group_ids onchange should have been triggered",
            )

            user_form["group_ids"] = group_public
            self.assertTrue(
                user_form.share,
                "The group_ids onchange should have been triggered",
            )

            user_form["group_ids"] = group_user
            user_form["group_ids"] = group_user + group_contain_user

            user_form.save()

        with self.debug_mode():
            user_form = Form(self.env["res.users"], view="base.view_users_form")
            user_form.name = "Test-2"
            user_form.login = "Test-2"

            user_form["group_ids"] = group_portal
            self.assertTrue(user_form.share)

            user_form["group_ids"] = group_portal + group_contain_user
            self.assertFalse(
                user_form.share,
                "The group_ids onchange should have been triggered",
            )

            with self.assertRaises(
                ValidationError,
                msg="The user cannot be at the same time in groups: ['Membre', 'Portal', 'Foo / Small user group']",
            ):
                user_form.save()

    def test_view_group_hierarchy(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        group_system = self.env.ref("base.group_system")
        group_system.with_context(lang="fr_FR").name = "Administrateur"

        view_group_hierarchy_en = self.env["res.groups"]._get_view_group_hierarchy()
        view_group_hierarchy_fr = (
            self.env["res.groups"]
            .with_context(lang="fr_FR")
            ._get_view_group_hierarchy()
        )
        self.assertNotEqual(
            view_group_hierarchy_en["groups"][group_system.id]["name"],
            "Administrateur",
        )
        self.assertEqual(
            view_group_hierarchy_fr["groups"][group_system.id]["name"],
            "Administrateur",
        )

        self.env.registry.clear_cache("groups")
        view_group_hierarchy_fr = (
            self.env["res.groups"]
            .with_context(lang="fr_FR")
            ._get_view_group_hierarchy()
        )
        view_group_hierarchy_en = self.env["res.groups"]._get_view_group_hierarchy()
        self.assertNotEqual(
            view_group_hierarchy_en["groups"][group_system.id]["name"],
            "Administrateur",
        )
        self.assertEqual(
            view_group_hierarchy_fr["groups"][group_system.id]["name"],
            "Administrateur",
        )

        with patch(
            "odoo.addons.base.models.res_groups.ResGroups._get_view_group_hierarchy"
        ) as mock:
            self.user_portal_1.copy_data()
            self.assertFalse(mock.called)

    @users("portal_1")
    @mute_logger("odoo.addons.base.models.ir_model")
    def test_self_writeable_fields(self):
        self.assertIn(
            "post_install",
            self.test_tags,
            "This test **must** be `post_install` to ensure the expected behavior despite other modules",
        )
        self.assertIn(
            "email",
            self.env["res.users"].SELF_WRITEABLE_FIELDS,
            "For this test to make sense, 'email' must be in the `SELF_WRITEABLE_FIELDS`",
        )
        self.assertNotIn(
            "login",
            self.env["res.users"].SELF_WRITEABLE_FIELDS,
            "For this test to make sense, 'login' must not be in the `SELF_WRITEABLE_FIELDS`",
        )

        me = self.env["res.users"].browse(self.env.user.id)
        other = self.env["res.users"].browse(self.user_portal_2.id)

        me.email = "foo@bar.com"
        self.assertEqual(me.email, "foo@bar.com")
        with self.assertRaises(AccessError):
            me.login = "foo"

        with self.assertRaises(AccessError):
            other.email = "foo@bar.com"
        with self.assertRaises(AccessError):
            other.login = "foo"

    @users("user_internal")
    def test_self_readable_writeable_fields_preferences_form(self):
        my_user = self.env["res.users"].browse(self.env.user.id)
        self.assertIn(
            "name",
            my_user.SELF_WRITEABLE_FIELDS,
            "This test doesn't make sense if not tested on a field part of the SELF_WRITEABLE_FIELDS",
        )
        self.patch(
            self.env.registry["res.users"]._fields["name"],
            "groups",
            "base.group_system",
        )
        with Form(my_user, view="base.view_users_form_simple_modif") as UserForm:
            UserForm.name = "Raoulette Poiluchette"
        self.assertEqual(my_user.name, "Raoulette Poiluchette")

    @warmup
    def test_write_group_ids_performance(self):
        contact_creation_group = self.env.ref("base.group_partner_manager")
        self.assertNotIn(contact_creation_group, self.user_internal.group_ids)

        with self.assertQueryCount(24):
            self.user_internal.write(
                {
                    "group_ids": [Command.link(contact_creation_group.id)],
                }
            )

    def test_portal_user_manager_access(self):
        group_portal = self.env.ref("base.group_portal")
        group_user = self.env.ref("base.group_user")
        group_partner_manager = self.env.ref("base.group_partner_manager")
        group_portal_user_manager = self.env["res.groups"].create(
            {
                "name": "Portal User Manager",
                "user_ids": [],
            }
        )

        self.env["ir.model.access"].create(
            {
                "name": "Allow user profile update",
                "model_id": self.env["ir.model"]._get("res.users").id,
                "group_id": group_portal_user_manager.id,
                "perm_write": True,
            }
        )

        self.env["ir.rule"].create(
            {
                "name": "Allow updates by Portal Managers on PORTAL users (only)",
                "model_id": self.env["ir.model"]._get("res.users").id,
                "groups": [group_portal_user_manager.id],
                "domain_force": [("share", "=", True)],
                "perm_write": True,
            }
        )

        portal_user_manager = self.env["res.users"].create(
            {
                "name": "Portal User Manager",
                "login": "maintainer",
                "password": "password",
                "group_ids": [
                    group_user.id,
                    group_partner_manager.id,
                    group_portal_user_manager.id,
                ],
            }
        )
        user = self.env["res.users"].create(
            {
                "name": "User",
                "login": "user_",
                "password": "password",
                "group_ids": [group_user.id, group_partner_manager.id],
            }
        )
        portal = self.env["res.users"].create(
            {
                "name": "Portal",
                "login": "portal_",
                "password": "password",
                "group_ids": [group_portal.id],
            }
        )

        with self.assertRaises(AccessError):
            user.with_user(portal_user_manager).write({"name": "New name for you"})
        portal.with_user(portal_user_manager).write({"name": "New name for you"})

        with self.assertRaises(AccessError):
            user.partner_id.with_user(portal_user_manager).write(
                {"name": "New name for you"}
            )
        portal.partner_id.with_user(portal_user_manager).write(
            {"name": "New name for you"}
        )

        with self.assertRaises(AccessError):
            self.user_internal.with_user(user).write({"name": "New name for you"})
        with self.assertRaises(AccessError):
            portal.with_user(user).write({"name": "New name for you"})

        with self.assertRaises(AccessError):
            self.user_internal.partner_id.with_user(user).write(
                {"name": "New name for you"}
            )
        portal.partner_id.with_user(user).write({"name": "New name for you"})


class TestEmptyPassword(TransactionCase):
    def test_password_change_preserves_spaces_and_rejects_blank_passwords(self):
        user = new_test_user(self.env, "password_spaces", password="Original!Pwd123")
        password = "  New!Secret456  "

        user._change_password(password)

        self.assertEqual(
            self._check_credentials(user, password)["auth_method"], "password"
        )
        with self.assertRaises(AccessDenied):
            self._check_credentials(user, password.strip())
        for blank in ("", " \t "):
            with self.subTest(blank=repr(blank)), self.assertRaises(UserError):
                user._change_password(blank)
        self.assertEqual(
            self._check_credentials(user, password)["auth_method"], "password"
        )

    def _stored_password(self, user):
        self.env.cr.execute("SELECT password FROM res_users WHERE id=%s", (user.id,))
        return self.env.cr.fetchone()[0]

    def _check_credentials(self, user, password):
        return user.with_user(user)._check_credentials(
            {"type": "password", "login": user.login, "password": password},
            {"interactive": True},
        )

    def test_empty_password_stores_null_and_blocks_login(self):
        user = new_test_user(self.env, "nopwd_user", password="Secret!Pwd123")
        self.assertTrue(self._stored_password(user))
        self.assertEqual(
            self._check_credentials(user, "Secret!Pwd123")["auth_method"],
            "password",
        )

        user.password = ""

        self.assertIsNone(
            self._stored_password(user),
            "An empty password must be stored as SQL NULL.",
        )
        for attempt in ("Secret!Pwd123", "", " "):
            with self.assertRaises(AccessDenied):
                self._check_credentials(user, attempt)

    def test_reset_after_empty_password(self):
        user = new_test_user(self.env, "repwd_user", password="Secret!Pwd123")
        user.password = ""
        self.assertIsNone(self._stored_password(user))
        user.password = "New!Secret456"
        self.assertTrue(self._stored_password(user))
        self.assertEqual(
            self._check_credentials(user, "New!Secret456")["auth_method"],
            "password",
        )


class TestUsersTweaks(TransactionCase):
    def test_superuser(self):
        user = self.env["res.users"].browse(SUPERUSER_ID)
        self.assertFalse(user.active)
        with self.assertRaises(UserError):
            user.write({"active": True})


@tagged("post_install", "-at_install")
class TestUsersIdentitycheck(HttpCase):
    @users("admin")
    def test_revoke_all_devices(self):
        self.env.user.password = "admin@odoo"

        session = self.authenticate(
            "admin", "admin@odoo", session_extra={"_trace_disable": False}
        )

        self.authenticate(
            "admin", "admin@odoo", session_extra={"_trace_disable": False}
        )
        self.assertTrue(self.url_open("/web").url.endswith("/web"))

        # The double has to look like the request an HttpCase serves: the
        # identity check rate-limits by remote address and reads the
        # test-cursor cookie before it may open a pool cursor.
        _request_stack.push(
            SimpleNamespace(
                session=session,
                env=self.env,
                httprequest=SimpleNamespace(remote_addr="127.0.0.1", path="/web"),
                cookies={TEST_CURSOR_COOKIE_NAME: self.http_request_key},
            )
        )
        self.addCleanup(_request_stack.pop)
        action = self.env.user.action_revoke_all_devices()
        form = Form(
            self.env[action["res_model"]].browse(action["res_id"]),
            action.get("view_id"),
        )
        form.password = "admin@odoo"
        user_identity_check = form.save()
        action = user_identity_check.with_context(password=form.password).run_check()

        landing = self.url_open(f"/web?db={self.env.cr.dbname}").url
        self.assertIn("/web/login", landing)
        self.assertNotIn("/web/database/selector", landing)

        self.assertFalse(user_identity_check.password)


@tagged("post_install", "-at_install")
class TestContextGetPartnerInvalidation(TransactionCase):
    def test_partner_lang_write_invalidates_context_get(self):
        self.env["res.lang"].with_context(active_test=False).search(
            [("code", "in", ["fr_FR", "en_US"])]
        ).write({"active": True})
        self.addCleanup(self.env.registry.clear_cache)

        user = new_test_user(self.env, "rul01_lang_user", lang="en_US")
        user = user.with_user(user)
        self.assertEqual(user.context_get()["lang"], "en_US")

        user.partner_id.sudo().write({"lang": "fr_FR"})

        self.assertEqual(
            user.context_get()["lang"],
            "fr_FR",
            "context_get cache was not invalidated by a direct partner lang write",
        )


@tagged("post_install", "-at_install")
class TestLoginCooldown(TransactionCase):
    _REQUEST = "odoo.addons.base.models.res_users.request"

    def setUp(self):
        super().setUp()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("base.login_cooldown_after", "2")
        icp.set_param("base.login_cooldown_duration", "60")
        self.addCleanup(self._purge_cooldown_rows)

    def _purge_cooldown_rows(self):
        with self.env.registry.cursor() as cr:
            cr.execute(
                "DELETE FROM res_users_login_cooldown WHERE source LIKE ANY(%s)",
                [
                    [
                        "8.8.8.8",
                        "7.7.7.7",
                        "8.8.4.4",
                        "1.1.1.1",
                        "9.9.9.9",
                        "203.0.113.%",
                        "198.51.100.%",
                    ]
                ],
            )

    @staticmethod
    def _request(addr):
        return SimpleNamespace(httprequest=SimpleNamespace(remote_addr=addr))

    def _fail_once(self, users):
        with self.assertRaises(AccessDenied), users._assert_can_auth(user=self.env.uid):
            raise AccessDenied

    @mute_logger("odoo.addons.base.models.res_users")
    def test_cooldown_after_threshold(self):
        users = self.env["res.users"]
        with patch(self._REQUEST, self._request("8.8.8.8")):
            self._fail_once(users)
            self._fail_once(users)
            with (
                self.assertRaises(AccessDenied),
                users._assert_can_auth(user=self.env.uid),
            ):
                pass

    @mute_logger("odoo.addons.base.models.res_users")
    def test_change_password_is_rate_limited(self):
        target = self.env["res.users"].create(
            {
                "name": "Cooldown Target",
                "login": "cooldown_target",
                "password": "correct-horse-battery",
            }
        )
        as_target = self.env["res.users"].with_user(target)
        with patch(self._REQUEST, self._request("7.7.7.7")):
            for _ in range(2):
                with self.assertRaises(AccessDenied):
                    as_target.change_password("wrong", "irrelevant")
            with self.assertRaises(AccessDenied):
                as_target.change_password(
                    "correct-horse-battery", "a-brand-new-password"
                )

    def test_success_resets_counter(self):
        users = self.env["res.users"]
        with patch(self._REQUEST, self._request("8.8.4.4")):
            self._fail_once(users)
            with users._assert_can_auth(user=self.env.uid):
                pass
            self._fail_once(users)
            with users._assert_can_auth(user=self.env.uid):
                pass

    def test_disabled_when_cooldown_after_zero(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "base.login_cooldown_after", "0"
        )
        users = self.env["res.users"]
        with patch(self._REQUEST, self._request("1.1.1.1")):
            for _ in range(5):
                self._fail_once(users)
            with users._assert_can_auth(user=self.env.uid):
                pass

    def test_no_request_is_noop(self):
        users = self.env["res.users"]
        with patch(self._REQUEST, None):
            with users._assert_can_auth(user=self.env.uid):
                pass

    @mute_logger("odoo.addons.base.models.res_users")
    def test_cooldown_with_non_numeric_login(self):
        users = self.env["res.users"]
        login = "bob@example.com"
        with patch(self._REQUEST, self._request("9.9.9.9")):
            for _ in range(2):
                with (
                    self.assertRaises(AccessDenied),
                    users._assert_can_auth(user=login),
                ):
                    raise AccessDenied
            with (
                self.assertRaises(AccessDenied),
                users._assert_can_auth(user=login),
            ):
                pass

    @mute_logger("odoo.addons.base.models.res_users")
    def test_stale_failure_entries_are_pruned(self):
        users = self.env["res.users"]
        with patch(self._REQUEST, self._request("203.0.113.7")):
            self._fail_once(users)

        now = datetime.now(UTC).replace(tzinfo=None)
        stale = now - timedelta(seconds=120)
        stale_sources = [f"198.51.100.{i}" for i in range(4)]
        fresh_source = "198.51.100.200"
        with self.env.registry.cursor() as cr:
            for source in stale_sources:
                cr.execute(
                    "INSERT INTO res_users_login_cooldown (source, failures, last_failure) "
                    "VALUES (%s, 3, %s)",
                    [source, stale],
                )
            cr.execute(
                "INSERT INTO res_users_login_cooldown (source, failures, last_failure) "
                "VALUES (%s, 1, %s)",
                [fresh_source, now],
            )

        with patch(self._REQUEST, self._request("203.0.113.8")):
            self._fail_once(users)

        with self.env.registry.cursor() as cr:
            cr.execute("SELECT source FROM res_users_login_cooldown")
            remaining = {row[0] for row in cr.fetchall()}

        for source in stale_sources:
            self.assertNotIn(source, remaining, "stale entry must be pruned")
        self.assertIn(fresh_source, remaining, "in-window entry must survive")
        self.assertIn("203.0.113.7", remaining)
        self.assertIn(
            "203.0.113.8", remaining, "the just-failed source must be recorded"
        )


@tagged("post_install", "-at_install")
class TestLoginTimingSideChannel(TransactionCase):
    @mute_logger("odoo.addons.base.models.res_users")
    def test_unknown_user_pays_a_dummy_hash_check(self):
        from odoo.addons.base.models.res_users import _DUMMY_PASSWORD_HASH

        with patch(
            "odoo.libs.password.CryptContext.match_and_update",
            return_value=(False, None),
        ) as match_and_update:
            with self.assertRaises(AccessDenied):
                self.env["res.users"].sudo()._login(
                    {
                        "login": "auth1-no-such-user",
                        "type": "password",
                        "password": "whatever",
                    },
                    {"interactive": True},
                )

        match_and_update.assert_called_once_with("whatever", _DUMMY_PASSWORD_HASH)


@tagged("post_install", "-at_install")
class TestResUsersInitPasswordMigration(TransactionCase):
    def test_init_invalidates_all_migrated_passwords(self):
        User = self.env["res.users"]
        password_field = User._fields["password"]
        user_a = new_test_user(self.env, login="rul09_a")
        user_b = new_test_user(self.env, login="rul09_b")

        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_users SET password=%s WHERE id = ANY(%s)",
            ("plaintext-secret", [user_a.id, user_b.id]),
        )
        (user_a + user_b).invalidate_recordset(["password"])
        _ = user_a.sudo().password
        _ = user_b.sudo().password
        self.assertTrue(self.env.cache.contains(user_a, password_field))
        self.assertTrue(self.env.cache.contains(user_b, password_field))

        User.init()

        self.assertFalse(
            self.env.cache.contains(user_a, password_field),
            "init() must invalidate every migrated user's cached password (RU-L09)",
        )
        self.assertFalse(self.env.cache.contains(user_b, password_field))

        ctx = User._get_crypt_context()
        self.env.cr.execute(
            "SELECT password FROM res_users WHERE id = ANY(%s)",
            ([user_a.id, user_b.id],),
        )
        for (stored,) in self.env.cr.fetchall():
            self.assertTrue(stored.startswith("$"), "stored hash must be MCF")
            self.assertTrue(ctx.is_password_valid("plaintext-secret", stored))


@tagged("post_install", "-at_install")
class TestCheckUidPasswdCacheContract(TransactionCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(self.env.registry.clear_cache)
        self.env.registry.clear_cache()

    def test_orm_password_change_invalidates_cache(self):
        Users = self.env["res.users"]
        user = new_test_user(self.env, login="rut3_orm", password="old-password")

        Users._check_uid_passwd(user.id, "old-password")

        user.password = "new-password"

        with self.assertRaises(AccessDenied):
            Users._check_uid_passwd(user.id, "old-password")
        Users._check_uid_passwd(user.id, "new-password")

    def test_raw_sql_change_without_clear_keeps_cache_stale(self):
        Users = self.env["res.users"]
        user = new_test_user(self.env, login="rut3_rawsql", password="old-password")

        Users._check_uid_passwd(user.id, "old-password")

        new_hash = Users._get_crypt_context().hash("new-password")
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_users SET password=%s WHERE id=%s", (new_hash, user.id)
        )
        self.env.invalidate_all()

        Users._check_uid_passwd(user.id, "old-password")
        self.env.registry.clear_cache()
        with self.assertRaises(AccessDenied):
            Users._check_uid_passwd(user.id, "old-password")


@tagged("post_install", "-at_install")
class TestSelfWriteCompanyGuard(UsersCommonCase):
    def test_self_write_company_id_non_member_is_refused(self):
        user = new_test_user(self.env, login="rut4_company", groups="base.group_user")
        other_company = self.env["res.company"].create({"name": "RU-T4 Other Co"})
        self.assertNotIn(other_company.id, user.company_ids.ids)
        original_company = user.company_id

        me = user.with_user(user)
        with self.assertRaises(ValidationError):
            me.write({"company_id": other_company.id})
            self.env.flush_all()
        self.env.cr.precommit.clear()
        self.assertEqual(user.company_id, original_company)

    def test_self_write_company_id_member_is_applied(self):
        company_b = self.env["res.company"].create({"name": "RU-T4 Co B"})
        user = new_test_user(self.env, login="rut4_member", groups="base.group_user")
        user.sudo().write({"company_ids": [Command.link(company_b.id)]})
        self.assertIn(company_b.id, user.company_ids.ids)

        me = user.with_user(user)
        me.write({"company_id": company_b.id})
        self.assertEqual(
            user.company_id,
            company_b,
            "a self-written company_id that IS a member company must be applied",
        )

    def test_self_write_does_not_mutate_the_caller_vals(self):
        user = new_test_user(self.env, login="rut4_novals", groups="base.group_user")
        other_company = self.env["res.company"].create({"name": "RU-T4 Untouched Co"})
        vals = {"company_id": other_company.id, "tz": "Europe/Brussels"}

        with self.assertRaises(ValidationError):
            user.with_user(user).write(vals)
            self.env.flush_all()
        self.env.cr.precommit.clear()

        self.assertEqual(
            vals,
            {"company_id": other_company.id, "tz": "Europe/Brussels"},
            "write() mutated the caller's vals dict",
        )


@tagged("post_install", "-at_install")
class TestAtLeastOneAdministrator(TransactionCase):
    def test_admin_via_implying_group_only(self):
        group_system = self.env.ref("base.group_system")
        implying_group = self.env["res.groups"].create(
            {
                "name": "RU-M3 Implied Admins",
                "implied_ids": [Command.link(group_system.id)],
            }
        )
        indirect_admin = self.env["res.users"].create(
            {
                "name": "RU-M3 Indirect Admin",
                "login": "ru_m3_indirect_admin",
                "group_ids": [Command.set(implying_group.ids)],
            }
        )
        self.assertNotIn(group_system, indirect_admin.group_ids)
        self.assertIn(group_system, indirect_admin.all_group_ids)

        direct_admins = group_system.user_ids
        self.assertTrue(direct_admins, "the test DB must have a direct admin")
        direct_admins.write({"group_ids": [Command.unlink(group_system.id)]})

        self.assertFalse(group_system.user_ids, "no direct member must remain")
        self.assertTrue(
            self.env["res.users"].search_count(
                [
                    ("all_group_ids", "in", group_system.ids),
                    ("active", "=", True),
                ],
                limit=1,
            ),
            "the implied-only admin must still be an effective administrator",
        )


@tagged("post_install", "-at_install")
class TestDeviceLogGC(TransactionCase):
    def _log(self, **vals):
        base = {
            "session_identifier": "sid_rdev_p3_a",
            "platform": "linux",
            "browser": "firefox",
            "ip_address": "127.0.0.1",
            "user_id": self.env.uid,
            "first_activity": "2026-07-01 10:00:00",
            "last_activity": "2026-07-01 10:00:00",
        }
        base.update(vals)
        return self.env["res.device.log"].create(base)

    def test_gc_keeps_latest_log_per_device(self):
        DeviceLog = self.env["res.device.log"]

        self._log(last_activity="2026-07-01 10:00:00")
        self._log(last_activity="2026-07-01 11:00:00")
        keep_a = self._log(last_activity="2026-07-01 12:00:00")

        self._log(platform=False, browser=False, last_activity="2026-07-01 10:00:00")
        keep_b = self._log(
            platform=False, browser=False, last_activity="2026-07-01 11:00:00"
        )

        self._log(
            session_identifier="sid_rdev_p3_c", last_activity="2026-07-01 09:00:00"
        )
        keep_c = self._log(
            session_identifier="sid_rdev_p3_c", last_activity="2026-07-01 09:00:00"
        )

        keep_d = self._log(
            session_identifier="sid_rdev_p3_d",
            ip_address="10.0.0.8",
            last_activity="2020-01-01 00:00:00",
        )

        self.env.flush_all()
        DeviceLog._gc_device_log()
        self.env.invalidate_all()

        survivors = DeviceLog.search(
            [
                (
                    "session_identifier",
                    "in",
                    ["sid_rdev_p3_a", "sid_rdev_p3_c", "sid_rdev_p3_d"],
                )
            ],
            order="id",
        )
        self.assertEqual(survivors, keep_a | keep_b | keep_c | keep_d)


class TestAccessesCount(UsersCommonCase):
    def test_counts_match_relational_reads(self):
        user = self.user_internal
        groups = user.all_group_ids
        self.assertEqual(user.groups_count, len(groups))
        self.assertEqual(user.accesses_count, len(groups.model_access))
        self.assertEqual(user.rules_count, len(groups.rule_groups))
        self.assertGreater(user.accesses_count, 0)
        self.assertGreater(user.rules_count, 0)

    def test_counts_follow_active_test_like_the_relational_reads(self):
        group = self.env["res.groups"].create({"name": "accesses count group"})
        model_partner = self.env.ref("base.model_res_partner")
        rule = self.env["ir.rule"].create(
            {
                "name": "accesses count rule",
                "model_id": model_partner.id,
                "groups": [Command.link(group.id)],
                "domain_force": "[(1, '=', 1)]",
            }
        )
        acl = self.env["ir.model.access"].create(
            {
                "name": "accesses count acl",
                "model_id": model_partner.id,
                "group_id": group.id,
                "perm_read": True,
            }
        )
        self.user_internal.write({"group_ids": [Command.link(group.id)]})
        user = self.user_internal
        groups = user.all_group_ids
        self.assertIn(acl, groups.model_access)
        self.assertIn(rule, groups.rule_groups)
        active_accesses = user.accesses_count
        active_rules = user.rules_count
        self.assertEqual(active_accesses, len(groups.model_access))
        self.assertEqual(active_rules, len(groups.rule_groups))

        rule.action_archive()
        acl.action_archive()
        self.env.invalidate_all()
        self.assertNotIn(acl, groups.model_access)
        self.assertNotIn(rule, groups.rule_groups)
        self.assertEqual(user.accesses_count, active_accesses - 1)
        self.assertEqual(user.rules_count, active_rules - 1)
        self.assertEqual(user.accesses_count, len(groups.model_access))
        self.assertEqual(user.rules_count, len(groups.rule_groups))

        self.env.invalidate_all()
        user_no_active_test = user.with_context(active_test=False)
        groups_no_active_test = user_no_active_test.all_group_ids
        self.assertIn(acl, groups_no_active_test.model_access)
        self.assertIn(rule, groups_no_active_test.rule_groups)
        self.assertEqual(
            user_no_active_test.accesses_count,
            len(groups_no_active_test.model_access),
        )
        self.assertEqual(
            user_no_active_test.rules_count,
            len(groups_no_active_test.rule_groups),
        )


class TestWriteCacheInvalidation(UsersCommonCase):
    def _user_context_lang(self, user):
        return self.env["res.users"].with_user(user).context_get()["lang"]

    def test_lang_only_write_invalidates_context_cache(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        user = self.user_internal
        self.assertEqual(self._user_context_lang(user), "en_US")
        user.write({"lang": "fr_FR"})
        self.assertEqual(self._user_context_lang(user), "fr_FR")

    def test_combined_group_and_lang_write_invalidates_context_cache(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        user = self.user_internal
        self.assertEqual(self._user_context_lang(user), "en_US")
        group = self.env["res.groups"].create({"name": "cache inval group"})
        user.write({"group_ids": [Command.link(group.id)], "lang": "fr_FR"})
        self.assertEqual(self._user_context_lang(user), "fr_FR")
        self.assertIn(group, user.all_group_ids)


class TestInstalledLangCodes(TransactionCase):
    def test_codes_match_get_installed_and_track_activation(self):
        Users = self.env["res.users"]
        codes = Users._get_installed_lang_codes()
        self.assertIsInstance(codes, tuple)
        self.assertIn("en_US", codes)
        self.assertEqual(
            codes,
            tuple(code for code, _name in self.env["res.lang"].get_installed()),
            "the order is load-bearing: _get_context_cached falls back to codes[0]",
        )
        if "fr_FR" in codes:
            self.skipTest("fr_FR already installed; cannot test invalidation")
        self.env["res.lang"]._activate_lang("fr_FR")
        self.assertIn("fr_FR", Users._get_installed_lang_codes())


class TestDeviceIdentityAlignment(TransactionCase):
    def _log(self, **vals):
        base = {
            "session_identifier": "sid_rdev_p4",
            "platform": "linux",
            "browser": "firefox",
            "ip_address": "10.0.0.1",
            "user_id": self.env.uid,
            "first_activity": "2026-07-01 10:00:00",
            "last_activity": "2026-07-01 10:00:00",
        }
        base.update(vals)
        return self.env["res.device.log"].create(base)

    def test_view_identity_derives_from_constant(self):
        from odoo.addons.base.models.res_device import _DEVICE_IDENTITY_COLUMNS

        where = self.env["res.device"]._where()
        for column, _nullable in _DEVICE_IDENTITY_COLUMNS:
            self.assertIn(f"D2.{column}", where)
        self.assertNotIn("ip_address", where)

    def test_gc_keeps_ip_history_view_shows_latest(self):
        old_ip = self._log(last_activity="2026-07-01 10:00:00")
        new_ip = self._log(ip_address="10.0.0.2", last_activity="2026-07-01 11:00:00")
        self.env.flush_all()
        devices = (
            self.env["res.device"]
            .sudo()
            .search([("session_identifier", "=", "sid_rdev_p4")])
        )
        self.assertEqual(devices.ids, [new_ip.id], "view shows only the latest row")
        self.env["res.device.log"]._gc_device_log()
        survivors = self.env["res.device.log"].search(
            [("session_identifier", "=", "sid_rdev_p4")]
        )
        self.assertEqual(
            survivors,
            old_ip | new_ip,
            "GC keeps one row per IP for linked_ip_addresses history",
        )

    def test_null_user_rows_dedup_consistently(self):
        old = self._log(user_id=False, last_activity="2026-07-01 10:00:00")
        newest = self._log(user_id=False, last_activity="2026-07-01 11:00:00")
        self.env.flush_all()
        devices = (
            self.env["res.device"]
            .sudo()
            .search([("session_identifier", "=", "sid_rdev_p4")])
        )
        self.assertEqual(devices.ids, [newest.id])
        self.env["res.device.log"]._gc_device_log()
        survivors = self.env["res.device.log"].search(
            [("session_identifier", "=", "sid_rdev_p4")]
        )
        self.assertEqual(survivors, newest, f"GC must delete hidden row {old.id}")


@tagged("post_install", "-at_install")
class TestSelfServiceEscalation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="escalation_user")
        cls.tag = cls.env["res.partner.tag"].create({"name": "victim tag"})
        cls.other = cls.env["res.partner"].create(
            {"name": "other", "tag_ids": [Command.link(cls.tag.id)]}
        )
        cls.self_writeable = cls.env["res.users"]._get_self_accessible_fields()[1]

    def _self_write(self, vals):
        self.user.with_user(self.user).write(vals)

    def test_no_one2many_is_self_writeable(self):
        fields_ = self.env["res.users"]._fields
        listed = [
            name
            for name in self.self_writeable
            if fields_.get(name) and fields_[name].type == "one2many"
        ]
        self.assertFalse(listed, "one2many fields cannot be self-written")

    def test_one2many_command_is_not_escalated(self):
        key = (
            self.env["res.users.apikeys"]
            .with_user(self.user)
            ._generate(None, "k", datetime.now() + timedelta(hours=1))
        )
        self.assertTrue(key)
        record = (
            self.env["res.users.apikeys"]
            .sudo()
            .search([("user_id", "=", self.user.id)])
        )
        with patch.object(
            type(self.env["res.users"]),
            "SELF_WRITEABLE_FIELDS",
            property(lambda s: ["api_key_ids"]),
        ):
            self.env.registry.clear_cache("stable")
            with self.assertRaises(AccessError):
                self._self_write({"api_key_ids": [Command.delete(record.id)]})
        self.env.registry.clear_cache("stable")
        self.assertTrue(record.exists(), "the key was destroyed by a self-write")

    def test_destructive_many2many_command_is_not_escalated(self):
        with patch.object(
            type(self.env["res.users"]),
            "SELF_WRITEABLE_FIELDS",
            property(lambda s: ["tag_ids"]),
        ):
            self.env.registry.clear_cache("stable")
            for command in (
                Command.delete(self.tag.id),
                Command.create({"name": "forged"}),
                Command.update(self.tag.id, {"name": "renamed"}),
            ):
                with self.assertRaises(AccessError):
                    self._self_write({"tag_ids": [command]})
        self.env.registry.clear_cache("stable")
        self.assertTrue(self.tag.exists(), "the tag was destroyed by a self-write")
        self.assertEqual(self.tag.name, "victim tag", "the tag was renamed")

    def test_relation_only_many2many_command_is_escalated(self):
        with patch.object(
            type(self.env["res.users"]),
            "SELF_WRITEABLE_FIELDS",
            property(lambda s: ["tag_ids"]),
        ):
            self.env.registry.clear_cache("stable")
            self._self_write({"tag_ids": [Command.link(self.tag.id)]})
            self.assertIn(self.tag, self.user.tag_ids)
            self._self_write({"tag_ids": [Command.unlink(self.tag.id)]})
            self.assertNotIn(self.tag, self.user.tag_ids)
            self._self_write({"tag_ids": [Command.set(self.tag.ids)]})
            self.assertEqual(self.user.tag_ids, self.tag)
            self._self_write({"tag_ids": [Command.clear()]})
            self.assertFalse(self.user.tag_ids)
        self.env.registry.clear_cache("stable")
        self.assertTrue(self.tag.exists(), "a relation edit destroyed the tag")

    def test_shorthand_values_are_classified_by_effect(self):
        Users = self.env["res.users"]
        self.assertTrue(
            Users._is_escaping_own_record({"tag_ids": [{"name": "forged"}]}),
            "the dict create shorthand must not be escalated",
        )
        self.assertFalse(
            Users._is_escaping_own_record({"tag_ids": [self.tag.id]}),
            "the bare-id link shorthand is a relation edit",
        )
        self.assertFalse(
            Users._is_escaping_own_record({"tag_ids": self.tag}),
            "assigning a recordset replaces the relation only",
        )
        self.assertFalse(
            Users._is_escaping_own_record({"tz": "Europe/Brussels"}),
            "scalars never escape the row",
        )


class TestSelfFieldBatchAccessLeak(UsersCommonCase):
    def _spy_ensure_access(self):
        from odoo.fields import Field

        seen = []
        original = Field.check_read_access

        def spy(field, record):
            seen.append(len(record))
            return original(field, record)

        patcher = patch.object(Field, "check_read_access", spy)
        patcher.start()
        self.addCleanup(patcher.stop)
        return seen

    def test_mapped_checks_the_whole_recordset(self):
        pair = self.user_internal | self.user_portal_1
        seen = self._spy_ensure_access()
        pair.mapped("login")
        self.assertIn(
            2,
            seen,
            "mapped must check_read_access on the full recordset, not records[:1]",
        )
        self.assertNotIn(1, seen, "no fast-path check_read_access saw only one record")

    def test_filtered_checks_the_whole_recordset(self):
        pair = self.user_internal | self.user_portal_1
        seen = self._spy_ensure_access()
        pair.filtered("share")
        self.assertIn(2, seen)
        self.assertNotIn(1, seen)

    def test_grouped_checks_the_whole_recordset(self):
        pair = self.user_internal | self.user_portal_1
        seen = self._spy_ensure_access()
        pair.grouped("login")
        self.assertIn(2, seen)
        self.assertNotIn(1, seen)

    def test_sorted_checks_the_whole_recordset(self):
        pair = self.user_internal | self.user_portal_1
        seen = self._spy_ensure_access()
        pair.sorted("login")
        self.assertIn(2, seen)
        self.assertNotIn(1, seen)

    def test_end_to_end_disclosure_is_blocked(self):
        alice = new_test_user(self.env, login="b7_alice", groups="base.group_user")
        bob = new_test_user(self.env, login="b7_bob", groups="base.group_user")
        login = self.env["res.users"]._fields["login"]
        self.assertIn("login", alice._get_self_accessible_fields()[0])
        original_groups = login.groups
        login.groups = "base.group_system"
        self.addCleanup(setattr, login, "groups", original_groups)

        as_alice = self.env(user=alice)
        pair = as_alice["res.users"].browse([alice.id, bob.id])
        pair.sudo().read(["login"])
        with self.assertRaises(AccessError):
            pair.mapped("login")

    def test_own_record_still_readable(self):
        alice = new_test_user(self.env, login="b7_alice2", groups="base.group_user")
        login = self.env["res.users"]._fields["login"]
        original_groups = login.groups
        login.groups = "base.group_system"
        self.addCleanup(setattr, login, "groups", original_groups)
        own = self.env(user=alice)["res.users"].browse(alice.id).mapped("login")
        self.assertEqual(own, ["b7_alice2"])


class TestSessionTokenInvalidation(TransactionCase):
    SID = "session-id-under-test-0123456789"

    def _user(self, login):
        return new_test_user(self.env, login, password="Secret!Pwd123")

    def test_write_path_rotates_the_token(self):
        user = self._user("sess_write")
        before = user._get_session_token(self.SID)
        self.assertTrue(before)

        user.write({"password": "Another!Pwd456"})
        self.env.flush_all()
        self.assertNotEqual(before, user._get_session_token(self.SID))

    def test_encrypted_setter_rotates_the_token(self):
        user = self._user("sess_encrypted")
        before = user._get_session_token(self.SID)

        hashed = self.env["res.users"]._get_crypt_context().hash("Another!Pwd456")
        user._update_encrypted_password(user.id, hashed)
        self.env.flush_all()

        self.assertNotEqual(
            before,
            user._get_session_token(self.SID),
            "a password written straight to the column must still end the session",
        )

    def test_empty_password_setter_rotates_the_token(self):
        user = self._user("sess_empty")
        before = user._get_session_token(self.SID)

        user._clear_password()
        self.env.flush_all()

        self.assertNotEqual(
            before,
            user._get_session_token(self.SID),
            "clearing the password must end the session -- this is the path "
            "auth_ldap.change_password takes",
        )

    def test_archiving_rotates_the_token(self):
        user = self._user("sess_archive")
        before = user._get_session_token(self.SID)

        user.active = False
        self.env.flush_all()

        self.assertNotEqual(before, user._get_session_token(self.SID))

    def test_an_untouched_user_keeps_its_token(self):
        user = self._user("sess_stable")
        other = self._user("sess_other")
        before = user._get_session_token(self.SID)

        other.write({"password": "Another!Pwd456"})
        self.env.flush_all()

        self.assertEqual(
            before,
            user._get_session_token(self.SID),
            "one user's password change must not invalidate another's session",
        )


class TestAdministratorSurvivesArchiving(TransactionCase):
    def _admin(self, login):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "group_ids": [Command.link(self.env.ref("base.group_system").id)],
            }
        )

    def _active_admins(self):
        return (
            self.env["res.users"]
            .sudo()
            .search(
                [
                    ("all_group_ids", "in", self.env.ref("base.group_system").ids),
                    ("active", "=", True),
                ]
            )
        )

    def test_archiving_the_last_administrator_is_refused(self):
        spare = self._admin("ru_arch_spare")
        admins = self._active_admins()
        self.assertIn(spare, admins)

        (admins - spare).write({"active": False})
        self.env.flush_all()
        self.assertEqual(
            self._active_admins(),
            spare,
            "archiving all but one administrator must be allowed",
        )

        with self.assertRaises(ValidationError):
            spare.with_user(SUPERUSER_ID).write({"active": False})
            self.env.flush_all()

    def test_archiving_a_non_administrator_is_unaffected(self):
        portal = new_test_user(
            self.env, login="ru_arch_portal", groups="base.group_portal"
        )
        before = self._active_admins()

        portal.with_user(SUPERUSER_ID).write({"active": False})
        self.env.flush_all()

        self.assertFalse(portal.active)
        self.assertEqual(self._active_admins(), before)


class TestBlankNameAvatar(TransactionCase):
    def test_a_blank_after_strip_name_does_not_crash_create(self):
        user = self.env["res.users"].create({"login": "ru_blank_name", "name": "   "})
        self.env.flush_all()
        self.assertFalse(
            user.image_1920,
            "no avatar can be generated from a name with no first character",
        )
        self.assertTrue(user.avatar_128, "the mixin still answers with a placeholder")

    def test_the_import_path_accepts_a_blank_name(self):
        result = self.env["res.users"].load(
            ["login", "name"], [["ru_blank_load", "  "]]
        )
        self.assertFalse(
            [m for m in result["messages"] if m.get("type") == "error"],
            f"import must not fail on a padded-blank name: {result['messages']}",
        )
        self.assertTrue(result["ids"])

    def test_a_real_name_still_gets_an_avatar(self):
        user = self.env["res.users"].create(
            {"login": "ru_real_name", "name": " Real Name "}
        )
        self.env.flush_all()
        self.assertTrue(user.image_1920)


class TestRoleIsWritable(TransactionCase):
    def _user(self, login):
        return self.env["res.users"].create({"name": login, "login": login})

    def test_writing_role_changes_the_groups(self):
        user = self._user("ru_role_write")
        self.assertEqual(user.role, "group_user")

        user.write({"role": "group_system"})
        self.env.flush_all()
        user.invalidate_recordset()

        self.assertEqual(user.role, "group_system")
        self.assertTrue(user._is_system())
        self.assertTrue(user._is_internal(), "the implied internal group must remain")

    def test_writing_role_back_to_user_drops_the_admin_group(self):
        self.env["res.users"].create(
            {
                "name": "ru_role_spare_admin",
                "login": "ru_role_spare_admin",
                "group_ids": [Command.link(self.env.ref("base.group_system").id)],
            }
        )
        user = self._user("ru_role_demote")
        user.write({"role": "group_system"})
        self.env.flush_all()

        user.write({"role": "group_user"})
        self.env.flush_all()
        user.invalidate_recordset()

        self.assertEqual(user.role, "group_user")
        self.assertFalse(user._is_system())

    def test_the_import_path_applies_the_role(self):
        result = self.env["res.users"].load(
            ["login", "name", "role"],
            [["ru_role_import", "Ru Role Import", "group_system"]],
        )
        self.assertTrue(result["ids"], result["messages"])
        self.env.flush_all()

        user = self.env["res.users"].browse(result["ids"][0])
        self.assertTrue(
            user._is_system(),
            "an imported Role column must produce the access rights it names",
        )

    def test_role_keeps_the_other_groups(self):
        extra = self.env["res.groups"].create({"name": "RU Role Extra"})
        user = self._user("ru_role_keep")
        user.write({"group_ids": [Command.link(extra.id)]})
        self.env.flush_all()

        user.write({"role": "group_system"})
        self.env.flush_all()
        user.invalidate_recordset()

        self.assertIn(extra, user.group_ids)
        self.assertTrue(user._is_system())

    def test_login_date_declares_no_write(self):
        field = self.env["res.users"]._fields["login_date"]
        self.assertTrue(
            field.readonly,
            "login_date resolves through a readonly target, so it takes no inverse",
        )
        self.assertIsNone(field.inverse)


class TestCredentialsBindToSelf(TransactionCase):
    PASSWORD = "Ru!Cred12345"

    def _user(self, login, password=None):
        user = self.env["res.users"].create({"name": login, "login": login})
        user._change_password(password or self.PASSWORD)
        self.env.flush_all()
        return user

    def test_credentials_answer_about_self_not_env_user(self):
        victim = self._user("ru_cred_victim", "Ru!Victim12345")
        caller = self._user("ru_cred_caller", "Ru!Caller12345")

        with self.assertRaises(
            AccessDenied,
            msg="the caller's own password must not authenticate another record",
        ):
            victim.with_user(caller)._check_credentials(
                {
                    "login": caller.login,
                    "password": "Ru!Caller12345",
                    "type": "password",
                },
                {"interactive": True},
            )

        self.assertEqual(
            victim.with_user(caller)._check_credentials(
                {
                    "login": victim.login,
                    "password": "Ru!Victim12345",
                    "type": "password",
                },
                {"interactive": True},
            )["uid"],
            victim.id,
            "the record's own password must still authenticate it",
        )

    def test_the_returned_uid_is_the_checked_record(self):
        user = self._user("ru_cred_uid")
        public = self.env.ref("base.public_user")

        result = user.with_user(public)._check_credentials(
            {"login": user.login, "password": self.PASSWORD, "type": "password"},
            {"interactive": True},
        )

        self.assertEqual(
            result["uid"],
            user.id,
            "the uid must name the authenticated record, not the acting environment",
        )

    def test_a_multi_record_check_is_refused(self):
        two = self._user("ru_cred_a") | self._user("ru_cred_b")
        with self.assertRaises(ValueError):
            two._check_credentials(
                {"login": "x", "password": self.PASSWORD, "type": "password"},
                {"interactive": True},
            )


class TestUnknownGroupReference(TransactionCase):
    def test_an_uninstalled_module_stays_lenient(self):
        user = self.env.ref("base.user_admin")
        with self.assertNoLogs("odoo.addons.base.models.res_users", "WARNING"):
            self.assertFalse(user.has_group("no_such_module.group_x"))
            self.assertTrue(user.has_groups("!no_such_module.group_x"))

    def test_a_typo_inside_a_loaded_module_is_named(self):
        user = self.env.ref("base.user_admin")
        with self.assertLogs("odoo.addons.base.models.res_users", "WARNING") as logs:
            self.assertFalse(user.has_group("base.group_sytem_typo_probe"))
        self.assertIn("group_sytem_typo_probe", "".join(logs.output))

    def test_known_references_are_unaffected(self):
        user = self.env.ref("base.user_admin")
        self.assertTrue(user.has_group("base.group_system"))
        self.assertTrue(user.has_groups("base.group_system,base.group_user"))
        self.assertFalse(user.has_groups("!base.group_system"))
        self.assertTrue(user.has_groups("!base.group_portal"))
        self.assertFalse(user.has_groups("."))
        self.assertFalse(user.has_groups(""))

    def test_every_group_family_shares_one_debug_rule(self):
        user = self.env.ref("base.user_admin")
        no_one = self.env.ref("base.group_no_one")
        user.write({"group_ids": [Command.link(no_one.id)]})
        self.env.flush_all()

        self.assertFalse(user.has_group("base.group_no_one"))
        self.assertFalse(user.has_groups("base.group_no_one"))
        self.assertFalse(user.has_any_group_id(no_one.ids))


class TestRelatedInverseIsBatched(TransactionCase):
    def _users(self, n, prefix):
        return self.env["res.users"].create(
            [{"name": f"{prefix}{i}", "login": f"{prefix}{i}"} for i in range(n)]
        )

    def _cost(self, users, vals):
        self.env.flush_all()
        before = self.env.cr.sql_statement_count
        users.write(vals)
        self.env.flush_all()
        return self.env.cr.sql_statement_count - before

    def test_one_shared_value_costs_one_write_however_many_records(self):
        few = self._users(2, "ru_rel_few")
        many = self._users(20, "ru_rel_many")
        self.env.flush_all()

        small = self._cost(few, {"name": "Ru Rel Shared"})
        large = self._cost(many, {"name": "Ru Rel Shared"})

        self.assertLessEqual(
            large - small,
            4,
            f"writing one related value to 20 records must not cost per record "
            f"(N=2 {small} queries, N=20 {large})",
        )

    def test_distinct_values_still_land_on_their_own_record(self):
        users = self._users(3, "ru_rel_distinct")
        self.env.flush_all()

        users[0].name = "Ru Alpha"
        users[1].name = "Ru Beta"
        users[2].name = "Ru Gamma"
        self.env.flush_all()
        users.invalidate_recordset()

        self.assertEqual(users.mapped("name"), ["Ru Alpha", "Ru Beta", "Ru Gamma"])
        self.assertEqual(
            users.partner_id.mapped("name"), ["Ru Alpha", "Ru Beta", "Ru Gamma"]
        )

    def test_the_last_record_wins_when_two_share_a_target(self):
        company = self.env["res.company"].create({"name": "Ru Rel Co"})
        users = self.env["res.users"].create(
            [
                {
                    "name": f"ru_rel_share{i}",
                    "login": f"ru_rel_share{i}",
                    "company_id": company.id,
                    "company_ids": [Command.set(company.ids)],
                }
                for i in range(3)
            ]
        )
        self.env.flush_all()

        partner = self.env["res.partner"].create({"name": "Ru Shared Target"})
        users.write({"partner_id": partner.id})
        self.env.flush_all()

        users[0].name = "Ru First"
        users[1].name = "Ru Second"
        users[2].name = "Ru First"
        self.env.flush_all()
        partner.invalidate_recordset()

        self.assertEqual(
            partner.name,
            "Ru First",
            "the last record written must win, as it did record by record",
        )

    def test_a_falsy_value_still_reaches_the_target(self):
        users = self._users(2, "ru_rel_falsy")
        users.write({"email": "shared@example.com"})
        self.env.flush_all()

        users.write({"email": False})
        self.env.flush_all()
        users.invalidate_recordset()

        self.assertFalse(any(users.mapped("email")))
        self.assertFalse(any(users.partner_id.mapped("email")))


class TestPasswordWriteIsBatched(TransactionCase):
    def test_a_batch_password_write_costs_one_statement_per_row(self):
        users = self.env["res.users"].create(
            [{"name": f"ru_pw{i}", "login": f"ru_pw{i}"} for i in range(3)]
        )
        self.env.flush_all()

        users.write({"password": "Ru!Batch12345"})
        self.env.flush_all()

        for user in users:
            self.assertEqual(
                user._check_credentials(
                    {
                        "login": user.login,
                        "password": "Ru!Batch12345",
                        "type": "password",
                    },
                    {"interactive": True},
                )["uid"],
                user.id,
            )

    def test_clearing_passwords_in_a_batch_clears_every_row(self):
        users = self.env["res.users"].create(
            [{"name": f"ru_pwc{i}", "login": f"ru_pwc{i}"} for i in range(3)]
        )
        users.write({"password": "Ru!Batch12345"})
        self.env.flush_all()

        users.write({"password": ""})
        self.env.flush_all()

        self.env.cr.execute(
            "SELECT COUNT(*) FROM res_users WHERE id = ANY(%s) AND password IS NOT NULL",
            (users.ids,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], 0)


class TestCryptContextConfiguration(TransactionCase):
    def test_a_non_numeric_rounds_parameter_does_not_break_authentication(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "password.hashing.rounds", "not-a-number"
        )
        with mute_logger("odoo.addons.base.models.res_users"):
            context = self.env["res.users"]._get_crypt_context()
        self.assertTrue(context.hash("Ru!Rounds1234"))

    def test_rounds_above_the_backend_maximum_still_authenticate(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "password.hashing.rounds", "20000000"
        )
        self.env.registry.clear_cache("stable")
        context = self.env["res.users"]._get_crypt_context()
        hashed = context.hash("Ru!Rounds9999")
        self.assertTrue(
            context.is_password_valid("Ru!Rounds9999", hashed),
            "a rounds value above the backend cap must not lock users out",
        )


class TestLoginPath(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = new_test_user(self.env, "login_path", password="Login!Path123")
        self.credential = {
            "login": "login_path",
            "password": "Login!Path123",
            "type": "password",
        }

    def _login(self, **overrides):
        return self.env["res.users"]._login(
            {**self.credential, **overrides}, {"interactive": True}
        )

    def _store_raw_password(self, raw):
        self.env.cr.execute(
            "UPDATE res_users SET password = %s WHERE id = %s", [raw, self.user.id]
        )
        self.env.registry.clear_cache()

    def _stored_password(self):
        self.env.cr.execute(
            "SELECT password FROM res_users WHERE id = %s", [self.user.id]
        )
        return self.env.cr.fetchone()[0]

    def test_a_valid_login_answers_with_the_user(self):
        self.assertEqual(self._login()["uid"], self.user.id)

    def test_an_unknown_login_is_denied(self):
        with self.assertRaises(AccessDenied):
            self._login(login="nobody-here")

    def test_an_archived_user_is_denied(self):
        self.user.active = False
        self.env.flush_all()
        with self.assertRaises(AccessDenied):
            self._login()

    def _production_crypt_context(self):
        return patch(
            "odoo.addons.base.models.res_users.ResUsersPatchedInTest._get_crypt_context",
            lambda user: CryptContext(
                ["pbkdf2_sha512", "plaintext"],
                deprecated=["auto"],
                pbkdf2_sha512__rounds=1,
            ),
        )

    def test_a_stored_plaintext_password_logs_in_and_is_hashed_on_the_way(self):
        self._store_raw_password("legacy-plain")
        with self._production_crypt_context():
            self.assertEqual(self._login(password="legacy-plain")["uid"], self.user.id)
        stored = self._stored_password()
        context = self.env["res.users"]._get_crypt_context()
        self.assertNotEqual(stored, "legacy-plain")
        self.assertEqual(context.identify(stored), "pbkdf2_sha512")
        self.assertEqual(
            self._login(password="legacy-plain")["uid"],
            self.user.id,
            "the rehashed password still matches",
        )

    def test_a_hash_at_other_rounds_than_configured_is_rehashed_at_login(self):
        context = self.env["res.users"]._get_crypt_context()
        weak = pbkdf2_sha512_hash("weak-rounds", 2)
        self.assertIsNotNone(
            context.match_and_update("weak-rounds", weak)[1],
            "precondition: the weak hash is one the context wants to replace",
        )
        self._store_raw_password(weak)
        self._login(password="weak-rounds")
        self.assertEqual(
            context.match_and_update("weak-rounds", self._stored_password()),
            (True, None),
            "after one login the stored hash is at the configured strength",
        )

    def test_an_api_key_is_not_an_interactive_password(self):
        key = (
            self.env["res.users.apikeys"]
            .with_user(self.user)
            ._generate("rpc", "k", datetime.now() + timedelta(days=1))
        )
        with self.assertRaises(AccessDenied):
            self._login(password=key)
        auth = self.user.with_user(self.user)._check_credentials(
            {**self.credential, "password": key}, {"interactive": False}
        )
        self.assertEqual(
            auth, {"uid": self.user.id, "auth_method": "apikey", "mfa": "default"}
        )

    def test_authenticate_records_the_base_url_for_system_users_only(self):
        ICP = self.env["ir.config_parameter"].sudo()
        agent = {"interactive": True, "base_location": "http://from-login.test"}
        Users = self.env["res.users"]

        Users.authenticate(self.credential, agent)
        self.assertNotEqual(ICP.get_param("web.base.url"), "http://from-login.test")

        new_test_user(
            self.env,
            "login_path_admin",
            password="Admin!Path123",
            groups="base.group_system",
        )
        admin_credential = {
            **self.credential,
            "login": "login_path_admin",
            "password": "Admin!Path123",
        }
        Users.authenticate(admin_credential, agent)
        self.assertEqual(ICP.get_param("web.base.url"), "http://from-login.test")

        ICP.set_param("web.base.url.freeze", "True")
        Users.authenticate(
            admin_credential, {**agent, "base_location": "http://later.test"}
        )
        self.assertEqual(ICP.get_param("web.base.url"), "http://from-login.test")


class TestUsersDisplayName(TransactionCase):
    def test_name_is_the_display_name_without_context(self):
        Users = self.env["res.users"].with_context({})
        new_test_user(self.env, "dn_column_user", name="Column User")
        for user in Users.with_context(active_test=False).search([]):
            self.assertEqual(
                user.display_name,
                user.name,
                "with no display context, display_name must be the declared column",
            )
        self.assertEqual(Users._display_name_column, "name")

    def test_an_exact_login_takes_precedence_over_the_name_search(self):
        Users = self.env["res.users"]
        exact = new_test_user(self.env, "exact_login", name="Someone Else")
        new_test_user(self.env, "other_login", name="exact_login by name")
        self.assertEqual(Users._display_name_search_exact, ("login",))
        self.assertEqual(
            Users._search_display_name("ilike", "exact_login"),
            [("id", "in", [exact.id])],
        )
        self.assertEqual(
            Users._search_display_name("in", ["exact_login", "nobody"]),
            [("id", "in", [exact.id])],
        )
        self.assertEqual(
            Users._search_display_name("ilike", "by name"),
            models.BaseModel._search_display_name(Users, "ilike", "by name"),
            "without an exact login the default composition answers",
        )
        self.assertEqual(
            Users._search_display_name("=", "exact_login"),
            models.BaseModel._search_display_name(Users, "=", "exact_login"),
            "precedence applies to 'in' and 'ilike' only",
        )
