"""
Lightweight profiler for identifying optimization opportunities in mixins.

Usage:
    from odoo.tools.mixin_profiler import profile_methods, get_profile_report

    # Enable profiling for specific methods
    profile_methods('res.partner', ['create', 'write', 'read', '_compute_display_name'])

    # Do operations...
    partners = env['res.partner'].create([...])

    # Get report
    _logger.info(get_profile_report())

See Also
--------
- ``odoo.tools.orm_profiler`` — Aggregate per-model/operation stats per transaction
- ``odoo.tools.nplusone`` — N+1 CRUD detection (repeated single-record calls)
- ``odoo.tools.profiler`` — Sampling profiler (flamegraphs, SQL tracing)
- ``odoo.tests.benchmark`` — Micro-benchmark statistical utilities
- ``.claude/rules/profiling.md`` — Decision tree: which tool to use when
"""

import functools
import logging
import threading
import time
from collections import defaultdict
from contextlib import contextmanager

_logger = logging.getLogger(__name__)

# Thread-local storage for profiling data
_profile_data = threading.local()


def _get_data():
    if not hasattr(_profile_data, "methods"):
        _profile_data.methods = defaultdict(
            lambda: {
                "calls": 0,
                "total_time": 0.0,
                "total_queries": 0,
                "total_query_time": 0.0,
                "self_time": 0.0,  # Time excluding nested calls
                "samples": [],  # Recent samples for analysis
            }
        )
        _profile_data.call_stack = []
        _profile_data.enabled = False
    return _profile_data


def _wrap_method(model_name, method_name, original_method):
    """Wrap a method to collect profiling data."""

    @functools.wraps(original_method)
    def wrapper(self, *args, **kwargs):
        data = _get_data()
        if not data.enabled:
            return original_method(self, *args, **kwargs)

        key = f"{model_name}.{method_name}"
        cr = self.env.cr
        thread = threading.current_thread()

        # Track timing
        start_time = time.perf_counter()
        start_queries = cr.sql_log_count if hasattr(cr, "sql_log_count") else 0
        start_query_time = getattr(thread, "query_time", 0.0)

        # Push child-time accumulator for self-time calculation.
        # Each entry is the total elapsed time of profiled children.
        data.call_stack.append(0.0)

        try:
            result = original_method(self, *args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start_time
            queries = (
                cr.sql_log_count if hasattr(cr, "sql_log_count") else 0
            ) - start_queries
            query_time = getattr(thread, "query_time", 0.0) - start_query_time

            child_time = data.call_stack.pop()

            # Report my elapsed to parent's child-time accumulator
            if data.call_stack:
                data.call_stack[-1] += elapsed

            # Update stats
            stats = data.methods[key]
            stats["calls"] += 1
            stats["total_time"] += elapsed
            stats["total_queries"] += queries
            stats["total_query_time"] += query_time
            stats["self_time"] += elapsed - child_time

            # Keep recent samples for variance analysis
            if len(stats["samples"]) < 100:
                stats["samples"].append(
                    {
                        "time": elapsed * 1000,  # ms
                        "queries": queries,
                        "records": len(self) if hasattr(self, "__len__") else 1,
                    }
                )

        return result

    return wrapper


def profile_methods(model_name, method_names, registry=None):
    """
    Enable profiling for specific methods on a model.

    Args:
        model_name: The model to profile (e.g., 'res.partner')
        method_names: List of method names to profile
        registry: Optional registry (uses thread's registry if not provided)
    """
    if registry is None:
        # Import here to avoid circular imports
        from odoo.modules.registry import Registry

        registry = Registry.registries.get(threading.current_thread().dbname)

    if registry is None:
        _logger.warning("No registry found, cannot profile methods")
        return

    model_class = registry.get(model_name)
    if model_class is None:
        _logger.warning("Model %s not found in registry", model_name)
        return

    for method_name in method_names:
        if hasattr(model_class, method_name):
            original = getattr(model_class, method_name)
            if not hasattr(original, "_profiled"):
                wrapped = _wrap_method(model_name, method_name, original)
                wrapped._profiled = True
                wrapped._original = original
                setattr(model_class, method_name, wrapped)
                _logger.info("Profiling enabled for %s.%s", model_name, method_name)


def unprofile_methods(model_name, method_names, registry=None):
    """Remove profiling from methods."""
    if registry is None:
        from odoo.modules.registry import Registry

        registry = Registry.registries.get(threading.current_thread().dbname)

    if registry is None:
        return

    model_class = registry.get(model_name)
    if model_class is None:
        return

    for method_name in method_names:
        method = getattr(model_class, method_name, None)
        if method and hasattr(method, "_original"):
            setattr(model_class, method_name, method._original)


@contextmanager
def profiling_enabled():
    """Context manager to enable profiling collection."""
    data = _get_data()
    was_enabled = data.enabled
    data.enabled = True
    try:
        yield
    finally:
        data.enabled = was_enabled


def clear_profile_data():
    """Clear all collected profiling data."""
    data = _get_data()
    data.methods.clear()


def get_profile_report(sort_by="total_time", top_n=20):
    """
    Generate a profiling report.

    Args:
        sort_by: 'total_time', 'calls', 'queries', 'self_time', 'avg_time'
        top_n: Number of top methods to show
    """
    data = _get_data()

    if not data.methods:
        return "No profiling data collected."

    lines = []
    lines.extend(("\n" + "=" * 100, "MIXIN METHOD PROFILING REPORT", "=" * 100))

    # Calculate derived metrics
    methods = []
    for key, stats in data.methods.items():
        if stats["calls"] == 0:
            continue
        avg_time = stats["total_time"] / stats["calls"] * 1000  # ms
        avg_queries = stats["total_queries"] / stats["calls"]
        python_time = stats["total_time"] - stats["total_query_time"]
        python_pct = (
            (python_time / stats["total_time"] * 100) if stats["total_time"] > 0 else 0
        )

        methods.append(
            {
                "key": key,
                "calls": stats["calls"],
                "total_time": stats["total_time"] * 1000,  # ms
                "self_time": stats["self_time"] * 1000,  # ms
                "avg_time": avg_time,
                "total_queries": stats["total_queries"],
                "avg_queries": avg_queries,
                "python_pct": python_pct,
                "samples": stats["samples"],
            }
        )

    # Sort
    sort_keys = {
        "total_time": lambda m: -m["total_time"],
        "self_time": lambda m: -m["self_time"],
        "calls": lambda m: -m["calls"],
        "queries": lambda m: -m["total_queries"],
        "avg_time": lambda m: -m["avg_time"],
    }
    methods.sort(key=sort_keys.get(sort_by, sort_keys["total_time"]))

    # Header
    lines.extend((f"\n{'Method':<50} {'Calls':>8} {'Total(ms)':>10} {'Avg(ms)':>10} {'Queries':>8} {'Python%':>8}", "-" * 100))

    # Top methods
    lines.extend(f"{m['key']:<50} {m['calls']:>8} {m['total_time']:>10.2f} "
            f"{m['avg_time']:>10.3f} {m['total_queries']:>8} {m['python_pct']:>7.1f}%" for m in methods[:top_n])

    # Optimization opportunities
    lines.extend(("\n" + "=" * 100, "OPTIMIZATION OPPORTUNITIES", "=" * 100))

    # High Python percentage (mixin overhead candidates)
    high_python = [m for m in methods if m["python_pct"] > 70 and m["total_time"] > 10]
    if high_python:
        lines.append(
            "\n[HIGH PYTHON TIME] These methods spend >70% time in Python (mixin/ORM overhead):"
        )
        lines.extend(f"  - {m['key']}: {m['python_pct']:.1f}% Python, {m['avg_time']:.3f}ms avg" for m in high_python[:5])

    # High query count per call (N+1 candidates)
    high_queries = [m for m in methods if m["avg_queries"] > 5]
    if high_queries:
        lines.append("\n[N+1 QUERY PATTERN] These methods execute >5 queries per call:")
        lines.extend(f"  - {m['key']}: {m['avg_queries']:.1f} queries/call" for m in sorted(high_queries, key=lambda x: -x["avg_queries"])[:5])

    # High variance (inconsistent performance)
    for m in methods:
        if len(m["samples"]) >= 10:
            times = [s["time"] for s in m["samples"]]
            avg = sum(times) / len(times)
            variance = sum((t - avg) ** 2 for t in times) / len(times)
            std_dev = variance**0.5
            cv = (std_dev / avg * 100) if avg > 0 else 0
            m["cv"] = cv

    high_variance = [m for m in methods if m.get("cv", 0) > 50]
    if high_variance:
        lines.append(
            "\n[HIGH VARIANCE] These methods have inconsistent performance (CV > 50%):"
        )
        lines.extend(f"  - {m['key']}: CV={m['cv']:.1f}% (caching opportunity?)" for m in sorted(high_variance, key=lambda x: -x.get("cv", 0))[:5])

    # Frequently called (micro-optimization candidates)
    hot_methods = [m for m in methods if m["calls"] > 1000 and m["avg_time"] > 0.1]
    if hot_methods:
        lines.append(
            "\n[HOT METHODS] Called >1000 times with >0.1ms avg (micro-optimization targets):"
        )
        for m in sorted(hot_methods, key=lambda x: -x["calls"])[:5]:
            potential_savings = (
                m["calls"] * m["avg_time"] * 0.2
            )  # 20% improvement estimate
            lines.extend((f"  - {m['key']}: {m['calls']} calls, {m['avg_time']:.3f}ms avg", f"    → 20% speedup would save {potential_savings:.1f}ms total"))

    return "\n".join(lines)


def get_query_patterns():
    """Analyze query patterns from samples."""
    data = _get_data()
    patterns = []

    for key, stats in data.methods.items():
        samples = stats["samples"]
        if not samples:
            continue

        # Check for scaling issues
        records_queries = [
            (s["records"], s["queries"]) for s in samples if s["records"] > 0
        ]
        if len(records_queries) >= 5:
            # Simple linear regression to detect O(n) query patterns
            n_values = [r for r, q in records_queries]
            q_values = [q for r, q in records_queries]
            if max(n_values) > min(n_values) * 2:  # Enough variance in record counts
                # Check if queries scale with records
                n_range = max(n_values) - min(n_values)
                q_range = max(q_values) - min(q_values)
                if n_range > 0 and q_range > n_range * 0.5:
                    patterns.append(
                        {
                            "method": key,
                            "pattern": "O(n) queries",
                            "detail": f"Queries scale with record count: {min(q_values)}-{max(q_values)} for {min(n_values)}-{max(n_values)} records",
                        }
                    )

    return patterns
