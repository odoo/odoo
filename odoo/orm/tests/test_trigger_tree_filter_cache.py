import itertools

from odoo.orm.tests.test_trigger_publication_staleness import (
    _FakeField,
    _FakeModel,
    _FakeRegistry,
)


def _stored_computed(name, depends):
    field = _FakeField(name, "m", depends=depends)
    field.compute = f"_compute_{name}"
    return field


def _registry():
    a = _FakeField("a", "m")
    b = _stored_computed("b", [(a,)])
    c = _FakeField("c", "m", depends=[(a,)])
    c.store = False
    c.compute = "_compute_c"
    d = _FakeField("d", "m", depends=[(c,)])
    d.store = False
    d.compute = "_compute_d"
    registry = _FakeRegistry({"m": _FakeModel([a, b, c, d])})
    return registry, a, b, c, d


def test_the_filtered_tree_is_the_walk_for_every_cache_outcome_and_is_reused():
    registry, a, _b, c, d = _registry()

    def static(field):
        return field.is_stored_computed

    for cached in itertools.chain.from_iterable(
        itertools.combinations((c, d), n) for n in range(3)
    ):

        def select(field, cached=frozenset(cached)):
            return static(field) or field in cached

        expected = registry.model_graph.get_trigger_tree([a])._filtered(select)
        first = registry.get_trigger_tree([a], select=select, static=static)
        again = registry.get_trigger_tree([a], select=select, static=static)
        assert first == expected
        assert again is first


def test_a_changed_cache_outcome_is_not_served_the_previous_tree():
    registry, a, _b, c, _d = _registry()

    def static(field):
        return field.is_stored_computed

    cached = set()

    def select(field):
        return static(field) or field in cached

    without_c = registry.get_trigger_tree([a], select=select, static=static)
    cached.add(c)
    with_c = registry.get_trigger_tree([a], select=select, static=static)
    assert c not in without_c.root
    assert c in with_c.root
