from odoo import api, fields, models


class Website(models.Model):
    _inherit = "website"

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
