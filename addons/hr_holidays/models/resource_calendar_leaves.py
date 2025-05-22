# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Time Off Request')
