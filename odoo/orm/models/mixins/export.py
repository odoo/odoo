import collections
import logging
import typing
from collections import defaultdict
from typing import Self

from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import groupby, unique
from odoo.tools.translate import _

from ..._recordset import is_recordset
from ...fields.temporal import Datetime
from ...parsing import fix_import_export_id_paths
from ._model_stubs import _ModelStubs

_logger = logging.getLogger("odoo.models")
_debug = DebugLog(__name__)


if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from datetime import datetime


class ExportMixin(_ModelStubs):
    __slots__ = ()

    def _get_or_create_xml_ids(
        self, skip: bool = False
    ) -> Iterator[tuple[Self, str | None]]:
        if skip:
            return ((record, None) for record in self)

        if not self:
            return iter([])

        if not self._is_an_ordinary_table():
            raise UserError(
                self.env._(
                    "You can not export the column ID of model %(model)s, because the"
                    " table %(table)s is not an ordinary table.",
                    model=self._name,
                    table=self._table,
                )
            )

        xids = self.env.registry.xmlids.get_or_create_for_records(self, "__export__")
        _debug.pipeline(
            "export.xmlids_resolved",
            model=self._name,
            records=len(self),
            xmlids=len(xids),
        )
        return ((record, xids[record.id]) for record in self)

    def _export_get_cell_value(self, record, name, cache_properties):
        if "." in name:
            fname, prop_name = name.split(".")
            field = record._fields[fname]
            field_type, cache_value = cache_properties[field].get(
                prop_name, ("char", None)
            )
            value = cache_value.get(record.id, "") if cache_value else ""
        else:
            field = record._fields[name]
            field_type = field.type
            value = record[name]
        return field, field_type, value

    @staticmethod
    def _export_convert_cell(field, field_type, value, record):
        if field.is_properties and field_type == "datetime" and value:
            # a property is stored as the client stores it, in UTC; export it
            # in the user's timezone exactly like a datetime column, so the
            # sheet reads the same and re-imports through the same converter
            utc = typing.cast("datetime", Datetime.to_datetime(value))
            localized = Datetime.context_timestamp(record, utc)
            return Datetime.to_datetime(Datetime.to_string(localized))
        return field.convert_to_export(value, record)

    def _export_get_many2many_cell(self, value, fields2, index_fallback):
        index = None
        subfield = None
        for candidate in (".id", "id", "name", "display_name"):
            target = (candidate,)
            index = next(
                (pos for pos, f2 in enumerate(fields2) if tuple(f2) == target),
                None,
            )
            if index is not None:
                subfield = candidate
                break
        if index is None:
            index = index_fallback

        if subfield == "id":
            text = ",".join(xid for _, xid in value._get_or_create_xml_ids())
        elif subfield == ".id":
            text = ",".join(str(rec_id) for rec_id in value.ids)
        else:
            text = ",".join(value.mapped("display_name")) if value else ""
        return index, text

    def _export_rows(
        self, fields: Sequence[Sequence[str]], *, _is_toplevel_call: bool = True
    ) -> list[list]:
        import_compatible = self.env.context.get("import_compat", True)
        lines = []

        if not _is_toplevel_call:
            cache_properties = self.env.cr.cache["export_properties_cache"]
        else:
            cache_properties = self.env.cr.cache["export_properties_cache"] = (
                defaultdict(dict)
            )
            self._export_prefetch_fields(self, fields, cache_properties)

        for record in self:
            current: list[typing.Any] = [""] * len(fields)
            lines.append(current)

            primary_done = set()

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
                    field, field_type, value = self._export_get_cell_value(
                        record, name, cache_properties
                    )

                    if not is_recordset(value):
                        current[i] = self._export_convert_cell(
                            field, field_type, value, record
                        )

                    elif import_compatible and field_type == "reference":
                        current[i] = f"{value._name},{value.id}"

                    else:
                        primary_done.add(name)
                        fields2 = [
                            (p[1:] or ["display_name"] if p and p[0] == name else [])
                            for p in fields
                        ]

                        if import_compatible and field_type == "many2many":
                            index, text = self._export_get_many2many_cell(
                                value, fields2, i
                            )
                            current[index] = text
                            continue

                        lines2 = value._export_rows(fields2, _is_toplevel_call=False)
                        if lines2:
                            for j, val in enumerate(lines2[0]):
                                if val or isinstance(val, (int, float)):
                                    current[j] = val
                            lines += lines2[1:]
                        else:
                            current[i] = ""

        if _is_toplevel_call and any(f[-1] == "id" for f in fields):
            self._update_export_xids(lines, fields)

        if _is_toplevel_call:
            self.env.cr.cache.pop("export_properties_cache", None)
            _debug.pipeline(
                "export.rows",
                model=self._name,
                records=len(self),
                fields=len(fields),
                rows=len(lines),
                import_compatible=import_compatible,
            )

        return lines

    def _export_update_properties_cache(
        self, records, fnames_by_path, fname, cache_properties
    ):
        cache_properties_field = cache_properties[records._fields[fname]]

        for row in records.read([fname]):
            properties = row[fname]
            if not properties:
                continue
            rec_id = row["id"]

            for prop in properties:
                current_prop_name = prop["name"]
                if f"{fname}.{current_prop_name}" not in fnames_by_path:
                    continue
                property_type = prop["type"]
                if current_prop_name not in cache_properties_field:
                    cache_properties_field[current_prop_name] = [property_type, {}]

                __, cache_by_id = cache_properties_field[current_prop_name]
                if rec_id in cache_by_id:
                    continue

                value = prop.get("value")
                if property_type in ("many2one", "many2many"):
                    if not isinstance(value, list):
                        value = [value] if value else []
                    value = self.env[prop["comodel"]].browse([val[0] for val in value])
                elif property_type == "tags" and value:
                    value = ",".join(
                        next(
                            iter(tag[1] for tag in prop["tags"] if tag[0] == v),
                            "",
                        )
                        for v in value
                    )
                elif property_type == "selection":
                    value = dict(prop["selection"]).get(value, "")
                cache_by_id[rec_id] = value

    def _export_prefetch_fields(self, records, field_paths, cache_properties):
        if not records:
            return

        fnames_by_path = dict(
            groupby(
                [path for path in field_paths if path and path[0] not in ("id", ".id")],
                lambda path: path[0],
            )
        )

        fnames = list(unique(fname.split(".")[0] for fname in fnames_by_path))
        _debug.pipeline(
            "export.prefetch",
            model=records._name,
            records=len(records),
            fields=len(fnames),
            paths=len(fnames_by_path),
        )
        records.fetch(fnames)
        for fname in fnames:
            field = records._fields[fname]
            if field.is_properties:
                self._export_update_properties_cache(
                    records, fnames_by_path, fname, cache_properties
                )

        for fname, paths in fnames_by_path.items():
            if "." in fname:
                fname, prop_name = fname.split(".")
                field = records._fields[fname]
                if not (field.is_properties and prop_name):
                    raise ValueError(
                        f"export expected a properties subfield, got {field!r}.{prop_name!r}"
                    )

                property_type, property_cache = cache_properties[field].get(
                    prop_name, ("char", None)
                )
                if property_type not in ("many2one", "many2many") or not property_cache:
                    continue
                model = next(iter(property_cache.values())).browse()
                subrecords = model.union(
                    *[
                        property_cache[rec_id]
                        for rec_id in records.ids
                        if rec_id in property_cache
                    ]
                )
            else:
                field = records._fields[fname]
                if not field.relational:
                    continue
                subrecords = records[fname]

            paths = [path[1:] or ["display_name"] for path in paths]
            self._export_prefetch_fields(subrecords, paths, cache_properties)

    def _update_export_xids(self, lines, fields):
        bymodels = collections.defaultdict(set)
        xidmap = collections.defaultdict(list)
        for i, line in enumerate(lines):
            for j, cell in enumerate(line):
                if isinstance(cell, tuple):
                    bymodels[cell[0]].add(cell[1])
                    xidmap[cell].append((i, j))
        _debug.perf.count(
            "export.xids_to_resolve",
            model=self._name,
            models=len(bymodels),
            cells=len(xidmap),
            rows=len(lines),
        )
        for model, ids in bymodels.items():
            for record, xid in self.env[model].browse(ids)._get_or_create_xml_ids():
                for i, j in xidmap.pop((record._name, record.id)):
                    lines[i][j] = xid
        if xidmap:
            raise RuntimeError(
                "failed to export xids for "
                + ", ".join(f"{k}:{v}" for k, v in xidmap.items())
            )

    def export_data(self, fields_to_export: list[str]) -> dict[str, list]:
        if not (
            self.env.is_admin() or self.env.user.has_group("base.group_allow_export")
        ):
            _debug.logic(
                "export.denied",
                model=self._name,
                uid=self.env.uid,
                records=len(self),
            )
            raise UserError(
                _(
                    "You don't have the rights to export data. Please contact an Administrator."
                )
            )
        field_paths = [fix_import_export_id_paths(f) for f in fields_to_export]
        with _debug.perf(
            "export.data",
            cr=self.env.cr,
            model=self._name,
            records=len(self),
            fields=len(field_paths),
        ) as span:
            rows = self._export_rows(field_paths)
            span.set(rows=len(rows))
        return {"datas": rows}
