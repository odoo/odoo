import typing

from odoo.libs.debug_log import DebugLog

from ... import decorators as api
from ...fields.properties import check_property_field_value_name
from ...parsing import parse_field_expr
from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from ...fields.base import Field

_debug = DebugLog(__name__)


class _PropertiesMixin(_ModelStubs):
    __slots__ = ()

    @api.model
    def get_property_definition(self, full_name: str) -> dict:
        self.browse().check_access("read")
        field_name, property_name = parse_field_expr(full_name)
        if property_name is None:
            raise ValueError(f"{full_name!r} does not name a property")
        field = self._fields.get(field_name)
        if not field:
            raise ValueError(f"Invalid field {field_name!r} on model {self._name!r}")
        if not field.is_properties:
            raise ValueError(
                f"Field {field_name!r} on model {self._name!r} is not a "
                f"properties field"
            )
        check_property_field_value_name(property_name)

        definition_record = field.definition_record
        definition_record_field = field.definition_record_field
        if definition_record is None or definition_record_field is None:
            raise ValueError(
                f"Field {field_name!r} on model {self._name!r} declares no "
                f"definition record"
            )

        target_model = self.env[self._fields[definition_record].comodel_name or ""]
        # the first definition record, by id, whose stored definition names
        # the property -- the column as stored, through the column store, not
        # the field's normalised reading, so an invalid comodel written to it
        # still surfaces as the SQL scan surfaced it
        target_model.flush_model([definition_record_field])
        definition: dict = {}
        for _holder_id, stored in self.env.backend.columns.get_column_values(
            target_model, definition_record_field
        ):
            definition = next(
                (
                    entry
                    for entry in stored or ()
                    if isinstance(entry, dict) and entry.get("name") == property_name
                ),
                {},
            )
            if definition:
                break
        _debug.perf.count(
            "properties.definition_read",
            model=self._name,
            field=field_name,
            property=property_name,
            definition_model=target_model._name,
            found=bool(definition),
        )
        return dict(definition)

    def _remove_stale_properties(self) -> None:
        for fname, field in self._fields.items():
            if not field.is_properties:
                continue
            for record in self:
                old_value = record[fname]._values
                if not old_value:
                    continue

                definitions = field._get_properties_definition(record) or ()
                all_names = {definition["name"] for definition in definitions}
                new_values = {
                    name: value
                    for name, value in old_value.items()
                    if name in all_names
                }
                if len(new_values) != len(old_value):
                    _debug.lifecycle(
                        "properties.stale_removed",
                        model=self._name,
                        field=fname,
                        record=record.id,
                        removed=len(old_value) - len(new_values),
                        kept=len(new_values),
                    )
                    record[fname] = new_values

    def _check_properties_definition(
        self, properties_definition: typing.Any, field: Field
    ) -> None:
        pass

    def _get_additional_allowed_keys_properties_definition(self) -> tuple[str, ...]:
        return ()

    def _convert_to_cache_properties_definition(self, value: typing.Any) -> typing.Any:
        return value

    def _convert_to_column_properties_definition(self, value: typing.Any) -> typing.Any:
        return value
