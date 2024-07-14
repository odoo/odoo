# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, _lt, fields, models


class SaleOrderRecurrence(models.Model):
    _name = 'sale.temporal.recurrence'
    _description = "Sale temporal Recurrence"
    _order = 'unit,duration'

    active = fields.Boolean(default=True)
    name = fields.Char(translate=True, required=True, default="Monthly")
    duration = fields.Integer(
        required=True,
        default=1,
        help="Minimum duration before this rule is applied. If set to 0, it represents a fixed"
            "rental price.",
    )
    unit = fields.Selection(
        selection=[
            ('hour', "Hours"),
            ('day', "Days"),
            ('week', "Weeks"),
            ('month', "Months"),
            ('year', "Years"),
        ],
        required=True,
        default='month',
    )
    duration_display = fields.Char(compute='_compute_duration_display')

    _sql_constraints = [
        (
            "temporal_recurrence_duration",
            "CHECK(duration >= 0)",
            "The pricing duration has to be greater or equal to 0.",
        ),
    ]

    def _compute_duration_display(self):
        for record in self:
            duration = record.duration
            record.duration_display = _(
                "%(duration)s %(unit)s", duration=duration, unit=record._get_unit_label(duration)
            )

    def _get_unit_label(self, duration):
        """ Get the translated product pricing unit label. """
        self.ensure_one()
        if duration == 1:
            singular_labels = {
                'hour': _lt("Hour"),
                'day': _lt("Day"),
                'week': _lt("Week"),
                'month': _lt("Month"),
                'year': _lt("Year"),
            }
            return str(singular_labels[self.unit])
        return dict(self._fields['unit']._description_selection(self.env))[self.unit]
