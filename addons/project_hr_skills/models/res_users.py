from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
