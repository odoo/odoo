from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    private_city_id = fields.Many2one(related='employee_id.private_city_id', readonly=False, groups="hr.group_hr_user")
