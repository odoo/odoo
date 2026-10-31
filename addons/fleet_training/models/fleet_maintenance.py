from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetMaintenance(models.Model):
    _name = 'fleet_training.maintenance'
    _description = 'Fleet Vehicle Maintenance'
    _order = 'date desc, id desc'

    vehicle_id = fields.Many2one('fleet_training.vehicle', string="Vehicle", required=True, ondelete='cascade')
    date = fields.Date(required=True, default=fields.Date.context_today)
    maintenance_type = fields.Selection(
        [
            ('service', 'Periodic Service'),
            ('repair', 'Repair'),
            ('tires', 'Tires'),
            ('other', 'Other'),
        ],
        string="Type", default='service', required=True,
    )
    odometer = fields.Integer(string="Odometer (km)")
    cost = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    description = fields.Text()

    @api.constrains('odometer')
    def _check_odometer(self):
        for record in self:
            if record.odometer < 0:
                raise ValidationError(self.env._("Odometer reading cannot be negative."))
