# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def display_name_for(self, models):
        """
        Returns the display names from provided models which the current user can access.
        The result is the same whether someone tries to access an inexistent model or a model they cannot access.
        :models list(str): list of technical model names to lookup (e.g. `["res.partner"]`)
        :return: list of dicts of the form `{ "model", "display_name" }` (e.g. `{ "model": "res_partner", "display_name": "Contact"}`)
        """
        # Store accessible models in a temporary list in order to execute only one SQL query
        accessible_models = []
        not_accessible_models = []
        for model in models:
            if self._is_valid_for_model_selector(model):
                accessible_models.append(model)
            else:
                not_accessible_models.append({"display_name": model, "model": model})
        return self._display_name_for(accessible_models) + not_accessible_models

    @api.model
    def _display_name_for(self, models):
        records = self.sudo().search_read([("model", "in", models)], ["name", "model"])
        return [{
            "display_name": model["name"],
            "model": model["model"],
        } for model in records]

    @api.model
    def _is_valid_for_model_selector(self, model):
        model = self.env.get(model)
        return (
            self.env.user._is_internal()
            and model is not None
            and model.has_access("read")
            and not model._transient
            and not model._abstract
        )

    @api.model
    def get_available_models(self):
        """
        Return the list of models the current user has access to, with their
        corresponding display name.
        """
        accessible_models = [model for model in self.pool if self._is_valid_for_model_selector(model)]
        return self._display_name_for(accessible_models)

    def _get_definitions(self, model_names):
        model_definitions = {}
        for model_name in model_names:
            model = self.env[model_name]
            # get fields, relational fields are kept only if the related model is in model_names
            fields_data_by_fname = {
                fname: field_data
                for fname, field_data in model.fields_get(
                    attributes={
                        'definition_record_field', 'definition_record', 'aggregator',
                        'name', 'readonly', 'related', 'relation', 'required', 'searchable',
                        'selection', 'sortable', 'store', 'string', 'tracking', 'type',
                    },
                ).items()
                if field_data.get('selectable', True) and (
                    not field_data.get('relation') or field_data['relation'] in model_names
                )
            }
            fields_data_by_fname = {
                fname: field_data
                for fname, field_data in fields_data_by_fname.items()
                if not field_data.get('related') or field_data['related'].split('.')[0] in fields_data_by_fname
            }
            for fname, field_data in fields_data_by_fname.items():
                if fname in model._fields:
                    inverse_fields = [
                        field for field in model.pool.field_inverses[model._fields[fname]]
                        if field.model_name in model_names
                    ]
                    if inverse_fields:
                        field_data['inverse_fname_by_model_name'] = {field.model_name: field.name for field in inverse_fields}
                    if field_data['type'] == 'many2one_reference':
                        field_data['model_name_ref_fname'] = model._fields[fname].model_field
            model_definitions[model_name] = {
                'description': model._description,
                'fields': fields_data_by_fname,
                'inherit': [model_name for model_name in model._inherit_module if model_name in model_names],
                'order': model._order,
                'parent_name': model._parent_name,
                'rec_name': model._rec_name,
            }
        return model_definitions
