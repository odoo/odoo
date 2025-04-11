from markupsafe import Markup
from ast import literal_eval

from odoo import fields, models, api, _


class HrJob(models.Model):
    _inherit = "hr.job"

    skill_ids = fields.Many2many(comodel_name='hr.skill', string="Expected Skills")
    applicant_matching_score = fields.Float(string="Matching Score(%)", compute="_compute_applicant_matching_score")

    @api.depends_context("active_applicant_id")
    def _compute_applicant_matching_score(self):
        # TODO: Is this an ensure_one situation?
        active_applicant_id = self.env.context.get('active_applicant_id')
        if not active_applicant_id:
            for job in self:
                job.applicant_matching_score = False
            return
        applicant = self.env['hr.applicant'].browse(active_applicant_id)
        for job in self:
            # TODO: Do the proper calculation
            job.applicant_matching_score = (len(job.skill_ids & applicant.skill_ids) / len(job.skill_ids) * 100) if job.skill_ids else False

    def action_search_matching_applicants(self):
        self.ensure_one()
        help_message_1 = _("No Matching Applicants")
        help_message_2 = _("We do not have any applicants who meet the skill requirements for this job position in the database at the moment.")
        action = self.env['ir.actions.actions']._for_xml_id('hr_recruitment.crm_case_categ0_act_job')
        context = literal_eval(action['context'])
        context['active_id'] = self.id
        action.update({
            'name': _("Matching Applicants"),
            'views': [
                (self.env.ref('hr_recruitment_skills.crm_case_tree_view_inherit_hr_recruitment_skills').id, 'list'),
                (False, 'form'),
            ],
            'context': context,
            'domain': [
                ('job_id', '!=', self.id),
                ('skill_ids', 'in', self.skill_ids.ids)
            ],
            'help': Markup("<p class='o_view_nocontent_empty_folder'>%s</p><p>%s</p>") % (help_message_1, help_message_2),
        })
        return action
