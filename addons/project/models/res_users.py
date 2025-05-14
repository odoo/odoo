from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    favorite_project_ids = fields.Many2many('project.project', 'project_favorite_user_rel', 'user_id', 'project_id',
                                            string='Favorite Projects', export_string_translation=False, copy=False)
