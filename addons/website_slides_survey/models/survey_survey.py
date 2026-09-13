from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    slide_channel_ids = fields.One2many(
        comodel_name="slide.channel",
        string="Certification Courses",
        compute="_compute_slide_channel_data",
        groups="website_slides.group_website_slides_officer",
        help="The courses this survey is linked to through the e-learning application",
    )
    slide_channel_count = fields.Count(
        count_of="slide_channel_ids",
        string="Courses Count",
        groups="website_slides.group_website_slides_officer",
    )

    @api.depends("slide_ids.channel_id")
    def _compute_slide_channel_data(self):
        for survey in self:
            survey.slide_channel_ids = survey.slide_ids.mapped("channel_id")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_to_course(self):
        certifications = (
            self.sudo()
            .slide_ids.filtered(lambda slide: slide.slide_type == "certification")
            .mapped("survey_id")
            .exists()
        )
        if certifications:
            certifications_course_mapping = [
                self.env._(
                    "- %(certification)s (Courses - %(courses)s)",
                    certification=certi.title,
                    courses=certi.slide_channel_ids.mapped("name"),
                )
                for certi in certifications
            ]
            raise ValidationError(
                _(
                    "Uh-oh! You can’t delete surveys used as a Course Certification! Otherwise, students might think diplomas just grow on trees.\n"
                    "The courses that need them are:\n%s",
                    "\n".join(certifications_course_mapping),
                )
            )

    def action_survey_view_slide_channels(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website_slides.slide_channel_action_overview"
        )
        action["display_name"] = _("Courses")
        if self.slide_channel_count == 1:
            action.update(
                {"views": [(False, "form")], "res_id": self.slide_channel_ids[0].id}
            )
        else:
            action.update(
                {
                    "views": [[False, "list"], [False, "form"]],
                    "domain": [("id", "in", self.slide_channel_ids.ids)],
                }
            )
        action["context"] = dict(
            self.env["ir.actions.actions"]._eval_action_context(
                action.get("context") or "{}"
            ),
            create=False,
        )
        return action

    def _prepare_challenge_category(self):
        slide_survey = self.env["slide.slide"].search([("survey_id", "=", self.id)])
        return "slides" if slide_survey else "certification"
