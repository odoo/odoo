# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    renting_minimal_time_duration = fields.Integer("Minimal Rental Duration")
    renting_minimal_time_unit = fields.Selection([
        ("hour", "Hours"),
        ("day", "Days"),
        ("week", "Weeks"),
        ("month", "Months")
    ], string="Minimal Rental Duration Unit", required=True, default='day')
    renting_forbidden_mon = fields.Boolean("Monday")
    renting_forbidden_tue = fields.Boolean("Tuesday")
    renting_forbidden_wed = fields.Boolean("Wednesday")
    renting_forbidden_thu = fields.Boolean("Thursday")
    renting_forbidden_fri = fields.Boolean("Friday")
    renting_forbidden_sat = fields.Boolean("Saturday")
    renting_forbidden_sun = fields.Boolean("Sunday")

    def _get_minimal_rental_duration(self):
        """Get minimal rental duration expressed in relativedelta"""
        return relativedelta(
            **{f'{self.renting_minimal_time_unit}s': self.renting_minimal_time_duration}
        )

    def _get_renting_forbidden_days(self):
        forbidden_day_fields = {
            'renting_forbidden_mon': 1,
            'renting_forbidden_tue': 2,
            'renting_forbidden_wed': 3,
            'renting_forbidden_thu': 4,
            'renting_forbidden_fri': 5,
            'renting_forbidden_sat': 6,
            'renting_forbidden_sun': 7,
        }
        return [value for field, value in forbidden_day_fields.items() if self[field]]
