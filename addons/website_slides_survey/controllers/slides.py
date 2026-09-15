import werkzeug.exceptions

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_slides.controllers.main import WebsiteSlides

_debug = DebugLog(__name__)


class WebsiteSlidesSurvey(WebsiteSlides):
    @http.route(
        ["/slides_survey/slide/get_certification_url"],
        type="http",
        auth="user",
        website=True,
    )
    def slide_get_certification_url(self, slide_id, **kw):
        fetch_res = self._get_slide(slide_id)
        if fetch_res.get("error"):
            _debug.logic(
                "certification_url_refused",
                reason=str(fetch_res["error"]),
                slide=slide_id,
            )
            raise werkzeug.exceptions.NotFound
        slide = fetch_res["slide"]
        if slide.channel_id.is_member:
            slide.action_set_viewed()
        certification_url = slide._generate_certification_url().get(slide.id)
        if not certification_url:
            _debug.logic("certification_url_refused", reason="no_url", slide=slide.id)
            raise werkzeug.exceptions.NotFound
        return request.redirect(certification_url)

    @http.route(
        ["/slides_survey/certification/search_read"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def slides_certification_search_read(self, fields):
        can_create = request.env["survey.survey"].has_access("create")
        return {
            "read_results": request.env["survey.survey"].search_read(
                [("certification", "=", True)], fields
            ),
            "can_create": can_create,
        }

    @http.route()
    def create_slide(self, *args, **post):
        create_new_survey = (
            post["slide_category"] == "certification"
            and post.get("survey")
            and not post["survey"]["id"]
        )
        linked_survey_id = int(post.get("survey", {}).get("id") or 0)

        if create_new_survey:
            if not request.env["survey.survey"].has_access("create"):
                return {"error": _("You are not allowed to create a survey.")}

            post["survey_id"] = (
                request.env["survey.survey"]
                .create(
                    {
                        "title": post["survey"]["title"],
                        "questions_layout": "page_per_question",
                        "is_attempts_limited": True,
                        "attempts_limit": 1,
                        "is_time_limited": False,
                        "scoring_type": "scoring_without_answers",
                        "certification": True,
                        "scoring_success_min": 70.0,
                        "certification_mail_template_id": request.env.ref(
                            "survey.mail_template_certification"
                        ).id,
                    }
                )
                .id
            )
        elif linked_survey_id:
            try:
                request.env["survey.survey"].browse([linked_survey_id]).read(["title"])
            except AccessError:
                return {"error": _("You are not allowed to link a certification.")}

            post["survey_id"] = post["survey"]["id"]

        result = super().create_slide(*args, **post)

        if post["slide_category"] == "certification":
            slide = request.env["slide.slide"].browse(result["slide_id"])
            result["url"] = (
                f"/slides/slide/{request.env['ir.http']._slug(slide)}?fullscreen=1"
            )

        return result

    def _slide_mark_completed(self, slide):
        if slide.slide_category == "certification":
            _debug.logic(
                "slide_complete_refused", reason="certification", slide=slide.id
            )
            raise werkzeug.exceptions.Forbidden(
                _("Certification slides are completed when the survey is succeeded.")
            )
        return super()._slide_mark_completed(slide)

    def _get_allowed_slide_post_fields(self):
        result = super()._get_allowed_slide_post_fields()
        result.append("survey_id")
        return result

    def _prepare_user_slides_profile(self, user):
        values = super()._prepare_user_slides_profile(user)
        values.update({"certificates": self._get_users_certificates(user)[user.id]})
        return values

    def _prepare_all_users_values(self, users):
        result = super()._prepare_all_users_values(users)
        certificates_per_user = self._get_users_certificates(users)
        for index, user in enumerate(users):
            result[index].update(
                {"certification_count": len(certificates_per_user.get(user.id, []))}
            )
        return result

    def _get_users_certificates(self, users):
        partner_ids = [user.partner_id.id for user in users]
        domain = [
            ("slide_partner_id.partner_id", "in", partner_ids),
            ("scoring_success", "=", True),
            ("slide_partner_id.survey_scoring_success", "=", True),
        ]
        certificates = request.env["survey.user_input"].sudo().search(domain)
        return {
            user.id: [
                certificate
                for certificate in certificates
                if certificate.partner_id == user.partner_id
            ]
            for user in users
        }

    def _prepare_ranks_badges_values(self, **kwargs):
        values = super()._prepare_ranks_badges_values(**kwargs)

        domain = Domain.AND(
            [[("survey_id", "!=", False)], self._get_domain_badges(**kwargs)]
        )
        certification_badges = request.env["gamification.badge"].sudo().search(domain)
        certification_badges = certification_badges.filtered(
            lambda b: "slides" in b.challenge_ids.mapped("challenge_category")
        )

        if not certification_badges:
            return values

        certification_badges = certification_badges.sorted(
            "granted_users_count", reverse=True
        )

        badges = values["badges"] - certification_badges

        certification_slides = (
            request.env["slide.slide"]
            .sudo()
            .search([("survey_id", "in", certification_badges.mapped("survey_id").ids)])
        )
        certification_badge_urls = {
            slide.survey_id.certification_badge_id.id: slide.channel_id.website_absolute_url
            for slide in certification_slides
        }

        values.update(
            {
                "badges": badges,
                "certification_badges": certification_badges,
                "certification_badge_urls": certification_badge_urls,
            }
        )
        return values
