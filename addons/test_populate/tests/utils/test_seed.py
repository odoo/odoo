from odoo.tests import TransactionCase

from odoo.addons.populate.utils.seed import MASK_INT32, derive_seed_from


class TestSeedDerivation(TransactionCase):

    def test_derive_from_deterministic(self):
        base_seed = 12345
        index = 42
        derived1 = derive_seed_from(base_seed, index)
        derived2 = derive_seed_from(base_seed, index)
        self.assertEqual(derived1, derived2)

    def test_derive_from_different_indices_unique(self):
        COUNT = 100
        base_seed = 12345
        derived_seeds = {derive_seed_from(base_seed, i) for i in range(COUNT)}
        self.assertEqual(len(derived_seeds), COUNT, "All seeds should be unique")

    def test_derive_from_within_int32_range(self):
        base_seed = 12345
        for i in range(1, 50):
            derived = base_seed = derive_seed_from(base_seed, i)
            self.assertGreaterEqual(derived, 0)
            self.assertLessEqual(derived, MASK_INT32)

    def test_derive_from_different_base_seeds(self):
        index = 1
        seed1 = derive_seed_from(12345, index)
        seed2 = derive_seed_from(67890, index)
        self.assertNotEqual(seed1, seed2)
