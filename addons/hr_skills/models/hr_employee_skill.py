# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import fields, models

# DONE
class HrEmployeeSkill(models.Model):
    _name = 'hr.employee.skill'
    _inherit = 'hr.individual.skill.mixin'
    _description = "Skill level for employee"
    _order = "skill_type_id, skill_level_id"
    _rec_name = "skill_id"

    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='cascade')

    def _linked_field_name(self):
        return 'employee_id'

    def get_current_skills_by_employee(self):
        emp_skill_grouped = dict(self.grouped(lambda emp_skill: (emp_skill.employee_id, emp_skill.skill_id)))
        result_dict = defaultdict(lambda: self.env['hr.employee.skill'])
        for (employee, skill), emp_skills in emp_skill_grouped.items():
            filtered_emp_skill = emp_skills.filtered(
                lambda employee_skill: not employee_skill.valid_to or employee_skill.valid_to >= fields.Date.today()
            )
            if skill.skill_type_id.is_certification and not filtered_emp_skill:
                expired_skills = (emp_skills - filtered_emp_skill)
                expired_skills_group_by_valid_to = expired_skills.grouped('valid_to')
                max_valid_to = max(expired_skills.mapped('valid_to'))
                result_dict[employee.id] += expired_skills_group_by_valid_to[max_valid_to]
                continue
            result_dict[employee.id] += filtered_emp_skill
        return result_dict

    def open_hr_employee_skill_modal(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.skill',
            'res_id': self.id if self else False,
            'target': 'new',
            'context': {
                'show_employee': True,
                'default_skill_type_id': self.env['hr.skill.type'].search([('is_certification', '=', True)], limit=1).id
            },
            'views': [(self.env.ref('hr_skills.employee_skill_view_inherit_certificate_form').id, 'form')],
        }

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}
