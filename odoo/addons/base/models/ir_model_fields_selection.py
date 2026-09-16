import logging
from typing import Any, Self

import psycopg
from psycopg.types.json import Json

from odoo import _, api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet

from .ir_model_common import (
    MODULE_UNINSTALL_FLAG,
    mark_modified,
    query_insert,
    query_update,
    selection_xmlid,
    upsert_en,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrModelFieldsSelection(models.Model):
    _name = "ir.model.fields.selection"
    _is_registry_metadata = True
    _order = "sequence, id"
    _description = "Fields Selection"
    _allow_sudo_commands = False

    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        index=True,
        required=True,
        domain=[("ttype", "in", ["selection", "reference"])],
        ondelete="cascade",
    )
    value = fields.Char(required=True)
    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=1000)

    _selection_field_uniq = models.Constraint(
        "UNIQUE (field_id, value)",
        "Selections values must be unique per field",
    )

    def _get_selection_data(self, field_id: int) -> list[tuple[str, str]]:
        self.env.cr.execute(
            """
            SELECT value, name->>'en_US'
            FROM ir_model_fields_selection
            WHERE field_id=%s
            ORDER BY sequence, id
        """,
            (field_id,),
        )
        rows = self.env.cr.fetchall()
        _debug.perf.count("selection_data.loaded", field=field_id, values=len(rows))
        return rows

    def _reflect_selections(self, model_names: list[str]) -> None:
        selection_fields = [
            field
            for model_name in model_names
            for field in self.env[model_name]._fields.values()
            if field.type in ("selection", "reference")
            if isinstance(field.selection, list)
        ]
        if not selection_fields:
            _debug.logic("reflect_selections.skipped", models=len(model_names))
            return
        if invalid_fields := OrderedSet(
            field
            for field in selection_fields
            for selection in field.selection
            for value_label in selection
            if not isinstance(value_label, str)
        ):
            _debug.logic(
                "reflect_selections.rejected",
                fields=len(invalid_fields),
                reason="non_str_value_label",
            )
            raise ValidationError(
                _(
                    "Fields %s contain a non-str value/label in selection",
                    ", ".join(
                        f"{field.model_name}.{field.name}" for field in invalid_fields
                    ),
                )
            )

        IMF = self.env["ir.model.fields"]
        expected = {
            (field_id, value): (label, index)
            for field in selection_fields
            for field_id in [IMF._get_ids_by_name(field.model_name)[field.name]]
            for index, (value, label) in enumerate(field.selection)
        }

        cr = self.env.cr
        query = """
            SELECT s.field_id, s.value, s.name->>'en_US', s.sequence
            FROM ir_model_fields_selection s, ir_model_fields f
            WHERE s.field_id = f.id AND f.model = ANY(%s)
        """
        cr.execute(query, [list(model_names)])
        existing = {row[:2]: row[2:] for row in cr.fetchall()}

        cols = ["field_id", "value", "name", "sequence"]
        rows = [key + val for key, val in expected.items() if existing.get(key) != val]
        _debug.pipeline(
            "reflect_selections",
            models=len(model_names),
            fields=len(selection_fields),
            expected=len(expected),
            existing=len(existing),
            changed=len(rows),
        )
        if rows:
            with _debug.perf(
                "reflect_selections.upsert", cr=self.env.cr, rows=len(rows)
            ):
                ids = upsert_en(self, cols, rows, ["field_id", "value"])
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        module = self.env.context.get("module")
        if not module:
            _debug.logic("reflect_selections.no_xmlids", reason="no_module_in_context")
            return

        query = """
            SELECT f.model, f.name, s.value, s.id
            FROM ir_model_fields_selection s, ir_model_fields f
            WHERE s.field_id = f.id AND f.model = ANY(%s)
        """
        cr.execute(query, [list(model_names)])
        selection_ids = {row[:3]: row[3] for row in cr.fetchall()}

        data_list = []
        for field in selection_fields:
            model = self.env[field.model_name]
            for value, modules in field._get_selection_modules(model).items():
                for m in modules:
                    xml_id = selection_xmlid(m, field.model_name, field.name, value)
                    record = self.browse(
                        selection_ids[field.model_name, field.name, value]
                    )
                    data_list.append({"xml_id": xml_id, "record": record})
        _debug.pipeline(
            "reflect_selections_xmlids", module=module, xmlids=len(data_list)
        )
        self.env["ir.model.data"]._update_xmlids(data_list)

    def _update_selection(
        self, model_name: str, field_name: str, selection: list[tuple[str, str]]
    ) -> None:
        field_id = self.env["ir.model.fields"]._get_ids_by_name(model_name)[field_name]

        cur_rows = self._get_existing_selection_data(model_name, field_name)
        new_rows = {
            value: {"value": value, "name": label, "sequence": index}
            for index, (value, label) in enumerate(selection)
        }

        rows_to_insert = []
        rows_to_update = []
        rows_to_remove = []
        for value in new_rows.keys() | cur_rows.keys():
            new_row, cur_row = new_rows.get(value), cur_rows.get(value)
            if new_row is None:
                if self.pool.ready:
                    _logger.warning(
                        "Removing selection value %s on %s.%s",
                        cur_row["value"],
                        model_name,
                        field_name,
                    )
                    rows_to_remove.append(cur_row["id"])
            elif cur_row is None:
                new_row["name"] = Json({"en_US": new_row["name"]})
                rows_to_insert.append(dict(new_row, field_id=field_id))
            elif any(new_row[key] != cur_row[key] for key in new_row):
                new_row["name"] = Json({"en_US": new_row["name"]})
                rows_to_update.append(dict(new_row, id=cur_row["id"]))

        _debug.lifecycle(
            "update_selection",
            model=model_name,
            field=field_name,
            inserted=len(rows_to_insert),
            updated=len(rows_to_update),
            removed=len(rows_to_remove),
        )
        if rows_to_insert:
            query_insert(self.env.cr, self._table, rows_to_insert)

        for row in rows_to_update:
            query_update(self.env.cr, self._table, row, ["id"])

        if rows_to_remove:
            self.browse(rows_to_remove).unlink()

    def _get_existing_selection_data(
        self, model_name: str, field_name: str
    ) -> dict[str, dict[str, Any]]:
        query = """
            SELECT s.*, s.name->>'en_US' AS name
            FROM ir_model_fields_selection s
            JOIN ir_model_fields f ON s.field_id=f.id
            WHERE f.model=%s and f.name=%s
        """
        self.env.cr.execute(query, [model_name, field_name])
        return {row["value"]: row for row in self.env.cr.dictfetchall()}

    def _prepare_base_field_error(self) -> UserError:
        return UserError(
            _(
                "Properties of base fields cannot be altered in this manner! "
                "Please modify them through Python code, "
                "preferably through a custom addon!"
            )
        )

    def _check_base_field_mutation(self, fields_: Any) -> None:
        if any(field.state != "manual" for field in fields_):
            _debug.logic("mutation.rejected", fields=len(fields_), reason="base_field")
            raise self._prepare_base_field_error()

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        field_ids = {vals["field_id"] for vals in vals_list}
        fields_ = self.env["ir.model.fields"].browse(field_ids)
        self._check_base_field_mutation(fields_)
        field_names = {(field.model, field.name) for field in fields_}
        recs = super().create(vals_list)

        model_names = OrderedSet()
        for model, name in field_names:
            if model in self.pool and name in self.pool[model]._fields:
                model_names.add(model)
            else:
                _logger.debug(
                    "Skipped registry setup for selection on %s.%s: "
                    "field not in registry",
                    model,
                    name,
                )
                _debug.logic(
                    "create.setup_skipped",
                    model=model,
                    field=name,
                    reason="field_not_in_registry",
                )
        _debug.lifecycle("create", count=len(recs), setup_models=list(model_names))
        if model_names:
            self.env.flush_all()
            with _debug.perf("registry_setup_after_create", cr=self.env.cr):
                self.pool.setup_models(self.env.cr, model_names)

        return recs

    def _is_jsonb_stored(self, field) -> bool:
        return bool(field.company_dependent)

    def _is_reference(self, field) -> bool:
        return field.ttype == "reference"

    def _prepare_stored_value_match(self, field, stored: SQL, value: str) -> SQL:
        if self._is_reference(field):
            return SQL("split_part(%s, ',', 1) = %s", stored, value)
        return SQL("%s = %s", stored, value)

    def _prepare_renamed_stored_value(
        self, field, stored: SQL, old_value: str, new_value: str
    ) -> SQL:
        if self._is_reference(field):
            return SQL("%s || substr(%s, %s)", new_value, stored, len(old_value) + 1)
        return SQL("%s", new_value)

    def _rename_stored_values(self, field, old_value: str, new_value: str) -> None:
        model = self.env[field.model]
        fname = field.name
        column = SQL.identifier(fname)
        model.invalidate_model([fname])
        _debug.logic(
            "rename_stored_values.strategy",
            model=field.model,
            field=fname,
            jsonb=self._is_jsonb_stored(field),
            reference=self._is_reference(field),
        )
        if self._is_jsonb_stored(field):
            stored = SQL("(e.value #>> '{}')")
            query = SQL(
                "UPDATE %s AS t SET %s = ("
                " SELECT jsonb_object_agg(e.key,"
                " CASE WHEN jsonb_typeof(e.value) = 'string' AND %s"
                " THEN to_jsonb(%s::text) ELSE e.value END)"
                " FROM jsonb_each(t.%s) AS e"
                ") WHERE jsonb_typeof(t.%s) = 'object' AND EXISTS ("
                " SELECT 1 FROM jsonb_each(t.%s) AS e"
                " WHERE jsonb_typeof(e.value) = 'string' AND %s"
                ")",
                SQL.identifier(model._table),
                column,
                self._prepare_stored_value_match(field, stored, old_value),
                self._prepare_renamed_stored_value(field, stored, old_value, new_value),
                column,
                column,
                column,
                self._prepare_stored_value_match(field, stored, old_value),
            )
        else:
            query = SQL(
                "UPDATE %s SET %s = %s WHERE %s",
                SQL.identifier(model._table),
                column,
                self._prepare_renamed_stored_value(field, column, old_value, new_value),
                self._prepare_stored_value_match(field, column, old_value),
            )
        with _debug.perf(
            "rename_stored_values.query", cr=self.env.cr, table=model._table
        ) as span:
            self.env.cr.execute(query)
            span.set(rows=self.env.cr.rowcount)

    def write(self, vals: dict[str, Any]) -> bool:
        if not self:
            return True

        if not all(self._fields[fname].translate for fname in vals):
            self._check_base_field_mutation(self.field_id)

        if "value" in vals:
            if len(self) > len(self.field_id):
                _debug.logic(
                    "write.rejected",
                    count=len(self),
                    fields=len(self.field_id),
                    reason="duplicate_value_per_field",
                )
                raise UserError(
                    _(
                        "Cannot set the same value on several selection options "
                        "of one field; selection values must be unique per field."
                    )
                )
            for selection in self:
                if selection.value == vals["value"]:
                    continue
                if selection.field_id.store:
                    _debug.lifecycle(
                        "rename_stored_values",
                        field=f"{selection.field_id.model}.{selection.field_id.name}",
                        old=selection.value,
                        new=vals["value"],
                    )
                    self._rename_stored_values(
                        selection.field_id, selection.value, vals["value"]
                    )
        old_values = {selection.id: selection.value for selection in self}
        _debug.lifecycle("write", count=len(self), fields=list(vals))

        result = super().write(vals)

        self.env.flush_all()
        if {"value", "sequence", "field_id"} & vals.keys():
            model_names = self.field_id.model_id.mapped("model")
            with _debug.perf(
                "registry_setup_after_write", cr=self.env.cr, models=model_names
            ):
                self.pool.setup_models(self.env.cr, model_names)
        elif "name" in vals:
            _debug.logic("write.cache_cleared", reason="label_only")
            self.env.registry.clear_cache("stable")

        if "value" in vals:
            self._rename_defaults(old_values)

        return result

    def _rename_defaults(self, old_values: dict[int, str]) -> None:
        IrDefault = self.env["ir.default"]
        for selection in self:
            if old_values[selection.id] != selection.value:
                _debug.pipeline(
                    "rename_defaults",
                    model=selection.field_id.model,
                    field=selection.field_id.name,
                )
                IrDefault.rename_value(
                    selection.field_id.model,
                    selection.field_id.name,
                    old_values[selection.id],
                    selection.value,
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_base_field(self) -> None:
        if self.pool.ready:
            self._check_base_field_mutation(self.field_id)

    def unlink(self) -> bool:
        model_names = self.field_id.model_id.mapped("model")
        uninstalling = self.env.context.get(MODULE_UNINSTALL_FLAG)
        _debug.lifecycle(
            "unlink",
            count=len(self),
            models=model_names,
            uninstalling=bool(uninstalling),
        )
        self._process_ondelete()
        if not uninstalling:
            self._discard_defaults()
        result = super().unlink()

        if not uninstalling:
            self.env.flush_all()
            with _debug.perf(
                "registry_setup_after_unlink", cr=self.env.cr, models=model_names
            ):
                self.pool.setup_models(self.env.cr, model_names)

        return result

    def _discard_defaults(self) -> None:
        IrDefault = self.env["ir.default"]
        for field_record, selections in self.grouped("field_id").items():
            if field_record.model in self.env:
                _debug.pipeline(
                    "discard_defaults",
                    model=field_record.model,
                    field=field_record.name,
                    values=len(selections),
                )
                IrDefault.discard_values(
                    field_record.model, field_record.name, selections.mapped("value")
                )

    def _process_ondelete(self) -> None:

        def safe_write(records: Any, fname: str, value: Any) -> None:
            if not records:
                return
            try:
                with self.env.cr.savepoint():
                    records.write({fname: value})
            except (UserError, psycopg.Error) as error:
                _logger.warning(
                    "Could not fulfill ondelete action for field %s.%s (%s); "
                    "attempting ORM bypass",
                    records._name,
                    fname,
                    error,
                )
                _debug.logic("ondelete_orm_bypass", model=records._name, field=fname)
                self.env.execute_query(
                    SQL(
                        "UPDATE %s SET %s = %s WHERE id = ANY(%s)",
                        SQL.identifier(records._table),
                        SQL.identifier(fname),
                        self._bypass_assignment(records, field, value),
                        list(records._ids),
                    )
                )
                records.invalidate_recordset([fname])

        for field_record, selections in self.grouped("field_id").items():
            Model = self.env.get(field_record.model)
            if Model is None:
                _debug.logic(
                    "ondelete.skipped",
                    model=field_record.model,
                    field=field_record.name,
                    reason="model_not_in_registry",
                )
                continue
            field = Model._fields.get(field_record.name)
            if not field or not field.store or not Model._auto:
                _debug.logic(
                    "ondelete.skipped",
                    model=field_record.model,
                    field=field_record.name,
                    reason="not_stored",
                )
                continue

            if field.type not in ("selection", "reference"):
                _debug.logic(
                    "ondelete.skipped",
                    model=field_record.model,
                    field=field_record.name,
                    reason="not_selection",
                )
                continue

            policies = {}
            for selection in selections:
                ondelete = (field.ondelete or {}).get(selection.value)
                if ondelete is None and field.manual and not field.required:
                    ondelete = "set null"
                if ondelete is not None:
                    policies[selection.value] = ondelete
            if not policies:
                continue
            _debug.logic("ondelete", field=field_record.name, policies=policies)

            companies = (
                self._get_companies_with_stored_value(Model, field)
                if field_record.company_dependent
                else self.env.company
            )
            for company in companies:
                company_model = Model.with_company(company.id)
                records_by_value = self._get_records_by_value(
                    company_model, field, list(policies)
                )
                for value, ondelete in policies.items():
                    records = records_by_value.get(value, company_model.browse())
                    _debug.logic(
                        "ondelete.applied",
                        model=Model._name,
                        field=field.name,
                        company=company.id,
                        policy=ondelete if isinstance(ondelete, str) else "callable",
                        records=len(records),
                    )
                    if callable(ondelete):
                        ondelete(records)
                    elif ondelete == "set null":
                        safe_write(records, field.name, False)
                    elif ondelete == "set default":
                        default = field.convert_to_write(
                            field.default(company_model), company_model
                        )
                        safe_write(records, field.name, default)
                    elif ondelete.startswith("set "):
                        safe_write(records, field.name, ondelete.removeprefix("set "))
                    elif ondelete == "cascade":
                        records.unlink()
                    else:
                        raise ValueError(
                            f'The ondelete policy "{ondelete}" is not valid for '
                            f'field "{field_record.model}.{field.name}"'
                        )

    def _bypass_assignment(self, records: Any, field: Any, value: Any) -> SQL:
        column = SQL.identifier(field.name)
        if not self._is_jsonb_stored(field):
            return SQL("%s", field.convert_to_column_insert(value, records))

        company_key = str(records.env.company.id)
        if not value:
            return SQL("%s - %s", column, company_key)
        return SQL(
            "jsonb_set(COALESCE(%s, '{}'::jsonb), ARRAY[%s], to_jsonb(%s::text))",
            column,
            company_key,
            value,
        )

    def _get_companies_with_stored_value(self, model: Any, field: Any) -> Any:
        model.flush_model([field.name])
        rows = self.env.execute_query(
            SQL(
                "SELECT DISTINCT jsonb_object_keys(%s) FROM %s"
                " WHERE jsonb_typeof(%s) = 'object'",
                SQL.identifier(field.name),
                SQL.identifier(model._table),
                SQL.identifier(field.name),
            )
        )
        return (
            self.env["res.company"]
            .browse(int(key) for (key,) in rows if key.isdigit())
            .exists()
        )

    def _get_records_by_value(
        self, company_model: Any, field: Any, values: list
    ) -> dict:
        fname = field.name
        company_model.flush_model([fname])
        if self._is_jsonb_stored(field):
            stored = SQL(
                "%s ->> %s", SQL.identifier(fname), str(company_model.env.company.id)
            )
        else:
            stored = SQL.identifier(fname)
        if field.type == "reference":
            stored = SQL("split_part(%s, ',', 1)", stored)
        query = SQL(
            "SELECT %s AS value, array_agg(id) AS ids FROM %s "
            "WHERE %s = ANY(%s) GROUP BY 1",
            stored,
            SQL.identifier(company_model._table),
            stored,
            values,
        )
        self.env.cr.execute(query)
        by_value = {
            value: company_model.browse(ids) for value, ids in self.env.cr.fetchall()
        }
        _debug.perf.count(
            "records_by_value.fetched",
            model=company_model._name,
            field=fname,
            values=len(values),
            matched=len(by_value),
        )
        return by_value
