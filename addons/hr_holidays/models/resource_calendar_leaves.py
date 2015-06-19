# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class ResourceCalendarLeaves(models.Model):
    _description = "Leave Detail"
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.holidays", "Leave Request")
