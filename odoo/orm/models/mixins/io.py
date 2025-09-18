"""
Import/Export operations mixin for BaseModel.

This module provides the IOMixin class containing all import/export-related
methods. BaseModel inherits from this mixin.

Methods:
- __ensure_xml_id: Create missing external ids for export
- _export_rows: Export records to row format
- export_data: Public export API
- load: Import data matrix
- _extract_records: Extract records from import data
- _convert_records: Convert imported records for database
- _load_records_write: Write during data loading
- _load_records_create: Create during data loading
- _load_records: Main data loading implementation
"""

import collections
import contextlib
import functools
import itertools
import logging
import typing
import uuid
from collections import defaultdict

import psycopg

from odoo.exceptions import UserError, ValidationError
from odoo.libs.lru import LRU
from odoo.tools import SQL, groupby, unique
from odoo.tools.translate import _

from ... import decorators as api
from ..._typing import ValuesType
from ...helpers import get_columns_from_sql_diagnostics, itemgetter_tuple
from ...parsing import fix_import_export_id_paths

_logger = logging.getLogger("odoo.models")


from collections.abc import Callable, Generator, Iterator
from typing import Self


class IOMixin:
    """Mixin providing import/export operations functionality.

    This mixin is inherited by BaseModel and provides methods for importing
    and exporting data.
    """

    __slots__ = ()

    # Type hints for attributes provided by BaseModel (runtime)
    _fields: dict
    _table: str
    _name: str
    _inherits: dict
    env: typing.Any
    pool: typing.Any

    def __ensure_xml_id(self, skip: bool = False) -> Iterator[tuple[Self, str | None]]:
        """Create missing external ids for records in ``self``, and return an
        iterator of pairs ``(record, xmlid)`` for the records in ``self``.
        """
        if skip:
            return ((record, None) for record in self)

        if not self:
            return iter([])

        if not self._is_an_ordinary_table():
            raise Exception(
                f"You can not export the column ID of model {self._name}, because the "
                f"table {self._table} is not an ordinary table."
            )

        modname = "__export__"

        cr = self.env.cr
        cr.execute(
            SQL(
                """
            SELECT res_id, module, name
            FROM ir_model_data
            WHERE model = %s AND res_id = ANY(%s)
        """,
                self._name,
                list(self.ids),
            )
        )
        xids = {res_id: (module, name) for res_id, module, name in cr.fetchall()}

        def to_xid(record_id):
            module, name = xids[record_id]
            return f"{module}.{name}" if module else name

        # create missing xml ids
        missing = self.filtered(lambda r: r.id not in xids)
        if not missing:
            return ((record, to_xid(record.id)) for record in self)

        xids.update(
            (
                r.id,
                (
                    modname,
                    f"{r._table}_{r.id}_{uuid.uuid4().hex[:8]}",
                ),
            )
            for r in missing
        )
        fields = ["module", "model", "name", "res_id"]

        cr.copy_from(
            "ir_model_data",
            fields,
            [
                (modname, record._name, xids[record.id][1], record.id)
                for record in missing
            ],
        )
        self.env["ir.model.data"].invalidate_model(fields)

        return ((record, to_xid(record.id)) for record in self)

    def _export_rows(
        self, fields: list[list[str]], *, _is_toplevel_call: bool = True
    ) -> list[list]:
        """Export fields of the records in ``self``.

        :param fields: list of lists of fields to traverse
        :param _is_toplevel_call: used when recursing, avoid using when calling from outside
        :return: list of lists of corresponding values
        """
        import_compatible = self.env.context.get("import_compat", True)
        lines = []

        if not _is_toplevel_call:
            # {properties_field: {property_name: [property_type, {record_id: value}]}}
            cache_properties = self.env.cr.cache["export_properties_cache"]
        else:
            cache_properties = self.env.cr.cache["export_properties_cache"] = (
                defaultdict(dict)
            )

            def fill_properties_cache(records, fnames_by_path, fname):
                """Fill the cache for the ``fname`` properties field and return it"""
                cache_properties_field = cache_properties[records._fields[fname]]

                # read properties to have all the logic of Properties.convert_to_read_multi
                for row in records.read([fname]):
                    properties = row[fname]
                    if not properties:
                        continue
                    rec_id = row["id"]

                    for property in properties:
                        current_prop_name = property["name"]
                        if f"{fname}.{current_prop_name}" not in fnames_by_path:
                            continue
                        property_type = property["type"]
                        if current_prop_name not in cache_properties_field:
                            cache_properties_field[current_prop_name] = [
                                property_type,
                                {},
                            ]

                        __, cache_by_id = cache_properties_field[current_prop_name]
                        if rec_id in cache_by_id:
                            continue

                        value = property.get("value")
                        if property_type in ("many2one", "many2many"):
                            if not isinstance(value, list):
                                value = [value] if value else []
                            value = self.env[property["comodel"]].browse(
                                [val[0] for val in value]
                            )
                        elif property_type == "tags" and value:
                            value = ",".join(
                                next(
                                    iter(
                                        tag[1]
                                        for tag in property["tags"]
                                        if tag[0] == v
                                    ),
                                    "",
                                )
                                for v in value
                            )
                        elif property_type == "selection":
                            value = dict(property["selection"]).get(value, "")
                        cache_by_id[rec_id] = value

            def fetch_fields(records, field_paths):
                """Fill the cache of ``records`` for all ``field_paths`` recursively included properties"""
                if not records:
                    return

                fnames_by_path = dict(
                    groupby(
                        [
                            path
                            for path in field_paths
                            if path and path[0] not in ("id", ".id")
                        ],
                        lambda path: path[0],
                    )
                )

                # Fetch needed fields (remove '.property_name' part)
                fnames = list(unique(fname.split(".")[0] for fname in fnames_by_path))
                records.fetch(fnames)
                # Fill the cache of the properties field
                for fname in fnames:
                    field = records._fields[fname]
                    if field.type == "properties":
                        fill_properties_cache(records, fnames_by_path, fname)

                # Call it recursively for relational field (included property relational field)
                for fname, paths in fnames_by_path.items():
                    if "." in fname:  # Properties field
                        fname, prop_name = fname.split(".")
                        field = records._fields[fname]
                        assert field.type == "properties" and prop_name

                        property_type, property_cache = cache_properties[field].get(
                            prop_name, ("char", None)
                        )
                        if (
                            property_type not in ("many2one", "many2many")
                            or not property_cache
                        ):
                            continue
                        model = next(iter(property_cache.values())).browse()
                        subrecords = model.union(
                            *[
                                property_cache[rec_id]
                                for rec_id in records.ids
                                if rec_id in property_cache
                            ]
                        )
                    else:  # Normal field
                        field = records._fields[fname]
                        if not field.relational:
                            continue
                        subrecords = records[fname]

                    paths = [path[1:] or ["display_name"] for path in paths]
                    fetch_fields(subrecords, paths)

            fetch_fields(self, fields)

        for record in self:
            # main line of record, initially empty
            current = [""] * len(fields)
            lines.append(current)

            # set of primary fields followed by secondary field(s)
            primary_done = set()

            # process column by column
            for i, path in enumerate(fields):
                if not path:
                    continue

                name = path[0]
                if name in primary_done:
                    continue

                if name == ".id":
                    current[i] = str(record.id)
                elif name == "id":
                    current[i] = (record._name, record.id)
                else:
                    prop_name = None
                    if "." in name:  # Properties field
                        fname, prop_name = name.split(".")
                        field = record._fields[fname]
                        field_type, cache_value = cache_properties[field].get(
                            prop_name, ("char", None)
                        )
                        value = cache_value.get(record.id, "") if cache_value else ""
                    else:  # Normal field
                        field = record._fields[name]
                        field_type = field.type
                        value = record[name]

                    # this part could be simpler, but it has to be done this way
                    # in order to reproduce the former behavior
                    if not isinstance(value, IOMixin):
                        current[i] = field.convert_to_export(value, record)

                    elif import_compatible and field_type == "reference":
                        current[i] = f"{value._name},{value.id}"

                    else:
                        primary_done.add(name)
                        # recursively export the fields that follow name; use
                        # 'display_name' where no subfield is exported
                        fields2 = [
                            (p[1:] or ["display_name"] if p and p[0] == name else [])
                            for p in fields
                        ]

                        # in import_compat mode, m2m should always be exported as
                        # a comma-separated list of xids or names in a single cell
                        if import_compatible and field_type == "many2many":
                            index = None
                            # find out which subfield the user wants & its
                            # location as we might not get it as the first
                            # column we encounter
                            for name in ["id", "name", "display_name"]:
                                with contextlib.suppress(ValueError):
                                    index = fields2.index([name])
                                    break
                            if index is None:
                                # not found anything, assume we just want the
                                # display_name in the first column
                                name = None
                                index = i

                            if name == "id":
                                xml_ids = [xid for _, xid in value.__ensure_xml_id()]
                                current[index] = ",".join(xml_ids)
                            else:
                                current[index] = (
                                    ",".join(value.mapped("display_name"))
                                    if value
                                    else ""
                                )
                            continue

                        lines2 = value._export_rows(fields2, _is_toplevel_call=False)
                        if lines2:
                            # merge first line with record's main line
                            for j, val in enumerate(lines2[0]):
                                if val or isinstance(val, (int, float)):
                                    current[j] = val
                            # append the other lines at the end
                            lines += lines2[1:]
                        else:
                            current[i] = ""

        # if any xid should be exported, only do so at toplevel
        if _is_toplevel_call and any(f[-1] == "id" for f in fields):
            bymodels = collections.defaultdict(set)
            xidmap = collections.defaultdict(list)
            # collect all the tuples in "lines" (along with their coordinates)
            for i, line in enumerate(lines):
                for j, cell in enumerate(line):
                    if isinstance(cell, tuple):
                        bymodels[cell[0]].add(cell[1])
                        xidmap[cell].append((i, j))
            # for each model, xid-export everything and inject in matrix
            for model, ids in bymodels.items():
                for record, xid in self.env[model].browse(ids).__ensure_xml_id():
                    for i, j in xidmap.pop((record._name, record.id)):
                        lines[i][j] = xid
            assert not xidmap, (
                f"failed to export xids for "
                f"{', '.join(f'{k}:{v}' for k, v in xidmap.items())}"
            )

        if _is_toplevel_call:
            self.env.cr.cache.pop("export_properties_cache", None)

        return lines

    def export_data(self, fields_to_export: list[str]) -> dict[str, list]:
        """Export fields for selected objects.

        This method is used when exporting data via client menu.

        :param fields_to_export: list of fields
        :returns: dictionary with a *datas* matrix
        """
        if not (
            self.env.is_admin() or self.env.user.has_group("base.group_allow_export")
        ):
            raise UserError(
                _(
                    "You don't have the rights to export data. Please contact an Administrator."
                )
            )
        fields_to_export = [fix_import_export_id_paths(f) for f in fields_to_export]
        return {"datas": self._export_rows(fields_to_export)}

    @api.model
    def load(self, fields: list[str], data: list[list[str]]) -> dict:
        """Attempt to load the data matrix, and return a list of ids (or
        ``False`` if there was an error and no id could be generated) and a
        list of messages.

        The ids are those of the records created and saved (in database), in
        the same order they were extracted from the file. They can be passed
        directly to :meth:`~read`.

        :param fields: list of fields to import, at the same index as the corresponding data
        :param data: row-major matrix of data to import
        :returns: ``{ids: list[int] | False, messages: list[dict], nextrow: int}``
        """
        from ...fields.relational import One2many

        # determine values of mode, current_module and noupdate
        mode = self.env.context.get("mode", "init")
        current_module = self.env.context.get("module", "__import__")
        noupdate = self.env.context.get("noupdate", False)
        # add current module in context for the conversion of xml ids
        self = self.with_context(_import_current_module=current_module)

        cr = self.env.cr
        savepoint = cr.savepoint()

        fields = [fix_import_export_id_paths(f) for f in fields]

        ids = []
        messages = []

        # list of (xid, vals, info) for records to be created in batch
        batch = []
        batch_xml_ids = set()
        # models in which we may have created / modified data, therefore might
        # require flushing in order to name_search: the root model and any
        # o2m
        creatable_models = {self._name}
        for field_path in fields:
            if field_path[0] in (None, "id", ".id"):
                continue
            model_fields = self._fields
            for field_name in field_path:
                if field_name in (None, "id", ".id"):
                    break

                if isinstance(model_fields.get(field_name), One2many):
                    comodel = model_fields[field_name].comodel_name
                    creatable_models.add(comodel)
                    model_fields = self.env[comodel]._fields

        def flush(*, xml_id=None, model=None):
            if not batch:
                return

            assert not (
                xml_id and model
            ), "flush can specify *either* an external id or a model, not both"

            if xml_id and xml_id not in batch_xml_ids:
                if xml_id not in self.env:
                    return
            if model and model not in creatable_models:
                return

            data_list = [
                {"xml_id": xid, "values": vals, "info": info, "noupdate": noupdate}
                for xid, vals, info in batch
            ]
            batch.clear()
            batch_xml_ids.clear()

            # try to create in batch
            global_error_message = None
            try:
                with cr.savepoint():
                    recs = self._load_records(data_list, mode == "update")
                    ids.extend(recs.ids)
                return
            except psycopg.InternalError as e:
                # broken transaction, exit and hope the source error was already logged
                if not any(message["type"] == "error" for message in messages):
                    info = data_list[0]["info"]
                    messages.append(
                        dict(
                            info,
                            type="error",
                            message=_("Unknown database error: '%s'", e),
                        )
                    )
                return
            except UserError as e:
                global_error_message = dict(
                    data_list[0]["info"], type="error", message=str(e)
                )
            except Exception:
                _logger.debug("Batch load failed, retrying record by record", exc_info=True)

            errors = 0
            # try again, this time record by record
            for i, rec_data in enumerate(data_list, 1):
                try:
                    rec = self._load_records([rec_data], mode == "update")
                    cr.flush()  # make sure flush exceptions are raised here
                    ids.append(rec.id)
                except psycopg.Warning as e:
                    savepoint.rollback()
                    info = rec_data["info"]
                    messages.append(dict(info, type="warning", message=str(e)))
                except psycopg.Error as e:
                    savepoint.rollback()
                    info = rec_data["info"]
                    pg_error_info = {"message": self._sql_error_to_message(e)}
                    if e.diag.table_name == self._table:
                        e_fields = get_columns_from_sql_diagnostics(
                            self.env.cr, e.diag, check_registry=True
                        )
                        if len(e_fields) == 1:
                            pg_error_info["field"] = e_fields[0]
                    messages.append(dict(info, type="error", **pg_error_info))
                    # Failed to write, log to messages, rollback savepoint (to
                    # avoid broken transaction) and keep going
                    errors += 1
                except UserError as e:
                    savepoint.rollback()
                    info = rec_data["info"]
                    messages.append(dict(info, type="error", message=str(e)))
                    errors += 1
                except Exception as e:
                    savepoint.rollback()
                    _logger.debug("Error while loading record", exc_info=True)
                    info = rec_data["info"]
                    message = _(
                        "Unknown error during import: %(error_type)s: %(error_message)s",
                        error_type=e.__class__,
                        error_message=e,
                    )
                    moreinfo = _("Resolve other errors first")
                    messages.append(
                        dict(
                            info,
                            type="error",
                            message=message,
                            moreinfo=moreinfo,
                        )
                    )
                    # Failed for some reason, perhaps due to invalid data supplied,
                    # rollback savepoint and keep going
                    errors += 1
                if errors >= 10 and (errors >= i / 10):
                    messages.append(
                        {
                            "type": "warning",
                            "message": _(
                                "Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors."
                            ),
                        }
                    )
                    break
            if (
                errors > 0
                and global_error_message
                and global_error_message not in messages
            ):
                # If we cannot create the records 1 by 1, we display the error raised when we created the records simultaneously
                messages.insert(0, global_error_message)

        # make 'flush' available to the methods below, in the case where XMLID
        # resolution fails, for instance
        flush_recordset = self.with_context(import_flush=flush, import_cache=LRU(1024))

        # The import limit is passed via context because load()'s public API
        # (fields, data) has no parameter for it.  Changing the API would break
        # all callers (web client, base_import, etc.) — not worth the churn.
        limit = self.env.context.get("_import_limit")
        if limit is None:
            limit = float("inf")
        extracted = flush_recordset._extract_records(
            fields, data, log=messages.append, limit=limit
        )

        converted = flush_recordset._convert_records(
            extracted, log=messages.append, savepoint=savepoint
        )

        info = {"rows": {"to": -1}}
        for id, xid, record, info in converted:
            if self.env.context.get("import_file") and self.env.context.get(
                "import_skip_records"
            ):
                if any(
                    record.get(field) is None
                        for field in self.env.context["import_skip_records"]
                ):
                    continue
            if xid:
                xid = xid if "." in xid else f"{current_module}.{xid}"
                batch_xml_ids.add(xid)
            elif id:
                record["id"] = id
            batch.append((xid, record, info))

        flush()
        if any(message["type"] == "error" for message in messages):
            savepoint.rollback()
            ids = False
            # cancel all changes done to the registry/ormcache
            self.pool.reset_changes()
        savepoint.close(rollback=False)

        nextrow = info["rows"]["to"] + 1
        if nextrow < limit:
            nextrow = 0
        return {
            "ids": ids,
            "messages": messages,
            "nextrow": nextrow,
        }

    def _extract_records(
        self,
        field_paths: list[list[str | None]],
        data: list[list[str]],
        log: Callable = lambda a: None,
        limit: float = float("inf"),
    ) -> Generator[tuple[dict, dict]]:
        """Generates record dicts from the data sequence.

        The result is a generator of dicts mapping field names to raw
        (unconverted, unvalidated) values.

        For relational fields, if sub-fields were provided the value will be
        a list of sub-records

        The following sub-fields may be set on the record (by key):

        * None is the display_name for the record (to use with name_create/name_search)
        * "id" is the External ID for the record
        * ".id" is the Database ID for the record
        """
        fields = self._fields

        get_o2m_values = itemgetter_tuple(
            [
                index
                for index, fnames in enumerate(field_paths)
                if fnames[0] in fields and fields[fnames[0]].type == "one2many"
            ]
        )
        get_nono2m_values = itemgetter_tuple(
            [
                index
                for index, fnames in enumerate(field_paths)
                if fnames[0] not in fields or fields[fnames[0]].type != "one2many"
            ]
        )

        # Checks if the provided row has any non-empty one2many fields
        def only_o2m_values(row):
            return any(get_o2m_values(row)) and not any(get_nono2m_values(row))

        property_definitions = {}
        property_columns = defaultdict(list)
        for fname, *__ in field_paths:
            if not fname:
                continue
            if "." not in fname:
                if fname not in fields:
                    raise ValueError(f"Invalid field name {fname!r}")
                continue

            f_prop_name, property_name = fname.split(".")
            if f_prop_name not in fields or fields[f_prop_name].type != "properties":
                # Can be .id
                continue

            definition = self.get_property_definition(fname)
            if not definition:
                # Can happen if someone remove the property, UserError ?
                raise ValueError(
                    f"Property {property_name!r} doesn't have any definition on {fname!r} field"
                )

            property_definitions[fname] = definition
            property_columns[f_prop_name].append(fname)

        # m2o fields can't be on multiple lines so don't take it in account
        # for only_o2m_values rows filter, but special-case it later on to
        # be handled with relational fields (as it can have subfields).
        # Pre-compute set of relational field names for O(1) lookup per row
        relational_fnames = {fname for fname in fields if fields[fname].relational} | {
            fname
            for fname, defn in property_definitions.items()
            if defn.get("type") in ("many2one", "many2many")
        }

        def is_relational(fname):
            return fname in relational_fnames

        index = 0
        while index < len(data) and index < limit:
            row = data[index]

            # copy non-relational fields to record dict
            record = {
                fnames[0]: value
                for fnames, value in zip(field_paths, row, strict=False)
                if not is_relational(fnames[0])
            }

            # Get all following rows which have relational values attached to
            # the current record (no non-relational values)
            record_span = itertools.takewhile(
                only_o2m_values,
                (data[j] for j in range(index + 1, len(data))),
            )
            # stitch record row back on for relational fields
            record_span = list(itertools.chain([row], record_span))

            for relfield, *__ in field_paths:
                if not is_relational(relfield):
                    continue

                if relfield not in property_definitions:
                    comodel = self.env[fields[relfield].comodel_name]
                else:
                    comodel = self.env[property_definitions[relfield]["comodel"]]

                # get only cells for this sub-field, should be strictly
                # non-empty, field path [None] is for display_name field
                indices, subfields = zip(
                    *(
                        (index, fnames[1:] or [None])
                        for index, fnames in enumerate(field_paths)
                        if fnames[0] == relfield
                    ), strict=False
                )

                # return all rows which have at least one value for the
                # subfields of relfield
                relfield_data = [
                    it for it in map(itemgetter_tuple(indices), record_span) if any(it)
                ]
                record[relfield] = [
                    subrecord
                    for subrecord, _subinfo in comodel._extract_records(
                        subfields, relfield_data, log=log
                    )
                ]

            for (
                properties_fname,
                property_indexes_names,
            ) in property_columns.items():
                properties = []
                for property_name in property_indexes_names:
                    value = record.pop(property_name)
                    properties.append(
                        dict(**property_definitions[property_name], value=value)
                    )
                record[properties_fname] = properties

            yield (
                record,
                {
                    "rows": {
                        "from": index,
                        "to": index + len(record_span) - 1,
                    }
                },
            )
            index += len(record_span)

    @api.model
    def _convert_records(
        self,
        records: Generator[tuple[dict, dict]],
        *,
        log: Callable = lambda a: None,
        savepoint: typing.Any,
    ) -> Generator[tuple[int | bool, str | bool, dict, dict]]:
        """Convert records from the source iterable (recursive dicts of
        strings) into forms which can be written to the database (via
        ``self.create`` or ``(ir.model.data)._update``).

        :returns: generator of ``(id, xid, converted_record, info)`` tuples
        """
        field_names = {name: field.string for name, field in self._fields.items()}
        if self.env.lang:
            field_names.update(self.env["ir.model.fields"].get_field_string(self._name))

        convert = self.env["ir.fields.converter"].for_model(self, savepoint=savepoint)

        def _log(base, record, field, exception):
            type = "warning" if isinstance(exception, Warning) else "error"
            # logs the logical (not human-readable) field name for automated
            # processing of response, but injects human readable in message
            field_name = field_names[field]
            exc_vals = dict(base, record=record, field=field_name)
            record = dict(
                base,
                type=type,
                record=record,
                field=field,
                message=str(exception.args[0]) % exc_vals,
            )
            if len(exception.args) > 1:
                info = {}
                if exception.args[1] and isinstance(exception.args[1], dict):
                    info = exception.args[1]
                # ensure field_name is added to the exception. Used in import to
                # concatenate multiple errors in the same block
                info["field_name"] = field_name
                record.update(info)
            log(record)

        for stream_index, (record, extras) in enumerate(records):
            # xid
            xid = record.get("id", False)
            # dbid
            dbid = False
            if record.get(".id"):
                try:
                    dbid = int(record[".id"])
                except ValueError:
                    # in case of overridden id column
                    dbid = record[".id"]
                if not self.search([("id", "=", dbid)]):
                    log(
                        dict(
                            extras,
                            type="error",
                            record=stream_index,
                            field=".id",
                            message=_("Unknown database identifier '%s'", dbid),
                        )
                    )
                    dbid = False

            converted = convert(record, functools.partial(_log, extras, stream_index))

            yield dbid, xid, converted, dict(extras, record=stream_index)

    def _load_records_write(self, values: ValuesType) -> None:
        self.ensure_one()
        to_write = (
            {}
        )  # Deferred the write to avoid using the old definition if it changed
        for fname in list(values):
            if fname not in self._fields or self._fields[fname].type != "properties":
                continue
            field_converter = self._fields[fname].convert_to_cache
            to_write[fname] = dict(
                self[fname]._values or {},
                **field_converter(values.pop(fname), self, validate=False),
            )

        self.write(values)
        if to_write:
            self.write(to_write)
            # Because we don't know which properties was linked to which definition,
            # we can know clean properties (note that it is not mandatory, we can wait
            # that client change the record in a Form view)
            self._clean_properties()

    def _load_records_create(self, vals_list: list[ValuesType]) -> Self:
        records = self.create(vals_list)
        if any(field.type == "properties" for field in self._fields.values()):
            records._clean_properties()
        return records

    def _load_records(self, data_list: list[dict], update: bool = False) -> Self:
        """Create or update records of this model, and assign XMLIDs.

        :param data_list: list of dicts with keys ``xml_id`` (XMLID to
            assign), ``noupdate`` (flag on XMLID), ``values`` (field values)
        :param update: should be ``True`` when upgrading a module
        :return: the records corresponding to ``data_list``
        """
        original_self = self.browse()

        imd = self.env["ir.model.data"].sudo()

        # The algorithm below partitions 'data_list' into three sets: the ones
        # to create, the ones to update, and the others. For each set, we assign
        # data['record'] for each data. All those records are then retrieved for
        # the result.

        # determine existing xml_ids
        xml_ids = [data["xml_id"] for data in data_list if data.get("xml_id")]
        existing = {
            f"{row[1]}.{row[2]}": row for row in imd._lookup_xmlids(xml_ids, self)
        }

        # determine which records to create and update
        to_create = []  # list of data
        to_update = []  # list of data
        imd_data_list = []  # list of data for _update_xmlids()

        for data in data_list:
            xml_id = data.get("xml_id")
            if not xml_id:
                vals = data["values"]
                if vals.get("id"):
                    data["record"] = self.browse(vals["id"])
                    to_update.append(data)
                elif not update:
                    to_create.append(data)
                else:
                    raise ValidationError(
                        _("Cannot update a record without specifying its id or xml_id")
                    )
                continue
            row = existing.get(xml_id)
            if not row:
                to_create.append(data)
                continue
            d_id, _d_module, _d_name, d_model, d_res_id, d_noupdate, r_id = row
            if self._name != d_model:
                raise ValidationError(  # pylint: disable=missing-gettext
                    f"For external id {xml_id} "
                    f"when trying to create/update a record of model {self._name} "
                    f"found record of different model {d_model} ({d_id})"
                )
            record = self.browse(d_res_id)
            if r_id:
                data["record"] = record
                imd_data_list.append(data)
                if not (update and d_noupdate):
                    to_update.append(data)
            else:
                imd.browse(d_id).unlink()
                to_create.append(data)

        # update existing records
        for data in to_update:
            data["record"]._load_records_write(data["values"])

        # check for records to create with an XMLID from another module
        module = self.env.context.get("install_module")
        if module:
            prefix = module + "."
            for data in to_create:
                if (
                    data.get("xml_id")
                    and not data["xml_id"].startswith(prefix)
                    and not self.env.context.get("foreign_record_to_create")
                ):
                    _logger.warning(
                        "Creating record %s in module %s.",
                        data["xml_id"],
                        module,
                    )

        if self.env.context.get("import_file"):
            existing_modules = (
                self.env["ir.module.module"].sudo().search([]).mapped("name")
            )
            for data in to_create:
                xml_id = data.get("xml_id")
                if xml_id and not data.get("noupdate"):
                    module_name, sep, record_id = xml_id.partition(".")
                    if sep and module_name in existing_modules:
                        raise UserError(
                            _(
                                "The record %(xml_id)s has the module prefix %(module_name)s. This is the part before the '.' in the external id. Because the prefix refers to an existing module, the record would be deleted when the module is upgraded. Use either no prefix and no dot or a prefix that isn't an existing module. For example, __import__, resulting in the external id __import__.%(record_id)s.",
                                xml_id=xml_id,
                                module_name=module_name,
                                record_id=record_id,
                            )
                        )

        # create records
        if to_create:
            records = self._load_records_create([data["values"] for data in to_create])
            for data, record in zip(to_create, records, strict=False):
                data["record"] = record
                if data.get("xml_id"):
                    # add XML ids for parent records that have just been created
                    for parent_model, parent_field in self._inherits.items():
                        if not data["values"].get(parent_field):
                            imd_data_list.append(
                                {
                                    "xml_id": f"{data['xml_id']}_{parent_model.replace('.', '_')}",
                                    "record": record[parent_field],
                                    "noupdate": data.get("noupdate", False),
                                }
                            )
                    imd_data_list.append(data)

        # create or update XMLIDs
        imd._update_xmlids(imd_data_list, update)

        return original_self.concat(*(data["record"] for data in data_list))
