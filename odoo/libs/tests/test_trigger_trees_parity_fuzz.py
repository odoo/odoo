import random

import pytest

from odoo.libs._trigger_trees import get_trigger_trees as reference

fast = pytest.importorskip("odoo_rust", exc_type=ImportError)

SEED = 20260903


def _random_graph(rng):
    n_fields = rng.randrange(2, 40)
    n_models = rng.randrange(1, 4)
    meta = []
    for _ in range(n_fields):
        kind = rng.random()
        model = rng.randrange(n_models)
        comodel = rng.randrange(n_models)
        if kind < 0.25:
            meta.append((True, False, rng.randrange(6), 0, model, comodel, 0))
        elif kind < 0.5:
            meta.append((False, True, 0, rng.randrange(6), model, comodel, 0))
        else:
            meta.append((False, False, rng.randrange(6), 0, model, comodel, 0))
    # a fact shared by a few fields, as sibling copies of one column share it
    n_facts = rng.randrange(max(1, n_fields // 2), n_fields + 1)
    meta = [(*m[:6], rng.randrange(n_facts)) for m in meta]
    triggers = []
    for dep in rng.sample(range(n_fields), rng.randrange(1, n_fields // 2 + 1)):
        buckets: dict[tuple[int, ...], list] = {}
        for _ in range(rng.randrange(1, 3)):
            path = tuple(rng.randrange(n_fields) for _ in range(rng.randrange(0, 3)))
            targets = buckets.setdefault(path, [])
            for _ in range(rng.randrange(1, 3)):
                if rng.random() < 0.85 and dep + 1 < n_fields:
                    target = rng.randrange(dep + 1, n_fields)
                else:
                    target = rng.randrange(n_fields)
                if target not in targets:
                    targets.append(target)
        triggers.append((dep, [(list(p), t) for p, t in buckets.items()]))
    return triggers, meta


def test_the_native_builder_matches_the_reference_on_random_graphs():
    rng = random.Random(SEED)
    for _ in range(800):
        triggers, meta = _random_graph(rng)
        assert fast.get_trigger_trees(triggers, meta) == reference(triggers, meta), (
            f"triggers={triggers!r} meta={meta!r}"
        )


def test_a_field_subset_is_built_in_the_order_asked():
    rng = random.Random(SEED + 1)
    triggers, meta = _random_graph(rng)
    fields = [dep for dep, _ in triggers][::-1] + [len(meta) - 1]
    assert fast.get_trigger_trees(triggers, meta, fields) == reference(
        triggers, meta, fields
    )
    assert [f for f, _ in fast.get_trigger_trees(triggers, meta, fields)] == fields


def test_an_untriggered_field_is_an_empty_tree_on_both_sides():
    triggers: list = [(0, [([], [1])])]
    meta = [(False, False, 0, 0, 0, 0, i) for i in range(3)]
    assert fast.get_trigger_trees(triggers, meta, [2]) == reference(triggers, meta, [2])
    assert fast.get_trigger_trees(triggers, meta, [2]) == [(2, ([], []))]


@pytest.mark.parametrize("build", [fast.get_trigger_trees, reference])
def test_an_out_of_range_field_id_is_refused(build):
    meta = [(False, False, 0, 0, 0, 0, i) for i in range(2)]
    with pytest.raises(IndexError):
        build([(0, [([], [5])])], meta)
    with pytest.raises(IndexError):
        build([(0, [([], [1])])], meta, [7])
