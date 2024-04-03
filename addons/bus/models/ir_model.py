# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModel(models.Model):
    _inherit = 'ir.model'

    def _get_model_definitions(self, model_names_to_fetch):
        fields_by_model_names = {}
        for model_name in model_names_to_fetch:
            model = self.env[model_name]
            # get fields, relational fields are kept only if the related model is in model_names_to_fetch
            fields_data_by_fname = {
                fname: field_data
                for fname, field_data in model.fields_get(
                    attributes=['name', 'type', 'relation', 'required', 'readonly', 'selection', 'string']
                ).items()
                if not field_data.get('relation') or field_data['relation'] in model_names_to_fetch
            }
            for fname, field_data in fields_data_by_fname.items():
                if fname in model._fields:
                    inverse_fields = [
                        field for field in model.pool.field_inverses[model._fields[fname]]
                        if field.model_name in model_names_to_fetch
                    ]
                    if inverse_fields:
                        field_data['inverse_fname_by_model_name'] = {field.model_name: field.name for field in inverse_fields}
                    if field_data['type'] == 'many2one_reference':
                        field_data['model_name_ref_fname'] = model._fields[fname].model_field
            fields_by_model_names[model_name] = fields_data_by_fname
        return fields_by_model_names
