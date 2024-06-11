# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import fields, models, api


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    applicant_skill_ids = fields.One2many('hr.applicant.skill', 'applicant_id', string="Skills")
    skill_ids = fields.Many2many('hr.skill', compute='_compute_skill_ids', store=True)
    is_interviewer = fields.Boolean(compute='_compute_is_interviewer')
    matching_skill_ids = fields.Many2many(comodel_name='hr.skill', string="Matching Skills", compute="_compute_matching_skill_ids")
    missing_skill_ids = fields.Many2many(comodel_name='hr.skill', string="Missing Skills", compute="_compute_matching_skill_ids")
    matching_score = fields.Float(string="Matching Score(%)", compute="_compute_matching_skill_ids")

    @api.depends_context('uid')
    @api.depends('interviewer_ids', 'job_id.interviewer_ids')
    def _compute_is_interviewer(self):
        is_recruiter = self.env.user.has_group('hr_recruitment.group_hr_recruitment_user')
        for applicant in self:
            applicant.is_interviewer = not is_recruiter and self.env.user in (applicant.interviewer_ids | applicant.job_id.interviewer_ids)

    @api.depends('applicant_skill_ids.skill_id')
    def _compute_skill_ids(self):
        for applicant in self:
            applicant.skill_ids = applicant.applicant_skill_ids.skill_id

    @api.depends_context('active_id')
    @api.depends('skill_ids')
    def _compute_matching_skill_ids(self):
        job_id = self.env.context.get('active_id')
        if not job_id:
            self.matching_skill_ids = False
            self.missing_skill_ids = False
            self.matching_score = 0
        else:
            for applicant in self:
                job_skills = self.env['hr.job'].browse(job_id).skill_ids
                applicant.matching_skill_ids = job_skills & applicant.skill_ids
                applicant.missing_skill_ids = job_skills - applicant.skill_ids
                applicant.matching_score = (len(applicant.matching_skill_ids) / len(job_skills)) * 100 if job_skills else 0

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        vals['employee_skill_ids'] = [(0, 0, {
            'skill_id': applicant_skill.skill_id.id,
            'skill_level_id': applicant_skill.skill_level_id.id,
            'skill_type_id': applicant_skill.skill_type_id.id,
        }) for applicant_skill in self.applicant_skill_ids]
        return vals

    def _update_employee_from_applicant(self):
        vals_list = []
        for applicant in self:
            existing_skills = applicant.emp_id.employee_skill_ids.skill_id
            skills_to_create = applicant.applicant_skill_ids.skill_id - existing_skills
            vals_list.extend([{
                'employee_id': applicant.emp_id.id,
                'skill_id': skill.id,
                'skill_level_id': applicant.applicant_skill_ids.filtered(lambda s: s.skill_id == skill).skill_level_id.id,
                'skill_type_id': skill.skill_type_id.id,
            } for skill in skills_to_create])
        self.env['hr.employee.skill'].create(vals_list)
        return super()._update_employee_from_applicant()

    def action_add_to_job(self):
        self.with_context(just_moved=True).write({
            'job_id': self.env['hr.job'].browse(self.env.context.get('active_id')).id,
            'stage_id': self.env.ref('hr_recruitment.stage_job0'),
        })
        action = self.env['ir.actions.actions']._for_xml_id('hr_recruitment.action_hr_job_applications')
        action['context'] = literal_eval(action['context'].replace('active_id', str(self.job_id.id)))
        return action
