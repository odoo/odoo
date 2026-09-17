import contextlib
import functools
import itertools
import logging
import typing
from collections import defaultdict
from typing import Self

import psycopg

from odoo.db import schema as sql
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.libs.lru import LRU
from odoo.tools.translate import _

from ... import decorators as api
from ..._typing import ValuesType
from ...helpers import get_tuple_itemgetter
from ...parsing import fix_import_export_id_paths
from ._model_stubs import _ModelStubs

_logger = logging.getLogger("odoo.models")
_debug = DebugLog(__name__)


if typing.TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence


type FieldPaths = Sequence[Sequence[str | None]]


class LoadMixin(_ModelStubs):
    __slots__ = ()

    def _load_creatable_models(self, fields: FieldPaths) -> set[str]:
        creatable_models = {self._name}
        for field_path in fields:
            if field_path[0] in (None, "id", ".id"):
                continue
            model_fields = self._fields
            for field_name in field_path:
                if field_name is None or field_name in ("id", ".id"):
                    break

                o2m_field = model_fields.get(field_name)
                if (
                    o2m_field is not None
                    and o2m_field.is_one2many
                    and (comodel := o2m_field.comodel_name)
                ):
                    creatable_models.add(comodel)
                    model_fields = self.env[comodel]._fields
        _debug.logic(
            "load.creatable_models",
            model=self._name,
            fields=len(fields),
            models=len(creatable_models),
        )
        return creatable_models

    def _load_data_list(
        self, data_list: list[dict], update: bool, messages: list, ids: list
    ) -> None:
        global_error_message = None
        try:
            with self.env.cr.savepoint():
                ids.extend(self._load_records(data_list, update).ids)
            _debug.pipeline(
                "load.batch_loaded",
                model=self._name,
                records=len(data_list),
                update=update,
            )
            return
        except psycopg.InternalError as e:
            _debug.logic(
                "load.batch_internal_error",
                model=self._name,
                records=len(data_list),
                error=type(e).__name__,
            )
            if not any(message["type"] == "error" for message in messages):
                messages.append(
                    dict(
                        data_list[0]["info"],
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

        _debug.logic(
            "load.batch_failed_retry_one_by_one",
            model=self._name,
            records=len(data_list),
            update=update,
        )
        errors = self._load_data_list_one_by_one(data_list, update, messages, ids)
        if errors and global_error_message and global_error_message not in messages:
            messages.insert(0, global_error_message)

    def _load_data_list_one_by_one(
        self, data_list: list[dict], update: bool, messages: list, ids: list
    ) -> int:
        cr = self.env.cr
        errors = 0
        for position, rec_data in enumerate(data_list, 1):
            try:
                with cr.savepoint():
                    rec = self._load_records([rec_data], update)
                    cr.flush()
                ids.append(rec.id)
            except Exception as exc:
                message = self._load_record_failure(rec_data, exc)
                messages.append(message)
                if message["type"] == "error":
                    errors += 1
            if errors >= 10 and (errors >= position / 10):
                _debug.logic(
                    "load.interrupted_too_many_errors",
                    model=self._name,
                    position=position,
                    errors=errors,
                )
                messages.append(
                    {
                        "type": "warning",
                        "message": _(
                            "Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors."
                        ),
                    }
                )
                break
        _debug.pipeline(
            "load.one_by_one_done",
            model=self._name,
            records=len(data_list),
            loaded=len(ids),
            errors=errors,
            update=update,
        )
        return errors

    def _load_record_failure(self, rec_data: dict, exc: BaseException) -> dict:
        info = rec_data["info"]
        _debug.logic(
            "load.record_failed",
            model=self._name,
            error=type(exc).__name__,
            pg_error=isinstance(exc, psycopg.Error),
            user_error=isinstance(exc, UserError),
        )
        if isinstance(exc, psycopg.Warning):
            return dict(info, type="warning", message=str(exc))
        if isinstance(exc, psycopg.Error):
            pg_error_info = {"message": self._sql_error_to_message(exc)}
            if exc.diag.table_name == self._table:
                e_fields = sql.get_column_names_in_constraint(
                    self.env.cr, exc.diag, check_catalog=True
                )
                if len(e_fields) == 1:
                    pg_error_info["field"] = e_fields[0]
            return dict(info, type="error", **pg_error_info)
        if isinstance(exc, UserError):
            return dict(info, type="error", message=str(exc))
        _logger.debug("Error while loading record", exc_info=exc)
        return dict(
            info,
            type="error",
            message=_(
                "Unknown error during import: %(error_type)s: %(error_message)s",
                error_type=exc.__class__,
                error_message=exc,
            ),
            moreinfo=_("Resolve other errors first"),
        )

    @api.model
    def load(self, fields: list[str], data: list[list[str]]) -> dict:
        mode = self.env.context.get("mode", "init")
        current_module = self.env.context.get("module", "__import__")
        noupdate = self.env.context.get("noupdate", False)
        self = self.with_context(_import_current_module=current_module)

        cr = self.env.cr

        field_paths = [fix_import_export_id_paths(f) for f in fields]

        ids: list[int] = []
        failed = False
        messages: list[dict] = []

        batch: list[tuple] = []
        batch_xml_ids: set[str] = set()
        if invalid := self._get_invalid_load_paths(field_paths):
            _debug.logic("load.invalid_paths", model=self._name, paths=len(invalid))
            return {"ids": False, "messages": invalid, "nextrow": 0}

        creatable_models = self._load_creatable_models(field_paths)

        batch_tokens: dict[str, set] = defaultdict(set)

        def flush(*, xml_id=None, model=None, name=None) -> bool:
            if not batch:
                return False

            if xml_id and model:
                raise ValueError(
                    "flush can specify *either* an external id or a model, not both"
                )

            if xml_id and xml_id not in batch_xml_ids:
                return False
            if model and model not in creatable_models:
                return False
            if name is not None and name not in batch_tokens.get(model, ()):
                # the batch holds no record this name could resolve to, so
                # the reference is settled by storage alone and the batch
                # stays whole; flushing here split an import into one create
                # per distinct name
                return False

            data_list = [
                {"xml_id": xid, "values": vals, "info": info, "noupdate": noupdate}
                for xid, vals, info in batch
            ]
            batch.clear()
            batch_xml_ids.clear()
            batch_tokens.clear()
            self._load_data_list(data_list, mode == "update", messages, ids)
            return True

        flush_recordset = self.with_context(import_flush=flush, import_cache=LRU(65536))

        limit = self.env.context.get("_import_limit")
        if limit is None:
            limit = float("inf")

        savepoint = cr.savepoint()
        try:
            extracted = flush_recordset._extract_records(
                field_paths, data, log=messages.append, limit=limit
            )
            converted = flush_recordset._convert_records(extracted, log=messages.append)
            info = self._collect_load_batch(
                converted, current_module, batch, batch_xml_ids, batch_tokens
            )
            flush()
            if any(message["type"] == "error" for message in messages):
                _debug.logic("load.rolled_back", model=self._name, errors=len(messages))
                savepoint.rollback()
                failed = True
                self.pool.reset_changes()
        except Exception:
            savepoint.close(rollback=True)
            raise
        savepoint.close(rollback=False)
        _debug.pipeline(
            "load.end",
            model=self._name,
            mode=mode,
            module=current_module,
            rows=len(data),
            ids=len(ids),
            failed=failed,
            messages=len(messages),
        )

        nextrow = info["rows"]["to"] + 1
        if nextrow < limit:
            nextrow = 0
        return {
            "ids": False if failed else ids,
            "messages": messages,
            "nextrow": nextrow,
        }

    @api.model
    def _get_invalid_load_paths(self, field_paths: FieldPaths) -> list[dict]:
        messages = []
        for field_path in field_paths:
            if not field_path or field_path[0] in (None, "id", ".id"):
                continue
            model = self
            for index, field_name in enumerate(field_path[:-1]):
                if field_name is None or field_name in ("id", ".id"):
                    break
                field = model._fields.get(field_name)
                if field is None:
                    break
                if not field.relational:
                    messages.append(
                        {
                            "type": "error",
                            "rows": {"from": 0, "to": 0},
                            "record": 0,
                            "field": field_path[0],
                            "field_path": list(field_path),
                            "message": _(
                                "Column %(path)s cannot be imported: %(field)s is not a "
                                "relation on model %(model)s, so it has no sub-fields.",
                                path="/".join(map(str, field_path)),
                                field="/".join(map(str, field_path[: index + 1])),
                                model=model._name,
                            ),
                        }
                    )
                    break
                model = self.env[field.comodel_name]
        return messages

    def _collect_load_batch(
        self,
        converted,
        current_module: str,
        batch: list,
        batch_xml_ids: set,
        batch_tokens: dict[str, set],
    ) -> dict:
        info = {"rows": {"to": -1}}
        for dbid, xid, record, info in converted:
            if record is None:
                continue
            if xid:
                xid = xid if "." in xid else f"{current_module}.{xid}"
                batch_xml_ids.add(xid)
            elif dbid:
                record["id"] = dbid
            batch.append((xid, record, info))
            self._collect_pending_tokens(record, batch_tokens)
        return info

    def _collect_pending_tokens(self, vals: dict, tokens: dict[str, set]) -> None:
        # every text a name reference could resolve to once this batch is
        # created. A rec-name field is often computed (res.partner searches
        # complete_name, which is not in vals), so every string value of the
        # pending record counts, not only the searchable fields; a reference
        # equal to a value that only exists after compute is the one shape
        # this cannot see, and it costs a lost "multiple matches" warning,
        # never a wrong link
        for fname, value in vals.items():
            field = self._fields.get(fname)
            if field is None:
                continue
            if isinstance(value, str):
                tokens[self._name].add(value)
            elif field.is_x2many and isinstance(value, list):
                comodel = self.env[field.comodel_name]
                for command in value:
                    if (
                        isinstance(command, (list, tuple))
                        and len(command) == 3
                        and isinstance(command[2], dict)
                    ):
                        comodel._collect_pending_tokens(command[2], tokens)

    def _get_o2m_only_row_predicate(
        self, field_paths: FieldPaths
    ) -> Callable[[list[str]], bool]:
        fields = self._fields

        def is_o2m(fnames) -> bool:
            fname0 = fnames[0]
            return (
                fname0 is not None and fname0 in fields and fields[fname0].is_one2many
            )

        get_o2m_values = get_tuple_itemgetter(
            [index for index, fnames in enumerate(field_paths) if is_o2m(fnames)]
        )
        get_other_values = get_tuple_itemgetter(
            [index for index, fnames in enumerate(field_paths) if not is_o2m(fnames)]
        )

        def is_only_o2m_row(row) -> bool:
            return any(get_o2m_values(row)) and not any(get_other_values(row))

        return is_only_o2m_row

    def _extract_property_definitions(
        self, field_paths: FieldPaths
    ) -> tuple[dict, dict[str, list[str]]]:
        fields = self._fields
        property_definitions: dict = {}
        property_columns: dict[str, list[str]] = defaultdict(list)
        for fname, *__ in field_paths:
            if not fname:
                continue
            f_prop_name, sep, property_name = fname.partition(".")
            if not sep:
                continue
            if f_prop_name not in fields or not fields[f_prop_name].is_properties:
                continue

            definition = self.get_property_definition(fname)
            if not definition:
                raise ValueError(
                    f"Property {property_name!r} doesn't have any definition on {fname!r} field"
                )

            property_definitions[fname] = definition
            property_columns[f_prop_name].append(fname)
        return property_definitions, property_columns

    def _extract_relational_values(
        self,
        relfield: str,
        field_paths: FieldPaths,
        record_span: list[list[str]],
        property_definitions: dict,
        log: Callable,
    ) -> list[dict]:
        if relfield not in property_definitions:
            comodel = self.env[self._fields[relfield].comodel_name]
        else:
            comodel = self.env[property_definitions[relfield]["comodel"]]

        indices, subfields = zip(
            *(
                (position, fnames[1:] or [None])
                for position, fnames in enumerate(field_paths)
                if fnames[0] == relfield
            ),
            strict=False,
        )
        relfield_data = [
            it for it in map(get_tuple_itemgetter(indices), record_span) if any(it)
        ]
        return [
            subrecord
            for subrecord, _subinfo in comodel._extract_records(
                subfields, relfield_data, log=log
            )
        ]

    @staticmethod
    def _collapse_property_columns(
        record: dict, property_columns: dict[str, list[str]], property_definitions: dict
    ) -> None:
        for properties_fname, property_indexes_names in property_columns.items():
            record[properties_fname] = [
                dict(
                    **property_definitions[property_name],
                    value=record.pop(property_name),
                )
                for property_name in property_indexes_names
            ]

    def _extract_records(
        self,
        field_paths: FieldPaths,
        data: list[list[str]],
        log: Callable = lambda a: None,
        limit: float = float("inf"),
    ) -> Generator[tuple[dict, dict]]:
        fields = self._fields
        is_only_o2m_row = self._get_o2m_only_row_predicate(field_paths)

        property_definitions, property_columns = self._extract_property_definitions(
            field_paths
        )

        relational_fnames = {fname for fname in fields if fields[fname].relational} | {
            fname
            for fname, defn in property_definitions.items()
            if defn.get("type") in ("many2one", "many2many")
        }

        def is_relational(fname):
            return fname in relational_fnames

        _debug.pipeline(
            "load.extract",
            model=self._name,
            fields=len(field_paths),
            rows=len(data),
            properties=len(property_definitions),
            relational=len(relational_fnames),
        )
        index = 0
        while index < len(data) and index < limit:
            row = data[index]

            record: dict[typing.Any, typing.Any] = {
                fnames[0]: value
                for fnames, value in zip(field_paths, row, strict=False)
                if not is_relational(fnames[0])
            }

            following = itertools.takewhile(
                is_only_o2m_row,
                (data[j] for j in range(index + 1, len(data))),
            )
            record_span = list(itertools.chain([row], following))

            for relfield, *__ in field_paths:
                if relfield is None or not is_relational(relfield):
                    continue

                record[relfield] = self._extract_relational_values(
                    relfield, field_paths, record_span, property_definitions, log
                )

            self._collapse_property_columns(
                record, property_columns, property_definitions
            )

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
    ) -> Generator[tuple[int | bool, str | bool, dict, dict]]:
        field_names = {name: field.string for name, field in self._fields.items()}
        if self.env.lang:
            field_names.update(
                self.env.registry.metaschema.field_strings(self.env, self._name)
            )

        converter = self.env["ir.fields.converter"]
        convert = converter._get_converter_record(self)

        def _log(base, record, field, exception):
            type = "warning" if isinstance(exception, Warning) else "error"
            field_name = field_names.get(field, field)
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
                info["field_name"] = field_name
                record.update(info)
            log(record)

        stream = list(records)
        converter._prefetch_name_references(
            self, [record for record, _extras in stream]
        )
        wanted_ids = set()
        for record, _extras in stream:
            if record.get(".id"):
                with contextlib.suppress(ValueError):
                    wanted_ids.add(int(record[".id"]))
        known_ids = (
            set(self.search([("id", "in", sorted(wanted_ids))])._ids)
            if wanted_ids
            else frozenset()
        )
        _debug.pipeline(
            "load.convert",
            model=self._name,
            records=len(stream),
            db_ids=len(wanted_ids),
            known=len(known_ids),
            lang=bool(self.env.lang),
        )

        for stream_index, (record, extras) in enumerate(stream):
            xid = record.get("id", False)
            dbid: typing.Any = False
            if record.get(".id"):
                try:
                    dbid = int(record[".id"])
                except ValueError:
                    dbid = record[".id"]
                if dbid not in known_ids:
                    _debug.logic(
                        "load.unknown_db_id",
                        model=self._name,
                        record=stream_index,
                        dbid=dbid,
                    )
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
        self.check_singleton()
        to_write = {}
        for fname in list(values):
            if fname not in self._fields or not self._fields[fname].is_properties:
                continue
            field_converter = self._fields[fname].convert_to_cache
            to_write[fname] = dict(
                self[fname]._values or {},
                **field_converter(values.pop(fname), self, validate=False),
            )

        self.write(values)
        if to_write:
            _debug.logic(
                "load.properties_merged",
                model=self._name,
                record=self.id,
                fields=len(to_write),
            )
            self.write(to_write)
            self._remove_stale_properties()

    def _load_records_create(self, vals_list: list[ValuesType]) -> Self:
        records = self.create(vals_list)
        if any(field.is_properties for field in self._fields.values()):
            records._remove_stale_properties()
        return records

    def _load_records(self, data_list: list[dict], update: bool = False) -> Self:
        original_self = self.browse()

        xmlids = self.env.registry.xmlids

        xml_ids = [data["xml_id"] for data in data_list if data.get("xml_id")]
        existing = {
            f"{row[1]}.{row[2]}": row for row in xmlids.resolve(self.env, xml_ids, self)
        }

        to_create = []
        to_update = []
        imd_data_list = []

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
                raise ValidationError(
                    _(
                        "For external id %(xml_id)s when trying to create/update a "
                        "record of model %(model)s found record of different model "
                        "%(found_model)s (%(found_id)s)",
                        xml_id=xml_id,
                        model=self._name,
                        found_model=d_model,
                        found_id=d_id,
                    )
                )
            record = self.browse(d_res_id)
            if r_id:
                data["record"] = record
                imd_data_list.append(data)
                if not (update and d_noupdate):
                    to_update.append(data)
            else:
                xmlids.remove(self.env, [d_id])
                to_create.append(data)

        _debug.pipeline(
            "load.records_partitioned",
            model=self._name,
            records=len(data_list),
            xml_ids=len(xml_ids),
            existing=len(existing),
            to_create=len(to_create),
            to_update=len(to_update),
            update=update,
        )
        for data in to_update:
            data["record"]._load_records_write(data["values"])

        self._load_records_warn_foreign_module(to_create)
        self._load_records_check_import_prefix(to_create)

        if to_create:
            self._load_records_create_batch(to_create, imd_data_list)

        _debug.lifecycle(
            "load.xmlids_updated",
            model=self._name,
            xmlids=len(imd_data_list),
            update=update,
        )
        xmlids.update(self.env, imd_data_list, update)

        return original_self.concat(*(data["record"] for data in data_list))

    def _load_records_create_batch(
        self, to_create: list[dict], imd_data_list: list[dict]
    ) -> None:
        records = self._load_records_create([data["values"] for data in to_create])
        _debug.lifecycle(
            "load.records_created",
            model=self._name,
            records=len(records),
            inherits=len(self._inherits),
        )
        for data, created in zip(to_create, records, strict=True):
            data["record"] = created
            if data.get("xml_id"):
                for parent_model, parent_field in self._inherits.items():
                    if not data["values"].get(parent_field):
                        imd_data_list.append(
                            {
                                "xml_id": f"{data['xml_id']}_{parent_model.replace('.', '_')}",
                                "record": created[parent_field],
                                "noupdate": data.get("noupdate", False),
                            }
                        )
                imd_data_list.append(data)

    def _load_records_warn_foreign_module(self, to_create: list[dict]) -> None:
        module = self.env.context.get("install_module")
        if not module:
            return
        prefix = module + "."
        for data in to_create:
            if (
                data.get("xml_id")
                and not data["xml_id"].startswith(prefix)
                and not self.env.context.get("foreign_record_to_create")
            ):
                _logger.warning(
                    "Creating record %s in module %s.", data["xml_id"], module
                )
                _debug.logic(
                    "load.foreign_record_created",
                    model=self._name,
                    module=module,
                    xml_id=data["xml_id"],
                )

    def _load_records_check_import_prefix(self, to_create: list[dict]) -> None:
        if not self.env.context.get("import_file"):
            return
        dotted = [
            data["xml_id"]
            for data in to_create
            if data.get("xml_id") and not data.get("noupdate") and "." in data["xml_id"]
        ]
        if not dotted:
            return
        existing_modules = self.env.registry.metaschema.module_names(self.env)
        _debug.logic(
            "load.import_prefix_checked",
            model=self._name,
            dotted=len(dotted),
            modules=len(existing_modules),
        )
        for xml_id in dotted:
            module_name, _sep, record_id = xml_id.partition(".")
            if module_name in existing_modules:
                raise UserError(
                    _(
                        "The record %(xml_id)s has the module prefix %(module_name)s. This is the part before the '.' in the external id. Because the prefix refers to an existing module, the record would be deleted when the module is upgraded. Use either no prefix and no dot or a prefix that isn't an existing module. For example, __import__, resulting in the external id __import__.%(record_id)s.",
                        xml_id=xml_id,
                        module_name=module_name,
                        record_id=record_id,
                    )
                )
