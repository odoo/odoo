# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_based = fields.Boolean(string="Default Tracking", related='company_id.attendance_based', groups="hr.group_hr_user", readonly=False)
