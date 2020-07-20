# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    count_attendance_extra_hours = fields.Boolean(string="Count Extra Hours")
    extra_hours_start_date = fields.Datetime(string="Extra Hours Starting Date")
