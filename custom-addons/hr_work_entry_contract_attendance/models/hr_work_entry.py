#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    attendance_id = fields.Many2one('hr.attendance', 'Attendance')
