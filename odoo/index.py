import dataclasses
import enum
import logging
import warnings
from abc import ABC
from typing import Dict, Optional

from .modules.db import FunctionStatus, get_unaccent_wrapper
from .tools import sql

_logger = logging.getLogger(__name__)


def quote(ident: str) -> str:
    ident = ident.replace('"', '""')
    return f'"{ident}"'


# reserved keywords in postgres, must be quoted. List extracted from appendix C
# table 1 of the documentation: https://www.postgresql.org/docs/current/sql-keywords-appendix.html#KEYWORDS-TABLE
RESERVED = {
    'all',
    'analyse',
    'analyze',
    'and',
    'any',
    'array',
    'as',
    'asc',
    'asymmetric',
    'authorization',
    'binary',
    'both',
    'case',
    'cast',
    'check',
    'collate',
    'collation',
    'column',
    'concurrently',
    'constraint',
    'create',
    'cross',
    'current_catalog',
    'current_date',
    'current_role',
    'current_schema',
    'current_time',
    'current_timestamp',
    'current_user',
    'default',
    'deferrable',
    'desc',
    'distinct',
    'do',
    'else',
    'end',
    'except',
    'false',
    'fetch',
    'for',
    'foreign',
    'freeze',
    'from',
    'full',
    'grant',
    'group',
    'having',
    'ilike',
    'in',
    'initially',
    'inner',
    'intersect',
    'into',
    'is',
    'isnull',
    'join',
    'lateral',
    'leading',
    'left',
    'like',
    'limit',
    'localtime',
    'localtimestamp',
    'natural',
    'not',
    'notnull',
    'null',
    'offset',
    'on',
    'only',
    'or',
    'order',
    'outer',
    'overlaps',
    'placing',
    'primary',
    'references',
    'returning',
    'right',
    'select',
    'session_user',
    'similar',
    'some',
    'symmetric',
    'system_user',
    'table',
    'tablesample',
    'then',
    'to',
    'trailing',
    'true',
    'union',
    'unique',
    'user',
    'using',
    'variadic',
    'verbose',
    'when',
    'where',
    'window',
    'with',
}


def maybe_quote(ident: str) -> str:
    # SQL identifiers and key words must begin with a letter (a-z, but also
    # letters with diacritical marks and non-Latin letters) or an underscore
    # (_). Subsequent characters in an identifier or key word can be letters,
    # underscores, digits (0-9), or dollar signs ($).
    # FIXME: find stricter SQL definition but this will do for now (?)
    # odoo is generally case-sensitive so non-lowercase names must be quoted
    if ident.isidentifier() and ident not in RESERVED and ident.casefold() == ident:
        return ident
    return quote(ident)

def install(Model, field, index: 'Index', existing: Optional[str] = None):
    expr = index.to_sql(Model, field)
    if not expr:
        return

    if existing:
        if expr.lower() == existing.lower():
            return

        _logger.warning(
            "Ignoring index: already exists with a different definition, "
            "you may want to update the index to the new version\n"
            "current: %s\n    new: %s",
            existing,
            expr
        )
        return

    with Model.env.cr.savepoint(flush=False):
        Model.env.cr.execute(expr)

class Nulls(enum.Enum):
    # maybe as convenient alias for $field IS NOT NULL?
    # NO = enum.auto()
    DISTINCT = enum.auto()
    # PG15 only
    # NOT_DISTINCT = enum.auto()

@dataclasses.dataclass
class Index(ABC):
    method: str = 'btree'
    # partial index condition, `{field}` will expand to the host field's name
    # (for single-field indexes)
    where: str = ''

    def to_sql(self, Model, field):
        expression = self.expression(Model, field)
        if expression is None:
            return

        schema = 'public'
        table = Model._table
        # TODO: pass table and name from outside?
        index_name = sql.make_index_name(table, field.name)
        where = ''
        if self.where:
            if self.where.format(field=field.name).isidentifier():
                where = f' where {self.where}'
            else:
                where = f' where ({self.where})'
        return (
            f'create index {maybe_quote(index_name)} '
            f'on {maybe_quote(schema)}.{maybe_quote(table)} '
            f'using {self.method} '
            f'({expression})'
            f'{where}'
        ).format(field=field.name)

    def expression(self, Model, field):
        if field.translate:
            _logger.warning(
                "Using a non-trigram index on translated field %s is "
                "useless, ignoring.",
                field
            )
            return None

        return maybe_quote(field.name)


@dataclasses.dataclass
class unique(Index):
    nulls: Nulls = Nulls.DISTINCT
    # error message on constraint failure
    message: str = ''

    def to_sql(self, Model, field):
        query = super().to_sql(Model, field)
        if query is None:
            return None

        return query.replace('create index', 'create unique index')


@dataclasses.dataclass
class btree(Index):
    pass

# maybe should be class methods of btree?
def not_null(**kw) -> btree:
    return btree(**kw, where="{field} is not null")

@dataclasses.dataclass
class _boolean(Index):
    def expression(self, Model, field):
        if field.type != 'boolean':
            _logger.warning(
                "Boolean partial indexes should only be used on boolean "
                "fields, %s (%s) is incorrect", field, field.type)
            return
        # not useful to index the value we're specifically filtering on, so
        # index id instead to get a covering index
        return 'id'

@dataclasses.dataclass
class true(_boolean):
    where: str = '{field}'

@dataclasses.dataclass
class false(_boolean):
    where: str = 'not {field}'

@dataclasses.dataclass
class hash(Index): # pylint: disable=redefined-builtin
    method: str = 'hash'

@dataclasses.dataclass
class trigram(Index):
    method: str = 'gin'
    def expression(self, Model, field):
        expr = maybe_quote(field.name)
        if field.translate:
            expr = f"jsonb_path_query_array({expr}, '$.*'::jsonpath)"
        if field.column_type[0] != 'text':
            expr = f'({expr})::text'
        if hasattr(field, 'unaccent') and field.unaccent:
            if Model.env.registry.has_unaccent == FunctionStatus.INDEXABLE:
                expr = get_unaccent_wrapper(Model.env.cr)(expr)
            else:
                if Model.env.registry.has_unaccent == FunctionStatus.PRESENT:
                    warnings.warn("Unaccent present but not immutable")
                expr = f'({expr})'
        else:
            expr = f'({expr})'

        # there's actually a failure point: if `field` is compatible with
        # gin_trgm_ops (which is?) and neither function gets applied, then
        # there are no wrapper parens or type casting
        return f'{expr} gin_trgm_ops'


STRING_TO_INDEX: Dict[str, Index] = {
    'trigram': trigram(),
    'btree': btree(),
    'btree_not_null': not_null(),
}
