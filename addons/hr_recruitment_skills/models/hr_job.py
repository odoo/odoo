from markupsafe import Markup
from ast import literal_eval

from odoo import fields, models, _


class HrJob(models.Model):
    _inherit = "hr.job"

    skill_ids = fields.Many2many(comodel_name='hr.skill', string="Expected Skills")

    def action_search_matching_applicant(self):
        help_message_1 = _("No Matching Applicants")
        help_message_2 = _("We do not have any applicants who meet the skill requirements for this job position in the database at the moment.")
        action = self.env['ir.actions.actions']._for_xml_id('hr_recruitment.crm_case_categ0_act_job')
        context = literal_eval(action['context'])
        context['active_id'] = self.id
        action.update({
            'name': _("Matching Applicants"),
            'views': [
                (self.env.ref('hr_recruitment_skills.crm_case_tree_view_inherit_hr_recruitment_skills').id, 'tree'),
                (False, 'form'),
            ],
            'context': context,
            'domain': [
                ('job_id', '!=', self.id),
                ('skill_ids', 'in', self.skill_ids.ids),
            ],
            'help': Markup("<p class='o_view_nocontent_empty_folder'>%s</p><p>%s</p>") % (help_message_1, help_message_2),
        })
        return action
