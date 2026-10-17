# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    calendar_weekend_days = fields.Json(
        string="Calendar Weekend Days",
        default=lambda self: [0, 6],
        help="Days hidden when Show weekends is disabled in calendar views. "
             "This display setting does not change working schedules.",
    )

    @api.constrains('calendar_weekend_days')
    def _check_calendar_weekend_days(self):
        for company in self:
            days = company.calendar_weekend_days if company.calendar_weekend_days is not False else []
            if (
                not isinstance(days, list)
                or any(not isinstance(day, int) or isinstance(day, bool) or not 0 <= day <= 6 for day in days)
                or len(days) != len(set(days))
            ):
                raise ValidationError(self.env._("Weekend days must be distinct days of the week."))
            if len(days) == 7:
                raise ValidationError(self.env._("At least one day must remain visible in calendar views."))
