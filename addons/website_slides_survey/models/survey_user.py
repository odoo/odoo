# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    slide_id = fields.Many2one('slide.slide', 'Related course slide',
        help="The related course slide when there is no membership information")
    slide_partner_id = fields.Many2one('slide.slide.partner', 'Subscriber information',
        help="Slide membership information for the logged in user")

    @api.model_create_multi
    def create(self, vals_list):
        records = super(SurveyUserInput, self).create(vals_list)
        records._check_for_failed_attempt()
        return records

    @api.multi
    def write(self, vals):
        res = super(SurveyUserInput, self).write(vals)
        self._check_for_failed_attempt()
        return res

    def _check_for_failed_attempt(self):
        """ If the user fails his last attempt at a course certification,
        we remove him from the members of the course (and he has to enroll again).
        He receives an email in the process notifying him of his failure and suggesting
        he enrolls to the course again.

        The purpose is to have a 'certification flow' where the user can re-purchase the
        certification when they have failed it."""
        for record in self:
            if record.state == 'done' and not record.quizz_passed and record.slide_partner_id:
                if not record.survey_id._has_attempts_left(record.partner_id, record.email, record.invite_token):
                    # The mail needs to be sent BEFORE deleting slide and channel relations because we use them in the layout
                    self.env.ref('website_slides_survey.mail_template_user_input_certification_failed').send_mail(record.id, notif_layout="mail.mail_notification_light")

                    channel_id = record.slide_partner_id.channel_id.id
                    self.env['slide.slide.partner'].sudo().search([
                        ('partner_id', '=', record.partner_id.id),
                        ('slide_id', 'in', record.slide_partner_id.channel_id.slide_ids.ids)
                    ]).unlink()

                    self.env['slide.channel.partner'].sudo().search([
                        ('partner_id', '=', record.partner_id.id),
                        ('channel_id', '=', channel_id)
                    ]).unlink()
