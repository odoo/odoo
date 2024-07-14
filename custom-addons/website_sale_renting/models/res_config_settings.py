# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    renting_minimal_time_duration = fields.Integer(
        related='company_id.renting_minimal_time_duration', readonly=False)
    renting_minimal_time_unit = fields.Selection(
        related='company_id.renting_minimal_time_unit', readonly=False, required=True)
    renting_forbidden_mon = fields.Boolean(
        "Monday", related="company_id.renting_forbidden_mon", readonly=False)
    renting_forbidden_tue = fields.Boolean(
        "Tuesday", related="company_id.renting_forbidden_tue", readonly=False)
    renting_forbidden_wed = fields.Boolean(
        "Wednesday", related="company_id.renting_forbidden_wed", readonly=False)
    renting_forbidden_thu = fields.Boolean(
        "Thursday", related="company_id.renting_forbidden_thu", readonly=False)
    renting_forbidden_fri = fields.Boolean(
        "Friday", related="company_id.renting_forbidden_fri", readonly=False)
    renting_forbidden_sat = fields.Boolean(
        "Saturday", related="company_id.renting_forbidden_sat", readonly=False)
    renting_forbidden_sun = fields.Boolean(
        "Sunday", related="company_id.renting_forbidden_sun", readonly=False)
