import types
import typing
import unittest

from odoo.libs.collections import OrderedSet
from odoo.libs.datetime import utc
from odoo.orm.domain import optimizations
from odoo.orm.domain.ast import (
    MAX_DOMAIN_NESTING,
    Domain,
    DomainCondition,
    OptimizationLevel,
)
from odoo.orm.primitives import NewId
from odoo.tools import SQL

_UNSET = object()

if typing.TYPE_CHECKING:
    from odoo.orm.models import BaseModel


def _as_model(stub: object) -> BaseModel:
    return typing.cast("BaseModel", stub)


class _StubField:
    get_search_domain: typing.Any = None

    def _optimize_condition(self, condition, model, level):
        return condition

    _PREDICATES_BY_TYPE = {
        "is_many2one": frozenset({"many2one"}),
        "is_x2many": frozenset({"many2many", "one2many"}),
        "is_temporal": frozenset({"date", "datetime"}),
        "is_properties": frozenset({"properties"}),
        "is_one2many": frozenset({"one2many"}),
        "is_many2many": frozenset({"many2many"}),
        "is_many2one_reference": frozenset({"many2one_reference"}),
        "is_boolean": frozenset({"boolean"}),
        "is_integer": frozenset({"integer"}),
        "is_monetary": frozenset({"monetary"}),
        "is_date": frozenset({"date"}),
        "is_datetime": frozenset({"datetime"}),
        "is_html": frozenset({"html"}),
        "is_binary": frozenset({"binary"}),
    }
    """Mirrors ``PREDICATE_TYPES`` in ``orm/tests/test_field_predicates.py``.

    A second copy, and deliberately so: this suite is DB-free and cannot import
    ``odoo.orm.fields`` -- ``fields/base.py`` imports ``odoo.orm.domain``, which
    is the package under test here, so asking the real classes would be a cycle.
    ``TestTheDomainStubKeepsUp`` over there reads this table with ``ast`` and
    fails when the two disagree, which is how the copy is kept honest.
    """

    _FALSY_BY_TYPE = {
        "char": "",
        "text": "",
        "html": "",
        "integer": 0,
        "float": 0.0,
        "monetary": 0.0,
        "boolean": False,
    }

    def __init__(
        self,
        name,
        ftype="integer",
        *,
        relational=False,
        comodel=None,
        search=None,
        falsy_value=_UNSET,
    ):
        self.name = name
        self.type = ftype
        self.relational = relational
        self.model_name = "m"
        self.comodel_name = comodel
        self.store = True
        self.required = False
        self.inherited = False
        self.related = None
        self.company_dependent = False
        self.falsy_value = (
            self._FALSY_BY_TYPE.get(ftype) if falsy_value is _UNSET else falsy_value
        )
        self.search = search
        for predicate, holds_for in self._PREDICATES_BY_TYPE.items():
            setattr(self, predicate, ftype in holds_for)


class _StubEnv:
    tz = utc
    su = False
    registry: typing.Any = None

    def __init__(self, model):
        self._model = model

    def __getitem__(self, model_name):
        return self._model


class _StubModel:
    _name = "m"
    _auto = True
    _ids: tuple = ()

    def _check_field_access(self, field, operation):
        pass

    def __init__(self):
        self._fields = {
            "a": _StubField("a"),
            "b": _StubField("b"),
            "c": _StubField("c"),
            "name": _StubField("name", "char"),
            "ok": _StubField("ok", "boolean"),
            "d": _StubField("d", "date"),
            "dt": _StubField("dt", "datetime"),
            "rel": _StubField("rel", "many2one", relational=True, comodel="m"),
        }
        self.env = _StubEnv(self)


def _opt(domain):
    return list(domain.optimize(_as_model(_StubModel())))


class TestScalarNormalisation(unittest.TestCase):
    def test_eq_becomes_in(self):
        self.assertEqual(_opt(Domain("a", "=", 1)), [("a", "in", [1])])

    def test_neq_becomes_not_in(self):
        self.assertEqual(_opt(Domain("a", "!=", 1)), [("a", "not in", [1])])

    def test_in_singleton_stays_in(self):
        self.assertEqual(_opt(Domain("a", "in", [1])), [("a", "in", [1])])

    def test_in_dedups_values(self):
        self.assertEqual(_opt(Domain("a", "in", [1, 2, 2, 1])), [("a", "in", [1, 2])])

    def test_like_is_left_alone(self):
        self.assertEqual(_opt(Domain("name", "like", "x")), [("name", "like", "x")])


class TestBooleanNormalisation(unittest.TestCase):
    def test_eq_true(self):
        self.assertEqual(_opt(Domain("ok", "=", True)), [("ok", "in", [True])])

    def test_neq_false_equals_eq_true(self):
        self.assertEqual(_opt(Domain("ok", "!=", False)), [("ok", "in", [True])])


class TestNegation(unittest.TestCase):
    def test_single_negation(self):
        self.assertEqual(_opt(~Domain("a", "=", 1)), [("a", "not in", [1])])

    def test_double_negation_cancels(self):
        self.assertEqual(_opt(~~Domain("a", "=", 1)), [("a", "in", [1])])


class TestSetMerging(unittest.TestCase):
    def test_or_unions(self):
        self.assertEqual(
            _opt(Domain("a", "in", [1, 2]) | Domain("a", "in", [2, 3])),
            [("a", "in", [1, 2, 3])],
        )

    def test_and_intersects(self):
        self.assertEqual(
            _opt(Domain("a", "in", [1, 2]) & Domain("a", "in", [2, 3])),
            [("a", "in", [2])],
        )

    def test_or_of_eqs_merges(self):
        self.assertEqual(
            _opt(Domain("a", "=", 1) | Domain("a", "=", 2)),
            [("a", "in", [1, 2])],
        )

    def test_and_of_equal_eqs_dedups(self):
        self.assertEqual(
            _opt(Domain("a", "=", 1) & Domain("a", "=", 1)),
            [("a", "in", [1])],
        )

    def test_contradiction_collapses_to_false(self):
        self.assertEqual(
            _opt(Domain("a", "=", 1) & Domain("a", "=", 2)),
            [(0, "=", 1)],
        )

    def test_distinct_field_inequalities_not_merged(self):
        canonical = ["&", ("a", "<", 3), ("a", "<", 5)]
        self.assertEqual(_opt(Domain("a", "<", 5) & Domain("a", "<", 3)), canonical)
        self.assertEqual(_opt(Domain("a", "<", 3) & Domain("a", "<", 5)), canonical)


class TestFalsyValueSetMerging(unittest.TestCase):
    def test_eq_empty_string_canonicalizes_to_false(self):
        self.assertEqual(_opt(Domain("name", "=", "")), [("name", "in", [False])])
        self.assertEqual(_opt(Domain("name", "=", False)), [("name", "in", [False])])

    def test_neq_empty_string_canonicalizes_to_false(self):
        self.assertEqual(_opt(Domain("name", "!=", "")), [("name", "not in", [False])])
        self.assertEqual(
            _opt(Domain("name", "!=", False)), [("name", "not in", [False])]
        )

    def test_or_of_neq_empty_and_neq_false_is_not_tautology(self):
        self.assertEqual(
            _opt(Domain("name", "!=", "") | Domain("name", "!=", False)),
            [("name", "not in", [False])],
        )

    def test_and_of_eq_empty_and_neq_false_is_false(self):
        self.assertEqual(
            _opt(Domain("name", "=", "") & Domain("name", "!=", False)),
            [(0, "=", 1)],
        )

    def test_in_set_mixed_empty_and_value(self):
        self.assertEqual(
            _opt(Domain("name", "in", ["a", ""])), [("name", "in", ["a", False])]
        )
        self.assertEqual(
            _opt(Domain("name", "in", ["a", False])), [("name", "in", ["a", False])]
        )


class TestBooleanAbsorption(unittest.TestCase):
    def test_true_and_x_is_x(self):
        self.assertEqual(_opt(Domain.TRUE & Domain("a", "=", 1)), [("a", "in", [1])])

    def test_false_and_x_is_false(self):
        self.assertEqual(_opt(Domain.FALSE & Domain("a", "=", 1)), [(0, "=", 1)])

    def test_true_or_x_is_true(self):
        self.assertEqual(_opt(Domain.TRUE | Domain("a", "=", 1)), [(1, "=", 1)])

    def test_false_or_x_is_x(self):
        self.assertEqual(_opt(Domain.FALSE | Domain("a", "=", 1)), [("a", "in", [1])])


class TestNaryFlattening(unittest.TestCase):
    def test_nested_and_flattens(self):
        d = (Domain("a", "=", 1) & Domain("b", "=", 2)) & Domain("c", "=", 3)
        self.assertEqual(
            _opt(d),
            ["&", "&", ("a", "in", [1]), ("b", "in", [2]), ("c", "in", [3])],
        )

    def test_nested_or_flattens(self):
        d = (Domain("a", "=", 1) | Domain("b", "=", 2)) | Domain("c", "=", 3)
        self.assertEqual(
            _opt(d),
            ["|", "|", ("a", "in", [1]), ("b", "in", [2]), ("c", "in", [3])],
        )


class TestOptimizerInvariants(unittest.TestCase):
    def test_optimize_does_not_mutate_original(self):
        original = Domain("a", "=", 1)
        original.optimize(_as_model(_StubModel()))
        self.assertEqual(list(original), [("a", "=", 1)])
        self.assertIs(original._opt_level, OptimizationLevel.NONE)

    def test_optimize_state_is_written_atomically(self):
        original = Domain("name", "like", "x")
        self.assertEqual(original._opt, (OptimizationLevel.NONE, None))
        out = original.optimize(_as_model(_StubModel()))
        self.assertIs(out, original)
        self.assertEqual(out._opt, (OptimizationLevel.BASIC, "m"))

    def test_optimize_is_idempotent(self):
        model = _StubModel()
        once = (Domain("a", "in", [1, 2]) | Domain("a", "in", [2, 3])).optimize(
            _as_model(model)
        )
        twice = once.optimize(_as_model(model))
        self.assertEqual(once, twice)
        self.assertIs(once._opt_level, twice._opt_level)

    def test_boolean_singletons_optimize_to_themselves(self):
        model = _StubModel()
        self.assertIs(Domain.TRUE.optimize(_as_model(model)), Domain.TRUE)
        self.assertIs(Domain.FALSE.optimize(_as_model(model)), Domain.FALSE)


class TestOptimizeModelScoping(unittest.TestCase):
    class _Field:
        def _optimize_condition(self, condition, model, level):
            return condition

        def __init__(self, name, ftype, model_name):
            self.name = name
            self.type = ftype
            self.relational = False
            self.model_name = model_name
            self.comodel_name = None
            self.store = True
            self.required = False
            self.inherited = False
            self.company_dependent = False
            self.falsy_value = _StubField._FALSY_BY_TYPE.get(ftype)

    class _Model:
        def __init__(self, name, field_types):
            self._name = name
            self._fields = {
                n: TestOptimizeModelScoping._Field(n, t, name)
                for n, t in field_types.items()
            }

    def test_reuse_across_models_recoerces_value(self):
        int_model = self._Model("int_model", {"a": "integer"})
        bool_model = self._Model("bool_model", {"a": "boolean"})
        opt = Domain("a", "=", 5).optimize(_as_model(int_model))
        self.assertEqual(list(opt), [("a", "in", [5])])
        reused = list(opt.optimize(_as_model(bool_model)))
        self.assertEqual(
            reused, list(Domain("a", "=", 5).optimize(_as_model(bool_model)))
        )
        self.assertEqual(reused, [("a", "in", [True])])

    def test_same_model_reuse_stays_idempotent(self):
        int_model = self._Model("int_model", {"a": "integer"})
        opt = Domain("a", "=", 5).optimize(_as_model(int_model))
        again = opt.optimize(_as_model(int_model))
        self.assertEqual(list(again), list(opt))
        self.assertIs(again._opt_level, opt._opt_level)
        self.assertEqual(opt._opt_model_name, "int_model")

    def test_reuse_across_models_leaves_shared_node_unmutated(self):
        int_model = self._Model("int_model", {"a": "integer"})
        bool_model = self._Model("bool_model", {"a": "boolean"})
        node = Domain("a", "=", 5).optimize(_as_model(int_model))
        stamp_before = node._opt
        self.assertEqual(node._opt_model_name, "int_model")

        reused = node.optimize(_as_model(bool_model))
        self.assertEqual(list(reused), [("a", "in", [True])])
        self.assertIsNot(reused, node)
        self.assertEqual(node._opt, stamp_before)
        self.assertEqual(node._opt_model_name, "int_model")
        self.assertIs(node.optimize(_as_model(int_model)), node)


class TestBooleanSearchableTautology(unittest.TestCase):
    def _model_with_searchable_bool(self, calls):
        model = _StubModel()
        field = _StubField("flag", "boolean", search=True)

        def get_search_domain(model, operator, value):
            calls.append((operator, sorted(value)))
            return [("a", "in", [1])]

        field.get_search_domain = get_search_domain
        model._fields["flag"] = field
        return model

    def test_in_true_false_collapses_before_search(self):
        calls: list = []
        model = self._model_with_searchable_bool(calls)
        result = Domain("flag", "in", [True, False]).optimize_full(_as_model(model))
        self.assertEqual(calls, [])
        self.assertEqual(list(result), [(1, "=", 1)])

    def test_single_value_still_uses_search(self):
        calls: list = []
        model = self._model_with_searchable_bool(calls)
        result = Domain("flag", "in", [True]).optimize_full(_as_model(model))
        self.assertEqual(calls, [("in", [True])])
        self.assertEqual(list(result), [("a", "in", [1])])


class TestSubdomainNestingGuardCaseInsensitive(unittest.TestCase):
    @staticmethod
    def _nested_any(depth, op):
        subdomain: list[tuple] = [("a", "=", 1)]
        for _ in range(depth):
            subdomain = [("rel", op, subdomain)]
        return subdomain

    def _assert_rejected_at_parse(self, op):
        with self.assertRaisesRegex(ValueError, "nesting too deep"):
            Domain("rel", "any", self._nested_any(MAX_DOMAIN_NESTING + 10, op))

    def test_lowercase_any_deep_chain_rejected(self):
        self._assert_rejected_at_parse("any")

    def test_uppercase_any_deep_chain_rejected(self):
        self._assert_rejected_at_parse("ANY")

    def test_uppercase_not_any_deep_chain_rejected(self):
        self._assert_rejected_at_parse("NOT ANY")


class TestDeepDomainSurfacesValueError(unittest.TestCase):
    def test_operator_chain_is_rejected_at_construction(self):
        domain = Domain("a", "=", 1)
        with self.assertRaisesRegex(ValueError, "nesting too deep"):
            for _ in range(2000):
                domain = (domain & Domain("a", "=", 2)) | Domain("a", "=", 3)

    def test_any_chain_is_rejected_at_construction(self):
        domain = Domain("a", "=", 1)
        with self.assertRaisesRegex(ValueError, "nesting too deep"):
            for _ in range(5000):
                domain = Domain("rel", "any", domain)

    def test_a_flat_or_of_many_conditions_is_not_deep(self):
        domain = Domain.OR(Domain("a", "=", i) for i in range(500))
        self.assertLessEqual(domain._depth, 2)

    def test_every_node_kind_carries_a_depth(self):
        from odoo.orm.domain.ast import DomainCustom, DomainNot

        custom = DomainCustom(lambda model, alias, query: SQL("TRUE"))
        self.assertEqual(custom._depth, 1)
        self.assertEqual((custom & Domain("a", "=", 1))._depth, 2)
        self.assertEqual(Domain.TRUE._depth, 1)
        self.assertEqual(DomainNot(Domain("a", "=", 1))._depth, 2)


class TestConditionHashHonoursEquality(unittest.TestCase):
    def test_reordered_list_values_hash_together(self):
        a = DomainCondition("f", "in", [1, 2])
        b = DomainCondition("f", "in", [2, 1])
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(len({a, b}), 1)

    def test_reordered_tuple_values_hash_together(self):
        a = DomainCondition("f", "in", (1, 2))
        b = DomainCondition("f", "in", (2, 1))
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(len({a, b}), 1)

    def test_unhashable_members_still_fall_back(self):
        a = DomainCondition("f", "in", [[1], [2]])
        self.assertEqual(hash(a), hash(DomainCondition("f", "in", [[2], [1]])))


class TestPredicateHonoursOptModel(unittest.TestCase):
    def test_optimized_for_one_model_reoptimizes_for_another(self):
        m = _as_model(_StubModel())
        domain = Domain("d", "in", ["2024-01-05"])._optimize(
            m, OptimizationLevel.DYNAMIC_VALUES
        )
        self.assertEqual(domain._opt[1], "m")

        other = _StubModel()
        other._name = "m2"
        again = domain._predicate_optimized(_as_model(other))
        assert again is not None
        self.assertEqual(again._opt[1], "m2")

    def test_optimized_for_the_same_model_is_reused(self):
        m = _as_model(_StubModel())
        domain = Domain("d", "in", ["2024-01-05"])._optimize(
            m, OptimizationLevel.DYNAMIC_VALUES
        )
        self.assertIsNone(domain._predicate_optimized(m))


class TestMergedSetCanonicalOrder(unittest.TestCase):
    def test_or_union_is_value_sorted(self):
        canonical = [("a", "in", [1, 2, 3])]
        self.assertEqual(
            _opt(Domain("a", "in", [3, 1]) | Domain("a", "in", [2])), canonical
        )
        self.assertEqual(
            _opt(Domain("a", "in", [2]) | Domain("a", "in", [3, 1])), canonical
        )

    def test_and_intersection_is_value_sorted(self):
        self.assertEqual(
            _opt(Domain("a", "in", [2, 1, 3]) & Domain("a", "in", [3, 1, 2])),
            [("a", "in", [1, 2, 3])],
        )

    def test_and_not_in_union_is_value_sorted(self):
        self.assertEqual(
            _opt(Domain("a", "not in", [5, 4]) & Domain("a", "not in", [6])),
            [("a", "not in", [4, 5, 6])],
        )

    def test_unmerged_set_keeps_caller_order(self):
        self.assertEqual(_opt(Domain("a", "in", [3, 1])), [("a", "in", [3, 1])])

    def test_confluence_across_sibling_subtrees(self):
        model = _StubModel()

        def sub(values):
            domain = Domain("ok", "=", True)
            for v in values:
                domain |= Domain("a", "in", [v])
            return domain

        other = Domain("b", "in", [7]) | Domain("name", "like", "z")
        d1 = (sub([1, 2]) & other).optimize(_as_model(model))
        d2 = (other & sub([2, 1])).optimize(_as_model(model))
        self.assertEqual(d1, d2)
        self.assertEqual(list(d1), list(d2))


class _HierarchyStubModel(_StubModel):
    _parent_name = "rel"
    _parent_store = False
    ids: list = []

    def __init__(self):
        super().__init__()
        self._fields["id"] = _StubField("id")

    def sudo(self):
        return self

    def with_context(self, **kwargs):
        return self

    def search(self, domain, order=None):
        self.searched = True
        return self

    def browse(self, ids=()):
        return self

    def check_access(self, operation):
        self.access_checked = operation


class TestHierarchyBooleanValues(unittest.TestCase):
    def test_scalar_true_raises_clean_value_error(self):
        for op in ("child_of", "parent_of"):
            with self.assertRaisesRegex(ValueError, "not a valid hierarchy value"):
                optimizations._optimize_hierarchy(
                    DomainCondition("id", op, True), _HierarchyStubModel()
                )

    def test_scalar_false_collapses_to_false_domain(self):
        for op in ("child_of", "parent_of"):
            result = optimizations._optimize_hierarchy(
                DomainCondition("id", op, False), _HierarchyStubModel()
            )
            self.assertIs(result, Domain.FALSE)

    def test_collection_true_raises_clean_value_error(self):
        with self.assertRaisesRegex(ValueError, "not a valid hierarchy value"):
            optimizations._optimize_hierarchy(
                DomainCondition("id", "child_of", [True, 3]), _HierarchyStubModel()
            )

    def test_collection_false_is_dropped(self):
        result = optimizations._optimize_hierarchy(
            DomainCondition("id", "child_of", [False]), _HierarchyStubModel()
        )
        self.assertIs(result, Domain.FALSE)

    def test_integer_roots_skip_the_search_but_keep_the_read_check(self):
        model = _HierarchyStubModel()
        optimizations._optimize_hierarchy(
            DomainCondition("id", "child_of", [False]), model
        )
        self.assertFalse(hasattr(model, "searched"))
        self.assertEqual(model.access_checked, "read")
        model = _HierarchyStubModel()
        model.env.su = True
        optimizations._optimize_hierarchy(
            DomainCondition("id", "child_of", [False]), model
        )
        self.assertFalse(hasattr(model, "access_checked"))


class TestInRequiredPredicateSafety(unittest.TestCase):
    def _model(self, ids):
        model = _StubModel()
        field = _StubField("rel", "many2one", relational=True, comodel="m")
        field.required = True
        model._fields["rel"] = field
        model._ids = ids
        model.env.registry = types.SimpleNamespace(not_null_fields={field})
        return model

    def test_persisted_binding_strips_and_keeps_fallback(self):
        condition = DomainCondition("rel", "in", OrderedSet([False, 5]))
        result = optimizations._optimize_in_required(condition, self._model((1, 2)))
        self.assertIsNot(result, condition)
        self.assertEqual(list(result.value), [5])
        self.assertIs(result._predicate_fallback, condition)

    def test_unbound_model_strips_vacuously(self):
        condition = DomainCondition("rel", "in", OrderedSet([False, 5]))
        result = optimizations._optimize_in_required(condition, self._model(()))
        self.assertEqual(list(result.value), [5])
        self.assertIs(result._predicate_fallback, condition)

    def test_newid_binding_disables_the_strip(self):
        condition = DomainCondition("rel", "in", OrderedSet([False, 5]))
        for new_id in (NewId(), NewId(origin=7)):
            result = optimizations._optimize_in_required(
                condition, self._model((1, new_id))
            )
            self.assertIs(result, condition)

    def test_not_required_field_is_untouched(self):
        condition = DomainCondition("rel", "in", OrderedSet([False, 5]))
        model = self._model((1, 2))
        model._fields["rel"].required = False
        model.env.registry.not_null_fields = set()
        self.assertIs(optimizations._optimize_in_required(condition, model), condition)


class TestBasicPassesSkipNoOpRebuild(unittest.TestCase):
    def test_boolean_all_bool_values_is_same_object(self):
        for values in ([True], [True, False]):
            condition = DomainCondition("ok", "in", OrderedSet(values))
            result = optimizations._optimize_boolean_in(condition, _StubModel())
            self.assertIs(result, condition)

    def test_boolean_single_false_still_normalizes(self):
        condition = DomainCondition("ok", "in", OrderedSet([False]))
        result = optimizations._optimize_boolean_in(condition, _StubModel())
        self.assertIsNot(result, condition)
        self.assertEqual(result.operator, "not in")
        self.assertEqual(list(result.value), [True])

    def test_boolean_coercion_still_rebuilds(self):
        condition = DomainCondition("ok", "in", OrderedSet([1, "false"]))
        result = optimizations._optimize_boolean_in(condition, _StubModel())
        self.assertIsNot(result, condition)
        self.assertEqual(set(result.value), {True, False})
