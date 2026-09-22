from typing import Any

from odoo.api import NewId
from odoo.fields import Command
from odoo.models import BaseModel
from odoo.tools.authority_keys import strip_authority_keys


class RecordSnapshot(dict):
    __slots__ = ["fields_spec", "record"]
    __hash__ = None  # type: ignore[assignment]  # unhashable: overrides __eq__

    def __init__(
        self, record: BaseModel, fields_spec: dict, update_all: bool = True
    ) -> None:
        super().__init__()
        self.record = record
        self.fields_spec = fields_spec
        if update_all:
            for name in fields_spec:
                self.update_field(name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RecordSnapshot):
            return NotImplemented
        return self.record == other.record and super().__eq__(other)

    def update_field(self, field_name: str) -> None:
        if self.record._fields[field_name].type in ("one2many", "many2many"):
            lines = self.record[field_name]
            if "context" in self.fields_spec[field_name]:
                lines = lines.with_context(
                    **strip_authority_keys(
                        self.fields_spec[field_name]["context"], door="onchange"
                    )
                )
            sub_fields_spec = self.fields_spec[field_name].get("fields") or {}
            self[field_name] = {
                line.id: RecordSnapshot(line, sub_fields_spec) for line in lines
            }
        else:
            self[field_name] = self.record[field_name]

    def has_changed(self, field_name) -> bool:
        if field_name not in self:
            return True
        if self.record._fields[field_name].type not in (
            "one2many",
            "many2many",
        ):
            return self[field_name] != self.record[field_name]
        return self[field_name].keys() != set(self.record[field_name]._ids) or any(
            line_snapshot.has_changed(subname)
            for line_snapshot in self[field_name].values()
            for subname in self.fields_spec[field_name].get("fields") or {}
        )

    def diff(self, other: RecordSnapshot, force: bool = False) -> dict[str, Any]:
        simple_fields_spec = {}
        x2many_fields_spec = {}
        for field_name, field_spec in self.fields_spec.items():
            if field_name == "id":
                continue
            if not force and other.get(field_name) == self[field_name]:
                continue
            field = self.record._fields[field_name]
            if field.type in ("one2many", "many2many"):
                x2many_fields_spec[field_name] = field_spec
            else:
                simple_fields_spec[field_name] = field_spec

        [result] = self.record.web_read(simple_fields_spec)

        result.pop("id")

        for field_name, field_spec in x2many_fields_spec.items():
            commands = []

            self_value = self[field_name]
            other_value = {} if force else other.get(field_name) or {}
            if other_value:
                first_key = next(iter(other_value))
                if not isinstance(first_key, NewId):
                    other_value = {
                        NewId(id_): snap for id_, snap in other_value.items()
                    }

            field = self.record._fields[field_name]
            remove = Command.delete if field.type == "one2many" else Command.unlink
            commands.extend(
                remove(id_.origin or id_.ref or 0)
                for id_ in other_value
                if id_ not in self_value
            )

            sub_fields_spec = field_spec.get("fields") or {}
            link_origins = self.record[field_name].browse()
            for id_, line_snapshot in self_value.items():
                is_update = not force and id_ in other_value
                if not is_update and id_.origin:
                    link_origins |= line_snapshot.record._origin
            if link_origins:
                link_origins.web_read(sub_fields_spec)

            for id_, line_snapshot in self_value.items():
                if not force and id_ in other_value:
                    line_diff = line_snapshot.diff(other_value[id_])
                    if line_diff:
                        commands.append(
                            Command.update(id_.origin or id_.ref or 0, line_diff)
                        )

                elif not id_.origin:
                    line_diff = line_snapshot.diff({})
                    commands.append(
                        (Command.CREATE, id_.origin or id_.ref or 0, line_diff)
                    )

                else:
                    base_line = line_snapshot.record._origin
                    [base_data] = base_line.web_read(field_spec.get("fields") or {})
                    commands.append((Command.LINK, base_line.id, base_data))

                    base_snapshot = RecordSnapshot(
                        base_line, field_spec.get("fields") or {}
                    )
                    line_diff = line_snapshot.diff(base_snapshot)
                    if line_diff:
                        commands.append(Command.update(id_.origin, line_diff))

            if commands:
                result[field_name] = commands

        return result
