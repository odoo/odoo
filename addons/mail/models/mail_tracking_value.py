import logging
import typing
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal, Self

from odoo import api, fields, models
from odoo.exceptions import MissingError
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from odoo.api import Environment

    from .mail_message import MailMessage
    from odoo.addons.base.models.ir_model_fields import IrModelFields
    from odoo.addons.base.models.res_currency import ResCurrency


_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _tracking_sort_key(
    tracking: MailTrackingValue, fields_sequence_map: dict[str, int]
) -> tuple:
    field_info = tracking.field_info or {}
    field_name = tracking.field_id.name or field_info.get("name", "unknown")
    return (
        fields_sequence_map.get(field_name, 100),
        tracking.field_id.ttype == "properties",
        field_name,
        field_info.get("definition_index", 0),
        -tracking.id,
    )


class MailTrackingValue(models.Model):
    _name = "mail.tracking.value"
    _description = "Mail Tracking Value"
    _rec_name = "field_id"
    _order = "id DESC"

    field_id: IrModelFields = fields.Many2one(
        comodel_name="ir.model.fields",
        index=True,
        readonly=True,
        required=False,
        ondelete="set null",
    )
    field_info = fields.Json(string="Removed field information")

    old_value_integer = fields.Integer(readonly=True)
    old_value_float = fields.Float(readonly=True)
    old_value_char = fields.Char(readonly=True)
    old_value_text = fields.Text(readonly=True)
    old_value_datetime = fields.Datetime(
        string="Old Value DateTime",
        readonly=True,
    )

    new_value_integer = fields.Integer(readonly=True)
    new_value_float = fields.Float(readonly=True)
    new_value_char = fields.Char(readonly=True)
    new_value_text = fields.Text(readonly=True)
    new_value_datetime = fields.Datetime(readonly=True)

    currency_id: ResCurrency = fields.Many2one(
        comodel_name="res.currency",
        readonly=True,
        ondelete="set null",
        help="Used to display the currency when tracking monetary values",
    )

    mail_message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Message ID",
        index=True,
        required=True,
        ondelete="cascade",
    )

    def _filtered_has_field_access(self, env: Environment) -> Self:
        def has_field_access(tracking: MailTrackingValue) -> bool:
            if not tracking.field_id:
                return env.is_system()
            model = env[tracking.field_id.model]
            model_field = model._fields.get(tracking.field_id.name)
            return (
                model._has_field_access(model_field, "read") if model_field else False
            )

        accessible = self.filtered(has_field_access)
        if _debug.logic.enabled and len(accessible) != len(self):
            _debug.logic(
                "tracking_values_hidden",
                asked=len(self),
                hidden=len(self) - len(accessible),
                uid=env.uid,
            )
        return accessible

    def _filtered_free_field_access(self) -> Self:
        def has_free_access(tracking: MailTrackingValue) -> bool:
            if not tracking.field_id:
                return False
            model_field = self.env[tracking.field_id.model]._fields.get(
                tracking.field_id.name
            )
            return model_field and not model_field.groups

        return self.filtered(has_free_access)

    @api.model
    def _prepare_tracking_values(
        self,
        initial_value: Any,
        new_value: Any,
        col_name: str,
        col_info: dict,
        record: models.Model,
    ) -> dict:
        field = self.env["ir.model.fields"]._get(record._name, col_name)
        if not field:
            _debug.logic("tracking_field_unknown", model=record._name, field=col_name)
            raise ValueError(f"Unknown field {col_name} on model {record._name}")

        col_type = col_info["type"]
        if col_type in {"integer", "float", "char", "text", "datetime"}:
            values = {
                f"old_value_{col_type}": initial_value,
                f"new_value_{col_type}": new_value,
            }
        elif col_type == "monetary":
            values = {
                "currency_id": record[col_info["currency_field"]].id,
                "old_value_float": initial_value,
                "new_value_float": new_value,
            }
        elif col_type == "date":
            values = self._prepare_tracking_values_date(initial_value, new_value)
        elif col_type == "boolean":
            values = {
                "old_value_integer": initial_value,
                "new_value_integer": new_value,
            }
        elif col_type == "selection":
            values = self._prepare_tracking_values_selection(
                initial_value, new_value, col_info
            )
        elif col_type == "many2one":
            values = self._prepare_tracking_values_many2one(initial_value, new_value)
        elif col_type in {"one2many", "many2many", "tags"}:
            values = self._prepare_tracking_values_x2many(
                initial_value, new_value, field
            )
        else:
            raise NotImplementedError(
                f"Unsupported tracking on field {field.name} (type {col_type}"
            )

        return {"field_id": field.id, **values}

    def _prepare_tracking_values_date(self, initial_value: Any, new_value: Any) -> dict:
        def as_datetime_string(value: Any) -> str | Literal[False]:
            if not value:
                return False
            return fields.Datetime.to_string(
                datetime.combine(fields.Date.from_string(value), datetime.min.time())
            )

        return {
            "old_value_datetime": as_datetime_string(initial_value),
            "new_value_datetime": as_datetime_string(new_value),
        }

    def _prepare_tracking_values_selection(
        self, initial_value: Any, new_value: Any, col_info: dict
    ) -> dict:
        labels = dict(col_info["selection"])
        return {
            "old_value_char": (
                initial_value and labels.get(initial_value, initial_value)
            )
            or "",
            "new_value_char": (new_value and labels.get(new_value, new_value)) or "",
        }

    def _prepare_tracking_values_many2one(
        self, initial_value: Any, new_value: Any
    ) -> dict:
        def as_id_and_name(value: Any) -> tuple:
            if not value:
                return (0, "")
            if isinstance(value, models.BaseModel):
                return (value.id, self._tracked_display_name(value))
            return value

        old_id, old_name = as_id_and_name(initial_value)
        new_id, new_name = as_id_and_name(new_value)
        return {
            "old_value_integer": old_id,
            "new_value_integer": new_id,
            "old_value_char": old_name,
            "new_value_char": new_name,
        }

    def _prepare_tracking_values_x2many(
        self, initial_value: Any, new_value: Any, field: models.Model
    ) -> dict:
        model_name = self.env["ir.model"]._get(field.relation).display_name

        def as_names(value: Any) -> str:
            if not value:
                return ""
            if isinstance(value, models.BaseModel):
                return ", ".join(
                    self._tracked_display_name(record)
                    or self.env._(
                        "Unnamed %(record_model_name)s (%(record_id)s)",
                        record_model_name=model_name,
                        record_id=record.id,
                    )
                    for record in value
                )
            return ", ".join(item[1] for item in value)

        return {
            "old_value_char": as_names(initial_value),
            "new_value_char": as_names(new_value),
        }

    def _tracked_display_name(self, record: models.BaseModel) -> str:
        try:
            return record.display_name
        except MissingError:
            _logger.warning(
                "Tracked %s record %s no longer exists, tracking it without a name",
                record._name,
                record.id,
            )
            return ""

    def _prepare_tracking_values_property(
        self,
        initial_value: dict,
        col_name: str,
        col_info: dict,
        record: models.Model,
        definition_index: int = 0,
    ) -> dict:
        property_col_info = col_info | {
            "type": initial_value["type"],
            "selection": initial_value.get("selection"),
        }
        if initial_value["type"] == "monetary" and "currency_field" not in col_info:
            property_col_info["currency_field"] = initial_value.get("currency_field")

        field_info = {
            "definition_index": definition_index,
            "desc": f"{property_col_info['string']}: {initial_value['string']}",
            "name": col_name,
            "type": initial_value["type"],
        }
        value = initial_value.get("value", False)
        if value and initial_value["type"] == "tags":
            value = [t for t in initial_value.get("tags", []) if t[0] in value]

        tracking_values = self.env["mail.tracking.value"]._prepare_tracking_values(
            value, False, col_name, property_col_info, record
        )
        return {**tracking_values, "field_info": field_info}

    def _tracking_value_format(self) -> list:
        model_ids = defaultdict(list)
        for tracking in self:
            model = tracking.field_id.model or tracking.mail_message_id.model
            model_ids[model].append(tracking.id)
        formatted = []
        for model, ids in model_ids.items():
            formatted += self.browse(ids)._tracking_value_format_model(model)
        _debug.perf.count(
            "tracking_values_formatted", values=len(self), models=len(model_ids)
        )
        return formatted

    def _tracking_value_format_model(self, model: str | Literal[False]) -> list:
        if not self:
            return []

        if model:
            TrackedModel = self.env[model]
            tracked_fields = TrackedModel.fields_get(
                self.field_id.mapped("name"), attributes={"digits", "string", "type"}
            )
            model_sequence_info = TrackedModel._mail_track_field_sequences(
                tracked_fields
            )
        else:
            tracked_fields, model_sequence_info = {}, {}

        fields_sequence_map = dict(
            {
                tracking.field_info["name"]: tracking.field_info.get("sequence", 100)
                for tracking in self.filtered("field_info")
            },
            **model_sequence_info,
        )
        fields_col_info = (
            (
                tracking.field_id.ttype != "properties"
                and tracked_fields.get(tracking.field_id.name)
            )
            or {
                "string": tracking.field_info["desc"]
                if tracking.field_info
                else self.env._("Unknown"),
                "type": tracking.field_info["type"] if tracking.field_info else "char",
            }
            for tracking in self
        )

        return [
            {
                "id": tracking.id,
                "fieldInfo": {
                    "changedField": col_info["string"],
                    "currencyId": tracking.currency_id.id,
                    "floatPrecision": col_info.get("digits"),
                    "fieldType": col_info["type"],
                    "isPropertyField": tracking.field_id.ttype == "properties",
                },
                "newValue": tracking._format_display_value(col_info["type"], new=True)[
                    0
                ],
                "oldValue": tracking._format_display_value(col_info["type"], new=False)[
                    0
                ],
            }
            for tracking, col_info in sorted(
                zip(self, fields_col_info, strict=False),
                key=lambda pair: _tracking_sort_key(pair[0], fields_sequence_map),
            )
        ]

    def _format_display_value(self, field_type: str, new: bool = True) -> list:
        field_mapping = {
            "boolean": ("old_value_integer", "new_value_integer"),
            "date": ("old_value_datetime", "new_value_datetime"),
            "datetime": ("old_value_datetime", "new_value_datetime"),
            "char": ("old_value_char", "new_value_char"),
            "float": ("old_value_float", "new_value_float"),
            "integer": ("old_value_integer", "new_value_integer"),
            "monetary": ("old_value_float", "new_value_float"),
            "text": ("old_value_text", "new_value_text"),
        }

        result = []
        for record in self:
            value_fname = field_mapping.get(
                field_type, ("old_value_char", "new_value_char")
            )[bool(new)]
            value = record[value_fname]

            if field_type in {"integer", "float", "char", "text", "monetary"}:
                result.append(value)
            elif field_type in {"date", "datetime"}:
                if not record[value_fname]:
                    result.append(value)
                elif field_type == "date":
                    result.append(fields.Date.to_string(value))
                else:
                    result.append(f"{value}Z")
            elif field_type == "boolean":
                result.append(bool(value))
            else:
                result.append(value)
        return result
