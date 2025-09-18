"""Pure-Python tests for ModelGraph and TriggerTree — no Odoo, no database.

Uses a lightweight MockField class as hashable mock field keys with the
attributes that the graph's internal helpers check.
"""

import unittest

from odoo.orm.components.model_graph import (
    ModelGraph,
    TriggerTree,
    _Collector,
    _concat_paths,
)

# ---------------------------------------------------------------------------
# Helpers — mock field factories
# ---------------------------------------------------------------------------


class MockField:
    """Hashable mock field object for testing ModelGraph."""

    __slots__ = (
        "comodel_name",
        "compute",
        "inverse_name",
        "is_stored_computed",
        "model_name",
        "name",
        "relational",
        "store",
        "type",
    )

    def __init__(self, name, model_name="m", type_="char", relational=False, **kw):
        self.name = name
        self.model_name = model_name
        self.type = type_
        self.relational = relational
        self.comodel_name = kw.get("comodel_name")
        self.inverse_name = kw.get("inverse_name")
        self.is_stored_computed = kw.get("is_stored_computed", False)
        self.compute = kw.get("compute")
        self.store = kw.get("store", False)

    def __repr__(self):
        return f"MockField({self.name!r})"

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other


def _field(name, model="m", type_="char", relational=False, **kw):
    """Create a mock field with the attributes ModelGraph needs."""
    return MockField(name, model, type_, relational, **kw)


# ---------------------------------------------------------------------------
# TriggerTree tests
# ---------------------------------------------------------------------------


class TestTriggerTree(unittest.TestCase):
    """Test TriggerTree data structure operations."""

    def test_empty_tree_is_falsy(self):
        tree = TriggerTree()
        self.assertFalse(tree)

    def test_tree_with_root_is_truthy(self):
        tree = TriggerTree(["field_a"])
        self.assertTrue(tree)

    def test_tree_with_children_is_truthy(self):
        tree = TriggerTree()
        tree["edge"] = TriggerTree(["field_b"])
        self.assertTrue(tree)

    def test_increase_creates_subtree(self):
        tree = TriggerTree()
        sub = tree.increase("edge_x")
        self.assertIsInstance(sub, TriggerTree)
        self.assertIs(tree["edge_x"], sub)

    def test_increase_returns_existing(self):
        tree = TriggerTree()
        sub1 = tree.increase("edge_x")
        sub2 = tree.increase("edge_x")
        self.assertIs(sub1, sub2)

    def test_depth_first(self):
        root = TriggerTree(["A"])
        child = TriggerTree(["B"])
        grandchild = TriggerTree(["C"])
        child["gc"] = grandchild
        root["ch"] = child

        nodes = list(root.depth_first())
        self.assertEqual(len(nodes), 3)
        self.assertIs(nodes[0], root)
        self.assertIs(nodes[1], child)
        self.assertIs(nodes[2], grandchild)

    def test_repr(self):
        tree = TriggerTree(["f1"])
        r = repr(tree)
        self.assertIn("TriggerTree", r)
        self.assertIn("f1", r)

    # -- merge --

    def test_merge_empty(self):
        result = TriggerTree.merge([])
        self.assertFalse(result)

    def test_merge_single(self):
        tree = TriggerTree(["A", "B"])
        result = TriggerTree.merge([tree])
        self.assertEqual(list(result.root), ["A", "B"])

    def test_merge_roots(self):
        t1 = TriggerTree(["A", "B"])
        t2 = TriggerTree(["B", "C"])
        result = TriggerTree.merge([t1, t2])
        # A, B, C — B deduplicated
        self.assertEqual(list(result.root), ["A", "B", "C"])

    def test_merge_subtrees(self):
        edge = "edge_x"
        t1 = TriggerTree()
        t1[edge] = TriggerTree(["H1"])
        t2 = TriggerTree()
        t2[edge] = TriggerTree(["H2"])

        result = TriggerTree.merge([t1, t2])
        self.assertIn(edge, result)
        self.assertEqual(list(result[edge].root), ["H1", "H2"])

    def test_merge_select_filter(self):
        """The select function filters root fields."""
        t1 = TriggerTree(["keep", "drop"])
        result = TriggerTree.merge([t1], select=lambda f: f == "keep")
        self.assertEqual(list(result.root), ["keep"])

    def test_merge_discards_empty_subtrees(self):
        """Subtrees that become empty after filtering are excluded."""
        edge = "edge_x"
        t1 = TriggerTree()
        t1[edge] = TriggerTree(["only_field"])

        result = TriggerTree.merge([t1], select=lambda f: False)
        self.assertNotIn(edge, result)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# ModelGraph construction tests
# ---------------------------------------------------------------------------


class TestModelGraphConstruction(unittest.TestCase):
    """Test building a ModelGraph from scratch."""

    def test_add_trigger(self):
        g = ModelGraph()
        f = _field("price")
        t = _field("total", is_stored_computed=True)
        g.add_trigger(f, (), [t])
        self.assertTrue(g.has_triggers(f))

    def test_add_trigger_deduplicates(self):
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.add_trigger(f, (), [t])
        self.assertEqual(len(g._triggers[f][()]), 1)

    def test_inverses_via_collector(self):
        g = ModelGraph()
        f = _field("partner_id")
        inv = _field("order_ids")
        g._inverses[f] = (inv,)
        self.assertEqual(g.field_inverses[f], (inv,))

    def test_depends_via_collector(self):
        g = ModelGraph()
        f = _field("total")
        dep = _field("price")
        g._depends[f] = (dep,)
        self.assertEqual(g.field_depends[f], (dep,))

    def test_depends_context_via_collector(self):
        g = ModelGraph()
        f = _field("name")
        g._depends_context[f] = ("lang",)
        self.assertEqual(g.field_depends_context[f], ("lang",))

    def test_computed_direct_assignment(self):
        g = ModelGraph()
        f1 = _field("total")
        f2 = _field("tax")
        g._computed[f1] = [f1, f2]
        g._computed[f2] = [f1, f2]
        self.assertEqual(g.field_computed[f1], [f1, f2])

    def test_reset_field_metadata(self):
        g = ModelGraph()
        f = _field("price")
        g._depends[f] = ("dep",)
        g._depends_context[f] = ("lang",)
        g._inverses[f] = ("inv",)
        g._computed[f] = ["f1"]
        g.reset_field_metadata()
        self.assertEqual(len(g._depends), 0)
        self.assertEqual(len(g._depends_context), 0)
        self.assertEqual(len(g._inverses), 0)
        self.assertEqual(len(g._computed), 0)
        # Collections should be fresh instances
        self.assertIsInstance(g._depends, _Collector)
        self.assertIsInstance(g._inverses, _Collector)

    def test_no_triggers_is_falsy(self):
        g = ModelGraph()
        self.assertFalse(g.has_triggers(_field("whatever")))

    def test_reset_triggers(self):
        """reset_triggers() clears all trigger data and caches."""
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.get_field_trigger_tree(f)  # populate cache
        self.assertTrue(g.has_triggers(f))
        self.assertTrue(g._trigger_trees)

        g.reset_triggers()
        self.assertFalse(g.has_triggers(f))
        self.assertFalse(g._trigger_trees)
        self.assertFalse(g._modifying_relations)

    def test_reset_triggers_allows_rebuild(self):
        """After reset_triggers(), new triggers can be added incrementally."""
        g = ModelGraph()
        f1 = _field("price")
        t1 = _field("total")
        g.add_trigger(f1, (), [t1])

        # Reset and rebuild with different data
        g.reset_triggers()
        f2 = _field("name")
        t2 = _field("display_name")
        g.add_trigger(f2, (), [t2])

        # Old data gone, new data present
        self.assertFalse(g.has_triggers(f1))
        self.assertTrue(g.has_triggers(f2))
        deps = list(g.get_dependent_fields(f2))
        self.assertIn(t2, deps)

    def test_incremental_build_workflow(self):
        """Simulate the Registry pattern: reset → add_trigger × N → query."""
        g = ModelGraph()
        g.reset_triggers()

        price = _field("price", model="line")
        qty = _field("qty", model="line")
        total = _field("total", model="line", is_stored_computed=True)
        partner_id = _field(
            "partner_id",
            model="line",
            type_="many2one",
            comodel_name="partner",
            relational=True,
        )
        partner_total = _field(
            "partner_total", model="partner", is_stored_computed=True
        )

        # Simulate resolved dependencies:
        # total depends on price (direct) and qty (direct)
        g.add_trigger(price, (), [total])
        g.add_trigger(qty, (), [total])
        # partner_total depends on price via partner_id
        g.add_trigger(price, (partner_id,), [partner_total])

        # Verify trigger tree structure
        tree = g.get_trigger_tree([price])
        self.assertIn(total, tree.root)
        self.assertIn(partner_id, tree)
        self.assertIn(partner_total, tree[partner_id].root)

        tree2 = g.get_trigger_tree([qty])
        self.assertIn(total, tree2.root)

    def test_reset_triggers_preserves_field_metadata(self):
        """reset_triggers() only clears triggers, not depends/inverses/computed."""
        g = ModelGraph()
        f = _field("price")
        g._depends[f] = ("dep",)
        g._inverses[f] = ("inv",)
        g.add_trigger(f, (), [_field("total")])

        g.reset_triggers()
        # Triggers cleared
        self.assertFalse(g.has_triggers(f))
        # Other metadata preserved
        self.assertEqual(g._depends[f], ("dep",))
        self.assertEqual(g._inverses[f], ("inv",))


# ---------------------------------------------------------------------------
# ModelGraph query tests
# ---------------------------------------------------------------------------


class TestModelGraphQueries(unittest.TestCase):
    """Test querying the dependency graph."""

    def setUp(self):
        """Build a graph: price → total (direct), partner_id.price → partner_total (via path)."""
        self.g = ModelGraph()

        self.price = _field("price", model="order.line")
        self.total = _field("total", model="order.line", is_stored_computed=True)
        self.partner_id = _field(
            "partner_id",
            model="order.line",
            type_="many2one",
            comodel_name="partner",
            relational=True,
        )
        self.partner_total = _field(
            "partner_total",
            model="partner",
            is_stored_computed=True,
        )

        # price triggers total (direct — empty path)
        self.g.add_trigger(self.price, (), [self.total])
        # price also triggers partner_total (via partner_id path)
        self.g.add_trigger(self.price, (self.partner_id,), [self.partner_total])

    def test_get_trigger_tree_direct(self):
        tree = self.g.get_trigger_tree([self.price])
        self.assertIn(self.total, tree.root)

    def test_get_trigger_tree_with_path(self):
        tree = self.g.get_trigger_tree([self.price])
        self.assertIn(self.partner_id, tree)
        subtree = tree[self.partner_id]
        self.assertIn(self.partner_total, subtree.root)

    def test_get_trigger_tree_caches(self):
        tree1 = self.g.get_field_trigger_tree(self.price)
        tree2 = self.g.get_field_trigger_tree(self.price)
        self.assertIs(tree1, tree2)

    def test_get_trigger_tree_no_triggers(self):
        tree = self.g.get_trigger_tree([_field("unknown")])
        self.assertFalse(tree)

    def test_get_trigger_tree_select_filter(self):
        tree = self.g.get_trigger_tree(
            [self.price],
            select=lambda f: f is self.total,
        )
        self.assertIn(self.total, tree.root)
        # partner_total filtered out → subtree should be empty/missing
        if self.partner_id in tree:
            subtree = tree[self.partner_id]
            self.assertNotIn(self.partner_total, subtree.root)

    def test_get_dependent_fields(self):
        deps = list(self.g.get_dependent_fields(self.price))
        self.assertIn(self.total, deps)
        self.assertIn(self.partner_total, deps)

    def test_get_dependent_fields_no_triggers(self):
        deps = list(self.g.get_dependent_fields(_field("unknown")))
        self.assertEqual(deps, [])

    def test_clear_caches(self):
        # Populate the cache
        self.g.get_field_trigger_tree(self.price)
        self.assertTrue(self.g._trigger_trees)
        # Clear
        self.g.clear_caches()
        self.assertFalse(self.g._trigger_trees)

    def test_has_triggers(self):
        self.assertTrue(self.g.has_triggers(self.price))
        self.assertFalse(self.g.has_triggers(self.total))


class TestIsModifyingRelations(unittest.TestCase):
    """Test is_modifying_relations() logic."""

    def test_relational_field_with_triggers(self):
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        dep = _field("partner_name", is_stored_computed=True)
        g.add_trigger(m2o, (), [dep])
        self.assertTrue(g.is_modifying_relations(m2o))

    def test_scalar_field_no_relational_deps(self):
        g = ModelGraph()
        scalar = _field("name")
        dep = _field("display_name", is_stored_computed=True)
        g.add_trigger(scalar, (), [dep])
        # scalar with no relational deps → False
        self.assertFalse(g.is_modifying_relations(scalar))

    def test_scalar_with_relational_dependent(self):
        g = ModelGraph()
        scalar = _field("code")
        dep = _field("ref_id", relational=True)
        g.add_trigger(scalar, (), [dep])
        # dep is relational → True
        self.assertTrue(g.is_modifying_relations(scalar))

    def test_field_with_inverses(self):
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        o2m = _field("order_ids", type_="one2many", relational=True)
        dep = _field("total")
        g.add_trigger(m2o, (), [dep])
        g._inverses[m2o] = (o2m,)
        self.assertTrue(g.is_modifying_relations(m2o))

    def test_no_triggers_is_false(self):
        g = ModelGraph()
        self.assertFalse(g.is_modifying_relations(_field("x")))

    def test_caches_result(self):
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        dep = _field("total")
        g.add_trigger(m2o, (), [dep])
        g._inverses[m2o] = (dep,)
        r1 = g.is_modifying_relations(m2o)
        r2 = g.is_modifying_relations(m2o)
        self.assertEqual(r1, r2)
        self.assertIn(m2o, g._modifying_relations)


# ---------------------------------------------------------------------------
# Transitive trigger closure tests
# ---------------------------------------------------------------------------


class TestTransitiveTriggers(unittest.TestCase):
    """Test that trigger trees compute the transitive closure correctly."""

    def test_chain_a_to_b_to_c(self):
        """A → B → C should produce a tree where A triggers both B and C."""
        g = ModelGraph()
        a = _field("a")
        b = _field("b", is_stored_computed=True)
        c = _field("c", is_stored_computed=True)
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [c])

        g.get_field_trigger_tree(a)
        all_deps = list(g.get_dependent_fields(a))
        self.assertIn(b, all_deps)
        self.assertIn(c, all_deps)

    def test_cycle_detection(self):
        """Cycles in triggers should not cause infinite loops."""
        g = ModelGraph()
        a = _field("a")
        b = _field("b")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [a])

        # Should not hang
        tree = g.get_field_trigger_tree(a)
        self.assertTrue(tree)

    def test_diamond_dependency(self):
        """A → B, A → C, B → D, C → D should yield D once."""
        g = ModelGraph()
        a = _field("a")
        b = _field("b")
        c = _field("c")
        d = _field("d")
        g.add_trigger(a, (), [b, c])
        g.add_trigger(b, (), [d])
        g.add_trigger(c, (), [d])

        deps = list(g.get_dependent_fields(a))
        self.assertIn(b, deps)
        self.assertIn(c, deps)
        self.assertIn(d, deps)


# ---------------------------------------------------------------------------
# Path concatenation tests
# ---------------------------------------------------------------------------


class TestConcatPaths(unittest.TestCase):
    """Test _concat_paths m2o→o2m cancellation."""

    def test_simple_concat(self):
        a = _field("a")
        b = _field("b")
        result = _concat_paths((a,), (b,), {})
        self.assertEqual(result, (a, b))

    def test_empty_concat(self):
        self.assertEqual(_concat_paths((), (), {}), ())
        a = _field("a")
        self.assertEqual(_concat_paths((a,), (), {}), (a,))
        self.assertEqual(_concat_paths((), (a,), {}), (a,))

    def test_m2o_o2m_cancellation(self):
        """A many2one followed by its inverse one2many should cancel."""
        m2o = _field(
            "partner_id",
            model="order",
            type_="many2one",
            comodel_name="partner",
            relational=True,
        )
        o2m = _field(
            "order_ids",
            model="partner",
            type_="one2many",
            comodel_name="order",
            inverse_name="partner_id",
            relational=True,
        )
        result = _concat_paths((m2o,), (o2m,), {})
        self.assertEqual(result, ())

    def test_m2o_o2m_no_cancel_if_different_inverse(self):
        """Don't cancel if the o2m's inverse_name doesn't match the m2o's name."""
        m2o = _field(
            "partner_id",
            model="order",
            type_="many2one",
            comodel_name="partner",
            relational=True,
        )
        o2m = _field(
            "order_ids",
            model="partner",
            type_="one2many",
            comodel_name="order",
            inverse_name="other_id",
            relational=True,
        )
        result = _concat_paths((m2o,), (o2m,), {})
        self.assertEqual(result, (m2o, o2m))

    def test_m2o_o2m_no_cancel_if_different_models(self):
        """Don't cancel if the models don't match."""
        m2o = _field(
            "partner_id",
            model="order",
            type_="many2one",
            comodel_name="partner",
            relational=True,
        )
        o2m = _field(
            "order_ids",
            model="other_model",
            type_="one2many",
            comodel_name="order",
            inverse_name="partner_id",
            relational=True,
        )
        result = _concat_paths((m2o,), (o2m,), {})
        self.assertEqual(result, (m2o, o2m))


# ---------------------------------------------------------------------------
# discard_fields tests
# ---------------------------------------------------------------------------


class TestDiscardFields(unittest.TestCase):
    """Test removing fields from the graph."""

    def test_discard_from_triggers(self):
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.discard_fields([f])
        self.assertFalse(g.has_triggers(f))

    def test_discard_from_depends(self):
        g = ModelGraph()
        f = _field("total")
        g._depends[f] = ("price",)
        g.discard_fields([f])
        self.assertNotIn(f, g.field_depends)

    def test_discard_from_inverses_key(self):
        g = ModelGraph()
        f = _field("partner_id")
        inv = _field("order_ids")
        g._inverses[f] = (inv,)
        g.discard_fields([f])
        self.assertNotIn(f, g.field_inverses)

    def test_discard_from_inverses_value(self):
        g = ModelGraph()
        f = _field("partner_id")
        inv = _field("order_ids")
        g._inverses[f] = (inv,)
        g.discard_fields([inv])
        # f still exists but inv is filtered out of its tuple
        self.assertNotIn(f, g.field_inverses)  # empty tuple → removed

    def test_discard_clears_caches(self):
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.get_field_trigger_tree(f)  # populate cache
        g.discard_fields([f])
        self.assertFalse(g._trigger_trees)


# ---------------------------------------------------------------------------
# _Collector tests
# ---------------------------------------------------------------------------


class TestCollector(unittest.TestCase):
    """Test the lightweight _Collector dict subclass."""

    def test_missing_key_returns_empty_tuple(self):
        c = _Collector()
        self.assertEqual(c["nonexistent"], ())

    def test_setitem_stores_tuple(self):
        c = _Collector()
        c["key"] = [1, 2, 3]
        self.assertEqual(c["key"], (1, 2, 3))

    def test_setitem_removes_on_empty(self):
        c = _Collector()
        c["key"] = [1, 2]
        c["key"] = []
        self.assertNotIn("key", c)

    def test_add_appends(self):
        c = _Collector()
        c.add("key", "a")
        c.add("key", "b")
        self.assertEqual(c["key"], ("a", "b"))

    def test_add_deduplicates(self):
        c = _Collector()
        c.add("key", "a")
        c.add("key", "a")
        self.assertEqual(c["key"], ("a",))

    def test_discard_keys_and_values(self):
        c = _Collector()
        c["a"] = ("x", "y")
        c["b"] = ("x", "z")
        c["x"] = ("w",)
        c.discard_keys_and_values({"x"})
        self.assertNotIn("x", c)  # key removed
        self.assertEqual(c["a"], ("y",))  # value filtered
        self.assertEqual(c["b"], ("z",))

    def test_discard_removes_empty_after_filter(self):
        c = _Collector()
        c["a"] = ("x",)
        c.discard_keys_and_values({"x"})
        self.assertNotIn("a", c)  # became empty → removed

    def test_pop_works(self):
        c = _Collector()
        c["key"] = ("val",)
        result = c.pop("key", None)
        self.assertEqual(result, ("val",))
        self.assertNotIn("key", c)

    def test_clear_empties(self):
        c = _Collector()
        c["a"] = ("x",)
        c["b"] = ("y",)
        c.clear()
        self.assertEqual(len(c), 0)

    def test_get_returns_default(self):
        c = _Collector()
        self.assertEqual(c.get("missing"), None)
        self.assertEqual(c.get("missing", "default"), "default")

    def test_iteration(self):
        c = _Collector()
        c["a"] = ("x",)
        c["b"] = ("y",)
        self.assertEqual(set(c), {"a", "b"})


# ---------------------------------------------------------------------------
# Data ownership tests
# ---------------------------------------------------------------------------


class TestDataOwnership(unittest.TestCase):
    """Test that ModelGraph owns all field metadata collections."""

    def test_inverses_are_collector(self):
        g = ModelGraph()
        self.assertIsInstance(g._inverses, _Collector)

    def test_depends_are_collector(self):
        g = ModelGraph()
        self.assertIsInstance(g._depends, _Collector)

    def test_depends_context_are_collector(self):
        g = ModelGraph()
        self.assertIsInstance(g._depends_context, _Collector)

    def test_properties_delegate_to_internals(self):
        g = ModelGraph()
        self.assertIs(g.field_inverses, g._inverses)
        self.assertIs(g.field_depends, g._depends)
        self.assertIs(g.field_depends_context, g._depends_context)
        self.assertIs(g.field_computed, g._computed)

    def test_external_assignment_updates_property(self):
        """Simulates what Registry.field_inverses cached_property does:
        build a new Collector and assign it to model_graph._inverses.
        """
        g = ModelGraph()
        new_inverses = _Collector()
        f = _field("partner_id")
        inv = _field("order_ids")
        new_inverses[f] = (inv,)
        g._inverses = new_inverses
        self.assertIs(g.field_inverses, new_inverses)
        self.assertEqual(g.field_inverses[f], (inv,))

    def test_missing_key_returns_empty_tuple_via_property(self):
        """Ensure property delegation preserves _Collector's __getitem__ behavior."""
        g = ModelGraph()
        f = _field("nonexistent")
        self.assertEqual(g.field_inverses[f], ())
        self.assertEqual(g.field_depends[f], ())
        self.assertEqual(g.field_depends_context[f], ())


# ---------------------------------------------------------------------------
# Topological recompute order tests
# ---------------------------------------------------------------------------


class TestRecomputeOrder(unittest.TestCase):
    """Test _compute_recompute_order() topological sorting via Kahn's algorithm."""

    def _stored_computed(self, name, model="m"):
        """Create a mock field that looks like a stored computed field."""
        return _field(name, model=model, store=True, compute="_compute_" + name)

    def test_linear_chain_ordering(self):
        """A → B → C: priority(A) < priority(B) < priority(C)."""
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        c = self._stored_computed("c")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [c])

        order = g.recompute_order
        self.assertLess(order[a], order[b])
        self.assertLess(order[b], order[c])

    def test_diamond_dependencies(self):
        """A → B, A → C, B → D, C → D: A first, D last, B/C same level."""
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        c = self._stored_computed("c")
        d = self._stored_computed("d")
        g.add_trigger(a, (), [b, c])
        g.add_trigger(b, (), [d])
        g.add_trigger(c, (), [d])

        order = g.recompute_order
        self.assertLess(order[a], order[b])
        self.assertLess(order[a], order[c])
        self.assertLess(order[b], order[d])
        self.assertLess(order[c], order[d])
        # B and C should be at the same priority level
        self.assertEqual(order[b], order[c])

    def test_cycle_gets_max_priority(self):
        """A → B → A (cycle): both get the highest priority."""
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [a])

        order = g.recompute_order
        # Both should be present and get the same (max) priority
        self.assertIn(a, order)
        self.assertIn(b, order)
        self.assertEqual(order[a], order[b])

    def test_empty_graph(self):
        """No triggers → empty order dict."""
        g = ModelGraph()
        order = g.recompute_order
        self.assertEqual(order, {})

    def test_non_stored_fields_excluded(self):
        """Non-stored computed fields are not in the recompute order."""
        g = ModelGraph()
        source = self._stored_computed("source")
        non_stored = _field("non_stored", compute="_compute_ns", store=False)
        g.add_trigger(source, (), [non_stored])

        order = g.recompute_order
        self.assertNotIn(non_stored, order)

    def test_non_computed_fields_excluded(self):
        """Fields without compute are not in the recompute order."""
        g = ModelGraph()
        regular = _field("regular", store=True)  # no compute
        target = self._stored_computed("target")
        g.add_trigger(regular, (), [target])

        order = g.recompute_order
        # regular is not computed, should not be in order
        self.assertNotIn(regular, order)
        # target IS stored-computed, should be present
        self.assertIn(target, order)

    def test_caching(self):
        """recompute_order is computed once and cached."""
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        g.add_trigger(a, (), [b])

        order1 = g.recompute_order
        order2 = g.recompute_order
        self.assertIs(order1, order2)

    def test_cache_cleared_on_clear_caches(self):
        """clear_caches() invalidates the recompute order cache."""
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        g.add_trigger(a, (), [b])

        order1 = g.recompute_order
        g.clear_caches()
        order2 = g.recompute_order
        self.assertIsNot(order1, order2)
        # But values should be equal
        self.assertEqual(order1, order2)

    def test_mixed_cycle_and_chain(self):
        """A → B → C → B (cycle in B,C), A should be before B and C."""
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        c = self._stored_computed("c")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [c])
        g.add_trigger(c, (), [b])  # cycle

        order = g.recompute_order
        self.assertLess(order[a], order[b])
        self.assertLess(order[a], order[c])
        # B and C are in a cycle → same (max) priority
        self.assertEqual(order[b], order[c])


if __name__ == "__main__":
    unittest.main()
