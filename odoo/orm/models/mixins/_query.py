import logging
import typing
from typing import Self

from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools import SQL, Query, ormcache, partition
from odoo.tools.translate import _

from ... import decorators as api
from ..._typing import DomainType
from ...constants import SQL_ORDER_DIR, SQL_ORDER_NULLS
from ...domain import Domain
from ...parsing import parse_field_expr, regex_order
from ...primitives import NewId
from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from ..._typing import BaseModel
    from ...fields.base import Field

_logger = logging.getLogger("odoo.models")
_orm_read = logging.getLogger("odoo.orm.read")
_debug = DebugLog(__name__)


class _QueryMixin(_ModelStubs):
    __slots__ = ()

    def _check_qorder(self, word: str) -> None:
        if not regex_order.match(word):
            raise UserError(
                _(
                    'Invalid "order" specified (%s).'
                    ' A valid "order" specification is a comma-separated list of valid field names'
                    " (optionally followed by asc/desc for the direction)",
                    word,
                )
            )

    def _order_to_sql(
        self,
        order: str,
        query: Query,
        alias: str | None = None,
        reverse: bool = False,
    ) -> SQL:
        order = order or self._order
        if not order:
            return SQL.EMPTY
        self._check_qorder(order)

        alias = alias or self._table

        terms = []
        for order_part in order.split(","):
            order_match = regex_order.match(order_part)
            if order_match is None:
                raise RuntimeError(
                    f"Order part {order_part!r} did not match regex_order "
                    f"despite passing _check_qorder({order!r})"
                )
            field_name = order_match["field"]

            direction = (order_match["direction"] or "").upper()
            nulls = (order_match["nulls"] or "").upper()
            if reverse:
                direction = "ASC" if direction == "DESC" else "DESC"
                if nulls:
                    nulls = "NULLS LAST" if nulls == "NULLS FIRST" else "NULLS FIRST"

            sql_direction = SQL_ORDER_DIR.get(direction, SQL.EMPTY)
            sql_nulls = SQL_ORDER_NULLS.get(nulls, SQL.EMPTY)

            if property_name := order_match["property"]:
                field_name = f"{field_name}.{property_name}"
            term = self._order_field_to_sql(
                alias, field_name, sql_direction, sql_nulls, query
            )
            if term:
                terms.append(term)

        return SQL(", ").join(terms)

    @api.model
    @ormcache("field_name", "self.env.su", "self.env.user._get_group_ids()")
    def _is_field_sortable(self, field_name: str) -> bool:
        try:
            query = self._as_query(ordered=False)
            term = self._order_field_to_sql(
                self._table, field_name, SQL.EMPTY, SQL.EMPTY, query
            )
            sortable = bool(term)
        except ValueError, AccessError, NotImplementedError:
            sortable = False
        _debug.perf.count(
            "query.field_sortable_probed",
            model=self._name,
            field=field_name,
            sortable=sortable,
            su=self.env.su,
        )
        return sortable

    def _order_field_to_sql(
        self,
        alias: str,
        field_name: str,
        direction: SQL,
        nulls: SQL,
        query: Query,
    ) -> SQL:
        fname, property_name = parse_field_expr(field_name)
        field = self._fields.get(fname)
        if not field:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")

        if not self._has_field_access(field, "read"):
            _logger.debug(
                "Ignoring ORDER BY %s.%s: not readable by user %s",
                self._name,
                field_name,
                self.env.uid,
            )
            _debug.logic(
                "query.order_field_unreadable",
                model=self._name,
                field=field_name,
                uid=self.env.uid,
            )
            return SQL.EMPTY

        if field.order_by_field:
            return self._order_field_to_sql(
                alias,
                field.order_by_field + field_name[len(fname) :],
                direction,
                nulls,
                query,
            )
        if field.order_by_sql:
            return getattr(self, field.order_by_sql)(
                field, alias, direction, nulls, query
            )

        if field.is_many2one:
            seen = self.env.context.get("__m2o_order_seen", ())
            if field in seen:
                _debug.logic(
                    "query.order_m2o_cycle",
                    model=self._name,
                    field=fname,
                    depth=len(seen),
                )
                return SQL.EMPTY
            self = self.with_context(__m2o_order_seen=frozenset((field, *seen)))

            comodel = self.env[field.comodel_name]
            if property_name == "id":
                coorder = "id"
                sql_field = self._field_to_sql(alias, fname, query)
            else:
                coorder = comodel._order
                sql_field = self._field_to_sql(alias, field_name, query)

            if coorder == "id":
                return self._order_value_to_sql(sql_field, direction, nulls, query)

            terms = []
            if nulls.code == "NULLS FIRST":
                terms.append(SQL("%s IS NOT NULL", sql_field))
            elif nulls.code == "NULLS LAST":
                terms.append(SQL("%s IS NULL", sql_field))

            _comodel, coalias = field.join(self, alias, query)

            reverse = direction.code == "DESC"
            term = comodel._order_to_sql(coorder, query, alias=coalias, reverse=reverse)
            if term:
                terms.append(term)
            return SQL(", ").join(terms)

        sql_field = self._field_to_sql(alias, field_name, query)
        if field.is_boolean:
            sql_field = SQL("COALESCE(%s, FALSE)", sql_field)
        return self._order_value_to_sql(sql_field, direction, nulls, query)

    def _order_value_to_sql(
        self, sql_value: SQL, direction: SQL, nulls: SQL, query: Query
    ) -> SQL:
        """The ORDER BY term for a value: under a grouped query the value is
        either aggregated or added to the GROUP BY, which an `order_by_sql`
        hook composing its own value must do the same way."""
        if query._any_value_orderby:
            sql_value = SQL("ANY_VALUE(%s)", sql_value)
        elif query._collect_order_groupby:
            query._order_groupby.append(sql_value)
        return SQL("%s %s %s", sql_value, direction, nulls)

    @api.model
    def _search(
        self,
        domain: DomainType,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        *,
        active_test: bool = True,
        bypass_access: bool = False,
    ) -> Query:
        prof = _OrmProfile(_orm_read)

        check_access = not (self.env.su or bypass_access)
        if check_access:
            self.browse().check_access("read")
        prof.mark("acl")

        domain = Domain(domain)
        if (
            self._active_name
            and active_test
            and self.env.context.get("active_test", True)
            and not any(
                leaf.field_expr == self._active_name
                for leaf in domain.iter_conditions()
            )
        ):
            _debug.logic(
                "query.search.active_test_added",
                model=self._name,
                field=self._active_name,
            )
            domain &= Domain(self._active_name, "=", True)

        backend = self.env.backend
        query = backend.search_raw(
            self, domain, offset, limit, order, check_access=check_access
        )
        if query is not None:
            prof.mark("raw")
            return query

        domain = domain.optimize_full(typing.cast("BaseModel", self))
        if domain.is_false():
            _debug.logic("query.search.domain_false", model=self._name)
            return self.browse()._as_query()

        return backend.search(
            self, domain, offset, limit, order, check_access=check_access, prof=prof
        )

    def _as_query(self, ordered: bool = True) -> Query:
        return self.env.backend.as_query(self, ordered)

    def _traverse_related_sql(
        self, alias: str, field: Field, query: Query
    ) -> tuple[typing.Any, Field, str]:
        if not (field.related and not field.store):
            raise ValueError(
                f"_traverse_related_sql expects a non-stored related field, got {field!r}"
            )
        if not (self.env.su or field.compute_sudo or field.inherited):
            raise ValueError(
                f"Cannot convert {field} to SQL because it is not a sudoed related or inherited field"
            )

        model = self.sudo(self.env.su or field.compute_sudo)
        *path_fnames, last_fname = field.related.split(".")
        for path_fname in path_fnames:
            path_field = model._fields[path_fname]
            if not (path_field.is_many2one or path_field.is_one2one):
                raise ValueError(
                    f"Cannot convert {field} (related={field.related}) to SQL because {path_fname} is not a Many2one or a One2one"
                )
            model, alias = path_field.join(model, alias, query)

        _debug.logic(
            "query.related_traversed",
            model=self._name,
            field=field.name,
            related=field.related,
            joins=len(path_fnames),
            target=model._name,
        )
        return model, model._fields[last_fname], alias

    def _field_to_sql(
        self, alias: str, field_expr: str, query: Query | None = None
    ) -> SQL:
        fname, property_name = parse_field_expr(field_expr)
        field = self._fields.get(fname)
        if not field:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")

        if field.related and not field.store:
            if query is None:
                raise ValueError(
                    f"query is required to convert related field {field} to SQL"
                )
            model, field, alias = self._traverse_related_sql(alias, field, query)
            related_expr = (
                field.name if not property_name else f"{field.name}.{property_name}"
            )
            return model._field_to_sql(alias, related_expr, query)

        self._check_field_access(field, "read")

        if field.value_sql:
            # the field names the method that composes its SQL: an expression
            # over other columns, a join it hangs on the query, a constant
            if property_name:
                raise ValueError(
                    f"{field_expr!r}: a property of a field that composes its own SQL"
                )
            return getattr(self, field.value_sql)(field, alias, query)

        if field.is_one2one:
            # no column on this side: the value is the id of the one comodel
            # row whose unique inverse names this row
            if property_name or query is None:
                raise ValueError(
                    f"{field_expr!r}: a One2one converts to SQL only as itself, with a query"
                )
            _comodel, coalias = field.join(self, alias, query)
            return SQL.identifier(coalias, "id")

        if not property_name and alias == self._table:
            # proven by the first fetch of the column to be exactly this
            # identifier (see _fetch_term); spelled once, reused by every
            # WHERE and ORDER BY on the model's own table
            term = field._column_term
            if term is not None:
                return term

        sql = field.to_sql(self, alias)
        if property_name:
            if query is None:
                raise ValueError(
                    f"query is required to convert property field expression"
                    f" {field_expr!r} to SQL"
                )
            sql = field.property_to_sql(sql, property_name, self, alias, query)
        return sql

    @api.private
    def exists(self) -> Self:
        new_ids, ids = partition(lambda i: isinstance(i, NewId), self._ids)
        if not ids:
            return self
        valid_ids = {*self.env.backend.get_existing_ids(self, ids), *new_ids}
        if _debug.logic.enabled and len(valid_ids) != len(self._ids):
            _debug.logic(
                "query.exists.missing",
                model=self._name,
                records=len(self._ids),
                missing=len(self._ids) - len(valid_ids),
            )
        # one record of a batch stays one record of the batch
        return self._spawn(
            self.env, tuple(i for i in self._ids if i in valid_ids), self._prefetch_ids
        )
