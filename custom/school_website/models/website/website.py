import threading
from urllib.parse import urlsplit

from odoo import api, fields, models, tools
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    @api.model
    def get_current_website(self, fallback=True):
        """
        Override get_current_website to safely extract the netloc (host:port)
        from thread_url instead of passing full request paths, preventing
        UnicodeError in the IDNA codec on non-standard local hosts.
        """
        thread_url = hasattr(threading.current_thread(), "url") and threading.current_thread().url
        thread_host = urlsplit(thread_url).netloc if thread_url else ""
        domain_name = (
            request and request.httprequest.host
            or thread_host
            or ""
        )
        website_id = self.sudo()._get_current_website_id(domain_name, fallback=fallback)
        return self.browse(website_id)

    @api.model
    @tools.ormcache("domain_name", "fallback")
    def _get_current_website_id(self, domain_name, fallback=True):
        """
        Inherit _get_current_website_id to sanitize domain_name (strip URL scheme/path)
        and catch any UnicodeError on encoding.
        """
        if domain_name and ("://" in domain_name or "/" in domain_name):
            domain_name = urlsplit(domain_name).netloc
        try:
            return super()._get_current_website_id(domain_name, fallback=fallback)
        except UnicodeError:
            default_site = self.search([], limit=1)
            return default_site.id if default_site else False

    def get_featured_programs(self, limit=6):
        """Fetch active university programs for the homepage showcase."""
        if "university.program" in self.env:
            return self.env["university.program"].sudo().search([("active", "=", True)], limit=limit)
        return self.env["university.program"]

    def get_upcoming_campus_events(self, limit=4):
        """Fetch upcoming campus events and announcements."""
        if "university.notice.board" in self.env:
            return self.env["university.notice.board"].sudo().search(
                [("notice_type", "in", ["event", "academic"])],
                order="pinned desc, date desc",
                limit=limit,
            )
        return self.env["university.notice.board"]

    def get_university_stats(self):
        """Fetch quick statistics for the university landing page."""
        stats = {
            "students_count": 0,
            "teachers_count": 0,
            "programs_count": 0,
            "departments_count": 0,
        }
        if "university.student" in self.env:
            stats["students_count"] = self.env["university.student"].sudo().search_count([("status", "=", "active")])
        if "university.teacher" in self.env:
            stats["teachers_count"] = self.env["university.teacher"].sudo().search_count([("active", "=", True)])
        if "university.program" in self.env:
            stats["programs_count"] = self.env["university.program"].sudo().search_count([("active", "=", True)])
        if "university.department" in self.env:
            stats["departments_count"] = self.env["university.department"].sudo().search_count([("active", "=", True)])
        return stats
