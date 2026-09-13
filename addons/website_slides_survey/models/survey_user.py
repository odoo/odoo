from odoo import api, fields, models


class SurveyUser_Input(models.Model):
    _inherit = "survey.user_input"

    slide_id = fields.Many2one(
        comodel_name="slide.slide",
        string="Related course slide",
        help="The related course slide when there is no membership information",
    )
    slide_partner_id = fields.Many2one(
        comodel_name="slide.slide.partner",
        string="Subscriber information",
        index="btree_not_null",
        help="Slide membership information for the logged in user",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_for_failed_attempt()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self._check_for_failed_attempt()
        return res

    def _check_for_failed_attempt(self):

        if self:
            user_inputs = self.search(
                [
                    ("id", "in", self.ids),
                    ("state", "=", "done"),
                    ("scoring_success", "=", False),
                    ("slide_partner_id", "!=", False),
                ]
            )

            if user_inputs:
                removed_memberships_per_partner = {}
                for user_input in user_inputs:
                    if user_input.survey_id._has_attempts_left(
                        user_input.partner_id, user_input.email, user_input.invite_token
                    ):
                        continue

                    self.env.ref(
                        "website_slides_survey.mail_template_user_input_certification_failed"
                    ).send_mail(
                        user_input.id, email_layout_xmlid="mail.mail_notification_light"
                    )

                    removed_memberships = removed_memberships_per_partner.get(
                        user_input.partner_id, self.env["slide.channel"]
                    )
                    removed_memberships |= user_input.slide_partner_id.channel_id
                    removed_memberships_per_partner[user_input.partner_id] = (
                        removed_memberships
                    )

                for (
                    partner_id,
                    removed_memberships,
                ) in removed_memberships_per_partner.items():
                    removed_memberships._remove_membership(partner_id.ids)
