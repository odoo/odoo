from odoo import fields, models
from odoo.tools import format_duration


class PosConfig(models.Model):
    _inherit = 'pos.config'

    urbanpiper_minimum_preparation_time = fields.Integer(
        string='Minimum Preparation Time (Seconds)',
        help='The minimum amount of time the customer must wait for the order to be prepared.',
        default=2700,
        required=True,
    )

    def prepare_store_data(self, data):
        self.ensure_one()
        data = super().prepare_store_data(data)
        config_store_timing = self.env['pos.store.timing'].search([('config_ids', 'in', self.ids)])
        timings = [
            {
                'day': timing.weekday,
                'slots': [
                    {
                        'start_time': "23:59:00" if timing.start_hour == 24.0 else f"{format_duration(timing.start_hour)}:00",
                        'end_time': "23:59:00" if timing.end_hour == 24.0 else f"{format_duration(timing.end_hour)}:00"
                    }
                ]
            } for timing in config_store_timing
        ]
        if timings:
            data['stores'][0]['timings'] = timings
        data['stores'][0]['min_pickup_time'] = self.urbanpiper_minimum_preparation_time
        return data
