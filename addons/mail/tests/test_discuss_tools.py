# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common import MailCase
from odoo.tests.common import new_test_user
from odoo.addons.bus.tests.common import BusResult


class TestDiscussTools(MailCase):
    """Test class for discuss tools."""

    # 0xx generic tests (key not in ids_by_model)

    def test_010_store_dict(self):
        """Test dict is present in result."""
        store = Store()
        store.add_model_values("key1", {"id": 1, "test": True})
        self.assertEqual(store._build_result(), {"key1": [{"id": 1, "test": True}]})

    def test_011_store_dict_update_same_id(self):
        """Test dict update same id."""
        store = Store()
        store.add_model_values("key1", {"id": 1, "test": True})
        store.add_model_values("key1", {"id": 1, "test": False, "abc": 1})
        self.assertEqual(store._build_result(), {"key1": [{"id": 1, "test": False, "abc": 1}]})

    def test_012_store_dict_update_multiple_ids(self):
        """Test dict update multiple ids."""
        store = Store()
        store.add_model_values("key1", {"id": 1, "test": True})
        store.add_model_values("key1", {"id": 2, "test": True})
        store.add_model_values("key1", {"id": 2, "test": False, "abc": 1})
        self.assertEqual(
            store._build_result(),
            {"key1": [{"id": 1, "test": True}, {"id": 2, "test": False, "abc": 1}]},
        )

    def test_040_store_invalid(self):
        """Test adding invalid value."""
        store = Store()
        store.add_model_values("key1", True)
        with self.assertRaises(TypeError):
            store._build_result()

    def test_042_store_invalid_missing_id(self):
        """Test Thread adding invalid list value."""
        store = Store()
        store.add_model_values("key1", {"test": True})
        with self.assertRaises(AssertionError):
            store._build_result()

    def test_060_store_data_empty_val(self):
        """Test empty values are not present in result."""
        store = Store()
        store.add_model_values("key1", {})
        self.assertEqual(store._build_result(), {})

    def test_061_store_data_empty_not_empty(self):
        """Test mixing empty and non-empty values."""
        store = Store()
        store.add_model_values("key1", {})
        store.add_model_values("key2", {"id": 1})
        self.assertEqual(store._build_result(), {"key2": [{"id": 1}]})

    def test_075_store_same_related_field_twice(self):
        """Test adding the same related field twice combines their data"""
        user = mail_new_test_user(self.env, login="test_user", name="Test User")
        store = Store().add(
            user,
            lambda res: (
                res.one("partner_id", ["name"]),
                res.one("partner_id", ["country_id"]),
            ),
        )
        self.assertEqual(
            store._build_result(),
            {
                "res.partner": [
                    {
                        "id": user.partner_id.id,
                        "name": "Test User",
                        "country_id": False,
                    },
                ],
                "res.users": [
                    {"id": user.id, "partner_id": user.partner_id.id},
                ],
            },
        )
    # 1xx Store specific tests (singleton in ids_by_model)

    def test_110_store_store_singleton(self):
        """Test Store dict is present in result as a singleton."""
        store = Store()
        store.add_global_values(test=True)
        self.assertEqual(store._build_result(), {"Store": {"test": True}})

    def test_111_store_store_dict_update(self):
        """Test Store dict update."""
        store = Store()
        store.add_global_values(test=True)
        store.add_global_values(test=False, abc=1)
        self.assertEqual(store._build_result(), {"Store": {"test": False, "abc": 1}})

    def test_140_store_store_invalid_bool(self):
        """Test Store adding invalid value."""
        store = Store()
        store.add_model_values("key1", True)
        with self.assertRaises(TypeError):
            store._build_result()

    def test_141_store_store_invalid_list(self):
        """Test adding invalid value."""
        store = Store()
        store.add_model_values("key1", [{"test": True}])
        with self.assertRaises(AssertionError):
            store._build_result()

    def test_160_store_store_data_empty_val(self):
        """Test Store empty values are not present in result."""
        store = Store()
        store.add_global_values()
        self.assertEqual(store._build_result(), {})

    def test_161_store_store_data_empty_not_empty(self):
        """Test Store mixing empty and non-empty values."""
        store = Store()
        store.add_global_values()
        store.add_model_values("key2", {"id": 1})
        self.assertEqual(store._build_result(), {"key2": [{"id": 1}]})

    # 2xx Thread specific tests (dual id in ids_by_model)

    def test_210_store_thread_dict(self):
        """Test Thread dict is present in result."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": True})
        self.assertEqual(
            store._build_result(), {"mail.thread": [{"id": 1, "model": "res.partner", "test": True}]}
        )

    def test_211_store_thread_dict_update_same_id(self):
        """Test Thread dict update same id."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": False, "abc": 1})
        self.assertEqual(
            store._build_result(),
            {"mail.thread": [{"id": 1, "model": "res.partner", "test": False, "abc": 1}]},
        )

    def test_212_store_thread_dict_update_multiple_ids(self):
        """Test Thread dict update multiple ids."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 2, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 2, "model": "res.partner", "test": False, "abc": 1})
        self.assertEqual(
            store._build_result(),
            {
                "mail.thread": [
                    {"id": 1, "model": "res.partner", "test": True},
                    {"id": 2, "model": "res.partner", "test": False, "abc": 1},
                ]
            },
        )

    def test_213_store_thread_dict_update_multiple_models(self):
        """Test Thread dict update multiple models."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 2, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 2, "model": "discuss.channel", "test": True, "abc": 1})
        store.add_model_values("mail.thread", {"id": 2, "model": "discuss.channel", "test": False, "abc": 2})
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": False})
        self.assertEqual(
            store._build_result(),
            {
                "mail.thread": [
                    {"id": 1, "model": "res.partner", "test": False},
                    {"id": 2, "model": "res.partner", "test": True},
                    {"id": 2, "model": "discuss.channel", "test": False, "abc": 2},
                ]
            },
        )

    def test_240_store_thread_invalid_bool(self):
        """Test Thread adding invalid bool value."""
        store = Store()
        store.add_model_values("mail.thread", True)
        with self.assertRaises(TypeError):
            store._build_result()

    def test_241_store_thread_invalid_list(self):
        """Test Thread adding invalid list value."""
        store = Store()
        store.add_model_values("mail.thread", [True])
        with self.assertRaises(AttributeError):
            store._build_result()

    def test_242_store_thread_invalid_missing_id(self):
        """Test Thread adding invalid missing id."""
        store = Store()
        store.add_model_values("mail.thread", {"model": "res.partner"})
        with self.assertRaises(AssertionError):
            store._build_result()

    def test_243_store_thread_invalid_missing_model(self):
        """Test Thread adding invalid list value."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1})
        with self.assertRaises(AssertionError):
            store._build_result()

    def test_260_store_thread_data_empty_val(self):
        """Test Thread empty values are not present in result."""
        store = Store()
        store.add_model_values("mail.thread", {})
        self.assertEqual(store._build_result(), {})

    def test_261_store_thread_data_empty_not_empty(self):
        """Test Thread mixing empty and non-empty values."""
        store = Store()
        store.add_model_values("key1", {})
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner"})
        self.assertEqual(store._build_result(), {"mail.thread": [{"id": 1, "model": "res.partner"}]})

    # 3xx Tests with real models

    def test_350_non_list_extra_fields_copy_when_following_relations(self):
        """Test that non-list extra fields are properly copied when following relations."""
        user = new_test_user(self.env, "test_user_350@example.com")
        store = Store().add(
            user,
            lambda res: res.one(
                "partner_id",
                lambda res: (
                    res.from_method("_store_partner_fields"),
                    res.attr("email"),
                ),
            ),
        )
        self.assertEqual(store._build_result()["res.partner"][0]["email"], "test_user_350@example.com")

    def test_355_single_extra_fields_copy_with_records(self):
        """Test that dynamic_fields apply individually to each record even when list extra fields are present."""
        user_a = new_test_user(self.env, "test_user_355_a@example.com")
        user_b = new_test_user(self.env, "test_user_355_b@example.com")

        def fields(user_res: Store.FieldList, user):
            if user == user_a:
                user_res.attr("email")

        store = Store().add(
            user_a + user_b,
            lambda res: res.one("partner_id", lambda res: res.attr("name"), dynamic_fields=fields),
        )
        data = store._build_result()
        self.assertEqual(data["res.partner"][0]["email"], "test_user_355_a@example.com")
        self.assertNotIn("email", data["res.partner"][1])

    def test_360_internal_fields(self):
        public_category = self.env["discuss.category"].create({"name": "Public Channels"})
        public_channel = self.env["discuss.channel"].create(
            {
                "name": "Public Channel",
                "description": "secret",
                "group_public_id": False,
                "discuss_category_id": public_category.id,
            },
        )
        odoobot_partner = self.env.ref("base.partner_root")
        odoobot_member = public_channel.channel_member_ids.filtered(
            lambda m: m.partner_id == odoobot_partner,
        )
        bob_user = new_test_user(self.env, "bob_user", name="Bob", email="bob@secret.com")
        bob_member = public_channel._add_members(users=bob_user)
        portal_user = new_test_user(self.env, login="portal_user", groups="base.group_portal")
        test_message = public_channel.message_post(body="Test Message")

        def _get_fields(res):
            res.attr("name")
            res.attr("description", internal=True)
            res.many(
                "channel_member_ids",
                lambda res: (
                    res.one(
                        "partner_id",
                        lambda res: (
                            res.attr("name"),
                            res.extend(["email", "phone"], internal=True),
                        ),
                    ),
                    res.attr("seen_message_id"),
                ),
            )
            res.many("message_ids", ["author_id"], internal=True)
            res.one(
                "discuss_category_id",
                lambda res: (
                    res.attr("id"),
                    res.from_method("_store_category_fields", internal=True),
                ),
            )

        non_internal_payload = {
            "discuss.category": [{"id": public_category.id}],
            "discuss.channel": [
                {
                    "channel_member_ids": public_channel.channel_member_ids.ids,
                    "discuss_category_id": public_category.id,
                    "id": public_channel.id,
                    "name": "Public Channel",
                },
            ],
            "discuss.channel.member": [
                {
                    "id": odoobot_member.id,
                    "partner_id": odoobot_partner.id,
                    "seen_message_id": test_message.id,
                },
                {
                    "id": bob_member.id,
                    "partner_id": bob_user.partner_id.id,
                    "seen_message_id": False,
                },
            ],
            "res.partner": [
                {"id": odoobot_partner.id, "name": "OdooBot"},
                {"id": bob_user.partner_id.id, "name": "Bob"},
            ],
        }
        internal_payload = {
            "discuss.channel": [
                {
                    "description": "secret",
                    "id": public_channel.id,
                    "message_ids": [test_message.id],
                },
            ],
            "discuss.category": [
                {
                    "bus_channel_access_token": public_category._get_bus_channel_access_token(),
                    "id": public_category.id,
                    "name": "Public Channels",
                    "sequence": public_category.sequence,
                },
            ],
            "mail.message": [{"id": test_message.id, "author_id": odoobot_partner.id}],
            "res.partner": [
                {"id": odoobot_partner.id, "email": "odoobot@example.com", "phone": False},
                {"id": bob_user.partner_id.id, "email": "bob@secret.com", "phone": False},
            ],
        }
        with self.assertBus([
            BusResult(public_channel, "mail.record/insert", non_internal_payload),
            BusResult((public_channel, "internal_users"), "mail.record/insert", internal_payload),
        ]):
            store = Store(bus_channel=public_channel)
            store.add(public_channel, _get_fields)
            store.bus_send()
        with self.assertBus([BusResult(portal_user, "mail.record/insert", non_internal_payload)]):
            store = Store(bus_channel=portal_user)
            store.add(public_channel, _get_fields)
            store.bus_send()

    def test_390_add_no_loop(self):
        """Test that store.add() does not loop indefinitely but it is still allowed to process
        consecutive calls."""
        user_a = new_test_user(self.env, "test_user_390@example.com")
        store = Store()
        store.add(user_a, "_store_im_status_fields")
        data = store._build_result()
        self.assertEqual(data["res.partner"][0]["im_status"], "offline")
        self.env["mail.presence"]._update_presence(user_a)
        store.add(user_a, "_store_im_status_fields")
        data2 = store._build_result()
        self.assertEqual(data2["res.partner"][0]["im_status"], "online")

    def test_391_add_no_loop_callable_identity_obj(self):
        def _store_partner_test_fields(res):
            res.attr("test", lambda p: p.id, predicate=lambda p: p.id)
            res.one("main_user_id", _store_user_test_fields)

        def _store_user_test_fields(res):
            res.attr("test", lambda u: u.id, predicate=lambda u: u.id)
            res.one("partner_id", _store_partner_test_fields)

        user = new_test_user(self.env, "test_user_391@example.com")
        data = Store().add(user, _store_user_test_fields)._build_result()
        self.assertEqual(data["res.partner"][0]["test"], user.partner_id.id)
        self.assertEqual(data["res.users"][0]["test"], user.id)

    def test_393_delayed_add(self):
        """Test that delayed store.add() postpones reading fields until _build_result()."""
        user_a = new_test_user(self.env, "test_user_390@example.com")
        store = Store()
        store.add(user_a, "_store_im_status_fields")
        self.assertEqual(user_a.partner_id.im_status, "offline")
        self.env["mail.presence"]._update_presence(user_a)
        data = store._build_result()
        self.assertEqual(data["res.partner"][0]["im_status"], "online")

    def test_395_delayed_add_ignores_deleted_record(self):
        """Test that delayed store.add() ignores deleted records."""
        user_a = new_test_user(self.env, "test_user_390@example.com")
        store = Store()
        store.add(user_a, ["name"])
        user_a.unlink()
        data = store._build_result()
        self.assertFalse(data)

    def test_397_delayed_delete_keeps_deleted_record(self):
        """Test that delayed store.delete() keeps deleted records."""
        user_a = new_test_user(self.env, "test_user_390@example.com")
        store = Store()
        user_a.unlink()
        store.add(user_a, ["name"])
        store.delete(user_a)
        data = store._build_result()
        self.assertEqual({"res.users": [{"id": user_a.id, "_DELETE": True}]}, data)

    # 4xx Tests many command modes

    def test_450_replace_clear_existing_data(self):
        general = self.env["discuss.channel"].create({"name": "General"})
        general.message_post(body="Message 1")
        general.message_post(body="Message 2")
        store = Store()
        store.add(
            general,
            lambda res: (
                res.many("messages", [], value=general.message_ids[0], mode="ADD"),
                res.many("messages", [], value=general.message_ids[1], mode="REPLACE"),
            ),
        )
        data = store._build_result()
        self.assertEqual(data["discuss.channel"][0]["messages"], general.message_ids[1].ids)

    def test_460_replace_wrapped_into_command_when_multiple_commands_are_added(self):
        general = self.env["discuss.channel"].create({"name": "General"})
        general.message_post(body="Message 1")
        general.message_post(body="Message 2")
        general.message_post(body="Message 3")
        store = Store()
        store.add(
            general,
            lambda res: res.many("messages", [], value=general.message_ids, mode="REPLACE"),
        )
        data = store._build_result()
        store = Store()
        self.assertEqual(data["discuss.channel"][0]["messages"], general.message_ids.ids)
        store.add(
            general,
            lambda res: (
                res.many("messages", [], value=general.message_ids, mode="REPLACE"),
                res.many("messages", [], value=general.message_ids[2], mode="DELETE"),
            ),
        )
        data = store._build_result()
        self.assertEqual(
            data["discuss.channel"][0]["messages"],
            [("REPLACE", general.message_ids.ids), ("DELETE", general.message_ids[2].ids)],
        )
