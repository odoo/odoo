# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class TestCalendar(models.Model):
    _name = 'web_test.calendar'
    _description = 'Test Calendar'

    name = fields.Char(required=True, store=True, readonly=False)
    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    date = fields.Date(required=True, string='From')
    duration = fields.Float(required=True, store=True, string="Duration", readonly=False)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', index=True, default=lambda self: self.env['hr.work.entry.type'].search([], limit=1))
    color = fields.Integer(related='work_entry_type_id.color', readonly=True)
