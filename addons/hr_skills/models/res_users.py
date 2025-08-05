# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

# DONE
class ResUsers(models.Model):
    _inherit = 'res.users'

    resume_line_ids = fields.One2many(related='employee_id.resume_line_ids', readonly=False)
    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
    current_employee_skill_ids = fields.One2many('hr.employee.skill', related="employee_id.current_employee_skill_ids", readonly=False)
    certification_ids = fields.One2many('hr.employee.skill', related="employee_id.certification_ids", readonly=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'resume_line_ids',
            'employee_skill_ids',
            'current_employee_skill_ids',
            'certification_ids',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'resume_line_ids',
        ]

    def write(self, vals):
        if 'current_employee_skill_ids' in vals or 'certification_ids' in vals or 'employee_skill_ids' in vals:
            vals['employee_skill_ids'] = vals.pop('current_employee_skill_ids', []) + vals.pop('certification_ids', []) + vals.get('employee_skill_ids', [])

        # Must be called directly on employee_id to prevent SET values in vals from causing unintended behavior
        if 'employee_skill_ids' in vals:
            self.employee_id.write({'employee_skill_ids': vals.pop("employee_skill_ids")})
        res = super().write(vals)
        return res
