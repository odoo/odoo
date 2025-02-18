# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HrJob(models.Model):
    _inherit = "hr.job"

    survey_id = fields.Many2one(
        'survey.survey', "Interview Form", index='btree_not_null',
        help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job")

    def action_test_survey(self):
        self.ensure_one()
        action = self.survey_id.action_test_survey()
        return action

    def action_new_survey(self):
        self.ensure_one()
        survey = self.env['survey.survey'].create({
            'title': _("Interview Form: %s", self.name),
        })
        self.write({'survey_id': survey.id})

        action = {
                'name': _('Survey'),
                'view_mode': 'form,list',
                'res_model': 'survey.survey',
                'type': 'ir.actions.act_window',
                'res_id': survey.id,
            }

        return action
