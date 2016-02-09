# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

from odoo import fields, models


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"

    holiday_id = fields.Many2one("hr.holidays", "Leave Request")
