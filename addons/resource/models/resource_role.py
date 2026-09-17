from odoo import fields, models


class ResourceRole(models.Model):
    _name = "resource.role"
    _inherit = ["mixin.color"]
    _description = "Resource Role"
    _order = "sequence, name, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    color = fields.Integer(default=lambda self: self._default_color())
    sequence = fields.Integer(export_string_translation=False)

    resource_ids = fields.Many2many(
        comodel_name="resource.resource",
        relation="resource_resource_role_rel",
        column1="role_id",
        column2="resource_resource_id",
        string="Resources",
    )

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", record.name))
            for record, vals in zip(self, vals_list, strict=True)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )
