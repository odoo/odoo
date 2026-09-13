import typing

from odoo import fields, models

if typing.TYPE_CHECKING:
    from .mail_activity_schedule import MailActivitySchedule
    from odoo.addons.bus.models.res_users import ResUsers


class MailActivityScheduleSummary(models.TransientModel):
    _name = "mail.activity.schedule.line"
    _description = "Mail Activity Schedule Line"
    _order = "line_date_deadline asc, id asc"
    _rec_name = "activity_schedule_id"

    activity_schedule_id: MailActivitySchedule = fields.Many2one(
        comodel_name="mail.activity.schedule",
        required=True,
        ondelete="cascade",
    )
    line_description = fields.Char()
    line_date_deadline = fields.Date(string="Date Deadline")
    responsible_user_id: ResUsers = fields.Many2one(comodel_name="res.users")
