# Part of Odoo. See LICENSE file for full copyright and licensing terms.

"""HTTP controllers for data export (CSV and XLSX).

Writer classes and grouped-export data structures live in
``export_writers.py``; this module provides the route controllers.
"""

import csv
import io
import itertools
import logging
import operator
import typing
from collections import defaultdict
from typing import Any

from werkzeug.exceptions import InternalServerError

from odoo import http
from odoo.exceptions import UserError
from odoo.http import Response, content_disposition, request
from odoo.libs.filesystem import osutil
from odoo.libs.json import dumps as json_dumps
from odoo.libs.json import loads as json_loads

from .export_writers import (
    ExportXlsxWriter,
    GroupExportXlsxWriter,
    GroupsTreeNode,
)

try:
    from odoo_rust import csv_export as _rust_csv_export

    _RUST_CSV = True
except ImportError:
    _RUST_CSV = False


_logger = logging.getLogger(__name__)


class Export(http.Controller):
    @http.route("/web/export/formats", type="jsonrpc", auth="user", readonly=True)
    def formats(self) -> list[dict[str, Any]]:
        """Return all valid export formats.

        :returns: for each export format, a pair of identifier and printable name
        :rtype: list[dict]
        """
        try:
            import xlsxwriter  # noqa: F401

            xlsx_error = None
        except ModuleNotFoundError:
            xlsx_error = "XlsxWriter 0.9.3 required"
        return [
            {"tag": "xlsx", "label": "XLSX", "error": xlsx_error},
            {"tag": "csv", "label": "CSV"},
        ]

    def _get_property_fields(
        self,
        fields: dict[str, dict[str, Any]],
        model: str,
        domain: list = (),
    ) -> dict[str, dict[str, Any]]:
        """Return property fields existing for the *domain*."""
        property_fields = {}
        Model = request.env[model]
        for fname, field in fields.items():
            if field.get("type") != "properties":
                continue

            definition_record = field["definition_record"]
            definition_record_field = field["definition_record_field"]

            # sudo(): user may lack access to property definition model
            target_model = Model.env[
                Model._fields[definition_record].comodel_name
            ].sudo()
            domain_definition = [(definition_record_field, "!=", False)]
            # Depends of the records selected to avoid showing useless Properties
            if domain:
                self_subquery = Model.with_context(active_test=False)._search(domain)
                field_to_get = Model._field_to_sql(
                    Model._table, definition_record, self_subquery
                )
                domain_definition.append(
                    ("id", "in", self_subquery.subselect(field_to_get))
                )

            definition_records = target_model.search_fetch(
                domain_definition,
                [definition_record_field, "display_name"],
                order="id",  # Avoid complex order
            )

            for record in definition_records:
                for definition in record[definition_record_field]:
                    if definition["type"] == "separator" or (
                        definition["type"] in ("many2one", "many2many")
                        and definition.get("comodel") not in Model.env
                    ):
                        continue
                    id_field = f"{fname}.{definition['name']}"
                    property_fields[id_field] = {
                        "type": definition["type"],
                        "string": Model.env._(
                            "%(property_string)s (%(parent_name)s)",
                            property_string=definition["string"],
                            parent_name=record.display_name,
                        ),
                        "default_export_compatible": field["default_export_compatible"],
                    }
                    if definition["type"] in ("many2one", "many2many"):
                        property_fields[id_field]["relation"] = definition["comodel"]

        return property_fields

    @http.route("/web/export/get_fields", type="jsonrpc", auth="user", readonly=True)
    def get_fields(
        self,
        model: str,
        domain: list,
        prefix: str = "",
        parent_name: str = "",
        import_compat: bool = True,
        parent_field_type: str | None = None,
        parent_field: dict[str, Any] | None = None,
        exclude: list[str] | None = None,
    ) -> list[dict[str, Any]]:

        Model = request.env[model]
        fields = Model.fields_get(
            attributes=[
                "type",
                "string",
                "required",
                "relation_field",
                "default_export_compatible",
                "relation",
                "definition_record",
                "definition_record_field",
                "exportable",
                "readonly",
            ],
        )

        if import_compat:
            if parent_field_type in ["many2one", "many2many"]:
                rec_name = Model._rec_name_fallback()
                fields = {"id": fields["id"], rec_name: fields[rec_name]}
        else:
            fields[".id"] = {**fields["id"]}

        fields["id"]["string"] = request.env._("External ID")

        if not Model._is_an_ordinary_table():
            fields.pop("id", None)
        elif parent_field:
            parent_field["string"] = request.env._("External ID")
            fields["id"] = parent_field
            fields["id"]["type"] = parent_field["field_type"]

        exportable_fields = {}
        for field_name, field in fields.items():
            if import_compat and field_name != "id":
                if exclude and field_name in exclude:
                    continue
                if field.get("readonly"):
                    continue
            if not field.get("exportable", True):
                continue
            exportable_fields[field_name] = field

        exportable_fields.update(
            self._get_property_fields(fields, model, domain=domain)
        )

        fields_sequence = sorted(
            exportable_fields.items(),
            key=lambda field: field[1]["string"].lower(),
        )

        result = []
        for field_name, field in fields_sequence:
            ident = prefix + ("/" if prefix else "") + field_name
            val = ident
            if (
                field_name == "name"
                and import_compat
                and parent_field_type in ["many2one", "many2many"]
            ):
                # Add name field when expand m2o and m2m fields in import-compatible mode
                val = prefix
            name = parent_name + ((parent_name and "/") or "") + field["string"]
            field_dict = {
                "id": ident,
                "string": name,
                "value": val,
                "children": False,
                "field_type": field.get("type"),
                "required": field.get("required"),
                "relation_field": field.get("relation_field"),
                "default_export": import_compat
                and field.get("default_export_compatible"),
            }
            if len(ident.split("/")) < 3 and "relation" in field:
                field_dict["value"] += "/id"
                field_dict["params"] = {
                    "model": field["relation"],
                    "prefix": ident,
                    "name": name,
                    "parent_field": field,
                }
                field_dict["children"] = True

            result.append(field_dict)

        return result

    @http.route("/web/export/namelist", type="jsonrpc", auth="user", readonly=True)
    def namelist(self, model: str, export_id: int) -> list[dict[str, Any]]:
        export = request.env["ir.exports"].browse([export_id])
        return self.fields_info(model, export.export_fields.mapped("name"))

    def fields_info(self, model: str, export_fields: list[str]) -> list[dict[str, Any]]:
        """Build field info dicts for the given *export_fields*."""
        field_info = []
        fields = request.env[model].fields_get(
            attributes=[
                "type",
                "string",
                "required",
                "relation_field",
                "default_export_compatible",
                "relation",
                "definition_record",
                "definition_record_field",
            ],
        )
        fields.update(self._get_property_fields(fields, model))
        if ".id" in export_fields:
            fields[".id"] = fields.get("id", {"string": "ID"})

        for (base, length), subfields in itertools.groupby(
            sorted(export_fields),
            lambda field: (field.split("/", 1)[0], len(field.split("/", 1))),
        ):
            subfields = list(subfields)
            if length == 2:
                field_info.extend(
                    self.graft_subfields(
                        fields[base]["relation"],
                        base,
                        fields[base]["string"],
                        subfields,
                    ),
                )
            elif base in fields:
                field_dict = fields[base]
                field_info.append(
                    {
                        "id": base,
                        "string": field_dict["string"],
                        "field_type": field_dict["type"],
                    }
                )

        indexes_dict = {fname: i for i, fname in enumerate(export_fields)}
        return sorted(field_info, key=lambda field_dict: indexes_dict[field_dict["id"]])

    def graft_subfields(
        self,
        model: str,
        prefix: str,
        prefix_string: str,
        fields: list[str],
    ) -> typing.Iterator[dict[str, Any]]:
        """Recursively build field info for sub-fields of *prefix*."""
        export_fields = [field.split("/", 1)[1] for field in fields]
        return (
            dict(
                field_info,
                id=f"{prefix}/{field_info['id']}",
                string=f"{prefix_string}/{field_info['string']}",
            )
            for field_info in self.fields_info(model, export_fields)
        )


class ExportFormat:
    @property
    def content_type(self) -> str:
        """Provide the format's content type."""
        raise NotImplementedError

    @property
    def extension(self) -> str:
        raise NotImplementedError

    def filename(self, base: str) -> str:
        """Create a filename *without extension* for the item / format of model *base*."""
        if base not in request.env:
            return base

        model_description = request.env["ir.model"]._get(base).name
        return f"{model_description} ({base})"

    def from_data(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        rows: list[list[Any]],
    ) -> str | bytes:
        """Convert Odoo's export data to the current format's output.

        :params list fields: a list of fields to export
        :params list rows: a list of records to export
        :returns:
        :rtype: bytes
        """
        raise NotImplementedError

    def from_group_data(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        groups: GroupsTreeNode,
    ) -> str | bytes:
        raise NotImplementedError

    def base(self, data: str) -> Response:
        """Core export logic shared by CSV and XLSX controllers."""
        params = json_loads(data)
        model, fields, ids, domain, import_compat = operator.itemgetter(
            "model", "fields", "ids", "domain", "import_compat"
        )(params)

        Model = request.env[model].with_context(
            import_compat=import_compat, **params.get("context", {})
        )
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field["name"] != "id"]

        field_names = [f["name"] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val["label"].strip() for val in fields]

        records = Model.browse(ids) if ids else Model.search(domain)

        groupby = params.get("groupby")
        if not import_compat and groupby:
            export_data = records.export_data([".id"] + field_names).get("datas", [])
            groupby_type = [
                Model._fields[x.split(":", 1)[0].split(".", 1)[0]].type for x in groupby
            ]
            tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
            if ids:
                domain = [("id", "in", ids)]
                SearchModel = Model.with_context(active_test=False)
            else:
                SearchModel = Model
            groups_data = SearchModel.formatted_read_group(
                domain, groupby, ["__count", "id:array_agg"]
            )

            # Build a map from record ID to its export rows
            record_rows = {}
            current_id = None
            for row in export_data:
                if row[0]:  # First column is the record ID
                    current_id = int(row[0])
                    record_rows[current_id] = []
                record_rows[current_id].append(row[1:])

            # To preserve the natural model order, base the data order on the result of `export_data`,
            # which comes from a `Model.search`

            # 1. Map each record ID to its group index
            groups = [group["id:array_agg"] for group in groups_data]
            record_to_group = defaultdict(list)
            for group_index, group_record_ids in enumerate(groups):
                for record_id in group_record_ids:
                    record_to_group[record_id].append(group_index)

            # 2. Iterate on the result of `export_data` and assign each data to its right group
            grouped_rows = [[] for _ in groups]
            for record_id, rows in record_rows.items():
                for group_index in record_to_group[record_id]:
                    grouped_rows[group_index].extend(rows)

            # 3. Insert one leaf per group, providing the group information and its data
            for group_info, group_rows in zip(groups_data, grouped_rows, strict=True):
                tree.insert_leaf(group_info, group_rows)

            response_data = self.from_group_data(fields, columns_headers, tree)
        else:
            export_data = records.export_data(field_names).get("datas", [])
            response_data = self.from_data(fields, columns_headers, export_data)

        _logger.info(
            "User %d exported %d %r records from %s. Fields: %s. %s: %s",
            request.env.user.id,
            len(records.ids),
            records._name,
            request.httprequest.environ["REMOTE_ADDR"],
            ",".join(field_names),
            "IDs sample" if ids else "Domain",
            records.ids[:10] if ids else domain,
        )

        # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(
            response_data,
            headers=[
                (
                    "Content-Disposition",
                    content_disposition(
                        osutil.clean_filename(self.filename(model) + self.extension)
                    ),
                ),
                ("Content-Type", self.content_type),
            ],
        )


class CSVExport(ExportFormat, http.Controller):
    @http.route("/web/export/csv", type="http", auth="user")
    def web_export_csv(self, data: str) -> Response:
        try:
            return self.base(data)
        except Exception as exc:
            _logger.exception("Exception during request handling.")
            payload = json_dumps(
                {
                    "code": 0,
                    "message": "Odoo Server Error",
                    "data": http.serialize_exception(exc),
                }
            )
            raise InternalServerError(payload) from exc

    @property
    def content_type(self) -> str:
        return "text/csv;charset=utf8"

    @property
    def extension(self) -> str:
        return ".csv"

    def from_group_data(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        groups: GroupsTreeNode,
    ) -> str | bytes:
        raise UserError(
            request.env._("Exporting grouped data to csv is not supported.")
        )

    def from_data(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        rows: list[list[Any]],
    ) -> str | bytes:
        if _RUST_CSV:
            return _rust_csv_export(columns_headers, rows)

        fp = io.StringIO()
        writer = csv.writer(fp, quoting=1)

        writer.writerow(columns_headers)

        for data in rows:
            row = []
            for d in data:
                if d is None or d is False:
                    d = ""
                elif isinstance(d, bytes):
                    d = d.decode()
                # Spreadsheet apps tend to detect formulas on leading =, +, - and @
                if isinstance(d, str) and d.startswith(("=", "-", "+", "@")):
                    d = "'" + d

                row.append(d)
            writer.writerow(row)

        return fp.getvalue()


class ExcelExport(ExportFormat, http.Controller):
    @http.route("/web/export/xlsx", type="http", auth="user")
    def web_export_xlsx(self, data: str) -> Response:
        try:
            return self.base(data)
        except Exception as exc:
            _logger.exception("Exception during request handling.")
            payload = json_dumps(
                {
                    "code": 0,
                    "message": "Odoo Server Error",
                    "data": http.serialize_exception(exc),
                }
            )
            raise InternalServerError(payload) from exc

    @property
    def content_type(self) -> str:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @property
    def extension(self) -> str:
        return ".xlsx"

    def from_group_data(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        groups: GroupsTreeNode,
    ) -> bytes:
        with GroupExportXlsxWriter(
            fields, columns_headers, groups.count
        ) as xlsx_writer:
            x, y = 1, 0
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group)

        return xlsx_writer.value

    def from_data(
        self,
        fields: list[dict[str, Any]],
        columns_headers: list[str],
        rows: list[list[Any]],
    ) -> bytes:
        with ExportXlsxWriter(fields, columns_headers, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value
