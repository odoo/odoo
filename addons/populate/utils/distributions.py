from __future__ import annotations

import inspect
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from random import Random
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any

type DistributionFactory = Callable[[Random], Distribution]
type DistributionKwargs = Mapping[str, float]

MAX_REJECTION_SAMPLES = 100


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a value to be within [min_value, max_value]."""
    return max(min_value, min(value, max_value))


class Distribution(ABC):
    """Base class for statistical distributions."""

    name: ClassVar[str]
    _registry: ClassVar[dict[str, type[Distribution]]] = {}

    def __init_subclass__(cls, *args, **kwargs):
        super().__init_subclass__(*args, **kwargs)
        if not inspect.isabstract(cls):
            if cls.name is None:
                raise TypeError(
                    f"Concrete Distribution subclass '{cls.__qualname__}' "
                    f"must define a 'name' class attribute.",
                )

            Distribution._registry[cls.name] = cls

    def __init__(self, random: Random | None = None, **kwargs):
        if random is None:
            random = Random()

        self.random = random

    def __eq__(self, other):
        if not isinstance(self, type(other)):
            return False

        return all(getattr(self, attr) == getattr(other, attr) for attr in vars(self) if attr != 'random')

    def __hash__(self):
        return hash(tuple(sorted((k, v) for k, v in vars(self).items() if k != 'random')))

    def __repr__(self):
        params = ', '.join(f"{k}={v!r}" for k, v in sorted(vars(self).items()) if k != 'random')
        if params:
            return f"<{self.__class__.__name__!r}({params!r})>"
        return f"<{self.__class__.__name__!r}>"

    @staticmethod
    def _parse(distribution_def: str) -> tuple[str, DistributionKwargs]:
        """
        Parse distribution string like "normal(mean=50.0, std=10.0)"

        :param distribution_def: Blueprint distribution definition.
        :return: Distribution name and parsed float kwargs.

        Example:
            >>> Distribution._parse("normal(mean=50, std=10)")
            ('normal', {'mean': 50.0, 'std': 10.0})
        """
        pattern = r'^(\w+)\((.*)\)$'
        match = re.match(pattern, distribution_def.strip())

        if not match:
            raise ValueError(
                f"Invalid distribution format: '{distribution_def}'. "
                f"Expected format: 'name(param1=value1, param2=value2)', e.g. 'normal(mean=50, std=10)'.",
            )

        dist_name = match.group(1)
        params_str = match.group(2)

        params = {}
        if params_str.strip():
            for param in params_str.split(','):
                key, value = param.split('=')
                key = key.strip()
                value = value.strip()
                params[key] = float(value)

        return dist_name, params

    @classmethod
    def from_definition(cls, distribution_def, partial=False) -> Distribution | DistributionFactory:
        """Create a distribution, or a random-bound factory, from a blueprint string.

        :param distribution_def: Definition such as ``"normal(mean=50, std=10)"``.
        :param partial: When true, return a factory expecting the job's random source.
        :return: Distribution instance or factory.
        """
        name, params = Distribution._parse(distribution_def)
        distribution_class = cls.by_name(name)
        if partial:
            def distribution_factory(random: Random | None = None) -> Distribution:
                return distribution_class(random=random, **params)

            return distribution_factory

        return distribution_class(**params)

    @classmethod
    def by_name(cls, name: str) -> type[Distribution]:
        """Return the distribution class registered under ``name``.

        :param name: Distribution name from a blueprint definition.
        :return: Matching distribution class.
        """
        return cls._registry[name]

    @abstractmethod
    def sample(self) -> float:
        """Get a single sample from the distribution."""
        ...

    @staticmethod
    def _validate_sample_params(start, end):
        if start >= end:
            raise ValueError(f"Requires start < end, got start={start}, end={end} instead.")

    def _try_sample_bounded(self, start: float, end: float) -> float | None:
        """
        Try to sample a value in the continuous range [start, end] via rejection sampling.
        Returns None if no sample was found within bounds.
        """
        for _ in range(MAX_REJECTION_SAMPLES):
            candidate = self.sample()
            if start <= candidate <= end:
                return candidate

        return None

    def sample_discrete(self, start: int, end: int) -> int:
        """
        Sample an integer between [start, end].

        :param start: Start of the range (inclusive)
        :param end: End of the range (inclusive)
        :return: An integer in [start, end]
        """
        self._validate_sample_params(start, end)

        # Sample from [start, end+1) and floor, so every integer in [start, end]
        # gets equal probability (round() would halve the probability of endpoints).
        unbiased_end = end + (1 - 10e-9)

        sample = self._try_sample_bounded(start, unbiased_end)

        if sample is None:
            # Fallback: clamp if the user asked for bounds
            # completely outside the native distribution range
            sample = clamp(self.sample(), start, unbiased_end)

        return math.floor(sample)

    def sample_continuous(self, start: float, end: float) -> float:
        """
        Sample a value in the continuous range [start, end].

        :param start: Start of the range (inclusive)
        :param end: End of the range (inclusive)
        :return: A value in [start, end]
        """
        self._validate_sample_params(start, end)

        sample = self._try_sample_bounded(start, end)

        if sample is None:
            # Fallback: clamp if the user asked for bounds
            # completely outside the native distribution range
            sample = clamp(self.sample(), start, end)

        return sample

    def choice[T](self, seq: Sequence[T]) -> T:
        """Pick one element from a sequence."""
        if not seq:
            msg = "Cannot choose from an empty sequence"
            raise IndexError(msg)

        if len(seq) == 1:
            return seq[0]

        idx = self.sample_discrete(0, len(seq) - 1)
        assert 0 <= idx <= len(seq) - 1
        return seq[idx]

    def choices[T](self, seq: Sequence[T], *, k: int = 1) -> list[T]:
        """Pick k elements (with replacement) from a sequence."""
        if not seq:
            msg = "Cannot choose from an empty sequence"
            raise IndexError(msg)

        return [self.choice(seq) for _ in range(k)]

    def pick[T](self, seq: Sequence[T], k: int) -> list[T]:
        """Pick k elements (without replacement) from a sequence."""
        if not seq:
            msg = "Cannot choose from an empty sequence"
            raise IndexError(msg)

        if k > len(seq):
            msg = "Sample larger than population"
            raise ValueError(msg)

        indexes = []
        available = list(range(len(seq)))
        for _ in range(k):
            pos = self.sample_discrete(0, len(available) - 1) if len(available) > 1 else 0
            indexes.append(available.pop(pos))

        return [seq[i] for i in indexes]


class WeightedDistribution(Distribution):
    """A discrete distribution that samples from a fixed set of values with given weights."""

    name = 'weighted'

    def __init__(self, weighted_values: Mapping[Any, float], **kwargs):
        """Initialize weighted sampling over explicit values.

        :param weighted_values: Values mapped to their relative sampling weights.
        """
        super().__init__(**kwargs)
        values, weights = weighted_values.keys(), weighted_values.values()

        if any(w < 0 for w in weights):
            msg = "Weights must be non-negative."
            raise ValueError(msg)

        self.values = list(values)
        self.weights = list(weights)

    def sample(self) -> float:
        return self.random.choices(self.values, weights=self.weights)[0]

    def sample_discrete(self, start: int, end: int):
        msg = (
            "WeightedDistribution is a discrete distribution and does not support rejection sampling. "
            "Use sample() instead."
        )
        raise TypeError(msg)

    def sample_continuous(self, start: float, end: float):
        msg = (
            "WeightedDistribution is a discrete distribution and does not support rejection sampling. "
            "Use sample() instead."
        )
        raise TypeError(msg)

    def choice[T](self, seq: Sequence[T]) -> T:
        # ignore the arg, used baked-in values
        return self.random.choices(self.values, weights=self.weights)[0]

    def choices[T](self, seq: Sequence[T], *, k: int = 1) -> list[T]:
        # ignore the arg, used baked-in values
        return self.random.choices(self.values, weights=self.weights, k=k)


class NormalDistribution(Distribution):
    """
    Normal (Gaussian) distribution.

    The classic bell curve. Values cluster around the mean, with fewer values further away.

    When to use:
    - Modeling natural variations (heights, measurement errors, response times)
    - When you expect most values near the average with symmetrical spread
    - Real-world phenomena that result from many small random factors

    Example: User response times, server latency with consistent behavior
    """

    name = 'normal'

    def __init__(self, mean: float, std: float, **kwargs):
        """
        :param mean: Mean of the distribution
        :param std: Standard deviation (must be > 0)
        """
        super().__init__(**kwargs)
        if std <= 0:
            raise ValueError(f"Standard deviation must be positive, get {std} instead.", std)

        self.mean = mean
        self.std = std

    def sample(self):
        return self.random.gauss(self.mean, self.std)


class UniformDistribution(Distribution):
    """
    Uniform distribution.
    Every value in the range has an equal probability. Completely flat distribution.
    If no or just one bound is provided, the distribution is unbounded on both sides.
    When to use:
    - Random selection where all options are equally likely
    - When you have no reason to prefer any value over another in a range
    Example: Random color picker, dice rolls, shuffling items, selecting random test data
    """

    name = 'uniform'

    def __init__(self, min: float | None = None, max: float | None = None, **kwargs):
        """
        :param min: Minimum value
        :param max: Maximum value (must be > min)
        """
        super().__init__(**kwargs)
        if min is not None and max is not None and min >= max:
            raise ValueError(
                f"`min` must be less than `max`, "
                f"got min={min}, max={max} instead.",
            )

        self.min = min
        self.max = max

    @property
    def is_bounded(self):
        return self.min is not None and self.max is not None

    def sample(self):
        return self.random.uniform(self.min, self.max) if self.is_bounded else self.random.random()

    def sample_discrete(self, start: int, end: int):
        self._validate_sample_params(start, end)
        if self.is_bounded:
            # Perf: skip rejection sampling by
            # sampling directly from the overlapping range.
            # This yields the same result for a uniform distribution.
            low = max(start, self.min)
            high = min(end, self.max)
            return self.random.randint(low, high)

        return self.random.randint(start, end)

    def sample_continuous(self, start: float, end: float):
        self._validate_sample_params(start, end)
        if self.is_bounded:
            # Perf: skip rejection sampling by
            # sampling directly from the overlapping range.
            # This yields the same result for a uniform distribution.
            low = max(start, self.min)
            high = min(end, self.max)
            return self.random.uniform(low, high)

        return self.random.uniform(start, end)


class ExponentialDistribution(Distribution):
    """
    Exponential distribution.

    Models time between events. Many small values, few large ones. Heavily skewed right.

    When to use:
    - Time until something happens (waiting times, failures)
    - Intervals between independent events

    Example: Time between customer arrivals, time until the next system failure, session durations
    """

    name = 'exponential'

    def __init__(self, rate: float, **kwargs):
        """
        :param rate: Rate parameter λ (must be > 0)
        """
        super().__init__(**kwargs)
        if rate <= 0:
            raise ValueError(f"Rate must be positive, got {rate} instead.")

        self.rate = rate

    def sample(self):
        return self.random.expovariate(self.rate)


class BetaDistribution(Distribution):
    """
    Beta distribution.

    Bounded between 0 and 1. Shape varies dramatically based on parameters - can be U-shaped, bell-shaped, or skewed.

    When to use:
    - Modeling percentages, probabilities, or proportions
    - When values must stay within [0, 1] range
    - A/B testing and conversion rates

    Example: Click-through rates, success probabilities, confidence scores
    """

    name = 'beta'

    def __init__(self, alpha: float, beta: float, **kwargs):
        """
        :param alpha: Shape parameter α (must be > 0)
        :param beta: Shape parameter β (must be > 0)
        """  # noqa: RUF002
        super().__init__(**kwargs)
        if alpha <= 0:
            raise ValueError(f"Alpha must be positive, got {alpha} instead.")
        if beta <= 0:
            raise ValueError(f"Beta must be positive, got {beta} instead.")

        self.alpha = alpha
        self.beta = beta

    def sample(self):
        # Note: Beta is natively normalized within [0, 1]
        return self.random.betavariate(self.alpha, self.beta)

    # Overrides to stretch the Beta shape across the requested bounds,
    # since that's what often is expected for this distribution (used as a "shape" source).

    def sample_discrete(self, start: int, end: int):
        self._validate_sample_params(start, end)
        span = end - start + 1
        return start + min(math.floor(self.sample() * span), span - 1)

    def sample_continuous(self, start: float, end: float) -> float:
        self._validate_sample_params(start, end)
        return start + (self.sample() * (end - start))


class PoissonDistribution(Distribution):
    """
    Poisson distribution (discrete).

    Counts how many events occur in a fixed interval. Discrete (whole numbers only).

    When to use:
    - Counting rare events in a fixed time/space
    - Events that occur independently at a constant average rate

    Example: Number of bugs per 1000 lines of code, API requests per minute, emails received per hour
    """

    name = 'poisson'

    def __init__(self, lam: float, **kwargs):
        """
        :param lam: Average rate λ (must be > 0)
        """
        super().__init__(**kwargs)
        if lam <= 0:
            raise ValueError(f"Lambda must be positive, got {lam} instead.")

        self.lam = lam

    def sample(self):
        # Knuth's algorithm for Poisson sampling
        L = math.e ** (-self.lam)  # e^(-lambda)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= self.random.random()
        return k - 1

    def sample_continuous(self, start: float, end: float):
        msg = (
            "PoissonDistribution is a discrete distribution and does not support continuous sampling. "
            "Use sample_discrete() instead."
        )
        raise TypeError(msg)


class TriangularDistribution(Distribution):
    """
    Triangular distribution.

    Simple distribution with a min, max, and most likely value (mode). Linear increase to the peak, then linear decrease.

    When to use:
    - When you only know min/max/most-likely values (common in project estimation)
    - Quick approximations without detailed data

    Example: Task duration estimates, risk modeling, cost estimates when you have "best case, worst case, most likely"
    """

    name = 'triangular'

    def __init__(self, min: float, max: float, mode: float, **kwargs):
        """
        :param min: Minimum value
        :param max: Maximum value
        :param mode: Most likely value (peak of distribution)
        """
        super().__init__(**kwargs)
        if not (min <= mode <= max):
            raise ValueError(
                f"`mode` must be between `min` and `max`, "
                f"got min={min}, max={max}, mode={mode} instead.",
            )

        self.min = min
        self.max = max
        self.mode = mode

    def sample(self):
        return self.random.triangular(self.min, self.max, self.mode)
