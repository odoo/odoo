from markupsafe import Markup
from ast import literal_eval

from odoo import fields, models, _


class HrJob(models.Model):
    _inherit = "hr.job"

    skill_ids = fields.Many2many(comodel_name='hr.skill', string="Expected Skills")

    def action_search_matching_candidates(self):
        self.ensure_one()
        help_message_1 = _("No Matching Candidates")
        help_message_2 = _("We do not have any candidates who meet the skill requirements for this job position in the database at the moment.")
        action = self.env['ir.actions.actions']._for_xml_id('hr_recruitment.action_hr_candidate')
        context = literal_eval(action['context'])
        context['active_id'] = self.id
        matching_candidates = self.env['hr.candidate'].search([('skill_ids', 'in', self.skill_ids.ids)]).filtered(lambda c: self.id not in c.applicant_ids.job_id.ids)
        action.update({
            'name': _("Matching Candidates"),
            'views': [
                (self.env.ref('hr_recruitment_skills.hr_candidate_view_tree').id, 'tree'),
                (False, 'form'),
            ],
            'context': context,
            'domain': [('id', 'in', matching_candidates.ids)],
            'help': Markup("<p class='o_view_nocontent_empty_folder'>%s</p><p>%s</p>") % (help_message_1, help_message_2),
        })
        return action
