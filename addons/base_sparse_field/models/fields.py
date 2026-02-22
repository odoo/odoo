# -*- coding: utf-8 -*-

import json
import logging

from odoo import fields
from odoo.tools import sql, SQL, Query
from odoo.osv import expression

_logger = logging.getLogger(__name__)

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
    query = Query(self.env, self.model_name)
    cast_type = self.column_type[0]
    sql_op = expression.SQL_OPERATORS[operator].code
    query.add_where(
        SQL("(%s ->> %s)::%s %s %s", self.sparse, self.name, cast_type, sql_op, value)
    )
    return [("id", "in", query)]


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
            definition = f"CHECK (jsonb_typeof({self.name}) = 'object')"
            conname = '%s_%s_jsonobject' % (model._table, self.name)
            if len(conname) > 63:
                hashed_conname = sql.make_identifier(conname)
                current_definition = sql.constraint_definition(model._cr, model._table, hashed_conname)
                if not current_definition:
                    _logger.info("Constraint name %r has more than 63 characters, internal PG identifier is %r", conname, hashed_conname)
                conname = hashed_conname
            else:
                current_definition = sql.constraint_definition(model._cr, model._table, conname)
            
            if current_definition != definition:
                if current_definition:
                    # constraint exists but its definition may have changed
                    sql.drop_constraint(model._cr, model._table, conname)
                model.pool.post_constraint(model._cr, lambda cr: sql.add_constraint(cr, model._table, conname, definition), conname)
        return res


fields.Serialized = Serialized
