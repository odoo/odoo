# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')
