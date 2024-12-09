# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tools.discuss import Store
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestDiscussTools(TransactionCase):
    """Test class for discuss tools."""

    # 0xx generic tests (key not in ids_by_model)

    def test_010_store_dict(self):
        """Test dict is present in result."""
        store = Store()
        store.add_model_values("key1", {"id": 1, "test": True})
        self.assertEqual(store.get_result(), {"key1": [{"id": 1, "test": True}]})

    def test_011_store_dict_update_same_id(self):
        """Test dict update same id."""
        store = Store()
        store.add_model_values("key1", {"id": 1, "test": True})
        store.add_model_values("key1", {"id": 1, "test": False, "abc": 1})
        self.assertEqual(store.get_result(), {"key1": [{"id": 1, "test": False, "abc": 1}]})

    def test_012_store_dict_update_multiple_ids(self):
        """Test dict update multiple ids."""
        store = Store()
        store.add_model_values("key1", {"id": 1, "test": True})
        store.add_model_values("key1", {"id": 2, "test": True})
        store.add_model_values("key1", {"id": 2, "test": False, "abc": 1})
        self.assertEqual(
            store.get_result(),
            {"key1": [{"id": 1, "test": True}, {"id": 2, "test": False, "abc": 1}]},
        )

    def test_040_store_invalid(self):
        """Test adding invalid value."""
        store = Store()
        with self.assertRaises(AttributeError):
            store.add_model_values("key1", True)

    def test_042_store_invalid_missing_id(self):
        """Test Thread adding invalid list value."""
        store = Store()
        with self.assertRaises(AssertionError):
            store.add_model_values("key1", {"test": True})

    def test_060_store_data_empty_val(self):
        """Test empty values are not present in result."""
        store = Store()
        store.add_model_values("key1", {})
        self.assertEqual(store.get_result(), {})

    def test_061_store_data_empty_not_empty(self):
        """Test mixing empty and non-empty values."""
        store = Store()
        store.add_model_values("key1", {})
        store.add_model_values("key2", {"id": 1})
        self.assertEqual(store.get_result(), {"key2": [{"id": 1}]})

    # 1xx Store specific tests (singleton in ids_by_model)

    def test_110_store_store_singleton(self):
        """Test Store dict is present in result as a singleton."""
        store = Store()
        store.add_global_values(test=True)
        self.assertEqual(store.get_result(), {"Store": {"test": True}})

    def test_111_store_store_dict_update(self):
        """Test Store dict update."""
        store = Store()
        store.add_global_values(test=True)
        store.add_global_values(test=False, abc=1)
        self.assertEqual(store.get_result(), {"Store": {"test": False, "abc": 1}})

    def test_140_store_store_invalid_bool(self):
        """Test Store adding invalid value."""
        store = Store()
        with self.assertRaises(AttributeError):
            store.add_model_values("key1", True)

    def test_141_store_store_invalid_list(self):
        """Test adding invalid value."""
        store = Store()
        with self.assertRaises(AttributeError):
            store.add_model_values("key1", [{"test": True}])

    def test_160_store_store_data_empty_val(self):
        """Test Store empty values are not present in result."""
        store = Store()
        store.add_global_values()
        self.assertEqual(store.get_result(), {})

    def test_161_store_store_data_empty_not_empty(self):
        """Test Store mixing empty and non-empty values."""
        store = Store()
        store.add_global_values()
        store.add_model_values("key2", {"id": 1})
        self.assertEqual(store.get_result(), {"key2": [{"id": 1}]})

    # 2xx Thread specific tests (dual id in ids_by_model)

    def test_210_store_thread_dict(self):
        """Test Thread dict is present in result."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": True})
        self.assertEqual(
            store.get_result(), {"mail.thread": [{"id": 1, "model": "res.partner", "test": True}]}
        )

    def test_211_store_thread_dict_update_same_id(self):
        """Test Thread dict update same id."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": False, "abc": 1})
        self.assertEqual(
            store.get_result(),
            {"mail.thread": [{"id": 1, "model": "res.partner", "test": False, "abc": 1}]},
        )

    def test_212_store_thread_dict_update_multiple_ids(self):
        """Test Thread dict update multiple ids."""
        store = Store()
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 2, "model": "res.partner", "test": True})
        store.add_model_values("mail.thread", {"id": 2, "model": "res.partner", "test": False, "abc": 1})
        self.assertEqual(
            store.get_result(),
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
            store.get_result(),
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
        with self.assertRaises(AttributeError):
            store.add_model_values("mail.thread", True)

    def test_241_store_thread_invalid_list(self):
        """Test Thread adding invalid list value."""
        store = Store()
        with self.assertRaises(AttributeError):
            store.add_model_values("mail.thread", [True])

    def test_242_store_thread_invalid_missing_id(self):
        """Test Thread adding invalid missing id."""
        store = Store()
        with self.assertRaises(AssertionError):
            store.add_model_values("mail.thread", {"model": "res.partner"})

    def test_243_store_thread_invalid_missing_model(self):
        """Test Thread adding invalid list value."""
        store = Store()
        with self.assertRaises(AssertionError):
            store.add_model_values("mail.thread", {"id": 1})

    def test_260_store_thread_data_empty_val(self):
        """Test Thread empty values are not present in result."""
        store = Store()
        store.add_model_values("mail.thread", {})
        self.assertEqual(store.get_result(), {})

    def test_261_store_thread_data_empty_not_empty(self):
        """Test Thread mixing empty and non-empty values."""
        store = Store()
        store.add_model_values("key1", {})
        store.add_model_values("mail.thread", {"id": 1, "model": "res.partner"})
        self.assertEqual(store.get_result(), {"mail.thread": [{"id": 1, "model": "res.partner"}]})
