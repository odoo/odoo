from odoo import fields, models


class UniversityNoticeBoardHoliday(models.Model):
    _inherit = "university.notice.board"

    holiday_id = fields.Many2one(
        "public.holiday",
        string="Public Holiday",
        ondelete="set null",
        index=True,
        copy=False,
        readonly=True,
    )
    holiday_ids = fields.One2many(
        "public.holiday",
        "notice_id",
        string="Linked Public Holidays",
        readonly=True,
    )

    _holiday_notice_unique = models.Constraint(
        "UNIQUE(holiday_id)",
        "A public holiday can be linked to only one notice.",
    )
