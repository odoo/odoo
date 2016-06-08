# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Calendar(models.Model):

    _inherit = "resource.calendar"

    uom_id = fields.Many2one("product.uom", string="Hours per Day", required=True,
        default=lambda self: self.env.ref('product.product_uom_hour'),
        help="""Average hours of work per day.
                It is used in an employee leave request to compute the number of days consumed based on the resource calendar.
                It can be used to handle various contract types, e.g.:
                - 38 Hours/Week, 5 Days/Week: 1 Day = 7.6 Hours
                - 45 Hours/Week, 5 Days/Week: 1 Day = 9.0 Hours""")


class CalendarLeaves(models.Model):

    _inherit = "resource.calendar.leaves"
    _description = "Leave Detail"

    holiday_id = fields.Many2one("hr.holidays", string='Leave Request')
