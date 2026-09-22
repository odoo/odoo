import sys

import pytest

from odoo import api, fields, models
from odoo.orm.model_test_env import model_test_env
from odoo.orm.stubs import class_name, render, render_registry

_MOD = "test_stubs"


class Author(models.Model):
    _name = "stub.author"
    _module = _MOD
    _description = "author"

    name = fields.Char()
    born = fields.Date()
    book_ids = fields.One2many("stub.book", "author_id")


class Book(models.Model):
    _name = "stub.book"
    _module = _MOD
    _description = "book"

    title = fields.Char(required=True)

    def action_publish(self, when, *, notify=False):
        return when

    @api.model
    def _from_title(self, title):
        return self.search([("title", "=", title)], limit=1)

    pages = fields.Integer()
    price = fields.Float()
    author_id = fields.Many2one("stub.author")
    tag_ids = fields.Many2many("stub.tag")


class Tag(models.Model):
    _name = "stub.tag"
    _module = _MOD
    _description = "tag"

    name = fields.Char()


def test_class_name_camel_cases_dots_and_underscores():
    assert class_name("res.partner") == "ResPartner"
    assert class_name("ir.model.fields") == "IrModelFields"
    assert class_name("account_move.line") == "AccountMoveLine"
    assert class_name("2d.shape") == "Model2dShape"


def test_render_types_every_field_and_relations_to_the_comodel_class():
    with model_test_env(Author, Book, Tag) as env:
        source = render_registry(env.registry)
    assert "class StubBook(BaseModel):" in source
    assert '    _name: Literal["stub.book"]' in source
    assert "    title: _F[str | Literal[False]]" in source
    assert "    pages: _F[int]" in source
    assert "    price: _F[float]" in source
    assert "    author_id: _F[StubAuthor]" in source
    assert "    tag_ids: _F[StubTag]" in source
    assert "    book_ids: _F[StubBook]" in source
    assert "    born: _F[datetime.date | Literal[False]]" in source
    assert (
        "    def action_publish(self, when: Any, *, notify: Any = ...) -> Any: ..."
        in source
    )
    assert "    def _from_title(self, title: Any) -> Any: ..." in source
    assert "    id: _F[int]" in source
    assert (
        '    def __getitem__(self, model_name: Literal["stub.book"]) -> StubBook: ...'
        in source
    )
    compile(source, "odoo_registry_stubs.pyi", "exec")


def test_render_refuses_two_models_stubbing_as_one_class():
    with pytest.raises(ValueError, match="both stub as"):
        render([("a.b", {}), ("a_b", {})])


def test_render_marks_a_field_that_shadows_a_base_method():
    source = render([("s.m", {"count": fields.Integer()})], reserved={"count"})
    assert "    count: _F[int]  # type: ignore[assignment]" in source


def test_render_skips_a_field_named_like_a_keyword():
    source = render([("k.w", {"class": fields.Char(), "ok": fields.Char()})])
    assert "    ok: _F[" in source
    assert "    class: " not in source


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
