from markupsafe import escape

from odoo import _, api, fields, models


class SchoolDashboardHoliday(models.Model):
    _inherit = "school.dashboard"

    upcoming_holidays_html = fields.Html(
        string="Upcoming Holidays",
        compute="_compute_upcoming_holidays",
        sanitize=True,
    )

    @api.depends()
    def _compute_upcoming_holidays(self):
        today = fields.Date.context_today(self)
        holidays = self.env["public.holiday"].sudo().search(
            [("active", "=", True), ("date_to", ">=", today)],
            order="date_from asc, id asc",
            limit=3,
        )
        for dashboard in self:
            if not holidays:
                dashboard.upcoming_holidays_html = (
                    '<p class="text-muted mb-0">%s</p>'
                    % escape(_("No upcoming holidays scheduled."))
                )
                continue
            items = []
            for holiday in holidays:
                date_text = fields.Date.to_string(holiday.date_from)
                if holiday.date_to and holiday.date_to != holiday.date_from:
                    date_text = "%s – %s" % (
                        date_text,
                        fields.Date.to_string(holiday.date_to),
                    )
                items.append(
                    '<li class="list-group-item d-flex justify-content-between align-items-center px-0">'
                    '<span><strong>%s</strong><br/><small class="text-muted">%s</small></span>'
                    '<span class="badge text-bg-warning">%s</span></li>'
                    % (escape(holiday.name), escape(date_text), escape(_("Holiday")))
                )
            dashboard.upcoming_holidays_html = (
                '<ul class="list-group list-group-flush">%s</ul>' % "".join(items)
            )

    def action_open_upcoming_holidays(self):
        return self.env.ref("school_public_holiday.action_public_holiday").read()[0]
