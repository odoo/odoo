import pytest

from odoo import fields, models
from odoo.orm.domain import Domain
from odoo.orm.model_test_env import model_test_env

_MOD = "test_regex_operator"


class Doc(models.Model):
    _name = "rx.doc"
    _module = _MOD
    _description = "doc"
    _log_access = False

    name = fields.Char()
    prefix = fields.Char()
    parent_id = fields.Many2one("rx.doc")


def _docs(env):
    Doc = env["rx.doc"]
    return (
        Doc.create({"name": "INV/2026/00001", "prefix": "INV/2026/"}),
        Doc.create({"name": "INV/2026/02/00007", "prefix": "INV/2026/02/"}),
        Doc.create({"name": "draft", "prefix": False}),
    )


def test_regex_matches_anywhere_and_is_case_sensitive():
    with model_test_env(Doc) as env:
        yearly, monthly, _draft = _docs(env)
        docs = env["rx.doc"]
        assert docs.search([("prefix", "=~", r"^INV/\d{4}/$")]) == yearly
        assert docs.search([("name", "=~", r"/\d{2}/")]) == monthly
        assert not docs.search([("name", "=~", "inv")])


def test_negated_regex_keeps_the_empty_values():
    with model_test_env(Doc) as env:
        yearly, _monthly, draft = _docs(env)
        found = env["rx.doc"].search([("prefix", "not =~", r"^INV/\d{4}/\d{2}/$")])
        assert set(found.ids) == {yearly.id, draft.id}


def test_filtered_domain_agrees_with_search():
    with model_test_env(Doc) as env:
        docs = env["rx.doc"].concat(*_docs(env))
        domain = [("name", "=~", r"^INV/\d{4}/\d{5}$")]
        assert docs.filtered_domain(domain) == env["rx.doc"].search(domain)


def test_an_empty_or_non_string_pattern_is_refused():
    with model_test_env(Doc) as env:
        _docs(env)
        for bad in ("", 42, False):
            with pytest.raises(TypeError):
                env["rx.doc"].search([("name", "=~", bad)])
        with pytest.raises(TypeError):
            env["rx.doc"].search([("parent_id", "=~", "1")])


def test_the_negative_form_inverts_to_the_positive_one():
    negated = ~Domain("name", "=~", "x")
    assert negated == Domain("name", "not =~", "x")
    assert ~negated == Domain("name", "=~", "x")
