# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrRecruitmentStage(models.Model):
    _name = 'hr.recruitment.stage'
    _description = "Recruitment Stages"
    _order = 'sequence'

    name = fields.Char("Stage Name", required=True, translate=True)
    sequence = fields.Integer(
        "Sequence", default=10)
    job_ids = fields.Many2many(
        'hr.job', string='Job Specific',
        help='Specific jobs that use this stage. Other jobs will not use this stage.')
    requirements = fields.Text("Requirements")
    template_id = fields.Many2one(
        'mail.template', "Email Template",
        help="If set, a message is posted on the applicant using the template when the applicant is set to the stage.")
    fold = fields.Boolean(
        "Folded in Kanban",
        help="This stage is folded in the kanban view when there are no records in that stage to display.")
    hired_stage = fields.Boolean('Hired Stage',
        help="If checked, this stage is used to determine the hire date of an applicant")
    rotting_threshold_days = fields.Integer('Days to rot', default=0, help='Day count before applicants in this stage become stale. \
        Set to 0 to disable.  Changing this parameter will not affect the rotting status/date of resources last updated before this change.')
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda self: _('Blocked'), translate=True, required=True)
    legend_waiting = fields.Char(
        'Orange Kanban Label', default=lambda self: _('Waiting'), translate=True, required=True)
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda self: _('Ready for Next Stage'), translate=True, required=True)
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda self: _('In Progress'), translate=True, required=True)
    is_warning_visible = fields.Boolean(compute='_compute_is_warning_visible')

    @api.model
    def default_get(self, fields):
        if self.env.context and self.env.context.get('default_job_id') and not self.env.context.get('hr_recruitment_stage_mono', False):
            context = dict(self.env.context)
            context.pop('default_job_id')
            self = self.with_context(context)
        return super().default_get(fields)

    @api.depends('hired_stage')
    def _compute_is_warning_visible(self):
        applicant_data = self.env['hr.applicant']._read_group([('stage_id', 'in', self.ids)], ['stage_id'], ['__count'])
        applicants = {stage.id: count for stage, count in applicant_data}
        for stage in self:
            if stage._origin.hired_stage and not stage.hired_stage and applicants.get(stage._origin.id):
                stage.is_warning_visible = True
            else:
                stage.is_warning_visible = False
