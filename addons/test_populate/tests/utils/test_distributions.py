from random import Random

from odoo.tests import TransactionCase

from odoo.addons.populate.utils.distributions import (
    BetaDistribution,
    Distribution,
    ExponentialDistribution,
    NormalDistribution,
    PoissonDistribution,
    TriangularDistribution,
    UniformDistribution,
    WeightedDistribution,
)


class TestDistributionParsing(TransactionCase):

    def test_parse_normal_distribution(self):
        name, params = Distribution._parse("normal(mean=50.0, std=10.0)")
        self.assertEqual(name, 'normal')
        self.assertEqual(params, {'mean': 50.0, 'std': 10.0})

    def test_parse_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            Distribution._parse("invalid_format")

    def test_from_definition(self):
        cases = [
            ("normal(mean=50, std=10)", NormalDistribution),
            ("uniform(min=0, max=1)", UniformDistribution),
            ("exponential(rate=1)", ExponentialDistribution),
            ("beta(alpha=2, beta=2)", BetaDistribution),
            ("poisson(lam=3)", PoissonDistribution),
            ("triangular(min=0, max=10, mode=5)", TriangularDistribution),
        ]
        for definition, expected_class in cases:
            with self.subTest(definition=definition):
                self.assertIsInstance(Distribution.from_definition(definition), expected_class)

    def test_by_name(self):
        self.assertIs(Distribution.by_name('normal'), NormalDistribution)

    def test_from_definition_partial(self):
        random = Random(42)
        factory = Distribution.from_definition("normal(mean=50, std=10)", partial=True)
        dist = factory(random=random)
        self.assertIsInstance(dist, NormalDistribution)
        self.assertIs(dist.random, random)


class TestDistributionBaseMethods(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Normal doesn't have overrides -> good base example.
        cls.dist = NormalDistribution(mean=0, std=10.0, random=Random(0))

    def test_equality_and_hash(self):
        d1 = NormalDistribution(mean=50.0, std=10.0)
        d2 = NormalDistribution(mean=50.0, std=10.0)
        d3 = NormalDistribution(mean=40.0, std=10.0)
        self.assertEqual(d1, d2)
        self.assertEqual(hash(d1), hash(d2))
        self.assertNotEqual(d1, d3)

    def test_sample_discrete_range(self):
        samples = [self.dist.sample_discrete(1, 10) for _ in range(50)]
        self.assertTrue(all(isinstance(s, int) for s in samples))
        self.assertTrue(all(1 <= s <= 10 for s in samples))

    def test_sample_discrete_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            self.dist.sample_discrete(10, 10)

    def test_sample_continuous_range(self):
        samples = [self.dist.sample_continuous(0.0, 100.0) for _ in range(50)]
        self.assertTrue(all(0.0 <= s <= 100.0 for s in samples))

    def test_sample_continuous_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            self.dist.sample_continuous(10.0, 10.0)

    def test_choice(self):
        seq = ['a', 'b', 'c', 'd', 'e']
        self.assertIn(self.dist.choice(seq), seq)

    def test_choice_single_element(self):
        self.assertEqual(self.dist.choice(['only']), 'only')

    def test_choice_empty_raises(self):
        with self.assertRaises(IndexError):
            self.dist.choice([])

    def test_choices(self):
        seq = ['a', 'b', 'c']
        results = self.dist.choices(seq, k=10)
        self.assertEqual(len(results), 10)
        self.assertTrue(all(r in seq for r in results))

    def test_pick_no_duplicates(self):
        result = self.dist.pick([1, 2, 3, 4, 5], k=3)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(set(result)), 3)

    def test_pick_exceeds_population_raises(self):
        with self.assertRaises(ValueError):
            self.dist.pick([1, 2], k=5)

    def test_pick_empty_raises(self):
        with self.assertRaises(IndexError):
            self.dist.pick([], k=1)


class TestNormalDistribution(TransactionCase):

    def test_sample(self):
        dist = NormalDistribution(mean=50.0, std=10.0)
        self.assertIsInstance(dist.sample(), float)

    def test_invalid_std_raises(self):
        with self.assertRaises(ValueError):
            NormalDistribution(mean=50.0, std=0.0)


class TestUniformDistribution(TransactionCase):

    def test_sample_bounded(self):
        dist = UniformDistribution(min=0, max=1)
        sample = dist.sample()
        self.assertIsInstance(sample, float)
        self.assertTrue(0.0 <= sample <= 1.0)

    def test_sample_unbounded_returns_float_in_unit_interval(self):
        dist = UniformDistribution()
        samples = [dist.sample() for _ in range(50)]
        self.assertTrue(all(isinstance(s, float) for s in samples))
        self.assertTrue(all(0.0 <= s <= 1.0 for s in samples))

    def test_sample_discrete_unbounded(self):
        dist = UniformDistribution(random=Random(0))
        samples = [dist.sample_discrete(1, 6) for _ in range(100)]
        self.assertTrue(all(isinstance(s, int) for s in samples))
        self.assertTrue(all(1 <= s <= 6 for s in samples))
        # All values should appear with roughly equal probability
        self.assertEqual(len(set(samples)), 6)

    def test_sample_continuous_unbounded(self):
        dist = UniformDistribution(random=Random(0))
        samples = [dist.sample_continuous(10.0, 20.0) for _ in range(50)]
        self.assertTrue(all(10.0 <= s <= 20.0 for s in samples))

    def test_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            UniformDistribution(min=5, max=5)

    def test_partially_bounded_is_allowed(self):
        # Only one bound set should not raise
        dist = UniformDistribution(min=0)
        self.assertIsNotNone(dist)


class TestExponentialDistribution(TransactionCase):

    def test_sample(self):
        dist = ExponentialDistribution(rate=1.0)
        self.assertGreaterEqual(dist.sample(), 0.0)

    def test_invalid_rate_raises(self):
        with self.assertRaises(ValueError):
            ExponentialDistribution(rate=0.0)


class TestBetaDistribution(TransactionCase):

    def test_sample_in_unit_interval(self):
        dist = BetaDistribution(alpha=2.0, beta=5.0)
        samples = [dist.sample() for _ in range(50)]
        self.assertTrue(all(0.0 <= s <= 1.0 for s in samples))

    def test_sample_discrete_stretches_to_range(self):
        dist = BetaDistribution(alpha=2.0, beta=5.0, random=Random(0))
        samples = [dist.sample_discrete(0, 9) for _ in range(100)]
        self.assertTrue(all(isinstance(s, int) for s in samples))
        self.assertTrue(all(0 <= s <= 9 for s in samples))

    def test_sample_continuous_stretches_to_range(self):
        dist = BetaDistribution(alpha=2.0, beta=5.0, random=Random(0))
        samples = [dist.sample_continuous(0.0, 100.0) for _ in range(50)]
        self.assertTrue(all(0.0 <= s <= 100.0 for s in samples))

    def test_invalid_params_raise(self):
        with self.assertRaises(ValueError):
            BetaDistribution(alpha=0.0, beta=1.0)
        with self.assertRaises(ValueError):
            BetaDistribution(alpha=1.0, beta=0.0)


class TestTriangularDistribution(TransactionCase):

    def test_sample_in_range(self):
        dist = TriangularDistribution(min=0.0, max=10.0, mode=5.0)
        samples = [dist.sample() for _ in range(50)]
        self.assertTrue(all(0.0 <= s <= 10.0 for s in samples))

    def test_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            TriangularDistribution(min=0.0, max=10.0, mode=11.0)


class TestPoissonDistribution(TransactionCase):

    def test_sample_is_non_negative_integer(self):
        dist = PoissonDistribution(lam=5.0)
        samples = [dist.sample() for _ in range(50)]
        self.assertTrue(all(isinstance(s, int) and s >= 0 for s in samples))

    def test_sample_discrete_in_range(self):
        dist = PoissonDistribution(lam=5.0, random=Random(0))
        samples = [dist.sample_discrete(0, 20) for _ in range(50)]
        self.assertTrue(all(isinstance(s, int) for s in samples))
        self.assertTrue(all(0 <= s <= 20 for s in samples))

    def test_sample_continuous_raises(self):
        dist = PoissonDistribution(lam=5.0)
        with self.assertRaises(TypeError):
            dist.sample_continuous(0.0, 10.0)

    def test_invalid_lambda_raises(self):
        with self.assertRaises(ValueError):
            PoissonDistribution(lam=0.0)


class TestWeightedDistribution(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.weighted_values = {'a': 1.0, 'b': 2.0, 'c': 7.0}
        cls.dist = WeightedDistribution(weighted_values=cls.weighted_values, random=Random(0))

    def test_sample_returns_a_known_value(self):
        for _ in range(50):
            self.assertIn(self.dist.sample(), self.weighted_values)

    def test_choice_ignores_seq_and_uses_weighted_values(self):
        # choice() ignores its argument and draws from the baked-in weighted values
        result = self.dist.choice(['x', 'y', 'z'])
        self.assertIn(result, self.weighted_values)

    def test_choices_returns_correct_count(self):
        results = self.dist.choices(['x'], k=20)
        self.assertEqual(len(results), 20)
        self.assertTrue(all(r in self.weighted_values for r in results))

    def test_weight_bias(self):
        # 'c' has weight 7 out of 10 — should appear ~70% of the time
        dist = WeightedDistribution(weighted_values={'a': 1.0, 'b': 2.0, 'c': 7.0}, random=Random(42))
        samples = [dist.sample() for _ in range(1000)]
        c_ratio = samples.count('c') / len(samples)
        self.assertGreater(c_ratio, 0.55)  # well above noise floor

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            WeightedDistribution(weighted_values={'a': 1.0, 'b': -0.5})

    def test_sample_discrete_raises(self):
        with self.assertRaises(TypeError):
            self.dist.sample_discrete(0.0, 1.0)

    def test_sample_continuous_raises(self):
        with self.assertRaises(TypeError):
            self.dist.sample_continuous(0.0, 1.0)
