import logging
from typing import Any, Self

from psycopg.types.json import Json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL, OrderedSet
from odoo.orm._typing import ValuesType

from .ir_model import (
    MODULE_UNINSTALL_FLAG,
    mark_modified,
    query_insert,
    query_update,
    selection_xmlid,
    upsert_en,
)

_logger = logging.getLogger(__name__)


class IrModelFieldsSelection(models.Model):
    _name = "ir.model.fields.selection"
    _order = "sequence, id"
    _description = "Fields Selection"
    _allow_sudo_commands = False

    field_id = fields.Many2one(
        "ir.model.fields",
        required=True,
        ondelete="cascade",
        index=True,
        domain=[("ttype", "in", ["selection", "reference"])],
    )
    value = fields.Char(required=True)
    name = fields.Char(translate=True, required=True)
    sequence = fields.Integer(default=1000)

    _selection_field_uniq = models.Constraint(
        "UNIQUE (field_id, value)",
        "Selections values must be unique per field",
    )

    def _get_selection(self, field_id: int) -> list[tuple[str, str]]:
        """Return the given field's selection as a list of pairs (value, string)."""
        self.flush_model(["value", "name", "field_id", "sequence"])
        return self._get_selection_data(field_id)

    def _get_selection_data(self, field_id: int) -> list[tuple[str, str]]:
        # return selection as expected on registry (no translations)
        self.env.cr.execute(
            """
            SELECT value, name->>'en_US'
            FROM ir_model_fields_selection
            WHERE field_id=%s
            ORDER BY sequence, id
        """,
            (field_id,),
        )
        return self.env.cr.fetchall()

    def _reflect_selections(self, model_names: list[str]) -> None:
        """Reflect the selections of the fields of the given models."""
        fields = [
            field
            for model_name in model_names
            for field_name, field in self.env[model_name]._fields.items()
            if field.type in ("selection", "reference")
            if isinstance(field.selection, list)
        ]
        if not fields:
            return
        if invalid_fields := OrderedSet(
            field
            for field in fields
            for selection in field.selection
            for value_label in selection
            if not isinstance(value_label, str)
        ):
            raise ValidationError(
                _(
                    "Fields %s contain a non-str value/label in selection",
                    invalid_fields,
                )
            )

        # determine expected and existing rows
        IMF = self.env["ir.model.fields"]
        expected = {
            (field_id, value): (label, index)
            for field in fields
            for field_id in [IMF._get_ids(field.model_name)[field.name]]
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

        # create or update rows
        cols = ["field_id", "value", "name", "sequence"]
        rows = [key + val for key, val in expected.items() if existing.get(key) != val]
        if rows:
            ids = upsert_en(self, cols, rows, ["field_id", "value"])
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        # update their XML ids
        module = self.env.context.get("module")
        if not module:
            return

        query = """
            SELECT f.model, f.name, s.value, s.id
            FROM ir_model_fields_selection s, ir_model_fields f
            WHERE s.field_id = f.id AND f.model = ANY(%s)
        """
        cr.execute(query, [list(model_names)])
        selection_ids = {row[:3]: row[3] for row in cr.fetchall()}

        data_list = []
        for field in fields:
            model = self.env[field.model_name]
            for value, modules in field._selection_modules(model).items():
                for m in modules:
                    xml_id = selection_xmlid(m, field.model_name, field.name, value)
                    record = self.browse(
                        selection_ids[field.model_name, field.name, value]
                    )
                    data_list.append({"xml_id": xml_id, "record": record})
        self.env["ir.model.data"]._update_xmlids(data_list)

    def _update_selection(
        self, model_name: str, field_name: str, selection: list[tuple[str, str]]
    ) -> dict[str, dict[str, Any]]:
        """Set the selection of a field to the given list, and return the row
        values of the given selection records.
        """
        field_id = self.env["ir.model.fields"]._get_ids(model_name)[field_name]

        # selection rows {value: row}
        cur_rows = self._existing_selection_data(model_name, field_name)
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
                    # removing a selection in the new list, at your own risks
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

        if rows_to_insert:
            row_ids = query_insert(self.env.cr, self._table, rows_to_insert)
            # update cur_rows for output
            for row, row_id in zip(rows_to_insert, row_ids, strict=True):
                cur_rows[row["value"]] = dict(row, id=row_id)

        for row in rows_to_update:
            query_update(self.env.cr, self._table, row, ["id"])

        if rows_to_remove:
            self.browse(rows_to_remove).unlink()

        return cur_rows

    def _existing_selection_data(
        self, model_name: str, field_name: str
    ) -> dict[str, dict[str, Any]]:
        """Return the selection data of the given model, by field and value, as
        a dict {field_name: {value: row_values}}.
        """
        query = """
            SELECT s.*, s.name->>'en_US' AS name
            FROM ir_model_fields_selection s
            JOIN ir_model_fields f ON s.field_id=f.id
            WHERE f.model=%s and f.name=%s
        """
        self.env.cr.execute(query, [model_name, field_name])
        return {row["value"]: row for row in self.env.cr.dictfetchall()}

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        field_ids = {vals["field_id"] for vals in vals_list}
        field_names = set()
        for field in self.env["ir.model.fields"].browse(field_ids):
            field_names.add((field.model, field.name))
            if field.state != "manual":
                raise UserError(
                    _(
                        "Properties of base fields cannot be altered in this manner! "
                        "Please modify them through Python code, "
                        "preferably through a custom addon!"
                    )
                )
        recs = super().create(vals_list)

        model_names = OrderedSet(
            model
            for model, name in field_names
            if model in self.pool and name in self.pool[model]._fields
        )
        if model_names:
            # setup models; this re-initializes model in registry
            self.env.flush_all()
            self.pool._setup_models__(self.env.cr, model_names)

        return recs

    def write(self, vals: dict[str, Any]) -> bool:
        if not self:
            return True

        if not self.env.user._is_admin() and any(
            record.field_id.state != "manual" for record in self
        ):
            raise UserError(
                _(
                    "Properties of base fields cannot be altered in this manner! "
                    "Please modify them through Python code, "
                    "preferably through a custom addon!"
                )
            )

        if "value" in vals:
            for selection in self:
                if selection.value == vals["value"]:
                    continue
                if selection.field_id.store:
                    # in order to keep the cache consistent, flush the
                    # corresponding field, and invalidate it from cache
                    model = self.env[selection.field_id.model]
                    fname = selection.field_id.name
                    model.invalidate_model([fname])
                    # replace the value by the new one in the field's corresponding column
                    query = SQL(
                        "UPDATE %s SET %s = %s WHERE %s = %s",
                        SQL.identifier(model._table),
                        SQL.identifier(fname),
                        vals["value"],
                        SQL.identifier(fname),
                        selection.value,
                    )
                    self.env.cr.execute(query)

        result = super().write(vals)

        # setup models; this re-initializes model in registry
        self.env.flush_all()
        model_names = self.field_id.model_id.mapped("model")
        self.pool._setup_models__(self.env.cr, model_names)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_manual(self) -> None:
        # Prevent manual deletion of module columns
        if self.pool.ready and any(
            selection.field_id.state != "manual" for selection in self
        ):
            raise UserError(
                _(
                    "Properties of base fields cannot be altered in this manner! "
                    "Please modify them through Python code, "
                    "preferably through a custom addon!"
                )
            )

    def unlink(self) -> bool:
        model_names = self.field_id.model_id.mapped("model")
        self._process_ondelete()
        result = super().unlink()

        # Reload registry for normal unlink only. For module uninstall, the
        # reload is done independently in odoo.modules.loading.
        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this re-initializes model in registry
            self.env.flush_all()
            self.pool._setup_models__(self.env.cr, model_names)

        return result

    def _process_ondelete(self) -> None:
        """Process the 'ondelete' of the given selection values."""

        def safe_write(records: Any, fname: str, value: Any) -> None:
            if not records:
                return
            try:
                with self.env.cr.savepoint():
                    records.write({fname: value})
            except Exception:
                # going through the ORM failed, probably because of an exception
                # in an override or possibly a constraint.
                _logger.runbot(
                    "Could not fulfill ondelete action for field %s.%s, attempting ORM bypass...",
                    records._name,
                    fname,
                )
                # if this fails then we're shit out of luck and there's nothing
                # we can do except fix on a case-by-case basis
                self.env.execute_query(
                    SQL(
                        "UPDATE %s SET %s=%s WHERE id = ANY(%s)",
                        SQL.identifier(records._table),
                        SQL.identifier(fname),
                        field.convert_to_column_insert(value, records),
                        list(records._ids),
                    )
                )
                records.invalidate_recordset([fname])

        for selection in self:
            # The field may exist in database but not in registry. In this case
            # we allow the field to be skipped, but for production this should
            # be handled through a migration script. The ORM will take care of
            # the orphaned 'ir.model.fields' down the stack, and will log a
            # warning prompting the developer to write a migration script.
            Model = self.env.get(selection.field_id.model)
            if Model is None:
                continue
            field = Model._fields.get(selection.field_id.name)
            if not field or not field.store or not Model._auto:
                continue

            # Field changed its type, skip it.
            if field.type not in ("selection", "reference"):
                continue

            ondelete = (field.ondelete or {}).get(selection.value)
            # special case for custom fields
            if ondelete is None and field.manual and not field.required:
                ondelete = "set null"

            if ondelete is None:
                # nothing to do, the selection does not come from a field extension
                continue

            companies = (
                self.env.companies
                if selection.field_id.company_dependent
                else [self.env.company]
            )
            for company in companies:
                # make a company-specific env for the Model and selection
                company_model = Model.with_company(company.id)
                company_selection = selection.with_company(company.id)
                if callable(ondelete):
                    ondelete(company_selection._get_records())
                elif ondelete == "set null":
                    safe_write(company_selection._get_records(), field.name, False)
                elif ondelete == "set default":
                    value = field.convert_to_write(
                        field.default(company_model), company_model
                    )
                    safe_write(company_selection._get_records(), field.name, value)
                elif ondelete.startswith("set "):
                    safe_write(
                        company_selection._get_records(),
                        field.name,
                        ondelete.removeprefix("set "),
                    )
                elif ondelete == "cascade":
                    company_selection._get_records().unlink()
                else:
                    # this shouldn't happen... simply a sanity check
                    raise ValueError(
                        _(
                            'The ondelete policy "%(policy)s" is not valid for field "%(field)s"',
                            policy=ondelete,
                            field=selection,
                        )
                    )

    def _get_records(self) -> Any:
        """Return the records having 'self' as a value."""
        self.ensure_one()
        Model = self.env[self.field_id.model]
        Model.flush_model([self.field_id.name])
        if self.field_id.company_dependent:
            # company-dependent fields are stored as jsonb (e.g; {company_id: value})
            query = SQL(
                "SELECT id FROM %s WHERE %s ->> %s = %s",
                SQL.identifier(Model._table),
                SQL.identifier(self.field_id.name),
                str(self.env.company.id),
                self.value,
            )
        else:
            # normal selection fields are stored as general datatype
            query = SQL(
                "SELECT id FROM %s WHERE %s = %s",
                SQL.identifier(Model._table),
                SQL.identifier(self.field_id.name),
                self.value,
            )
        self.env.cr.execute(query)
        return Model.browse(r[0] for r in self.env.cr.fetchall())
