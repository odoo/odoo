from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.orm.domain.constants import INVERSE_OPERATOR, NEGATIVE_CONDITION_OPERATORS
from odoo.orm.model_test_env import model_test_env

_MOD = "test_orm_invariants"


class IScalars(models.Model):
    _name = "i.scalars"
    _module = _MOD
    _description = "All fast-path scalar types"

    f_bool = fields.Boolean()
    f_int = fields.Integer()
    f_float = fields.Float()
    f_char = fields.Char()
    f_text = fields.Text()
    f_sel = fields.Selection([("a", "A"), ("b", "B")])
    f_date = fields.Date()
    f_dt = fields.Datetime()
    f_money = fields.Monetary()
    currency_id = fields.Many2one("res.currency")


class IAlpha(models.Model):
    _name = "i.alpha"
    _module = _MOD
    _description = "Non-stored searchable field"

    ref = fields.Char(compute="_compute_ref", search="_search_ref", store=False)

    def _compute_ref(self) -> None:
        for rec in self:
            rec.ref = "x"

    def _search_ref(self, operator: str, value: object) -> list:
        return [("id", "in", [11, 22])]


class IBeta(models.Model):
    _name = "i.beta"
    _module = _MOD
    _description = "Plain stored field, different semantics"

    ref = fields.Char()


class ICurrency(models.Model):
    _name = "res.currency"
    _module = _MOD
    _description = "Currency (test double)"

    name = fields.Char()
    rounding = fields.Float(default=0.01)

    def round(self, amount: float) -> float:
        self.check_singleton()
        prec = self.rounding or 0.01
        return round(amount / prec) * prec


class IInvoice(models.Model):
    _name = "i.invoice"
    _module = _MOD
    _description = "Monetary host"

    currency_id = fields.Many2one("res.currency")
    amount = fields.Monetary()


_FASTPATH_SCALARS = (
    "f_bool",
    "f_int",
    "f_float",
    "f_char",
    "f_text",
    "f_sel",
    "f_date",
    "f_dt",
    "f_money",
)


def test_inverse_operator_is_exact_negation_map() -> None:
    expected = {
        "not any": "any",
        "not any!": "any!",
        "not in": "in",
        "not like": "like",
        "not ilike": "ilike",
        "not =like": "=like",
        "not =ilike": "=ilike",
        "not =~": "=~",
        "!=": "=",
        "<>": "=",
        "any": "not any",
        "any!": "not any!",
        "in": "not in",
        "like": "not like",
        "ilike": "not ilike",
        "=like": "not =like",
        "=ilike": "not =ilike",
        "=~": "not =~",
        "=": "!=",
    }
    assert expected == INVERSE_OPERATOR
    for neg, pos in NEGATIVE_CONDITION_OPERATORS.items():
        assert INVERSE_OPERATOR[neg] == pos


def test_inverse_operator_is_an_involution_on_canonical_operators() -> None:
    for op, inv in INVERSE_OPERATOR.items():
        if op == "<>":
            continue
        assert INVERSE_OPERATOR[inv] == op, f"{op} -> {inv} -> {INVERSE_OPERATOR[inv]}"


def test_optimize_does_not_mutate_the_original_domain() -> None:
    with model_test_env(IAlpha, IBeta) as env:
        original = Domain([("ref", "=", "x")])
        level_before = original._opt_level

        out_alpha = original.optimize_full(env["i.alpha"])
        assert original._opt_level == level_before
        assert out_alpha is not original

        out_beta = original.optimize_full(env["i.beta"])
        assert list(out_alpha) == [("id", "in", [11, 22])]
        assert list(out_beta) == [("ref", "in", ["x"])]


def test_optimized_output_is_model_specific_not_reusable_across_models() -> None:
    with model_test_env(IAlpha, IBeta) as env:
        out_alpha = Domain([("ref", "=", "x")]).optimize_full(env["i.alpha"])
        reused = out_alpha.optimize_full(env["i.beta"])
        assert list(reused) == [("id", "in", [11, 22])]


def test_scalar_none_value_is_record_independent() -> None:
    with model_test_env(IScalars, ICurrency) as env:
        model = env["i.scalars"]
        rec = model.create({})
        for fname in _FASTPATH_SCALARS:
            field = model._fields[fname]
            via_none = field.convert_to_record(None, None)
            via_rec = field.convert_to_record(None, rec[:1])
            assert via_none == via_rec, fname


def _fastpath_cache_to_record(
    field: fields.Field,
) -> Callable[[fields.Field, Any, Any], Any] | None:
    for klass in type(field).__mro__:
        fn = klass.__dict__.get("__get__")
        if fn is None:
            continue
        freevars = getattr(getattr(fn, "__code__", None), "co_freevars", ())
        if "cache_to_record" in freevars:
            return fn.__closure__[freevars.index("cache_to_record")].cell_contents
        return None
    return None


_FASTPATH_CACHE_SAMPLES: dict[str, list] = {
    "f_bool": [None, False, True],
    "f_char": [None, "", "hello"],
    "f_text": [None, "", "multi\nline"],
    "f_int": [None, 0, 7],
    "f_float": [None, 0.0, 3.5],
    "f_money": [None, 0.0, 3.5],
    "f_sel": [None, "a"],
    "f_date": [None, date(2020, 1, 2)],
    "f_dt": [None, datetime(2020, 1, 2, 3, 4)],
}


def test_scalar_fastpath_lambda_matches_convert_to_record() -> None:
    with model_test_env(IScalars, ICurrency) as env:
        model = env["i.scalars"]
        rec = model.create({})[:1]
        checked = []
        for fname in _FASTPATH_SCALARS:
            field = model._fields[fname]
            cache_to_record = _fastpath_cache_to_record(field)
            if cache_to_record is None:
                continue
            checked.append(fname)
            for v in _FASTPATH_CACHE_SAMPLES[fname]:
                fast = cache_to_record(field, v, rec)
                slow = field.convert_to_record(v, rec)
                assert fast == slow, (
                    f"{fname}: fast-path lambda({v!r})={fast!r} != "
                    f"convert_to_record({v!r})={slow!r}"
                )
        assert set(checked) == set(_FASTPATH_CACHE_SAMPLES), checked


def test_missing_comodel_is_tolerated_and_recorded() -> None:

    class WithGhost(models.Model):
        _name = "i.withghost"
        _module = _MOD + ".ghost"
        _description = "Absent-comodel host"

        name = fields.Char()
        ghost_id = fields.Many2one("i.does.not.exist")

    with model_test_env(WithGhost) as env:
        degraded = {f"{f.model_name}.{f.name}" for f in env.registry.degraded_fields}
        assert "i.withghost.ghost_id" in degraded
        assert env["i.withghost"].create({"name": "ok"}).name == "ok"


def test_real_dependency_error_propagates_not_swallowed() -> None:

    class BadDepends(models.Model):
        _name = "i.bad"
        _module = _MOD + ".bad"
        _description = "Broken @depends"

        a = fields.Integer()
        b = fields.Integer(compute="_compute_b", store=True)

        @api.depends(lambda self: 1 / 0)  # type: ignore[arg-type, return-value]
        def _compute_b(self) -> None:
            for rec in self:
                rec.b = rec.a

    raised = False
    try:
        with model_test_env(BadDepends):
            pass
    except ZeroDivisionError:
        raised = True
    assert raised


def test_monetary_column_rounds_via_currency() -> None:
    with model_test_env(ICurrency, IInvoice) as env:
        cur = env["res.currency"].create({"name": "USD", "rounding": 0.01})
        inv = env["i.invoice"].create({"currency_id": cur.id, "amount": 3.14159})
        field = env["i.invoice"]._fields["amount"]

        assert field._resolve_currency_record(inv) == cur
        assert abs(field.convert_to_column(3.14159, inv) - 3.14) < 1e-9

        plain = env["i.invoice"].create({"amount": 9.999})
        assert abs(field.convert_to_column(9.999, plain) - 9.999) < 1e-9


def test_every_construction_path_sets_all_slots() -> None:
    from odoo.orm.models.base import BaseModel

    slots = tuple(BaseModel.__slots__)
    assert slots, "BaseModel must declare __slots__"

    with model_test_env(IScalars, ICurrency) as env:
        Model = env["i.scalars"]
        recs = Model.create([{"f_int": i} for i in range(3)])

        def assert_full(rec: BaseModel, label: str) -> None:
            for slot in slots:
                assert hasattr(rec, slot), f"{label}: record missing slot {slot!r}"

        assert_full(Model._spawn(env, (1,), (1,)), "_spawn")
        assert_full(Model.browse((1, 2)), "browse")
        assert_full(recs.with_env(env), "with_env")
        assert_full(recs.with_prefetch((1,)), "with_prefetch")
        assert_full(recs[1:], "__getitem__ slice")
        assert_full(recs[0], "__getitem__ int")
        assert_full(recs.sorted("f_int"), "sorted")
        assert_full(next(iter(recs)), "__iter__")
        assert_full(next(reversed(recs)), "__reversed__")
        assert_full(env["i.scalars"], "Environment.__getitem__")


def test_persistence_backend_seam_is_wired() -> None:
    from odoo.orm.runtime._backend_memory import InMemoryBackend

    with model_test_env(IScalars) as env:
        backend = env.backend
        assert isinstance(backend, InMemoryBackend), (
            f"env.backend must be an InMemoryBackend in the DB-free tier, "
            f"got {backend!r}"
        )
        assert not hasattr(backend, "supports_parent_store")
        assert callable(backend.set_parent_paths)
        assert env.backend is env.transaction.backend


def test_all_cached_ids_spans_per_context_subdicts() -> None:
    from odoo.orm.components.cache import FieldCache

    cache = FieldCache()
    cache.get_context_data("G", ("en_US",))[1] = "a"
    cache.get_context_data("G", ("fr_FR",))[2] = "b"
    assert set(cache.get_context_cached_ids("G")) == {1, 2}


def test_all_cached_ids_skips_stale_flat_entries() -> None:
    from odoo.orm.components.cache import FieldCache

    cache = FieldCache()
    cache.get_context_data("G", ("en_US",))[1] = "a"
    cache.get_field_data("G").update({5: "stale-scalar", 6: None, 7: {"json-key": "v"}})
    assert set(cache.get_context_cached_ids("G")) == {1}


def test_invalidate_mixed_state_never_reaches_into_json_values() -> None:
    from odoo.orm.components.cache import FieldCache

    cache = FieldCache()
    sub = cache.get_context_data("G", ("en_US",))
    sub.update({1: "a", 2: "b"})
    flat = cache.get_field_data("G")
    flat[1] = {2: "json-payload"}
    cache.invalidate("G", [2])
    assert sub == {1: "a"}
    assert flat[1] == {2: "json-payload"}
    cache.invalidate("G", [1])
    assert 1 not in flat
    assert sub == {}
