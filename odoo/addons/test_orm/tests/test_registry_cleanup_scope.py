from odoo.tests import common


class TestRegistryCleanupScopeUntouched(common.TransactionCase):
    def test_a_class_that_changes_nothing_starts_clean(self):
        # the loader may hold the flag while at_install suites run; the class
        # is judged by its own changes, so it starts with none
        self.assertFalse(self.registry.registry_invalidated)
        self.assertEqual(self.registry.invalidated_model_names, set())
        self.assertEqual(self._registry_guard.models_touched, set())


class TestRegistryCleanupScopeNamed(common.TransactionCase):
    def test_a_named_setup_is_what_the_cleanup_rebuilds(self):
        self.registry.setup_models(self.env.cr, ["res.partner.title"])
        self.assertTrue(self.registry.registry_invalidated)
        self.assertEqual(self.registry.invalidated_model_names, {"res.partner.title"})


class TestRegistryCleanupScopeByHand(common.TransactionCase):
    def test_a_flag_flipped_by_hand_widens_to_the_whole_registry(self):
        self.registry.setup_models(self.env.cr, ["res.partner.title"])
        self.registry.registry_invalidated = True
        self.assertIsNone(self.registry.invalidated_model_names)
