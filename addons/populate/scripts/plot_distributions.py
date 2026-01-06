#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "matplotlib",
#   "numpy",
# ]
# ///
"""
Visualize all distributions from populate/utils/distributions.py.

Mainly to visually validate the correctness of the implementation.
"""
if __name__ != '__main__':
    raise ImportError(
        f"'{__file__}' is a standalone script and must not be imported as a module.",
    )

import importlib.util
import math
import sys
from pathlib import Path
from random import Random

_distributions_path = Path(__file__).resolve().parents[1] / 'utils' / 'distributions.py'
_spec = importlib.util.spec_from_file_location('distributions', _distributions_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BetaDistribution = _mod.BetaDistribution
ExponentialDistribution = _mod.ExponentialDistribution
NormalDistribution = _mod.NormalDistribution
PoissonDistribution = _mod.PoissonDistribution
TriangularDistribution = _mod.TriangularDistribution
UniformDistribution = _mod.UniformDistribution

try:
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    gridspec = plt = np = None
    sys.exit("matplotlib and numpy are required: pip install matplotlib numpy")

N_SAMPLES = 10_000
RANDOM_SEED = 42
RANDOM = Random(RANDOM_SEED)

CONTINUOUS_RANGE = (0.0, 100.0)
DISCRETE_RANGE = (0, 100)

PLOT_COLORS = {
    'raw': '#4C72B0',
    'continuous': '#2CA02C',
    'discrete': '#D62728',
}
THEORETICAL_COLOR = 'r'

DISTRIBUTIONS = [
    {
        'label': "Normal\n(mean=50, std=40)",
        'dist': NormalDistribution(mean=50, std=40, random=RANDOM),
        'discrete': False,
    },
    {
        'label': "Uniform\n(min=10, max=90)",
        'dist': UniformDistribution(min=10, max=90, random=RANDOM),
        'discrete': False,
    },
    {
        'label': "Exponential\n(rate=0.04)",
        'dist': ExponentialDistribution(rate=0.04, random=RANDOM),
        'discrete': False,
    },
    {
        'label': "Beta\n(α=2, β=5)",
        'dist': BetaDistribution(alpha=2, beta=5, random=RANDOM),
        'discrete': False,
    },
    {
        'label': "Triangular\n(min=10, max=90, mode=70)",
        'dist': TriangularDistribution(min=10, max=90, mode=70, random=RANDOM),
        'discrete': False,
    },
    {
        'label': "Poisson\n(λ=45)",
        'dist': PoissonDistribution(lam=45, random=RANDOM),
        'discrete': True,
    },
]


# --- Theoretical PDF/PMF curves ---

def normal_pdf(x: np.ndarray, mean: float, std: float) -> np.ndarray:
    """Compute the normal probability density function."""
    return (1 / (std * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2)


def uniform_pdf(x: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """Compute the uniform probability density function."""
    return np.where((x >= min_val) & (x <= max_val), 1 / (max_val - min_val), 0.0)


def exponential_pdf(x: np.ndarray, rate: float) -> np.ndarray:
    """Compute the exponential probability density function."""
    return np.where(x >= 0, rate * np.exp(-rate * x), 0.0)


def beta_pdf(x: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    """Compute the beta probability density function."""
    coefficient = math.gamma(alpha + beta) / (math.gamma(alpha) * math.gamma(beta))
    return np.where(
        (x > 0) & (x < 1),
        coefficient * x ** (alpha - 1) * (1 - x) ** (beta - 1),
        0.0,
    )


def triangular_pdf(x: np.ndarray, min_val: float, max_val: float, mode: float) -> np.ndarray:
    """Compute the triangular probability density function."""
    output = np.zeros_like(x, dtype=float)
    ascending_mask = (x >= min_val) & (x <= mode)
    descending_mask = (x > mode) & (x <= max_val)
    output[ascending_mask] = 2 * (x[ascending_mask] - min_val) / ((max_val - min_val) * (mode - min_val))
    output[descending_mask] = 2 * (max_val - x[descending_mask]) / ((max_val - min_val) * (max_val - mode))
    return output


def poisson_pmf(k: np.ndarray, lam: float) -> np.ndarray:
    """Compute the Poisson probability mass function."""
    return np.array([math.exp(-lam + k_i * math.log(lam) - math.lgamma(k_i + 1)) for k_i in k])


# Theoretical functions for raw sampling (unbounded)
THEORETICAL_RAW = [
    lambda x: normal_pdf(x, 50, 40),
    lambda x: uniform_pdf(x, 10, 90),
    lambda x: exponential_pdf(x, 0.04),
    lambda x: beta_pdf(x, 2, 5),
    lambda x: triangular_pdf(x, 10, 90, 70),
    None,  # Poisson handled separately
]

# Theoretical functions for continuous/discrete sampling (bounded)
THEORETICAL_BOUNDED = [
    lambda x: normal_pdf(x, 50, 40),
    lambda x: uniform_pdf(x, 10, 90),
    lambda x: exponential_pdf(x, 0.04),
    lambda x: beta_pdf(x / 100, 2, 5) / 100,  # Beta retains the stretch!
    lambda x: triangular_pdf(x, 10, 90, 70),
    None,  # Poisson handled separately
]


# --- Helper functions ---

def generate_samples(dist, n_samples: int) -> list[float]:
    """Generate samples from a distribution without range constraints."""
    return [dist.sample() for _ in range(n_samples)]


def generate_continuous_samples(dist, n_samples: int, start: float, end: float) -> list[float]:
    """Generate samples from a distribution within a continuous range."""
    return [dist.sample_continuous(start, end) for _ in range(n_samples)]


def generate_discrete_samples(dist, n_samples: int, start: int, end: int) -> list[int]:
    """Generate samples from a distribution within a discrete range."""
    return [dist.sample_discrete(start, end) for _ in range(n_samples)]


def compute_discrete_frequencies(samples: list[int | float]) -> tuple[list, list[float]]:
    """Compute frequency distribution from discrete samples."""
    counts = {}
    for sample in samples:
        counts[sample] = counts.get(sample, 0) + 1

    discrete_values = sorted(counts)
    frequencies = [counts[value] / len(samples) for value in discrete_values]
    return discrete_values, frequencies


def normalize_density(density_values: np.ndarray, x_values: np.ndarray) -> np.ndarray:
    """Normalize density to integrate to 1.0."""
    dx = x_values[1] - x_values[0]
    return density_values / (density_values.sum() * dx)


def get_theoretical_probabilities(
    entry: dict,
    distribution_index: int,
    value_range: np.ndarray,
) -> np.ndarray | None:
    """Compute theoretical probabilities for discrete sampling."""
    if entry['discrete']:
        return poisson_pmf(value_range, lam=entry['dist'].lam)

    theoretical_function = THEORETICAL_BOUNDED[distribution_index]
    if theoretical_function is None:
        return None

    return theoretical_function(value_range)


def configure_plot_axes(ax, row_index: int):
    """Configure axes labels, legend, and grid for a subplot."""
    ax.set_xlabel("Value")
    ax.set_ylabel("Density / Prob." if row_index < 2 else "Probability")

    handles, _ = ax.get_legend_handles_labels()
    if handles:
        ax.legend(fontsize=7)

    ax.grid(True, linestyle="--", alpha=0.4)


# --- Plotting functions ---

def plot_raw(ax, entry: dict, distribution_index: int):
    """Plot raw sample() distribution without range constraints."""
    dist = entry['dist']
    is_discrete = entry['discrete']
    samples = generate_samples(dist, N_SAMPLES)

    if is_discrete:
        discrete_values, frequencies = compute_discrete_frequencies(samples)
        ax.bar(
            discrete_values,
            frequencies,
            color=PLOT_COLORS['raw'],
            alpha=0.7,
            label="Sampled",
            zorder=2,
        )

        value_range = np.arange(0, max(discrete_values) + 1)
        theoretical_probabilities = poisson_pmf(value_range, lam=dist.lam)
        ax.plot(
            value_range,
            theoretical_probabilities,
            f'{THEORETICAL_COLOR}-o',
            markersize=4,
            linewidth=1.5,
            label="Theoretical PMF",
            zorder=3,
        )
    else:
        ax.hist(
            samples,
            bins=60,
            density=True,
            color=PLOT_COLORS['raw'],
            alpha=0.7,
            label="Sampled",
            zorder=2,
        )

        sample_min, sample_max = min(samples), max(samples)
        x_values = np.linspace(sample_min, sample_max, 500)
        theoretical_density = THEORETICAL_RAW[distribution_index](x_values)
        ax.plot(
            x_values,
            theoretical_density,
            f'{THEORETICAL_COLOR}-',
            linewidth=2,
            label="Theoretical PDF",
            zorder=3,
        )

    ax.set_title(entry['label'] + "\nsample()", fontsize=8)


def plot_continuous(ax, entry: dict, distribution_index: int):
    """Plot sample_continuous() distribution with range constraints."""
    dist = entry['dist']
    is_discrete = entry['discrete']

    if is_discrete:
        ax.text(
            0.5,
            0.5,
            "N/A\n(discrete)",
            ha='center',
            va='center',
            transform=ax.transAxes,
            fontsize=9,
            color='gray',
        )
        ax.set_title(entry['label'] + "\nsample_continuous()", fontsize=8)
        return

    continuous_start, continuous_end = CONTINUOUS_RANGE
    samples = generate_continuous_samples(dist, N_SAMPLES, continuous_start, continuous_end)
    ax.hist(
        samples,
        bins=60,
        density=True,
        color=PLOT_COLORS['continuous'],
        alpha=0.7,
        label="Sampled",
        zorder=2,
    )

    x_values = np.linspace(continuous_start, continuous_end, 500)
    theoretical_function = THEORETICAL_BOUNDED[distribution_index]
    if theoretical_function is not None:
        theoretical_density = theoretical_function(x_values)
        # Normalize area to 1.0 so the theoretical line matches truncated histograms
        theoretical_density = normalize_density(theoretical_density, x_values)
        ax.plot(
            x_values,
            theoretical_density,
            f'{THEORETICAL_COLOR}-',
            linewidth=2,
            label="Theoretical PDF",
            zorder=3,
        )

    ax.set_title(
        entry['label'] + f"\nsample_continuous({continuous_start}, {continuous_end})",
        fontsize=8,
    )


def plot_discrete(ax, entry: dict, distribution_index: int):
    """Plot sample_discrete() distribution with range constraints."""
    dist = entry['dist']
    discrete_start, discrete_end = DISCRETE_RANGE

    samples = generate_discrete_samples(dist, N_SAMPLES, discrete_start, discrete_end)
    discrete_values, frequencies = compute_discrete_frequencies(samples)
    ax.bar(
        discrete_values,
        frequencies,
        color=PLOT_COLORS['discrete'],
        alpha=0.7,
        label="Sampled",
        zorder=2,
    )

    value_range = np.arange(discrete_start, discrete_end + 1, dtype=float)
    theoretical_probabilities = get_theoretical_probabilities(entry, distribution_index, value_range)

    if theoretical_probabilities is not None:
        # Normalize to sum-to-1
        theoretical_probabilities = theoretical_probabilities / theoretical_probabilities.sum()

        if entry['discrete']:
            ax.plot(
                value_range,
                theoretical_probabilities,
                f'{THEORETICAL_COLOR}-o',
                markersize=4,
                linewidth=1.5,
                label="Theoretical PMF",
                zorder=3,
            )
        else:
            ax.plot(
                value_range,
                theoretical_probabilities,
                f'{THEORETICAL_COLOR}-',
                linewidth=1.5,
                label="Theoretical (normalized)",
                zorder=3,
            )

    ax.set_title(
        entry['label'] + f'\nsample_discrete({discrete_start}, {discrete_end})',
        fontsize=8,
    )


def create_all_subplots(fig, grid_spec, distributions: list[dict]):
    """Create all distribution comparison subplots."""
    plot_functions = [plot_raw, plot_continuous, plot_discrete]

    for column_index, distribution_entry in enumerate(distributions):
        for row_index, plot_function in enumerate(plot_functions):
            ax = fig.add_subplot(grid_spec[row_index, column_index])
            plot_function(ax, distribution_entry, column_index)
            configure_plot_axes(ax, row_index)


# --- Main execution ---

n_distributions = len(DISTRIBUTIONS)
fig = plt.figure(figsize=(20, 12))
fig.suptitle(
    "Distribution Samples vs Theoretical PDF/PMF\n"
    "Row 1: sample()  |  Row 2: sample_continuous(0,100)  |  Row 3: sample_discrete(0,100)",
    fontsize=13,
    fontweight="bold",
)
gs = gridspec.GridSpec(3, n_distributions, figure=fig, hspace=0.6, wspace=0.35)

create_all_subplots(fig, gs, DISTRIBUTIONS)

plt.savefig('distributions.webp', dpi=96, bbox_inches='tight')
print("Saved distributions.webp")  # noqa: T201
plt.show()
