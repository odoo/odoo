import logging
from datetime import datetime

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class RamWebsiteReview(models.Model):
    _name = "ram.website.review"
    _description = "RAM Website Review"
    _inherit = ["website.published.multi.mixin"]
    _order = "sequence asc, id desc"

    sequence = fields.Integer(default=10)
    author_name = fields.Char(required=True)
    rating = fields.Integer(default=5)
    content = fields.Text(required=True)
    source = fields.Selection(
        selection=[("manual", "Manual"), ("google", "Google Reviews")],
        default="manual",
        required=True,
    )
    external_id = fields.Char(
        string="External ID",
        help="Identifier used to deduplicate external reviews (e.g., Google review id).",
        index=True,
    )
    review_url = fields.Char(string="Review URL")
    author_photo_url = fields.Char(string="Author Photo URL")
    review_time = fields.Datetime(string="Review Time")

    @api.constrains("rating")
    def _check_rating(self):
        for record in self:
            if record.rating < 1 or record.rating > 5:
                raise ValidationError("Rating must be between 1 and 5.")

    @api.model
    def _google_places_params(self):
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "api_key": (icp.get_param("ram_webiste.google_places_api_key") or "").strip(),
            "place_id": (icp.get_param("ram_webiste.google_place_id") or "").strip(),
            "language": (icp.get_param("ram_webiste.google_reviews_language") or "en").strip() or "en",
            "max_reviews": int(icp.get_param("ram_webiste.google_reviews_max") or 12),
        }

    @api.model
    def action_sync_google_reviews(self):
        params = self._google_places_params()
        if not params["api_key"] or not params["place_id"]:
            raise UserError(
                "Google Reviews sync is not configured.\n\n"
                "Set your Google Places API Key and Place ID in Settings > RAM Website."
            )
        created, updated = self._sync_google_reviews(params)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Google Reviews Synced",
                "message": f"Created: {created} • Updated: {updated}",
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def cron_sync_google_reviews(self):
        params = self._google_places_params()
        if not params["api_key"] or not params["place_id"]:
            _logger.info("ram_webiste: skipping Google Reviews sync (not configured).")
            return
        try:
            self._sync_google_reviews(params)
        except Exception:
            # Cron jobs should never spam tracebacks to users; log and move on.
            _logger.exception("ram_webiste: Google Reviews cron sync failed.")

    @api.model
    def _sync_google_reviews(self, params):
        # Google Places API: Place Details (reviews)
        # https://developers.google.com/maps/documentation/places/web-service/details
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        query = {
            "place_id": params["place_id"],
            "fields": "reviews,url",
            "reviews_sort": "newest",
            "language": params["language"],
            "key": params["api_key"],
        }
        try:
            resp = requests.get(url, params=query, timeout=15)
        except requests.exceptions.RequestException as exc:
            raise UserError(f"Google Places request failed: {exc}") from exc
        if resp.status_code != 200:
            raise UserError(f"Google Places request failed (HTTP {resp.status_code}).")

        payload = resp.json() or {}
        if payload.get("status") not in ("OK", "ZERO_RESULTS"):
            raise UserError(f"Google Places error: {payload.get('status')}: {payload.get('error_message')}")

        result = payload.get("result") or {}
        place_url = result.get("url")
        reviews = (result.get("reviews") or [])[: params["max_reviews"]]

        created = 0
        updated = 0
        for item in reviews:
            # The Places API does not expose a dedicated review id. Build a stable-ish external key.
            external_id = f"{item.get('author_name','')}:{item.get('time','')}:{item.get('rating','')}"
            content = (item.get("text") or "").strip()
            if not content:
                continue

            vals = {
                "author_name": item.get("author_name") or "Google User",
                "rating": max(1, min(5, int(item.get("rating") or 5))),
                "content": content,
                "source": "google",
                "external_id": str(external_id).strip(),
                "review_url": place_url or False,
                "author_photo_url": item.get("profile_photo_url") or False,
                # Google returns epoch seconds; store as naive UTC datetime (Odoo convention).
                "review_time": datetime.utcfromtimestamp(int(item.get("time"))) if item.get("time") else False,
                "is_published": True,
            }
            existing = self.search([("source", "=", "google"), ("external_id", "=", vals["external_id"])], limit=1)
            if existing:
                existing.write(vals)
                updated += 1
            else:
                self.create(vals)
                created += 1
        return created, updated
