# -*- coding: utf-8 -*-

import json

from odoo import fields


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

@monkey_patch(fields.Field)
def _get_attrs(self, model, name):
    attrs = _get_attrs.super(self, model, name)
    if attrs.get('sparse'):
        # by default, sparse fields are not stored and not copied
        attrs['store'] = False
        attrs['copy'] = attrs.get('copy', False)
        attrs['compute'] = self._compute_sparse
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
        value = self.convert_to_read(record[self.name], record, use_name_get=False)
        if value:
            if values.get(self.name) != value:
                values[self.name] = value
                record[self.sparse] = values
        else:
            if self.name in values:
                values.pop(self.name)
                record[self.sparse] = values


#
# Definition and implementation of serialized fields
#

class Serialized(fields.Field):
    """ Serialized fields provide the storage for sparse fields. """
    type = 'serialized'
    _slots = {
        'prefetch': False,              # not prefetched by default
    }
    column_type = ('text', 'text')

    def convert_to_column(self, value, record, values=None):
        return json.dumps(value)

    def convert_to_cache(self, value, record, validate=True):
        # cache format: dict
        value = value or {}
        return value if isinstance(value, dict) else json.loads(value)

fields.Serialized = Serialized
