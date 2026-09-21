import typing
import unittest

from odoo.orm.components.model_graph import (
    ModelGraph,
    TriggerTree,
    _Collector,
)


def _concat_paths(seq1: tuple, seq2: tuple) -> tuple:
    if seq1 and seq2:
        f1, f2 = seq1[-1], seq2[0]
        if (
            f1.is_many2one
            and f2.is_one2many
            and getattr(f2, "inverse_name", None) == getattr(f1, "name", None)
            and getattr(f1, "model_name", None) == getattr(f2, "comodel_name", None)
            and getattr(f1, "comodel_name", None) == getattr(f2, "model_name", None)
        ):
            return _concat_paths(seq1[:-1], seq2[1:])
    return seq1 + seq2


class MockField:
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

    def __init__(
        self,
        name: str,
        model_name: str = "m",
        type_: str = "char",
        relational: bool = False,
        **kw,
    ) -> None:
        self.name = name
        self.model_name = model_name
        self.type = type_
        self.relational = relational
        self.comodel_name = kw.get("comodel_name")
        self.inverse_name = kw.get("inverse_name")
        self.is_stored_computed = kw.get("is_stored_computed", False)
        self.compute = kw.get("compute")
        self.store = kw.get("store", False)

    @property
    def is_many2one(self) -> bool:
        return self.type == "many2one"

    @property
    def is_one2many(self) -> bool:
        return self.type == "one2many"

    def __repr__(self) -> str:
        return f"MockField({self.name!r})"

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        return self is other


def _field(name, model="m", type_="char", relational=False, **kw):
    return MockField(name, model, type_, relational, **kw)


class TestTriggerTree(unittest.TestCase):
    def test_empty_tree_is_falsy(self) -> None:
        tree = TriggerTree()
        self.assertFalse(tree)

    def test_tree_with_root_is_truthy(self) -> None:
        tree = TriggerTree(["field_a"])
        self.assertTrue(tree)

    def test_tree_with_children_is_truthy(self) -> None:
        tree = TriggerTree()
        tree["edge"] = TriggerTree(["field_b"])
        self.assertTrue(tree)

    def test_increase_creates_subtree(self) -> None:
        tree = TriggerTree()
        sub = tree.increase("edge_x")
        self.assertIsInstance(sub, TriggerTree)
        self.assertIs(tree["edge_x"], sub)

    def test_increase_returns_existing(self) -> None:
        tree = TriggerTree()
        sub1 = tree.increase("edge_x")
        sub2 = tree.increase("edge_x")
        self.assertIs(sub1, sub2)

    def test_depth_first(self) -> None:
        root = TriggerTree(["A"])
        child = TriggerTree(["B"])
        grandchild = TriggerTree(["C"])
        child["gc"] = grandchild
        root["ch"] = child

        nodes = list(root.iter_depth_first())
        self.assertEqual(len(nodes), 3)
        self.assertIs(nodes[0], root)
        self.assertIs(nodes[1], child)
        self.assertIs(nodes[2], grandchild)

    def test_repr(self) -> None:
        tree = TriggerTree(["f1"])
        r = repr(tree)
        self.assertIn("TriggerTree", r)
        self.assertIn("f1", r)

    def test_merge_empty(self) -> None:
        result = TriggerTree.merge([])
        self.assertFalse(result)

    def test_merge_single(self) -> None:
        tree = TriggerTree(["A", "B"])
        result = TriggerTree.merge([tree])
        self.assertEqual(list(result.root), ["A", "B"])

    def test_root_is_immutable_tuple(self) -> None:
        tree = TriggerTree(["A", "B"])
        self.assertIsInstance(tree.root, tuple)
        self.assertIs(TriggerTree.merge([tree]), tree)
        with self.assertRaises(AttributeError):
            typing.cast("typing.Any", tree.root).append("C")

    def test_merge_roots(self) -> None:
        t1 = TriggerTree(["A", "B"])
        t2 = TriggerTree(["B", "C"])
        result = TriggerTree.merge([t1, t2])
        self.assertEqual(list(result.root), ["A", "B", "C"])

    def test_merge_subtrees(self) -> None:
        edge = "edge_x"
        t1 = TriggerTree()
        t1[edge] = TriggerTree(["H1"])
        t2 = TriggerTree()
        t2[edge] = TriggerTree(["H2"])

        result = TriggerTree.merge([t1, t2])
        self.assertIn(edge, result)
        self.assertEqual(list(result[edge].root), ["H1", "H2"])

    def test_merge_select_filter(self) -> None:
        t1 = TriggerTree(["keep", "drop"])
        result = TriggerTree.merge([t1], select=lambda f: f == "keep")
        self.assertEqual(list(result.root), ["keep"])

    def test_merge_discards_empty_subtrees(self) -> None:
        edge = "edge_x"
        t1 = TriggerTree()
        t1[edge] = TriggerTree(["only_field"])

        result = TriggerTree.merge([t1], select=lambda f: False)
        self.assertNotIn(edge, result)
        self.assertFalse(result)


class TestModelGraphConstruction(unittest.TestCase):
    def test_add_trigger(self) -> None:
        g = ModelGraph()
        f = _field("price")
        t = _field("total", is_stored_computed=True)
        g.add_trigger(f, (), [t])
        self.assertTrue(g.has_triggers(f))

    def test_add_trigger_deduplicates(self) -> None:
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.add_trigger(f, (), [t])
        self.assertEqual(len(g._triggers[f][()]), 1)

    def test_add_trigger_rebuilds_the_trees_that_reach_the_field(self) -> None:
        # a tree is transitive: base's tree embeds mid's buckets, so an edge
        # added to mid makes base's cached tree stale too
        g = ModelGraph()
        base = _field("base")
        mid = _field("mid", is_stored_computed=True)
        late = _field("late", is_stored_computed=True)

        g.add_trigger(base, (), [mid])
        g.add_trigger(mid, (), [late])
        before = g.get_field_trigger_tree(base)
        self.assertEqual(set(before.root), {mid, late})

        later = _field("later", is_stored_computed=True)
        g.add_trigger(mid, (), [later])
        after = g.get_field_trigger_tree(base)
        self.assertEqual(set(after.root), {mid, late, later})
        self.assertIsNot(before, after)

    def test_add_trigger_after_the_tree_was_built(self) -> None:
        g = ModelGraph()
        f = _field("price")
        first = _field("total", is_stored_computed=True)
        second = _field("tax", is_stored_computed=True)

        g.add_trigger(f, (), [first])
        before = g.get_field_trigger_tree(f)
        self.assertEqual(set(before.root), {first})

        g.add_trigger(f, (), [second])
        after = g.get_field_trigger_tree(f)
        self.assertEqual(set(after.root), {first, second})
        self.assertIsNot(before, after)

    def test_inverses_via_collector(self) -> None:
        g = ModelGraph()
        f = _field("partner_id")
        inv = _field("order_ids")
        g._inverses[f] = (inv,)
        self.assertEqual(g.field_inverses[f], (inv,))

    def test_depends_via_collector(self) -> None:
        g = ModelGraph()
        f = _field("total")
        dep = _field("price")
        g._depends[f] = (dep,)
        self.assertEqual(g.field_depends[f], (dep,))

    def test_depends_context_via_collector(self) -> None:
        g = ModelGraph()
        f = _field("name")
        g._depends_context[f] = ("lang",)
        self.assertEqual(g.field_depends_context[f], ("lang",))

    def test_computed_direct_assignment(self) -> None:
        g = ModelGraph()
        f1 = _field("total")
        f2 = _field("tax")
        g._computed[f1] = [f1, f2]
        g._computed[f2] = [f1, f2]
        self.assertEqual(g.field_computed[f1], [f1, f2])

    def test_reset_field_metadata_clears_in_place(self) -> None:
        g = ModelGraph()
        f = _field("price")
        g._depends[f] = ("dep",)
        g._depends_context[f] = ("lang",)
        g._inverses[f] = ("inv",)
        g._computed[f] = ["f1"]
        depends, depends_ctx = g._depends, g._depends_context
        inverses, computed = g._inverses, g._computed

        g.reset_field_metadata()

        self.assertEqual(len(g._depends), 0)
        self.assertEqual(len(g._depends_context), 0)
        self.assertEqual(len(g._inverses), 0)
        self.assertEqual(len(g._computed), 0)
        self.assertIs(g._depends, depends)
        self.assertIs(g._depends_context, depends_ctx)
        self.assertIs(g._inverses, inverses)
        self.assertIs(g._computed, computed)
        self.assertIsInstance(g._depends, _Collector)

    def test_no_triggers_is_falsy(self) -> None:
        g = ModelGraph()
        self.assertFalse(g.has_triggers(_field("whatever")))

    def test_reset_triggers(self) -> None:
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.get_field_trigger_tree(f)
        self.assertTrue(g.has_triggers(f))
        self.assertTrue(g._trigger_trees)

        g.reset_triggers()
        self.assertFalse(g.has_triggers(f))
        self.assertFalse(g._trigger_trees)
        self.assertFalse(g._modifying_relations)

    def test_reset_triggers_allows_rebuild(self) -> None:
        g = ModelGraph()
        f1 = _field("price")
        t1 = _field("total")
        g.add_trigger(f1, (), [t1])

        g.reset_triggers()
        f2 = _field("name")
        t2 = _field("display_name")
        g.add_trigger(f2, (), [t2])

        self.assertFalse(g.has_triggers(f1))
        self.assertTrue(g.has_triggers(f2))
        deps = list(g.get_dependent_fields(f2))
        self.assertIn(t2, deps)

    def test_set_triggers_publishes_atomically(self) -> None:
        from collections import defaultdict

        g = ModelGraph()
        f_old, t_old = _field("price"), _field("total")
        g.add_trigger(f_old, (), [t_old])
        g.get_field_trigger_tree(f_old)
        self.assertTrue(g._trigger_trees)

        f_new, t_new = _field("name"), _field("display_name")
        staged: defaultdict = defaultdict(lambda: defaultdict(list))
        staged[f_new][()].append(t_new)

        g.set_triggers(staged)
        self.assertIs(g._triggers, staged)
        self.assertFalse(g._trigger_trees)
        self.assertFalse(g._modifying_relations)
        self.assertFalse(g.has_triggers(f_old))
        self.assertTrue(g.has_triggers(f_new))
        self.assertIn(t_new, list(g.get_dependent_fields(f_new)))

    def test_incremental_build_workflow(self) -> None:
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

        g.add_trigger(price, (), [total])
        g.add_trigger(qty, (), [total])
        g.add_trigger(price, (partner_id,), [partner_total])

        tree = g.get_trigger_tree([price])
        self.assertIn(total, tree.root)
        self.assertIn(partner_id, tree)
        self.assertIn(partner_total, tree[partner_id].root)

        tree2 = g.get_trigger_tree([qty])
        self.assertIn(total, tree2.root)

    def test_reset_triggers_preserves_field_metadata(self) -> None:
        g = ModelGraph()
        f = _field("price")
        g._depends[f] = ("dep",)
        g._inverses[f] = ("inv",)
        g.add_trigger(f, (), [_field("total")])

        g.reset_triggers()
        self.assertFalse(g.has_triggers(f))
        self.assertEqual(g._depends[f], ("dep",))
        self.assertEqual(g._inverses[f], ("inv",))


class TestModelGraphQueries(unittest.TestCase):
    def setUp(self) -> None:
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

        self.g.add_trigger(self.price, (), [self.total])
        self.g.add_trigger(self.price, (self.partner_id,), [self.partner_total])

    def test_get_trigger_tree_direct(self) -> None:
        tree = self.g.get_trigger_tree([self.price])
        self.assertIn(self.total, tree.root)

    def test_get_trigger_tree_with_path(self) -> None:
        tree = self.g.get_trigger_tree([self.price])
        self.assertIn(self.partner_id, tree)
        subtree = tree[self.partner_id]
        self.assertIn(self.partner_total, subtree.root)

    def test_get_trigger_tree_caches(self) -> None:
        tree1 = self.g.get_field_trigger_tree(self.price)
        tree2 = self.g.get_field_trigger_tree(self.price)
        self.assertIs(tree1, tree2)

    def test_get_trigger_tree_no_triggers(self) -> None:
        tree = self.g.get_trigger_tree([_field("unknown")])
        self.assertFalse(tree)

    def test_get_trigger_tree_select_filter(self) -> None:
        tree = self.g.get_trigger_tree(
            [self.price],
            select=lambda f: f is self.total,
        )
        self.assertIn(self.total, tree.root)
        if self.partner_id in tree:
            subtree = tree[self.partner_id]
            self.assertNotIn(self.partner_total, subtree.root)

    def test_get_dependent_fields(self) -> None:
        deps = list(self.g.get_dependent_fields(self.price))
        self.assertIn(self.total, deps)
        self.assertIn(self.partner_total, deps)

    def test_get_dependent_fields_no_triggers(self) -> None:
        deps = list(self.g.get_dependent_fields(_field("unknown")))
        self.assertEqual(deps, [])

    def test_clear_caches(self) -> None:
        self.g.get_field_trigger_tree(self.price)
        self.assertTrue(self.g._trigger_trees)
        self.g.clear_caches()
        self.assertFalse(self.g._trigger_trees)

    def test_has_triggers(self) -> None:
        self.assertTrue(self.g.has_triggers(self.price))
        self.assertFalse(self.g.has_triggers(self.total))


class TestIsModifyingRelations(unittest.TestCase):
    def test_relational_field_no_path_traverses_it(self) -> None:
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        dep = _field("partner_name", is_stored_computed=True)
        g.add_trigger(m2o, (), [dep])
        self.assertFalse(g.is_modifying_relations(m2o))

    def test_relational_field_a_path_traverses(self) -> None:
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        dep = _field("partner_name", is_stored_computed=True)
        g.add_trigger(m2o, (), [dep])
        g.add_trigger(_field("name"), (m2o,), [dep])
        self.assertTrue(g.is_modifying_relations(m2o))

    def test_scalar_field_no_relational_deps(self) -> None:
        g = ModelGraph()
        scalar = _field("name")
        dep = _field("display_name", is_stored_computed=True)
        g.add_trigger(scalar, (), [dep])
        self.assertFalse(g.is_modifying_relations(scalar))

    def test_scalar_with_untraversed_relational_dependent(self) -> None:
        g = ModelGraph()
        scalar = _field("code")
        dep = _field("ref_id", relational=True)
        g.add_trigger(scalar, (), [dep])
        self.assertFalse(g.is_modifying_relations(scalar))

    def test_scalar_with_traversed_relational_dependent(self) -> None:
        g = ModelGraph()
        scalar = _field("code")
        dep = _field("ref_id", relational=True)
        g.add_trigger(scalar, (), [dep])
        g.add_trigger(_field("label"), (dep,), [_field("ref_label")])
        self.assertTrue(g.is_modifying_relations(scalar))

    def test_field_with_inverses(self) -> None:
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        o2m = _field("order_ids", type_="one2many", relational=True)
        dep = _field("total")
        g.add_trigger(m2o, (), [dep])
        g._inverses[m2o] = (o2m,)
        self.assertTrue(g.is_modifying_relations(m2o))

    def test_scalar_field_with_inverses(self) -> None:
        g = ModelGraph()
        res_id = _field("res_id", type_="many2one_reference")
        o2m = _field("attachment_ids", type_="one2many", relational=True)
        g.add_trigger(res_id, (), [_field("name", is_stored_computed=True)])
        g._inverses[res_id] = (o2m,)
        self.assertTrue(g.is_modifying_relations(res_id))

    def test_dependent_with_inverses(self) -> None:
        g = ModelGraph()
        scalar = _field("code")
        dep = _field("line_ids", type_="one2many", relational=True)
        g.add_trigger(scalar, (), [dep])
        g._inverses[dep] = (_field("parent_id", type_="many2one", relational=True),)
        self.assertTrue(g.is_modifying_relations(scalar))

    def test_no_triggers_is_false(self) -> None:
        g = ModelGraph()
        self.assertFalse(g.is_modifying_relations(_field("x")))

    def test_a_new_path_reopens_a_cached_false(self) -> None:
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        dep = _field("partner_name", is_stored_computed=True)
        g.add_trigger(m2o, (), [dep])
        self.assertFalse(g.is_modifying_relations(m2o))
        g.add_trigger(_field("name"), (m2o,), [dep])
        self.assertTrue(g.is_modifying_relations(m2o))

    def test_caches_result(self) -> None:
        g = ModelGraph()
        m2o = _field("partner_id", type_="many2one", relational=True)
        dep = _field("total")
        g.add_trigger(m2o, (), [dep])
        g._inverses[m2o] = (dep,)
        r1 = g.is_modifying_relations(m2o)
        r2 = g.is_modifying_relations(m2o)
        self.assertEqual(r1, r2)
        self.assertIn(m2o, g._modifying_relations)


class TestTransitiveTriggers(unittest.TestCase):
    def test_chain_a_to_b_to_c(self) -> None:
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

    def test_cycle_detection(self) -> None:
        g = ModelGraph()
        a = _field("a")
        b = _field("b")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [a])

        tree = g.get_field_trigger_tree(a)
        self.assertTrue(tree)

    def test_diamond_dependency(self) -> None:
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

    def test_deep_same_model_chain(self) -> None:
        g = ModelGraph()
        fields = [_field(f"f{i}") for i in range(200)]
        for i in range(len(fields) - 1):
            g.add_trigger(fields[i], (), [fields[i + 1]])

        tree = g.get_field_trigger_tree(fields[0])
        self.assertEqual(tree.root, tuple(fields[1:]))
        self.assertEqual(len(tree.root), len(set(tree.root)))


def _naive_trigger_tree(graph: ModelGraph, field) -> TriggerTree:
    triggers = graph._triggers
    if field not in triggers:
        return TriggerTree()
    collected: dict[tuple, tuple[list, set]] = {}
    seen: set = set()

    def collect(f, prefix):
        if f in seen or f not in triggers:
            return
        seen.add(f)
        for path, targets in triggers[f].items():
            full_path = _concat_paths(prefix, path)
            entry = collected.get(full_path)
            if entry is None:
                entry = ([], set())
                collected[full_path] = entry
            root_list, root_set = entry
            for target in targets:
                if target not in root_set:
                    root_set.add(target)
                    root_list.append(target)
            for target in targets:
                collect(target, full_path)
        seen.discard(f)

    collect(field, ())
    tree = TriggerTree()
    for full_path, (root_list, _root_set) in collected.items():
        current = tree
        for label in full_path:
            current = current.increase(label)
        current.root = tuple(root_list)
    return tree


def _as_plain(tree: TriggerTree):
    return (tree.root, [(label, _as_plain(sub)) for label, sub in tree.items()])


def _build_diamond(depth: int, labelled: bool = False) -> tuple[ModelGraph, MockField]:
    g = ModelGraph()
    f_fields = [_field(f"F{i}") for i in range(depth + 1)]
    for i in range(depth):
        a = _field(f"A{i + 1}")
        b = _field(f"B{i + 1}")
        path = (_field(f"x{i}"),) if labelled else ()
        g.add_trigger(f_fields[i], (), [a, b])
        g.add_trigger(a, path, [f_fields[i + 1]])
        g.add_trigger(b, path, [f_fields[i + 1]])
    return g, f_fields[0]


class TestTriggerTreeMemoization(unittest.TestCase):
    def assert_matches_naive(self, graph: ModelGraph, field) -> None:
        expected = _as_plain(_naive_trigger_tree(graph, field))
        actual = _as_plain(graph.get_field_trigger_tree(field))
        self.assertEqual(actual, expected)

    def test_small_diamond_equivalence_empty_paths(self) -> None:
        graph, root = _build_diamond(4)
        self.assert_matches_naive(graph, root)

    def test_small_diamond_equivalence_labelled_paths(self) -> None:
        graph, root = _build_diamond(4, labelled=True)
        self.assert_matches_naive(graph, root)

    def test_shared_target_under_different_prefixes(self) -> None:
        g = ModelGraph()
        f = _field("f")
        a, b, t, u = _field("a"), _field("b"), _field("t"), _field("u")
        x, y = _field("x"), _field("y")
        g.add_trigger(f, (), [a, b])
        g.add_trigger(a, (x,), [t])
        g.add_trigger(b, (y,), [t])
        g.add_trigger(t, (), [u])

        tree = g.get_field_trigger_tree(f)
        self.assertEqual(tree[x].root, (t, u))
        self.assertEqual(tree[y].root, (t, u))
        self.assert_matches_naive(g, f)

    def test_cycle_equivalence(self) -> None:
        g = ModelGraph()
        a, b, c = _field("a"), _field("b"), _field("c")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [a, c])
        g.add_trigger(c, (), [a])
        for root in (a, b, c):
            with self.subTest(root=root):
                g.clear_caches()
                self.assert_matches_naive(g, root)

    def test_self_loop_equivalence(self) -> None:
        g = ModelGraph()
        a, b = _field("a"), _field("b")
        g.add_trigger(a, (), [a, b])
        g.add_trigger(b, (), [b])
        self.assert_matches_naive(g, a)

    def test_diamond_reaching_into_cycle_equivalence(self) -> None:
        g = ModelGraph()
        f, a, b, t = _field("f"), _field("a"), _field("b"), _field("t")
        p, q = _field("p"), _field("q")
        g.add_trigger(f, (), [a, b])
        g.add_trigger(a, (p,), [t])
        g.add_trigger(b, (p,), [t])
        g.add_trigger(t, (q,), [f])
        g.add_trigger(f, (q,), [t])
        self.assert_matches_naive(g, f)
        g.clear_caches()
        self.assert_matches_naive(g, t)

    def test_m2o_o2m_cancellation_with_memo_reuse(self) -> None:
        parent_id = _field(
            "parent_id",
            model="child",
            type_="many2one",
            relational=True,
            comodel_name="parent",
        )
        child_ids = _field(
            "child_ids",
            model="parent",
            type_="one2many",
            relational=True,
            comodel_name="child",
            inverse_name="parent_id",
        )
        g = ModelGraph()
        f, a, b = _field("f"), _field("a"), _field("b")
        t1, t2 = _field("t1"), _field("t2")
        g.add_trigger(f, (), [a, b])
        g.add_trigger(a, (parent_id,), [t1])
        g.add_trigger(b, (parent_id,), [t1])
        g.add_trigger(t1, (child_ids,), [t2])

        tree = g.get_field_trigger_tree(f)
        self.assertEqual(tree.root, (a, b, t2))
        self.assertEqual(tree[parent_id].root, (t1,))
        self.assert_matches_naive(g, f)

    def test_deep_diamond_is_not_exponential(self) -> None:
        import time

        for labelled in (False, True):
            with self.subTest(labelled=labelled):
                graph, root = _build_diamond(22, labelled=labelled)
                start = time.perf_counter()
                tree = graph.get_field_trigger_tree(root)
                elapsed = time.perf_counter() - start
                self.assertTrue(tree)
                self.assertLess(
                    elapsed,
                    1.0,
                    f"diamond depth 22 took {elapsed:.3f}s — "
                    "recursion memoization regressed",
                )

    def test_deep_diamond_matches_naive_at_tractable_depth(self) -> None:
        for labelled in (False, True):
            with self.subTest(labelled=labelled):
                graph, root = _build_diamond(12, labelled=labelled)
                self.assert_matches_naive(graph, root)


class TestConcatPaths(unittest.TestCase):
    def test_simple_concat(self) -> None:
        a = _field("a")
        b = _field("b")
        result = _concat_paths((a,), (b,))
        self.assertEqual(result, (a, b))

    def test_empty_concat(self) -> None:
        self.assertEqual(_concat_paths((), ()), ())
        a = _field("a")
        self.assertEqual(_concat_paths((a,), ()), (a,))
        self.assertEqual(_concat_paths((), (a,)), (a,))

    def test_m2o_o2m_cancellation(self) -> None:
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
        result = _concat_paths((m2o,), (o2m,))
        self.assertEqual(result, ())

    def test_m2o_o2m_no_cancel_if_different_inverse(self) -> None:
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
        result = _concat_paths((m2o,), (o2m,))
        self.assertEqual(result, (m2o, o2m))

    def test_m2o_o2m_no_cancel_if_different_models(self) -> None:
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
        result = _concat_paths((m2o,), (o2m,))
        self.assertEqual(result, (m2o, o2m))


class TestDiscardFields(unittest.TestCase):
    def test_discard_from_triggers(self) -> None:
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.discard_fields([f])
        self.assertFalse(g.has_triggers(f))

    def test_discard_from_triggers_as_target(self) -> None:
        g = ModelGraph()
        dep = _field("price")
        gone = _field("total")
        kept = _field("subtotal")
        g.add_trigger(dep, (), [gone, kept])
        g.discard_fields([gone])
        tree = g.get_trigger_tree([dep])
        self.assertIn(kept, tree.root)
        self.assertNotIn(gone, tree.root)

    def test_discard_target_removes_emptied_dep(self) -> None:
        g = ModelGraph()
        dep = _field("price")
        gone = _field("total")
        g.add_trigger(dep, (), [gone])
        g.discard_fields([gone])
        self.assertFalse(g.has_triggers(dep))

    def test_discard_from_depends(self) -> None:
        g = ModelGraph()
        f = _field("total")
        g._depends[f] = ("price",)
        g.discard_fields([f])
        self.assertNotIn(f, g.field_depends)

    def test_discard_from_inverses_key(self) -> None:
        g = ModelGraph()
        f = _field("partner_id")
        inv = _field("order_ids")
        g._inverses[f] = (inv,)
        g.discard_fields([f])
        self.assertNotIn(f, g.field_inverses)

    def test_discard_from_inverses_value(self) -> None:
        g = ModelGraph()
        f = _field("partner_id")
        inv = _field("order_ids")
        g._inverses[f] = (inv,)
        g.discard_fields([inv])
        self.assertNotIn(f, g.field_inverses)

    def test_discard_clears_caches(self) -> None:
        g = ModelGraph()
        f = _field("price")
        t = _field("total")
        g.add_trigger(f, (), [t])
        g.get_field_trigger_tree(f)
        g.discard_fields([f])
        self.assertFalse(g._trigger_trees)


class TestCollector(unittest.TestCase):
    def test_missing_key_returns_empty_tuple(self) -> None:
        c: _Collector = _Collector()
        self.assertEqual(c["nonexistent"], ())

    def test_setitem_stores_tuple(self) -> None:
        c: _Collector = _Collector()
        c["key"] = [1, 2, 3]
        self.assertEqual(c["key"], (1, 2, 3))

    def test_setitem_removes_on_empty(self) -> None:
        c: _Collector = _Collector()
        c["key"] = [1, 2]
        c["key"] = []
        self.assertNotIn("key", c)

    def test_add_appends(self) -> None:
        c: _Collector = _Collector()
        c.add("key", "a")
        c.add("key", "b")
        self.assertEqual(c["key"], ("a", "b"))

    def test_add_deduplicates(self) -> None:
        c: _Collector = _Collector()
        c.add("key", "a")
        c.add("key", "a")
        self.assertEqual(c["key"], ("a",))

    def test_discard_keys_and_values(self) -> None:
        c: _Collector = _Collector()
        c["a"] = ("x", "y")
        c["b"] = ("x", "z")
        c["x"] = ("w",)
        c.discard_keys_and_values({"x"})
        self.assertNotIn("x", c)
        self.assertEqual(c["a"], ("y",))
        self.assertEqual(c["b"], ("z",))

    def test_discard_removes_empty_after_filter(self) -> None:
        c: _Collector = _Collector()
        c["a"] = ("x",)
        c.discard_keys_and_values({"x"})
        self.assertNotIn("a", c)

    def test_pop_works(self) -> None:
        c: _Collector = _Collector()
        c["key"] = ("val",)
        result = c.pop("key", None)
        self.assertEqual(result, ("val",))
        self.assertNotIn("key", c)

    def test_clear_empties(self) -> None:
        c: _Collector = _Collector()
        c["a"] = ("x",)
        c["b"] = ("y",)
        c.clear()
        self.assertEqual(len(c), 0)

    def test_get_agrees_with_getitem_on_a_missing_key(self) -> None:
        c: _Collector = _Collector()
        self.assertEqual(c.get("missing"), ())
        self.assertEqual(c["missing"], ())
        self.assertEqual(c.get("missing", "default"), "default")
        self.assertIsNone(c.get("missing", None))

    def test_pop_agrees_with_getitem_too(self) -> None:
        c: _Collector = _Collector()
        self.assertEqual(c.pop("missing"), ())
        self.assertEqual(c.pop("missing", "default"), "default")
        c["a"] = ("x",)
        self.assertEqual(c.pop("a"), ("x",))
        self.assertNotIn("a", c)

    def test_iteration(self) -> None:
        c: _Collector = _Collector()
        c["a"] = ("x",)
        c["b"] = ("y",)
        self.assertEqual(set(c), {"a", "b"})


class TestDataOwnership(unittest.TestCase):
    def test_inverses_are_collector(self) -> None:
        g = ModelGraph()
        self.assertIsInstance(g._inverses, _Collector)

    def test_depends_are_collector(self) -> None:
        g = ModelGraph()
        self.assertIsInstance(g._depends, _Collector)

    def test_depends_context_are_collector(self) -> None:
        g = ModelGraph()
        self.assertIsInstance(g._depends_context, _Collector)

    def test_properties_delegate_to_internals(self) -> None:
        g = ModelGraph()
        self.assertIs(g.field_inverses, g._inverses)
        self.assertIs(g.field_depends, g._depends)
        self.assertIs(g.field_depends_context, g._depends_context)
        self.assertIs(g.field_computed, g._computed)

    def test_external_assignment_updates_property(self) -> None:
        g = ModelGraph()
        new_inverses: _Collector = _Collector()
        f = _field("partner_id")
        inv = _field("order_ids")
        new_inverses[f] = (inv,)
        g._inverses = new_inverses
        self.assertIs(g.field_inverses, new_inverses)
        self.assertEqual(g.field_inverses[f], (inv,))

    def test_missing_key_returns_empty_tuple_via_property(self) -> None:
        g = ModelGraph()
        f = _field("nonexistent")
        self.assertEqual(g.field_inverses[f], ())
        self.assertEqual(g.field_depends[f], ())
        self.assertEqual(g.field_depends_context[f], ())


class TestRecomputeOrder(unittest.TestCase):
    def _stored_computed(self, name: str, model: str = "m") -> MockField:
        return _field(name, model=model, store=True, compute="_compute_" + name)

    def test_linear_chain_ordering(self) -> None:
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        c = self._stored_computed("c")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [c])

        order = g.recompute_order
        self.assertLess(order[a], order[b])
        self.assertLess(order[b], order[c])

    def test_diamond_dependencies(self) -> None:
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
        self.assertEqual(order[b], order[c])

    def test_cycle_gets_max_priority(self) -> None:
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [a])

        order = g.recompute_order
        self.assertIn(a, order)
        self.assertIn(b, order)
        self.assertEqual(order[a], order[b])

    def test_empty_graph(self) -> None:
        g = ModelGraph()
        order = g.recompute_order
        self.assertEqual(order, {})

    def test_non_stored_fields_excluded(self) -> None:
        g = ModelGraph()
        source = self._stored_computed("source")
        non_stored = _field("non_stored", compute="_compute_ns", store=False)
        g.add_trigger(source, (), [non_stored])

        order = g.recompute_order
        self.assertNotIn(non_stored, order)

    def test_non_computed_fields_excluded(self) -> None:
        g = ModelGraph()
        regular = _field("regular", store=True)
        target = self._stored_computed("target")
        g.add_trigger(regular, (), [target])

        order = g.recompute_order
        self.assertNotIn(regular, order)
        self.assertIn(target, order)

    def test_caching(self) -> None:
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        g.add_trigger(a, (), [b])

        order1 = g.recompute_order
        order2 = g.recompute_order
        self.assertIs(order1, order2)

    def test_cache_cleared_on_clear_caches(self) -> None:
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        g.add_trigger(a, (), [b])

        order1 = g.recompute_order
        g.clear_caches()
        order2 = g.recompute_order
        self.assertIsNot(order1, order2)
        self.assertEqual(order1, order2)

    def test_mixed_cycle_and_chain(self) -> None:
        g = ModelGraph()
        a = self._stored_computed("a")
        b = self._stored_computed("b")
        c = self._stored_computed("c")
        g.add_trigger(a, (), [b])
        g.add_trigger(b, (), [c])
        g.add_trigger(c, (), [b])

        order = g.recompute_order
        self.assertLess(order[a], order[b])
        self.assertLess(order[a], order[c])
        self.assertEqual(order[b], order[c])

    def test_plain_column_feeding_computed_chain(self) -> None:
        g = ModelGraph()
        column = _field("amount", store=True)
        total = self._stored_computed("total")
        grand_total = self._stored_computed("grand_total")
        g.add_trigger(column, (), [total])
        g.add_trigger(total, (), [grand_total])

        order = g.recompute_order
        self.assertNotIn(column, order)
        self.assertIn(total, order)
        self.assertIn(grand_total, order)
        self.assertLess(order[total], order[grand_total])

    def test_only_stored_computed_fields_in_order(self) -> None:
        g = ModelGraph()
        col = _field("col", store=True)
        non_stored = _field("ns", store=False, compute="_c")
        sc = self._stored_computed("sc")
        g.add_trigger(col, (), [sc, non_stored])
        g.add_trigger(non_stored, (), [sc])

        order = g.recompute_order
        self.assertEqual(set(order), {sc})


class TestModelGraphFreeze(unittest.TestCase):
    def _build_graph(self) -> ModelGraph:
        g = ModelGraph()
        price = _field("price")
        qty = _field("qty")
        partner_id = _field("partner_id", type_="many2one", relational=True)
        total = _field("total", is_stored_computed=True, store=True, compute="_c")
        partner_total = _field(
            "partner_total", is_stored_computed=True, store=True, compute="_c"
        )
        g.add_trigger(price, (), [total])
        g.add_trigger(qty, (), [total])
        g.add_trigger(price, (partner_id,), [partner_total])
        g.add_trigger(total, (), [partner_total])
        g._inverses[partner_id] = (partner_id,)
        return g

    def test_freeze_populates_all_caches(self) -> None:
        g = self._build_graph()
        self.assertEqual(g._trigger_trees, {})
        self.assertEqual(g._modifying_relations, {})
        self.assertIsNone(g._recompute_order)

        g.freeze()

        for field in g._triggers:
            self.assertIn(field, g._trigger_trees)
            self.assertIn(field, g._modifying_relations)
        self.assertIsNotNone(g._recompute_order)

    def test_queries_after_freeze_do_not_mutate(self) -> None:
        g = self._build_graph()
        g.freeze()

        trees_keys = set(g._trigger_trees)
        modrel_keys = set(g._modifying_relations)
        order_obj = g._recompute_order

        non_trigger = _field("unrelated")
        for field in list(g._triggers) + [non_trigger]:
            g.get_field_trigger_tree(field)
            g.is_modifying_relations(field)
            list(g.get_dependent_fields(field))
        g.get_trigger_tree(list(g._triggers) + [non_trigger])
        _ = g.recompute_order

        self.assertEqual(set(g._trigger_trees), trees_keys, "trigger-tree cache grew")
        self.assertEqual(
            set(g._modifying_relations), modrel_keys, "modifying-relations cache grew"
        )
        self.assertIs(g._recompute_order, order_obj, "recompute_order recomputed")

    def test_non_trigger_field_is_uncached(self) -> None:
        g = self._build_graph()
        g.freeze()
        x = _field("no_deps")
        self.assertFalse(g.is_modifying_relations(x))
        self.assertNotIn(x, g._modifying_relations)

    def test_freeze_is_idempotent(self) -> None:
        g = self._build_graph()
        g.freeze()
        trees, modrel, order = (
            dict(g._trigger_trees),
            dict(g._modifying_relations),
            dict(g.recompute_order),
        )
        g.freeze()
        self.assertEqual(set(g._trigger_trees), set(trees))
        self.assertEqual(g._modifying_relations, modrel)
        self.assertEqual(g.recompute_order, order)

    def test_freeze_preserves_query_results(self) -> None:
        eager = self._build_graph()
        eager.freeze()
        lazy = self._build_graph()
        for f_eager in eager._triggers:
            f_lazy = next(f for f in lazy._triggers if f.name == f_eager.name)
            self.assertEqual(
                eager.is_modifying_relations(f_eager),
                lazy.is_modifying_relations(f_lazy),
            )
            self.assertEqual(
                {d.name for d in eager.get_dependent_fields(f_eager)},
                {d.name for d in lazy.get_dependent_fields(f_lazy)},
            )
        self.assertEqual(
            {f.name: p for f, p in eager.recompute_order.items()},
            {f.name: p for f, p in lazy.recompute_order.items()},
        )


if __name__ == "__main__":
    unittest.main()
