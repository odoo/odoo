import re
import warnings
from collections.abc import Hashable, Reversible
from collections.abc import Set as AbstractSet

import dateutil.relativedelta

from odoo.exceptions import AccessError, ValidationError
from odoo.tools import OrderedSet, SQL

regex_alphanumeric = re.compile(r'^[a-z0-9_]+$')
regex_object_name = re.compile(r'^[a-z0-9_.]+$')
regex_pg_name = re.compile(r'^[a-z_][a-z0-9_$]*$', re.IGNORECASE)
# match private methods, to prevent their remote invocation
regex_private = re.compile(r'^(_.*|init)$')

# types handled as collections
COLLECTION_TYPES = (list, tuple, AbstractSet)
# The hard-coded super-user id (a.k.a. root user, or OdooBot).
SUPERUSER_ID = 1

# _read_group stuff
READ_GROUP_TIME_GRANULARITY = {
    'hour': dateutil.relativedelta.relativedelta(hours=1),
    'day': dateutil.relativedelta.relativedelta(days=1),
    'week': dateutil.relativedelta.relativedelta(days=7),
    'month': dateutil.relativedelta.relativedelta(months=1),
    'quarter': dateutil.relativedelta.relativedelta(months=3),
    'year': dateutil.relativedelta.relativedelta(years=1)
}

READ_GROUP_NUMBER_GRANULARITY = {
    'year_number': 'year',
    'quarter_number': 'quarter',
    'month_number': 'month',
    'iso_week_number': 'week',  # ISO week number because anything else than ISO is nonsense
    'day_of_year': 'doy',
    'day_of_month': 'day',
    'day_of_week': 'dow',
    'hour_number': 'hour',
    'minute_number': 'minute',
    'second_number': 'second',
}

READ_GROUP_ALL_TIME_GRANULARITY = READ_GROUP_TIME_GRANULARITY | READ_GROUP_NUMBER_GRANULARITY


# SQL operators with spaces around them
# hardcoded to avoid changing SQL injection linting
SQL_OPERATORS = {
    "=": SQL(" = "),
    "!=": SQL(" != "),
    "in": SQL(" IN "),
    "not in": SQL(" NOT IN "),
    "<": SQL(" < "),
    ">": SQL(" > "),
    "<=": SQL(" <= "),
    ">=": SQL(" >= "),
    "like": SQL(" LIKE "),
    "ilike": SQL(" ILIKE "),
    "=like": SQL(" LIKE "),
    "=ilike": SQL(" ILIKE "),
    "not like": SQL(" NOT LIKE "),
    "not ilike": SQL(" NOT ILIKE "),
    "not =like": SQL(" NOT LIKE "),
    "not =ilike": SQL(" NOT ILIKE "),
}


def check_method_name(name):
    """ Raise an ``AccessError`` if ``name`` is a private method name. """
    warnings.warn("Since 19.0, use odoo.service.model.get_public_method", DeprecationWarning)
    if regex_private.match(name):
        raise AccessError('Private methods (such as %s) cannot be called remotely.' % name)


def check_object_name(name):
    """ Check if the given name is a valid model name.

        The _name attribute in osv and osv_memory object is subject to
        some restrictions. This function returns True or False whether
        the given name is allowed or not.

        TODO: this is an approximation. The goal in this approximation
        is to disallow uppercase characters (in some places, we quote
        table/column names and in other not, which leads to this kind
        of errors:

            psycopg2.ProgrammingError: relation "xxx" does not exist).

        The same restriction should apply to both osv and osv_memory
        objects for consistency.

    """
    return regex_object_name.match(name) is not None


def check_pg_name(name):
    """ Check whether the given name is a valid PostgreSQL identifier name. """
    if not regex_pg_name.match(name):
        raise ValidationError("Invalid characters in table name %r" % name)
    if len(name) > 63:
        raise ValidationError("Table name %r is too long" % name)


def parse_field_expr(field_expr: str) -> tuple[str, str | None]:
    if (property_index := field_expr.find(".")) >= 0:
        property_name = field_expr[property_index + 1:]
        field_expr = field_expr[:property_index]
    else:
        property_name = None
    if not field_expr:
        raise ValueError(f"Invalid field expression {field_expr!r}")
    return field_expr, property_name


def expand_ids(id0, ids):
    """ Return an iterator of unique ids from the concatenation of ``[id0]`` and
        ``ids``, and of the same kind (all real or all new).
    """
    yield id0
    seen = {id0}
    kind = bool(id0)
    for id_ in ids:
        if id_ not in seen and bool(id_) == kind:
            yield id_
            seen.add(id_)


#
# The value of _prefetch_ids must be iterable, reversible, and hashable.
#

class PrefetchRelational(Reversible, Hashable):
    """ Iterable for the values of a many2one field on the prefetch set of a given record. """
    __slots__ = ('_field', '_records')

    def __init__(self, field, records):
        self._field = field
        self._records = records

    def __hash__(self):
        return hash(self._field) ^ hash(self._records._prefetch_ids)

    def __eq__(self, other):
        return isinstance(other, PrefetchRelational) and (
            self._field is other._field and self._records._prefetch_ids == other._records._prefetch_ids
        )

    def __iter__(self):
        field_cache = self._field._get_cache(self._records.env)
        if self._field.type == 'many2one':
            for id_ in self._records._prefetch_ids:
                if (coid := field_cache.get(id_)) is not None:
                    yield coid
        else:
            for id_ in self._records._prefetch_ids:
                yield from field_cache.get(id_, ())

    def __reversed__(self):
        field_cache = self._field._get_cache(self._records.env)
        if self._field.type == 'many2one':
            for id_ in reversed(self._records._prefetch_ids):
                if (coid := field_cache.get(id_)) is not None:
                    yield coid
        else:
            for id_ in reversed(self._records._prefetch_ids):
                yield from field_cache.get(id_, ())


class OriginIds(Reversible, Hashable):
    """ A reversible iterable returning the origin ids of a collection of ``ids``.
        Actual ids are returned as is, and ids without origin are not returned.
    """
    __slots__ = ['ids']

    def __init__(self, ids):
        self.ids = ids

    def __hash__(self):
        return hash(self.ids)

    def __eq__(self, other):
        return isinstance(other, OriginIds) and self.ids == other.ids

    def __iter__(self):
        for id_ in self.ids:
            if id_ := id_ or id_.origin:
                yield id_

    def __reversed__(self):
        for id_ in reversed(self.ids):
            if id_ := id_ or id_.origin:
                yield id_


class ConcatIds(Reversible, Hashable):
    """ A reversible iterable returning the union of collections of ``ids``. """
    __slots__ = ['_iterables']

    def __init__(self, iterables):
        self._iterables = tuple(iterables)

    def __hash__(self):
        return hash(self._iterables)

    def __eq__(self, other):
        return isinstance(other, ConcatIds) and self._iterables == other._iterables

    def __iter__(self):
        for iterable in self._iterables:
            yield from iterable

    def __reversed__(self):
        for iterable in reversed(self._iterables):
            yield from reversed(iterable)


class Prefetch:
    relational = PrefetchRelational
    origin = OriginIds

    @staticmethod
    def union(iterables):
        ids = OrderedSet()      # union of tuples in iterables
        extra = OrderedSet()    # non-tuple items in iterables

        for it in iterables:
            if isinstance(it, ConcatIds):
                for it1 in it._iterables:
                    ids.update(it1) if isinstance(it1, tuple) else extra.add(it1)
            else:
                ids.update(it) if isinstance(it, tuple) else extra.add(it)

        if not extra:
            return tuple(ids)
        if not ids and len(extra) == 1:
            return next(iter(extra))
        return ConcatIds([tuple(ids), *extra])
