from unittest.mock import patch

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.orm.runtime.backend import _get_fetch_term

_MOD = "test_fetch_term_cache"


class Thing(models.Model):
    _name = "term.thing"
    _module = _MOD
    _description = "a model with plain, translated and company-dependent columns"

    name = fields.Char(translate=True)
    code = fields.Char()
    ref = fields.Char(company_dependent=True)


def test_a_plain_column_term_is_built_once_and_access_checked_every_time():
    with model_test_env(Thing) as env:
        model = env["term.thing"]
        query = model._as_query()
        field = model._fields["code"]
        with patch.object(type(model), "_check_field_access") as check:
            first = _get_fetch_term(model, field, query)
            second = _get_fetch_term(model, field, query)
        assert first is second
        assert first.code == '"term_thing"."code"'
        assert not first.params
        assert not tuple(first.to_flush)
        assert check.call_count == 2
        # the same identifier, with the field to flush, serves every other
        # spelling of the column against the model's own table
        column = model._field_to_sql("term_thing", "code", query)
        assert column is field._column_term
        assert column.code == first.code
        assert tuple(column.to_flush) == (field,)
        assert model._field_to_sql("other_alias", "code", query) is not column


def test_a_company_dependent_column_is_never_cached():
    with model_test_env(Thing) as env:
        model = env["term.thing"]
        query = model._as_query()
        field = model._fields["ref"]
        first = _get_fetch_term(model, field, query)
        second = _get_fetch_term(model, field, query)
        assert first is not second
        assert field._fetch_term is None


def test_a_translated_column_term_is_cached_per_language_chain():
    with model_test_env(Thing) as env:
        model = env["term.thing"]
        query = model._as_query()
        field = model._fields["name"]
        first = _get_fetch_term(model, field, query)
        assert first is _get_fetch_term(model, field, query)
        assert first.params == ("en_US",)
        assert first.code == '"term_thing"."name"->>%s'
        assert tuple(first.to_flush) == (field,)
        prefetching = model.with_context(prefetch_langs=True)
        assert _get_fetch_term(prefetching, field, query) is not first
