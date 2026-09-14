from odoo import fields, models
from odoo.libs.debug_log import DebugLog

from .hr_homeworking import DAYS, PLAIN_IM_STATUSES

_debug = DebugLog(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    monday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        related="employee_id.monday_location_id",
        string="Mondays",
        readonly=False,
    )
    tuesday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        related="employee_id.tuesday_location_id",
        string="Tuesdays",
        readonly=False,
    )
    wednesday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        related="employee_id.wednesday_location_id",
        string="Wednesdays",
        readonly=False,
    )
    thursday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        related="employee_id.thursday_location_id",
        string="Thursdays",
        readonly=False,
    )
    friday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        related="employee_id.friday_location_id",
        string="Fridays",
        readonly=False,
    )
    saturday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        related="employee_id.saturday_location_id",
        string="Saturdays",
        readonly=False,
    )
    sunday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        related="employee_id.sunday_location_id",
        string="Sundays",
        readonly=False,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + DAYS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + DAYS

    def _compute_im_status(self):
        super()._compute_im_status()
        employees = self.employee_id.sudo()
        locations = employees._get_today_location()
        for user in self:
            location = locations.get(user.employee_id.id)
            if not location or user.im_status not in PLAIN_IM_STATUSES:
                continue
            _debug.logic(
                "im_status.located",
                user=user,
                status=user.im_status,
                location_type=location.location_type,
            )
            user.im_status = f"{location.location_type}_{user.im_status}"
