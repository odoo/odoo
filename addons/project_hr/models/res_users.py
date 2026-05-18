from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
    job_id = fields.Many2one(store=True, depends=('employee_id.job_id',))
    skill_ids = fields.Many2many(store=True, depends=('employee_id.skill_ids',))
