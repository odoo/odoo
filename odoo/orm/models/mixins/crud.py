"""
CRUD operations mixin for BaseModel.

This module contains the create, write, and unlink methods, along with
their supporting private methods for database operations.

Copy/duplication operations have been extracted to copy.py (CopyMixin).
"""

import logging
import os
import time
import typing
from collections import defaultdict
from itertools import batched
from operator import attrgetter

from odoo.exceptions import AccessError, UserError
from odoo.libs.json import dumps as json_dumps
from odoo.libs.json import loads as json_loads
from odoo.tools import SQL, OrderedSet, clean_context
from odoo.tools.misc import PENDING
from odoo.tools.nplusone import _n1_enabled
from odoo.tools.orm_profiler import _orm_profiling_enabled
from odoo.tools.translate import _

# Minimum batch size to use COPY protocol instead of INSERT.
# COPY avoids SQL parsing/planning overhead and is faster for large batches,
# but adds +1 query (SELECT nextval) for ID pre-generation.
# Below threshold, multi-row INSERT with RETURNING is used (single query).
# With binary COPY on PG18, the break-even is ~5 rows; 10 is conservative.
COPY_THRESHOLD = int(os.environ.get("ODOO_COPY_THRESHOLD", "10"))
COPY_DISABLED = os.environ.get("ODOO_DISABLE_COPY", "").lower() in (
    "1",
    "true",
    "yes",
)

# Pre-computed bad_names sets for write() — avoids recreating per call.
# _WRITE_BAD_NAMES_LOG: models with _log_access (the default)
# _WRITE_BAD_NAMES:     models without _log_access
_WRITE_BAD_NAMES_LOG = frozenset(
    {
        "id",
        "parent_path",
        "create_uid",
        "create_date",
        "write_uid",
        "write_date",
    }
)
_WRITE_BAD_NAMES = frozenset({"id", "parent_path"})

# Pre-computed bad_names sets for create() — avoids recreating per call.
# Mirrors _WRITE_BAD_NAMES but LOG_ACCESS_COLUMNS are included because
# create() strips them (then re-adds with setdefault).
# The precompute+readonly field names are model-specific and cached on
# the model class at first create (see _prepare_create_values).
_CREATE_BAD_NAMES_LOG = frozenset(
    {
        "id",
        "parent_path",
        "create_uid",
        "create_date",
        "write_uid",
        "write_date",
    }
)
_CREATE_BAD_NAMES = frozenset({"id", "parent_path"})

from typing import Self

from ... import decorators as api
from ..._typing import ValuesType
from ...primitives import (
    INSERT_BATCH_SIZE,
    LOG_ACCESS_COLUMNS,
    SQL_DEFAULT,
    SUPERUSER_ID,
    UPDATE_BATCH_SIZE,
    Command,
)

if typing.TYPE_CHECKING:
    from ...fields.base import Field


_logger = logging.getLogger("odoo.models")
_unlink = logging.getLogger("odoo.models.unlink")
_orm_crud = logging.getLogger("odoo.orm.crud")


class CrudMixin:
    """Mixin providing CRUD (Create, Read, Update, Delete) operations.

    This mixin contains the core data manipulation methods:
    - default_get(): Return default values for fields
    - create(): Create new records
    - write(): Update existing records
    - unlink(): Delete records

    And their supporting private methods for database operations.
    Copy/duplication is in CopyMixin (copy.py).

    Operation Contracts
    ===================

    The three mutation methods (create/write/unlink) follow a standardized
    pipeline with guaranteed step ordering.  Understanding this contract is
    critical for writing correct compute methods, constraints, and overrides.

    **create()** — Immediate INSERT
    ::

        1. Model-level ACL check + field-level access
        2. Prepare values: defaults, precomputed fields, magic fields
        3. Classify fields: stored / inversed / inherited / protected
        4. Create _inherits parent records (recursive)
        5. SQL INSERT (or COPY for ≥10 rows) — IMMEDIATE
        6. Populate cache, update parent_path
        7. modified(ALL_FIELDS, create=True) — trigger recomputation
        8. Validate Pass 1: stored fields
        9. Run inverse methods for inversed fields
        10. Validate Pass 2: inversed fields (excl. stored)
        11. _check_company()
        12. Record-level ACL check (late — needs record to exist)

    **write()** — Deferred UPDATE (see ``flush_all()``)
    ::

        1. Record-level ACL check + field-level access
        2. Prepare values: magic fields (write_uid/write_date)
        3. Classify fields, pre-fetch x2many inverse fields
        4. Force recompute co-computed fields not being assigned
        5. WITH protecting(dependents):
           a. _modified_before(RELATIONAL fields) — OLD dependency graph
           b. mark_dirty(fields) in write_sequence order — NO SQL YET
           c. modified(WRITTEN fields) — NEW dependency graph
           d. Validate Pass 1: vals minus inversed
           e. Run inverse methods
           f. Validate Pass 2: inversed fields only
        6. _check_company()

        SQL UPDATE is deferred until flush_all()/flush_model()/implicit flush.
        Multiple writes are batched into a single UPDATE FROM VALUES.

    **unlink()** — Immediate DELETE
    ::

        1. Record-level ACL check
        2. Run @api.ondelete methods
        3. Clear pending recomputes for deleted IDs
        4. Targeted flush: self + FK-referencing models
        5. _modified_before(ALL_FIELDS) — capture ALL dependency paths
        6. Batched DELETE WHERE id IN (...) — IMMEDIATE
        7. Handle company-dependent M2O cascade/set-null (raw SQL)
        8. Targeted cache invalidation (per-field, per-ID)
        9. Recursive cleanup: ir.model.data, ir.attachment

    Key Asymmetries (by design)
    ---------------------------

    - **SQL timing**: write() is deferred (batched), create()/unlink() are
      immediate.  Raw SQL after write() sees OLD values until flush.
    - **modified() scope**: write() uses _modified_before(RELATIONAL) only,
      because scalar fields don't change the dependency graph.  unlink() uses
      _modified_before(ALL_FIELDS) because deletion breaks every path.
    - **Validation**: create() validates stored→inversed; write() validates
      (vals-inversed)→inversed.  Both are two-pass.
    - **ACL timing**: create() checks record-level rules LATE (needs record);
      write()/unlink() check them EARLY (records exist).

    See Also
    --------
    - ``CacheMixin.modified()``: trigger tree propagation
    - ``CacheMixin.flush_model()``: dirty guard + flush
    - ``Environment.flush_all()``: convergence loop (recompute → flush → repeat)
    - ``Field.write_sequence``: field processing order in write()
    """

    __slots__ = ()

    # -------------------------------------------------------------------------
    # Default values
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        """Return default values for the fields in ``fields_list``. Default
        values are determined by the context, user defaults, user fallbacks
        and the model itself.

        :param fields: names of field whose default is requested
        :return: a dictionary mapping field names to their corresponding default values,
            if they have a default value.

        .. note::

            Unrequested defaults won't be considered, there is no need to return a
            value for fields whose names are not in `fields_list`.
        """
        defaults = {}
        parent_fields = defaultdict(list)
        ir_defaults = self.env["ir.default"]._get_model_defaults(self._name)

        for name in fields:
            # 1. look up context
            key = "default_" + name
            if key in self.env.context:
                defaults[name] = self.env.context[key]
                continue

            field = self._fields.get(name)
            if not field:
                continue

            # 2. look up default for non-company_dependent fields
            if not field.company_dependent and name in ir_defaults:
                defaults[name] = ir_defaults[name]
                continue

            # 3. look up field.default
            if field.default:
                defaults[name] = field.default(self)
                continue

            # 4. look up fallback for company_dependent fields
            if field.company_dependent and name in ir_defaults:
                defaults[name] = ir_defaults[name]
                continue

            # 5. delegate to parent model
            if field.inherited:
                field = field.related_field
                parent_fields[field.model_name].append(field.name)

        # convert default values to the right format
        #
        # we explicitly avoid using _convert_to_write() for x2many fields,
        # because the latter leaves values like [(Command.LINK, 2),
        # (Command.LINK, 3)], which are not supported by the web client as
        # default values; stepping through the cache allows to normalize
        # such a list to [(Command.SET, 0, [2, 3])], which is properly
        # supported by the web client
        for fname, value in defaults.items():
            if fname in self._fields:
                field = self._fields[fname]
                value = field.convert_to_cache(value, self, validate=False)
                defaults[fname] = field.convert_to_write(value, self)

        # add default values for inherited fields
        for model, names in parent_fields.items():
            defaults.update(self.env[model].default_get(names))

        return defaults

    @api.model
    def _add_missing_default_values(
        self,
        values: ValuesType,
        _missing_defaults_cache: dict[frozenset[str], list[str]] | None = None,
    ) -> ValuesType:
        # Determine which fields need defaults.  When called in a batch from
        # _prepare_create_values, the ``_missing_defaults_cache`` argument caches
        # the (expensive) missing-defaults computation per unique set of provided
        # field names.  This avoids iterating all model fields for every record
        # when the provided keys are identical.
        vals_keys = frozenset(values)
        if _missing_defaults_cache is not None and vals_keys in _missing_defaults_cache:
            missing_defaults = _missing_defaults_cache[vals_keys]
        else:
            # avoid overriding inherited values when parent is set
            avoid_models = set()

            def collect_models_to_avoid(model):
                for parent_mname, parent_fname in model._inherits.items():
                    if parent_fname in values:
                        avoid_models.add(parent_mname)
                    else:
                        # manage the case where an ancestor parent field is set
                        collect_models_to_avoid(self.env[parent_mname])

            collect_models_to_avoid(self)

            def avoid(field):
                # check whether the field is inherited from one of avoid_models
                if avoid_models:
                    while field.inherited:
                        field = field.related_field
                        if field.model_name in avoid_models:
                            return True
                return False

            # compute missing fields
            missing_defaults = [
                name
                for name, field in self._fields.items()
                if name not in values
                if not avoid(field)
            ]
            if _missing_defaults_cache is not None:
                _missing_defaults_cache[vals_keys] = missing_defaults

        if missing_defaults:
            # override defaults with the provided values, never allow the other way around
            defaults = self.default_get(missing_defaults)
            for name, value in defaults.items():
                if (
                    self._fields[name].type == "many2many"
                    and value
                    and isinstance(value[0], int)
                ):
                    # convert a list of ids into a list of commands
                    defaults[name] = [Command.set(value)]
                elif (
                    self._fields[name].type == "one2many"
                    and value
                    and isinstance(value[0], dict)
                ):
                    # convert a list of dicts into a list of commands
                    defaults[name] = [Command.create(x) for x in value]
            defaults.update(values)

        else:
            defaults = values

        # delegate the default properties to the properties field
        for field in self._fields.values():
            if field.type == "properties":
                defaults[field.name] = field._add_default_values(self.env, defaults)

        return defaults

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        """Create new records for the model.

        The new records are initialized using the values from the list of dicts
        ``vals_list``, and if necessary those from :meth:`~.default_get`.

        :param vals_list:
            values for the model's fields, as a list of dictionaries::

                [{'field_name': field_value, ...}, ...]

            For backward compatibility, ``vals_list`` may be a dictionary.
            It is treated as a singleton list ``[vals]``, and a single record
            is returned.

            see :meth:`~.write` for details

        :return: the created records
        :raise AccessError: if the current user is not allowed to create records of the specified model
        :raise ValidationError: if user tries to enter invalid value for a selection field
        :raise ValueError: if a field name specified in the create values does not exist.
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation
          (such as setting an object as its own parent)
        """
        assert isinstance(vals_list, (list, tuple))
        if not vals_list:
            return self.browse()

        _debug = _orm_crud.isEnabledFor(logging.DEBUG)
        _agg = _orm_profiling_enabled
        if _debug or _agg:
            _t0 = time.perf_counter()

        if _n1_enabled and (tracker := self.env.transaction._n1_tracker):
            fnames = frozenset(fname for vals in vals_list for fname in vals)
            tracker.record("create", self._name, len(vals_list), fnames)

        # Model-level ACL: check that the user can create this model at all.
        # Called on an empty recordset so only ir.model.access is checked,
        # not ir.rules (which need actual record ids).
        self = self.browse()
        self.check_access("create")

        # check access to all user-provided fields
        field_names = OrderedSet(fname for vals in vals_list for fname in vals)
        field_names.update(
            field_name
            for context_key in self.env.context
            if context_key.startswith("default_")
            and (field_name := context_key.removeprefix("default_"))
            and field_name in self._fields
        )
        for field_name in field_names:
            field = self._fields.get(field_name)
            if field is None:
                raise ValueError(f"Invalid field {field_name!r} in {self._name!r}")
            self._check_field_access(field, "write")
        if _debug:
            _t_acl = time.perf_counter()

        new_vals_list = self._prepare_create_values(vals_list)

        # classify fields for each record
        data_list = []
        determine_inverses = defaultdict(OrderedSet)  # {inverse: fields}

        for vals in new_vals_list:
            precomputed = vals.pop("__precomputed__", ())

            # distribute fields into sets for various purposes
            data = {}
            data["stored"] = stored = {}
            data["inversed"] = inversed = {}
            data["inherited"] = inherited = defaultdict(dict)
            data["protected"] = protected = set()
            for key, val in vals.items():
                field = self._fields.get(key)
                if not field:
                    raise ValueError(f"Invalid field {key!r} on model {self._name!r}")
                if field.store:
                    stored[key] = val
                if field.inherited:
                    inherited[field.related_field.model_name][key] = val
                elif field.inverse and field not in precomputed:
                    inversed[key] = val
                    determine_inverses[field.inverse].add(field)
                # protect editable computed fields and precomputed fields
                # against (re)computation
                if field.compute and (not field.readonly or field.precompute):
                    protected.update(self.pool.field_computed.get(field, [field]))

            data_list.append(data)
        if _debug:
            _t_prep = time.perf_counter()

        # create or update parent records
        for model_name, parent_name in self._inherits.items():
            parent_data_list = []
            for data in data_list:
                if not data["stored"].get(parent_name):
                    parent_data_list.append(data)
                elif data["inherited"][model_name]:
                    parent = self.env[model_name].browse(data["stored"][parent_name])
                    parent.write(data["inherited"][model_name])

            if parent_data_list:
                parents = self.env[model_name].create(
                    [data["inherited"][model_name] for data in parent_data_list]
                )
                for parent, data in zip(parents, parent_data_list, strict=False):
                    data["stored"][parent_name] = parent.id

        if _debug:
            _t_parent = time.perf_counter()

        # create records with stored fields
        records = self._create(data_list)
        if _debug:
            _t_sql = time.perf_counter()

        # Validation strategy for create() — two passes:
        #   Pass 1 (in _create): _validate_fields(stored_names) — constraints
        #     touching only stored fields.
        #   Pass 2 (below):      _validate_fields(inversed, excluded=stored) —
        #     constraints touching inversed fields, excluding any that also
        #     touch stored fields (already covered in pass 1).
        # Inverse methods run BEFORE both passes because they write to related
        # models — constraints may need those related records to exist.
        # Compare with write(), which validates non-inversed first because
        # dirty cache values are already available without running inverses.

        # protect fields being written against recomputation
        protected_fields = [(data["protected"], data["record"]) for data in data_list]
        with self.env.protecting(protected_fields):
            # call inverse method for each group of fields
            for fields in determine_inverses.values():
                # determine which records to inverse for those fields
                inv_names = {field.name for field in fields}
                inv_rec_ids = []
                for data in data_list:
                    if inv_names.isdisjoint(data["inversed"]):
                        continue
                    record = data["record"]
                    record._update_cache(
                        {
                            fname: value
                            for fname, value in data["inversed"].items()
                            if fname in inv_names and fname not in data["stored"]
                        }
                    )
                    inv_rec_ids.append(record.id)

                inv_records = self.browse(inv_rec_ids)
                next(iter(fields)).determine_inverse(inv_records)
                # Values of non-stored fields were cached before running inverse methods. In case of x2many create
                # commands, the cache may therefore hold NewId records. We must now invalidate those values.
                inv_relational_fnames = [
                    field.name
                    for field in fields
                    if field.type in ("one2many", "many2many") and not field.store
                ]
                inv_records.invalidate_recordset(fnames=inv_relational_fnames)
        if _debug:
            _t_trigger = time.perf_counter()

        # Pass 2: validate constraints touching inversed fields, excluding
        # those that also touch stored fields (already validated in pass 1).
        for data in data_list:
            data["record"]._validate_fields(data["inversed"], data["stored"])

        if self._check_company_auto:
            records._check_company()

        if _debug or _agg:
            _t_end = time.perf_counter()
        if _debug:
            _orm_crud.debug(
                "[%.3f ms] create %s: %d records, %d fields"
                " | acl=%.1f prep=%.1f parent=%.1f sql=%.1f trigger=%.1f validate=%.1f",
                (_t_end - _t0) * 1000,
                self._name,
                len(records),
                len(field_names),
                (_t_acl - _t0) * 1000,
                (_t_prep - _t_acl) * 1000,
                (_t_parent - _t_prep) * 1000,
                (_t_sql - _t_parent) * 1000,
                (_t_trigger - _t_sql) * 1000,
                (_t_end - _t_trigger) * 1000,
            )
        if _agg and (p := self.env.transaction._orm_profiler):
            p.record_create(self._name, len(records), _t_end - _t0)

        self._create_update_xmlids(records, vals_list)
        return records

    def _prepare_create_values(self, vals_list: list[ValuesType]) -> list[ValuesType]:
        """Clean up and complete the given create values, and return a list of
        new vals containing:

        * default values,
        * discarded forbidden values (magic fields),
        * precomputed fields.

        :param vals_list: List of create values
        :returns: new list of completed create values
        """
        # Use pre-computed static bad_names sets (module-level frozensets).
        if self._log_access:
            # the superuser can set log_access fields while loading registry
            if not (self.env.uid == SUPERUSER_ID and not self.pool.ready):
                bad_names = _CREATE_BAD_NAMES_LOG
            else:
                bad_names = _CREATE_BAD_NAMES
        else:
            bad_names = _CREATE_BAD_NAMES

        # Also discard precomputed readonly fields (to force their computation).
        # Cache the set on the model class to avoid iterating all fields per call.
        precompute_readonly = getattr(type(self), "_precompute_readonly_names", None)
        if precompute_readonly is None:
            precompute_readonly = frozenset(
                fname
                for fname, field in self._fields.items()
                if field.precompute and field.readonly
            )
            type(self)._precompute_readonly_names = precompute_readonly
        if precompute_readonly:
            bad_names = bad_names | precompute_readonly

        # Pre-compute missing_defaults for each unique set of provided field names.
        # In batch creates, all vals typically have the same keys, so this
        # avoids iterating ~150 fields N times to determine defaults.
        missing_defaults_cache: dict[frozenset[str], list[str]] = {}

        result_vals_list = []
        for vals in vals_list:
            # add default values (with cached missing_defaults)
            vals = self._add_missing_default_values(vals, missing_defaults_cache)

            # add magic fields
            for fname in bad_names:
                vals.pop(fname, None)
            if self._log_access:
                vals.setdefault("create_uid", self.env.uid)
                vals.setdefault("create_date", self.env.cr.now())
                vals.setdefault("write_uid", self.env.uid)
                vals.setdefault("write_date", self.env.cr.now())

            result_vals_list.append(vals)

        # add precomputed fields
        self._add_precomputed_values(result_vals_list)

        return result_vals_list

    def _add_precomputed_values(self, vals_list: list[ValuesType]) -> None:
        """Add missing precomputed fields to ``vals_list`` values.
        Only applies for precompute=True fields.
        """
        precomputable = {
            fname: field for fname, field in self._fields.items() if field.precompute
        }
        if not precomputable:
            return

        # determine which vals must be completed
        vals_list_todo = [
            vals
            for vals in vals_list
            if any(fname not in vals for fname in precomputable)
        ]
        if not vals_list_todo:
            return

        # create new records for the vals that must be completed
        records = self.browse().concat(*(self.new(vals) for vals in vals_list_todo))

        for record, vals in zip(records, vals_list_todo, strict=False):
            vals["__precomputed__"] = precomputed = set()
            for fname, field in precomputable.items():
                if fname not in vals:
                    # computed stored fields with a column
                    # have to be computed before create
                    # s.t. required and constraints can be applied on those fields.
                    vals[fname] = field.convert_to_write(record[fname], self)
                    precomputed.add(field)

    @api.model
    def _create(self, data_list: list[ValuesType]) -> Self:
        """Create records from the stored field values in ``data_list``."""
        assert data_list
        cr = self.env.cr
        _debug = _orm_crud.isEnabledFor(logging.DEBUG)
        if _debug:
            _tc0 = time.perf_counter()

        # insert rows in batches of maximum INSERT_BATCH_SIZE
        ids: list[int] = []  # ids of created records
        other_fields: OrderedSet[Field] = OrderedSet()  # non-column fields

        for data_sublist in batched(data_list, INSERT_BATCH_SIZE):
            stored_list = [data["stored"] for data in data_sublist]
            fnames = sorted({name for stored in stored_list for name in stored})

            columns: list[str] = []
            col_fields: list[Field] = []
            for fname in fnames:
                field = self._fields[fname]
                if field.column_type:
                    columns.append(fname)
                    col_fields.append(field)
                else:
                    other_fields.add(field)

                if field.type == "properties":
                    # force calling fields.create for properties field because
                    # we might want to update the parent definition
                    other_fields.add(field)

            # --- Backend dispatch: DictBackend or PostgreSQL ---
            storage = self.env.transaction.storage
            if storage is not None:
                # In-memory path: insert rows into DictBackend.
                # Converts values identically to the SQL paths, but stores
                # in the dict-of-dicts structure instead of issuing SQL.
                tbl = storage._tables.setdefault(self._table, {})
                for stored in stored_list:
                    new_id = storage.next_id(self._table)
                    row_dict: dict[str, typing.Any] = {"id": new_id}
                    for fname, field in zip(columns, col_fields, strict=False):
                        if fname in stored:
                            row_dict[fname] = field.convert_to_column_insert(
                                stored[fname], self, stored
                            )
                        # Missing columns default to None (same as SQL NULL)
                    tbl[new_id] = row_dict
                    ids.append(new_id)
                continue

            use_copy = (
                not COPY_DISABLED and col_fields and len(stored_list) >= COPY_THRESHOLD
            )
            _debug = _orm_crud.isEnabledFor(logging.DEBUG)
            if _debug:
                _t0 = time.perf_counter()

            if use_copy:
                # COPY path: 2-5x faster than INSERT for large batches.
                # Uses None instead of SQL_DEFAULT (safe: _prepare_create_values
                # already applied all Python defaults; remaining gaps are
                # non-required fields whose database default is NULL).
                copy_rows = []
                for stored in stored_list:
                    row = tuple(
                        (
                            field.convert_to_column_insert(stored[fname], self, stored)
                            if fname in stored
                            else None
                        )
                        for fname, field in zip(columns, col_fields, strict=False)
                    )
                    copy_rows.append(row)
                batch_ids = cr.copy_from(
                    self._table,
                    columns,
                    copy_rows,
                    returning_ids=True,
                    binary=True,
                )
                ids.extend(batch_ids)
                if _debug:
                    _orm_crud.debug(
                        "[%.3f ms] _create %s: %d records via COPY (%d columns)",
                        (time.perf_counter() - _t0) * 1000,
                        self._name,
                        len(stored_list),
                        len(columns),
                    )
            else:
                # INSERT path: used for small batches and empty-record edge case.
                # Uses None instead of SQL_DEFAULT for missing columns (same
                # rationale as the COPY path): _prepare_create_values already
                # applied all Python defaults; remaining gaps are non-required
                # fields whose database default is NULL.  This produces uniform
                # rows without DEFAULT keywords, enabling standard parameter
                # binding for the entire VALUES clause.
                if not columns:
                    columns = ["id"]
                rows: list[list[typing.Any]] = [[] for _ in stored_list]
                for fname, field in zip(columns, col_fields, strict=False):
                    for stored, row in zip(stored_list, rows, strict=False):
                        if fname in stored:
                            row.append(
                                field.convert_to_column_insert(
                                    stored[fname], self, stored
                                )
                            )
                        else:
                            row.append(None)
                if not col_fields:
                    for row in rows:
                        row.append(SQL_DEFAULT)

                cr.execute(
                    SQL(
                        'INSERT INTO %s (%s) VALUES %s RETURNING "id"',
                        SQL.identifier(self._table),
                        SQL(", ").join(map(SQL.identifier, columns)),
                        SQL(", ").join(
                            SQL("(%s)", SQL(", ").join(row)) for row in rows
                        ),
                    )
                )
                ids.extend(id_ for (id_,) in cr.fetchall())
                if _debug:
                    _orm_crud.debug(
                        "[%.3f ms] _create %s: %d records via INSERT (%d columns)",
                        (time.perf_counter() - _t0) * 1000,
                        self._name,
                        len(stored_list),
                        len(columns),
                    )

        if _debug:
            _tc_sql = time.perf_counter()

        # put the new records in cache, and update inverse fields, for many2one
        records, inverses_update = self._populate_create_cache(ids, data_list)
        if _debug:
            _tc_cache = time.perf_counter()

        for (field, value), record_ids in inverses_update.items():
            field._update_inverses(self.browse(record_ids), value)
        if _debug:
            _tc_inverses = time.perf_counter()

        # update parent_path
        records._parent_store_create()

        # protect fields being written against recomputation
        protected = [(data["protected"], data["record"]) for data in data_list]
        with self.env.protecting(protected):
            # mark computed fields as todo
            records.modified(self._fields, create=True)

            if other_fields:
                # discard default values from context for other fields
                others = records.with_context(clean_context(self.env.context))
                for field in sorted(other_fields, key=attrgetter("_sequence")):
                    field.create(
                        [
                            (other, data["stored"][field.name])
                            for other, data in zip(others, data_list, strict=False)
                            if field.name in data["stored"]
                        ]
                    )

                # mark fields to recompute
                records.modified([field.name for field in other_fields], create=True)

        # Pass 1: validate constraints touching stored fields.
        records._validate_fields(name for data in data_list for name in data["stored"])
        # Record-level rules: check that ir.rules allow creating *these
        # specific* records (e.g. multi-company rules).  This is NOT a
        # duplicate of the model-level check above — that one verified ACLs
        # on an empty recordset; this one evaluates record rules against the
        # actual created records.
        records.check_access("create")

        if _debug:
            _tc_end = time.perf_counter()
            _orm_crud.debug(
                "[%.3f ms] _create %s: %d records"
                " | sql=%.1f cache=%.1f inverses=%.1f trigger=%.1f",
                (_tc_end - _tc0) * 1000,
                self._name,
                len(records),
                (_tc_sql - _tc0) * 1000,
                (_tc_cache - _tc_sql) * 1000,
                (_tc_inverses - _tc_cache) * 1000,
                (_tc_end - _tc_inverses) * 1000,
            )
        return records

    def _populate_create_cache(self, ids, data_list):
        """Populate the ORM cache for newly created records.

        Fills cache slots for all stored fields, converts values to cache
        format, and collects many2one inverse updates.

        :param ids: list of newly created record IDs
        :param data_list: list of data dicts with 'stored' and 'inherited' keys
        :return: (records, inverses_update) — the browse recordset and a dict
            of {(field, cache_value): [record_ids]} for M2O inverse updates.
            Also mutates data_list entries to add 'record' key.
        """
        # using bin_size=False to put binary values in the right place
        records = self.browse(ids)
        inverses_update = defaultdict(list)  # {(field, value): ids}
        common_set_vals = frozenset((*LOG_ACCESS_COLUMNS, "id", "parent_path"))

        # Pre-classify stored fields once (avoids re-checking per record).
        # Also pre-get field caches to avoid repeated _get_cache() calls.
        env = self.env
        _stored_x2m_caches = []  # [(field, cache)] for x2many stored fields
        _stored_scalar_caches = (
            []
        )  # [(field, field_name, cache, default)] for scalar stored fields
        for field in self._fields.values():
            if not field.store:
                continue
            if field.type in ("one2many", "many2many"):
                _stored_x2m_caches.append((field, field._get_cache(env)))
            else:
                # Stored computed fields get PENDING (not None) so cache reads
                # can distinguish "not yet computed" from "genuinely null".
                default = PENDING if field.is_stored_computed else None
                _stored_scalar_caches.append(
                    (field, field.name, field._get_cache(env), default)
                )

        _fields = self._fields
        _field_inverses = self.pool.field_inverses
        _x2m_html_types = frozenset(("one2many", "many2many", "html"))
        _m2o_types = frozenset(("many2one", "many2one_reference"))
        for data, record in zip(data_list, records.with_context(bin_size=False), strict=False):
            data["record"] = record
            # DLE P104: test_inherit.py, test_50_search_one2many
            vals = dict(
                {k: v for d in data["inherited"].values() for k, v in d.items()},
                **data["stored"],
            )
            set_vals = common_set_vals.union(vals)

            record_id = record._ids[0]
            # put None/() in cache for all fields not part of the INSERT
            # Direct cache assignment avoids _update_cache() method overhead
            # (safe: new records have no dirty flags to check)
            for _field, cache in _stored_x2m_caches:
                cache[record_id] = ()
            for _field, fname, cache, default in _stored_scalar_caches:
                if fname not in set_vals:
                    cache[record_id] = default

            for fname, value in vals.items():
                field = _fields[fname]
                if field.type not in _x2m_html_types:
                    cache_value = field.convert_to_cache(value, record)
                    field._update_cache(record, cache_value)
                    if field.type in _m2o_types and _field_inverses[field]:
                        inverses_update[(field, cache_value)].append(record.id)

        return records, inverses_update

    @api.model
    def _create_update_xmlids(self, records, vals_list):
        """Update ir.model.data xmlids when creating records during import.

        Called at the end of create() to support setting xids directly by
        providing an "id" key during an import.
        """
        import_module = self.env.context.get("_import_current_module")
        if not import_module:
            return

        noupdate = self.env.context.get("noupdate", False)
        xids = (v.get("id") for v in vals_list)
        self.env["ir.model.data"]._update_xmlids(
            [
                {
                    "xml_id": (xid if "." in xid else f"{import_module}.{xid}"),
                    "record": rec,
                    # note: this is not used when updating o2ms above...
                    "noupdate": noupdate,
                }
                for rec, xid in zip(records, xids, strict=False)
                if xid and isinstance(xid, str)
            ]
        )

    def write(self, vals: ValuesType) -> typing.Literal[True]:
        """Update all records in ``self`` with the provided values.

        :param vals: fields to update and the value to set on them
        :raise AccessError: if user is not allowed to modify the specified records/fields
        :raise ValidationError: if invalid values are specified for selection fields
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)

        * For numeric fields (:class:`~odoo.fields.Integer`,
          :class:`~odoo.fields.Float`) the value should be of the
          corresponding type
        * For :class:`~odoo.fields.Boolean`, the value should be a
          :class:`python:bool`
        * For :class:`~odoo.fields.Selection`, the value should match the
          selection values (generally :class:`python:str`, sometimes
          :class:`python:int`)
        * For :class:`~odoo.fields.Many2one`, the value should be the
          database identifier of the record to set
        * The expected value of a :class:`~odoo.fields.One2many` or
          :class:`~odoo.fields.Many2many` relational field is a list of
          :class:`~odoo.fields.Command` that manipulate the relation the
          implement. There are a total of 7 commands:
          :meth:`~odoo.fields.Command.create`,
          :meth:`~odoo.fields.Command.update`,
          :meth:`~odoo.fields.Command.delete`,
          :meth:`~odoo.fields.Command.unlink`,
          :meth:`~odoo.fields.Command.link`,
          :meth:`~odoo.fields.Command.clear`, and
          :meth:`~odoo.fields.Command.set`.
        * For :class:`~odoo.fields.Date` and `~odoo.fields.Datetime`,
          the value should be either a date(time), or a string.

          .. warning::

            If a string is provided for Date(time) fields,
            it must be UTC-only and formatted according to
            :const:`odoo.tools.misc.DEFAULT_SERVER_DATE_FORMAT` and
            :const:`odoo.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT`

        * Other non-relational fields use a string for value

        .. note:: **Deferred SQL.**
            Unlike :meth:`create` and :meth:`unlink` which execute SQL
            immediately, ``write()`` only updates the ORM cache and marks
            fields as dirty.  The actual ``UPDATE`` statement is deferred
            until :meth:`flush_all` (or an implicit flush triggered by
            ``search()``, ``read()``, or transaction commit).  This enables
            batching multiple writes into a single ``UPDATE FROM VALUES``.

            **Consequence:** a raw SQL ``SELECT`` immediately after
            ``write()`` may return OLD values.  Always use the ORM to read
            values, or call ``flush_model()`` first if raw SQL is needed.
        """
        if not self:
            return True

        _debug = _orm_crud.isEnabledFor(logging.DEBUG)
        _agg = _orm_profiling_enabled
        if _debug or _agg:
            _t0 = time.perf_counter()

        if _n1_enabled and (tracker := self.env.transaction._n1_tracker):
            tracker.record("write", self._name, len(self), frozenset(vals))

        self.check_access("write")
        for field_name in vals:
            try:
                self._check_field_access(self._fields[field_name], "write")
            except KeyError as e:
                raise ValueError(
                    f"Invalid field {field_name!r} in {self._name!r}"
                ) from e
        if _debug:
            _t_acl = time.perf_counter()
        env = self.env

        # Select pre-computed frozenset of fields to strip from vals.
        # The superuser can set log_access fields while loading registry.
        if self._log_access and not (env.uid == SUPERUSER_ID and not self.pool.ready):
            bad_names = _WRITE_BAD_NAMES_LOG
        else:
            bad_names = _WRITE_BAD_NAMES

        # set magic fields
        vals = {key: val for key, val in vals.items() if key not in bad_names}
        if self._log_access:
            vals.setdefault("write_uid", self.env.uid)
            vals.setdefault("write_date", self.env.cr.now())

        field_values = []  # [(field, value)]
        determine_inverses = defaultdict(list)  # {inverse: fields}
        fnames_modifying_relations = []
        protected = set()
        x2m_inverse_fnames = []
        for fname, value in vals.items():
            field = self._fields.get(fname)
            if not field:
                raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")
            field_values.append((field, value))
            if field.inverse:
                if field.type in ("one2many", "many2many"):
                    x2m_inverse_fnames.append(fname)
                determine_inverses[field.inverse].append(field)
            if self.pool.is_modifying_relations(field):
                fnames_modifying_relations.append(fname)
            if field.inverse or (field.compute and not field.readonly):
                if field.store or field.type not in ("one2many", "many2many"):
                    # Protect the field from being recomputed while being
                    # inversed. In the case of non-stored x2many fields, the
                    # field's value may contain unexpeced new records (created
                    # by command 0). Those new records are necessary for
                    # inversing the field, but should no longer appear if the
                    # field is recomputed afterwards. Not protecting the field
                    # will automatically invalidate the field from the cache,
                    # forcing its value to be recomputed once dependencies are
                    # up-to-date.
                    protected.update(self.pool.field_computed.get(field, [field]))

        # Pre-read all x2many inverse fields in a single batch.  These fields
        # use command-based writes (add/remove/update), so their current value
        # must be in cache before the field is protected from recomputation.
        # Using fetch() instead of self[fname] per field: it populates cache
        # for all records at once without triggering ensure_one().
        if x2m_inverse_fnames:
            self.fetch(x2m_inverse_fnames)

        # force the computation of fields that are computed with some assigned
        # fields, but are not assigned themselves
        if protected:
            to_compute = [
                field.name
                for field in protected
                if field.compute and field.name not in vals
            ]
            if to_compute:
                self._recompute_recordset(to_compute)
        if _debug:
            _t_classify = time.perf_counter()

        # protect fields being written against recomputation
        with env.protecting(protected, self):
            # Determine records depending on values. When modifying a relational
            # field, you have to recompute what depends on the field's values
            # before and after modification.  This is because the modification
            # has an impact on the "data path" between a computed field and its
            # dependency.  Note that this double call to modified() is only
            # necessary for relational fields.
            #
            # It is best explained with a simple example: consider two sales
            # orders SO1 and SO2.  The computed total amount on sales orders
            # indirectly depends on the many2one field 'order_id' linking lines
            # to their sales order.  Now consider the following code:
            #
            #   line = so1.line_ids[0]      # pick a line from SO1
            #   line.order_id = so2         # move the line to SO2
            #
            # In this situation, the total amount must be recomputed on *both*
            # sales order: the line's order before the modification, and the
            # line's order after the modification.
            if fnames_modifying_relations:
                self._modified_before(fnames_modifying_relations)
            if _debug:
                _t_before = time.perf_counter()

            # Fast path: singleton with a real ID — skip filtered("id") overhead
            _ids = self._ids
            if len(_ids) == 1 and _ids[0]:
                real_recs = self
            else:
                real_recs = self.filtered("id")

            # Process fields in write_sequence order (see Field.write_sequence):
            # 0=scalars/M2O → 10=monetary/properties → 20=x2many
            if len(field_values) > 1:
                field_values.sort(key=lambda item: item[0].write_sequence)
            for field, value in field_values:
                field.mark_dirty(self, value)
            if _debug:
                _t_dirty = time.perf_counter()

            # determine records depending on new values
            #
            # Call modified after write, because the modified can trigger a
            # search which can trigger a flush which can trigger a recompute
            # which remove the field from the recompute list while all the
            # values required for the computation could not be yet in cache.
            # e.g. Write on `name` of `res.partner` trigger the recompute of
            # `display_name`, which triggers a search on child_ids to find the
            # childs to which the display_name must be recomputed, which
            # triggers the flush of `display_name` because the _order of
            # res.partner includes display_name. The computation of display_name
            # is then done too soon because the parent_id was not yet written.
            # (`test_01_website_reset_password_tour`)
            self.modified(vals)
            if _debug:
                _t_after = time.perf_counter()

            if self._parent_store and self._parent_name in vals:
                self.flush_model([self._parent_name])

            # Validation strategy for write() — two passes:
            #   Pass 1: _validate_fields(vals, excluded=inverse_fields) —
            #     constraints touching written fields, excluding inversed.
            #   Pass 2: _validate_fields(inverse_fields) — constraints
            #     touching only inversed fields, after inverses have run.
            # Non-inversed fields are validated first because their values
            # are already in the dirty cache.  Inverse methods run between
            # the passes because they write to related models.
            # Compare with create(), which runs inverses before both passes
            # because constraints may need the related records to exist.
            inverse_fields = [f.name for fs in determine_inverses.values() for f in fs]
            real_recs._validate_fields(vals, inverse_fields)
            if _debug:
                _t_validate1 = time.perf_counter()

            for fields in determine_inverses.values():
                # write again on non-stored fields that have been invalidated from cache
                for field in fields:
                    if (
                        not field.store
                        and (
                            not field.inherited
                            or field.type not in ("one2many", "many2many")
                        )
                        and any(field._cache_missing_ids(real_recs))
                    ):
                        field.mark_dirty(real_recs, vals[field.name])

                # inverse records that are not being computed
                try:
                    fields[0].determine_inverse(real_recs)
                except AccessError as e:
                    if fields[0].inherited:
                        description = self.env["ir.model"]._get(self._name).name
                        raise AccessError(
                            _(
                                "%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).",
                                previous_message=e.args[0],
                                document_kind=description,
                                document_model=self._name,
                            )
                        )
                    raise

            # Pass 2: validate constraints touching inversed fields.
            real_recs._validate_fields(inverse_fields)

        if self._check_company_auto:
            self._check_company(list(vals))

        if _debug or _agg:
            _t_end = time.perf_counter()
        if _debug:
            _fnames = (
                ", ".join(sorted(vals)) if len(vals) <= 20 else f"{len(vals)} fields"
            )
            _orm_crud.debug(
                "[%.3f ms] write %s: %d records, %s"
                " | acl=%.1f classify=%.1f before=%.1f dirty=%.1f after=%.1f"
                " validate=%.1f inverse=%.1f",
                (_t_end - _t0) * 1000,
                self._name,
                len(self),
                _fnames,
                (_t_acl - _t0) * 1000,
                (_t_classify - _t_acl) * 1000,
                (_t_before - _t_classify) * 1000,
                (_t_dirty - _t_before) * 1000,
                (_t_after - _t_dirty) * 1000,
                (_t_validate1 - _t_after) * 1000,
                (_t_end - _t_validate1) * 1000,
            )
        if _agg and (p := self.env.transaction._orm_profiler):
            p.record_write(self._name, len(self), _t_end - _t0)

        return True

    def _write(self, vals: ValuesType) -> None:
        """Low-level implementation of write()"""
        self._write_multi([vals] * len(self))
        # _write_multi bypasses field.write() and modified(), so the cache
        # retains stale pre-_write values.  Invalidate the updated fields to
        # ensure filtered_domain / Field.__get__ reads fresh DB values.
        if self:
            self.invalidate_recordset(list(vals), flush=False)

    def _write_multi(self, vals_list: list[ValuesType]) -> None:
        """Low-level implementation of write()"""
        assert len(self) == len(vals_list)

        if not self:
            return

        _debug = _orm_crud.isEnabledFor(logging.DEBUG)
        if _debug:
            _t0 = time.perf_counter()

        # determine records that require updating parent_path
        parent_records = (
            self._parent_store_update_prepare(vals_list) if self._parent_store else None
        )

        # Detect uniform vals (common: _write passes [vals]*N, all same object)
        uniform = len(vals_list) <= 1 or vals_list[0] is vals_list[-1]

        # Pipeline batches multiple UPDATE statements in a single round-trip.
        # Nesting is safe — psycopg3 reuses the active pipeline as a no-op.
        with self.env.cr.pipeline():
            if uniform:
                vals = vals_list[0]
                if self._log_access:
                    vals = {
                        "write_uid": self.env.uid,
                        "write_date": self.env.cr.now(),
                    } | vals
                fnames, template_row = zip(*sorted(vals.items()), strict=False)
                # Iterate _ids directly — avoids creating N singleton recordset objects
                rows = [((id_,) + template_row) for id_ in self._ids]
                for sub_rows in batched(rows, UPDATE_BATCH_SIZE):
                    self._execute_update(fnames, sub_rows)
            else:
                if self._log_access:
                    log_vals = {
                        "write_uid": self.env.uid,
                        "write_date": self.env.cr.now(),
                    }
                    vals_list = [(log_vals | vals) for vals in vals_list]
                updates = defaultdict(list)
                for id_, vals in zip(self._ids, vals_list, strict=False):
                    fnames, row = zip(*sorted(vals.items()), strict=False)
                    updates[fnames].append((id_,) + row)
                for fnames, rows in updates.items():
                    for sub_rows in batched(rows, UPDATE_BATCH_SIZE):
                        self._execute_update(fnames, sub_rows)

        # update parent_path
        if parent_records:
            parent_records._parent_store_update()

        if _debug:
            _orm_crud.debug(
                "[%.3f ms] _write_multi %s: %d records, %s, %d batches",
                (time.perf_counter() - _t0) * 1000,
                self._name,
                len(self),
                "uniform" if uniform else f"{len(updates)} groups",
                (len(self) + UPDATE_BATCH_SIZE - 1) // UPDATE_BATCH_SIZE,
            )

    def _execute_update(self, fnames, rows):
        """Execute UPDATE FROM VALUES for a group of records sharing the same fields.

        :param fnames: Tuple of field names being updated (sorted).
        :param rows: List of tuples (id, val1, val2, ...) — one per record.
        """
        # --- Backend dispatch: DictBackend or PostgreSQL ---
        storage = self.env.transaction.storage
        if storage is not None:
            # In-memory path: update rows in DictBackend directly.
            # Skips JSONB merge for translated/company-dependent fields —
            # stores as plain values (sufficient for business logic tests).
            tbl = storage._tables.get(self._table, {})
            for row in rows:
                # row is a plain tuple: (id, val1, val2, ...)
                record_id = row[0]
                values = dict(zip(fnames, row[1:], strict=False))
                if record_id in tbl:
                    tbl[record_id].update(values)
                else:
                    tbl[record_id] = {"id": record_id, **values}
            return

        columns = []
        assignments = []
        for fname in fnames:
            field = self._fields[fname]
            assert field.is_column
            column = SQL.identifier(fname)
            # the type cast is necessary for some values, like NULLs
            expr = SQL('"__tmp".%s::%s', column, SQL(field.column_type[1]))
            if field.translate is True:
                # this is the SQL equivalent of:
                # None if expr is None else (
                #     (column or {'en_US': next(iter(expr.values()))}) | expr
                # )
                expr = SQL(
                    """CASE WHEN %(expr)s IS NULL THEN NULL ELSE
                        COALESCE(%(table)s.%(column)s, jsonb_build_object(
                            'en_US', jsonb_path_query_first(%(expr)s, '$.*')
                        )) || %(expr)s
                    END""",
                    table=SQL.identifier(self._table),
                    column=column,
                    expr=expr,
                )
            if field.company_dependent:
                fallbacks = self.env["ir.default"]._get_field_column_fallbacks(
                    self._name, fname
                )
                expr = SQL(
                    """(SELECT jsonb_object_agg(d.key, d.value)
                    FROM jsonb_each(COALESCE(%(table)s.%(column)s, '{}'::jsonb) || %(expr)s) d
                    JOIN jsonb_each(%(fallbacks)s) f
                    ON d.key = f.key AND d.value != f.value)""",
                    table=SQL.identifier(self._table),
                    column=column,
                    expr=expr,
                    fallbacks=fallbacks,
                )
            columns.append(column)
            assignments.append(SQL("%s = %s", column, expr))

        self.env.cr.execute(
            SQL(
                """ UPDATE %(table)s
                SET %(assignments)s
                FROM (VALUES %(values)s) AS "__tmp"("id", %(columns)s)
                WHERE %(table)s."id" = "__tmp"."id"
            """,
                table=SQL.identifier(self._table),
                assignments=SQL(", ").join(assignments),
                values=SQL(", ").join(rows),
                columns=SQL(", ").join(columns),
            )
        )

    def unlink(self) -> typing.Literal[True]:
        """Delete the records in ``self``.

        :raise AccessError: if the user is not allowed to delete all the given records
        :raise UserError: if the record is default property for other records
        """
        if not self:
            return True

        _debug = _orm_crud.isEnabledFor(logging.DEBUG)
        _agg = _orm_profiling_enabled
        if _debug or _agg:
            _t0 = time.perf_counter()

        if _n1_enabled and (tracker := self.env.transaction._n1_tracker):
            tracker.record("unlink", self._name, len(self), frozenset())

        self.check_access("unlink")
        if _debug:
            _t_acl = time.perf_counter()

        from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

        for func in self._ondelete_methods:
            # func._ondelete is True if it should be called during uninstallation
            if func._ondelete or not self.env.context.get(MODULE_UNINSTALL_FLAG):
                func(self)
        if _debug:
            _t_ondelete = time.perf_counter()

        # TOFIX: this avoids an infinite loop when trying to recompute a
        # field, which triggers the recomputation of another field using the
        # same compute function, which then triggers again the computation
        # of those two fields
        core = self.env._core
        if core.has_any_pending():
            # Iterate pending entries (typically few) rather than all model
            # fields (often 100+).  Only clear entries for the current model.
            model_name = self._name
            deleted_ids = self._ids
            for field in list(core.pending_fields()):
                if field.model_name == model_name:
                    core.mark_done(field, deleted_ids)

        self.env.flush_all()

        if _debug:
            _t_flush = time.perf_counter()

        cr = self.env.cr
        Data = self.env["ir.model.data"].sudo().with_context({})
        Defaults = self.env["ir.default"].sudo()
        Attachment = self.env["ir.attachment"].sudo()
        ir_model_data_unlink = Data
        ir_attachment_unlink = Attachment

        # Capture ALL dependency paths before deletion (see _modified_before
        # docstring for why unlink passes ALL fields, not just relational ones).
        # Example: deleting a sale order line recomputes the order's total amount.
        with self.env.protecting(self._fields.values(), self):
            self._modified_before(self._fields)
        if _debug:
            _t_before = time.perf_counter()

        for sub_ids in batched(self.ids, cr.BATCH_SIZE):
            data, attachments = self._unlink_process_batch(
                sub_ids,
                Data,
                Defaults,
                Attachment,
            )
            ir_model_data_unlink |= data
            ir_attachment_unlink |= attachments
        if _debug:
            _t_sql = time.perf_counter()

        # Invalidate the *whole* cache, since the ORM does not handle all
        # changes made in the database, like cascading delete!
        # Targeted invalidation (_invalidate_unlink_caches) misses non-stored
        # computed/related fields that depend on FK fields through multi-hop
        # chains (e.g. personal_stage_type_id → personal_stage_id → stage_id).
        self.env.invalidate_all(flush=False)

        if ir_model_data_unlink:
            ir_model_data_unlink.unlink()
        if ir_attachment_unlink:
            ir_attachment_unlink.unlink()

        # auditing: deletions are infrequent and leave no trace in the database
        _unlink.info(
            "User #%s deleted %s records with IDs: %r",
            self.env.uid,
            self._name,
            self.ids,
        )

        if _debug or _agg:
            _t_end = time.perf_counter()
        if _debug:
            _orm_crud.debug(
                "[%.3f ms] unlink %s: %d records"
                " | acl=%.1f ondelete=%.1f flush=%.1f before=%.1f"
                " sql=%.1f invalidate=%.1f",
                (_t_end - _t0) * 1000,
                self._name,
                len(self),
                (_t_acl - _t0) * 1000,
                (_t_ondelete - _t_acl) * 1000,
                (_t_flush - _t_ondelete) * 1000,
                (_t_before - _t_flush) * 1000,
                (_t_sql - _t_before) * 1000,
                (_t_end - _t_sql) * 1000,
            )
        if _agg and (p := self.env.transaction._orm_profiler):
            p.record_unlink(self._name, len(self), _t_end - _t0)

        return True

    def _unlink_process_batch(self, sub_ids, Data, Defaults, Attachment):
        """Process one batch of record deletions during unlink().

        Executes DELETE SQL, collects ir.model.data and ir.attachment records
        for cleanup, handles company-dependent M2O restrict/set-null cascade,
        and discards ir.default entries.

        :param sub_ids: tuple of record IDs to delete in this batch
        :param Data: ir.model.data model proxy (sudo, empty context)
        :param Defaults: ir.default model proxy (sudo)
        :param Attachment: ir.attachment model proxy (sudo)
        :return: (data_records, attachment_records) to unlink after all batches
        """
        # --- Backend dispatch: DictBackend or PostgreSQL ---
        storage = self.env.transaction.storage
        if storage is not None:
            # In-memory path: remove rows from DictBackend.
            # Skip ir.model.data / ir.attachment / company-dependent cleanup —
            # those models may not exist in the test context.
            tbl = storage._tables.get(self._table, {})
            for id_ in sub_ids:
                tbl.pop(id_, None)
            return Data.browse(), Attachment.browse()

        from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

        cr = self.env.cr
        records = self.browse(sub_ids)

        cr.execute(
            SQL(
                "DELETE FROM %s WHERE id = ANY(%s)",
                SQL.identifier(self._table),
                list(sub_ids),
            )
        )

        # Removing the ir_model_data reference if the record being deleted
        # is a record created by xml/csv file, as these are not connected
        # with real database foreign keys, and would be dangling references.
        #
        # Note: the following steps are performed as superuser to avoid
        # access rights restrictions, and with no context to avoid possible
        # side-effects during admin calls.
        data = Data.search([("model", "=", self._name), ("res_id", "in", sub_ids)])

        # For the same reason, remove the relevant records in ir_attachment
        # (the search is performed with sql as the search method of
        # ir_attachment is overridden to hide attachments of deleted
        # records)
        cr.execute(
            SQL(
                "SELECT id FROM ir_attachment WHERE res_model=%s AND res_id = ANY(%s)",
                self._name,
                list(sub_ids),
            )
        )
        attachments = Attachment.browse(row[0] for row in cr.fetchall())

        # don't allow fallback value in ir.default for many2one company dependent fields to be deleted
        # Exception: when MODULE_UNINSTALL_FLAG, these fallbacks can be deleted by Defaults.discard_records(records)
        if (
            many2one_fields := self.env.registry.many2one_company_dependents[self._name]
        ) and not self.env.context.get(MODULE_UNINSTALL_FLAG):
            IrModelFields = self.env["ir.model.fields"]
            field_ids = tuple(
                IrModelFields._get_ids(field.model_name).get(field.name)
                for field in many2one_fields
            )
            sub_ids_json_text = tuple(json_dumps(id_) for id_ in sub_ids)
            if default := Defaults.search(
                [
                    ("field_id", "in", field_ids),
                    ("json_value", "in", sub_ids_json_text),
                ],
                limit=1,
                order="id desc",
            ):
                ir_field = default.field_id.sudo()
                field = self.env[ir_field.model]._fields[ir_field.name]
                record = self.browse(json_loads(default.json_value))
                raise UserError(
                    _(
                        "Unable to delete %(record)s because it is used as the default value of %(field)s",
                        record=record,
                        field=field,
                    )
                )

        # on delete set null/restrict for jsonb company dependent many2one
        for field in many2one_fields:
            model = self.env[field.model_name]
            if field.ondelete == "restrict" and not self.env.context.get(
                MODULE_UNINSTALL_FLAG
            ):
                if res := self.env.execute_query(
                    SQL(
                        """
                    SELECT id, %(field)s
                    FROM %(table)s
                    WHERE %(field)s IS NOT NULL
                    AND %(field)s @? %(jsonpath)s
                    ORDER BY id
                    LIMIT 1
                    """,
                        table=SQL.identifier(model._table),
                        field=SQL.identifier(field.name),
                        jsonpath=f"$.* ? ({' || '.join(f'@ == {id_}' for id_ in sub_ids)})",
                    )
                ):
                    on_restrict_id, field_json = res[0]
                    to_delete_id = next(iter(id_ for id_ in field_json.values()))
                    on_restrict_record = model.browse(on_restrict_id)
                    to_delete_record = self.browse(to_delete_id)
                    raise UserError(
                        _(
                            "You cannot delete %(to_delete_record)s, as it is used by %(on_restrict_record)s",
                            to_delete_record=to_delete_record,
                            on_restrict_record=on_restrict_record,
                        )
                    )
            else:
                # Set null on company-dependent M2O references.
                # RETURNING id lets us trigger modified() on affected
                # records so their computed dependents get recomputed.
                affected = self.env.execute_query(
                    SQL(
                        """
                    UPDATE %(table)s
                    SET %(field)s = (
                        SELECT jsonb_object_agg(
                            key,
                            CASE
                                WHEN value::int4 in %(ids)s THEN NULL
                                ELSE value::int4
                            END)
                        FROM jsonb_each_text(%(field)s)
                    )
                    WHERE %(field)s IS NOT NULL
                    AND %(field)s @? %(jsonpath)s
                    RETURNING id
                    """,
                        table=SQL.identifier(model._table),
                        field=SQL.identifier(field.name),
                        ids=sub_ids,
                        jsonpath=f"$.* ? ({' || '.join(f'@ == {id_}' for id_ in sub_ids)})",
                    )
                )
                if affected:
                    affected_recs = model.browse(row[0] for row in affected)
                    affected_recs.modified([field.name])

        # For the same reason, remove the defaults having some of the
        # records as value
        Defaults.discard_records(records)

        return data, attachments

    def _invalidate_unlink_caches(self, fk_refs, cd_m2o_fields):
        """Invalidate caches after deleting records.

        Performs targeted cache invalidation instead of invalidate_all():

        1. Deleted model's own fields + their inverses on other models
        2. FK-referencing models affected by PG ON DELETE cascade/set-null
        3. Company-dependent M2O JSONB columns updated by raw SQL

        :param fk_refs: iterable of (m2o_field, ondelete) from pool.field_fk_refs
        :param cd_m2o_fields: iterable of company-dependent M2O fields
        """
        deleted_ids = tuple(self.ids)
        env = self.env

        # 1. Invalidate the deleted model's own fields for the deleted IDs,
        #    plus their inverse fields on ALL models (including same-model
        #    self-referential M2M pairs like stock.move.move_orig_ids ↔
        #    move_dest_ids where surviving records still cache refs to
        #    deleted ones).
        for field in self._fields.values():
            field._invalidate_cache(env, deleted_ids)
            for invf in self.pool.field_inverses.get(field, ()):
                invf._invalidate_cache(env)

        # 2. Invalidate FK-referencing models affected by PG ON DELETE
        for m2o_field, ondelete in fk_refs:
            if ondelete == "cascade":
                # Rows cascade-deleted by PG — invalidate all fields
                for f in env[m2o_field.model_name]._fields.values():
                    f._invalidate_cache(env)
            elif ondelete == "set null":
                # PG set M2O to NULL — invalidate that field + its inverses
                m2o_field._invalidate_cache(env)
                for invf in self.pool.field_inverses.get(m2o_field, ()):
                    invf._invalidate_cache(env, deleted_ids)

        # 3. Company-dependent M2O: JSONB columns updated by raw SQL above
        for field in cd_m2o_fields:
            field._invalidate_cache(env)
            for invf in self.pool.field_inverses.get(field, ()):
                invf._invalidate_cache(env, deleted_ids)

        # 4. Invalidate one-directional M2M fields on other models that
        #    reference this model as comodel but have no registered inverse.
        #    Example: wizard fields (stock.quant.relocate.quant_ids) that
        #    cache references to deleted records.  These are not reachable
        #    via the field_inverses walk in step 1.
        model_name = self._name
        field_inverses = self.pool.field_inverses
        for model_cls in self.pool.models.values():
            if model_cls._abstract:
                continue
            for field in model_cls._fields.values():
                if (
                    field.type == "many2many"
                    and field.comodel_name == model_name
                    and not field_inverses.get(field)
                ):
                    field._invalidate_cache(env)

    def _parent_store_create(self) -> None:
        """Set the parent_path field on ``self`` after its creation."""
        if not self._parent_store:
            return
        # DictBackend: skip parent_path SQL — hierarchy not supported yet
        if self.env.transaction.storage is not None:
            return

        updated = self.env.execute_query(
            SQL(
                """ UPDATE %(table)s node
                SET parent_path=concat((
                        SELECT parent.parent_path
                        FROM %(table)s parent
                        WHERE parent.id=node.%(parent)s
                    ), node.id, '/')
                WHERE node.id IN %(ids)s
                RETURNING node.id, node.parent_path """,
                table=SQL.identifier(self._table),
                parent=SQL.identifier(self._parent_name),
                ids=tuple(self.ids),
            )
        )

        # update the cache of updated nodes, and determine what to recompute
        field = self._fields["parent_path"]
        for id_, path in updated:
            field._update_cache(self.browse(id_), path)

    def _parent_store_update_prepare(self, vals_list: list[ValuesType]) -> Self:
        """Return the records in ``self`` that must update their parent_path
        field. This must be called before updating the parent field.
        """
        if not self._parent_store:
            return self.browse()
        # DictBackend: skip parent_path SQL — hierarchy not supported yet
        if self.env.transaction.storage is not None:
            return self.browse()

        # associate each new parent_id to its corresponding record ids
        parent_to_ids = defaultdict(list)
        for id_, vals in zip(self._ids, vals_list, strict=False):
            if self._parent_name in vals:
                parent_to_ids[vals[self._parent_name]].append(id_)

        if not parent_to_ids:
            return self.browse()

        self.flush_recordset([self._parent_name])

        # return the records for which the parent field will change
        sql_parent = SQL.identifier(self._parent_name)
        conditions = []
        for parent_id, ids in parent_to_ids.items():
            if parent_id:
                condition = SQL(
                    "(%s != %s OR %s IS NULL)",
                    sql_parent,
                    parent_id,
                    sql_parent,
                )
            else:
                condition = SQL("%s IS NOT NULL", sql_parent)
            conditions.append(SQL('("id" = ANY(%s) AND %s)', list(ids), condition))

        rows = self.env.execute_query(
            SQL(
                "SELECT id FROM %s WHERE %s ORDER BY id",
                SQL.identifier(self._table),
                SQL(" OR ").join(conditions),
            )
        )
        return self.browse(row[0] for row in rows)

    def _parent_store_update(self) -> None:
        """Update the parent_path field of ``self``."""
        for parent, records in self.grouped(self._parent_name).items():
            # determine new prefix of parent_path of records
            prefix = parent.parent_path or ""

            # check for recursion
            if prefix:
                parent_ids = {int(label) for label in prefix.split("/")[:-1]}
                if not parent_ids.isdisjoint(records._ids):
                    raise UserError(_("Recursion Detected."))

            # update parent_path of all records and their descendants
            updated = dict(
                self.env.execute_query(
                    SQL(
                        """ UPDATE %(table)s child
                    SET parent_path = concat(%(prefix)s::text, substr(child.parent_path,
                            length(node.parent_path) - length(node.id || '/') + 1))
                    FROM %(table)s node
                    WHERE node.id IN %(ids)s
                    AND child.parent_path LIKE concat(node.parent_path, %(wildcard)s::text)
                    RETURNING child.id, child.parent_path """,
                        table=SQL.identifier(self._table),
                        prefix=prefix,
                        ids=tuple(records.ids),
                        wildcard="%",
                    )
                )
            )

            # update the cache of updated nodes, and determine what to recompute
            field = self._fields["parent_path"]
            for id_, path in updated.items():
                field._update_cache(self.browse(id_), path)
            records = self.browse(updated)
            records.modified(["parent_path"])
