# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    survey_id = fields.Many2one('survey.survey', related='job_id.survey_id', string="Survey", readonly=True)
    response_ids = fields.One2many('survey.user_input', 'applicant_id', string="Responses")

    def _cancel_survey_user_inputs(self) -> None:
        """Cancels all open surveys for the applicant(s)"""
        surveys_to_cancel_domain = Domain.AND([
            Domain('partner_id', 'in', self.partner_id.ids),
            Domain('state', 'in', ['new', 'in_progress']),
        ])
        self.env['survey.user_input'].search(surveys_to_cancel_domain).write(
            {'state': 'cancelled'},
        )

    def action_archive(self):
        res = super().action_archive()
        self._cancel_survey_user_inputs()
        return res

    def action_print_survey(self):
        """ If response is available then print this response otherwise print survey form (print template of the survey) """
        self.ensure_one()
        sorted_interviews = self.response_ids\
            .filtered(lambda i: i.survey_id == self.survey_id)\
            .sorted(lambda i: i.create_date, reverse=True)
        if not sorted_interviews:
            action = self.survey_id.action_print_survey()
            action['target'] = 'new'
            return action

        answered_interviews = sorted_interviews.filtered(lambda i: i.state == 'done')
        if answered_interviews:
            action = self.survey_id.action_print_survey(answer=answered_interviews[0])
            action['target'] = 'new'
            return action
        action = self.survey_id.action_print_survey(answer=sorted_interviews[0])
        action['target'] = 'new'
        return action

    def action_send_survey(self):
        template = self.env.ref('hr_recruitment_survey.mail_template_applicant_interview_invite', raise_if_not_found=False)

        applicant_partner_ids = self.env['res.partner']
        applicant_survey_ids = self.env['survey.survey']

        # If an applicant does not already have an associated partner, search for it, or create it.
        for applicant in self:
            if not applicant.partner_id:
                if not applicant.partner_name:
                    raise UserError(self.env._('Please provide an applicant name.'))

                applicant.partner_id = applicant.env['res.partner'].sudo().create({
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                })

            applicant.survey_id.check_validity()
            applicant_partner_ids += applicant.partner_id
            applicant_survey_ids += applicant.survey_id

        local_context = dict(
            default_applicant_ids=self.ids,
            default_survey_id=False,
            default_survey_ids=applicant_survey_ids.ids,
            default_partner_ids=applicant_partner_ids.ids,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_deadline=fields.Datetime.now() + timedelta(days=15)
        )

        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Send interviews"),
            'view_mode': 'form',
            'res_model': 'hr.recruitment.survey.invite',
            'target': 'new',
            'context': local_context,
        }

    def write(self, vals):
        stage = self.env['hr.recruitment.stage'].browse(vals.get('stage_id'))
        if stage.hired_stage:
            self._cancel_survey_user_inputs()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_cancel_user_inputs(self) -> None:
        self._cancel_survey_user_inputs()
