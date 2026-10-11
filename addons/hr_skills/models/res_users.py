from odoo import fields, models

from odoo.addons.hr.models.res_users import related_employee_field


class ResUsers(models.Model):
    _inherit = 'res.users'

    job_id = fields.Many2one('hr.job', **related_employee_field('job_id'))
    skill_ids = fields.Many2many('hr.skill', **related_employee_field('skill_ids'))
