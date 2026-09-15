import sys
from datetime import date, datetime

import pytest

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.orm.model_test_env import model_test_env
from odoo.tools.misc import PENDING, SENTINEL

_MOD = "test_field_get_equivalence"

_CANONICAL_GET = fields.Field.__get__


def _term_translate(_callback, value):
    return value


class GCurrency(models.Model):
    _name = "res.currency"
    _module = _MOD
    _description = "Currency (test double)"

    name = fields.Char()
    rounding = fields.Float(default=0.01)

    def round(self, amount: float) -> float:
        self.check_singleton()
        prec = self.rounding or 0.01
        return round(amount / prec) * prec


class GChild(models.Model):
    _name = "g.child"
    _module = _MOD
    _description = "O2m child"

    name = fields.Char()
    parent_id = fields.Many2one("g.host")


class GHost(models.Model):
    _name = "g.host"
    _module = _MOD
    _description = "Fast-path field host"

    f_bool = fields.Boolean()
    f_int = fields.Integer()
    f_float = fields.Float()
    f_money = fields.Monetary()
    f_sel = fields.Selection([("a", "A"), ("b", "B")])
    f_date = fields.Date()
    f_dt = fields.Datetime()
    currency_id = fields.Many2one("res.currency")
    f_char = fields.Char()
    f_text = fields.Text()
    f_html = fields.Html()
    f_m2o = fields.Many2one("res.currency")
    child_ids = fields.One2many("g.child", "parent_id")
    f_tchar = fields.Char(translate=True)
    f_thtml = fields.Html(translate=True, sanitize="email_outgoing")
    f_ctchar = fields.Char(translate=_term_translate)
    f_scomp = fields.Integer(compute="_compute_scomp", store=True)

    @api.depends("f_int")
    def _compute_scomp(self):
        for rec in self:
            rec.f_scomp = (rec.f_int or 0) + 1


_SCALAR_DIFFERENTIAL: dict[str, list] = {
    "f_bool": [None, False, True],
    "f_int": [None, 0, 7],
    "f_float": [None, 0.0, 3.5],
    "f_money": [None, 0.0, 3.5],
    "f_sel": [None, "a", "b"],
    "f_date": [None, date(2020, 1, 2)],
    "f_dt": [None, datetime(2020, 1, 2, 3, 4)],
    "f_char": [None, "", "hello"],
    "f_text": [None, "", "multi\nline"],
}

_SINGLETON_FIELDS = (*_SCALAR_DIFFERENTIAL, "f_html")

_RELATIONAL_FIELDS = ("f_m2o", "child_ids")

_ACL_FIELDS = (*_SINGLETON_FIELDS, *_RELATIONAL_FIELDS)


def _seed(env):
    cur = env["res.currency"]
    cur_a = cur.create({"name": "AAA", "rounding": 0.01})
    cur_b = cur.create({"name": "BBB", "rounding": 0.01})
    host = env["g.host"].create(
        {
            "currency_id": cur_a.id,
            "f_m2o": cur_b.id,
            "f_int": 5,
            "f_char": "hi",
        }
    )
    env["g.child"].create({"name": "c1", "parent_id": host.id})
    return host, cur_a, cur_b


def _put_cache(field, rec, value):
    field._get_cache(rec.env)[rec.id] = value


def test_scalar_and_textual_fastpath_matches_canonical_on_cache_hit():
    # the test plants cache values: no cache-against-rows check at the end
    with model_test_env(GHost, GChild, GCurrency, check_cache=False) as env:
        host, *_ = _seed(env)
        for fname, samples in _SCALAR_DIFFERENTIAL.items():
            field = host._fields[fname]
            fast = type(field).__get__
            assert fast is not _CANONICAL_GET, fname
            for raw in samples:
                _put_cache(field, host, raw)
                got = fast(field, host)
                ref = _CANONICAL_GET(field, host)
                assert got == ref, (
                    f"{fname}: fast={got!r} != canonical={ref!r} (raw={raw!r})"
                )
                assert got is not PENDING and got is not SENTINEL
                assert got == field.convert_to_record(raw, host), fname


def test_many2one_fastpath_matches_canonical_on_cache_hit():
    # the test plants cache values: no cache-against-rows check at the end
    with model_test_env(GHost, GChild, GCurrency, check_cache=False) as env:
        host, _cur_a, cur_b = _seed(env)
        field = host._fields["f_m2o"]
        fast = type(field).__get__
        for raw in (cur_b.id, None):
            _put_cache(field, host, raw)
            got = fast(field, host)
            ref = _CANONICAL_GET(field, host)
            assert got == ref, f"m2o fast={got!r} != canonical={ref!r} (raw={raw!r})"
            assert got._name == "res.currency"
            assert got.ids == (ref.ids)


def test_html_fastpath_matches_canonical_on_normal_hit():
    # the test plants cache values: no cache-against-rows check at the end
    with model_test_env(GHost, GChild, GCurrency, check_cache=False) as env:
        host, *_ = _seed(env)
        field = host._fields["f_html"]
        fast = type(field).__get__
        _put_cache(field, host, "<p>x</p>")
        got = fast(field, host)
        ref = _CANONICAL_GET(field, host)
        assert got == ref
        assert str(got) == str(ref)


def test_empty_recordset_returns_type_falsy_default_matching_base():
    with model_test_env(GHost, GChild, GCurrency) as env:
        _seed(env)
        empty = env["g.host"].browse(())
        for fname in _ACL_FIELDS:
            field = empty._fields[fname]
            got = type(field).__get__(field, empty)
            ref = _CANONICAL_GET(field, empty)
            assert got == ref, f"{fname}: empty fast={got!r} != base={ref!r}"
        assert type(empty._fields["f_int"]).__get__(empty._fields["f_int"], empty) == 0
        assert (
            type(empty._fields["f_bool"]).__get__(empty._fields["f_bool"], empty)
            is False
        )
        m2o = empty._fields["f_m2o"]
        got = type(m2o).__get__(m2o, empty)
        assert got._name == "res.currency" and len(got) == 0


def test_multirecord_singleton_types_raise_via_ensure_one():
    with model_test_env(GHost, GChild, GCurrency) as env:
        env["g.host"].create({"f_int": 1})
        env["g.host"].create({"f_int": 2})
        recs = env["g.host"].search([])
        assert len(recs) >= 2
        for fname in _SINGLETON_FIELDS:
            field = recs._fields[fname]
            with pytest.raises(ValueError):
                type(field).__get__(field, recs)
            with pytest.raises(ValueError):
                _CANONICAL_GET(field, recs)


def test_multirecord_relational_types_return_recordset_not_raise():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, cur_a, cur_b = _seed(env)
        host2 = env["g.host"].create({"f_m2o": cur_a.id})
        recs = host + host2
        m2o = recs._fields["f_m2o"]
        got = type(m2o).__get__(m2o, recs)
        assert got._name == "res.currency"
        assert set(got.ids) == {cur_a.id, cur_b.id}
        o2m = recs._fields["child_ids"]
        got_lines = type(o2m).__get__(o2m, recs)
        assert got_lines._name == "g.child"


class _AclSpy:
    def __init__(self, model_cls):
        self.model_cls = model_cls
        self.has_calls = 0
        self.check_calls = 0
        self.allow = True
        self._orig_has = model_cls.__dict__.get("_has_field_access")
        self._orig_check = model_cls.__dict__.get("_check_field_access")
        spy = self

        def _has_field_access(self, field, operation):
            spy.has_calls += 1
            return spy.allow

        def _check_field_access(self, field, operation):
            spy.check_calls += 1
            if not spy.allow:
                raise AccessError("spy-denied")

        model_cls._has_field_access = _has_field_access
        model_cls._check_field_access = _check_field_access

    def restore(self):
        for name, orig in (
            ("_has_field_access", self._orig_has),
            ("_check_field_access", self._orig_check),
        ):
            if orig is None:
                delattr(self.model_cls, name)
            else:
                setattr(self.model_cls, name, orig)


def test_acl_preamble_bypassed_when_field_ungrouped():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, *_ = _seed(env)
        spy = _AclSpy(type(host))
        try:
            for fname in _ACL_FIELDS:
                field = host._fields[fname]
                assert field.groups in (None, False), fname
                type(field).__get__(field, host)
            assert spy.has_calls == 0
            assert spy.check_calls == 0
        finally:
            spy.restore()


def test_acl_preamble_bypassed_for_superuser_even_when_grouped():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, *_ = _seed(env)
        assert env.su is True
        spy = _AclSpy(type(host))
        try:
            for fname in _ACL_FIELDS:
                field = host._fields[fname]
                orig = field.groups
                field.groups = "base.group_system"
                try:
                    type(field).__get__(field, host)
                finally:
                    field.groups = orig
            assert spy.has_calls == 0, "su must not consult _has_field_access"
            assert spy.check_calls == 0
        finally:
            spy.restore()


def test_acl_preamble_allows_when_has_field_access_true():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, *_ = _seed(env)
        child_ids = host.child_ids._ids
        host = host.with_env(env(user=2, su=False))
        assert host.env.su is False
        host._fields["child_ids"]._update_cache(host, child_ids)
        spy = _AclSpy(type(host))
        spy.allow = True
        try:
            for fname in _ACL_FIELDS:
                field = host._fields[fname]
                orig = field.groups
                field.groups = "base.group_system"
                try:
                    type(field).__get__(field, host)
                finally:
                    field.groups = orig
            assert spy.has_calls >= len(_ACL_FIELDS)
            assert spy.check_calls == 0
        finally:
            spy.restore()


def test_acl_preamble_raises_access_error_when_denied_on_every_fast_path():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, *_ = _seed(env)
        host = host.with_env(env(user=2, su=False))
        spy = _AclSpy(type(host))
        spy.allow = False
        try:
            for fname in _ACL_FIELDS:
                field = host._fields[fname]
                orig = field.groups
                field.groups = "base.group_system"
                try:
                    with pytest.raises(AccessError):
                        type(field).__get__(field, host)
                finally:
                    field.groups = orig
            assert spy.check_calls == len(_ACL_FIELDS)
        finally:
            spy.restore()


def test_acl_denied_multirecord_relational_also_raises():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, cur_a, _cur_b = _seed(env)
        host2 = env["g.host"].create({"f_m2o": cur_a.id})
        recs = (host + host2).with_env(env(user=2, su=False))
        spy = _AclSpy(type(recs))
        spy.allow = False
        try:
            for fname in _RELATIONAL_FIELDS:
                field = recs._fields[fname]
                orig = field.groups
                field.groups = "base.group_system"
                try:
                    with pytest.raises(AccessError):
                        type(field).__get__(field, recs)
                finally:
                    field.groups = orig
        finally:
            spy.restore()


def test_id_field_has_no_acl_preamble_by_design():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, *_ = _seed(env)
        rec_id = host.id
        host = host.with_env(env(user=2, su=False))
        spy = _AclSpy(type(host))
        spy.allow = False
        idf = host._fields["id"]
        orig = idf.groups
        idf.groups = "base.group_system"
        try:
            assert type(idf).__get__(idf, host) == rec_id
            assert spy.check_calls == 0
        finally:
            idf.groups = orig
            spy.restore()


def test_id_field_invariants():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, *_ = _seed(env)
        host2 = env["g.host"].create({})
        idf = host._fields["id"]
        get = type(idf).__get__
        assert get(idf, env["g.host"].browse(())) is False
        assert get(idf, host) == host.id
        with pytest.raises(ValueError, match="Expected singleton"):
            get(idf, host + host2)


def test_pending_in_cache_is_never_returned_protected_yields_falsy():
    # the test plants cache values: no cache-against-rows check at the end
    with model_test_env(GHost, GChild, GCurrency, check_cache=False) as env:
        host = env["g.host"].create({"f_int": 5})
        field = host._fields["f_int"]
        _put_cache(field, host, PENDING)
        with env.protecting([field], host):
            got = type(field).__get__(field, host)
        assert got is not PENDING
        assert got == 0
        _put_cache(field, host, PENDING)
        with env.protecting([field], host):
            ref = _CANONICAL_GET(field, host)
        assert ref == 0


def test_pending_in_cache_unprotected_falls_through_to_fetch():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host = env["g.host"].create({"f_int": 7})
        field = host._fields["f_int"]
        stored = type(field).__get__(field, host)
        assert stored == 7
        _put_cache(field, host, PENDING)
        got = type(field).__get__(field, host)
        assert got is not PENDING
        assert got == stored


def test_stored_computed_pending_guard_recomputes_and_never_leaks_pending():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host = env["g.host"].create({"f_int": 3})
        field = host._fields["f_scomp"]
        assert field.is_stored_computed
        assert type(field).__get__(field, host) == 4
        _put_cache(field, host, PENDING)
        env.core.schedule(field, [host.id])
        got = type(field).__get__(field, host)
        assert got is not PENDING
        assert got == 4
        assert not env.core.has_pending_field(field)


def test_pending_evicted_for_a_scalar_read():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host = env["g.host"].create({"f_int": 9})
        field = host._fields["f_int"]
        _put_cache(field, host, PENDING)
        got = type(field).__get__(field, host)
        assert got is not PENDING
        assert got == 9


def test_relational_pending_protected_yields_empty_recordset():
    with model_test_env(GHost, GChild, GCurrency) as env:
        host, _cur_a, _cur_b = _seed(env)
        field = host._fields["f_m2o"]
        _put_cache(field, host, PENDING)
        got = type(field).__get__(field, host)
        assert got is not PENDING
        assert got._name == "res.currency"


def test_translate_true_en_us_fallback_diverges_from_base_and_is_correct():
    with model_test_env(GHost, GChild, GCurrency) as env:
        field = env["g.host"]._fields["f_tchar"]
        assert field.translate is True
        rec = env["g.host"].new({"f_tchar": "english"})
        assert rec.f_tchar == "english"
        other = rec.with_context(lang="fr_FR")
        of = other._fields["f_tchar"]
        got = type(of).__get__(of, other)
        assert got == "english", f"en_US fallback expected, got {got!r}"


def test_callable_translate_delegates_to_base():
    with model_test_env(GHost, GChild, GCurrency) as env:
        rec = env["g.host"].create({"f_ctchar": "cval"})
        field = rec._fields["f_ctchar"]
        assert callable(field.translate)
        got = type(field).__get__(field, rec)
        ref = _CANONICAL_GET(field, rec)
        assert got == ref == "cval"


def test_html_translate_true_fallback_preserves_markup():
    from markupsafe import Markup

    with model_test_env(GHost, GChild, GCurrency) as env:
        field = env["g.host"]._fields["f_thtml"]
        assert field.translate is True
        rec = env["g.host"].new({"f_thtml": "<b>hi</b>"})
        assert isinstance(rec.f_thtml, Markup)
        other = rec.with_context(lang="fr_FR")
        of = other._fields["f_thtml"]
        got = type(of).__get__(of, other)
        assert isinstance(got, Markup), f"expected Markup fallback, got {type(got)}"
        assert "hi" in str(got)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
