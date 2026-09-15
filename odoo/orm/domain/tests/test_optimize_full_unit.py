import types
import typing
import unittest

from odoo.exceptions import UserError
from odoo.libs.collections import OrderedSet
from odoo.orm.domain import optimizations
from odoo.orm.domain.ast import Domain, DomainCondition


class _StubField:
    get_search_domain: typing.Any = None

    def _optimize_condition(self, condition, model, level):
        return condition

    def __init__(self, name, ftype="integer", *, relational=False, comodel=None):
        self.name = name
        self.type = ftype
        self.relational = relational
        self.model_name = "m"
        self.comodel_name = comodel
        self.store = True
        self.required = False
        self.inherited = False
        self.company_dependent = False
        self.falsy_value = None
        self.search = None
        self.bypass_search_access = False


class _StubEnv:
    su = True
    registry: typing.Any = None

    def __init__(self, model):
        self._model = model

    def __getitem__(self, model_name):
        return self._model


class _StubModel:
    _name = "m"
    _ids: tuple = ()
    _auto = True

    def __init__(self):
        self._fields = {
            "a": _StubField("a"),
            "rel": _StubField("rel", "many2one", relational=True, comodel="m"),
        }
        self.env = _StubEnv(self)

    def sudo(self):
        return self


class TestAnyWithRights(unittest.TestCase):
    SUB = Domain("a", "=", 7)

    def _model(self, *, su, bypass):
        model = _StubModel()
        model.env.su = su
        model._fields["rel"].bypass_search_access = bypass
        return model

    def test_superuser_escalates_any(self):
        condition = DomainCondition("rel", "any", self.SUB)
        result = optimizations._optimize_any_with_rights(
            condition, self._model(su=True, bypass=False)
        )
        self.assertEqual(result.operator, "any!")
        self.assertIs(result.value, self.SUB)

    def test_superuser_escalates_not_any(self):
        condition = DomainCondition("rel", "not any", self.SUB)
        result = optimizations._optimize_any_with_rights(
            condition, self._model(su=True, bypass=False)
        )
        self.assertEqual(result.operator, "not any!")
        self.assertIs(result.value, self.SUB)

    def test_bypass_search_access_escalates_without_su(self):
        condition = DomainCondition("rel", "any", self.SUB)
        result = optimizations._optimize_any_with_rights(
            condition, self._model(su=False, bypass=True)
        )
        self.assertEqual(result.operator, "any!")

    def test_plain_user_keeps_record_rules(self):
        condition = DomainCondition("rel", "any", self.SUB)
        result = optimizations._optimize_any_with_rights(
            condition, self._model(su=False, bypass=False)
        )
        self.assertIs(result, condition)


class TestInRequiredRemainingGates(unittest.TestCase):
    def _model(self, field):
        model = _StubModel()
        model._fields[field.name] = field
        model._ids = (1, 2)
        model.env.registry = types.SimpleNamespace(not_null_fields={field})
        return model

    def test_no_false_in_value_returns_same_node(self):
        field = _StubField("rel", "many2one", relational=True, comodel="m")
        field.required = True
        condition = DomainCondition("rel", "in", OrderedSet([1, 2]))
        result = optimizations._optimize_in_required(condition, self._model(field))
        self.assertIs(result, condition)

    def test_id_field_strips_without_required_flag(self):
        field = _StubField("id")
        condition = DomainCondition("id", "in", OrderedSet([False, 5]))
        result = optimizations._optimize_in_required(condition, self._model(field))
        self.assertIsNot(result, condition)
        self.assertEqual(list(result.value), [5])
        self.assertIs(result._predicate_fallback, condition)

    def test_falsy_value_field_is_untouched(self):
        field = _StubField("code", "char")
        field.required = True
        field.falsy_value = ""
        condition = DomainCondition("code", "in", OrderedSet([False, "x"]))
        result = optimizations._optimize_in_required(condition, self._model(field))
        self.assertIs(result, condition)

    def test_field_without_not_null_constraint_is_untouched(self):
        field = _StubField("rel", "many2one", relational=True, comodel="m")
        field.required = True
        model = self._model(field)
        model.env.registry.not_null_fields = set()
        condition = DomainCondition("rel", "in", OrderedSet([False, 5]))
        result = optimizations._optimize_in_required(condition, model)
        self.assertIs(result, condition)


class TestFieldSearchMethodLadder(unittest.TestCase):
    def _field(self, handlers, calls):
        field = _StubField("f", "char")
        field.search = True

        def get_search_domain(model, op, value):
            calls.append(op)
            handler = handlers.get(op, NotImplemented)
            if isinstance(handler, Exception):
                raise handler
            if callable(handler):
                return handler(value)
            return handler

        field.get_search_domain = get_search_domain
        return field

    def _model(self, handlers, calls, name="f"):
        model = _StubModel()
        field = self._field(handlers, calls)
        field.name = name
        model._fields[name] = field
        return model

    def test_direct_result_is_parsed_as_internal_domain(self):
        calls: list = []
        model = self._model({"in": [("a", "=", 1)]}, calls)
        result = DomainCondition(
            "f", "in", OrderedSet([1])
        )._optimize_field_search_method(model)
        self.assertEqual(calls, ["in"])
        self.assertEqual(list(result), [("a", "=", 1)])

    def test_negative_operator_retries_with_positive_and_negates(self):
        calls: list = []
        model = self._model({"in": [("a", "=", 1)]}, calls)
        result = DomainCondition(
            "f", "not in", OrderedSet([1])
        )._optimize_field_search_method(model)
        self.assertEqual(calls, ["not in", "in"])
        self.assertEqual(list(result), [("a", "!=", 1)])

    def test_in_falls_back_to_or_of_equalities(self):
        calls: list = []
        model = self._model({"=": lambda v: [("a", "=", v)]}, calls)
        result = DomainCondition(
            "f", "in", OrderedSet([1, 2])
        )._optimize_field_search_method(model)
        self.assertEqual(calls, ["in", "not in", "=", "="])
        self.assertEqual(list(result), ["|", ("a", "=", 1), ("a", "=", 2)])

    def test_not_in_falls_back_to_and_of_inequalities(self):
        calls: list = []
        model = self._model({"!=": lambda v: [("a", "!=", v)]}, calls)
        result = DomainCondition(
            "f", "not in", OrderedSet([1, 2])
        )._optimize_field_search_method(model)
        self.assertEqual(calls, ["not in", "in", "!=", "!="])
        self.assertEqual(list(result), ["&", ("a", "!=", 1), ("a", "!=", 2)])

    def test_any_bang_falls_back_to_any_with_sudo_and_warns(self):
        calls: list = []
        sub_domain = Domain("a", "=", 3)
        handlers = {
            "any!": NotImplementedError("no any!"),
            "any": [("a", "=", 3)],
        }
        model = self._model(handlers, calls, name="g")
        model._fields["g"].type = "many2one"
        model._fields["g"].relational = True
        model._fields["g"].comodel_name = "m"
        with self.assertLogs("odoo.domains", level="WARNING") as captured:
            result = DomainCondition(
                "g", "any!", sub_domain
            )._optimize_field_search_method(model)
        self.assertEqual(calls, ["any!", "any"])
        self.assertEqual(list(result), [("a", "=", 3)])
        self.assertTrue(
            any("should implement any! operator" in msg for msg in captured.output),
            captured.output,
        )

    def test_original_exception_wins_over_later_fallback_failures(self):
        calls: list = []
        model = self._model({"in": NotImplementedError("boom-in")}, calls)
        with self.assertRaisesRegex(NotImplementedError, "boom-in"):
            DomainCondition("f", "in", OrderedSet([1]))._optimize_field_search_method(
                model
            )
        self.assertEqual(calls, ["in", "="])

    def test_nothing_implemented_raises_user_error(self):

        class _EnvWithMetaschema(_StubEnv):
            # the message names the model through the metaschema port, never
            # through env["ir.model"] itself
            registry = types.SimpleNamespace(
                metaschema=types.SimpleNamespace(
                    model_description=lambda env, model_name: "Model M"
                )
            )

            def _(self, source, **kwargs):
                return source % kwargs

        calls: list = []
        model = self._model({}, calls)
        model._fields["f"].get_description = lambda env, attrs: {"string": "Field F"}
        model.env = _EnvWithMetaschema(model)
        with self.assertRaisesRegex(
            UserError, r"Unsupported operator on Field F 'Model M' \(m\)"
        ):
            DomainCondition("f", "like", "x")._optimize_field_search_method(model)
        self.assertEqual(calls, ["like", "not like"])


class TestResetOptCopyUndoesAModelDependentRewrite(unittest.TestCase):
    def _model(self, field, *, not_null):
        model = _StubModel()
        model._fields[field.name] = field
        model._ids = (1, 2)
        model.env.registry = types.SimpleNamespace(
            not_null_fields={field} if not_null else set()
        )
        return model

    def test_the_strip_does_not_survive_into_another_model(self):
        strict_field = _StubField("rel", "many2one", relational=True, comodel="m")
        strict_field.required = True
        loose_field = _StubField("rel", "many2one", relational=True, comodel="m")
        loose_field.required = False

        original = DomainCondition("rel", "in", OrderedSet([False, 5]))
        stripped = optimizations._optimize_in_required(
            original, self._model(strict_field, not_null=True)
        )
        self.assertEqual(list(stripped.value), [5], "test premise: it strips")

        reset = stripped._reset_opt_copy()
        self.assertEqual(
            list(reset.value),
            [False, 5],
            "the reset copy kept the strip the previous model justified",
        )

    def test_the_reset_copy_drops_the_stale_fallback(self):
        field = _StubField("rel", "many2one", relational=True, comodel="m")
        field.required = True
        original = DomainCondition("rel", "in", OrderedSet([False, 5]))
        stripped = optimizations._optimize_in_required(
            original, self._model(field, not_null=True)
        )
        reset = stripped._reset_opt_copy()
        self.assertIsNone(
            getattr(reset, "_predicate_fallback", None),
            "a fallback naming the previous model's strip must not ride along",
        )

    def test_a_condition_with_no_fallback_is_copied_as_before(self):
        condition = DomainCondition("rel", "in", OrderedSet([1, 2]))
        reset = typing.cast("DomainCondition", condition._reset_opt_copy())
        self.assertIsNot(reset, condition)
        self.assertEqual(list(reset.value), [1, 2])
        self.assertEqual(reset.field_expr, "rel")
        self.assertEqual(reset.operator, "in")
