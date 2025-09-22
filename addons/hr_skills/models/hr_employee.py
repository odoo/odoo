# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.tools import convert


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    resume_line_ids = fields.One2many('hr.resume.line', 'employee_id', string="Resume lines")
    employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id', string="Skills",
        domain=[('skill_type_id.active', '=', True)])
    current_employee_skill_ids = fields.One2many('hr.employee.skill',
        compute='_compute_current_employee_skill_ids', readonly=False)
    skill_ids = fields.Many2many('hr.skill', compute='_compute_skill_ids', store=True, groups="hr.group_hr_user")
    certification_ids = fields.One2many('hr.employee.skill', compute='_compute_certification_ids', readonly=False)

    @api.depends('employee_skill_ids')
    def _compute_current_employee_skill_ids(self):
        current_employee_skill_by_employee = self.employee_skill_ids.get_current_skills_by_employee()
        for employee in self:
            employee.current_employee_skill_ids = current_employee_skill_by_employee[employee.id]

    @api.depends('employee_skill_ids.skill_id')
    def _compute_skill_ids(self):
        for employee in self:
            employee.skill_ids = employee.employee_skill_ids.skill_id

    @api.depends('employee_skill_ids')
    def _compute_certification_ids(self):
        for employee in self:
            employee.certification_ids = employee.employee_skill_ids.filtered('is_certification')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals_emp_skill = vals.pop('current_employee_skill_ids', [])\
                + vals.pop('certification_ids', []) + vals.get('employee_skill_ids', [])
            vals['employee_skill_ids'] = self.env['hr.employee.skill']._get_transformed_commands(vals_emp_skill, self)
        return super().create(vals_list)

    def write(self, vals):
        if 'current_employee_skill_ids' in vals or 'certification_ids' in vals or 'employee_skill_ids' in vals:
            vals_emp_skill = vals.pop('current_employee_skill_ids', []) + vals.pop('certification_ids', [])\
                + vals.get('employee_skill_ids', [])
            vals['employee_skill_ids'] = self.env['hr.employee.skill']._get_transformed_commands(vals_emp_skill, self)
        return super().write(vals)

    @api.model
    def _add_certification_activity_to_employees(self):
        today = fields.Date.today()
        three_months_later = today + relativedelta(months=3)
        return_val = self.env["mail.activity"]

        jobs_with_certification = self.env["hr.job"].search([("job_skill_ids.is_certification", "=", True)])
        if not jobs_with_certification:
            return return_val

        job_skill_level_mapping = defaultdict(dict)

        for job in jobs_with_certification:
            for cert in job.job_skill_ids.filtered(lambda s: s.is_certification):
                key = (cert.skill_id, cert.skill_level_id)
                summary = f"{cert.skill_id.name}: {cert.skill_level_id.name}"
                job_skill_level_mapping[job][key] = summary

        if not job_skill_level_mapping:
            return return_val

        employee_domain = Domain.AND(
            [
                Domain("job_id", "in", jobs_with_certification.ids),
                Domain.OR(
                    [
                        Domain("user_id", "!=", False),
                        Domain("parent_id.user_id", "!=", False),
                        Domain("job_id.user_id", "!=", False),
                    ],
                ),
            ],
        )
        employees = self.env["hr.employee"].search(employee_domain)
        if not employees:
            return return_val

        emp_skills = self.env["hr.employee.skill"].search(
            Domain.AND(
                [Domain("employee_id", "in", employees.ids), Domain("is_certification", "=", True)],
            ),
        )

        employee_cert_data = defaultdict(dict)
        for es in emp_skills:
            key = (es.skill_id, es.skill_level_id)
            employee_cert_data[es.employee_id][key] = es.valid_to

        existing_activities = self.env["mail.activity"].search(
            Domain.AND(
                [
                    Domain("active", "=", True),
                    Domain("activity_category", "=", "upload_file"),
                    Domain("res_model", "=", "hr.employee"),
                    Domain("res_id", "in", employees.ids),
                ],
            ),
        )
        existing_activity_keys = {(act.res_id, act.summary) for act in existing_activities}

        for employee in employees:
            job_id = employee.job_id
            responsible = employee.user_id or employee.parent_id.user_id or job_id.user_id
            if job_id not in job_skill_level_mapping or not responsible:
                continue

            for skill_level_key, summary in job_skill_level_mapping[job_id].items():
                if (employee.id, summary) in existing_activity_keys:
                    continue

                valid_to_date = employee_cert_data.get(employee, {}).get(skill_level_key)
                if valid_to_date is not None and (valid_to_date is False or valid_to_date > three_months_later):
                    continue

                activity = employee.activity_schedule(
                    act_type_xmlid="hr_skills.mail_activity_data_upload_certification",
                    summary=summary,
                    note="Certification missing or expiring soon",
                    date_deadline=valid_to_date or today,
                    user_id=responsible.id,
                )
                return_val += activity

        return return_val

    def _load_scenario(self):
        super()._load_scenario()
        demo_tag = self.env.ref('hr_skills.employee_resume_line_emp_eg_1', raise_if_not_found=False)
        if demo_tag:
            return
        convert.convert_file(self.env, 'hr', 'data/scenarios/hr_scenario.xml', None, mode='init')
        convert.convert_file(self.env, 'hr_skills', 'data/scenarios/hr_skills_scenario.xml', None, mode='init')

    @api.model
    def get_internal_resume_lines(self, res_id, res_model):
        if not res_id:
            return []
        if res_model == 'res.users':
            res_id = self.env['res.users'].browse(res_id).employee_id.id
        if not self.env['hr.employee.public'].browse(res_id).has_access('read'):
            raise AccessError(self.env._("You cannot access the resume of this employee."))
        res = []
        employee_versions = self.env['hr.employee'].sudo().browse(res_id).version_ids
        interval_date_start = False
        for i in range(len(employee_versions) - 1):
            current_version = employee_versions[i]
            next_version = employee_versions[i + 1]
            current_date_start = max(current_version.date_version, current_version.contract_date_start or date.min)
            current_date_end = min(next_version.date_version + relativedelta(days=-1), current_version.contract_date_end or date.max)
            if not current_version.job_title:
                if interval_date_start:
                    previous_version = employee_versions[i - 1]
                    res.append({
                        'id': previous_version.id,
                        'job_title': previous_version.job_title,
                        'date_start': interval_date_start,
                        'date_end': current_date_start + relativedelta(days=-1),
                    })
                    interval_date_start = False
            elif current_version.job_title != next_version.job_title or current_date_end + relativedelta(days=1) != next_version.date_version:
                res.append({
                    'id': current_version.id,
                    'job_title': current_version.job_title,
                    'date_start': interval_date_start or current_date_start,
                    'date_end': current_date_end,
                })
                interval_date_start = False
            else:
                interval_date_start = interval_date_start or current_date_start

        last_version = employee_versions[-1]
        if last_version.job_title:
            current_date_start = max(last_version.date_version, last_version.contract_date_start or date.min)
            res.append({
                'id': last_version.id,
                'job_title': last_version.job_title,
                'date_start': interval_date_start or current_date_start,
                'date_end': last_version.contract_date_end or False,
            })
        elif interval_date_start:
            previous_version = employee_versions[-2]
            res.append({
                'id': previous_version.id,
                'job_title': previous_version.job_title,
                'date_start': interval_date_start,
                'date_end': current_date_start + relativedelta(days=-1),
            })
        return res[::-1]
