import datetime
import time
from urllib.parse import quote as url_quote

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

# Per-user cache for the short recognition summary on the portal home page.
RECOGNITION_SUMMARY_CACHE = {}
RECOGNITION_SUMMARY_TTL = 60


class Od19RecognitionPortal(http.Controller):

    # ------------------------------------------------------------------
    # Full page
    # ------------------------------------------------------------------
    @http.route(
        ["/my/recognition"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my_recognition(self, given=None, error=None, **kwargs):
        return request.render(
            "od19_recognition.portal_recognition_page",
            self._od19_page_data(given=given, error=error),
        )

    # ------------------------------------------------------------------
    # Give Kudos (POST + CSRF)
    # ------------------------------------------------------------------
    @http.route(
        ["/my/recognition/give"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        sitemap=False,
        csrf=True,
    )
    def my_recognition_give(self, recipient_id=None, badge_id=None, message=None, **kwargs):
        error = None
        try:
            self._od19_create_kudos(recipient_id, badge_id, message)
        except (ValidationError, ValueError) as exc:
            error = str(exc)
        if error:
            return request.redirect("/my/recognition?error=%s" % url_quote(error))
        return request.redirect("/my/recognition?given=1")

    def _od19_create_kudos(self, recipient_id, badge_id, message):
        employee = request.env.user.employee_id
        recipient = int(recipient_id) if recipient_id else False
        badge = int(badge_id) if badge_id else False
        text = (message or "").strip()
        if not employee or not recipient:
            raise ValueError("Recipient is required.")
        if not text:
            raise ValueError("Message is required.")
        request.env["od19.recognition"].sudo().create(
            {
                "author_id": employee.id,
                "recipient_id": recipient,
                "badge_id": badge,
                "message": text,
                "company_id": request.env.company.id,
                "is_public": True,
            }
        )

    # ------------------------------------------------------------------
    # JSON summary for the portal home block
    # ------------------------------------------------------------------
    @http.route(
        ["/my/recognition/summary"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my_recognition_summary(self, **kwargs):
        user_id = request.env.user.id
        mono = time.monotonic()
        cached = RECOGNITION_SUMMARY_CACHE.get(user_id)
        if cached and mono - cached[0] < RECOGNITION_SUMMARY_TTL:
            return request.make_json_response(cached[1])
        payload = self._od19_summary_data()
        RECOGNITION_SUMMARY_CACHE[user_id] = (mono, payload)
        return request.make_json_response(payload)

    def _od19_summary_data(self):
        feed = self._od19_feed(limit=5)
        return {"feed": feed, "celebrations": self._od19_celebrations()}

    def _od19_page_data(self, given=None, error=None):
        return {
            "given": given,
            "error": error,
            "feed": self._od19_feed(limit=30),
            "celebrations": self._od19_celebrations(),
            "employees": request.env["hr.employee"]
            .sudo()
            .search([("user_id", "!=", False)], order="name"),
            "badges": request.env["od19.recognition.badge"].sudo().search([]),
            "datetime": datetime,
        }

    def _od19_feed(self, limit=5):
        records = (
            request.env["od19.recognition"]
            .sudo()
            .search([("is_public", "=", True)], order="published_date desc, id desc", limit=limit)
        )
        return [
            {
                "id": record.id,
                "author": record.author_id.name or "",
                "recipient": record.recipient_id.name or "",
                "message": record.message or "",
                "badge": record.badge_id.name or "",
                "badge_icon": record.badge_id.icon or "fa-star",
                "badge_color": record.badge_id.color or "#9E2424",
                "date": record.published_date
                and fields.Datetime.context_timestamp(
                    request.env.user, record.published_date
                ).strftime("%d/%m/%Y")
                or "",
            }
            for record in records
        ]

    def _od19_celebrations(self):
        """Birthdays (only if shared) and work anniversaries for this month."""
        today = fields.Date.context_today(request.env.user)
        brothers = request.env["hr.employee"].sudo().search(
            [("user_id", "!=", False), ("company_id", "in", request.env.companies.ids)]
        )
        birthdays = []
        anniversaries = []
        for employee in brothers:
            public_date = employee.birthday_public_display_string
            if (
                employee.birthday
                and public_date
                and public_date != "hidden"
                and employee.birthday.month == today.month
            ):
                birthdays.append(
                    {
                        "employee_id": employee.id,
                        "name": employee.name,
                        "day": employee.birthday.day,
                    }
                )
            start = employee.contract_date_start or employee.date_start
            if start and start.month == today.month and start.year < today.year:
                anniversaries.append(
                    {
                        "employee_id": employee.id,
                        "name": employee.name,
                        "day": start.day,
                        "years": today.year - start.year,
                    }
                )
        return {"birthdays": birthdays, "anniversaries": anniversaries}
