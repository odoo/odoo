from __future__ import annotations

import copy
import json
import typing

from psycopg2.extras import Json as PsycopgJson

from odoo.tools import SQL

from .fields import Field
from .identifiers import IdType

if typing.TYPE_CHECKING:
    from .models import BaseModel
    from odoo.tools import Query

# integer needs to be imported before Id because of `type` attribute clash
from . import fields_numeric  # noqa: F401


class Boolean(Field[bool]):
    """ Encapsulates a :class:`bool`. """
    type = 'boolean'
    _column_type = ('bool', 'bool')
    falsy_value = False

    def convert_to_column(self, value, record, values=None, validate=True):
        return bool(value)

    def convert_to_cache(self, value, record, validate=True):
        return bool(value)

    def convert_to_export(self, value, record):
        return bool(value)

    def condition_to_sql(self, model: BaseModel, alias: str, field_expr: str, operator: str, value, query: Query) -> SQL:
        if operator not in ('in', 'not in'):
            return super().condition_to_sql(model, alias, field_expr, operator, value, query)
        # get field and check access
        sql_field = self.field_expr_to_sql(model, alias, field_expr, query)
        value = {bool(v) for v in value}  # make sure it's a set of bool
        if len(value) != 1:
            sql_expr = SQL("TRUE") if bool(value) == (operator == 'in') else SQL("FALSE")
        elif any(value) == (operator == 'in'):
            sql_expr = SQL("%s = TRUE", sql_field)
        else:
            sql_expr = SQL("(%s IS NULL OR %s = FALSE)", sql_field, sql_field)
        return self._condition_to_sql_company(sql_expr, model, alias, field_expr, operator, value, query)


class Json(Field):
    """ JSON Field that contain unstructured information in jsonb PostgreSQL column.
    This field is still in beta
    Some features have not been implemented and won't be implemented in stable versions, including:
    * searching
    * indexing
    * mutating the values.
    """

    type = 'json'
    _column_type = ('jsonb', 'jsonb')

    def convert_to_record(self, value, record):
        """ Return a copy of the value """
        return False if value is None else copy.deepcopy(value)

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return None
        return json.loads(json.dumps(value))

    def convert_to_column(self, value, record, values=None, validate=True):
        if not value:
            return None
        return PsycopgJson(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        return json.dumps(value)


class Id(Field[IdType | typing.Literal[False]]):
    """ Special case for field 'id'. """
    type = 'integer'  # note this conflicts with Integer
    column_type = ('int4', 'int4')

    string = 'ID'
    store = True
    readonly = True
    prefetch = False

    def update_db(self, model, columns):
        pass                            # this column is created with the table

    def __get__(self, record, owner=None):
        if record is None:
            return self         # the field is accessed through the class owner

        # the code below is written to make record.id as quick as possible
        ids = record._ids
        size = len(ids)
        if size == 0:
            return False
        elif size == 1:
            return ids[0]
        raise ValueError("Expected singleton: %s" % record)

    def __set__(self, record, value):
        raise TypeError("field 'id' cannot be assigned")

    def field_to_sql(self, model: BaseModel, alias: str, flush: bool = True) -> SQL:
        # do not flush, just return the identifier
        assert self.store, 'id field must be stored'
        return SQL.identifier(alias, self.name)
