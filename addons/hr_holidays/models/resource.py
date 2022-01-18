# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')

    @api.constrains('date_from', 'date_to', 'calendar_id')
    def _check_compare_dates(self):
        all_existing_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.company_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
        ])
        for record in self:
            if not record.resource_id:
                existing_leaves = all_existing_leaves.filtered(lambda leave:
                        record.id != leave.id
                        and record['company_id'] == leave['company_id']
                        and record['date_from'] <= leave['date_to']
                        and record['date_to'] >= leave['date_from'])
                if record.calendar_id:
                    existing_leaves = existing_leaves.filtered(lambda l: not l.calendar_id or l.calendar_id == record.calendar_id)
                if existing_leaves:
                    raise ValidationError(_('Two public holidays cannot overlap each other for the same working hours.'))

class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer("Leave Count", compute='_compute_associated_leaves_count')

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env['resource.calendar.leaves'].read_group(
            [('resource_id', '=', False)],
            ['calendar_id'],
            ['calendar_id']
        )
        result = dict((data['calendar_id'][0] if data['calendar_id'] else 'global', data['calendar_id_count']) for data in leaves_read_group)
        global_leave_count = result.get('global', 0)
        for calendar in self:
            calendar.associated_leaves_count = result.get(calendar.id, 0) + global_leave_count
