import unittest

from odoo.tools.config import configmanager


class TestConfigGeneration(unittest.TestCase):
    def setUp(self):
        self.config = configmanager()

    def _moves(self, action):
        before = self.config.generation
        action()
        self.assertGreater(self.config.generation, before)

    def test_every_write_path_moves_the_generation(self):
        config = self.config
        self._moves(lambda: config.__setitem__("db_name", "x"))
        self._moves(lambda: config.pop("db_name"))
        self._moves(lambda: config.options.__setitem__("db_name", "y"))
        self._moves(lambda: config.options.pop("db_name"))
        self._moves(lambda: config._runtime_options.update(db_maxconn=3))
        self._moves(config._file_options.clear)
        self._moves(lambda: config._env_options.setdefault("k", 1))

    def test_patch_moves_it_on_entry_and_exit(self):
        config = self.config
        before = config.generation
        with config.patch(db_name="z"):
            entered = config.generation
            self.assertGreater(entered, before)
        self.assertGreater(config.generation, entered)

    def test_a_read_does_not_move_it(self):
        config = self.config
        before = config.generation
        config.get("db_name")
        config.options.get("db_name")
        _ = "db_name" in config.options
        self.assertEqual(config.generation, before)

    def test_a_swapped_options_mapping_is_never_memoisable(self):
        from unittest.mock import patch

        config = self.config
        stable = config.generation
        self.assertEqual(config.generation, stable)
        with patch.object(config, "options", {**config.options, "x_sendfile": True}):
            self.assertNotEqual(config.generation, config.generation)
        restored = config.generation
        self.assertGreater(restored, stable)
        self.assertEqual(config.generation, restored)

    def test_a_deep_copied_layer_is_a_plain_dict_and_moves_nothing(self):
        import copy

        config = self.config
        config["db_name"] = "x"
        before = config.generation
        layer = copy.deepcopy(config._override_options)
        self.assertIs(type(layer), dict)
        self.assertEqual(layer, {"db_name": ["x"]})
        self.assertEqual(config.generation, before)
        layer["db_name"] = "y"
        self.assertEqual(config["db_name"], ["x"])

    def test_a_deep_copied_manager_works_and_never_memoises(self):
        import copy

        config = self.config
        config["db_name"] = "x"
        clone = copy.deepcopy(config)
        self.assertEqual(clone["db_name"], ["x"])
        clone["db_name"] = "y"
        self.assertEqual(config["db_name"], ["x"])
        self.assertNotEqual(clone.generation, clone.generation)
