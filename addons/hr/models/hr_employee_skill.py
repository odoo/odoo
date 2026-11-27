# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from urllib.parse import urlsplit

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_date


class HrEmployeeSkill(models.Model):
    _name = 'hr.employee.skill'
    _inherit = 'hr.individual.skill.mixin'
    _description = "Skill level for employee"
    _rec_name = "skill_id"

    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='employee_id.company_id')
    credential_url = fields.Char(string="Credential", help="Link to the online proof of the certification")

    @api.constrains('credential_url')
    def _check_credential_url(self):
        for skill in self:
            if skill.credential_url and self._get_url_scheme(skill.credential_url) not in ('http', 'https'):
                raise ValidationError(self.env._("The credential link must be a web link (http or https)."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_credential_url(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalize_credential_url(vals)
        return super().write(vals)

    @api.model
    def _normalize_credential_url(self, vals):
        if vals.get('credential_url'):
            url = vals['credential_url'].strip()
            vals['credential_url'] = (f'https://{url}' if self._get_url_scheme(url) == '' else url) if url else False

    @api.model
    def _get_url_scheme(self, url):
        try:
            return urlsplit(url).scheme.lower()
        except ValueError:
            # malformed URL, e.g. an unclosed IPv6 bracket
            return None

    def _linked_field_name(self):
        return 'employee_id'

    def _get_passive_fields(self):
        return super()._get_passive_fields() + ['credential_url']

    def _get_chatter_label(self):
        self.ensure_one()
        if not self.is_certification:
            return self.display_name
        return self.env._(
            "%(skill)s (from %(valid_from)s to %(valid_to)s)",
            skill=self.display_name,
            valid_from=format_date(self.env, self.valid_from),
            valid_to=format_date(self.env, self.valid_to) if self.valid_to else self.env._("no end date"),
        )

    def get_current_skills_by_employee(self):
        emp_skill_grouped = dict(self.grouped(lambda emp_skill: (emp_skill.employee_id, emp_skill.skill_id)))
        result_dict = defaultdict(lambda: self.env['hr.employee.skill'])
        today = fields.Date.context_today(self)
        for (employee, skill), emp_skills in emp_skill_grouped.items():
            filtered_emp_skill = emp_skills.filtered(
                lambda employee_skill: not employee_skill.valid_to or employee_skill.valid_to >= today,
            )
            if skill.skill_type_id.is_certification and not filtered_emp_skill:
                expired_skills = (emp_skills - filtered_emp_skill)
                expired_skills_group_by_valid_to = expired_skills.grouped('valid_to')
                max_valid_to = max(expired_skills.mapped('valid_to'))
                result_dict[employee.id] += expired_skills_group_by_valid_to[max_valid_to]
                continue
            result_dict[employee.id] += filtered_emp_skill
        return result_dict

    @api.model
    def get_help_data(self, domain):
        # used by the help view (see `hr_employee_skill_view_help`)
        return {
            'has_certification_skill_type': bool(self.env['hr.skill.type'].search_count([('is_certification', '=', True)], limit=1)),
        }

    def action_open_certification(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Certification'),
            'res_model': 'hr.employee.skill',
            'res_id': self.id if self else False,
            'target': 'new',
            'context': {
                'show_employee': True,
                'default_skill_type_id': self.env['hr.skill.type'].search([('is_certification', '=', True)], limit=1).id
            },
            'views': [(self.env.ref('hr.employee_skill_view_inherit_certificate_form').id, 'form')],
        }

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}
