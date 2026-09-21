from unittest.mock import patch

from odoo.exceptions import AccessError, ConcurrencyError, LockError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("web_unit", "web_users")
class TestResUsersSettings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "Jean",
                "login": "jean@mail.com",
                "password": "jean@mail.com",
            }
        )
        cls.user_settings = cls.env["res.users.settings"]._get_or_create_for_user(
            cls.user
        )
        cls.window_action = cls.env["ir.actions.act_window"].create(
            {
                "name": "Test Action",
                "res_model": "res.users",
            }
        )

    def test_fields_validity_embedded_action_settings(self):
        embedded_action_settings_data = {
            "user_setting_id": self.user_settings.id,
            "action_id": self.window_action.id,
            "res_model": "res.users",
            "res_id": self.user.id,
            "embedded_visibility": True,
        }

        embedded_action_settings_data.update(
            {
                "embedded_actions_order": "1,2,1",
                "embedded_actions_visibility": "3,3,4",
            }
        )
        with self.assertRaises(
            ValidationError,
            msg="The ids in embedded_actions_order must not be duplicated",
        ):
            self.env["res.users.settings.embedded.action"].create(
                embedded_action_settings_data
            )

        embedded_action_settings_data.update(
            {
                "embedded_actions_order": "1,2,true",
                "embedded_actions_visibility": "3,4,false,abc",
            }
        )
        with self.assertRaises(
            ValidationError,
            msg='The ids in embedded_actions_order must only be integers or "false"',
        ):
            self.env["res.users.settings.embedded.action"].create(
                embedded_action_settings_data
            )

    def test_unicode_superscript_digit_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["res.users.settings.embedded.action"].create(
                {
                    "user_setting_id": self.user_settings.id,
                    "action_id": self.window_action.id,
                    "res_model": "res.users",
                    "embedded_actions_order": "1,\u00b2,3",
                }
            )

    def test_set_and_get_embedded_action_settings(self):
        settings_vals = {
            "embedded_actions_order": [False, 1, 2, 3],
            "embedded_actions_visibility": [2, False, 3],
            "embedded_visibility": True,
        }
        self.user_settings.set_embedded_actions_setting(
            action_id=self.window_action.id,
            res_id=self.user.id,
            vals={
                **settings_vals,
                "res_model": "res.users",
            },
        )
        embedded_actions_config = self.user_settings.embedded_actions_config_ids
        self.assertEqual(
            len(embedded_actions_config),
            1,
            "There should be one embedded action setting created.",
        )
        self.assertEqual(
            embedded_actions_config.action_id,
            self.window_action,
            "The action should match the one set.",
        )
        self.assertEqual(
            embedded_actions_config.res_id,
            self.user.id,
            "The res_id should match the one set.",
        )
        self.assertEqual(
            embedded_actions_config.res_model,
            "res.users",
            "The res_model should match the one set.",
        )
        self.assertEqual(
            embedded_actions_config.embedded_actions_order,
            "false,1,2,3",
            "The embedded actions order should match the one set.",
        )
        self.assertEqual(
            embedded_actions_config.embedded_actions_visibility,
            "2,false,3",
            "The embedded actions visibility should match the one set.",
        )
        self.assertEqual(
            embedded_actions_config.embedded_visibility,
            True,
            "The embedded visibility should be True.",
        )
        embedded_settings = self.user_settings.get_embedded_actions_settings()
        expected_settings = {
            f"{self.window_action.id}+{self.user.id}": settings_vals,
        }
        self.assertEqual(
            embedded_settings,
            expected_settings,
            "The settings should be correctly formatted with the given values.",
        )

        new_settings_vals = {
            "embedded_actions_order": [3, 1, False, 2],
            "embedded_actions_visibility": [1, 3],
            "embedded_visibility": False,
        }
        self.user_settings.set_embedded_actions_setting(
            action_id=self.window_action.id,
            res_id=self.user.id,
            vals=new_settings_vals,
        )
        embedded_actions_config = self.user_settings.embedded_actions_config_ids
        self.assertEqual(
            len(embedded_actions_config),
            1,
            "There should still be one embedded action setting after update.",
        )
        self.assertEqual(
            embedded_actions_config.action_id,
            self.window_action,
            "The action should remain the same after update.",
        )
        self.assertEqual(
            embedded_actions_config.res_id,
            self.user.id,
            "The res_id should remain the same after update.",
        )
        self.assertEqual(
            embedded_actions_config.res_model,
            "res.users",
            "The res_model should remain the same after update.",
        )
        self.assertEqual(
            embedded_actions_config.embedded_actions_order,
            "3,1,false,2",
            "The embedded actions order should be updated.",
        )
        self.assertEqual(
            embedded_actions_config.embedded_actions_visibility,
            "1,3",
            "The embedded actions visibility should be updated.",
        )
        self.assertEqual(
            embedded_actions_config.embedded_visibility,
            False,
            "The embedded visibility should be updated to False.",
        )
        embedded_settings = self.user_settings.get_embedded_actions_settings()
        expected_settings = {
            f"{self.window_action.id}+{self.user.id}": new_settings_vals,
        }
        self.assertEqual(
            embedded_settings,
            expected_settings,
            "The settings should be correctly formatted after the update with the new values.",
        )

    def test_set_embedded_actions_ignores_non_whitelisted_keys(self):
        other_user = self.env["res.users"].create(
            {
                "name": "Mallory",
                "login": "mallory@mail.com",
                "password": "mallory@mail.com",
            }
        )
        other_settings = self.env["res.users.settings"]._get_or_create_for_user(
            other_user
        )
        self.user_settings.set_embedded_actions_setting(
            action_id=self.window_action.id,
            res_id=self.user.id,
            vals={
                "res_model": "res.users",
                "embedded_visibility": True,
                "user_setting_id": other_settings.id,
            },
        )
        config = self.user_settings.embedded_actions_config_ids
        self.assertEqual(len(config), 1)
        self.assertEqual(
            config.user_setting_id,
            self.user_settings,
            "The row must stay bound to the caller's own settings.",
        )
        self.assertFalse(
            other_settings.embedded_actions_config_ids,
            "The victim's settings must not have gained a config row.",
        )
        self.user_settings.set_embedded_actions_setting(
            action_id=self.window_action.id,
            res_id=self.user.id,
            vals={
                "embedded_visibility": False,
                "user_setting_id": other_settings.id,
            },
        )
        self.assertEqual(config.user_setting_id, self.user_settings)
        self.assertFalse(other_settings.embedded_actions_config_ids)

    def test_launcher_empty_override_and_operation_merging(self):
        settings = self.user_settings.with_user(self.user)
        self.user.company_id.web_config_id.homemenu_default_config = {
            "pinned": ["app.a"]
        }
        settings.update_homemenu_config(
            [{"operation": "pin", "xmlid": "app.a", "value": False}]
        )
        self.assertEqual(
            settings.homemenu_config,
            {"version": 2, "order": [], "pinned": [], "hidden": []},
        )
        settings.update_homemenu_config(
            [{"operation": "pin", "xmlid": "app.a", "value": True}]
        )
        settings.update_homemenu_config(
            [{"operation": "pin", "xmlid": "app.b", "value": True}]
        )
        self.assertEqual(settings.homemenu_config["pinned"], ["app.a", "app.b"])
        settings.update_homemenu_config(
            [{"operation": "pin", "xmlid": "app.b", "value": True}]
        )
        self.assertEqual(settings.homemenu_config["pinned"], ["app.a", "app.b"])

    def test_launcher_hide_reset_and_stale_pinned_order(self):
        settings = self.user_settings.with_user(self.user)
        settings.update_homemenu_config(
            [
                {"operation": "pin", "xmlid": "app.a", "value": True},
                {"operation": "pin", "xmlid": "app.b", "value": True},
                {"operation": "pin", "xmlid": "app.c", "value": True},
            ]
        )
        settings.update_homemenu_config(
            [{"operation": "pinned_order", "value": ["app.b", "app.a"]}]
        )
        self.assertEqual(
            settings.homemenu_config["pinned"], ["app.b", "app.a", "app.c"]
        )
        settings.update_homemenu_config(
            [{"operation": "hide", "xmlid": "app.a", "value": True}]
        )
        self.assertNotIn("app.a", settings.homemenu_config["pinned"])
        self.assertEqual(settings.homemenu_config["hidden"], ["app.a"])
        settings.update_homemenu_config([{"operation": "reset"}])
        self.assertFalse(settings.homemenu_config)

    def test_launcher_rejects_foreign_settings_and_invalid_changes(self):
        with self.assertRaises(AccessError):
            self.user_settings.update_homemenu_config([{"operation": "reset"}])
        settings = self.user_settings.with_user(self.user)
        for changes in (
            {},
            [None],
            [{"operation": "unknown"}],
            [{"operation": "pin", "xmlid": "app.a", "value": "yes"}],
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                settings.update_homemenu_config(changes)

    def test_launcher_normalizes_legacy_duplicate_and_conflicting_entries(self):
        normalize = self.user_settings._normalize_homemenu_config
        self.assertEqual(normalize('["app.a", "app.a"]')["order"], ["app.a"])
        self.assertEqual(
            normalize({"pinned": ["app.a", "app.a"], "hidden": ["app.a"]})["pinned"], []
        )
        self.assertIsNone(normalize({"version": 999}))
        self.assertIsNone(normalize("invalid"))

    def test_home_menu_lock_conflict_requests_transaction_retry(self):
        settings = self.user_settings.with_user(self.user)
        with patch.object(
            type(settings), "lock_for_update", side_effect=LockError("busy")
        ):
            with self.assertRaises(ConcurrencyError):
                settings.update_homemenu_config(
                    [{"operation": "pin", "xmlid": "app.a", "value": True}]
                )
        self.assertFalse(settings.homemenu_config)
