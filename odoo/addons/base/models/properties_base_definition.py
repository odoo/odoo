from typing import Any, Self

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import ormcache

DEFINITION_MEMO_CACHE_KEY = "properties_base_definition_ids"
_debug = DebugLog(__name__)


class PropertiesBaseDefinition(models.Model):
    _name = "properties.base.definition"
    _description = "Properties Base Definition"

    properties_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        required=True,
        ondelete="cascade",
    )
    properties_definition = fields.PropertiesDefinition()

    _unique_properties_field_id = models.Constraint(
        "UNIQUE(properties_field_id)",
        "Only one definition per properties field",
    )

    @api.depends("properties_field_id")
    def _compute_display_name(self) -> None:
        for definition in self:
            if not definition.properties_field_id.model:
                definition.display_name = False
                continue

            definition.display_name = _(
                "%s Properties",
                self.env[definition.properties_field_id.model]._description,
            )

    @api.constrains("properties_field_id")
    def _check_properties_field_id(self) -> None:
        if invalid_fields := self.mapped("properties_field_id").filtered(
            lambda f: f.ttype != "properties"
        ):
            _debug.logic(
                "definition_field_rejected", fields=invalid_fields.mapped("name")
            )
            raise ValidationError(
                _(
                    "The definition needs to be linked to a properties field. Those fields are not: %s.",
                    ", ".join(invalid_fields.mapped("name")),
                )
            )

    def write(self, vals: dict[str, Any]) -> bool:
        if "properties_field_id" in vals:
            _debug.logic("write_field_refused", definitions=self.ids)
            raise AccessError(_("You can not change the field of a base definition"))
        return super().write(vals)

    def unlink(self) -> bool:
        memo = self.env.cr.cache.get(DEFINITION_MEMO_CACHE_KEY) or {}
        stale = [key for key, value in memo.items() if value in self.ids]
        _debug.logic("definition_memo_evicted", entries=len(stale))
        for key in stale:
            del memo[key]
        result = super().unlink()
        self.env.registry.clear_cache("stable")
        _debug.lifecycle("definition_unlinked", definitions=self.ids)
        return result

    def _get_definition_for_property_field(
        self, model_name: str, field_name: str
    ) -> Self:
        return self.browse(
            self._get_or_create_definition_id_for_property_field(model_name, field_name)
        )

    def _get_definition_id_for_property_field(
        self, model_name: str, field_name: str
    ) -> int | None:
        memo = self.env.cr.cache.get(DEFINITION_MEMO_CACHE_KEY)
        if memo and (definition_id := memo.get((model_name, field_name))):
            _debug.logic(
                "definition_resolved", model=model_name, field=field_name, by="memo"
            )
            return definition_id
        try:
            return self._get_definition_id_for_property_field_stored(
                model_name, field_name
            )
        except ValueError:
            _debug.logic(
                "definition_resolved", model=model_name, field=field_name, by="none"
            )
            return None

    def _get_or_create_definition_id_for_property_field(
        self, model_name: str, field_name: str
    ) -> int:
        definition_id = self._get_definition_id_for_property_field(
            model_name, field_name
        )
        if definition_id:
            return definition_id
        _debug.logic(
            "definition_resolved", model=model_name, field=field_name, by="create"
        )

        field_ids = self.env["ir.model.fields"]._get_ids_by_name(model_name)
        field_id = field_ids.get(field_name)
        if not field_id:
            _debug.logic("definition_field_fetched", model=model_name, field=field_name)
            field = self.env["ir.model.fields"].sudo()._get(model_name, field_name)
            field_id = field.id

        definition_record = self.sudo().create({"properties_field_id": field_id})
        _debug.lifecycle(
            "definition_created",
            model=model_name,
            field=field_name,
            definition=definition_record.id,
        )
        memo = self.env.cr.cache.setdefault(DEFINITION_MEMO_CACHE_KEY, {})
        memo[model_name, field_name] = definition_record.id
        return definition_record.id

    @ormcache("model_name", "field_name", cache="stable")
    def _get_definition_id_for_property_field_stored(
        self, model_name: str, field_name: str
    ) -> int:
        field_ids = self.env["ir.model.fields"]._get_ids_by_name(model_name)
        field_id = field_ids.get(field_name)

        if field_id:
            definition = self.sudo().search(
                [("properties_field_id", "=", field_id)], limit=1
            )
            _debug.perf.count(
                "definition_looked_up",
                model=model_name,
                field=field_name,
                found=bool(definition),
            )
            if definition:
                return definition.id

        msg = f"No properties.base.definition for {model_name}.{field_name}"
        raise ValueError(msg)
