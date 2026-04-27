# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


def resolve_field(model, field_path):
    """Resolves a field path from a model and return intermediary fields.

    For example, providing the model 'hr.employee' with the field path 'user_id.name' will return
    the fields:
     - `hr.employee.user_id`
     - `res.users.name`

    :param models.Model model: The model on which we begin resolving the path
    :param str field_path: The path of fields
    :return list[odoo.fields.Field] | None: the resolved fields or None if the path is invalid.
    """
    resolved_fields = []
    *field_names, last_field_name = field_path.split(".")
    for field_name in field_names:
        field = model._fields.get(field_name)
        if not field or not getattr(field, "comodel_name", None):
            return  # field path is invalid

        resolved_fields.append(field)
        model = model.env[field.comodel_name]

    if field := model._fields.get(last_field_name):
        resolved_fields.append(field)
        return resolved_fields


class SignItem(models.Model):
    _inherit = "sign.item"

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        for item in res:
            if not self._valid_item_name_field_path(self.env["hr.contract"], item.name or ""):
                item.name = ""

        return res

    def write(self, vals):
        if "name" in vals:
            if not self._valid_item_name_field_path(self.env["hr.contract"], vals["name"] or ""):
                vals["name"] = ""

        return super().write(vals)

    def _valid_item_name_field_path(self, model, field_path):
        fields = resolve_field(model, field_path)
        return fields is None or all(self._valid_item_name_field(field) for field in fields)

    def _valid_item_name_field(self, field):
        model = self.env[field.model_name]
        return field.is_accessible(self.env) and model.has_access("read")
