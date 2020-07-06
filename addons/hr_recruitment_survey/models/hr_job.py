# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class Job(models.Model):
    _inherit = "hr.job"

    survey_id = fields.Many2one(
        'survey.survey', "Interview Form",
        help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job")

    def action_print_survey(self):
        return self.survey_id.action_print_survey()

    def action_new_survey(self):
        self.ensure_one()
        survey = self.env['survey.survey'].create({
            'title': _("Interview Form : %s") % self.name,
        })
        self.write({'survey_id': survey.id})
        survey_action = self.env.ref('hr_recruitment_survey.test_survey_view')
        dict_act_window = survey_action.read([])[0]
        dict_act_window['context'] = {'form_view_initial_mode': 'edit'}
        dict_act_window['res_id'] = survey.id

        return dict_act_window
