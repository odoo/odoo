from __future__ import annotations

import copy
import json
import typing

from psycopg2.extras import Json as PsycopgJson

from odoo.tools import SQL, json_default

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

    def _condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        if operator not in ('in', 'not in'):
            return super()._condition_to_sql(field_expr, operator, value, model, alias, query)

        # get field and check access
        sql_field = model._field_to_sql(alias, field_expr, query)

        # express all conditions as (field_expr, 'in', possible_values)
        possible_values = (
            {bool(v) for v in value} if operator == 'in' else
            {True, False} - {bool(v) for v in value}  # operator == 'not in'
        )
        if len(possible_values) != 1:
            return SQL("TRUE") if possible_values else SQL("FALSE")
        is_true = True in possible_values
        return SQL("%s IS TRUE", sql_field) if is_true else SQL("%s IS NOT TRUE", sql_field)


class Json(Field):
    """ JSON Field that contain unstructured information in jsonb PostgreSQL column.

    Some features won't be implemented, including:
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
        return json.loads(json.dumps(value, ensure_ascii=False, default=json_default))

    def convert_to_column(self, value, record, values=None, validate=True):
        if validate:
            value = self.convert_to_cache(value, record)
        if value is None:
            return None
        return PsycopgJson(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        return json.dumps(value)


class Id(Field[IdType | typing.Literal[False]]):
    """ Special case for field 'id'. """
    # Note: This field type is not necessarily an integer!
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

    def convert_to_column(self, value, record, values=None, validate=True):
        return value

    def to_sql(self, model: BaseModel, alias: str) -> SQL:
        # do not flush, just return the identifier
        assert self.store, 'id field must be stored'
        # id is never flushed
        return SQL.identifier(alias, self.name)

    def expression_getter(self, field_expr):
        if field_expr != 'id.origin':
            return super().expression_getter(field_expr)

        def getter(record):
            return (id_ := record._ids[0]) or getattr(id_, 'origin', None) or False

        return getter
