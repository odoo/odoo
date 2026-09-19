import copy
import timeit
from types import SimpleNamespace

import pytest

from odoo.libs._field_access._fallback import (
    batch_cache_fill,
    batch_cache_filter,
    batch_cache_get,
    batch_group_ids,
    sort_ids_by_cache,
    to_prefetch_ids,
)
from odoo.libs._trigger_trees import get_trigger_trees
from odoo.libs.accel import origin_ids_python as _origin_ids_python
from odoo.libs.tests._native_references import (
    NewId,
    clone_ref,
    csv_export_ref,
    rows_to_dicts_ref,
)

fast = pytest.importorskip("odoo_rust", exc_type=ImportError)

MAX_RATIO = 0.82

slow = SimpleNamespace(
    batch_cache_fill=batch_cache_fill,
    batch_cache_filter=batch_cache_filter,
    batch_cache_get=batch_cache_get,
    batch_group_ids=batch_group_ids,
    get_trigger_trees=get_trigger_trees,
    sort_ids_by_cache=sort_ids_by_cache,
    to_prefetch_ids=to_prefetch_ids,
    origin_ids=_origin_ids_python,
    csv_export=csv_export_ref,
    rows_to_dicts=rows_to_dicts_ref,
    fast_clone=clone_ref,
)

N = 500

SORT_N = 1000

_PENDING = object()
_NONE_VAL = object()

_IDS = tuple(range(1, N + 1))
_CACHE = {i: f"v{i % 37}" for i in _IDS}
_GROUPS = [f"g{i % 7}" for i in _IDS]

_SORT_IDS = tuple(range(1, SORT_N + 1))
_SORT_COLUMN = [f"v{(i * 7) % SORT_N}" for i in _SORT_IDS]
_SORT_CACHE = dict(zip(_SORT_IDS, _SORT_COLUMN, strict=True))

_COLUMNS = tuple(f"c{i}" for i in range(12))
_SQL_ROWS = [tuple(range(12)) for _ in range(N)]
_CSV_HEADERS = [f"h{i}" for i in range(12)]
_CSV_ROWS = [[f"cell {i}-{j}" for j in range(12)] for i in range(N)]
_BLOB = {"a": list(range(20)), "b": {"c": [{"d": i} for i in range(20)]}, "e": "x" * 50}
_ORIGIN_IDS = tuple(i if i % 3 else NewId(i * 10) for i in range(1, N + 1))


def _diamond_graph(depth: int):
    triggers: list = []
    meta: list = []

    def field(m2o=False, o2m=False, name=0, inverse=0, model=0, comodel=0):
        meta.append((m2o, o2m, name, inverse, model, comodel, len(meta)))
        return len(meta) - 1

    top = [field() for _ in range(depth + 1)]
    for i in range(depth):
        a, b, label = field(), field(), field()
        triggers.append((top[i], [([], [a, b])]))
        triggers.append((a, [([label], [top[i + 1]])]))
        triggers.append((b, [([label], [top[i + 1]])]))
    return triggers, meta


_TRIGGERS, _TRIGGER_META = _diamond_graph(40)


def _results():
    return [{"id": i} for i in _IDS]


CASES = (
    ("batch_cache_get", lambda m: m.batch_cache_get(_CACHE, _IDS, _PENDING, _NONE_VAL)),
    ("batch_cache_filter", lambda m: m.batch_cache_filter(_CACHE, _IDS, _PENDING)),
    (
        "batch_cache_fill",
        lambda m: m.batch_cache_fill(
            _CACHE, _IDS, _results(), "f", _PENDING, _NONE_VAL
        ),
    ),
    ("batch_group_ids", lambda m: m.batch_group_ids(_IDS, _GROUPS)),
    (
        "sort_ids_by_cache",
        lambda m: m.sort_ids_by_cache(_SORT_CACHE, _SORT_IDS, _PENDING, False, True),
    ),
    ("to_prefetch_ids", lambda m: m.to_prefetch_ids(1, _IDS, {}, 1000)),
    ("origin_ids", lambda m: m.origin_ids(_ORIGIN_IDS)),
    ("get_trigger_trees", lambda m: m.get_trigger_trees(_TRIGGERS, _TRIGGER_META)),
    ("rows_to_dicts", lambda m: m.rows_to_dicts(_COLUMNS, _SQL_ROWS)),
    ("csv_export", lambda m: m.csv_export(_CSV_HEADERS, [list(r) for r in _CSV_ROWS])),
    ("fast_clone", lambda m: m.fast_clone(_BLOB)),
)


def _best(call, module) -> float:
    number, repeat = 50, 7
    return (
        min(timeit.repeat(lambda: call(module), number=number, repeat=repeat)) / number
    )


@pytest.mark.parametrize(("name", "call"), CASES, ids=[c[0] for c in CASES])
def test_the_accelerated_call_beats_the_reference(name, call):
    accelerated = _best(call, fast)
    reference = _best(call, slow)
    ratio = accelerated / reference
    assert ratio <= MAX_RATIO, (
        f"{name} takes {ratio:.2f}x the pure-Python reference's time "
        f"({accelerated * 1e6:.2f}us against {reference * 1e6:.2f}us); the bar "
        f"is {MAX_RATIO}. It is a hard dependency whose only purpose is to be "
        f"faster. Either the Rust has a defect — `sort_ids_by_cache` once reached "
        f"1.16x by dispatching on a column type it had already decided — or the "
        f"boundary costs more than the work, in which case drop the export and "
        f"keep the reference, as `scalar_cache_get` did."
    )


@pytest.mark.parametrize(("name", "call"), CASES, ids=[c[0] for c in CASES])
def test_both_sides_compute_the_same_thing(name, call):
    assert call(fast) == call(slow)


def test_fast_clone_also_beats_the_deepcopy_it_replaced():
    accelerated = _best(lambda m: m.fast_clone(_BLOB), fast)
    deepcopy_time = (
        min(timeit.repeat(lambda: copy.deepcopy(_BLOB), number=50, repeat=7)) / 50
    )
    assert accelerated < deepcopy_time / 2, (
        f"fast_clone is {accelerated * 1e6:.2f}us against copy.deepcopy's "
        f"{deepcopy_time * 1e6:.2f}us; it replaced deepcopy on the strength of a "
        f"large margin and no longer has one"
    )


def test_every_accelerated_function_is_measured():
    measured = {name for name, _ in CASES}
    exported = {name for name in fast.__all__ if callable(getattr(fast, name, None))}
    assert exported == measured, (
        f"accelerated functions with no measurement: {sorted(exported - measured)}; "
        f"measured but no longer exported: {sorted(measured - exported)}"
    )
    assert measured <= set(vars(slow)), (
        f"no reference for {sorted(measured - set(vars(slow)))}"
    )


def test_the_field_access_references_are_the_production_ones():
    for name in (
        "batch_cache_fill",
        "batch_cache_filter",
        "batch_cache_get",
        "batch_group_ids",
        "sort_ids_by_cache",
        "to_prefetch_ids",
    ):
        reference = getattr(slow, name)
        assert reference.__module__.endswith("_fallback"), (
            f"{name}'s reference is {reference.__module__}, not _fallback — a "
            f"benchmark-only copy is not held to _fallback's correctness tests"
        )
