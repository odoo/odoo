import pytest

from odoo.libs import accel
from odoo.libs._trigger_trees import get_trigger_trees as reference

BUILDERS = [reference, accel.get_trigger_trees]


def _siblings(n: int, *, shared_fact: bool):
    # n copies F_i of one column, each depending on itself through its own
    # many2one P_i, so F_i --[P_j]--> F_j for every i and j
    meta = [(False, False, 0, 0, i, 0, 0 if shared_fact else i) for i in range(n)]
    meta += [(True, False, 1, 0, i, i, n if shared_fact else n + i) for i in range(n)]
    triggers = [(i, [([n + j], [j]) for j in range(n)]) for i in range(n)]
    return triggers, meta


def _count(node) -> int:
    return 1 + sum(_count(child) for _, child in node[1])


@pytest.mark.parametrize("build", BUILDERS)
def test_siblings_of_one_fact_cost_one_level(build):
    n = 9
    [(_, tree)] = build(*_siblings(n, shared_fact=True), [0])
    assert _count(tree) == 1 + n
    assert sorted(t for _, (roots, _) in tree[1] for t in roots) == list(range(n))
    assert sorted(label for label, _ in tree[1]) == list(range(n, 2 * n))


@pytest.mark.parametrize("build", BUILDERS)
def test_distinct_facts_keep_the_full_walk(build):
    [(_, tree)] = build(*_siblings(4, shared_fact=False), [0])
    assert _count(tree) == 65


def test_both_builders_agree_on_shared_facts():
    triggers, meta = _siblings(6, shared_fact=True)
    assert accel.get_trigger_trees(triggers, meta) == reference(triggers, meta)
