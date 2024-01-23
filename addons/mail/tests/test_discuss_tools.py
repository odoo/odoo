# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tools.discuss import StoreData
from odoo.tests import TransactionCase


class TestDiscussTools(TransactionCase):
    """Test class for discuss tools."""

    def test_10_store_dict(self):
        """Test dict is present in result."""
        store = StoreData()
        store.add({"Store": {"test": True}})
        self.assertEqual(store.get_result(), {"Store": {"test": True}})

    def test_11_store_dict_update(self):
        """Test dict update."""
        store = StoreData()
        store.add({"Store": {"test": True}})
        store.add({"Store": {"test": False, "abc": 1}})
        self.assertEqual(store.get_result(), {"Store": {"test": False, "abc": 1}})

    def test_20_store_list(self):
        """Test list is present in result."""
        store = StoreData()
        store.add({"Thread": [{"id": 1}, {"id": 2}]})
        self.assertEqual(store.get_result(), {"Thread": [{"id": 1}, {"id": 2}]})

    def test_21_store_list_append(self):
        """Test list append."""
        store = StoreData()
        store.add({"Thread": [{"id": 1}, {"id": 2}]})
        store.add({"Thread": [{"id": 4}, {"id": 5}]})
        self.assertEqual(
            store.get_result(), {"Thread": [{"id": 1}, {"id": 2}, {"id": 4}, {"id": 5}]}
        )

    def test_30_store_add_key(self):
        """Test adding several keys."""
        store = StoreData()
        store.add({"Store": {"test": True}})
        store.add({"Thread": [{"id": 4}, {"id": 5}]})
        self.assertEqual(
            store.get_result(), {"Store": {"test": True}, "Thread": [{"id": 4}, {"id": 5}]}
        )

    def test_40_store_invalid(self):
        """Test adding invalid value."""
        store = StoreData()
        with self.assertRaises(AssertionError):
            store.add({"Store": True})

    def test_50_store_dict_to_list(self):
        """Test adding dict to a list."""
        store = StoreData()
        store.add({"Thread": [{"id": 2}]})
        store.add({"Thread": {"id": 1}})
        self.assertEqual(store.get_result(), {"Thread": [{"id": 2}, {"id": 1}]})

    def test_51_store_list_to_dict(self):
        """Test adding list to a dict."""
        store = StoreData()
        store.add({"Thread": {"id": 1}})
        store.add({"Thread": [{"id": 2}]})
        self.assertEqual(store.get_result(), {"Thread": [{"id": 1}, {"id": 2}]})

    def test_60_store_data_empty_val(self):
        """Test empty values are not present in result."""
        store = StoreData()
        store.add({"Store": {}})
        self.assertEqual(store.get_result(), {})

    def test_61_store_data_empty_not_empty(self):
        """Test mixing empty and non-empty values."""
        store = StoreData()
        store.add({"Store": {}, "Thread": {"id": 1}})
        self.assertEqual(store.get_result(), {"Thread": {"id": 1}})
