import math
from datetime import time
from odoo import api, fields, models, _
from odoo.tools import format_time
from odoo.addons.resource.models.utils import float_to_time
from odoo.exceptions import ValidationError


class PlanningTemplate(models.Model):
    _name = 'planning.slot.template'
    _description = "Shift Template"
    _order = "sequence"

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Hours', compute="_compute_name")
    sequence = fields.Integer(export_string_translation=False, index=True)
    role_id = fields.Many2one('planning.role', string="Role")
    start_time = fields.Float('Planned Hours', aggregator=None, default_export_compatible=True, default=8.0)
    end_time = fields.Float('End Hour', aggregator=None, default_export_compatible=True, default=17.0)
    duration_days = fields.Integer('Duration Days', default=1, aggregator=None, default_export_compatible=True)

    _sql_constraints = [
        ('check_start_time_lower_than_24', 'CHECK(start_time < 24)', 'The start hour cannot be greater than 24.'),
        ('check_start_time_positive', 'CHECK(start_time >= 0)', 'The start hour cannot be negative.'),
        ('check_duration_days_positive', 'CHECK(duration_days > 0)', 'The span must be at least 1 working day.'),
    ]

    @api.constrains('start_time', 'end_time', 'duration_days')
    def _check_start_and_end_times(self):
        for template in self:
            if template.end_time < template.start_time and template.duration_days <= 1:
                raise ValidationError(_('The start hour cannot be before the end hour for a one-day shift template.'))

    @api.depends('start_time', 'end_time', 'duration_days')
    def _compute_name(self):
        for shift_template in self:
            if not (0 <= shift_template.start_time < 24 and 0 <= shift_template.end_time < 24):
                raise ValidationError(_('The start and end hours must be greater or equal to 0 and lower than 24.'))
            start_time = time(hour=int(shift_template.start_time), minute=min(59, round(math.modf(shift_template.start_time)[0] / (1 / 60.0))))
            end_time = time(hour=int(shift_template.end_time), minute=min(59, round(math.modf(shift_template.end_time)[0] / (1 / 60.0))))
            shift_template.name = '%s - %s %s' % (
                format_time(shift_template.env, start_time, time_format='short').replace(':00 ', ' '),
                format_time(shift_template.env, end_time, time_format='short').replace(':00 ', ' '),
                _('(%s days span)', shift_template.duration_days) if shift_template.duration_days > 1 else ''
            )

    @api.depends('role_id')
    def _compute_display_name(self):
        for shift_template in self:
            name = '{} {}'.format(
                shift_template.name,
                shift_template.role_id.name if shift_template.role_id.name is not False else '',
            )
            shift_template.display_name = name

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = []
        for data in super(PlanningTemplate, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy):
            if 'start_time' in data:
                data['start_time'] = float_to_time(data['start_time']).strftime('%H:%M')
            if 'end_time' in data:
                data['end_time'] = float_to_time(data['end_time']).strftime('%H:%M')
            res.append(data)

        return res
