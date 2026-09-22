import typing

from odoo import fields
from odoo.orm.models.mixins.schema import SchemaMixin


class _Cursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((" ".join(str(query.code).split()), tuple(query.params)))


class _Env:
    def __init__(self):
        self.cr = _Cursor()


def _model(default):
    field = fields.Boolean()
    field.default = lambda model: default

    class _Model(SchemaMixin):
        _table = "res_company"
        _fields = {"active": field}
        env: typing.Any = _Env()

    return typing.cast("typing.Any", object.__new__(_Model))


def test_a_new_boolean_column_backfills_every_row():
    model = _model(default=True)
    model._init_column("active", new_column=True)
    assert model.env.cr.executed == [
        ('UPDATE "res_company" SET "active" = %s', (True,)),
    ]


def test_an_existing_column_only_fills_the_nulls():
    model = _model(default=True)
    model._init_column("active")
    assert model.env.cr.executed == [
        ('UPDATE "res_company" SET "active" = %s WHERE "active" IS NULL', (True,)),
    ]


def test_a_boolean_default_of_false_needs_no_backfill():
    model = _model(default=False)
    model._init_column("active", new_column=True)
    assert model.env.cr.executed == []
