# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    display_type = fields.Selection(selection_add=[('event', 'Event')])
    event_id = fields.Many2one(
        'event.event', string="Event",
        ondelete='set null',
        domain=[('tag_ids.category_id', 'any', [('hr_resume_line_type_id', '!=', False)])],
        groups='event.group_event_user',
    )

    date_start = fields.Date(compute='_compute_event_data', store=True, readonly=False)
    date_end = fields.Date(compute='_compute_event_data', store=True, readonly=False)
    line_type_id = fields.Many2one('hr.resume.line.type', compute='_compute_event_data', store=True, readonly=False)
    name = fields.Char(compute='_compute_event_data', store=True, readonly=False)

    @api.depends('event_id')
    def _compute_event_data(self):
        for event, lines in self.filtered('event_id').grouped('event_id').items():
            values = self._values_from_event(event)
            if not values.get('line_type_id'):
                continue
            lines.write(values)

    @api.model
    def _values_from_event(self, event):
        line_type_id = False
        if line_types := event.tag_ids.category_id.hr_resume_line_type_id:
            line_type_id = line_types[0].id
        return {
            'date_start': event.date_begin,
            'date_end': event.date_end,
            'event_id': event.id,
            'display_type': 'event',
            'line_type_id': line_type_id,
            'name': event.name,
        }
