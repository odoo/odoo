# coding: utf-8

from odoo import fields, models


class PosOnlineDeliveryMealtime(models.Model):
    _name = 'pos.online.delivery.mealtime'
    _description = 'Pos Delivery Mealtime'

    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Week Day', required=True, default='1')
    start_hour = fields.Float('Starting Hour', required=True, default=8.0)
    end_hour = fields.Float('Ending Hour', required=True, default=17.0, compute='_compute_end_hour', readonly=False,
                            store=True)
    provider_id = fields.Many2one('pos.online.delivery.provider', string='Delivery Provider', required=True)
    name = fields.Char('Name')
    description = fields.Text('Description', size=500)
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920, required=True)

    _sql_constraints = [(
        'check_start_and_end_hour',
        """CHECK(
                ((end_hour=0 AND (start_hour BETWEEN 0 AND 23.99))
                    OR (start_hour BETWEEN 0 AND end_hour))
                AND (end_hour=0
                    OR (end_hour BETWEEN start_hour AND 23.99))
                )""",
        'The end time must be later than the start time.')]
