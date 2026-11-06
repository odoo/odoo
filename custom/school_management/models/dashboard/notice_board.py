from odoo import api, fields, models

class UniversityNoticeBoard(models.Model):
    _name = "university.notice.board"
    _description = "Campus Notice Board"
    _order = "pinned desc, date desc, id desc"

    name = fields.Char(string="Notice Title", required=True)
    date = fields.Date(string="Announcement Date", default=fields.Date.context_today, required=True, index=True)
    notice_type = fields.Selection(
        [
            ("academic", "Academic Announcement"),
            ("exam", "Exams & Timetables"),
            ("event", "Campus Event & Summit"),
            ("administrative", "Policy & Administration"),
            ("holiday", "Holiday & Break"),
            ("facility", "Campus Facilities & IT"),
        ],
        string="Category",
        default="academic",
        required=True,
        index=True,
    )
    priority = fields.Selection(
        [
            ("low", "Normal"),
            ("medium", "Important"),
            ("high", "Urgent / Alert"),
        ],
        string="Priority",
        default="medium",
        required=True,
        index=True,
    )
    target_audience = fields.Selection(
        [
            ("all", "All Students & Staff"),
            ("students", "Enrolled Students"),
            ("faculty", "Faculty Staff Only"),
            ("graduating", "Graduating Cohorts"),
        ],
        string="Target Audience",
        default="all",
        required=True,
    )
    department_id = fields.Many2one("university.department", string="Issuing Department")
    academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Academic Year",
        default=lambda self: self.env["university.academic.year"].search([("current", "=", True)], limit=1),
    )
    author_name = fields.Char(string="Issued By", default="Office of Academic Affairs")
    pinned = fields.Boolean(string="Pin to Top", default=False, help="Sticky notice at the top of the campus board.")
    image_1920 = fields.Image(string="Cover Banner", max_width=1920, max_height=1080)
    color = fields.Integer(string="Color Index", default=0)
    content = fields.Html(string="Notice Content", sanitize=True)
    active = fields.Boolean(string="Active", default=True)

    def action_toggle_pinned(self):
        for rec in self:
            rec.pinned = not rec.pinned
