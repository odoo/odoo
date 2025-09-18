"""
Read operations mixin for BaseModel.

This module contains methods for reading records from the database:
- read(): High-level read API returning list of dicts
- _read_format(): Format cached values as read() output
- _fetch_field(): Fetch a single field from database
- fetch(): Ensure fields are in cache
- _determine_fields_to_fetch(): Determine which fields to fetch
- _fetch_query(): Execute fetch query and populate cache
- fields_get(): Return field definitions
- get_metadata(): Return record metadata (create/write info, xmlid)
"""

import logging
import time
import typing
from collections import defaultdict, deque
from collections.abc import Collection, Sequence
from typing import Self

from odoo.exceptions import MissingError
from odoo.libs.constants import PREFETCH_MAX
from odoo.tools import SQL, OrderedSet
from odoo.tools.misc import PENDING, SENTINEL
from odoo.tools.orm_profiler import _orm_profiling_enabled

from ... import decorators as api
from ..._typing import ValuesType
from ...primitives import LOG_ACCESS_COLUMNS

if typing.TYPE_CHECKING:
    from ...fields.base import Field
    from ...tools import Query

_logger = logging.getLogger("odoo.models")
_orm_read = logging.getLogger("odoo.orm.read")


class ReadMixin:
    """Mixin providing read and fetch operations for recordsets.

    This mixin contains methods for:
    - Reading records from the database (read, fetch)
    - Formatting cached values as dictionaries
    - Field metadata retrieval (fields_get, get_metadata)
    """

    __slots__ = ()

    @api.model
    def fields_get(
        self,
        allfields: Collection[str] | None = None,
        attributes: Collection[str] | None = None,
    ) -> dict[str, ValuesType]:
        """Return the definition of each field.

        The returned value is a dictionary (indexed by field name) of
        dictionaries. The _inherits'd fields are included. The string, help,
        and selection (if present) attributes are translated.

        :param allfields: fields to document, all if empty or not provided
        :param attributes: attributes to return for each field, all if empty or not provided
        :return: dictionary mapping field names to a dictionary mapping attributes to values.
        """
        res = {}
        for fname, field in self._fields.items():
            if allfields and fname not in allfields:
                continue
            if not self._has_field_access(field, "read"):
                continue

            description = field.get_description(self.env, attributes=attributes)
            if "readonly" in description:
                description["readonly"] = description[
                    "readonly"
                ] or not self._has_field_access(field, "write")
            res[fname] = description

        return res

    @api.readonly
    def read(
        self, fields: Sequence[str] | None = None, load: str = "_classic_read"
    ) -> list[ValuesType]:
        """Read the requested fields for the records in ``self``, and return their
        values as a list of dicts.

        :param fields: field names to return (default is all fields)
        :param load: loading mode, currently the only option is to set to
            ``None`` to avoid loading the `display_name` of m2o fields
        :return: a list of dictionaries mapping field names to their values,
                 with one dictionary per record
        :raise AccessError: if user is not allowed to access requested information
        :raise ValueError: if a requested field does not exist

        This is a high-level method that is not supposed to be overridden. In
        order to modify how fields are read from database, see methods
        :meth:`_fetch_query` and :meth:`_read_format`.
        """
        _debug = _orm_read.isEnabledFor(logging.DEBUG)
        _agg = _orm_profiling_enabled
        if _debug or _agg:
            _t0 = time.perf_counter()

        if not fields:
            fields = list(self.fields_get(attributes=()))
        else:
            # Sanitize field names: the web client may send non-string values
            # (e.g. integer field IDs) which are invalid for the ORM.
            _model_fields = self._fields
            bad = [
                f for f in fields if not isinstance(f, str) or f not in _model_fields
            ]
            if bad:
                _logger.warning("Invalid field(s) %r on %r, skipping", bad, self._name)
                fields = [
                    f for f in fields if isinstance(f, str) and f in _model_fields
                ]
            if not self and not self.env.su:
                # check field access, otherwise done during fetch()
                self._determine_fields_to_fetch(fields)
        self._origin.fetch(fields)
        if _debug:
            _t_fetch = time.perf_counter()
        result = self._read_format(fnames=fields, load=load)

        if _debug or _agg:
            _t_end = time.perf_counter()
        if _debug:
            _orm_read.debug(
                "[%.3f ms] read %s: %d records, %d fields" " | fetch=%.1f format=%.1f",
                (_t_end - _t0) * 1000,
                self._name,
                len(self),
                len(fields),
                (_t_fetch - _t0) * 1000,
                (_t_end - _t_fetch) * 1000,
            )
        if _agg and (p := self.env.transaction._orm_profiler):
            p.record_read(self._name, len(self), _t_end - _t0)

        return result

    # Field types whose convert_to_record + convert_to_read chain is
    # equivalent to ``False if v is None else v`` (or ``v or 0`` for
    # numeric types).  For these types we can inline the conversion and
    # skip 3 method calls per (record, field) pair in _read_format.
    _SCALAR_READ_TYPES = frozenset(
        {
            "boolean",
            "selection",
            "date",
            "datetime",
            "char",
            "text",  # non-translate only (translate needs dict lookup)
            "integer",
            "float",
            "monetary",
        }
    )

    def _read_format(
        self, fnames: Sequence[str], load: str = "_classic_read"
    ) -> list[ValuesType]:
        """Return a list of dictionaries mapping field names to their values,
        with one dictionary per record that exists.

        The output format is the one expected from the `read` method, which uses
        this method as its implementation for formatting values.

        For the properties fields, call convert_to_read_multi instead of convert_to_read
        to prepare everything (record existences, display name, etc) in batch.

        The current method is different from `read` because it retrieves its
        values from the cache without doing a query when it is avoidable.
        """
        use_display_name = load == "_classic_read"
        env = self.env
        ids = self._ids
        _fields = self._fields
        _SENTINEL = SENTINEL
        _PENDING = PENDING
        _scalar_types = self._SCALAR_READ_TYPES

        # Classify fields: scalar stored fields that can use the fast path
        # (inline dict.get + identity conversion) vs everything else that
        # needs singleton records for convert_to_record / __get__.
        scalar_fnames = []
        record_fnames = []
        for name in fnames:
            field = _fields[name]
            if (
                field.store
                and not field.relational
                and not callable(field.translate)
                and field.type in _scalar_types
            ):
                scalar_fnames.append(name)
            else:
                record_fnames.append(name)

        # Phase 1: Scalar stored fields — no singleton creation needed.
        # Inline cache dict.get, skip read_cache() / convert_to_record() /
        # convert_to_read() method calls.  For these field types the full
        # conversion chain is equivalent to:
        #   None  → none_val  (False, 0, or 0.0 depending on type)
        #   other → cache_value unchanged
        results = [{"id": id_} for id_ in ids]
        for name in scalar_fnames:
            field = _fields[name]
            field.ensure_computed(self)
            field_cache = field._get_cache(env)
            # Pre-compute the None replacement:
            #   boolean/selection/date/datetime/char/text → False
            #   integer → 0
            #   float/monetary → 0.0
            none_val = field.convert_to_record(None, None)
            for id_, vals in zip(ids, results, strict=False):
                if not vals:
                    continue
                cache_value = field_cache.get(id_, _SENTINEL)
                if cache_value is _SENTINEL or cache_value is _PENDING:
                    # Cache miss after fetch() — record likely missing or
                    # a NewId (new record whose value comes from _origin).
                    # Fall back to full __get__ path via singleton.
                    # Wrap in tuple — NewId.__bool__ is False, so bare
                    # browse(new_id) would produce an empty recordset.
                    try:
                        record = self.browse((id_,))
                        vals[name] = field.convert_to_read(
                            record[name], record, use_display_name
                        )
                    except MissingError:
                        vals.clear()
                elif cache_value is None:
                    vals[name] = none_val
                else:
                    vals[name] = cache_value

        if not record_fnames:
            return [vals for vals in results if vals]

        # Phase 2: Fields that need singleton records (relational, translate,
        # html, binary, json, properties, non-stored computed).
        # Create singleton records lazily (only when needed).
        data = list(zip(self, results, strict=False))

        for name in record_fnames:
            field = _fields[name]
            if field.type == "properties":
                values_list = []
                records = []
                valid_data = []
                for record, vals in data:
                    try:
                        values_list.append(record[name])
                        records.append(record.id)
                        valid_data.append((record, vals))
                    except MissingError:
                        vals.clear()

                prop_results = field.convert_to_read_multi(
                    values_list, self.browse(records)
                )
                for (_, vals), convert_result in zip(valid_data, prop_results, strict=True):
                    vals[name] = convert_result
                continue

            if field.store:
                # Stored field path: bypass Field.__get__, use explicit
                # precondition API (ensure_computed, read_cache).
                field.ensure_computed(self)
                _read_cache = field.read_cache
                convert_to_record = field.convert_to_record
                convert_to_read = field.convert_to_read
                for record, vals in data:
                    if not vals:
                        continue
                    hit, cache_value = _read_cache(record._ids[0], env)
                    if not hit:
                        try:
                            vals[name] = convert_to_read(
                                record[name], record, use_display_name
                            )
                        except MissingError:
                            vals.clear()
                        continue
                    try:
                        vals[name] = convert_to_read(
                            convert_to_record(cache_value, record),
                            record,
                            use_display_name,
                        )
                    except MissingError:
                        vals.clear()
                    except KeyError:
                        # Rare: translation miss in translated Char/Text fields.
                        # Fall back to standard __get__ path which handles this.
                        try:
                            vals[name] = convert_to_read(
                                record[name], record, use_display_name
                            )
                        except MissingError:
                            vals.clear()
            else:
                # Non-stored fields (computed, related, etc.) are not populated
                # by fetch(); they need Field.__get__ to trigger computation.
                convert = field.convert_to_read
                for record, vals in data:
                    if not vals:
                        continue
                    try:
                        vals[name] = convert(record[name], record, use_display_name)
                    except MissingError:
                        vals.clear()

        return [vals for record, vals in data if vals]

    def _fetch_field(self, field: Field) -> None:
        """Read from the database in order to fetch ``field`` (:class:`Field`
        instance) for ``self`` in cache.
        """
        # determine which fields can be prefetched
        if self.env.context.get("prefetch_fields", True) and field.prefetch:
            fnames = [
                name
                for name, f in self._fields.items()
                # select fields with the same prefetch group
                if f.prefetch == field.prefetch
                # discard fields with groups that the user may not access
                if self._has_field_access(f, "read")
            ]
            if field.name not in fnames:
                fnames.append(field.name)
        else:
            fnames = [field.name]
        self.fetch(fnames)

    @api.private
    def fetch(self, field_names: Collection[str] | None = None) -> None:
        """Make sure the given fields are in memory for the records in ``self``,
        by fetching what is necessary from the database.  Non-stored fields are
        mostly ignored, except for their stored dependencies. This method should
        be called to optimize code.

        :param field_names: a collection of field names to fetch, or ``None`` for
            all accessible fields marked with ``prefetch=True``
        :raise AccessError: if user is not allowed to access requested information

        This method is implemented thanks to methods :meth:`_search` and
        :meth:`_fetch_query`, and should not be overridden.
        """
        self = self._origin
        if not self or not (field_names is None or field_names):
            return

        _debug = _orm_read.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()

        fields_to_fetch = self._determine_fields_to_fetch(
            field_names, ignore_when_in_cache=True
        )

        # first determine a query that satisfies the domain and access rules
        if any(field.column_type for field in fields_to_fetch):
            query = self._search([("id", "in", self.ids)], active_test=False)
        else:
            try:
                self.check_access("read")
            except MissingError:
                # Method fetch() should never raise a MissingError, but method
                # check_access() can, because it must read fields on self.
                # So we restrict 'self' to existing records (to avoid an extra
                # exists() at the end of the method).
                self = self.exists()
                self.check_access("read")
            if not fields_to_fetch:
                return
            query = self._as_query(ordered=False)

        # fetch the fields
        fetched = self._fetch_query(query, fields_to_fetch)

        if _debug:
            _orm_read.debug(
                "[%.3f ms] fetch %s: %d records, %d fields",
                (time.perf_counter() - _t0) * 1000,
                self._name,
                len(self),
                len(fields_to_fetch),
            )

        # possibly raise exception for the records that could not be read
        if fetched != self:
            forbidden = (self - fetched).exists()
            if forbidden:
                raise self.env["ir.rule"]._make_access_error("read", forbidden)

    def _determine_fields_to_fetch(
        self,
        field_names: Collection[str] | None = None,
        ignore_when_in_cache: bool = False,
    ) -> list[Field]:
        """
        Return the fields to fetch from database among the given field names,
        and following the dependencies of computed fields. The method is used
        by :meth:`fetch` and :meth:`search_fetch`.

        :param field_names: the collection of requested fields, or ``None`` for
            all accessible fields marked with ``prefetch=True``
        :param ignore_when_in_cache: whether to ignore fields that are alreay in cache for ``self``
        :return: the list of fields that must be fetched
        :raise AccessError: when trying to fetch fields to which the user does not have access
        """
        if field_names is None:
            return [
                field
                for field in self._fields.values()
                if field.prefetch is True and self._has_field_access(field, "read")
            ]

        if not field_names:
            return []

        fields_to_fetch: list[Field] = []
        fields_todo: deque[Field] = deque()
        fields_done = {self._fields["id"]}  # trick: ignore 'id'
        for field_name in field_names:
            if not isinstance(field_name, str) or field_name not in self._fields:
                _logger.warning(
                    "Invalid field %r on %r, skipping", field_name, self._name
                )
                continue
            field = self._fields[field_name]
            self._check_field_access(field, "read")
            fields_todo.append(field)

        while fields_todo:
            field = fields_todo.popleft()
            if field in fields_done:
                continue
            fields_done.add(field)
            if ignore_when_in_cache and not any(field._cache_missing_ids(self)):
                # field is already in cache: don't fetch it
                continue
            if field.store:
                fields_to_fetch.append(field)
            else:
                # optimization: fetch field dependencies
                for dotname in self.pool.field_depends[field]:
                    dep_field = self._fields[dotname.split(".", 1)[0]]
                    if (not dep_field.store) or (
                        dep_field.prefetch is True
                        and self._has_field_access(dep_field, "read")
                    ):
                        fields_todo.append(dep_field)

        return fields_to_fetch

    def _fetch_query(self, query: Query, fields: Sequence[Field]) -> Self:
        """Fetch the given fields (iterable of :class:`Field` instances) from
        the given query, put them in cache, and return the fetched records.

        This method may be overridden to change what fields to actually fetch,
        or to change the values that are put in cache.
        """
        _debug = _orm_read.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = _t_sql = _t_cache = time.perf_counter()

        # determine columns fields and those with their own read() method
        column_fields: OrderedSet[Field] = OrderedSet()
        other_fields: OrderedSet[Field] = OrderedSet()
        for field in fields:
            if field.name == "id":
                continue
            assert field.store
            (column_fields if field.column_type else other_fields).add(field)

        context = self.env.context

        # --- Backend dispatch: DictBackend or PostgreSQL ---
        storage = self.env.transaction.storage
        if storage is not None:
            # In-memory path: fetch from DictBackend, populate cache.
            # Get IDs from the query (set by _search_storage or _as_query).
            result_ids = query._ids
            if result_ids is None:
                # Fallback: query hasn't been resolved yet — extract from
                # storage using the table's known IDs.  This shouldn't happen
                # once Phase 6 (search) is wired, but is safe.
                result_ids = tuple(storage.table_ids(self._table))

            if not result_ids:
                return self.browse()

            fetched = self.browse(result_ids)
            if column_fields:
                # Pre-resolve field caches once.  Context-dependent fields
                # may fail (env.company unavailable) — write to base cache.
                env = self.env
                _fdc = env._field_depends_context
                field_caches: dict = {}
                for field in column_fields:
                    if field not in _fdc:
                        field_caches[field] = env._core.field_data(field)
                    else:
                        try:
                            field_caches[field] = field._get_cache(env)
                        except Exception:
                            field_caches[field] = env._core.field_data(field)
                for record_id in result_ids:
                    row = storage.get_row(self._table, record_id)
                    if row is not None:
                        for field in column_fields:
                            value = row.get(field.name)
                            fc = field_caches[field]
                            fc.setdefault(
                                record_id,
                                field.convert_to_cache(value, fetched),
                            )

            # process non-column fields
            if fetched:
                for field in other_fields:
                    field.read(fetched)
            return fetched

        if column_fields:
            # the query may involve several tables: we need fully-qualified names
            sql_terms = [SQL.identifier(self._table, "id")]
            for field in column_fields:
                sql = self._field_to_sql(self._table, field.name, query)
                if field.type == "binary" and (
                    context.get("bin_size") or context.get("bin_size_" + field.name)
                ):
                    # pg_size_pretty has both (bigint) and (numeric) overloads; cast to disambiguate
                    sql = SQL("pg_size_pretty(length(%s)::bigint)", sql)
                elif not field.translate:
                    # flushing is necessary to retrieve the en_US value of fields without a translation
                    # otherwise, re-create the SQL without flushing
                    to_flush = (f for f in sql.to_flush if f != field)
                    sql = SQL(sql.code, *sql.params, to_flush=to_flush)
                sql_terms.append(sql)

            # select the given columns from the rows in the query
            rows = self.env.execute_query(query.select(*sql_terms))
            if _debug:
                _t_sql = time.perf_counter()

            if not rows:
                return self.browse()

            # rows = [(id1, a1, b1), (id2, a2, b2), ...]
            # column_values = [(id1, id2, ...), (a1, a2, ...), (b1, b2, ...)]
            column_values = zip(*rows, strict=False)
            ids = next(column_values)
            fetched = self.browse(ids)

            # If we assume that the value of a pending update is in cache, we
            # can avoid flushing pending updates if the fetched values do not
            # overwrite values in cache.
            for field, values in zip(column_fields, column_values, strict=True):
                # store values in cache, but without overwriting
                field._insert_cache(fetched, values)
            if _debug:
                _t_cache = time.perf_counter()
        else:
            fetched = self.browse(query)
            if _debug:
                _t_sql = _t_cache = time.perf_counter()

        # process non-column fields
        if fetched:
            for field in other_fields:
                field.read(fetched)

        if _debug:
            _t_end = time.perf_counter()
            _orm_read.debug(
                "[%.3f ms] _fetch_query %s: %d col + %d other fields -> %d rows"
                " | sql=%.1f cache=%.1f other=%.1f",
                (_t_end - _t0) * 1000,
                self._name,
                len(column_fields),
                len(other_fields),
                len(fetched),
                (_t_sql - _t0) * 1000,
                (_t_cache - _t_sql) * 1000,
                (_t_end - _t_cache) * 1000,
            )

        return fetched

    def get_metadata(self) -> list[ValuesType]:
        """Return some metadata about the given records.

        :returns: list of ownership dictionaries for each requested record with the following keys:

            * id: object id
            * create_uid: user who created the record
            * create_date: date when the record was created
            * write_uid: last user who changed the record
            * write_date: date of the last change to the record
            * xmlid: XML ID to use to refer to this record (if there is one), in format ``module.name``
            * xmlids: list of dict with xmlid in format ``module.name``, and noupdate as boolean
            * noupdate: A boolean telling if the record will be updated or not
        """

        IrModelData = self.env["ir.model.data"].sudo()
        if self._log_access:
            res = self.read(LOG_ACCESS_COLUMNS)
        else:
            res = [{"id": x} for x in self.ids]

        xml_data = defaultdict(list)
        imds = IrModelData.search_read(
            [("model", "=", self._name), ("res_id", "in", self.ids)],
            ["res_id", "noupdate", "module", "name"],
            order="id DESC",
        )
        for imd in imds:
            xml_data[imd["res_id"]].append(
                {
                    "xmlid": f"{imd['module']}.{imd['name']}",
                    "noupdate": imd["noupdate"],
                }
            )

        for r in res:
            main = xml_data.get(r["id"], [{}])[-1]
            r["xmlid"] = main.get("xmlid", False)
            r["noupdate"] = main.get("noupdate", False)
            r["xmlids"] = xml_data.get(r["id"], [])[::-1]
        return res
