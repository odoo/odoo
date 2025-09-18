"""
Search and query mixin for BaseModel.

This module provides the SearchMixin class containing all search and query-related
methods. BaseModel inherits from this mixin.

Methods:
- search_count: Return the number of records matching a domain
- search: Search for records matching a domain
- search_fetch: Search and fetch fields in one query
- _search_display_name: Search on display_name field
- name_search: Search records by display name pattern
- _check_qorder: Validate order specification
- _order_to_sql: Convert order string to SQL
- _order_field_to_sql: Convert a single order field to SQL
- _search: Private search implementation
- _as_query: Convert recordset to a Query object
- search_read: Search and read records in one operation
"""

import contextlib
import logging
import time
import typing
from collections.abc import Sequence
from typing import Self

from odoo.exceptions import LockError, UserError
from odoo.tools import SQL, Query, partition
from odoo.tools.orm_profiler import _orm_profiling_enabled

from ... import decorators as api
from ..._typing import DomainType, ValuesType
from ...domain import Domain
from ...parsing import parse_field_expr, regex_order
from ...primitives import COLLECTION_TYPES, NewId

if typing.TYPE_CHECKING:
    from ...fields import Field

_logger = logging.getLogger("odoo.models")
_orm_read = logging.getLogger("odoo.orm.read")

# Pre-built SQL constants for ORDER BY — avoids repeated SQL() allocation
_SQL_ASC = SQL("ASC")
_SQL_DESC = SQL("DESC")
_SQL_NULLS_FIRST = SQL("NULLS FIRST")
_SQL_NULLS_LAST = SQL("NULLS LAST")
_SQL_DIR = {"ASC": _SQL_ASC, "DESC": _SQL_DESC}
_SQL_NULLS = {"NULLS FIRST": _SQL_NULLS_FIRST, "NULLS LAST": _SQL_NULLS_LAST}


class SearchMixin:
    """Mixin providing search and query functionality.

    This mixin is inherited by BaseModel and provides methods for searching
    records, building queries, and handling order specifications.
    """

    __slots__ = ()

    # Type hints for attributes provided by BaseModel (runtime)
    _fields: dict
    _table: str
    _name: str
    _order: str
    _active_name: str | None
    _rec_name: str | None
    _rec_names_search: list[str] | None
    _ids: tuple
    env: typing.Any

    @api.model
    @api.readonly
    def search_count(self, domain: DomainType, limit: int | None = None) -> int:
        """Return the number of records in the current model matching
        :ref:`the provided domain <reference/orm/domains>`.

        :param domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param limit: maximum number of record to count (upperbound) (default: all)

        This is a high-level method, which should not be overridden. Its actual
        implementation is done by method :meth:`_search`.
        """
        _debug = _orm_read.isEnabledFor(logging.DEBUG)
        _agg = _orm_profiling_enabled
        if _debug or _agg:
            _t0 = time.perf_counter()

        query = self._search(domain, limit=limit)
        count = len(query)

        if _debug or _agg:
            _t_end = time.perf_counter()
        if _debug:
            _orm_read.debug(
                "[%.3f ms] search_count %s: domain=%s, limit=%s -> %d",
                (_t_end - _t0) * 1000,
                self._name,
                str(domain)[:200],
                limit,
                count,
            )
        if _agg and (p := self.env.transaction._orm_profiler):
            p.record_search(self._name, count, _t_end - _t0)

        return count

    @api.model
    @api.readonly
    def search(
        self,
        domain: DomainType,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> Self:
        """Search for the records that satisfy the given ``domain``
        :ref:`search domain <reference/orm/domains>`.

        :param domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param offset: number of results to ignore (default: none)
        :param limit: maximum number of records to return (default: all)
        :param order: sort string
        :returns: at most ``limit`` records matching the search criteria
        :raise AccessError: if user is not allowed to access requested information

        This is a high-level method, which should not be overridden. Its actual
        implementation is done by method :meth:`_search`.
        """
        return self.search_fetch(domain, [], offset=offset, limit=limit, order=order)

    @api.model
    @api.private
    @api.readonly
    def search_fetch(
        self,
        domain: DomainType,
        field_names: Sequence[str] | None = None,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> Self:
        """Search for the records that satisfy the given ``domain``
        :ref:`search domain <reference/orm/domains>`, and fetch the given fields
        to the cache.  This method is like a combination of methods :meth:`search`
        and :meth:`fetch`, but it performs both tasks with a minimal number of
        SQL queries.

        :param domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param field_names: a collection of field names to fetch, or ``None`` for
            all accessible fields marked with ``prefetch=True``
        :param offset: number of results to ignore (default: none)
        :param limit: maximum number of records to return (default: all)
        :param order: sort string
        :returns: at most ``limit`` records matching the search criteria
        :raise AccessError: if user is not allowed to access requested information
        """
        _debug = _orm_read.isEnabledFor(logging.DEBUG)
        _agg = _orm_profiling_enabled
        if _debug or _agg:
            _t0 = time.perf_counter()

        # first determine a query that satisfies the domain and access rules
        query = self._search(
            domain, offset=offset, limit=limit, order=order or self._order
        )
        if _debug:
            _t_search = time.perf_counter()

        if query.is_empty():
            # optimization: don't execute the query at all
            if not self.env.su:  # check access to fields
                self._determine_fields_to_fetch(field_names)
            if _debug:
                _orm_read.debug(
                    "[%.3f ms] search_fetch %s: domain=%s -> 0 records (empty query)"
                    " | search=%.1f",
                    (time.perf_counter() - _t0) * 1000,
                    self._name,
                    str(domain)[:200],
                    (_t_search - _t0) * 1000,
                )
            if _agg and (p := self.env.transaction._orm_profiler):
                p.record_search(self._name, 0, time.perf_counter() - _t0)
            return self.browse()

        fields_to_fetch = self._determine_fields_to_fetch(field_names)
        if _debug:
            _t_fields = time.perf_counter()

        result = self._fetch_query(query, fields_to_fetch)

        if _debug or _agg:
            _t_end = time.perf_counter()
        if _debug:
            _orm_read.debug(
                "[%.3f ms] search_fetch %s: domain=%s, offset=%d, limit=%s -> %d records"
                " | search=%.1f fields=%.1f fetch=%.1f",
                (_t_end - _t0) * 1000,
                self._name,
                str(domain)[:200],
                offset,
                limit,
                len(result),
                (_t_search - _t0) * 1000,
                (_t_fields - _t_search) * 1000,
                (_t_end - _t_fields) * 1000,
            )
        if _agg and (p := self.env.transaction._orm_profiler):
            p.record_search(self._name, len(result), _t_end - _t0)

        return result

    @api.model
    def _search_display_name(self, operator, value):
        """
        Returns a domain that matches records whose display name matches the
        given ``name`` pattern when compared with the given ``operator``.
        This method is used to implement the search on the ``display_name``
        field, and can be overridden to change the search criteria.
        The default implementation searches the fields defined in `_rec_names_search`
        or `_rec_name`.
        """
        search_fnames = self._rec_names_search or (
            [self._rec_name] if self._rec_name else []
        )
        if not search_fnames:
            _logger.warning(
                "Cannot search on display_name, no _rec_name or _rec_names_search defined on %s",
                self._name,
            )
            # do not restrain anything
            return Domain.TRUE
        if operator.endswith("like") and not value and "=" not in operator:
            # optimize out the default criterion of ``like ''`` that matches everything
            # return all when operator is positive
            return (
                Domain.FALSE if operator in Domain.NEGATIVE_OPERATORS else Domain.TRUE
            )
        aggregator = Domain.AND if operator in Domain.NEGATIVE_OPERATORS else Domain.OR
        domains = []
        for field_name in search_fnames:
            # field_name may be a sequence of field names (partner_id.name)
            # retrieve the last field in the sequence
            model = self
            for fname in field_name.split("."):
                field = model._fields[fname]
                model = self.env.get(field.comodel_name)
            # depending on the operator, we may need to cast the value to the type of the field
            # ignore if we cannot convert
            if field.relational:
                # relational fields will search on the display_name
                domains.append([(field_name + ".display_name", operator, value)])
            elif operator.endswith("like"):
                domains.append([(field_name, operator, value)])
            elif isinstance(value, COLLECTION_TYPES):
                typed_value = []
                for v in value:
                    with contextlib.suppress(ValueError, TypeError):
                        typed_value.append(field.convert_to_write(v, self))
                domains.append([(field_name, operator, typed_value)])
            else:
                with contextlib.suppress(ValueError):
                    typed_value = field.convert_to_write(value, self)
                    domains.append([(field_name, operator, typed_value)])
        return aggregator(domains)

    @api.model
    @api.readonly
    def name_search(
        self,
        name: str = "",
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[tuple[int, str]]:
        """Search for records that have a display name matching the given
        ``name`` pattern when compared with the given ``operator``, while also
        matching the optional search domain (``domain``).

        This is used for example to provide suggestions based on a partial
        value for a relational field. Should usually behave as the reverse of
        ``display_name``, but that is not guaranteed.

        This method is equivalent to calling :meth:`~.search` with a search
        domain based on ``display_name`` and mapping id and display_name on
        the resulting search.

        :param name: the name pattern to match
        :param domain: search domain (see :meth:`~.search` for syntax),
                       specifying further restrictions
        :param operator: domain operator for matching ``name``,
                         such as ``'like'`` or ``'='``.
        :param limit: max number of records to return
        :return: list of pairs ``(id, display_name)`` for all matching records.
        """
        domain = Domain("display_name", operator, name) & Domain(domain or Domain.TRUE)
        records = self.search_fetch(domain, ["display_name"], limit=limit)
        return [(record.id, record.display_name) for record in records.sudo()]

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
        """Return an :class:`SQL` object that represents the given ORDER BY
        clause, without the ORDER BY keyword.  The method also checks whether
        the fields in the order are accessible for reading.
        """
        order = order or self._order
        if not order:
            return SQL.EMPTY
        self._check_qorder(order)

        alias = alias or self._table

        terms = []
        for order_part in order.split(","):
            order_match = regex_order.match(order_part)
            assert order_match is not None, "No match found"
            field_name = order_match["field"]

            direction = (order_match["direction"] or "").upper()
            nulls = (order_match["nulls"] or "").upper()
            if reverse:
                direction = "ASC" if direction == "DESC" else "DESC"
                if nulls:
                    nulls = "NULLS LAST" if nulls == "NULLS FIRST" else "NULLS FIRST"

            sql_direction = _SQL_DIR.get(direction, SQL.EMPTY)
            sql_nulls = _SQL_NULLS.get(nulls, SQL.EMPTY)

            if property_name := order_match["property"]:
                # field_name is an expression
                field_name = f"{field_name}.{property_name}"
            term = self._order_field_to_sql(
                alias, field_name, sql_direction, sql_nulls, query
            )
            if term:
                terms.append(term)

        return SQL(", ").join(terms)

    def _order_field_to_sql(
        self,
        alias: str,
        field_name: str,
        direction: SQL,
        nulls: SQL,
        query: Query,
    ) -> SQL:
        """Return an :class:`SQL` object that represents the ordering by the
        given field.  The method also checks whether the field is accessible for
        reading.

        :param direction: one of ``SQL("ASC")``, ``SQL("DESC")``, ``SQL()``
        :param nulls: one of ``SQL("NULLS FIRST")``, ``SQL("NULLS LAST")``, ``SQL()``
        """
        # field_name is an expression
        fname, property_name = parse_field_expr(field_name)
        field = self._fields.get(fname)
        if not field:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")

        if field.type == "many2one":
            seen = self.env.context.get("__m2o_order_seen", ())
            if field in seen:
                return SQL.EMPTY
            self = self.with_context(__m2o_order_seen=frozenset((field, *seen)))

            # figure out the applicable order_by for the m2o
            # special case: ordering by "x_id.id" doesn't recurse on x_id's comodel
            comodel = self.env[field.comodel_name]
            if property_name == "id":
                coorder = "id"
                sql_field = self._field_to_sql(alias, fname, query)
            else:
                coorder = comodel._order
                sql_field = self._field_to_sql(alias, field_name, query)

            if coorder == "id":
                if not query._any_value_orderby:
                    query._order_groupby.append(sql_field)
                return SQL("%s %s %s", sql_field, direction, nulls)

            # instead of ordering by the field's raw value, use the comodel's
            # order on many2one values
            terms = []
            if nulls.code == "NULLS FIRST":
                terms.append(SQL("%s IS NOT NULL", sql_field))
            elif nulls.code == "NULLS LAST":
                terms.append(SQL("%s IS NULL", sql_field))

            # LEFT JOIN the comodel table, in order to include NULL values, too
            _comodel, coalias = field.join(self, alias, query)

            # delegate the order to the comodel
            reverse = direction.code == "DESC"
            term = comodel._order_to_sql(coorder, query, alias=coalias, reverse=reverse)
            if term:
                terms.append(term)
            return SQL(", ").join(terms)

        sql_field = self._field_to_sql(alias, field_name, query)
        if field.type == "boolean":
            sql_field = SQL("COALESCE(%s, FALSE)", sql_field)

        if query._any_value_orderby:
            # Use ANY_VALUE() (PG16+) instead of adding to GROUP BY.
            # The column is functionally dependent on the grouped column
            # (e.g., partner.name depends on partner_id), so any arbitrary
            # value from the group is correct for ordering.
            sql_field = SQL("ANY_VALUE(%s)", sql_field)
        else:
            query._order_groupby.append(sql_field)

        return SQL("%s %s %s", sql_field, direction, nulls)

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
        """
        Private implementation of search() method.

        No default order is applied when the method is invoked without parameter ``order``.

        :return: a :class:`Query` object that represents the matching records

        This method may be overridden to modify the domain being searched, or to
        do some post-filtering of the resulting query object. Be careful with
        the latter option, though, as it might hurt performance. Indeed, by
        default the returned query object is not actually executed, and it can
        be injected as a value in a domain in order to generate sub-queries.

        The `active_test` flag specifies whether to filter only active records.
        The `bypass_access` controls whether or not permissions should be
        checked on the model and record rules should be applied.
        """
        _debug = _orm_read.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()

        check_access = not (self.env.su or bypass_access)
        if check_access:
            self.browse().check_access("read")
        if _debug:
            _t_acl = time.perf_counter()

        domain = Domain(domain)
        # inactive records unless they were explicitly asked for
        if (
            self._active_name
            and active_test
            and self.env.context.get("active_test", True)
            and not any(
                leaf.field_expr == self._active_name
                for leaf in domain.iter_conditions()
            )
        ):
            domain &= Domain(self._active_name, "=", True)

        # build the query
        domain = domain.optimize_full(self)
        if domain.is_false():
            return self.browse()._as_query()

        # --- Backend dispatch: DictBackend or PostgreSQL ---
        storage = self.env.transaction.storage
        if storage is not None:
            return self._search_storage(domain, offset, limit, order, storage)

        query = Query(self.env, self._table, self._table_sql)
        if not domain.is_true():
            query.add_where(domain._to_sql(self, self._table, query))
        if _debug:
            _t_domain = time.perf_counter()

        # security access domain
        if check_access:
            self_sudo = self.sudo().with_context(active_test=False)
            sec_domain = self.env["ir.rule"]._compute_domain(self._name, "read")
            sec_domain = sec_domain.optimize_full(self_sudo)
            if sec_domain.is_false():
                return self.browse()._as_query()
            if not sec_domain.is_true():
                query.add_where(sec_domain._to_sql(self_sudo, self._table, query))
        if _debug:
            _t_rules = time.perf_counter()

        # add order and limits
        if order:
            query.order = self._order_to_sql(order, query)

        # In RPC, None is not available; False is used instead to mean "no limit"
        # Note: True is kept for backward-compatibility (treated as 1)
        if limit is not None and limit is not False:
            query.limit = limit
        if offset is not None:
            query.offset = offset

        if _debug:
            _t_end = time.perf_counter()
            _orm_read.debug(
                "[%.3f ms] _search %s | acl=%.1f domain=%.1f rules=%.1f query=%.1f",
                (_t_end - _t0) * 1000,
                self._name,
                (_t_acl - _t0) * 1000,
                (_t_domain - _t_acl) * 1000,
                (_t_rules - _t_domain) * 1000,
                (_t_end - _t_rules) * 1000,
            )
        return query

    def _search_storage(self, domain, offset, limit, order, storage) -> Query:
        """Evaluate domain against DictBackend using Python predicates.

        Fetches all record IDs from storage, loads values into cache, then
        uses ``filtered_domain()`` (which calls ``domain._as_predicate()``)
        to evaluate the domain in pure Python.

        :param domain: Optimized Domain object.
        :param offset: Number of records to skip.
        :param limit: Maximum number of records to return.
        :param order: Order string (e.g. 'name asc, id desc').
        :param storage: DictBackend instance.
        :return: Query with ``_ids`` set to matching record IDs.
        """
        # 1. Get all record IDs from storage
        all_ids = storage.table_ids(self._table)
        if not all_ids:
            return self.browse()._as_query(ordered=False)

        # 2. Load storage values into cache — batch by field to avoid
        #    per-record browse() allocations and per-cell method overhead.
        all_records = self.browse(all_ids)
        tbl = storage._tables.get(self._table, {})

        # Pre-resolve storable fields and their cache dicts once.
        # For context-dependent fields (depends_context), _get_cache() needs
        # env.company which may not be available in DictBackend tests that
        # don't seed res.users.  Use env._core.field_data() directly for
        # non-context fields, and try/except for the rest.
        env = self.env
        fields_meta = self._fields
        _fdc = env._field_depends_context
        storable: list[tuple] = []  # (fname, field, field_cache)
        # Use a single sentinel browse record for convert_to_cache calls.
        sentinel = self.browse(all_ids[0]) if all_ids else self.browse()
        for fname, field in fields_meta.items():
            if fname != "id" and field.store and field.column_type:
                if field not in _fdc:
                    storable.append((fname, field, env._core.field_data(field)))
                else:
                    try:
                        storable.append((fname, field, field._get_cache(env)))
                    except Exception:
                        pass  # cache_key can't resolve (e.g. env.company)

        # Batch-load: iterate fields in outer loop, records in inner loop.
        # This writes directly to the cache dict without per-record browse()
        # or per-cell _update_cache() overhead.
        for fname, field, field_cache in storable:
            convert = field.convert_to_cache
            for record_id in all_ids:
                row = tbl.get(record_id)
                if row is not None and fname in row:
                    field_cache[record_id] = convert(row[fname], sentinel)

        # 3. Evaluate domain using existing Python predicates
        if not domain.is_true():
            matching = all_records.filtered_domain(domain)
        else:
            matching = all_records

        # 4. Apply ordering (Python-side via sorted())
        if order:
            matching = matching.sorted(key=order)

        # 5. Apply offset/limit
        ids = matching._ids
        if offset:
            ids = ids[offset:]
        if limit is not None and limit is not False:
            ids = ids[:limit]

        # 6. Return Query with known IDs (no SQL needed)
        query = Query(self.env, self._table, self._table_sql)
        query._ids = tuple(ids)
        return query

    def _as_query(self, ordered: bool = True) -> Query:
        """Return a :class:`Query` that corresponds to the recordset ``self``.
        This method is convenient for making a query object with a known result.

        :param ordered: whether the recordset order must be enforced by the query
        """
        # DictBackend: set _ids directly — skip SQL unnest
        if self.env.transaction.storage is not None:
            query = Query(self.env, self._table, self._table_sql)
            query._ids = tuple(self._ids)
            return query
        query = Query(self.env, self._table, self._table_sql)
        query.set_result_ids(self._ids, ordered)
        return query

    @api.model
    @api.readonly
    def search_read(
        self,
        domain: DomainType | None = None,
        fields: Sequence[str] | None = None,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        **read_kwargs,
    ) -> list[ValuesType]:
        """Perform a :meth:`search_fetch` followed by a :meth:`_read_format`.

        :param domain: Search domain, see ``args`` parameter in :meth:`search`.
            Defaults to an empty domain that will match all records.
        :param fields: List of fields to read, see ``fields`` parameter in :meth:`read`.
            Defaults to all fields.
        :param offset: Number of records to skip, see ``offset`` parameter in :meth:`search`.
            Defaults to 0.
        :param limit: Maximum number of records to return, see ``limit`` parameter in :meth:`search`.
            Defaults to no limit.
        :param order: Columns to sort result, see ``order`` parameter in :meth:`search`.
            Defaults to no sort.
        :param read_kwargs: All read keywords arguments used to call
            ``read(..., **read_kwargs)`` method e.g. you can use
            ``search_read(..., load='')`` in order to avoid computing display_name
        :return: List of dictionaries containing the asked fields.
        """
        if not fields:
            fields = list(self.fields_get(attributes=()))
        records = self.search_fetch(
            domain or [], fields, offset=offset, limit=limit, order=order
        )

        # Method _read_format() ignores 'active_test', but it would forward it
        # to any downstream search call(e.g. for x2m or computed fields), and
        # this is not the desired behavior. The flag was presumably only meant
        # for the main search().
        if "active_test" in self.env.context:
            context = dict(self.env.context)
            del context["active_test"]
            records = records.with_context(context)

        return records._read_format(fnames=fields, **read_kwargs)

    # -------------------------------------------------------------------------
    # SQL traversal utilities
    # -------------------------------------------------------------------------

    def _traverse_related_sql(self, alias: str, field: Field, query: Query) -> tuple:
        """Traverse the related `field` and add needed join to the `query`.

        :returns: tuple ``(model, field, alias)``, where ``field`` is the last
            field in the sequence, ``model`` is that field's model, and
            ``alias`` is the model's table alias
        """
        assert field.related and not field.store
        if not (self.env.su or field.compute_sudo or field.inherited):
            raise ValueError(
                f"Cannot convert {field} to SQL because it is not a sudoed related or inherited field"
            )

        model = self.sudo(self.env.su or field.compute_sudo)
        *path_fnames, last_fname = field.related.split(".")
        for path_fname in path_fnames:
            path_field = model._fields[path_fname]
            if path_field.type != "many2one":
                raise ValueError(
                    f"Cannot convert {field} (related={field.related}) to SQL because {path_fname} is not a Many2one"
                )
            model, alias = path_field.join(model, alias, query)

        return model, model._fields[last_fname], alias

    def _field_to_sql(
        self, alias: str, field_expr: str, query: Query | None = None
    ) -> SQL:
        """Return an :class:`SQL` object that represents the value of the given
        field from the given table alias, in the context of the given query.
        The method also checks that the field is accessible for reading.

        The query object is necessary for inherited fields, many2one fields and
        properties fields, where joins are added to the query.
        """
        fname, property_name = parse_field_expr(field_expr)
        field = self._fields.get(fname)
        if not field:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")

        if field.related and not field.store:
            model, field, alias = self._traverse_related_sql(alias, field, query)
            related_expr = (
                field.name if not property_name else f"{field.name}.{property_name}"
            )
            return model._field_to_sql(alias, related_expr, query)

        self._check_field_access(field, "read")

        sql = field.to_sql(self, alias)
        if property_name:
            sql = field.property_to_sql(sql, property_name, self, alias, query)
        return sql

    # -------------------------------------------------------------------------
    # Existence checking and row locking
    # -------------------------------------------------------------------------

    @api.private
    def exists(self) -> Self:
        """The subset of records in ``self`` that exist.
        It can be used as a test on records::

            if record.exists():
                ...

        By convention, new records are returned as existing.
        """
        new_ids, ids = partition(lambda i: isinstance(i, NewId), self._ids)
        if not ids:
            return self
        # DictBackend: check storage directly — no SQL needed
        storage = self.env.transaction.storage
        if storage is not None:
            tbl = storage._tables.get(self._table, {})
            valid_ids = {*[i for i in ids if i in tbl], *new_ids}
            return self.browse(i for i in self._ids if i in valid_ids)
        query = Query(self.env, self._table, self._table_sql)
        query.add_where(
            SQL("%s = ANY(%s)", SQL.identifier(self._table, "id"), list(ids))
        )
        real_ids = (id_ for [id_] in self.env.execute_query(query.select()))
        valid_ids = {*real_ids, *new_ids}
        return self.browse(i for i in self._ids if i in valid_ids)

    @api.private
    def lock_for_update(self, *, allow_referencing: bool = False) -> None:
        """Grab an exclusive write-lock to the rows with the given ids.

        This avoids blocking processing on the records due to concurrent
        modifications. If all records couldn't be locked, a `LockError`
        exception is raised.

        :param allow_referencing: Acquire a row lock which allows for other
            transactions to reference this record. Use only when modifying
            values that are not identifiers.
        :raises: ``LockError`` when some records could not be locked
        """
        ids = {id_ for id_ in self._ids if id_}
        if not ids:
            return
        query = Query(self.env, self._table, self._table_sql)
        query.add_where(
            SQL("%s = ANY(%s)", SQL.identifier(self._table, "id"), list(ids))
        )
        # Use SKIP LOCKED instead of NOWAIT because the later aborts the
        # transaction and we do not want to use SAVEPOINTS.
        if allow_referencing:
            lock_sql = SQL("FOR NO KEY UPDATE SKIP LOCKED")
        else:
            lock_sql = SQL("FOR UPDATE SKIP LOCKED")
        rows = self.env.execute_query(SQL("%s %s", query.select(), lock_sql))
        if len(rows) != len(ids):
            raise LockError(self.env._("Cannot grab a lock on records"))

    @api.private
    def try_lock_for_update(
        self, *, allow_referencing: bool = False, limit: int | None = None
    ) -> Self:
        """Grab an exclusive write-lock on some rows with the given ids.

        Skip locked records and browse the records that could be locked.

        :param allow_referencing: Acquire a row lock which allows for other
            transactions to reference this record. Use only when modifying
            values that are not identifiers.
        :param limit: The maximum number of rows to lock
        :return: The recordset of locked records
        """
        new_ids, ids = partition(lambda i: isinstance(i, NewId), self._ids)
        if limit is not None:
            if len(new_ids) >= limit:
                return self.browse(new_ids[:limit])
            # keep the order of ids when trying to lock
            query = self.browse(ids)._as_query(ordered=True)
            query.limit = limit - len(new_ids)
        else:
            query = Query(self.env, self._table, self._table_sql)
            query.add_where(
                SQL("%s = ANY(%s)", SQL.identifier(self._table, "id"), list(ids))
            )
        if not ids:
            return self
        if allow_referencing:
            lock_sql = SQL("FOR NO KEY UPDATE SKIP LOCKED")
        else:
            lock_sql = SQL("FOR UPDATE SKIP LOCKED")
        sql = SQL("%s %s", query.select(), lock_sql)
        real_ids = (id_ for [id_] in self.env.execute_query(sql))
        valid_ids = {*real_ids, *new_ids}
        return self.browse(i for i in self._ids if i in valid_ids)


# Import _ for translations - done after class definition to avoid issues
from odoo.tools.translate import _
