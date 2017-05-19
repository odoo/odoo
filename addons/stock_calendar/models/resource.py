# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    group_id = fields.Many2one('procurement.group', 'Procurement Group')


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    group_id = fields.Many2one('procurement.group', string="Procurement Group")
