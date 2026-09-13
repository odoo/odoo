from odoo import api, fields, models
from odoo.fields import Domain


class SlideSlidePartner(models.Model):
    _inherit = "slide.slide.partner"

    user_input_ids = fields.One2many(
        comodel_name="survey.user_input",
        inverse_name="slide_partner_id",
        string="Certification attempts",
    )
    survey_scoring_success = fields.Boolean(
        string="Certification Succeeded",
        compute="_compute_survey_scoring_success",
        store=True,
    )

    @api.depends("partner_id", "user_input_ids.scoring_success")
    def _compute_survey_scoring_success(self):
        succeeded_user_inputs = (
            self.env["survey.user_input"]
            .sudo()
            .search(
                [("slide_partner_id", "in", self.ids), ("scoring_success", "=", True)]
            )
        )
        succeeded_slide_partners = succeeded_user_inputs.mapped("slide_partner_id")
        for record in self:
            record.survey_scoring_success = record in succeeded_slide_partners

    def _compute_field_value(self, field, validate=True):
        super()._compute_field_value(field, validate=validate)
        if field.name == "survey_scoring_success":
            self.filtered("survey_scoring_success").write({"completed": True})

    def _recompute_completion(self):
        super()._recompute_completion()
        certification_success_slides = self.filtered(
            lambda slide: slide.survey_scoring_success
        )
        if not certification_success_slides:
            return
        certified_channels_domain = Domain.OR(
            Domain("partner_id", "=", slide.partner_id.id)
            & Domain("channel_id", "=", slide.channel_id.id)
            for slide in certification_success_slides
        )
        self.env["slide.channel.partner"].search(
            Domain("survey_certification_success", "=", False)
            & certified_channels_domain
        ).survey_certification_success = True


class SlideSlide(models.Model):
    _inherit = "slide.slide"

    name = fields.Char(
        compute="_compute_name",
        store=True,
        readonly=False,
    )
    is_preview = fields.Boolean(
        compute="_compute_is_preview",
        store=True,
        readonly=False,
    )

    @api.depends("survey_id")
    def _compute_name(self):
        for slide in self:
            if not slide.name and slide.survey_id:
                slide.name = slide.survey_id.title

    def _compute_mark_complete_actions(self):
        super()._compute_mark_complete_actions()
        for slide in self:
            if slide.slide_category == "certification":
                slide.can_self_mark_uncompleted = False
                slide.can_self_mark_completed = False

    @api.depends("slide_category")
    def _compute_is_preview(self):
        for slide in self:
            if slide.slide_category == "certification" or not slide.is_preview:
                slide.is_preview = False

    @api.model_create_multi
    def create(self, vals_list):
        slides = super().create(vals_list)
        slides_with_survey = slides.filtered("survey_id")
        slides_with_survey.slide_category = "certification"
        slides_with_survey._update_challenge_category()
        return slides

    def write(self, vals):
        old_surveys = self.mapped("survey_id")
        result = super().write(vals)
        if "survey_id" in vals:
            self._update_challenge_category(
                old_surveys=old_surveys - self.mapped("survey_id")
            )
        return result

    def unlink(self):
        old_surveys = self.mapped("survey_id")
        result = super().unlink()
        self._update_challenge_category(old_surveys=old_surveys, unlink=True)
        return result

    def _update_challenge_category(self, old_surveys=None, unlink=False):
        # Bookkeeping on gamification challenges the slide's certification owns:
        # an eLearning officer copying or editing a course need not be able to read
        # surveys or badges for their challenges to be filed under the right menu.
        if old_surveys:
            old_certification_challenges = (
                old_surveys.sudo().mapped("certification_badge_id").challenge_ids
            )
            old_certification_challenges.write({"challenge_category": "certification"})
        if not unlink:
            certification_challenges = (
                self.sudo().survey_id.certification_badge_id.challenge_ids
            )
            certification_challenges.write({"challenge_category": "slides"})

    def _generate_certification_url(self):
        certification_urls = {}
        for slide in self.filtered(
            lambda slide: slide.slide_category == "certification" and slide.survey_id
        ):
            if slide.channel_id.is_member:
                user_membership_id_sudo = slide.user_membership_id.sudo()
                if user_membership_id_sudo.user_input_ids:
                    last_user_input = next(
                        user_input
                        for user_input in user_membership_id_sudo.user_input_ids.sorted(
                            lambda user_input: user_input.create_date, reverse=True
                        )
                    )
                    certification_urls[slide.id] = last_user_input.get_start_url()
                else:
                    user_input = slide.survey_id.sudo()._create_answer(
                        partner=self.env.user.partner_id,
                        check_attempts=False,
                        slide_id=slide.id,
                        slide_partner_id=user_membership_id_sudo.id,
                        invite_token=self.env[
                            "survey.user_input"
                        ]._generate_invite_token(),
                    )
                    certification_urls[slide.id] = user_input.get_start_url()
            else:
                user_input = slide.survey_id.sudo()._create_answer(
                    partner=self.env.user.partner_id,
                    check_attempts=False,
                    test_entry=True,
                    slide_id=slide.id,
                )
                certification_urls[slide.id] = user_input.get_start_url()
        return certification_urls
