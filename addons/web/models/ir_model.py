from typing import Any

from odoo import api, models


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def display_name_for(self, model_names: list[str]) -> list[dict[str, str]]:
        """Return the display names for the given models accessible by the current user.

        The result is the same whether someone tries to access an inexistent
        model or a model they cannot access.

        :param list[str] model_names: technical model names (e.g. ``["res.partner"]``)
        :return: list of dicts ``{"model": ..., "display_name": ...}``
        """
        accessible = []
        not_accessible = []
        for name in model_names:
            if self._is_valid_for_model_selector(name):
                accessible.append(name)
            else:
                not_accessible.append({"display_name": name, "model": name})
        return self._display_name_for(accessible) + not_accessible

    @api.model
    def _display_name_for(self, model_names: list[str]) -> list[dict[str, str]]:
        records = self.sudo().search_read(
            [("model", "in", model_names)], ["name", "model"]
        )
        return [
            {
                "display_name": model["name"],
                "model": model["model"],
            }
            for model in records
        ]

    @api.model
    def _is_valid_for_model_selector(self, model: str) -> bool:
        model = self.env.get(model)
        return (
            self.env.user._is_internal()
            and model is not None
            and model.has_access("read")
            and not model._transient
            and not model._abstract
        )

    @api.model
    def get_available_models(self) -> list[dict[str, str]]:
        """
        Return the list of models the current user has access to, with their
        corresponding display name.
        """
        accessible_models = [
            model for model in self.pool if self._is_valid_for_model_selector(model)
        ]
        return self._display_name_for(accessible_models)

    def _get_definitions(self, model_names: list[str]) -> dict[str, dict[str, Any]]:
        model_definitions = {}
        for model_name in model_names:
            model = self.env.get(model_name)
            if model is None:
                continue
            # get fields, relational fields are kept only if the related model is in model_names
            fields_data_by_fname = {
                fname: field_data
                for fname, field_data in model.fields_get(
                    attributes={
                        "definition_record_field",
                        "definition_record",
                        "aggregator",
                        "name",
                        "readonly",
                        "related",
                        "relation",
                        "required",
                        "searchable",
                        "selection",
                        "sortable",
                        "store",
                        "string",
                        "tracking",
                        "type",
                    },
                ).items()
                if (
                    not field_data.get("relation")
                    or field_data["relation"] in model_names
                )
            }
            fields_data_by_fname = {
                fname: field_data
                for fname, field_data in fields_data_by_fname.items()
                if not field_data.get("related")
                or field_data["related"].split(".")[0] in fields_data_by_fname
            }
            for fname, field_data in fields_data_by_fname.items():
                if fname in model._fields:
                    inverse_fields = [
                        field
                        for field in model.pool.field_inverses[model._fields[fname]]
                        if field.model_name in model_names
                        and model.env[field.model_name]._has_field_access(field, "read")
                    ]
                    if inverse_fields:
                        field_data["inverse_fname_by_model_name"] = {
                            field.model_name: field.name for field in inverse_fields
                        }
                    if field_data["type"] == "many2one_reference":
                        field_data["model_name_ref_fname"] = model._fields[
                            fname
                        ].model_field
            model_definitions[model_name] = {
                "description": model._description,
                "fields": fields_data_by_fname,
                "inherit": [
                    parent for parent in model._inherit_module if parent in model_names
                ],
                "order": model._order,
                "parent_name": model._parent_name,
                "rec_name": model._rec_name,
            }
        return model_definitions
