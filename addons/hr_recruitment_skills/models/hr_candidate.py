# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import fields, models, api


class HrCandidate(models.Model):
    _inherit = 'hr.candidate'

    candidate_skill_ids = fields.One2many('hr.candidate.skill', 'candidate_id', string="Skills")
    skill_ids = fields.Many2many('hr.skill', compute='_compute_skill_ids', store=True)
    matching_skill_ids = fields.Many2many(comodel_name='hr.skill', string="Matching Skills", compute="_compute_matching_skill_ids")
    missing_skill_ids = fields.Many2many(comodel_name='hr.skill', string="Missing Skills", compute="_compute_matching_skill_ids")
    matching_score = fields.Float(string="Matching Score(%)", compute="_compute_matching_skill_ids")

    @api.depends_context('active_id')
    @api.depends('skill_ids')
    def _compute_matching_skill_ids(self):
        job_id = self.env.context.get('active_id')
        if not job_id:
            self.matching_skill_ids = False
            self.missing_skill_ids = False
            self.matching_score = 0
        else:
            for candidate in self:
                job_skills = self.env['hr.job'].browse(job_id).skill_ids
                candidate.matching_skill_ids = job_skills & candidate.skill_ids
                candidate.missing_skill_ids = job_skills - candidate.skill_ids
                candidate.matching_score = (len(candidate.matching_skill_ids) / len(job_skills)) * 100 if job_skills else 0

    @api.depends('candidate_skill_ids.skill_id')
    def _compute_skill_ids(self):
        for candidate in self:
            candidate.skill_ids = candidate.candidate_skill_ids.skill_id

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        vals['employee_skill_ids'] = [(0, 0, {
            'skill_id': candidate_skill.skill_id.id,
            'skill_level_id': candidate_skill.skill_level_id.id,
            'skill_type_id': candidate_skill.skill_type_id.id,
        }) for candidate_skill in self.candidate_skill_ids]
        return vals

    def action_create_application(self):
        job = self.env['hr.job'].browse(self.env.context.get('active_id'))
        self.env['hr.applicant'].with_context(just_moved=True).create([{
            'candidate_id': candidate.id,
            'job_id': job.id,
        } for candidate in self])
        action = self.env['ir.actions.actions']._for_xml_id('hr_recruitment.action_hr_job_applications')
        action['context'] = literal_eval(action['context'].replace('active_id', str(job.id)))
        return action
