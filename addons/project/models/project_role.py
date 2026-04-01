from random import randint

from odoo import fields, models


class ProjectRole(models.Model):
    _name = 'project.role'
    _description = 'Project Role'

    def _get_default_color(self):
        return randint(1, 11)

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=_get_default_color)
    sequence = fields.Integer(export_string_translation=False)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._('%s (copy)', role.name)) for role, vals in zip(self, vals_list)]
