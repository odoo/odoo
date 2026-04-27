from odoo import fields, models


class PosStoreTiming(models.Model):
    _name = 'pos.store.timing'
    _description = 'Pos Store Timings'

    weekday = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string='Week Day', required=True, default='monday')
    start_hour = fields.Float('Starting Hour', required=True, default=8.0)
    end_hour = fields.Float('Ending Hour', required=True, default=17.0)
    config_ids = fields.Many2many('pos.config', string='Point of Sale accociated to this timing')

    _sql_constraints = [(
        'check_start_and_end_hour',
        """CHECK(start_hour < end_hour)""",
        'The end time must be later than the start time.')]
