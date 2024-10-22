# -*- coding: utf-8 -*-

import json

from odoo import fields
from odoo import tools
from odoo.tools.query import Query
from odoo.osv import expression

def monkey_patch(cls):
    """ Return a method decorator to monkey-patch the given class. """
    def decorate(func):
        name = func.__name__
        func.super = getattr(cls, name, None)
        setattr(cls, name, func)
        return func
    return decorate


#
# Implement sparse fields by monkey-patching fields.Field
#

fields.Field.__doc__ += """

        .. _field-sparse:

        .. rubric:: Sparse fields

        Sparse fields have a very small probability of being not null. Therefore
        many such fields can be serialized compactly into a common location, the
        latter being a so-called "serialized" field.

        :param sparse: the name of the field where the value of this field must
            be stored.
"""
fields.Field.sparse = None

@monkey_patch(fields.Field)
def _get_attrs(self, model_class, name):
    attrs = _get_attrs.super(self, model_class, name)
    if attrs.get('sparse'):
        # by default, sparse fields are not stored and not copied
        attrs['store'] = False
        attrs['copy'] = attrs.get('copy', False)
        attrs['compute'] = self._compute_sparse
        attrs['search'] = self._search_sparse
        if not attrs.get('readonly'):
            attrs['inverse'] = self._inverse_sparse
    return attrs

@monkey_patch(fields.Field)
def _compute_sparse(self, records):
    for record in records:
        values = record[self.sparse]
        record[self.name] = values.get(self.name)
    if self.relational:
        for record in records:
            record[self.name] = record[self.name].exists()

@monkey_patch(fields.Field)
def _inverse_sparse(self, records):
    for record in records:
        values = record[self.sparse]
        value = self.convert_to_read(record[self.name], record, use_display_name=False)
        if value:
            if values.get(self.name) != value:
                values[self.name] = value
                record[self.sparse] = values
        else:
            if self.name in values:
                values.pop(self.name)
                record[self.sparse] = values


@monkey_patch(fields.Field)
def _search_sparse(self, records, operator, value):
    """ Determine the domain to search on field ``self``. """
    if isinstance(value, Query):
        value = list(value)
    model = records.env[self.model_name]
    cast_type = self.column_type[0]
    sql_op = expression.SQL_OPERATORS[operator].code

    base_query = f"SELECT id FROM {model._table} WHERE ({self.sparse} ->> %s)::{cast_type} {sql_op} %s"
    return [("id", "inselect", (base_query, [self.name, value]))]

#
# Definition and implementation of serialized fields
#

class Serialized(fields.Field):
    """ Serialized fields provide the storage for sparse fields. """
    type = 'serialized'
    column_type = ('jsonb', 'jsonb')

    prefetch = False                    # not prefetched by default

    def convert_to_column_insert(self, value, record, values=None, validate=True):
        return self.convert_to_cache(value, record, validate=validate)

    def convert_to_cache(self, value, record, validate=True):
        # cache format: json.dumps(value) or None
        return json.dumps(value) if isinstance(value, dict) else (value or None)

    def convert_to_record(self, value, record):
        return json.loads(value or "{}")

    def update_db(self, model, columns):
        res = super().update_db(model, columns)
        if self.store:
            constraint_name = f"{model._table}_{self.name}_jsonobject"
            definition = f"CHECK (jsonb_typeof({self.name}) = 'object')"
            current_definition = tools.constraint_definition(
                model._cr, model._table, constraint_name
            )
            if current_definition != definition:
                if current_definition:
                    tools.drop_constraint(model._cr, model._table, constraint_name)
                model.pool.post_constraint(
                    tools.add_constraint,
                    model._cr,
                    model._table,
                    constraint_name,
                    definition,
                )
        return res


fields.Serialized = Serialized
