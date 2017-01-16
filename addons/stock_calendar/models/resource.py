# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class WorkCalendarAttendance(models.Model):
    _inherit = "work.calendar.attendance"

    group_id = fields.Many2one('procurement.group', 'Procurement Group')


class WorkCalendarLeave(models.Model):
    _inherit = "work.calendar.leave"

    group_id = fields.Many2one('procurement.group', 'Procurement Group')
